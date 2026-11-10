"""The subscriber side of NENA WebSocket subscribe/notify, without any I/O.

``Subscriber`` turns notifier messages into the replies to send, so the
protocol can be tested without sockets; ``ntip.interop.conveyance.client``
moves the messages over a WebSocket.

Behaviour:

- ``start()`` subscribes to new EIDOs (``requestSubType: new``) or, with an
  incident id, to one incident (``single``), and ``renew()`` re-subscribes
  with the subscription id before it expires.
- Every EIDO in an ``event`` goes through the import gateway, under the
  tenant this subscription belongs to. The ``eventResponse`` says 200 only if
  every EIDO was accepted (or was a resend of one already accepted), 400 if
  any was rejected (its receipt is still stored), 413 if one was too large,
  and 500 if processing failed. A notification resent with the same
  transaction id gets the same answer without being processed again.
- An event or terminate for another subscription gets 481.
- A message that fails the pinned schema is answered when it can be (an
  invalid event with a transaction id gets 400) and is otherwise recorded as
  a protocol problem; it is never processed.
"""

import json
import logging
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ntip.interop.conveyance.messages import (
    NOTIFIER_MESSAGES,
    InvalidMessage,
    Message,
    check,
)
from ntip.interop.conveyance.profile import CONVEYANCE_PROFILE, ConveyanceProfile
from ntip.interop.eido.profile import PROFILE as EIDO_PROFILE
from ntip.interop.gateway import EidoGateway, PayloadTooLarge, RevisionConflict
from ntip.interop.receipts import ReceiptStatus

log = logging.getLogger(__name__)

_ACCEPTED = {
    ReceiptStatus.ACCEPTED,
    ReceiptStatus.ACCEPTED_NO_NARRATIVE,
    ReceiptStatus.OUT_OF_ORDER,
}
# Remembered acknowledgements, so a resent notification is not processed twice.
MAX_REMEMBERED_TRANSACTIONS = 1000
# Renew once this fraction of the subscription period has passed.
RENEW_AT = 0.8


class State(StrEnum):
    IDLE = "idle"
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"  # terminated by the notifier or unsubscribed
    FAILED = "failed"  # the notifier refused the subscription


@dataclass
class Subscriber:
    gateway: EidoGateway
    tenant_id: str
    new_id: Callable[[str], str]
    clock: Callable[[], float]  # monotonic seconds
    expires_s: int = 3600
    incident_id: str | None = None
    profile: ConveyanceProfile = CONVEYANCE_PROFILE

    state: State = State.IDLE
    subscription_id: str | None = None
    failure: str | None = None
    problems: list[str] = field(default_factory=list)
    _pending: str | None = None
    _renew_at: float | None = None
    _answered: OrderedDict[str, dict[str, Any]] = field(default_factory=OrderedDict)

    # ------------------------------------------------------------ outgoing

    def start(self) -> dict[str, Any]:
        """The subscribe request that opens a subscription."""
        request: dict[str, Any] = {
            "requestId": self._request(),
            "requestType": "EIDO",
            "requestAccepts": self.profile.request_accepts,
            "expires": self.expires_s,
        }
        if self.incident_id is None:
            request["requestSubType"] = "new"
        else:
            request |= {"requestSubType": "single", "incidentId": self.incident_id}
        self.state = State.PENDING
        return {"subscribe": request}

    def renewal_due(self) -> bool:
        return (
            self.state is State.ACTIVE
            and self._renew_at is not None
            and (self.clock() >= self._renew_at)
        )

    def renew(self) -> dict[str, Any]:
        """Re-subscribe with the subscription id, extending it."""
        self._renew_at = None
        request = {
            "requestId": self._request(),
            "subscriptionId": self.subscription_id,
            "expires": self.expires_s,
        }
        return {"subscribe": request}

    def stop(self) -> dict[str, Any] | None:
        """The unsubscribe request, if there is an active subscription."""
        if self.state is not State.ACTIVE or self.subscription_id is None:
            return None
        return {
            "unsubscribe": {"requestId": self._request(), "subscriptionId": self.subscription_id}
        }

    def _request(self) -> str:
        self._pending = self.new_id("req")
        return self._pending

    # ------------------------------------------------------------ incoming

    def receive(self, raw: Any, correlation_id: str) -> list[dict[str, Any]]:
        """Handle one notifier message; returns the replies to send, in order."""
        try:
            message = check(raw, NOTIFIER_MESSAGES, self.profile)
        except InvalidMessage as err:
            self._problem(str(err))
            transaction = _transaction_id(raw)
            if transaction is not None:
                return [_event_response(transaction, 400, "Invalid event message")]
            return []
        handler = {
            "subscribeResponse": self._on_subscribe_response,
            "unsubscribeResponse": self._on_unsubscribe_response,
            "response": self._on_response,
            "event": lambda m: self._on_event(m, correlation_id),
            "terminate": self._on_terminate,
        }[message.kind]
        return handler(message)

    def _on_subscribe_response(self, message: Message) -> list[dict[str, Any]]:
        body = message.body
        if body["requestId"] != self._pending:
            self._problem(f"subscribeResponse for unknown request {body['requestId']!r}")
            return []
        self._pending = None
        if body["statusCode"] != 200 or not body.get("subscriptionId"):
            self.state = State.FAILED
            self.failure = f"{body['statusCode']} {body['statusText']}"
            return []
        self.state = State.ACTIVE
        self.subscription_id = body["subscriptionId"]
        granted = body.get("expires", self.expires_s)
        self._renew_at = self.clock() + RENEW_AT * granted if granted > 0 else None
        return []

    def _on_unsubscribe_response(self, message: Message) -> list[dict[str, Any]]:
        if message.body["subscriptionId"] == self.subscription_id:
            self.state = State.ENDED
        return []

    def _on_response(self, message: Message) -> list[dict[str, Any]]:
        # 501: the notifier does not implement what was asked.
        if message.body["requestId"] == self._pending:
            self.state = State.FAILED
            self.failure = f"{message.body['statusCode']} {message.body['statusText']}"
        return []

    def _on_terminate(self, message: Message) -> list[dict[str, Any]]:
        body = message.body
        known = body["subscriptionId"] == self.subscription_id
        if known:
            self.state = State.ENDED
        status, text = (200, "OK") if known else (481, "Subscription does not exist")
        reply = {"requestId": body["requestId"], "subscriptionId": body["subscriptionId"],
                 "statusCode": status, "statusText": text}  # fmt: skip
        return [{"terminateResponse": reply}]

    def _on_event(self, message: Message, correlation_id: str) -> list[dict[str, Any]]:
        body = message.body
        transaction = body["transactionId"]
        if transaction in self._answered:
            return [self._answered[transaction]]
        if self.state is not State.ACTIVE or body["subscriptionId"] != self.subscription_id:
            return [_event_response(transaction, 481, "Subscription does not exist")]
        status, text = self._process(body.get("notification", []), correlation_id)
        reply = _event_response(transaction, status, text)
        self._answered[transaction] = reply
        while len(self._answered) > MAX_REMEMBERED_TRANSACTIONS:
            self._answered.popitem(last=False)
        return [reply]

    def _process(self, eidos: list[Any], correlation_id: str) -> tuple[int, str]:
        """Ingest each EIDO; the status code and text for the acknowledgement."""
        rejected: list[str] = []
        for i, eido in enumerate(eidos):
            raw = json.dumps(eido, ensure_ascii=False).encode("utf-8")
            try:
                result = self.gateway.ingest(
                    raw,
                    tenant_id=self.tenant_id,
                    profile_id=EIDO_PROFILE.profile_id,
                    correlation_id=f"{correlation_id}:{i}",
                )
            except PayloadTooLarge:
                return 413, "EIDO too large"
            except RevisionConflict:
                rejected.append(f"EIDO {i + 1}: same revision with different content")
                continue
            except Exception:  # surfaced to the notifier as a server error, and logged
                log.exception("conveyance: processing EIDO %d failed", i + 1)
                return 500, "Processing failed"
            if result.receipt.status not in _ACCEPTED:
                rejected.append(f"EIDO {i + 1}: {result.receipt.status}")
        if rejected:
            return 400, "; ".join(rejected)[:200]
        return 200, "OK"

    def _problem(self, problem: str) -> None:
        log.warning("conveyance: %s", problem)
        self.problems.append(problem)


def _transaction_id(raw: Any) -> str | None:
    if isinstance(raw, dict) and isinstance(raw.get("event"), dict):
        value = raw["event"].get("transactionId")
        return value if isinstance(value, str) else None
    return None


def _event_response(transaction: str, status: int, text: str) -> dict[str, Any]:
    return {"eventResponse": {"transactionId": transaction, "statusCode": status,
                              "statusText": text}}  # fmt: skip

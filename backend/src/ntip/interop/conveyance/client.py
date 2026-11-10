"""Carry a Subscriber over a WebSocket to a NENA-STA-024 notifier.

One subscription per connection. The client sends the subscribe request,
answers every notifier message with the subscriber's replies, renews before
the subscription expires, and unsubscribes when asked to stop. If the
connection drops, the notifier refuses or ends the subscription, it
reconnects with capped exponential backoff and subscribes afresh; the
gateway's idempotency makes any EIDO the notifier resends harmless.

Only ``wss://`` is accepted unless TLS is explicitly waived (local testing).
The bearer token, if any, is sent in the handshake's Authorization header.
"""

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import InvalidHandshake, InvalidURI, WebSocketException

from ntip.interop.conveyance.subscriber import State, Subscriber
from ntip.interop.gateway import MAX_PAYLOAD_BYTES

log = logging.getLogger(__name__)

BACKOFF_S = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 60.0)
# A notification may carry several EIDOs, each bounded by the gateway.
MAX_MESSAGE_BYTES = 8 * MAX_PAYLOAD_BYTES


class InsecureUrl(ValueError):
    pass


async def run(
    url: str,
    make_subscriber: Callable[[], Subscriber],
    *,
    stop: asyncio.Event,
    token: str | None = None,
    require_tls: bool = True,
    backoff_s: Sequence[float] = BACKOFF_S,
    poll_s: float = 1.0,
) -> None:
    """Subscribe and process notifications until ``stop`` is set."""
    if require_tls and not url.startswith("wss://"):
        raise InsecureUrl("conveyance requires wss:// (TLS) outside local testing")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    failures = 0
    while not stop.is_set():
        subscriber = make_subscriber()
        try:
            async with connect(
                url, additional_headers=headers, max_size=MAX_MESSAGE_BYTES, open_timeout=10
            ) as ws:
                await ws.send(json.dumps(subscriber.start()))
                while not stop.is_set() and subscriber.state not in {State.ENDED, State.FAILED}:
                    if subscriber.renewal_due():
                        await ws.send(json.dumps(subscriber.renew()))
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=poll_s)
                    except TimeoutError:
                        continue
                    for reply in await asyncio.to_thread(_handle, subscriber, raw):
                        await ws.send(json.dumps(reply))
                    if subscriber.state is State.ACTIVE:
                        failures = 0
                if stop.is_set():
                    goodbye = subscriber.stop()
                    if goodbye is not None:
                        await ws.send(json.dumps(goodbye))
                    return
        except (OSError, TimeoutError, InvalidURI, InvalidHandshake, WebSocketException) as err:
            log.warning("conveyance: connection to %s failed or dropped: %s", url, err)
        if subscriber.state is State.FAILED:
            log.error("conveyance: subscription refused: %s", subscriber.failure)
        delay = backoff_s[min(failures, len(backoff_s) - 1)]
        failures += 1
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=delay)


def _handle(subscriber: Subscriber, raw: str | bytes) -> list[dict[str, Any]]:
    correlation_id = f"conv_{uuid.uuid4().hex}"
    try:
        message = json.loads(raw)
    except ValueError:
        subscriber.problems.append("message is not JSON")
        return []
    return subscriber.receive(message, correlation_id)

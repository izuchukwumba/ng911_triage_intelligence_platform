"""NENA-STA-024 WebSocket subscriber: protocol behaviour, then end to end over a socket."""

import asyncio
import json
from itertools import count
from typing import Any

import pytest
from websockets.asyncio.server import ServerConnection, serve

from ntip.evaluation.runner import REPO_ROOT
from ntip.interop.conveyance.client import InsecureUrl, run
from ntip.interop.conveyance.messages import SUBSCRIBER_MESSAGES, check
from ntip.interop.conveyance.subscriber import State, Subscriber
from ntip.interop.eido.fetch import SchemaUnavailable, load_documents
from ntip.interop.gateway import EidoGateway
from ntip.pipeline import Pipeline
from ntip.store import InMemoryEventStore

FIXTURES = REPO_ROOT / "data" / "interop" / "eido"


@pytest.fixture(scope="module", autouse=True)
def schemas() -> None:
    from ntip.interop.conveyance.profile import CONVEYANCE_PROFILE

    try:
        load_documents()
        load_documents(CONVEYANCE_PROFILE)
    except SchemaUnavailable as err:
        pytest.skip(f"pinned NENA schema unavailable: {err}")


def eido(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text("utf-8"))


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def store() -> InMemoryEventStore:
    return InMemoryEventStore()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def subscriber(store: InMemoryEventStore, clock: Clock) -> Subscriber:
    ids = count(1)
    return Subscriber(
        gateway=EidoGateway(Pipeline(store=store)),
        tenant_id="psap-a",
        new_id=lambda prefix: f"{prefix}-{next(ids)}",
        clock=clock,
        expires_s=600,
    )


def subscribed(subscriber: Subscriber) -> Subscriber:
    request = subscriber.start()["subscribe"]
    subscriber.receive({"subscribeResponse": {"requestId": request["requestId"],
                        "subscriptionId": "sub-1", "expires": 600, "statusCode": 200,
                        "statusText": "OK"}}, "c")  # fmt: skip
    assert subscriber.state is State.ACTIVE
    return subscriber


def event(transaction: str, *eidos: Any, subscription: str = "sub-1") -> dict[str, Any]:
    return {"event": {"subscriptionId": subscription, "transactionId": transaction,
                      "notification": list(eidos)}}  # fmt: skip


def reply(messages: list[dict[str, Any]]) -> dict[str, Any]:
    [message] = messages
    check(message, SUBSCRIBER_MESSAGES)  # every reply is valid against NENA's schema
    [(_, body)] = message.items()
    assert isinstance(body, dict)
    return body


def test_subscribe_request_is_valid_and_asks_for_new_eidos(subscriber: Subscriber) -> None:
    message = subscriber.start()
    check(message, SUBSCRIBER_MESSAGES)
    assert message["subscribe"]["requestType"] == "EIDO"
    assert message["subscribe"]["requestSubType"] == "new"
    assert subscriber.state is State.PENDING


def test_an_event_is_ingested_and_acknowledged(
    subscriber: Subscriber, store: InMemoryEventStore
) -> None:
    subscribed(subscriber)
    body = reply(subscriber.receive(event("tx-1", eido("rev1-smoke.json")), "c"))
    assert (body["transactionId"], body["statusCode"]) == ("tx-1", 200)
    total, [summary] = store.list_incidents(limit=10, offset=0, tenant_id="psap-a")
    assert total == 1 and summary.latest_assessment is not None


def test_a_resent_notification_is_answered_without_reprocessing(
    subscriber: Subscriber, store: InMemoryEventStore
) -> None:
    subscribed(subscriber)
    first = subscriber.receive(event("tx-1", eido("rev1-smoke.json")), "c")
    again = subscriber.receive(event("tx-1", eido("rev1-smoke.json")), "c")
    assert first == again
    assert len(store.interop_receipts("psap-a", eido("rev1-smoke.json")["$id"])) == 1


def test_an_invalid_eido_is_rejected_but_kept(
    subscriber: Subscriber, store: InMemoryEventStore
) -> None:
    subscribed(subscriber)
    body = reply(
        subscriber.receive(
            event("tx-2", eido("rev1-smoke.json"), eido("unsupported-version.json")), "c"
        )
    )
    assert body["statusCode"] == 400
    assert "EIDO 2: rejected_unsupported_version" in body["statusText"]
    # The valid EIDO in the same notification was still processed.
    assert store.list_incidents(limit=10, offset=0, tenant_id="psap-a")[0] == 1


def test_events_for_another_subscription_get_481(subscriber: Subscriber) -> None:
    subscribed(subscriber)
    body = reply(subscriber.receive(event("tx-3", subscription="sub-other"), "c"))
    assert body["statusCode"] == 481


def test_an_invalid_message_is_never_processed(
    subscriber: Subscriber, store: InMemoryEventStore
) -> None:
    subscribed(subscriber)
    # notification must be an array; the transaction id lets the subscriber say so.
    bad = {"event": {"subscriptionId": "sub-1", "transactionId": "tx-4", "notification": "x"}}
    assert reply(subscriber.receive(bad, "c"))["statusCode"] == 400
    assert subscriber.receive({"hello": {}}, "c") == []
    assert subscriber.receive({"event": {}, "terminate": {}}, "c") == []
    assert len(subscriber.problems) == 3
    assert store.list_incidents(limit=10, offset=0)[0] == 0


def test_terminate_ends_the_subscription(subscriber: Subscriber) -> None:
    subscribed(subscriber)
    body = reply(
        subscriber.receive({"terminate": {"requestId": "n-1", "subscriptionId": "sub-1"}}, "c")
    )
    assert (body["statusCode"], subscriber.state) == (200, State.ENDED)


def test_a_refused_subscription_fails(subscriber: Subscriber) -> None:
    request = subscriber.start()["subscribe"]
    subscriber.receive({"subscribeResponse": {"requestId": request["requestId"],
                        "statusCode": 403, "statusText": "Forbidden"}}, "c")  # fmt: skip
    assert (subscriber.state, subscriber.failure) == (State.FAILED, "403 Forbidden")


def test_renewal_before_expiry_and_unsubscribe(subscriber: Subscriber, clock: Clock) -> None:
    subscribed(subscriber)
    assert not subscriber.renewal_due()
    clock.now = 0.8 * 600
    assert subscriber.renewal_due()
    renewal = subscriber.renew()
    check(renewal, SUBSCRIBER_MESSAGES)
    assert renewal["subscribe"]["subscriptionId"] == "sub-1"
    goodbye = subscriber.stop()
    assert goodbye is not None
    check(goodbye, SUBSCRIBER_MESSAGES)


def test_subscribing_to_one_incident(subscriber: Subscriber) -> None:
    subscriber.incident_id = "urn:emergency:uid:incidentid:synthetic-0001:synthetic.example"
    request = subscriber.start()["subscribe"]
    assert (request["requestSubType"], request["incidentId"]) == ("single", subscriber.incident_id)


# --------------------------------------------------------------- over a socket


def test_end_to_end_over_a_websocket_with_reconnect(store: InMemoryEventStore) -> None:
    """A fake notifier: subscribes the client, sends one EIDO, drops the
    connection, and expects the client to come back and subscribe again."""
    received: list[dict[str, Any]] = []
    tokens: list[str | None] = []
    connections = 0
    done = asyncio.Event()

    async def notifier(ws: ServerConnection) -> None:
        nonlocal connections
        connections += 1
        tokens.append(ws.request.headers.get("Authorization") if ws.request else None)
        subscribe = json.loads(await ws.recv())
        received.append(subscribe)
        response = {
            "requestId": subscribe["subscribe"]["requestId"],
            "subscriptionId": f"sub-{connections}",
            "expires": 600,
            "statusCode": 200,
            "statusText": "OK",
        }
        await ws.send(json.dumps({"subscribeResponse": response}))
        if connections == 1:
            await ws.send(json.dumps(event("tx-1", eido("rev1-smoke.json"), subscription="sub-1")))
            received.append(json.loads(await ws.recv()))
            await ws.close()  # simulate a dropped connection
        else:
            done.set()
            await ws.wait_closed()

    async def scenario() -> None:
        stop = asyncio.Event()
        ids = count(1)
        gateway = EidoGateway(Pipeline(store=store))

        def make() -> Subscriber:
            return Subscriber(gateway=gateway, tenant_id="psap-a",
                              new_id=lambda p: f"{p}-{next(ids)}", clock=lambda: 0.0)  # fmt: skip

        async with serve(notifier, "127.0.0.1", 0) as server:
            port = next(iter(server.sockets)).getsockname()[1]
            client = asyncio.create_task(
                run(
                    f"ws://127.0.0.1:{port}",
                    make,
                    stop=stop,
                    token="secret",
                    require_tls=False,
                    backoff_s=[0.05],
                    poll_s=0.05,
                )
            )
            await asyncio.wait_for(done.wait(), timeout=10)
            stop.set()
            await asyncio.wait_for(client, timeout=10)

    asyncio.run(scenario())
    assert connections == 2  # reconnected after the drop
    assert tokens == ["Bearer secret", "Bearer secret"]
    ack = received[1]["eventResponse"]
    assert (ack["transactionId"], ack["statusCode"]) == ("tx-1", 200)
    assert store.list_incidents(limit=10, offset=0, tenant_id="psap-a")[0] == 1


def test_plain_ws_is_refused_unless_waived() -> None:
    async def attempt() -> None:
        await run("ws://notifier.example/ent", lambda: None, stop=asyncio.Event())  # type: ignore[arg-type,return-value]

    with pytest.raises(InsecureUrl):
        asyncio.run(attempt())

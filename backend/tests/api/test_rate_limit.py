from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.ratelimit import RateLimiter, client_key
from ntip.api.settings import Settings
from ntip.store import InMemoryEventStore


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_sliding_window() -> None:
    clock = FakeClock()
    limiter = RateLimiter(2, clock)
    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") == 60  # third request in the same minute
    assert limiter.check("b") is None  # other clients are independent
    clock.now += 60
    assert limiter.check("a") is None


def test_disabled_at_zero() -> None:
    assert not RateLimiter(0).enabled


def test_clients_are_keyed_by_token_before_address() -> None:
    assert client_key("Bearer x", "1.2.3.4") != client_key("Bearer y", "1.2.3.4")
    assert client_key(None, "1.2.3.4") == "addr:1.2.3.4"
    assert "x" not in client_key("Bearer x", None)  # the token itself is not kept


def test_api_answers_429_with_retry_after_and_exempts_health() -> None:
    client = TestClient(
        create_app(store=InMemoryEventStore(), settings=Settings(rate_limit_per_minute=3))
    )
    statuses = [client.get("/v1/incidents").status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 429]
    limited = client.get("/v1/incidents")
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.json()["error"]["correlation_id"]
    assert all(client.get("/health/live").status_code == 200 for _ in range(5))

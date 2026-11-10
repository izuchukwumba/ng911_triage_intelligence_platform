from fastapi.testclient import TestClient

from ntip import __version__
from ntip.api import create_app
from ntip.store import InMemoryEventStore

client = TestClient(create_app())


def test_live_reports_ok_and_version() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_ready_checks_the_event_store() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"event_store": True}}


def test_not_ready_when_the_store_is_unreachable() -> None:
    class DownStore(InMemoryEventStore):
        def ping(self) -> bool:
            return False

    response = TestClient(create_app(store=DownStore())).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"

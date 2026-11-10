from fastapi.testclient import TestClient

from ntip import __version__
from ntip.api import create_app

client = TestClient(create_app())


def test_live_reports_ok_and_version() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_ready_reports_ready_with_no_dependencies() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {}}

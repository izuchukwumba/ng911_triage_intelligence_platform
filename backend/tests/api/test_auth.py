import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.auth import Principal, Role
from ntip.api.settings import ConfigurationError, Settings
from ntip.store import InMemoryEventStore

TOKENS = {
    "t-viewer": Principal("vera", Role.VIEWER),
    "t-operator": Principal("olu", Role.OPERATOR),
    "t-analyst": Principal("ana", Role.ANALYST),
}
CALL = {"text": "My father is not breathing at 12 Oak Street.", "synthetic": True}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(api_tokens=TOKENS, auth_disabled=False)
    return TestClient(create_app(store=InMemoryEventStore(), settings=settings))


def ingest(client: TestClient) -> dict[str, str]:
    response = client.post("/v1/incidents", json=CALL, headers=auth("t-operator"))
    assert response.status_code == 202
    body: dict[str, str] = response.json()
    return body


class TestConfiguration:
    def test_refuses_to_start_without_tokens_or_explicit_opt_out(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NTIP_API_TOKENS", raising=False)
        monkeypatch.delenv("NTIP_AUTH_DISABLED", raising=False)
        with pytest.raises(ConfigurationError, match="NTIP_API_TOKENS"):
            Settings.from_env()

    def test_parses_tokens_and_rejects_unknown_roles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NTIP_API_TOKENS", "abc:olu:operator, def:vera:viewer")
        settings = Settings.from_env()
        assert settings.api_tokens["abc"] == Principal("olu", Role.OPERATOR)
        assert not settings.auth_disabled
        monkeypatch.setenv("NTIP_API_TOKENS", "abc:olu:superuser")
        with pytest.raises(ConfigurationError, match="superuser"):
            Settings.from_env()

    def test_tokens_win_over_the_opt_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NTIP_API_TOKENS", "abc:olu:operator")
        monkeypatch.setenv("NTIP_AUTH_DISABLED", "1")
        assert not Settings.from_env().auth_disabled


class TestAccess:
    def test_missing_or_wrong_token_is_401(self, client: TestClient) -> None:
        response = client.get("/v1/incidents")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert client.get("/v1/incidents", headers=auth("nope")).status_code == 401

    def test_health_checks_stay_public(self, client: TestClient) -> None:
        assert client.get("/health/live").status_code == 200

    @pytest.mark.parametrize(
        ("token", "can_ingest", "can_replay"),
        [("t-viewer", False, False), ("t-operator", True, False), ("t-analyst", False, True)],
    )
    def test_roles(
        self, client: TestClient, token: str, can_ingest: bool, can_replay: bool
    ) -> None:
        assert client.get("/v1/incidents", headers=auth(token)).status_code == 200
        ingest_status = client.post("/v1/incidents", json=CALL, headers=auth(token)).status_code
        assert (ingest_status == 202) is can_ingest
        if not can_ingest:
            assert ingest_status == 403
        replay_status = client.post("/v1/replay-runs", json={}, headers=auth(token)).status_code
        assert (replay_status == 201) is can_replay

    def test_reviewer_is_the_token_holder_not_the_body(self, client: TestClient) -> None:
        created = ingest(client)
        response = client.post(
            f"/v1/incidents/{created['incident_id']}/reviews",
            json={"assessment_id": created["assessment_id"], "decision": "confirm",
                  "reviewer_id": "someone_else"},
            headers=auth("t-operator"),
        )  # fmt: skip
        assert response.status_code == 201
        assert response.json()["reviewer_id"] == "olu"
        events = client.get(
            f"/v1/incidents/{created['incident_id']}/events", headers=auth("t-viewer")
        ).json()["events"]
        assert events[-1]["actor"]["actor_id"] == "olu"

    def test_viewer_cannot_review(self, client: TestClient) -> None:
        created = ingest(client)
        response = client.post(
            f"/v1/incidents/{created['incident_id']}/reviews",
            json={"assessment_id": created["assessment_id"], "decision": "confirm"},
            headers=auth("t-viewer"),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_replay_requester_is_the_token_holder(self, client: TestClient) -> None:
        ingest(client)
        run = client.post("/v1/replay-runs", json={}, headers=auth("t-analyst")).json()
        assert run["requested_by"] == "ana"


def test_without_authentication_the_body_must_name_the_reviewer() -> None:
    client = TestClient(create_app(store=InMemoryEventStore(), settings=Settings()))
    created = client.post("/v1/incidents", json=CALL).json()
    response = client.post(
        f"/v1/incidents/{created['incident_id']}/reviews",
        json={"assessment_id": created["assessment_id"], "decision": "confirm"},
    )
    assert response.status_code == 422

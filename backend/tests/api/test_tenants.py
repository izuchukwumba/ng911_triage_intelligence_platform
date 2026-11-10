"""Incidents are separated by tenant (INT-010): another tenant's incident does not exist."""

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.auth import Principal, Role
from ntip.api.settings import ConfigurationError, Settings
from ntip.store import InMemoryEventStore

TOKENS = {
    "a-op": Principal("ada", Role.OPERATOR, tenant_id="psap-a"),
    "a-an": Principal("abe", Role.ANALYST, tenant_id="psap-a"),
    "b-op": Principal("bo", Role.OPERATOR, tenant_id="psap-b"),
    "b-an": Principal("bea", Role.ANALYST, tenant_id="psap-b"),
}
CALL = {"text": "My father is not breathing at 12 Oak Street.", "synthetic": True}


def auth(token: str, **extra: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", **extra}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(api_tokens=TOKENS, auth_disabled=False)
    return TestClient(create_app(store=InMemoryEventStore(), settings=settings))


@pytest.fixture
def incident_a(client: TestClient) -> dict[str, str]:
    response = client.post("/v1/incidents", json=CALL, headers=auth("a-op"))
    assert response.status_code == 202
    body: dict[str, str] = response.json()
    return body


def test_a_tenant_lists_only_its_own_incidents(
    client: TestClient, incident_a: dict[str, str]
) -> None:
    mine = client.get("/v1/incidents", headers=auth("a-op")).json()
    assert [i["incident_id"] for i in mine["items"]] == [incident_a["incident_id"]]
    assert client.get("/v1/incidents", headers=auth("b-op")).json()["total"] == 0


@pytest.mark.parametrize("path", ["", "/events", "/model-outputs"])
def test_another_tenants_incident_is_not_found(
    client: TestClient, incident_a: dict[str, str], path: str
) -> None:
    url = f"/v1/incidents/{incident_a['incident_id']}{path}"
    assert client.get(url, headers=auth("a-op")).status_code == 200
    other = client.get(url, headers=auth("b-op"))
    # Indistinguishable from an incident that does not exist.
    unknown = client.get(f"/v1/incidents/inc_missing{path}", headers=auth("b-op"))
    assert other.status_code == unknown.status_code == 404
    assert other.json()["error"]["code"] == unknown.json()["error"]["code"]


def test_another_tenant_cannot_add_messages_or_review(
    client: TestClient, incident_a: dict[str, str]
) -> None:
    incident_id = incident_a["incident_id"]
    message = client.post(f"/v1/incidents/{incident_id}/messages", json=CALL, headers=auth("b-op"))
    review = client.post(
        f"/v1/incidents/{incident_id}/reviews",
        json={"assessment_id": incident_a["assessment_id"], "decision": "confirm"},
        headers=auth("b-op"),
    )
    assert (message.status_code, review.status_code) == (404, 404)
    events = client.get(f"/v1/incidents/{incident_id}/events", headers=auth("a-op")).json()
    assert all(e["actor"]["actor_id"] != "bo" for e in events["events"])


def test_idempotency_keys_are_per_tenant(client: TestClient) -> None:
    key = {"Idempotency-Key": "call-123"}
    first_a = client.post("/v1/incidents", json=CALL, headers=auth("a-op", **key)).json()
    first_b = client.post("/v1/incidents", json=CALL, headers=auth("b-op", **key))
    # The same key in another tenant is a new request, not a replay of tenant A's.
    assert first_b.status_code == 202
    assert first_b.headers.get("Idempotent-Replayed") is None
    assert first_b.json()["incident_id"] != first_a["incident_id"]
    again_a = client.post("/v1/incidents", json=CALL, headers=auth("a-op", **key))
    assert again_a.headers["Idempotent-Replayed"] == "true"
    assert again_a.json()["incident_id"] == first_a["incident_id"]


def test_replay_runs_cover_and_show_one_tenant(
    client: TestClient, incident_a: dict[str, str]
) -> None:
    client.post("/v1/incidents", json=CALL, headers=auth("b-op"))
    run_a = client.post("/v1/replay-runs", json={}, headers=auth("a-an")).json()
    assert [c["incident_id"] for c in run_a["cases"]] == [incident_a["incident_id"]]
    assert run_a["tenant_id"] == "psap-a"

    assert client.get(f"/v1/replay-runs/{run_a['run_id']}", headers=auth("b-an")).status_code == 404
    assert client.get("/v1/replay-runs", headers=auth("b-an")).json() == []
    # Naming another tenant's incident explicitly does not work either.
    named = client.post(
        "/v1/replay-runs", json={"incident_ids": [incident_a["incident_id"]]}, headers=auth("b-an")
    )
    assert named.status_code == 404


def test_tokens_name_an_optional_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NTIP_API_TOKENS", "t1:ada:operator:psap-a, t2:vera:viewer")
    tokens = Settings.from_env().api_tokens
    assert tokens["t1"] == Principal("ada", Role.OPERATOR, tenant_id="psap-a")
    assert tokens["t2"].tenant_id == "default"
    monkeypatch.setenv("NTIP_API_TOKENS", "t1:ada:operator:psap a")
    with pytest.raises(ConfigurationError, match="tenant"):
        Settings.from_env()

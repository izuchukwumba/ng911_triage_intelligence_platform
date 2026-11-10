from typing import Any

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.store import InMemoryEventStore

CRITICAL = "My father is not breathing. We are at 12 Oak Street."


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(store=InMemoryEventStore()), raise_server_exceptions=False)


def ingest(client: TestClient, text: str = CRITICAL, **headers: str) -> Any:
    return client.post("/v1/incidents", json={"text": text, "synthetic": True}, headers=headers)


class TestIngest:
    def test_accepts_and_assesses(self, client: TestClient) -> None:
        response = ingest(client)
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["advisory_priority"] == "P0"
        assert body["processing_status"] == "completed"
        assert response.headers["X-Correlation-ID"].startswith("req_")

    def test_rejects_non_synthetic_input(self, client: TestClient) -> None:
        response = client.post("/v1/incidents", json={"text": CRITICAL, "synthetic": False})
        assert response.status_code == 422

    def test_rejects_unknown_fields(self, client: TestClient) -> None:
        body = {"text": CRITICAL, "synthetic": True, "priority": "P4"}
        assert client.post("/v1/incidents", json=body).status_code == 422

    def test_rejects_oversized_transcripts_without_echoing_them(self, client: TestClient) -> None:
        secret = "SECRET-MARKER " + "x" * 20_000
        response = ingest(client, secret)
        assert response.status_code == 422
        assert "SECRET-MARKER" not in response.text
        assert response.json()["error"]["code"] == "invalid_request"

    def test_idempotent_retry(self, client: TestClient) -> None:
        first = ingest(client, **{"Idempotency-Key": "abc"})
        retry = ingest(client, **{"Idempotency-Key": "abc"})
        assert retry.status_code == 202
        assert retry.headers["Idempotent-Replayed"] == "true"
        assert retry.json()["incident_id"] == first.json()["incident_id"]
        assert client.get("/v1/incidents").json()["total"] == 1

    def test_idempotency_key_reused_with_other_body(self, client: TestClient) -> None:
        ingest(client, **{"Idempotency-Key": "abc"})
        response = ingest(client, "Something else", **{"Idempotency-Key": "abc"})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "idempotency_conflict"

    def test_follow_up_message(self, client: TestClient) -> None:
        incident_id = ingest(client, "Smoke at 12 Oak Street.").json()["incident_id"]
        response = client.post(
            f"/v1/incidents/{incident_id}/messages",
            json={"text": "People are trapped inside.", "synthetic": True},
        )
        assert response.status_code == 202
        assert response.json()["advisory_priority"] == "P0"
        detail = client.get(f"/v1/incidents/{incident_id}").json()
        assert len(detail["sources"]) == 2

    def test_follow_up_to_unknown_incident(self, client: TestClient) -> None:
        response = client.post(
            "/v1/incidents/inc_missing/messages", json={"text": "hi", "synthetic": True}
        )
        assert response.status_code == 404


class TestRead:
    def test_list_newest_first(self, client: TestClient) -> None:
        ingest(client, "Smoke at 12 Oak Street.")
        ingest(client)
        page = client.get("/v1/incidents?limit=1").json()
        assert page["total"] == 2
        assert page["items"][0]["advisory_priority"] == "P0"
        assert len(page["items"]) == 1

    def test_detail_shows_evidence_and_state(self, client: TestClient) -> None:
        incident_id = ingest(client).json()["incident_id"]
        detail = client.get(f"/v1/incidents/{incident_id}").json()
        assert detail["state"] == "awaiting_review"
        assert detail["effective_priority"] == "P0"
        [obs] = [o for o in detail["incident"]["observations"] if o["code"] == "NOT_BREATHING"]
        assert obs["evidence"]["text"] == "is not breathing"
        assert detail["assessment"]["reasons"][0]["rule_id"] == "R-RESP-001"

    def test_audit_trail(self, client: TestClient) -> None:
        incident_id = ingest(client).json()["incident_id"]
        events = client.get(f"/v1/incidents/{incident_id}/events").json()["events"]
        assert [e["event_type"] for e in events] == [
            "source.received",
            "incident.parsed",
            "triage.assessed",
        ]

    def test_unknown_incident_is_404_with_structured_error(self, client: TestClient) -> None:
        response = client.get("/v1/incidents/inc_missing", headers={"X-Correlation-ID": "abc-1"})
        assert response.status_code == 404
        assert response.json() == {
            "error": {
                "code": "not_found",
                "message": "Incident or assessment not found.",
                "correlation_id": "abc-1",
            }
        }

    def test_get_assessment(self, client: TestClient) -> None:
        assessment_id = ingest(client).json()["assessment_id"]
        response = client.get(f"/v1/assessments/{assessment_id}")
        assert response.json()["severity_band"] == "critical"


class TestReview:
    def test_override_keeps_machine_output(self, client: TestClient) -> None:
        created = ingest(client, "I twisted my ankle at 99 Cedar Lane.").json()
        response = client.post(
            f"/v1/incidents/{created['incident_id']}/reviews",
            json={
                "assessment_id": created["assessment_id"],
                "reviewer_id": "op_7",
                "decision": "override_priority",
                "override_priority": "P1",
                "reason": "Caller is alone and cannot move",
            },
        )
        assert response.status_code == 201
        detail = client.get(f"/v1/incidents/{created['incident_id']}").json()
        assert (detail["state"], detail["effective_priority"]) == ("reviewed", "P1")
        assert detail["assessment"]["advisory_priority"] == "P3"

    def test_override_without_reason_is_rejected(self, client: TestClient) -> None:
        created = ingest(client).json()
        response = client.post(
            f"/v1/incidents/{created['incident_id']}/reviews",
            json={
                "assessment_id": created["assessment_id"],
                "reviewer_id": "op_7",
                "decision": "override_priority",
                "override_priority": "P3",
            },
        )
        assert response.status_code == 422


def test_unhandled_errors_do_not_leak_details() -> None:
    class Broken(InMemoryEventStore):
        def list_incidents(self, *, limit: int, offset: int) -> Any:
            raise RuntimeError("database password is hunter2")

    client = TestClient(create_app(store=Broken()), raise_server_exceptions=False)
    response = client.get("/v1/incidents")
    assert response.status_code == 500
    assert "hunter2" not in response.text
    assert response.json()["error"]["code"] == "internal_error"

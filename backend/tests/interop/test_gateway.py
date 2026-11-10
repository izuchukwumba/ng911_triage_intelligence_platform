"""Interoperability verification matrix, design v1.2 section 3B.7 (INT-001 to INT-012).

Each test is named after the matrix row it covers. They run through the HTTP
API against the pinned NENA schema and are skipped if it cannot be fetched.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.settings import Settings
from ntip.evaluation.runner import REPO_ROOT
from ntip.interop.eido.adapter import map_eido
from ntip.interop.eido.fetch import SchemaUnavailable, load_documents
from ntip.interop.eido.profile import ADAPTER_VERSION, PROFILE
from ntip.schema.canonical import Incident, InferenceMode
from ntip.store import InMemoryEventStore

FIXTURES = REPO_ROOT / "data" / "interop" / "eido"
GOLDEN = Path(__file__).parent / "golden" / "mapping-unknown-optional-field.json"
TENANT_A = {"Authorization": "Bearer token-a", "X-Interop-Profile": PROFILE.profile_id,
            "Content-Type": "application/json"}  # fmt: skip
TENANT_B = {**TENANT_A, "Authorization": "Bearer token-b"}


@pytest.fixture(scope="module", autouse=True)
def schema() -> None:
    try:
        load_documents()
    except SchemaUnavailable as err:
        pytest.skip(f"pinned EIDO schema unavailable: {err}")


@pytest.fixture
def client() -> TestClient:
    settings = Settings(interop_tokens={"token-a": "tenant-a", "token-b": "tenant-b"})
    return TestClient(create_app(store=InMemoryEventStore(), settings=settings))


def raw(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def post(client: TestClient, body: bytes, headers: dict[str, str] = TENANT_A) -> Any:
    return client.post("/v1/interop/eido/ingest", content=body, headers=headers)


def test_int_001_valid_payload_is_accepted_with_traceable_mapping(client: TestClient) -> None:
    response = post(client, raw("rev1-smoke.json"))
    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["adapterVersion"]) == (
        "accepted_for_advisory_processing",
        ADAPTER_VERSION,
    )
    receipt = client.get(f"/v1/interop/receipts/{body['receiptId']}", headers=TENANT_A).json()
    [notes] = [m for m in receipt["mapping"] if m["status"] == "mapped"]
    assert notes["source_pointer"] == "/notesComponent/0/notesActionComments"
    assert notes["target"] == "SourceEvent.text"
    detail = client.get(f"/v1/incidents/{body['incidentId']}").json()
    assert detail["sources"][0]["source_type"] == "eido_import"
    assert detail["assessment"]["severity_band"] == "elevated"


def test_int_002_unsupported_version_is_rejected_explicitly(client: TestClient) -> None:
    response = post(client, raw("unsupported-version.json"))
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "rejected_unsupported_version"
    assert "2.0" in body["problems"][0]
    assert body["incidentId"] is None


def test_int_003_missing_required_fields_are_quarantined_without_processing(
    client: TestClient,
) -> None:
    eido = json.loads(raw("rev1-smoke.json"))
    del eido["agencyComponent"]
    response = post(client, json.dumps(eido).encode())
    assert response.status_code == 422
    assert response.json()["status"] == "quarantined_invalid"
    assert client.get("/v1/incidents").json()["total"] == 0  # nothing reached the parser


def test_int_004_unknown_optional_field_is_preserved_and_flagged(client: TestClient) -> None:
    body = post(client, raw("unknown-optional-field.json")).json()
    receipt = client.get(f"/v1/interop/receipts/{body['receiptId']}", headers=TENANT_A).json()
    flagged = {m["source_pointer"]: m["status"] for m in receipt["mapping"]}
    assert flagged["/vendorExtension"] == "preserved_unmapped"
    payload = client.get(f"/v1/interop/receipts/{body['receiptId']}/payload", headers=TENANT_A)
    assert json.loads(payload.content)["vendorExtension"] == {"cadUnit": "E12"}


def test_int_005_duplicate_submission_is_one_logical_intake(client: TestClient) -> None:
    first = post(client, raw("rev1-smoke.json"))
    again = post(client, raw("rev1-smoke.json"))
    assert again.status_code == 202
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.json()["receiptId"] == first.json()["receiptId"]
    detail = client.get(f"/v1/incidents/{first.json()['incidentId']}").json()
    assert len(detail["sources"]) == 1


def test_int_005b_same_revision_with_different_content_conflicts(client: TestClient) -> None:
    post(client, raw("rev1-smoke.json"))
    altered = json.loads(raw("rev1-smoke.json"))
    altered["notesComponent"][0]["notesActionComments"] = "Something else."
    assert post(client, json.dumps(altered).encode()).status_code == 409


def test_int_006_out_of_order_revisions_keep_history_without_rollback(client: TestClient) -> None:
    newer = post(client, raw("rev2-trapped.json")).json()
    older = post(client, raw("rev1-smoke.json")).json()
    assert older["status"] == "accepted_out_of_order"
    assert older["assessmentStatus"] == "no_new_narrative"
    detail = client.get(f"/v1/incidents/{newer['incidentId']}").json()
    assert detail["assessment"]["advisory_priority"] == "P0"  # not rolled back
    assert len(detail["sources"]) == 1


def test_int_006b_in_order_revision_adds_only_new_notes(client: TestClient) -> None:
    first = post(client, raw("rev1-smoke.json")).json()
    second = post(client, raw("rev2-trapped.json")).json()
    assert second["incidentId"] == first["incidentId"]
    detail = client.get(f"/v1/incidents/{first['incidentId']}").json()
    assert [s["text"] for s in detail["sources"]] == [
        "Caller reports smoke on the second floor at 12 Oak Street.",
        "Update: two children are trapped in the back bedroom.",
    ]
    assert detail["assessment"]["severity_band"] == "critical"


def test_int_007_model_outage_does_not_block_the_incident_flow(client: TestClient) -> None:
    class Down:
        model_id, model_version = "down", "0"

        def infer(self, request: Any) -> Any:
            raise TimeoutError("inference timed out")

    pipeline = client.app.state.pipeline  # type: ignore[attr-defined]
    pipeline.inference_mode, pipeline.extractor = InferenceMode.HYBRID_REVIEW, Down()
    body = post(client, raw("rev1-smoke.json")).json()
    assert body["assessmentStatus"] == "assessed"
    incident = client.get(f"/v1/incidents/{body['incidentId']}").json()["incident"]
    assert Incident.model_validate(incident).inference is not None
    assert incident["inference"]["status"] == "degraded"


def test_int_008_contradictory_location_keeps_urgency(client: TestClient) -> None:
    body = post(client, raw("conflicting-location.json")).json()
    assessment = client.get(f"/v1/incidents/{body['incidentId']}").json()["assessment"]
    assert assessment["advisory_priority"] == "P0"
    assert assessment["location_quality"]["status"] == "conflicting"
    assert "VERIFY_LOCATION" in assessment["review_actions"]


def test_int_009_instructions_in_the_narrative_are_not_executed(client: TestClient) -> None:
    body = post(client, raw("injection.json")).json()
    assessment = client.get(f"/v1/incidents/{body['incidentId']}").json()["assessment"]
    assert assessment["advisory_priority"] == "P0"


def test_int_010_tenants_cannot_see_each_others_receipts(client: TestClient) -> None:
    receipt_id = post(client, raw("rev1-smoke.json")).json()["receiptId"]
    assert client.get(f"/v1/interop/receipts/{receipt_id}", headers=TENANT_B).status_code == 404
    assert (
        client.get(f"/v1/interop/receipts/{receipt_id}/payload", headers=TENANT_B).status_code
        == 404
    )
    # The same external incident id from another tenant is a different incident.
    other = post(client, raw("rev1-smoke.json"), TENANT_B).json()
    mine = client.get(f"/v1/interop/receipts/{receipt_id}", headers=TENANT_A).json()
    assert other["incidentId"] != mine["incident_id"]


def test_int_010b_interop_fails_closed(client: TestClient) -> None:
    assert (
        post(
            client, raw("rev1-smoke.json"), {**TENANT_A, "Authorization": "Bearer nope"}
        ).status_code
        == 401
    )
    disabled = TestClient(create_app(store=InMemoryEventStore(), settings=Settings()))
    assert post(disabled, raw("rev1-smoke.json")).status_code == 403
    wrong_profile = {**TENANT_A, "X-Interop-Profile": "something-else"}
    assert post(client, raw("rev1-smoke.json"), wrong_profile).status_code == 422
    assert (
        post(client, raw("rev1-smoke.json"), {**TENANT_A, "Content-Type": "text/plain"}).status_code
        == 415
    )


def test_int_011_original_payload_round_trips_byte_for_byte(client: TestClient) -> None:
    original = raw("conflicting-location.json")
    receipt_id = post(client, original).json()["receiptId"]
    returned = client.get(f"/v1/interop/receipts/{receipt_id}/payload", headers=TENANT_A)
    assert returned.content == original
    receipt = client.get(f"/v1/interop/receipts/{receipt_id}", headers=TENANT_A).json()
    import hashlib

    assert receipt["payload_digest"] == "sha256:" + hashlib.sha256(original).hexdigest()


def test_int_012_mapping_output_is_versioned_and_regression_checked() -> None:
    mapping = map_eido(json.loads(raw("unknown-optional-field.json")))
    current = {
        "adapter_version": ADAPTER_VERSION,
        "notes": [{"note_id": n.note_id, "text": n.text} for n in mapping.notes],
        "fields": [f.model_dump(mode="json") for f in mapping.fields],
    }
    expected = json.loads(GOLDEN.read_text("utf-8"))
    assert current == expected, (
        "Adapter output changed. If intended, bump ADAPTER_VERSION, review the diff and "
        "regenerate the golden file."
    )


def test_malformed_json_is_quarantined_with_its_bytes(client: TestClient) -> None:
    response = post(client, b"{not json")
    assert response.status_code == 422
    assert response.json()["status"] == "quarantined_invalid"

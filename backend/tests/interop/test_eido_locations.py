"""EIDO locations (PIDF-LO) become supplied locations, kept apart from the narrative."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ntip.api import create_app
from ntip.api.auth import Principal, Role
from ntip.api.settings import Settings
from ntip.evaluation.runner import REPO_ROOT
from ntip.interop.eido.fetch import SchemaUnavailable, load_documents
from ntip.interop.eido.profile import PROFILE
from ntip.parser.locations import normalise_street
from ntip.parser.parser import parse
from ntip.schema.base import CivicAddress
from ntip.schema.source import SourceEvent, SuppliedLocation
from ntip.store import InMemoryEventStore

FIXTURES = REPO_ROOT / "data" / "interop" / "eido"
INTEROP = {"Authorization": "Bearer token-a", "X-Interop-Profile": PROFILE.profile_id,
           "Content-Type": "application/json"}  # fmt: skip
VIEWER = {"Authorization": "Bearer viewer-a"}


@pytest.fixture(scope="module", autouse=True)
def schema() -> None:
    try:
        load_documents()
    except SchemaUnavailable as err:
        pytest.skip(f"pinned EIDO schema unavailable: {err}")


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        interop_tokens={"token-a": "tenant-a"},
        api_tokens={"viewer-a": Principal("vera", Role.VIEWER, tenant_id="tenant-a")},
        auth_disabled=False,
    )
    return TestClient(create_app(store=InMemoryEventStore(), settings=settings))


def submit(client: TestClient, name: str) -> Any:
    response = client.post(
        "/v1/interop/eido/ingest", content=(FIXTURES / name).read_bytes(), headers=INTEROP
    )
    assert response.status_code == 202, response.text
    return response.json()


def detail(client: TestClient, incident_id: str) -> Any:
    return client.get(f"/v1/incidents/{incident_id}", headers=VIEWER).json()


def test_supplied_civic_address_is_a_device_provided_location(client: TestClient) -> None:
    body = submit(client, "pidf-civic.json")
    view = detail(client, body["incidentId"])
    supplied = [loc for loc in view["incident"]["locations"] if loc["role"] == "device_provided"]
    [location] = supplied
    assert location["civic_address"]["house_number"] == "123"
    assert location["civic_address"]["street"] == "Main St"
    assert location["supplied_by"]["origin"] == "/locationComponent/0/locationByValue"
    assert location["validation"] == "unverified"  # supplied is not validated
    # "Main St" (PIDF-LO) and "Main Street" (narrative) are the same street.
    assert view["incident"]["conflicts"] == []
    receipt = client.get(f"/v1/interop/receipts/{body['receiptId']}", headers=INTEROP).json()
    mapped = {m["source_pointer"]: m for m in receipt["mapping"]}
    assert mapped["/locationComponent/0/locationByValue"]["status"] == "mapped"


def test_a_location_only_revision_still_reaches_the_incident(client: TestClient) -> None:
    first = submit(client, "pidf-civic.json")
    second = submit(client, "pidf-civic-rev2.json")
    assert second["status"] == "accepted_for_advisory_processing"
    assert second["incidentId"] == first["incidentId"]
    view = detail(client, first["incidentId"])
    numbers = {
        loc["civic_address"]["house_number"]
        for loc in view["incident"]["locations"]
        if loc["role"] == "device_provided"
    }
    assert numbers == {"123", "125"}
    # The moved location now disagrees with the earlier one: verification is required.
    assert view["assessment"]["location_quality"]["status"] == "conflicting"


def test_disagreeing_locations_keep_urgency_and_unreadable_ones_are_explained(
    client: TestClient,
) -> None:
    body = submit(client, "pidf-mixed.json")
    view = detail(client, body["incidentId"])
    assert view["assessment"]["advisory_priority"] == "P0"  # not breathing, whatever the address
    assert view["assessment"]["location_quality"]["status"] == "conflicting"
    circle = next(loc for loc in view["incident"]["locations"] if loc["coordinates"])
    assert circle["coordinates"]["uncertainty_m"] == 50
    assert circle["raw_text"] == "Device location"

    receipt = client.get(f"/v1/interop/receipts/{body['receiptId']}", headers=INTEROP).json()
    notes = {m["source_pointer"]: (m["status"], m["note"]) for m in receipt["mapping"]}
    assert notes["/locationComponent/2/locationByReferenceUrl"] == (
        "preserved_unmapped",
        "references are never dereferenced",
    )
    status, note = notes["/locationComponent/3/locationByValue"]
    assert status == "preserved_unmapped" and "DOCTYPE" in note


def test_parser_turns_supplied_locations_into_candidates() -> None:
    from datetime import UTC, datetime

    source = SourceEvent.from_text(
        source_event_id="evt_1",
        incident_id="inc_1",
        received_at=datetime(2026, 11, 10, tzinfo=UTC),
        text="Smoke at 4 Elm Ave.",
        source_type="eido_import",
        supplied_locations=[
            SuppliedLocation(
                origin="/locationComponent/0/locationByValue",
                civic_address=CivicAddress(house_number="4", street="Elm Avenue", locality="X"),
            )
        ],
    )
    incident = parse([source], derived_at=source.received_at)
    roles = sorted(loc.role for loc in incident.locations)
    assert roles == ["device_provided", "reported"]
    supplied = next(loc for loc in incident.locations if loc.role == "device_provided")
    assert supplied.missing_fields == ["region"]
    assert supplied.supplied_by is not None and supplied.supplied_by.source_event_id == "evt_1"
    assert incident.conflicts == []  # "Elm Ave" and "Elm Avenue" agree


@pytest.mark.parametrize(
    ("street", "normal"),
    [("Main St", "main street"), ("Main St.", "main street"), ("main   street", "main street"),
     ("Old Mill Rd", "old mill road"), ("St Paul Way", "st paul way")],
)  # fmt: skip
def test_normalise_street(street: str, normal: str) -> None:
    assert normalise_street(street) == normal

"""Location level L3: addresses checked against a NENA-format reference layer."""

from pathlib import Path

import pytest

from ntip.evaluation.runner import REPO_ROOT
from ntip.location.reference import InvalidReference, MatchStatus, ReferenceLayer
from ntip.pipeline import Pipeline
from ntip.replay import replay_incident
from ntip.schema.base import CivicAddress
from ntip.store import InMemoryEventStore

LAYER_PATH = REPO_ROOT / "data" / "gis" / "synthetic-ssap-1.0.0.csv"


@pytest.fixture(scope="module")
def layer() -> ReferenceLayer:
    return ReferenceLayer.load(LAYER_PATH)


@pytest.mark.parametrize(
    ("address", "status"),
    [
        (CivicAddress(house_number="14", street="Elm Street"), MatchStatus.VALIDATED),
        (CivicAddress(house_number="14", street="Elm St."), MatchStatus.VALIDATED),
        # 12 Oak Street exists in Springfield and in Riverton.
        (CivicAddress(house_number="12", street="Oak Street"), MatchStatus.AMBIGUOUS),
        (CivicAddress(house_number="12", street="Oak Street", locality="Riverton"),
         MatchStatus.VALIDATED),
        (CivicAddress(house_number="12", street="Oak Street", postal_code="62701"),
         MatchStatus.VALIDATED),
        (CivicAddress(house_number="999", street="Oak Street"), MatchStatus.NOT_FOUND),
        (CivicAddress(street="Oak Street"), MatchStatus.INCOMPLETE),
    ],
)  # fmt: skip
def test_matching(layer: ReferenceLayer, address: CivicAddress, status: MatchStatus) -> None:
    assert layer.match(address).status is status


def test_a_unique_match_makes_the_location_sufficient_without_changing_priority(
    layer: ReferenceLayer,
) -> None:
    text = "My father is not breathing at 14 Elm Street."
    plain = Pipeline(store=InMemoryEventStore()).ingest(text)
    store = InMemoryEventStore()
    checked = Pipeline(store=store, reference=layer).ingest(text)

    assert plain.assessment.location_quality.status == "requires_verification"
    assert checked.assessment.location_quality.status == "sufficient"
    assert checked.assessment.advisory_priority == plain.assessment.advisory_priority == "P0"

    assert checked.incident is not None
    [reported, geocoded] = checked.incident.locations
    assert reported.role == "reported" and reported.validation == "unverified"  # left as it was
    assert geocoded.role == "geocoded" and geocoded.validation == "reference_validated"
    assert geocoded.coordinates is not None
    assert geocoded.civic_address is not None and geocoded.civic_address.locality == "Springfield"
    assert geocoded.validation_source is not None
    assert geocoded.validation_source.startswith("synthetic-ssap-1.0.0@sha256:")
    assert geocoded.validation_source.endswith(":gis.synthetic.example")  # the point's NGUID

    # The stored, enriched incident still reproduces exactly under replay.
    case = replay_incident(store, checked.incident_id, candidate=None)
    assert case.reproducible is True


def test_an_ambiguous_address_still_needs_verifying(layer: ReferenceLayer) -> None:
    result = Pipeline(store=InMemoryEventStore(), reference=layer).ingest(
        "Smoke coming from the house at 12 Oak Street."
    )
    assert result.assessment.location_quality.status == "requires_verification"
    assert result.incident is not None
    assert all(loc.role != "geocoded" for loc in result.incident.locations)


def test_a_layer_without_the_required_nena_fields_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("NGUID,Add_Number,St_Name\nx,1,Oak\n", encoding="utf-8")
    with pytest.raises(InvalidReference, match="DiscrpAgID"):
        ReferenceLayer.load(path)


def test_the_committed_layer_is_synthetic(layer: ReferenceLayer) -> None:
    assert len(layer.points) > 100
    assert all(p.nguid.endswith(":gis.synthetic.example") for p in layer.points)

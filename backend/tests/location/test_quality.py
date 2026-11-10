from datetime import UTC, datetime

from ntip.location import assess_location
from ntip.parser.parser import parse
from ntip.schema.advisory import LocationQualityStatus
from ntip.schema.canonical import (
    CivicAddress,
    Extractor,
    ExtractorKind,
    Incident,
    LocationCandidate,
    LocationRole,
    LocationValidation,
)
from ntip.schema.source import SourceEvent

AT = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def parse_text(*texts: str) -> Incident:
    sources = [
        SourceEvent.from_text(
            source_event_id=f"evt_{i}", incident_id="inc_1", received_at=AT, text=text
        )
        for i, text in enumerate(texts, 1)
    ]
    return parse(sources, derived_at=AT)


def test_no_location_is_missing() -> None:
    quality = assess_location(parse_text("I don't know where I am, my wife is not breathing."))
    assert quality.status is LocationQualityStatus.MISSING
    assert quality.missing_fields == ["location"]


def test_parsed_address_requires_verification_and_lists_gaps() -> None:
    quality = assess_location(parse_text("We are at 12 Oak Street, apartment 4B."))
    assert quality.status is LocationQualityStatus.REQUIRES_VERIFICATION
    assert quality.missing_fields == ["locality", "region"]


def test_most_complete_candidate_is_reported() -> None:
    quality = assess_location(parse_text("Near the park. Actually it's 12 Oak Street."))
    assert "house_number" not in quality.missing_fields


def test_conflicting_addresses() -> None:
    incident = parse_text("I'm at 123 Main Street.", "Sorry, I mean 321 Main Street.")
    quality = assess_location(incident)
    assert quality.status is LocationQualityStatus.CONFLICTING
    assert quality.conflicting_location_ids == ["loc_1", "loc_2"]


def test_operator_verified_complete_location_is_sufficient() -> None:
    incident = parse_text("Smoke on the second floor.")
    verified = LocationCandidate(
        location_id="loc_v",
        role=LocationRole.DEVICE_PROVIDED,
        civic_address=CivicAddress(
            house_number="12", street="Oak Street", locality="Springfield", region="IL"
        ),
        extractor=Extractor(kind=ExtractorKind.OPERATOR, extractor_id="op_7", version="n/a"),
        validation=LocationValidation.OPERATOR_VERIFIED,
        validation_source="caller callback",
    )
    quality = assess_location(incident.model_copy(update={"locations": [verified]}))
    assert quality.status is LocationQualityStatus.SUFFICIENT

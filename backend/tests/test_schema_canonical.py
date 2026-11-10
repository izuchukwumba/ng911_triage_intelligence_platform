from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ntip.schema.base import Fact, FactStatus, SourceSpan
from ntip.schema.canonical import (
    Classification,
    Conflict,
    ConflictKind,
    Coordinates,
    Evidence,
    Extractor,
    ExtractorKind,
    Incident,
    IncidentDomain,
    LocationCandidate,
    LocationRole,
    LocationValidation,
    Observation,
    Polarity,
    provenance_errors,
)
from ntip.schema.source import SourceEvent

RULES = Extractor(kind=ExtractorKind.RULE, extractor_id="rules", version="1.0.0")
MODEL = Extractor(kind=ExtractorKind.MODEL, extractor_id="extractor", version="0.1.0")


def evidence(source: SourceEvent, phrase: str) -> Evidence:
    start = source.text.index(phrase)
    return Evidence(
        source_event_id=source.source_event_id,
        span=SourceSpan(start=start, end=start + len(phrase)),
        text=phrase,
    )


def observation(source: SourceEvent, **overrides: Any) -> Observation:
    fields: dict[str, Any] = {
        "observation_id": "obs_1",
        "code": "NOT_BREATHING_REPORTED",
        "polarity": Polarity.AFFIRMED,
        "evidence": evidence(source, "not breathing"),
        "extractor": RULES,
    }
    return Observation(**{**fields, **overrides})


def reported_location(source: SourceEvent, **overrides: Any) -> LocationCandidate:
    fields: dict[str, Any] = {
        "location_id": "loc_1",
        "role": LocationRole.REPORTED,
        "raw_text": "apartment 4B at 12 Oak Street",
        "evidence": evidence(source, "apartment 4B at 12 Oak Street"),
        "extractor": RULES,
    }
    return LocationCandidate(**{**fields, **overrides})


def incident(source: SourceEvent, **overrides: Any) -> Incident:
    fields: dict[str, Any] = {
        "incident_id": source.incident_id,
        "source_event_ids": [source.source_event_id],
        "derived_at": datetime(2026, 11, 9, 12, 0, 1, tzinfo=UTC),
        "classification": Classification(domain=IncidentDomain.EMS),
        "observations": [observation(source)],
        "locations": [reported_location(source)],
    }
    return Incident(**{**fields, **overrides})


class TestIncident:
    def test_valid_incident_has_grounded_provenance(self, source_event: SourceEvent) -> None:
        record = incident(source_event)
        assert provenance_errors(record, {source_event.source_event_id: source_event}) == []

    def test_victim_count_defaults_to_not_reported_rather_than_zero(
        self, source_event: SourceEvent
    ) -> None:
        assert incident(source_event).victim_count.status is FactStatus.NOT_REPORTED
        assert incident(source_event).victim_count.value is None

    def test_classification_starts_provisional(self, source_event: SourceEvent) -> None:
        assert incident(source_event).classification.status == "provisional"

    def test_rejects_evidence_from_an_unlisted_source_event(
        self, source_event: SourceEvent
    ) -> None:
        with pytest.raises(ValidationError, match="unknown source event"):
            incident(source_event, source_event_ids=["evt_other"])

    def test_rejects_duplicate_observation_ids(self, source_event: SourceEvent) -> None:
        obs = observation(source_event)
        with pytest.raises(ValidationError, match="duplicate observation_id"):
            incident(source_event, observations=[obs, obs])

    def test_round_trips_through_json(self, source_event: SourceEvent) -> None:
        record = incident(source_event)
        assert Incident.model_validate_json(record.model_dump_json()) == record


class TestProvenance:
    def test_flags_a_quote_that_does_not_match_the_source(self, source_event: SourceEvent) -> None:
        fabricated = Evidence(
            source_event_id=source_event.source_event_id,
            span=SourceSpan(start=0, end=13),
            text="not breathing",  # the span actually covers "My father is "
        )
        record = incident(
            source_event, observations=[observation(source_event, evidence=fabricated)]
        )

        [error] = provenance_errors(record, {source_event.source_event_id: source_event})
        assert "not 'not breathing'" in error

    def test_flags_a_span_outside_the_source(self, source_event: SourceEvent) -> None:
        outside = Evidence(
            source_event_id=source_event.source_event_id,
            span=SourceSpan(start=500, end=510),
            text="x",
        )
        record = incident(source_event, observations=[observation(source_event, evidence=outside)])

        [error] = provenance_errors(record, {source_event.source_event_id: source_event})
        assert "outside" in error

    def test_flags_a_missing_source_event(self, source_event: SourceEvent) -> None:
        errors = provenance_errors(incident(source_event), {})
        # one for the observation, one for the reported location
        assert len(errors) == 2
        assert all("not provided" in error for error in errors)


class TestLocationCandidate:
    def test_reported_location_must_quote_evidence(self, source_event: SourceEvent) -> None:
        with pytest.raises(ValidationError, match="must quote its evidence"):
            reported_location(source_event, evidence=None)

    def test_reported_location_cannot_carry_coordinates(self, source_event: SourceEvent) -> None:
        with pytest.raises(ValidationError, match="cannot carry coordinates"):
            reported_location(source_event, coordinates=Coordinates(lat=40.7, lng=-74.0))

    def test_validated_status_requires_a_validation_source(self, source_event: SourceEvent) -> None:
        with pytest.raises(ValidationError, match="requires a validation_source"):
            reported_location(source_event, validation=LocationValidation.OPERATOR_VERIFIED)

    def test_a_model_cannot_validate_a_location(self, source_event: SourceEvent) -> None:
        with pytest.raises(ValidationError, match="model cannot mark"):
            reported_location(
                source_event,
                extractor=MODEL,
                validation=LocationValidation.REFERENCE_VALIDATED,
                validation_source="gis-fixture-v1",
            )

    def test_geocoded_location_may_carry_coordinates_without_evidence(self) -> None:
        candidate = LocationCandidate(
            location_id="loc_geo",
            role=LocationRole.GEOCODED,
            coordinates=Coordinates(lat=40.7, lng=-74.0, uncertainty_m=50),
            extractor=RULES,
        )
        assert candidate.validation is LocationValidation.UNVERIFIED


class TestConflicts:
    def test_keeps_contradicting_observations_side_by_side(self, source_event: SourceEvent) -> None:
        affirmed = observation(source_event)
        negated = observation(source_event, observation_id="obs_2", polarity=Polarity.NEGATED)
        conflict = Conflict(
            conflict_id="conf_1",
            kind=ConflictKind.OBSERVATION_POLARITY,
            code="NOT_BREATHING_REPORTED",
            observation_ids=["obs_1", "obs_2"],
        )
        record = incident(source_event, observations=[affirmed, negated], conflicts=[conflict])
        assert record.conflicts == [conflict]

    def test_conflict_needs_two_distinct_items(self) -> None:
        with pytest.raises(ValidationError, match="at least two items"):
            Conflict(
                conflict_id="conf_1",
                kind=ConflictKind.LOCATION_MISMATCH,
                location_ids=["loc_1", "loc_1"],
            )

    def test_conflict_must_cite_existing_facts(self, source_event: SourceEvent) -> None:
        conflict = Conflict(
            conflict_id="conf_1",
            kind=ConflictKind.LOCATION_MISMATCH,
            location_ids=["loc_1", "loc_missing"],
        )
        with pytest.raises(ValidationError, match="unknown location"):
            incident(source_event, conflicts=[conflict])


class TestVictimCountEvidence:
    def test_count_evidence_is_checked_against_the_source(self, source_event: SourceEvent) -> None:
        quote = evidence(source_event, "My father")
        count = Fact[int](status=FactStatus.REPORTED, value=1, evidence=[quote])
        record = incident(source_event, victim_count=count)

        assert list(record.evidence())[-1] == quote
        assert provenance_errors(record, {source_event.source_event_id: source_event}) == []

    def test_count_evidence_must_cite_an_incident_source(self, source_event: SourceEvent) -> None:
        foreign = Evidence(source_event_id="evt_other", span=SourceSpan(start=0, end=2), text="My")
        count = Fact[int](status=FactStatus.REPORTED, value=2, evidence=[foreign])
        with pytest.raises(ValidationError, match="unknown source event"):
            incident(source_event, victim_count=count)

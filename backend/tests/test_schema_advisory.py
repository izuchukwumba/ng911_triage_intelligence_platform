from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ntip.schema.advisory import (
    AdvisoryPriority,
    Assessment,
    AssessmentStatus,
    LocationQuality,
    LocationQualityStatus,
    ReviewAction,
    RuleFiring,
    SeverityBand,
    assessment_reference_errors,
)
from ntip.schema.base import SourceSpan
from ntip.schema.canonical import (
    Classification,
    Evidence,
    Extractor,
    ExtractorKind,
    Incident,
    IncidentDomain,
    Observation,
    Polarity,
)

ENGINE = Extractor(kind=ExtractorKind.RULE, extractor_id="triage", version="1.0.0")
SUFFICIENT = LocationQuality(status=LocationQualityStatus.SUFFICIENT)
MISSING = LocationQuality(status=LocationQualityStatus.MISSING, missing_fields=["street"])


def assessment(**overrides: Any) -> Assessment:
    fields: dict[str, Any] = {
        "assessment_id": "assess_1",
        "incident_id": "inc_001",
        "assessed_at": datetime(2026, 11, 9, 12, 0, 2, tzinfo=UTC),
        "assessor": ENGINE,
        "ruleset_version": "1.0.0",
        "status": AssessmentStatus.COMPLETED,
        "severity_band": SeverityBand.STANDARD,
        "location_quality": SUFFICIENT,
        "advisory_priority": AdvisoryPriority.P3,
        "review_actions": [],
        "requires_human_review": False,
    }
    return Assessment(**{**fields, **overrides})


def failed(**overrides: Any) -> Assessment:
    fields: dict[str, Any] = {
        "status": AssessmentStatus.PROCESSING_FAILED,
        "failure_reason": "parser timeout",
        "severity_band": SeverityBand.UNDETERMINED,
        "advisory_priority": None,
        "review_actions": [ReviewAction.URGENT_HUMAN_REVIEW],
        "requires_human_review": True,
    }
    return assessment(**{**fields, **overrides})


class TestSeparationOfConcerns:
    def test_critical_severity_with_missing_location_stays_critical(self) -> None:
        # Location quality adds a verification step; it does not change severity
        # or priority (design v1.2, ADR-004).
        result = assessment(
            severity_band=SeverityBand.CRITICAL,
            advisory_priority=AdvisoryPriority.P0,
            location_quality=MISSING,
            review_actions=[ReviewAction.CONFIRM_CRITICAL_REPORT, ReviewAction.VERIFY_LOCATION],
            requires_human_review=True,
        )
        assert result.severity_band is SeverityBand.CRITICAL
        assert result.advisory_priority is AdvisoryPriority.P0

    def test_insufficient_location_requires_verify_location(self) -> None:
        with pytest.raises(ValidationError, match="requires VERIFY_LOCATION"):
            assessment(location_quality=MISSING)

    def test_critical_severity_requires_confirmation(self) -> None:
        with pytest.raises(ValidationError, match="requires CONFIRM_CRITICAL_REPORT"):
            assessment(severity_band=SeverityBand.CRITICAL, advisory_priority=AdvisoryPriority.P0)


class TestFailureNeverBecomesLowPriority:
    def test_valid_failed_assessment(self) -> None:
        result = failed()
        assert result.advisory_priority is None
        assert result.requires_human_review is True

    def test_failed_assessment_cannot_assign_a_priority(self) -> None:
        with pytest.raises(ValidationError, match="must not assign a priority"):
            failed(advisory_priority=AdvisoryPriority.P4)

    def test_failed_assessment_cannot_claim_a_severity(self) -> None:
        with pytest.raises(ValidationError, match="severity undetermined"):
            failed(severity_band=SeverityBand.LOW)

    def test_failed_assessment_requires_urgent_review(self) -> None:
        with pytest.raises(ValidationError, match="requires URGENT_HUMAN_REVIEW"):
            failed(review_actions=[ReviewAction.CONFIRM_CLASSIFICATION])

    def test_failed_assessment_must_explain_itself(self) -> None:
        with pytest.raises(ValidationError, match="failure_reason"):
            failed(failure_reason=None)

    def test_completed_assessment_must_assign_a_priority(self) -> None:
        with pytest.raises(ValidationError, match="must assign a priority"):
            assessment(advisory_priority=None)


class TestReviewFlag:
    def test_flag_must_match_actions(self) -> None:
        with pytest.raises(ValidationError, match="requires_human_review"):
            assessment(review_actions=[ReviewAction.CONFIRM_CLASSIFICATION])
        with pytest.raises(ValidationError, match="requires_human_review"):
            assessment(requires_human_review=True)

    def test_actions_must_not_repeat(self) -> None:
        with pytest.raises(ValidationError, match="must not repeat"):
            assessment(
                review_actions=[ReviewAction.CONFIRM_CLASSIFICATION] * 2,
                requires_human_review=True,
            )


class TestReferences:
    @pytest.fixture
    def incident(self) -> Incident:
        return Incident(
            incident_id="inc_001",
            source_event_ids=["evt_001"],
            derived_at=datetime(2026, 11, 9, 12, 0, 1, tzinfo=UTC),
            classification=Classification(domain=IncidentDomain.EMS),
            observations=[
                Observation(
                    observation_id="obs_1",
                    code="NOT_BREATHING_REPORTED",
                    polarity=Polarity.AFFIRMED,
                    evidence=Evidence(
                        source_event_id="evt_001",
                        span=SourceSpan(start=13, end=26),
                        text="not breathing",
                    ),
                    extractor=ENGINE,
                )
            ],
        )

    def test_accepts_references_to_existing_facts(self, incident: Incident) -> None:
        firing = RuleFiring(
            rule_id="R-RESP-001",
            rule_version="1.0.0",
            reason_code="NOT_BREATHING_REPORTED",
            observation_ids=["obs_1"],
        )
        assert assessment_reference_errors(assessment(reasons=[firing]), incident) == []

    def test_flags_unknown_facts_and_wrong_incident(self, incident: Incident) -> None:
        firing = RuleFiring(
            rule_id="R-RESP-001",
            rule_version="1.0.0",
            reason_code="NOT_BREATHING_REPORTED",
            observation_ids=["obs_missing"],
            location_ids=["loc_missing"],
        )
        errors = assessment_reference_errors(
            assessment(incident_id="inc_other", reasons=[firing]), incident
        )
        assert len(errors) == 3

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ntip.schema.advisory import AdvisoryPriority
from ntip.schema.canonical import Classification, ClassificationStatus, IncidentDomain
from ntip.schema.review import HumanReview, ReviewDecision


def review(**overrides: Any) -> HumanReview:
    fields: dict[str, Any] = {
        "review_id": "rev_1",
        "incident_id": "inc_001",
        "assessment_id": "assess_1",
        "reviewer_id": "operator_7",
        "reviewed_at": datetime(2026, 11, 9, 12, 1, tzinfo=UTC),
        "decision": ReviewDecision.CONFIRM,
    }
    return HumanReview(**{**fields, **overrides})


def test_confirmation_needs_no_reason() -> None:
    assert review().reason is None


def test_override_records_the_new_priority_and_why() -> None:
    result = review(
        decision=ReviewDecision.OVERRIDE_PRIORITY,
        override_priority=AdvisoryPriority.P0,
        reason="Caller confirmed second patient is unresponsive",
    )
    assert result.override_priority is AdvisoryPriority.P0


def test_override_without_a_reason_is_rejected() -> None:
    with pytest.raises(ValidationError, match="requires a reason"):
        review(decision=ReviewDecision.OVERRIDE_PRIORITY, override_priority=AdvisoryPriority.P0)


def test_override_without_a_priority_is_rejected() -> None:
    with pytest.raises(ValidationError, match="override_priority is required"):
        review(decision=ReviewDecision.OVERRIDE_PRIORITY, reason="looks worse")


def test_priority_only_accompanies_an_override() -> None:
    with pytest.raises(ValidationError, match="override_priority is required"):
        review(override_priority=AdvisoryPriority.P2)


def test_correction_carries_a_classification_and_reason() -> None:
    corrected = Classification(domain=IncidentDomain.FIRE, status=ClassificationStatus.CONFIRMED)
    result = review(
        decision=ReviewDecision.CORRECT_CLASSIFICATION,
        corrected_classification=corrected,
        reason="Smoke reported, not a medical call",
    )
    assert result.corrected_classification == corrected


def test_correction_without_a_classification_is_rejected() -> None:
    with pytest.raises(ValidationError, match="corrected_classification is required"):
        review(decision=ReviewDecision.CORRECT_CLASSIFICATION, reason="wrong domain")


def test_note_requires_text() -> None:
    with pytest.raises(ValidationError, match="note requires text"):
        review(decision=ReviewDecision.NOTE)

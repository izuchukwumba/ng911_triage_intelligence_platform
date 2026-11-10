"""Human decisions about an assessment.

A review never modifies the assessment it refers to. Confirmations,
corrections and overrides are recorded as their own objects, so the original
machine output stays available for audit and evaluation (design v1.2,
sections 4.1 and 7.5).
"""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ntip.schema.advisory import AdvisoryPriority
from ntip.schema.base import SCHEMA_VERSION, Identifier, SchemaModel, UtcDatetime
from ntip.schema.canonical import Classification


class ReviewDecision(StrEnum):
    CONFIRM = "confirm"
    CORRECT_CLASSIFICATION = "correct_classification"
    OVERRIDE_PRIORITY = "override_priority"
    ESCALATE = "escalate"
    NOTE = "note"
    # The operator has finished with the incident (design v1.2, 11.3). A new
    # message reopens it, because the new assessment has not been reviewed.
    CLOSE = "close"


class HumanReview(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    review_id: Identifier
    incident_id: Identifier
    assessment_id: Identifier
    reviewer_id: Identifier
    reviewed_at: UtcDatetime
    decision: ReviewDecision
    override_priority: AdvisoryPriority | None = None
    corrected_classification: Classification | None = None
    reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        is_override = self.decision is ReviewDecision.OVERRIDE_PRIORITY
        is_correction = self.decision is ReviewDecision.CORRECT_CLASSIFICATION

        if is_override != (self.override_priority is not None):
            raise ValueError("override_priority is required for, and only for, an override")
        if is_correction != (self.corrected_classification is not None):
            raise ValueError("corrected_classification is required for, and only for, a correction")
        # Changing the machine's output needs an explanation (design v1.2, 11.1).
        if (is_override or is_correction) and self.reason is None:
            raise ValueError(f"a {self.decision} requires a reason")
        if self.decision is ReviewDecision.NOTE and self.reason is None:
            raise ValueError("a note requires text in reason")
        return self

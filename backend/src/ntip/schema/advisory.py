"""Advisory layer: machine-generated, nonbinding assessments.

An assessment is stored next to the incident, never inside it, and is never
edited: a new ruleset or model produces a new assessment, and a human decision
is recorded as a separate review (design v1.2, ADR-INT-002 and ADR-005).

Four questions are answered independently and must not be folded into one
number (design v1.2, section 7.1):

- severity_band:      how serious are the reported conditions?
- location_quality:   can the incident be located?
- review_actions:     what does a human need to check?
- advisory_priority:  research queue ordering, with its reasons

In particular, location quality changes the *review actions*, never the
severity, and a processing failure can never come out as a low priority.
"""

from collections.abc import Iterable
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from ntip.schema.base import SCHEMA_VERSION, Identifier, ReasonCode, SchemaModel, UtcDatetime
from ntip.schema.canonical import Extractor, Incident


class SeverityBand(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    ELEVATED = "elevated"
    STANDARD = "standard"
    LOW = "low"
    UNDETERMINED = "undetermined"


class LocationQualityStatus(StrEnum):
    SUFFICIENT = "sufficient"
    REQUIRES_VERIFICATION = "requires_verification"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class LocationQuality(SchemaModel):
    status: LocationQualityStatus
    missing_fields: list[str] = Field(default_factory=list)
    conflicting_location_ids: list[Identifier] = Field(default_factory=list)


class ReviewAction(StrEnum):
    URGENT_HUMAN_REVIEW = "URGENT_HUMAN_REVIEW"
    CONFIRM_CRITICAL_REPORT = "CONFIRM_CRITICAL_REPORT"
    VERIFY_LOCATION = "VERIFY_LOCATION"
    CONFIRM_CLASSIFICATION = "CONFIRM_CLASSIFICATION"
    RESOLVE_CONFLICT = "RESOLVE_CONFLICT"


class AdvisoryPriority(StrEnum):
    """Project-defined research labels, not PSAP or dispatch-protocol codes."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class RuleFiring(SchemaModel):
    """One rule that contributed to the assessment, with the facts it used."""

    rule_id: Identifier
    rule_version: str = Field(min_length=1)
    reason_code: ReasonCode
    observation_ids: list[Identifier] = Field(default_factory=list)
    location_ids: list[Identifier] = Field(default_factory=list)


class AssessmentStatus(StrEnum):
    COMPLETED = "completed"
    PROCESSING_FAILED = "processing_failed"


class Assessment(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    assessment_id: Identifier
    incident_id: Identifier
    assessed_at: UtcDatetime
    assessor: Extractor
    ruleset_version: str = Field(min_length=1)
    status: AssessmentStatus
    failure_reason: str | None = None
    severity_band: SeverityBand
    location_quality: LocationQuality
    advisory_priority: AdvisoryPriority | None
    priority_scheme: Literal["research-v1"] = "research-v1"
    reasons: list[RuleFiring] = Field(default_factory=list)
    review_actions: list[ReviewAction] = Field(default_factory=list)
    requires_human_review: bool

    @model_validator(mode="after")
    def _check(self) -> Self:
        actions = set(self.review_actions)
        if len(actions) != len(self.review_actions):
            raise ValueError("review_actions must not repeat")

        if self.status is AssessmentStatus.PROCESSING_FAILED:
            # A failure is surfaced for urgent human attention; it is never
            # turned into a (low) priority.
            if self.failure_reason is None:
                raise ValueError("a failed assessment must give a failure_reason")
            if self.advisory_priority is not None:
                raise ValueError("a failed assessment must not assign a priority")
            if self.severity_band is not SeverityBand.UNDETERMINED:
                raise ValueError("a failed assessment must leave severity undetermined")
            if ReviewAction.URGENT_HUMAN_REVIEW not in actions:
                raise ValueError("a failed assessment requires URGENT_HUMAN_REVIEW")
        else:
            if self.failure_reason is not None:
                raise ValueError("only a failed assessment may give a failure_reason")
            if self.advisory_priority is None:
                raise ValueError("a completed assessment must assign a priority")

        if (
            self.location_quality.status is not LocationQualityStatus.SUFFICIENT
            and ReviewAction.VERIFY_LOCATION not in actions
        ):
            raise ValueError("insufficient location quality requires VERIFY_LOCATION")

        if (
            self.severity_band is SeverityBand.CRITICAL
            and ReviewAction.CONFIRM_CRITICAL_REPORT not in actions
        ):
            raise ValueError("a critical severity requires CONFIRM_CRITICAL_REPORT")

        if self.requires_human_review != bool(actions):
            raise ValueError("requires_human_review must be true exactly when actions are listed")
        return self


def assessment_reference_errors(assessment: Assessment, incident: Incident) -> list[str]:
    """Check that an assessment only cites facts that exist in its incident."""
    errors: list[str] = []
    if assessment.incident_id != incident.incident_id:
        errors.append(f"assessment is for {assessment.incident_id!r}, not {incident.incident_id!r}")
    observation_ids = {o.observation_id for o in incident.observations}
    location_ids = {loc.location_id for loc in incident.locations}
    for firing in assessment.reasons:
        errors.extend(_missing(firing, "observation", firing.observation_ids, observation_ids))
        errors.extend(_missing(firing, "location", firing.location_ids, location_ids))
    errors.extend(
        _missing_conflicts(assessment.location_quality.conflicting_location_ids, location_ids)
    )
    return errors


def _missing(firing: RuleFiring, kind: str, cited: Iterable[str], known: set[str]) -> list[str]:
    return [
        f"rule {firing.rule_id!r} cites unknown {kind} {ref!r}" for ref in cited if ref not in known
    ]


def _missing_conflicts(cited: Iterable[str], known: set[str]) -> list[str]:
    return [f"location_quality cites unknown location {ref!r}" for ref in cited if ref not in known]

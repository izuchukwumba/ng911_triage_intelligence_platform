"""Request and response bodies for the /v1 API.

Responses embed the versioned schema objects (Incident, Assessment,
HumanReview, AuditEvent) unchanged, so API consumers see exactly what is
stored.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ntip.pipeline import IncidentState, IncidentView, IngestResult
from ntip.schema.advisory import AdvisoryPriority, Assessment, ReviewAction, SeverityBand
from ntip.schema.audit import AuditEvent
from ntip.schema.canonical import Classification, Incident
from ntip.schema.review import HumanReview, ReviewDecision
from ntip.schema.source import MAX_TRANSCRIPT_CHARS, SourceEvent, SourceType
from ntip.store import IncidentSummary


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Out(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class MessageIn(_Body):
    text: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
    # The research prototype accepts synthetic data only (design v1.2, ADR-006).
    synthetic: Literal[True]
    source_type: SourceType = SourceType.SYNTHETIC_TRANSCRIPT


class IngestOut(_Out):
    status: Literal["accepted"] = "accepted"
    incident_id: str
    source_event_id: str
    assessment_id: str
    processing_status: str
    advisory_priority: AdvisoryPriority | None
    idempotent_replay: bool

    @classmethod
    def of(cls, result: IngestResult) -> "IngestOut":
        return cls(
            incident_id=result.incident_id,
            source_event_id=result.source_event_id,
            assessment_id=result.assessment.assessment_id,
            processing_status=result.assessment.status,
            advisory_priority=result.assessment.advisory_priority,
            idempotent_replay=result.idempotent_replay,
        )


class IncidentSummaryOut(_Out):
    incident_id: str
    first_received_at: datetime
    assessment_id: str | None
    processing_status: str | None
    severity_band: SeverityBand | None
    advisory_priority: AdvisoryPriority | None
    review_actions: list[ReviewAction]

    @classmethod
    def of(cls, summary: IncidentSummary) -> "IncidentSummaryOut":
        a = summary.latest_assessment
        return cls(
            incident_id=summary.incident_id,
            first_received_at=summary.first_received_at,
            assessment_id=a.assessment_id if a else None,
            processing_status=a.status if a else None,
            severity_band=a.severity_band if a else None,
            advisory_priority=a.advisory_priority if a else None,
            review_actions=a.review_actions if a else [],
        )


class IncidentPage(_Out):
    total: int
    limit: int
    offset: int
    items: list[IncidentSummaryOut]


class IncidentDetail(_Out):
    incident_id: str
    state: IncidentState
    effective_priority: AdvisoryPriority | None
    sources: list[SourceEvent]
    incident: Incident | None
    assessment: Assessment
    reviews: list[HumanReview]

    @classmethod
    def of(cls, view: IncidentView) -> "IncidentDetail":
        return cls(
            incident_id=view.incident_id,
            state=view.state,
            effective_priority=view.effective_priority,  # type: ignore[arg-type]
            sources=view.sources,
            incident=view.incident,
            assessment=view.assessment,
            reviews=view.reviews,
        )


class AuditTrail(_Out):
    incident_id: str
    events: list[AuditEvent]


class ReviewIn(_Body):
    assessment_id: str
    reviewer_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    decision: ReviewDecision
    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    override_priority: AdvisoryPriority | None = None
    corrected_classification: Classification | None = None

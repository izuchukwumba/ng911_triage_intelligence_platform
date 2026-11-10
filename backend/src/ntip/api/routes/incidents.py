"""/v1 incident endpoints (design v1.2, section 5.2)."""

from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from ntip.api.errors import correlation_id
from ntip.api.models import (
    AuditTrail,
    IncidentDetail,
    IncidentPage,
    IncidentSummaryOut,
    IngestOut,
    MessageIn,
    ReviewIn,
)
from ntip.pipeline import Pipeline
from ntip.schema.advisory import Assessment
from ntip.schema.review import HumanReview
from ntip.store import UnknownIncident

router = APIRouter(prefix="/v1", tags=["incidents"])

IdempotencyKey = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
]


def _pipeline(request: Request) -> Pipeline:
    pipeline: Pipeline = request.app.state.pipeline
    return pipeline


def _accepted(response: Response, result: IngestOut) -> IngestOut:
    if result.idempotent_replay:
        response.headers["Idempotent-Replayed"] = "true"
    return result


@router.post("/incidents", status_code=status.HTTP_202_ACCEPTED)
def create_incident(
    body: MessageIn, request: Request, response: Response, idempotency_key: IdempotencyKey = None
) -> IngestOut:
    """Open an incident from a first synthetic message."""
    result = _pipeline(request).ingest(
        body.text,
        source_type=body.source_type,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id(request),
    )
    return _accepted(response, IngestOut.of(result))


@router.post("/incidents/{incident_id}/messages", status_code=status.HTTP_202_ACCEPTED)
def add_message(
    incident_id: str,
    body: MessageIn,
    request: Request,
    response: Response,
    idempotency_key: IdempotencyKey = None,
) -> IngestOut:
    """Add a follow-up message; the whole conversation is re-assessed."""
    result = _pipeline(request).ingest(
        body.text,
        incident_id=incident_id,
        source_type=body.source_type,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id(request),
    )
    return _accepted(response, IngestOut.of(result))


@router.get("/incidents")
def list_incidents(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentPage:
    total, page = _pipeline(request).store.list_incidents(limit=limit, offset=offset)
    return IncidentPage(
        total=total, limit=limit, offset=offset, items=[IncidentSummaryOut.of(s) for s in page]
    )


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, request: Request) -> IncidentDetail:
    return IncidentDetail.of(_pipeline(request).view(incident_id))


@router.get("/incidents/{incident_id}/events")
def get_events(incident_id: str, request: Request) -> AuditTrail:
    store = _pipeline(request).store
    events = store.audit_events(incident_id)
    if not events:
        raise UnknownIncident(incident_id)
    return AuditTrail(incident_id=incident_id, events=events)


@router.post("/incidents/{incident_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(incident_id: str, body: ReviewIn, request: Request) -> HumanReview:
    """Record a confirmation, correction, override, escalation or note."""
    try:
        return _pipeline(request).review(
            incident_id,
            assessment_id=body.assessment_id,
            reviewer_id=body.reviewer_id,
            decision=body.decision,
            reason=body.reason,
            override_priority=body.override_priority,
            corrected_classification=(
                body.corrected_classification.model_dump()
                if body.corrected_classification
                else None
            ),
            correlation_id=correlation_id(request),
        )
    except ValidationError as err:
        # Cross-field rules (e.g. an override needs a reason) live on HumanReview.
        raise RequestValidationError(err.errors()) from None


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, request: Request) -> Assessment:
    assessment = _pipeline(request).store.assessment(assessment_id)
    if assessment is None:
        raise UnknownIncident(assessment_id)
    return assessment

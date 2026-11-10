"""/v1 incident endpoints (design v1.2, section 5.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from ntip.api.auth import Permission, Principal, acting_as, require
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
from ntip.ml.contract import ModelOutput
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


def _own(request: Request, incident_id: str, principal: Principal) -> Pipeline:
    """The pipeline, once the incident is known to belong to the caller's tenant."""
    pipeline = _pipeline(request)
    pipeline.check_tenant(incident_id, principal.tenant_id)
    return pipeline


def _accepted(response: Response, result: IngestOut) -> IngestOut:
    if result.idempotent_replay:
        response.headers["Idempotent-Replayed"] = "true"
    return result


@router.post(
    "/incidents",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_incident(
    body: MessageIn,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require(Permission.INGEST))],
    idempotency_key: IdempotencyKey = None,
) -> IngestOut:
    """Open an incident from a first synthetic message, in the caller's tenant."""
    result = _pipeline(request).ingest(
        body.text,
        tenant_id=principal.tenant_id,
        source_type=body.source_type,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id(request),
    )
    return _accepted(response, IngestOut.of(result))


@router.post(
    "/incidents/{incident_id}/messages",
    status_code=status.HTTP_202_ACCEPTED,
)
def add_message(
    incident_id: str,
    body: MessageIn,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require(Permission.INGEST))],
    idempotency_key: IdempotencyKey = None,
) -> IngestOut:
    """Add a follow-up message; the whole conversation is re-assessed."""
    result = _pipeline(request).ingest(
        body.text,
        tenant_id=principal.tenant_id,
        incident_id=incident_id,
        source_type=body.source_type,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id(request),
    )
    return _accepted(response, IngestOut.of(result))


@router.get("/incidents")
def list_incidents(
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentPage:
    """The caller's tenant's incidents, newest first."""
    total, page = _pipeline(request).store.list_incidents(
        limit=limit, offset=offset, tenant_id=principal.tenant_id
    )
    return IncidentPage(
        total=total, limit=limit, offset=offset, items=[IncidentSummaryOut.of(s) for s in page]
    )


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
) -> IncidentDetail:
    pipeline = _own(request, incident_id, principal)
    return IncidentDetail.of(pipeline.view(incident_id))


@router.get("/incidents/{incident_id}/events")
def get_events(
    incident_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
) -> AuditTrail:
    store = _own(request, incident_id, principal).store
    return AuditTrail(incident_id=incident_id, events=store.audit_events(incident_id))


@router.get("/incidents/{incident_id}/model-outputs")
def get_model_outputs(
    incident_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
) -> list[ModelOutput]:
    """Exact model requests and responses recorded for this incident (design 3A.9)."""
    return _own(request, incident_id, principal).store.model_outputs(incident_id)


@router.post("/incidents/{incident_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(
    incident_id: str,
    body: ReviewIn,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.REVIEW))],
) -> HumanReview:
    """Record a confirmation, correction, override, escalation or note."""
    pipeline = _own(request, incident_id, principal)
    try:
        return pipeline.review(
            incident_id,
            assessment_id=body.assessment_id,
            # With authentication on, the reviewer is whoever the token belongs to.
            reviewer_id=acting_as(principal, body.reviewer_id, "reviewer_id"),
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


@router.get("/assessments/{assessment_id}", dependencies=[Depends(require(Permission.READ))])
def get_assessment(assessment_id: str, request: Request) -> Assessment:
    assessment = _pipeline(request).store.assessment(assessment_id)
    if assessment is None:
        raise UnknownIncident(assessment_id)
    return assessment

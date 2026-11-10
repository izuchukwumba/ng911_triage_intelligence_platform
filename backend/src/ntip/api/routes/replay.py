"""/v1 replay and ruleset endpoints (design v1.2, sections 5.2 and 10)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from ntip.api.auth import Permission, Principal, acting_as, require
from ntip.api.errors import correlation_id
from ntip.pipeline import Pipeline
from ntip.replay import run_replay
from ntip.schema.replay import ReplayRun
from ntip.store import UnknownIncident
from ntip.triage.ruleset import DEFAULT_RULESET, RELEASED

router = APIRouter(prefix="/v1", tags=["replay"])


class ReplayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Omit to replay every stored incident.
    incident_ids: list[str] | None = Field(default=None, max_length=1000)
    # A released ruleset to compare against; omit for a reproducibility check only.
    candidate_ruleset: str | None = None
    # Ignored when authentication is on: the requester is the token's principal.
    requested_by: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"
    )


class RulesetOut(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    name: str
    digest: str
    default: bool


def _pipeline(request: Request) -> Pipeline:
    pipeline: Pipeline = request.app.state.pipeline
    return pipeline


@router.post("/replay-runs", status_code=status.HTTP_201_CREATED)
def create_replay_run(
    body: ReplayIn,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.REPLAY))],
) -> ReplayRun:
    """Re-assess stored incidents. Nothing stored is modified."""
    pipeline = _pipeline(request)
    return run_replay(
        pipeline.store,
        incident_ids=body.incident_ids,
        candidate_ruleset=body.candidate_ruleset,
        requested_by=acting_as(principal, body.requested_by, "requested_by"),
        clock=pipeline.clock,
        new_id=pipeline.new_id,
        correlation_id=correlation_id(request),
        tenant_id=principal.tenant_id,
    )


@router.get("/replay-runs")
def list_replay_runs(
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ReplayRun]:
    """The caller's tenant's replay runs, newest first."""
    return _pipeline(request).store.replay_runs(limit=limit, tenant_id=principal.tenant_id)


@router.get("/replay-runs/{run_id}")
def get_replay_run(
    run_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require(Permission.READ))],
) -> ReplayRun:
    run = _pipeline(request).store.replay_run(run_id)
    if run is None or run.tenant_id != principal.tenant_id:
        raise UnknownIncident(run_id)
    return run


@router.get("/rulesets", dependencies=[Depends(require(Permission.READ))])
def list_rulesets() -> list[RulesetOut]:
    """Released rulesets and their pinned digests."""
    return [
        RulesetOut(name=name, digest=digest, default=name == DEFAULT_RULESET)
        for name, digest in RELEASED.items()
    ]

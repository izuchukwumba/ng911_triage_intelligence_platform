"""Liveness and readiness probes (design v1.2, section 5.2)."""

from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from ntip import __version__

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    # One entry per dependency the backend needs (event store, later the
    # model service).
    checks: dict[str, bool]


@router.get("/live")
def live() -> LiveResponse:
    """The process is running and can serve requests."""
    return LiveResponse(status="ok", version=__version__)


@router.get("/ready")
def ready(request: Request, response: Response) -> ReadyResponse:
    """Every dependency the backend needs is reachable (503 otherwise)."""
    checks = {"event_store": request.app.state.pipeline.store.ping()}
    ok = all(checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="ready" if ok else "not_ready", checks=checks)

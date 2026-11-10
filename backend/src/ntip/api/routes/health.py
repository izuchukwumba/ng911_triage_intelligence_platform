"""Liveness and readiness probes (design v1.2, section 5.2)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ntip import __version__

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    # One entry per dependency (database, model service, ...). Empty until the
    # backend has dependencies to check.
    checks: dict[str, bool]


@router.get("/live")
def live() -> LiveResponse:
    """The process is running and can serve requests."""
    return LiveResponse(status="ok", version=__version__)


@router.get("/ready")
def ready() -> ReadyResponse:
    """Every dependency the backend needs is reachable."""
    checks: dict[str, bool] = {}
    status: Literal["ready", "not_ready"] = "ready" if all(checks.values()) else "not_ready"
    return ReadyResponse(status=status, checks=checks)

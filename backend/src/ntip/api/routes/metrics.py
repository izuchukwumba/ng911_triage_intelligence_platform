"""Prometheus metrics (design v1.2, section 13.3)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from ntip import __version__
from ntip.api.auth import Permission, require
from ntip.observability import Metrics
from ntip.parser.parser import PARSER_VERSION
from ntip.schema.base import SCHEMA_VERSION
from ntip.triage.engine import ENGINE_VERSION
from ntip.triage.ruleset import DEFAULT_RULESET

router = APIRouter(tags=["health"])


def create_metrics() -> Metrics:
    metrics = Metrics()
    metrics.info(
        "ntip_build_info",
        "Versions of this process; mode is always simulation.",
        {"version": __version__, "schema": SCHEMA_VERSION, "parser": PARSER_VERSION,
         "engine": ENGINE_VERSION, "ruleset": DEFAULT_RULESET, "mode": "simulation"},
    )  # fmt: skip
    metrics.counter("ntip_http_requests_total", "HTTP requests by method, route and status.")
    metrics.histogram("ntip_http_request_duration_seconds", "HTTP request latency by route.")
    metrics.counter(
        "ntip_assessments_total",
        "Assessments by status (completed, processing_failed) and model status.",
    )
    metrics.counter("ntip_interop_receipts_total", "EIDO import receipts by status.")
    return metrics


@router.get(
    "/metrics",
    dependencies=[Depends(require(Permission.READ))],
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}}},
)
def get_metrics(request: Request) -> PlainTextResponse:
    """Process metrics in the Prometheus text format (scrape with a viewer token)."""
    metrics: Metrics = request.app.state.metrics
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

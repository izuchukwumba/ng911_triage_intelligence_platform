"""Correlation ids and structured, leak-free error responses (design v1.2, 5.3).

Every response carries ``X-Correlation-ID`` (taken from the request or
generated). Errors are returned as ``{"error": {"code", "message",
"correlation_id"}}`` and never include stack traces or transcript text.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ntip.api.auth import Forbidden, Unauthenticated
from ntip.api.ratelimit import RateLimiter, client_key
from ntip.observability import Metrics, correlation
from ntip.pipeline import IdempotencyConflict
from ntip.replay import UnknownRuleset
from ntip.store import UnknownIncident

log = logging.getLogger(__name__)

HEADER = "X-Correlation-ID"
MODE_HEADER = "X-NTIP-Mode"


def correlation_id(request: Request) -> str:
    return str(request.state.correlation_id)


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    cid = correlation_id(request)
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "correlation_id": cid}},
        headers={HEADER: cid},
    )


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def _rate_limit(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        limiter: RateLimiter = request.app.state.rate_limiter
        if limiter.enabled and not request.url.path.startswith("/health"):
            key = client_key(
                request.headers.get("authorization"),
                request.client.host if request.client else None,
            )
            retry_after = limiter.check(key)
            if retry_after is not None:
                # _correlate wraps this middleware, so the correlation id is set.
                response = _error(request, 429, "rate_limited", "Too many requests; retry later.")
                response.headers["Retry-After"] = str(max(1, round(retry_after)))
                return response
        return await call_next(request)

    @app.middleware("http")
    async def _correlate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get(HEADER, "")
        valid = 0 < len(supplied) <= 128 and supplied.replace("-", "").replace("_", "").isalnum()
        request.state.correlation_id = supplied if valid else f"req_{uuid.uuid4().hex}"
        token = correlation.set(request.state.correlation_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                log.exception("unhandled error", extra={"event": "unhandled_error"})
                response = _error(request, 500, "internal_error", "Internal error.")
            response.headers[HEADER] = request.state.correlation_id
            response.headers[MODE_HEADER] = request.app.state.deployment_mode
            _record(request, response.status_code, time.perf_counter() - started)
            return response
        finally:
            correlation.reset(token)

    def _record(request: Request, status: int, elapsed_s: float) -> None:
        # The route template ("/v1/incidents/{incident_id}"), never the raw
        # path, so identifiers and query strings stay out of metrics and logs.
        route = getattr(request.scope.get("route"), "path", "unmatched")
        metrics: Metrics = request.app.state.metrics
        metrics.inc("ntip_http_requests_total", method=request.method, route=route,
                    status=str(status))  # fmt: skip
        metrics.observe("ntip_http_request_duration_seconds", elapsed_s, route=route)
        if not route.startswith("/health"):
            log.info("request", extra={"event": "request", "method": request.method,
                     "route": route, "status": status,
                     "duration_ms": round(elapsed_s * 1000, 1)})  # fmt: skip

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field locations and messages only; never echo the submitted values.
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return _error(request, 422, "invalid_request", problems)

    @app.exception_handler(UnknownIncident)
    async def _unknown(request: Request, exc: UnknownIncident) -> JSONResponse:
        return _error(request, 404, "not_found", "Incident, assessment or replay run not found.")

    @app.exception_handler(Unauthenticated)
    async def _unauthenticated(request: Request, exc: Unauthenticated) -> JSONResponse:
        response = _error(request, 401, "unauthorized", "Missing or invalid credentials.")
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(Forbidden)
    async def _forbidden(request: Request, exc: Forbidden) -> JSONResponse:
        return _error(request, 403, "forbidden", f"This role may not {exc.permission}.")

    @app.exception_handler(UnknownRuleset)
    async def _ruleset(request: Request, exc: UnknownRuleset) -> JSONResponse:
        return _error(request, 422, "unknown_ruleset", f"No released ruleset named {exc}.")

    @app.exception_handler(IdempotencyConflict)
    async def _conflict(request: Request, exc: IdempotencyConflict) -> JSONResponse:
        return _error(
            request,
            409,
            "idempotency_conflict",
            "This Idempotency-Key was already used with a different request body.",
        )

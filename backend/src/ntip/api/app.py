"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ntip import __version__
from ntip.api import errors
from ntip.api.ratelimit import RateLimiter
from ntip.api.routes import health, incidents, interop, replay
from ntip.api.settings import Settings
from ntip.interop.gateway import EidoGateway
from ntip.pipeline import Pipeline
from ntip.store import EventStore


def create_app(store: EventStore | None = None, settings: Settings | None = None) -> FastAPI:
    """Build the API application.

    A factory (rather than a module-level app) keeps tests isolated: each test
    can build a fresh app with its own store.
    """
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="NG911 Triage Intelligence Platform (research)",
        version=__version__,
        description=(
            "SIMULATION ONLY — not for live dispatch. Advisory, human-in-the-loop "
            "research API over synthetic data."
        ),
    )
    app.state.pipeline = Pipeline(
        store=store or settings.build_store(),
        inference_mode=settings.inference_mode,
        extractor=settings.build_extractor(),
    )
    app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
    app.state.api_tokens = settings.api_tokens
    app.state.auth_disabled = settings.auth_disabled
    app.state.eido_gateway = EidoGateway(app.state.pipeline)
    app.state.interop_tokens = settings.interop_tokens
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", errors.HEADER],
        expose_headers=[errors.HEADER, "Idempotent-Replayed"],
    )
    errors.install(app)
    app.include_router(health.router)
    app.include_router(incidents.router)
    app.include_router(replay.router)
    app.include_router(interop.router)
    return app

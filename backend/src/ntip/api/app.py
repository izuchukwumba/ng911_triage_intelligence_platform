"""FastAPI application factory."""

from fastapi import FastAPI

from ntip import __version__
from ntip.api.routes import health


def create_app() -> FastAPI:
    """Build the API application.

    A factory (rather than a module-level app) keeps tests isolated: each test
    can build a fresh app with its own dependencies.
    """
    app = FastAPI(
        title="NG911 Triage Intelligence Platform (research)",
        version=__version__,
        description="Simulation and research use only — not for live dispatch.",
    )
    app.include_router(health.router)
    return app

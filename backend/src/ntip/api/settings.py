"""Runtime configuration from environment variables."""

import os
from dataclasses import dataclass, field

from ntip.store import EventStore, InMemoryEventStore


@dataclass(frozen=True)
class Settings:
    # PostgreSQL URL for the event store. Unset -> in-memory store (demo only).
    database_url: str | None = None
    # Browser origins allowed to call the API (the dashboard in development).
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("NTIP_CORS_ORIGINS")
        return cls(
            database_url=os.environ.get("NTIP_DATABASE_URL") or None,
            cors_origins=[o.strip() for o in origins.split(",")] if origins else cls().cors_origins,
        )

    def build_store(self) -> EventStore:
        if self.database_url is None:
            return InMemoryEventStore()
        from ntip.store.postgres import PostgresEventStore

        return PostgresEventStore(self.database_url)

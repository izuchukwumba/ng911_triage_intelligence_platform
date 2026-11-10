"""Runtime configuration from environment variables."""

import os
from dataclasses import dataclass, field

from ntip.api.auth import Principal, Role
from ntip.ml.extractors import HttpExtractor, ModelExtractor
from ntip.schema.canonical import InferenceMode
from ntip.store import EventStore, InMemoryEventStore


@dataclass(frozen=True)
class Settings:
    # PostgreSQL URL for the event store. Unset -> in-memory store (demo only).
    database_url: str | None = None
    # Browser origins allowed to call the API (the dashboard in development).
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
    # Model use (design v1.2, 3A.3). rules_only needs no inference service.
    inference_mode: InferenceMode = InferenceMode.RULES_ONLY
    inference_url: str | None = None
    inference_timeout_s: float = 2.0
    # Interop credentials, token -> tenant. Empty means interop is disabled.
    interop_tokens: dict[str, str] = field(default_factory=dict)
    # /v1 credentials, token -> principal. Constructed directly (tests, library
    # use), Settings has authentication off; from_env() never silently does.
    api_tokens: dict[str, Principal] = field(default_factory=dict)
    auth_disabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("NTIP_CORS_ORIGINS")
        api_tokens = _parse_api_tokens(os.environ.get("NTIP_API_TOKENS", ""))
        auth_disabled = os.environ.get("NTIP_AUTH_DISABLED") == "1"
        if not api_tokens and not auth_disabled:
            raise ConfigurationError(
                "Set NTIP_API_TOKENS (token:principal:role,...) or, for an isolated local "
                "demo only, NTIP_AUTH_DISABLED=1."
            )
        return cls(
            api_tokens=api_tokens,
            auth_disabled=auth_disabled and not api_tokens,
            database_url=os.environ.get("NTIP_DATABASE_URL") or None,
            cors_origins=[o.strip() for o in origins.split(",")] if origins else cls().cors_origins,
            inference_mode=InferenceMode(os.environ.get("NTIP_INFERENCE_MODE", "rules_only")),
            inference_url=os.environ.get("NTIP_INFERENCE_URL") or None,
            inference_timeout_s=float(os.environ.get("NTIP_INFERENCE_TIMEOUT_S", "2.0")),
            interop_tokens=_parse_tokens(os.environ.get("NTIP_INTEROP_TOKENS", "")),
        )

    def build_extractor(self) -> ModelExtractor | None:
        if self.inference_mode is InferenceMode.RULES_ONLY or self.inference_url is None:
            return None
        return HttpExtractor(self.inference_url, timeout_s=self.inference_timeout_s)

    def build_store(self) -> EventStore:
        if self.database_url is None:
            return InMemoryEventStore()
        from ntip.store.postgres import PostgresEventStore

        return PostgresEventStore(self.database_url)


def _parse_tokens(raw: str) -> dict[str, str]:
    """``token:tenant,token:tenant`` -> {token: tenant}."""
    pairs = (item.strip().split(":", 1) for item in raw.split(",") if ":" in item)
    return {token.strip(): tenant.strip() for token, tenant in pairs if token.strip()}


class ConfigurationError(RuntimeError):
    pass


def _parse_api_tokens(raw: str) -> dict[str, Principal]:
    """``token:principal:role,...`` -> {token: Principal}."""
    tokens: dict[str, Principal] = {}
    for item in raw.split(","):
        parts = [p.strip() for p in item.split(":")]
        if len(parts) != 3 or not all(parts):
            continue
        token, principal_id, role = parts
        try:
            tokens[token] = Principal(principal_id, Role(role))
        except ValueError:
            raise ConfigurationError(f"unknown role {role!r} in NTIP_API_TOKENS") from None
    return tokens

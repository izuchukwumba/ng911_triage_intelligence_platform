"""Primitives shared by every schema layer.

Every persisted object is immutable (``frozen``) and rejects unknown fields
(``extra="forbid"``): corrections are new objects, never in-place edits, and
unrecognised input is an error rather than something silently dropped.
"""

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.3.0"


class SchemaModel(BaseModel):
    # Serialised documents always contain defaulted fields, so the
    # serialization schema (used for API responses) marks them required.
    model_config = ConfigDict(
        frozen=True, extra="forbid", json_schema_serialization_defaults_required=True
    )


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
"""Timezone-aware timestamp, normalised to UTC. Naive datetimes are rejected."""

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]
"""Opaque, stable identifier."""

Sha256Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]

ReasonCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$")]
"""Stable machine-readable code, e.g. ``NOT_BREATHING_REPORTED``."""


def sha256_digest(data: str | bytes) -> str:
    """Digest in the ``sha256:<hex>`` form used throughout the schema."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


class SourceSpan(SchemaModel):
    """Half-open character range ``[start, end)`` into a source text."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def _non_empty(self) -> Self:
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")
        return self

    def slice(self, text: str) -> str:
        if self.end > len(text):
            raise ValueError(f"span [{self.start}, {self.end}) exceeds text length {len(text)}")
        return text[self.start : self.end]


class Evidence(SchemaModel):
    """A quoted stretch of a specific source event."""

    source_event_id: Identifier
    span: SourceSpan
    text: str = Field(min_length=1)


class FactStatus(StrEnum):
    """How much is known about a fact (design v1.2, sections 3B.4 and 4.3).

    ``unknown``, ``not_reported``, ``negated`` and ``not_applicable`` are
    distinct and must never be collapsed into ``false``.
    """

    REPORTED = "reported"  # stated in the source
    INFERRED = "inferred"  # derived by a rule or model, not stated
    CONFIRMED = "confirmed"  # verified by an operator
    UNKNOWN = "unknown"  # the question came up but the answer is not known
    NOT_REPORTED = "not_reported"  # the source does not address it
    NEGATED = "negated"  # the source explicitly denies it
    NOT_APPLICABLE = "not_applicable"
    CONFLICTING = "conflicting"  # the source contains incompatible values


_HAS_VALUE = {FactStatus.REPORTED, FactStatus.INFERRED, FactStatus.CONFIRMED}


class Fact[T](SchemaModel):
    """A value together with how it is known.

    ``value`` is present exactly when the status asserts one; a conflicting
    fact lists the competing ``candidates`` instead of choosing between them.
    """

    status: FactStatus
    value: T | None = None
    candidates: list[T] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _value_matches_status(self) -> Self:
        if self.status in _HAS_VALUE and self.value is None:
            raise ValueError(f"a {self.status} fact requires a value")
        if self.status not in _HAS_VALUE and self.value is not None:
            raise ValueError(f"a {self.status} fact must not carry a value")
        if self.status is FactStatus.CONFLICTING and len(self.candidates) < 2:
            raise ValueError("a conflicting fact requires at least two candidates")
        if self.status is not FactStatus.CONFLICTING and self.candidates:
            raise ValueError("only a conflicting fact may list candidates")
        return self

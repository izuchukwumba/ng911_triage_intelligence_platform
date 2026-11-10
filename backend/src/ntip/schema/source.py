"""Source layer: inputs exactly as they were received.

A source event is never modified. A caller who changes their address, or an
upstream system that sends a revision, produces a new source event; the
canonical incident is re-derived from the full sequence.
"""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ntip.schema.base import (
    SCHEMA_VERSION,
    Identifier,
    SchemaModel,
    Sha256Digest,
    UtcDatetime,
    sha256_digest,
)

MAX_TRANSCRIPT_CHARS = 20_000


class SourceType(StrEnum):
    SYNTHETIC_TRANSCRIPT = "synthetic_transcript"
    STRUCTURED_TEST_EVENT = "structured_test_event"


class SourceEvent(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    source_event_id: Identifier
    incident_id: Identifier
    received_at: UtcDatetime
    source_type: SourceType
    text: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
    # Research fixtures must declare their provenance (design v1.2, section 4.3).
    # Only synthetic data is accepted until a governed real-data path exists.
    synthetic: bool
    payload_digest: Sha256Digest
    # Revision lineage: the source event this one corrects or extends, if any.
    supersedes: Identifier | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not self.synthetic:
            raise ValueError("only synthetic source events are accepted in the research prototype")
        if self.payload_digest != sha256_digest(self.text):
            raise ValueError("payload_digest does not match text")
        if self.supersedes == self.source_event_id:
            raise ValueError("a source event cannot supersede itself")
        return self

    @classmethod
    def from_text(
        cls,
        *,
        source_event_id: str,
        incident_id: str,
        received_at: UtcDatetime,
        text: str,
        source_type: SourceType = SourceType.SYNTHETIC_TRANSCRIPT,
        supersedes: str | None = None,
    ) -> Self:
        """Build a synthetic source event, computing its digest."""
        return cls(
            source_event_id=source_event_id,
            incident_id=incident_id,
            received_at=received_at,
            source_type=source_type,
            text=text,
            synthetic=True,
            payload_digest=sha256_digest(text),
            supersedes=supersedes,
        )

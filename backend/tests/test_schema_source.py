from typing import Any

import pytest
from pydantic import ValidationError

from ntip.schema.base import sha256_digest
from ntip.schema.source import MAX_TRANSCRIPT_CHARS, SourceEvent


def _with(event: SourceEvent, **changes: Any) -> dict[str, Any]:
    return {**event.model_dump(), **changes}


def test_from_text_computes_the_digest(source_event: SourceEvent) -> None:
    assert source_event.payload_digest == sha256_digest(source_event.text)
    assert source_event.synthetic is True


def test_rejects_a_digest_that_does_not_match_the_text(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError, match="payload_digest does not match"):
        SourceEvent(**_with(source_event, text="Different text"))


def test_rejects_non_synthetic_input(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError, match="only synthetic"):
        SourceEvent(**_with(source_event, synthetic=False))


def test_rejects_oversized_transcripts(source_event: SourceEvent) -> None:
    text = "a" * (MAX_TRANSCRIPT_CHARS + 1)
    with pytest.raises(ValidationError):
        SourceEvent(**_with(source_event, text=text, payload_digest=sha256_digest(text)))


def test_rejects_unknown_fields(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError):
        SourceEvent(**_with(source_event, priority="P0"))


def test_cannot_supersede_itself(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError, match="supersede itself"):
        SourceEvent(**_with(source_event, supersedes=source_event.source_event_id))


def test_round_trips_through_json(source_event: SourceEvent) -> None:
    assert SourceEvent.model_validate_json(source_event.model_dump_json()) == source_event

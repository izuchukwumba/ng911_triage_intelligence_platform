from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from ntip.schema.audit import Actor, ActorKind, AuditEvent, AuditEventType
from ntip.schema.base import sha256_digest
from ntip.schema.source import SourceEvent


def event(source: SourceEvent, **overrides: Any) -> AuditEvent:
    fields: dict[str, Any] = {
        "event_id": "ae_1",
        "incident_id": source.incident_id,
        "occurred_at": datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        "event_type": AuditEventType.SOURCE_RECEIVED,
        "actor": Actor(kind=ActorKind.SERVICE, actor_id="ingestion"),
        "correlation_id": "req_1",
        "subject_id": source.source_event_id,
        "subject_digest": sha256_digest(source.model_dump_json()),
    }
    return AuditEvent(**{**fields, **overrides})


def test_event_types_use_dotted_names(source_event: SourceEvent) -> None:
    assert event(source_event).model_dump(mode="json")["event_type"] == "source.received"


def test_rejects_a_malformed_digest(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError):
        event(source_event, subject_digest="md5:abc")


def test_events_are_immutable(source_event: SourceEvent) -> None:
    with pytest.raises(ValidationError):
        event(source_event).event_type = AuditEventType.TRIAGE_OVERRIDDEN  # type: ignore[misc]

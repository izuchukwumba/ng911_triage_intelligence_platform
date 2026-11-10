from datetime import UTC, datetime

import pytest

from ntip.schema.source import SourceEvent

TRANSCRIPT = "My father is not breathing. We're in apartment 4B at 12 Oak Street."


@pytest.fixture
def source_event() -> SourceEvent:
    return SourceEvent.from_text(
        source_event_id="evt_001",
        incident_id="inc_001",
        received_at=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        text=TRANSCRIPT,
    )

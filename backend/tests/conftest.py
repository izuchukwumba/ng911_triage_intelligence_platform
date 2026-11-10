import os
from datetime import UTC, datetime

import pytest

from ntip.schema.source import SourceEvent

# Tests that build the app from the environment run as the local demo
# (authentication off); tests/api/test_auth.py covers authentication.
os.environ.setdefault("NTIP_AUTH_DISABLED", "1")

TRANSCRIPT = "My father is not breathing. We're in apartment 4B at 12 Oak Street."


@pytest.fixture
def source_event() -> SourceEvent:
    return SourceEvent.from_text(
        source_event_id="evt_001",
        incident_id="inc_001",
        received_at=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
        text=TRANSCRIPT,
    )

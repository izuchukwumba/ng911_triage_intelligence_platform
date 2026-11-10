import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
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


ADMIN_URL = os.environ.get("NTIP_TEST_DATABASE_URL")


@pytest.fixture
def postgres_url() -> Iterator[str]:
    """A fresh, empty PostgreSQL database for one test.

    Needs NTIP_TEST_DATABASE_URL pointing at a server where the user may create
    databases; otherwise the test is skipped (CI always sets it).
    """
    if not ADMIN_URL:
        pytest.skip("NTIP_TEST_DATABASE_URL not set")
    name = f"ntip_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield psycopg.conninfo.make_conninfo(ADMIN_URL, dbname=name)
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')

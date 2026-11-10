"""Store fixtures: every contract test runs against each implementation.

PostgreSQL tests need ``NTIP_TEST_DATABASE_URL`` pointing at a server where
the user may create databases; each test gets a fresh, migrated database.
Without it they are skipped (CI sets it).
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from ntip.store import EventStore, InMemoryEventStore
from ntip.store.migrate import upgrade
from ntip.store.postgres import PostgresEventStore

ADMIN_URL = os.environ.get("NTIP_TEST_DATABASE_URL")


def _with_database(url: str, name: str) -> str:
    return psycopg.conninfo.make_conninfo(url, dbname=name)


@pytest.fixture
def postgres_url() -> Iterator[str]:
    if not ADMIN_URL:
        pytest.skip("NTIP_TEST_DATABASE_URL not set")
    name = f"ntip_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield _with_database(ADMIN_URL, name)
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(params=["memory", "postgres"])
def store(request: pytest.FixtureRequest) -> EventStore:
    if request.param == "memory":
        return InMemoryEventStore()
    url = request.getfixturevalue("postgres_url")
    upgrade(url)
    return PostgresEventStore(url)

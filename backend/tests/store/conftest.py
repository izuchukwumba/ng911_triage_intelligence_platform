"""Store fixtures: every contract test runs against each implementation.

The ``postgres_url`` fixture lives in the root conftest.
"""

from collections.abc import Iterator

import psycopg
import pytest

from ntip.store import EventStore, InMemoryEventStore
from ntip.store.migrate import upgrade
from ntip.store.postgres import APP_ROLE, PostgresEventStore


@pytest.fixture
def app_role_url(postgres_url: str) -> str:
    """The migrated test database, with sessions acting as the restricted
    application role (as the API does in a deployment)."""
    upgrade(postgres_url)
    return psycopg.conninfo.make_conninfo(postgres_url, options=f"-c role={APP_ROLE}")


@pytest.fixture(params=["memory", "postgres", "postgres-app-role"])
def store(request: pytest.FixtureRequest) -> Iterator[EventStore]:
    if request.param == "memory":
        yield InMemoryEventStore()
        return
    if request.param == "postgres":
        url = request.getfixturevalue("postgres_url")
        upgrade(url)
    else:
        url = request.getfixturevalue("app_role_url")
    pg = PostgresEventStore(url)
    yield pg
    pg.close()

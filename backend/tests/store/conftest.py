"""Store fixtures: every contract test runs against each implementation.

The ``postgres_url`` fixture lives in the root conftest.
"""

from collections.abc import Iterator

import pytest

from ntip.store import EventStore, InMemoryEventStore
from ntip.store.migrate import upgrade
from ntip.store.postgres import PostgresEventStore


@pytest.fixture(params=["memory", "postgres"])
def store(request: pytest.FixtureRequest) -> Iterator[EventStore]:
    if request.param == "memory":
        yield InMemoryEventStore()
        return
    url = request.getfixturevalue("postgres_url")
    upgrade(url)
    pg = PostgresEventStore(url)
    yield pg
    pg.close()

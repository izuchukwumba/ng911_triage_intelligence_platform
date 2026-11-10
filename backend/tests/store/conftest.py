"""Store fixtures: every contract test runs against each implementation.

The ``postgres_url`` fixture lives in the root conftest.
"""

import pytest

from ntip.store import EventStore, InMemoryEventStore
from ntip.store.migrate import upgrade
from ntip.store.postgres import PostgresEventStore


@pytest.fixture(params=["memory", "postgres"])
def store(request: pytest.FixtureRequest) -> EventStore:
    if request.param == "memory":
        return InMemoryEventStore()
    url = request.getfixturevalue("postgres_url")
    upgrade(url)
    return PostgresEventStore(url)

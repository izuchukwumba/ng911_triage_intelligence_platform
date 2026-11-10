"""The PostgreSQL store reuses a bounded pool of connections."""

import time

import psycopg

from ntip.evaluation.load import run
from ntip.store.migrate import upgrade
from ntip.store.postgres import PostgresEventStore


def _connections(url: str) -> int:
    with psycopg.connect(url) as conn:
        row = conn.execute(
            "SELECT count(*) FROM pg_stat_activity"
            " WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ).fetchone()
    return row[0] if row else 0


def test_concurrent_load_stays_within_the_pool(postgres_url: str) -> None:
    upgrade(postgres_url)
    store = PostgresEventStore(postgres_url, pool_size=3)
    try:
        result = run(store, workers=12, incidents=10, follow_ups=2)
        assert (result["errors"], result["consistency_problems"]) == (0, 0)
        assert _connections(postgres_url) <= 3
    finally:
        store.close()
    assert _connections(postgres_url) == 0


def test_readiness_fails_fast_when_the_database_is_unreachable() -> None:
    store = PostgresEventStore("postgresql://ntip@127.0.0.1:1/ntip", pool_size=1)
    try:
        started = time.monotonic()
        assert store.ping() is False
        assert time.monotonic() - started < 10
    finally:
        store.close()

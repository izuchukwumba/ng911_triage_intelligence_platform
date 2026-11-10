"""Database-level guarantees that only the PostgreSQL store can give."""

import psycopg
import pytest

from ntip.store.migrate import applied, available, downgrade, upgrade

TABLES = [
    "source_events",
    "incident_versions",
    "assessments",
    "human_reviews",
    "audit_events",
    "idempotency_claims",
    "replay_runs",
    "model_outputs",
    "interop_receipts",
]


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("statement", ["UPDATE {t} SET payload = payload", "DELETE FROM {t}"])
def test_rows_cannot_be_updated_or_deleted(postgres_url: str, table: str, statement: str) -> None:
    upgrade(postgres_url)
    with psycopg.connect(postgres_url) as conn:
        # Row triggers only fire when a row matches, so insert one first.
        _insert_dummy(conn, table)
        with pytest.raises(psycopg.errors.InsufficientPrivilege, match="append-only"):
            conn.execute(statement.format(t=table))


@pytest.mark.parametrize("table", TABLES)
def test_tables_cannot_be_truncated(postgres_url: str, table: str) -> None:
    upgrade(postgres_url)
    with (
        psycopg.connect(postgres_url) as conn,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        conn.execute(f"TRUNCATE {table} CASCADE")


def test_migrations_are_reversible(postgres_url: str) -> None:
    assert upgrade(postgres_url) == available()
    assert upgrade(postgres_url) == []  # idempotent
    assert downgrade(postgres_url, "0000") == list(reversed(available()))
    with psycopg.connect(postgres_url) as conn:
        assert applied(conn) == []
    assert upgrade(postgres_url) == available()


def _insert_dummy(conn: psycopg.Connection, table: str) -> None:
    statements = {
        "source_events": "INSERT INTO source_events (source_event_id, incident_id, received_at,"
        " synthetic, payload, payload_digest) VALUES ('s', 'i', now(), true, '{}', 'd')",
        "incident_versions": "INSERT INTO incident_versions (incident_id, version, derived_at,"
        " schema_version, payload, payload_digest) VALUES ('i', 1, now(), '2', '{}', 'd')",
        "assessments": "INSERT INTO assessments (assessment_id, incident_id, assessed_at,"
        " ruleset_version, status, payload, payload_digest)"
        " VALUES ('a', 'i', now(), 'r', 'completed', '{}', 'd')",
        "audit_events": "INSERT INTO audit_events (event_id, incident_id, occurred_at, event_type,"
        " correlation_id, payload) VALUES ('e', 'i', now(), 't', 'c', '{}')",
        "interop_receipts": "INSERT INTO interop_receipts (receipt_id, tenant_id, received_at,"
        " status, payload, payload_digest) VALUES ('r', 't', now(), 's', '{}', 'd')",
        "model_outputs": "INSERT INTO model_outputs (output_id, incident_id, recorded_at, mode,"
        " payload, payload_digest) VALUES ('m', 'i', now(), 'ml_shadow', '{}', 'd')",
        "replay_runs": "INSERT INTO replay_runs (run_id, created_at, payload, payload_digest)"
        " VALUES ('r', now(), '{}', 'd')",
        "idempotency_claims": "INSERT INTO idempotency_claims (key, request_digest, incident_id,"
        " claimed_at, payload) VALUES ('k', 'sha256:x', 'i', now(), '{}')",
    }
    if table == "human_reviews":
        conn.execute(statements["assessments"])
        conn.execute(
            "INSERT INTO human_reviews (review_id, incident_id, assessment_id, reviewed_at,"
            " payload, payload_digest) VALUES ('r', 'i', 'a', now(), '{}', 'd')"
        )
    else:
        conn.execute(statements[table])

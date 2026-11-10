"""Lawful erasure: owner-only, complete, audited, and nothing else can delete."""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from ntip.interop.receipts import InteropReceipt, ReceiptStatus
from ntip.pipeline import Pipeline
from ntip.schema.base import sha256_digest
from ntip.schema.review import ReviewDecision
from ntip.store.migrate import upgrade
from ntip.store.postgres import PostgresEventStore
from ntip.store.retention import INCIDENT_TABLES, NothingSelected, erase

T0 = datetime(2026, 3, 1, 12, tzinfo=UTC)


def receipt(receipt_id: str, incident_id: str | None, at: datetime) -> InteropReceipt:
    return InteropReceipt(
        receipt_id=receipt_id, received_at=at, tenant_id="default", profile_id="p",
        adapter_version="a", schema_artifact_digest=sha256_digest("s"),
        status=ReceiptStatus.ACCEPTED if incident_id else ReceiptStatus.QUARANTINED,
        payload='{"$id": "x"}', payload_digest=sha256_digest('{"$id": "x"}'),
        incident_id=incident_id,
    )  # fmt: skip


@pytest.fixture
def world(postgres_url: str) -> tuple[str, str, str]:
    """Two incidents: an old one with a review, receipt and idempotency claim, and a new one."""
    upgrade(postgres_url)
    store = PostgresEventStore(postgres_url)
    now = T0
    pipeline = Pipeline(store=store, clock=lambda: now)
    old = pipeline.ingest("My father is not breathing at 12 Oak Street.", idempotency_key="k-1")
    pipeline.ingest("He is now awake.", incident_id=old.incident_id)
    pipeline.review(old.incident_id, assessment_id=old.assessment.assessment_id,
                    reviewer_id="op_1", decision=ReviewDecision.CONFIRM)  # fmt: skip
    store.append([receipt("rcpt_1", old.incident_id, T0),
                  receipt("rcpt_orphan", None, T0)])  # fmt: skip
    now = T0 + timedelta(days=40)
    new = pipeline.ingest("Smoke at 4 Cedar Court.")
    store.close()
    return postgres_url, old.incident_id, new.incident_id


def count(url: str, table: str, incident_id: str) -> int:
    column = "payload ->> 'incident_id'" if table == "interop_receipts" else "incident_id"
    with psycopg.connect(url) as conn:
        row = conn.execute(
            f"SELECT count(*) FROM {table} WHERE {column} = %s", (incident_id,)
        ).fetchone()
    return row[0] if row else 0


def test_a_dry_run_reports_and_changes_nothing(world: tuple[str, str, str]) -> None:
    url, old, _ = world
    report = erase(url, reason="test", requested_by="dpo_1", incident_ids=[old])
    [planned] = report.erasures
    assert not report.executed and planned.erasure_id is None
    assert planned.rows["source_events"] == 2 and planned.rows["interop_receipts"] == 1
    assert count(url, "source_events", old) == 2


def test_erasing_an_incident_removes_everything_and_leaves_a_tombstone(
    world: tuple[str, str, str],
) -> None:
    url, old, new = world
    report = erase(url, reason="erasure request 17", requested_by="dpo_1", incident_ids=[old],
                   execute=True)  # fmt: skip
    [done] = report.erasures
    for table in (*INCIDENT_TABLES, "interop_receipts"):
        assert count(url, table, old) == 0, table
    assert count(url, "source_events", new) == 1  # others untouched
    with psycopg.connect(url) as conn:
        tombstone = conn.execute(
            "SELECT scope, subject_id, requested_by, reason, rows_deleted FROM erasures"
        ).fetchone()
    assert tombstone == ("incident", old, "dpo_1", "erasure request 17", done.rows)
    store = PostgresEventStore(url)
    try:
        assert store.tenant_of(old) is None  # the API now answers 404
    finally:
        store.close()


def test_a_retention_period_selects_by_age_including_unlinked_receipts(
    world: tuple[str, str, str],
) -> None:
    url, old, new = world
    report = erase(
        url,
        reason="retention: 30 days",
        requested_by="dpo_1",
        older_than=timedelta(days=30),
        execute=True,
        now=T0 + timedelta(days=41),
    )
    assert [(e.scope, e.subject_id) for e in report.erasures] == [
        ("incident", old),
        ("receipt", "rcpt_orphan"),
    ]
    assert count(url, "source_events", new) == 1


def test_outside_erasure_the_store_stays_append_only(world: tuple[str, str, str]) -> None:
    url, old, _ = world
    erase(url, reason="test", requested_by="dpo_1", incident_ids=[old], execute=True)
    with psycopg.connect(url) as conn:
        for statement in ("DELETE FROM source_events", "UPDATE erasures SET reason = 'x'",
                          "DELETE FROM erasures"):  # fmt: skip
            with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
                conn.execute(statement)
        # The erasure setting never allows updates.
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("SELECT set_config('ntip.erasure_id', 'e', true)")
            conn.execute("UPDATE source_events SET payload = payload")


def test_the_application_role_cannot_erase(world: tuple[str, str, str]) -> None:
    url, old, _ = world
    app = psycopg.conninfo.make_conninfo(url, options="-c role=ntip_app")
    with psycopg.connect(app) as conn:
        assert conn.execute("SELECT count(*) FROM erasures").fetchone() == (0,)
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("SELECT set_config('ntip.erasure_id', 'e', true)")
            conn.execute("DELETE FROM source_events WHERE incident_id = %s", (old,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("INSERT INTO erasures VALUES ('e', 'incident', 'i', 't', now(), 'x',"
                         " 'y', '{}')")  # fmt: skip


def test_a_reason_and_a_selection_are_required(world: tuple[str, str, str]) -> None:
    url, old, _ = world
    with pytest.raises(ValueError, match="reason"):
        erase(url, reason=" ", requested_by="dpo_1", incident_ids=[old])
    with pytest.raises(NothingSelected):
        erase(url, reason="x", requested_by="dpo_1")

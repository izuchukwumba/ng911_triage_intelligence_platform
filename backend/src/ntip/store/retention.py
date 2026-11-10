"""Retention and lawful erasure (design v1.2, sections 9.3 and 13.2).

The event store is append-only for the application. This procedure is the one
sanctioned way to remove data: run by an operator with the table owner's
credentials, it erases selected incidents, everything derived from them and
the EIDO payloads they came from, and records a content-free tombstone for
each. Selection is by incident or by age (a retention period), optionally
within one tenant. Nothing is removed without ``--execute``.

    python -m ntip.store.retention OWNER_URL --reason "retention: 30 days" \\
        --requested-by dpo_1 --older-than-days 30 [--tenant psap-a] [--execute]
    python -m ntip.store.retention OWNER_URL --reason "erasure request 17" \\
        --requested-by dpo_1 --incident inc_123 --execute

Replay runs are kept: they hold identifiers, priorities and reason codes, no
transcript text or payloads.
"""

import argparse
import json
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

# Tables keyed by incident, children before parents.
INCIDENT_TABLES = (
    "idempotency_claims",
    "model_outputs",
    "human_reviews",
    "audit_events",
    "assessments",
    "incident_versions",
    "source_events",
)


class NothingSelected(ValueError):
    pass


@dataclass(frozen=True)
class Erasure:
    scope: str  # "incident" or "receipt"
    subject_id: str
    tenant_id: str
    rows: dict[str, int]
    erasure_id: str | None = None  # set once executed


@dataclass
class Report:
    executed: bool
    erasures: list[Erasure] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return sum(sum(e.rows.values()) for e in self.erasures)


def _selected_incidents(
    conn: psycopg.Connection[Any],
    incident_ids: Sequence[str] | None,
    cutoff: datetime | None,
    tenant_id: str | None,
) -> list[tuple[str, str]]:
    """(incident_id, tenant_id) of every selected incident."""
    rows = conn.execute(
        """
        SELECT incident_id, min(tenant_id) FROM source_events
        GROUP BY incident_id
        HAVING (%(ids)s::text[] IS NULL OR incident_id = ANY(%(ids)s))
           AND (%(cutoff)s::timestamptz IS NULL OR min(received_at) < %(cutoff)s)
           AND (%(tenant)s::text IS NULL OR min(tenant_id) = %(tenant)s)
        ORDER BY min(received_at)
        """,
        {"ids": list(incident_ids) if incident_ids else None, "cutoff": cutoff,
         "tenant": tenant_id},
    ).fetchall()  # fmt: skip
    return [(r[0], r[1]) for r in rows]


def _unlinked_receipts(
    conn: psycopg.Connection[Any], cutoff: datetime, tenant_id: str | None
) -> list[tuple[str, str]]:
    """Receipts past the retention period that never became an incident."""
    rows = conn.execute(
        "SELECT receipt_id, tenant_id FROM interop_receipts"
        " WHERE payload ->> 'incident_id' IS NULL AND received_at < %(cutoff)s"
        " AND (%(tenant)s::text IS NULL OR tenant_id = %(tenant)s) ORDER BY seq",
        {"cutoff": cutoff, "tenant": tenant_id},
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _count_or_delete(
    cur: psycopg.Cursor[Any], scope: str, subject: str, delete: bool
) -> dict[str, int]:
    targets: list[tuple[str, str]] = (
        [(t, "incident_id = %s") for t in INCIDENT_TABLES]
        + [("interop_receipts", "payload ->> 'incident_id' = %s")]
        if scope == "incident"
        else [("interop_receipts", "receipt_id = %s")]
    )
    rows: dict[str, int] = {}
    for table, condition in targets:
        if delete:
            cur.execute(f"DELETE FROM {table} WHERE {condition}", (subject,))
            rows[table] = cur.rowcount
        else:
            found = cur.execute(
                f"SELECT count(*) FROM {table} WHERE {condition}", (subject,)
            ).fetchone()
            rows[table] = found[0] if found else 0
    return {t: n for t, n in rows.items() if n}


def erase(
    owner_url: str,
    *,
    reason: str,
    requested_by: str,
    incident_ids: Sequence[str] | None = None,
    older_than: timedelta | None = None,
    tenant_id: str | None = None,
    execute: bool = False,
    now: datetime | None = None,
) -> Report:
    """Erase (or, without ``execute``, report what would be erased)."""
    if not reason.strip() or not requested_by.strip():
        raise ValueError("a reason and a requester are required")
    if not incident_ids and older_than is None:
        raise NothingSelected("select incidents by id or by age")
    now = now or datetime.now(UTC)
    cutoff = now - older_than if older_than is not None else None
    report = Report(executed=execute)
    with psycopg.connect(owner_url) as conn:
        subjects = [("incident", i, t) for i, t in
                    _selected_incidents(conn, incident_ids, cutoff, tenant_id)]  # fmt: skip
        if cutoff is not None and not incident_ids:
            subjects += [("receipt", r, t) for r, t in _unlinked_receipts(conn, cutoff, tenant_id)]
        conn.commit()
        for scope, subject, tenant in subjects:
            # One transaction per subject: the incident is locked against
            # concurrent writes (the same lock ingest takes), its rows are
            # deleted and the tombstone written, or nothing happens.
            with conn.transaction(), conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (subject,))
                if not execute:
                    rows = _count_or_delete(cur, scope, subject, delete=False)
                    report.erasures.append(Erasure(scope, subject, tenant, rows))
                    continue
                erasure_id = f"erasure_{uuid.uuid4().hex}"
                cur.execute("SELECT set_config('ntip.erasure_id', %s, true)", (erasure_id,))
                rows = _count_or_delete(cur, scope, subject, delete=True)
                cur.execute(
                    "INSERT INTO erasures (erasure_id, scope, subject_id, tenant_id, erased_at,"
                    " requested_by, reason, rows_deleted) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (erasure_id, scope, subject, tenant, now, requested_by, reason,
                     json.dumps(rows)),
                )  # fmt: skip
                report.erasures.append(Erasure(scope, subject, tenant, rows, erasure_id))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Erase incidents (retention or erasure request).")
    parser.add_argument("owner_url", help="database URL of the table owner (not ntip_app)")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--incident", action="append", dest="incidents")
    parser.add_argument("--older-than-days", type=int)
    parser.add_argument("--tenant")
    parser.add_argument("--execute", action="store_true", help="without it, only report")
    args = parser.parse_args(argv)
    report = erase(
        args.owner_url,
        reason=args.reason,
        requested_by=args.requested_by,
        incident_ids=args.incidents,
        older_than=timedelta(days=args.older_than_days) if args.older_than_days else None,
        tenant_id=args.tenant,
        execute=args.execute,
    )
    print(json.dumps({"executed": report.executed, "rows": report.rows,
                      "erasures": [asdict(e) for e in report.erasures]}, indent=2))  # fmt: skip
    if not report.executed:
        print("dry run: nothing was erased; add --execute to erase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""PostgreSQL event store. Run ``ntip.store.migrate`` before first use."""

from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from ntip.interop.receipts import InteropReceipt
from ntip.ml.contract import ModelOutput
from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
from ntip.schema.base import sha256_digest
from ntip.schema.canonical import Incident
from ntip.schema.replay import ReplayRun
from ntip.schema.review import HumanReview
from ntip.schema.source import SourceEvent
from ntip.store.base import (
    ConcurrentModification,
    DuplicateRecord,
    Expectation,
    IdempotencyClaim,
    IncidentSummary,
    Record,
)


def _doc(record: Record) -> tuple[Jsonb, str]:
    payload = record.model_dump(mode="json")
    return Jsonb(payload), sha256_digest(record.model_dump_json())


def _insert(cur: psycopg.Cursor[Any], record: Record) -> None:
    payload, digest = _doc(record)
    match record:
        case SourceEvent():
            cur.execute(
                "INSERT INTO source_events (source_event_id, incident_id, tenant_id, received_at,"
                " synthetic, payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (record.source_event_id, record.incident_id, record.tenant_id,
                 record.received_at, record.synthetic, payload, digest),
            )  # fmt: skip
        case Incident():
            cur.execute(
                "INSERT INTO incident_versions (incident_id, version, derived_at, schema_version,"
                " payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    record.incident_id,
                    len(record.source_event_ids),
                    record.derived_at,
                    record.schema_version,
                    payload,
                    digest,
                ),
            )
        case Assessment():
            cur.execute(
                "INSERT INTO assessments (assessment_id, incident_id, assessed_at, ruleset_version,"
                " status, payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (record.assessment_id, record.incident_id, record.assessed_at,
                 record.ruleset_version, record.status, payload, digest),
            )  # fmt: skip
        case HumanReview():
            cur.execute(
                "INSERT INTO human_reviews (review_id, incident_id, assessment_id, reviewed_at,"
                " payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s)",
                (record.review_id, record.incident_id, record.assessment_id, record.reviewed_at,
                 payload, digest),
            )  # fmt: skip
        case AuditEvent():
            cur.execute(
                "INSERT INTO audit_events (event_id, incident_id, occurred_at, event_type,"
                " correlation_id, payload) VALUES (%s, %s, %s, %s, %s, %s)",
                (record.event_id, record.incident_id, record.occurred_at, record.event_type,
                 record.correlation_id, payload),
            )  # fmt: skip
        case ReplayRun():
            cur.execute(
                "INSERT INTO replay_runs (run_id, tenant_id, created_at, candidate_ruleset,"
                " payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    record.run_id,
                    record.tenant_id,
                    record.created_at,
                    record.candidate_ruleset,
                    payload,
                    digest,
                ),
            )
        case InteropReceipt():
            cur.execute(
                "INSERT INTO interop_receipts (receipt_id, tenant_id, source_event_id, received_at,"
                " status, payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (record.receipt_id, record.tenant_id, record.source_event_id, record.received_at,
                 record.status, payload, digest),
            )  # fmt: skip
        case ModelOutput():
            cur.execute(
                "INSERT INTO model_outputs (output_id, incident_id, recorded_at, mode, payload,"
                " payload_digest) VALUES (%s, %s, %s, %s, %s, %s)",
                (record.output_id, record.incident_id, record.recorded_at, record.mode, payload,
                 digest),
            )  # fmt: skip
        case IdempotencyClaim():
            cur.execute(
                "INSERT INTO idempotency_claims (key, request_digest, incident_id, claimed_at,"
                " payload) VALUES (%s, %s, %s, %s, %s)",
                (record.key, record.request_digest, record.incident_id, record.claimed_at, payload),
            )


#: The restricted role the application should act as (migration 0006): it may
#: read and append to these tables, and nothing else.
APP_ROLE = "ntip_app"
EVENT_TABLES = (
    "source_events",
    "incident_versions",
    "assessments",
    "human_reviews",
    "audit_events",
    "idempotency_claims",
    "replay_runs",
    "model_outputs",
    "interop_receipts",
)

#: How long a readiness check waits for a connection before reporting not ready.
PING_TIMEOUT_S = 2.0


class PostgresEventStore:
    """Event store on PostgreSQL, over a pool of connections.

    Each operation borrows a connection for one transaction (committed on
    success, rolled back on error) and returns it to the pool, so requests do
    not pay for a new connection each time. Call ``close()`` when done.
    """

    def __init__(self, url: str, *, pool_size: int = 10) -> None:
        # The pool connects in the background: an unreachable database does not
        # stop the API from starting, it makes readiness checks fail instead.
        self._pool = ConnectionPool(
            url, min_size=1, max_size=pool_size, open=True, name="ntip-event-store"
        )

    def _connect(self, timeout: float | None = None) -> Any:
        return self._pool.connection(timeout=timeout)

    def close(self) -> None:
        self._pool.close()

    def append(self, records: Sequence[Record], *, expect: Expectation | None = None) -> None:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                if expect is not None:
                    # Serialise writers of one incident for the rest of this
                    # transaction, then check nobody added a message meanwhile.
                    cur.execute(
                        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                        (expect.incident_id,),
                    )
                    row = cur.execute(
                        "SELECT count(*) FROM source_events WHERE incident_id = %s",
                        (expect.incident_id,),
                    ).fetchone()
                    current = row[0] if row else 0
                    if current != expect.source_events:
                        raise ConcurrentModification(
                            f"{expect.incident_id}: {current} source events, "
                            f"expected {expect.source_events}"
                        )
                for record in records:
                    _insert(cur, record)
        except psycopg.errors.UniqueViolation as err:
            raise DuplicateRecord(str(err).splitlines()[0]) from None

    def _payloads(self, sql: str, params: tuple[Any, ...]) -> list[Any]:
        with self._connect() as conn:
            return [row[0] for row in conn.execute(sql, params)]

    def idempotency_claim(self, key: str) -> IdempotencyClaim | None:
        rows = self._payloads("SELECT payload FROM idempotency_claims WHERE key = %s", (key,))
        return IdempotencyClaim.model_validate(rows[0]) if rows else None

    def source_events(self, incident_id: str) -> list[SourceEvent]:
        rows = self._payloads(
            "SELECT payload FROM source_events WHERE incident_id = %s ORDER BY seq", (incident_id,)
        )
        return [SourceEvent.model_validate(r) for r in rows]

    def incident_versions(self, incident_id: str) -> list[Incident]:
        rows = self._payloads(
            "SELECT payload FROM incident_versions WHERE incident_id = %s ORDER BY seq",
            (incident_id,),
        )
        return [Incident.model_validate(r) for r in rows]

    def assessments(self, incident_id: str) -> list[Assessment]:
        rows = self._payloads(
            "SELECT payload FROM assessments WHERE incident_id = %s ORDER BY seq", (incident_id,)
        )
        return [Assessment.model_validate(r) for r in rows]

    def assessment(self, assessment_id: str) -> Assessment | None:
        rows = self._payloads(
            "SELECT payload FROM assessments WHERE assessment_id = %s", (assessment_id,)
        )
        return Assessment.model_validate(rows[0]) if rows else None

    def reviews(self, incident_id: str) -> list[HumanReview]:
        rows = self._payloads(
            "SELECT payload FROM human_reviews WHERE incident_id = %s ORDER BY seq", (incident_id,)
        )
        return [HumanReview.model_validate(r) for r in rows]

    def audit_events(self, incident_id: str) -> list[AuditEvent]:
        rows = self._payloads(
            "SELECT payload FROM audit_events WHERE incident_id = %s ORDER BY seq", (incident_id,)
        )
        return [AuditEvent.model_validate(r) for r in rows]

    def list_incidents(
        self, *, limit: int, offset: int, tenant_id: str | None = None
    ) -> tuple[int, list[IncidentSummary]]:
        # Every message of an incident has the same tenant.
        with self._connect() as conn:
            total_row = conn.execute(
                "SELECT count(DISTINCT incident_id) FROM source_events"
                " WHERE %(tenant)s::text IS NULL OR tenant_id = %(tenant)s",
                {"tenant": tenant_id},
            ).fetchone()
            rows = conn.execute(
                """
                SELECT s.incident_id, s.first_received_at, a.payload
                FROM (
                    SELECT incident_id, min(received_at) AS first_received_at, min(seq) AS seq
                    FROM source_events
                    WHERE %(tenant)s::text IS NULL OR tenant_id = %(tenant)s
                    GROUP BY incident_id
                ) s
                LEFT JOIN LATERAL (
                    SELECT payload FROM assessments
                    WHERE incident_id = s.incident_id ORDER BY seq DESC LIMIT 1
                ) a ON true
                ORDER BY s.first_received_at DESC, s.seq DESC
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                {"tenant": tenant_id, "limit": limit, "offset": offset},
            ).fetchall()
        page = [
            IncidentSummary(
                incident_id=incident_id,
                first_received_at=received,
                latest_assessment=Assessment.model_validate(payload) if payload else None,
            )
            for incident_id, received, payload in rows
        ]
        return (total_row[0] if total_row else 0), page

    def model_outputs(self, incident_id: str) -> list[ModelOutput]:
        rows = self._payloads(
            "SELECT payload FROM model_outputs WHERE incident_id = %s ORDER BY seq", (incident_id,)
        )
        return [ModelOutput.model_validate(r) for r in rows]

    def interop_receipt(self, receipt_id: str) -> InteropReceipt | None:
        rows = self._payloads(
            "SELECT payload FROM interop_receipts WHERE receipt_id = %s", (receipt_id,)
        )
        return InteropReceipt.model_validate(rows[0]) if rows else None

    def interop_receipts(self, tenant_id: str, source_event_id: str) -> list[InteropReceipt]:
        rows = self._payloads(
            "SELECT payload FROM interop_receipts WHERE tenant_id = %s AND source_event_id = %s"
            " ORDER BY seq",
            (tenant_id, source_event_id),
        )
        return [InteropReceipt.model_validate(r) for r in rows]

    def replay_run(self, run_id: str) -> ReplayRun | None:
        rows = self._payloads("SELECT payload FROM replay_runs WHERE run_id = %s", (run_id,))
        return ReplayRun.model_validate(rows[0]) if rows else None

    def tenant_of(self, incident_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT tenant_id FROM source_events WHERE incident_id = %s ORDER BY seq LIMIT 1",
                (incident_id,),
            ).fetchone()
        return row[0] if row else None

    def replay_runs(self, *, limit: int, tenant_id: str | None = None) -> list[ReplayRun]:
        rows = self._payloads(
            "SELECT payload FROM replay_runs WHERE %s::text IS NULL OR tenant_id = %s"
            " ORDER BY seq DESC LIMIT %s",
            (tenant_id, tenant_id, limit),
        )
        return [ReplayRun.model_validate(r) for r in rows]

    def ping(self) -> bool:
        try:
            with self._connect(timeout=PING_TIMEOUT_S) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

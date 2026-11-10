"""PostgreSQL event store. Run ``ntip.store.migrate`` before first use."""

from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from ntip.interop.receipts import InteropReceipt
from ntip.ml.contract import ModelOutput
from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
from ntip.schema.base import sha256_digest
from ntip.schema.canonical import Incident
from ntip.schema.replay import ReplayRun
from ntip.schema.review import HumanReview
from ntip.schema.source import SourceEvent
from ntip.store.base import DuplicateRecord, IdempotencyClaim, IncidentSummary, Record


def _doc(record: Record) -> tuple[Jsonb, str]:
    payload = record.model_dump(mode="json")
    return Jsonb(payload), sha256_digest(record.model_dump_json())


def _insert(cur: psycopg.Cursor[Any], record: Record) -> None:
    payload, digest = _doc(record)
    match record:
        case SourceEvent():
            cur.execute(
                "INSERT INTO source_events (source_event_id, incident_id, received_at, synthetic,"
                " payload, payload_digest) VALUES (%s, %s, %s, %s, %s, %s)",
                (record.source_event_id, record.incident_id, record.received_at,
                 record.synthetic, payload, digest),
            )  # fmt: skip
        case Incident():
            cur.execute(
                "INSERT INTO incident_versions (incident_id, derived_at, schema_version, payload,"
                " payload_digest) VALUES (%s, %s, %s, %s, %s)",
                (record.incident_id, record.derived_at, record.schema_version, payload, digest),
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
                "INSERT INTO replay_runs (run_id, created_at, candidate_ruleset, payload,"
                " payload_digest) VALUES (%s, %s, %s, %s, %s)",
                (record.run_id, record.created_at, record.candidate_ruleset, payload, digest),
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


class PostgresEventStore:
    def __init__(self, url: str) -> None:
        self._url = url

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def append(self, records: Sequence[Record]) -> None:
        try:
            with self._connect() as conn, conn.cursor() as cur:
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

    def list_incidents(self, *, limit: int, offset: int) -> tuple[int, list[IncidentSummary]]:
        with self._connect() as conn:
            total_row = conn.execute(
                "SELECT count(DISTINCT incident_id) FROM source_events"
            ).fetchone()
            rows = conn.execute(
                """
                SELECT s.incident_id, s.first_received_at, a.payload
                FROM (
                    SELECT incident_id, min(received_at) AS first_received_at, min(seq) AS seq
                    FROM source_events GROUP BY incident_id
                ) s
                LEFT JOIN LATERAL (
                    SELECT payload FROM assessments
                    WHERE incident_id = s.incident_id ORDER BY seq DESC LIMIT 1
                ) a ON true
                ORDER BY s.first_received_at DESC, s.seq DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
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

    def replay_runs(self, *, limit: int) -> list[ReplayRun]:
        rows = self._payloads(
            "SELECT payload FROM replay_runs ORDER BY seq DESC LIMIT %s", (limit,)
        )
        return [ReplayRun.model_validate(r) for r in rows]

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

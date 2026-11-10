"""In-process event store for tests and local demos. Not durable."""

import threading
from collections.abc import Sequence

from ntip.interop.receipts import InteropReceipt
from ntip.ml.contract import ModelOutput
from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
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


def _identity(record: Record) -> tuple[str, ...]:
    match record:
        case SourceEvent():
            return ("source", record.source_event_id)
        case Incident():
            # Version n is the interpretation of the first n source events.
            return ("incident", record.incident_id, str(len(record.source_event_ids)))
        case Assessment():
            return ("assessment", record.assessment_id)
        case HumanReview():
            return ("review", record.review_id)
        case AuditEvent():
            return ("audit", record.event_id)
        case IdempotencyClaim():
            return ("idempotency", record.key)
        case ReplayRun():
            return ("replay", record.run_id)
        case ModelOutput():
            return ("model_output", record.output_id)
        case InteropReceipt():
            return ("receipt", record.receipt_id)


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[Record] = []
        self._identities: set[tuple[str, ...]] = set()

    def append(self, records: Sequence[Record], *, expect: Expectation | None = None) -> None:
        with self._lock:
            if expect is not None:
                current = sum(
                    1
                    for r in self._records
                    if isinstance(r, SourceEvent) and r.incident_id == expect.incident_id
                )
                if current != expect.source_events:
                    raise ConcurrentModification(
                        f"{expect.incident_id}: {current} source events, "
                        f"expected {expect.source_events}"
                    )
            identities = [_identity(r) for r in records]
            clash = [i for i in identities if i in self._identities]
            if clash or len(set(identities)) != len(identities):
                raise DuplicateRecord(f"already stored: {clash or identities}")
            self._records.extend(records)
            self._identities.update(identities)

    def _of[T](self, kind: type[T], incident_id: str | None = None) -> list[T]:
        with self._lock:
            return [
                r
                for r in self._records
                if isinstance(r, kind)
                and (incident_id is None or getattr(r, "incident_id", None) == incident_id)
            ]

    def idempotency_claim(self, key: str) -> IdempotencyClaim | None:
        return next((c for c in self._of(IdempotencyClaim) if c.key == key), None)

    def source_events(self, incident_id: str) -> list[SourceEvent]:
        return self._of(SourceEvent, incident_id)

    def incident_versions(self, incident_id: str) -> list[Incident]:
        return self._of(Incident, incident_id)

    def assessments(self, incident_id: str) -> list[Assessment]:
        return self._of(Assessment, incident_id)

    def assessment(self, assessment_id: str) -> Assessment | None:
        return next((a for a in self._of(Assessment) if a.assessment_id == assessment_id), None)

    def reviews(self, incident_id: str) -> list[HumanReview]:
        return self._of(HumanReview, incident_id)

    def audit_events(self, incident_id: str) -> list[AuditEvent]:
        return self._of(AuditEvent, incident_id)

    def list_incidents(self, *, limit: int, offset: int) -> tuple[int, list[IncidentSummary]]:
        first: dict[str, SourceEvent] = {}
        for source in self._of(SourceEvent):
            first.setdefault(source.incident_id, source)
        ordered = sorted(first.values(), key=lambda s: s.received_at, reverse=True)
        page = [
            IncidentSummary(
                incident_id=s.incident_id,
                first_received_at=s.received_at,
                latest_assessment=next(reversed(self.assessments(s.incident_id)), None),
            )
            for s in ordered[offset : offset + limit]
        ]
        return len(ordered), page

    def model_outputs(self, incident_id: str) -> list[ModelOutput]:
        return self._of(ModelOutput, incident_id)

    def interop_receipt(self, receipt_id: str) -> InteropReceipt | None:
        return next((r for r in self._of(InteropReceipt) if r.receipt_id == receipt_id), None)

    def interop_receipts(self, tenant_id: str, source_event_id: str) -> list[InteropReceipt]:
        return [
            r
            for r in self._of(InteropReceipt)
            if r.tenant_id == tenant_id and r.source_event_id == source_event_id
        ]

    def replay_run(self, run_id: str) -> ReplayRun | None:
        return next((r for r in self._of(ReplayRun) if r.run_id == run_id), None)

    def replay_runs(self, *, limit: int) -> list[ReplayRun]:
        return list(reversed(self._of(ReplayRun)))[:limit]

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass

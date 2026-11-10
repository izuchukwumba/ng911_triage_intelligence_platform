"""In-process event store for tests and local demos. Not durable."""

import threading
from collections.abc import Sequence

from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
from ntip.schema.canonical import Incident
from ntip.schema.replay import ReplayRun
from ntip.schema.review import HumanReview
from ntip.schema.source import SourceEvent
from ntip.store.base import DuplicateRecord, IdempotencyClaim, IncidentSummary, Record


def _identity(record: Record) -> tuple[str, ...]:
    match record:
        case SourceEvent():
            return ("source", record.source_event_id)
        case Incident():
            # Each derivation is a new version, identified by its inputs and time.
            return ("incident", record.incident_id, record.derived_at.isoformat())
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


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[Record] = []
        self._identities: set[tuple[str, ...]] = set()

    def append(self, records: Sequence[Record]) -> None:
        with self._lock:
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

    def replay_run(self, run_id: str) -> ReplayRun | None:
        return next((r for r in self._of(ReplayRun) if r.run_id == run_id), None)

    def replay_runs(self, *, limit: int) -> list[ReplayRun]:
        return list(reversed(self._of(ReplayRun)))[:limit]

    def ping(self) -> bool:
        return True

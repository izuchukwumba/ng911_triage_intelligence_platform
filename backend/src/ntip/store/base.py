"""The append-only event store interface (design v1.2, section 9).

Everything the platform learns or decides is appended, never updated:
source events as received, each derived version of an incident, every
assessment, every human review and an audit event for each action. The
"current state" of an incident is a projection over these records.

Writes happen in batches: one pipeline step appends all of its records (and,
for ingestion, its idempotency key) atomically, so a crash can never leave an
assessment without the audit event that explains it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ntip.schema.advisory import Assessment
from ntip.schema.audit import AuditEvent
from ntip.schema.base import Identifier, SchemaModel, Sha256Digest, UtcDatetime
from ntip.schema.canonical import Incident
from ntip.schema.replay import ReplayRun
from ntip.schema.review import HumanReview
from ntip.schema.source import SourceEvent


class IdempotencyClaim(SchemaModel):
    """Reserves an ingestion idempotency key for one request (design v1.2, 5.3)."""

    key: str
    request_digest: Sha256Digest
    incident_id: Identifier
    claimed_at: UtcDatetime


Record = (
    SourceEvent | Incident | Assessment | HumanReview | AuditEvent | IdempotencyClaim | ReplayRun
)


class StoreError(Exception):
    pass


class DuplicateRecord(StoreError):
    """A record with this identity already exists; the batch was not written."""


class UnknownIncident(StoreError):
    pass


@dataclass(frozen=True)
class IncidentSummary:
    incident_id: str
    first_received_at: UtcDatetime
    latest_assessment: Assessment | None


class EventStore(Protocol):
    def append(self, records: Sequence[Record]) -> None:
        """Write all records or none. Raises DuplicateRecord on an identity clash."""

    def idempotency_claim(self, key: str) -> IdempotencyClaim | None: ...

    def source_events(self, incident_id: str) -> list[SourceEvent]:
        """In order received."""

    def incident_versions(self, incident_id: str) -> list[Incident]:
        """Every derived version, oldest first."""

    def assessments(self, incident_id: str) -> list[Assessment]:
        """Oldest first."""

    def assessment(self, assessment_id: str) -> Assessment | None: ...

    def reviews(self, incident_id: str) -> list[HumanReview]:
        """Oldest first."""

    def audit_events(self, incident_id: str) -> list[AuditEvent]:
        """In the order they were appended."""

    def list_incidents(self, *, limit: int, offset: int) -> tuple[int, list[IncidentSummary]]:
        """(total, page) ordered by first receipt, newest first."""

    def replay_run(self, run_id: str) -> ReplayRun | None: ...

    def replay_runs(self, *, limit: int) -> list[ReplayRun]:
        """Newest first."""

    def ping(self) -> bool:
        """True when the store can serve requests (used by readiness checks)."""

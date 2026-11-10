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

from ntip.interop.receipts import InteropReceipt
from ntip.ml.contract import ModelOutput
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
    SourceEvent
    | Incident
    | Assessment
    | HumanReview
    | AuditEvent
    | IdempotencyClaim
    | ReplayRun
    | ModelOutput
    | InteropReceipt
)


class StoreError(Exception):
    pass


class DuplicateRecord(StoreError):
    """A record with this identity already exists; the batch was not written."""


class ConcurrentModification(StoreError):
    """The incident changed since it was read; the batch was not written."""


@dataclass(frozen=True)
class Expectation:
    """A precondition checked atomically with a write (optimistic concurrency).

    The batch is written only if the incident still has exactly
    ``source_events`` source events, i.e. nobody else added a message between
    reading the conversation and writing the result derived from it.
    """

    incident_id: str
    source_events: int


class UnknownIncident(StoreError):
    pass


@dataclass(frozen=True)
class IncidentSummary:
    incident_id: str
    first_received_at: UtcDatetime
    latest_assessment: Assessment | None


class EventStore(Protocol):
    def append(self, records: Sequence[Record], *, expect: Expectation | None = None) -> None:
        """Write all records or none.

        Raises DuplicateRecord on an identity clash and ConcurrentModification
        when ``expect`` no longer holds.
        """

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

    def model_outputs(self, incident_id: str) -> list[ModelOutput]:
        """Recorded model calls for an incident, oldest first."""

    def interop_receipt(self, receipt_id: str) -> InteropReceipt | None: ...

    def interop_receipts(self, tenant_id: str, source_event_id: str) -> list[InteropReceipt]:
        """Receipts for one external incident from one tenant, oldest first."""

    def replay_run(self, run_id: str) -> ReplayRun | None: ...

    def replay_runs(self, *, limit: int) -> list[ReplayRun]:
        """Newest first."""

    def ping(self) -> bool:
        """True when the store can serve requests (used by readiness checks)."""

    def close(self) -> None:
        """Release held resources such as database connections. Idempotent."""

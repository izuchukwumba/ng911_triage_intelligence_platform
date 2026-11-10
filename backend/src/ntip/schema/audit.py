"""Append-only audit events (design v1.2, section 9.1).

Every action by the system or an operator produces one event. Events
reference the object they concern by id and digest rather than embedding it,
so the log can be retained, exported and verified independently.
"""

from enum import StrEnum

from ntip.schema.base import SCHEMA_VERSION, Identifier, SchemaModel, Sha256Digest, UtcDatetime


class AuditEventType(StrEnum):
    SOURCE_RECEIVED = "source.received"
    INCIDENT_PARSED = "incident.parsed"
    LOCATION_ASSESSED = "location.assessed"
    TRIAGE_ASSESSED = "triage.assessed"
    PROCESSING_FAILED = "processing.failed"
    INCIDENT_REVIEWED = "incident.reviewed"
    TRIAGE_OVERRIDDEN = "triage.overridden"
    INCIDENT_REPLAYED = "incident.replayed"
    EVALUATION_COMPLETED = "evaluation.completed"


class ActorKind(StrEnum):
    SERVICE = "service"
    OPERATOR = "operator"


class Actor(SchemaModel):
    kind: ActorKind
    actor_id: Identifier


class AuditEvent(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    event_id: Identifier
    incident_id: Identifier
    occurred_at: UtcDatetime
    event_type: AuditEventType
    actor: Actor
    # Version of the component that acted, e.g. "rules-1.0.0".
    component_version: str | None = None
    # Ties together every event caused by one request.
    correlation_id: Identifier
    # The object the event concerns: its id and a digest of its JSON.
    subject_id: Identifier
    subject_digest: Sha256Digest

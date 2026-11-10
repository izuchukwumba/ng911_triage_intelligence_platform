"""Interop receipts: an immutable record of every external submission.

Every payload that reaches the gateway gets a receipt, whether it was
accepted, rejected or quarantined. The receipt keeps the original bytes, their
digest, the profile and adapter versions, any validation problems, and a
field-level mapping record (design v1.2, sections 3B.3 and 3B.4).
"""

from enum import StrEnum

from pydantic import Field

from ntip.schema.base import SCHEMA_VERSION, Identifier, SchemaModel, Sha256Digest, UtcDatetime


class ReceiptStatus(StrEnum):
    ACCEPTED = "accepted_for_advisory_processing"
    # Valid, but carries no narrative the parser can read (or none that is new).
    ACCEPTED_NO_NARRATIVE = "accepted_no_new_narrative"
    # Valid, but older than a revision already processed: kept, not reprocessed.
    OUT_OF_ORDER = "accepted_out_of_order"
    UNSUPPORTED_VERSION = "rejected_unsupported_version"
    # Not valid against the pinned schema; kept for diagnosis, never processed.
    QUARANTINED = "quarantined_invalid"


class MappingStatus(StrEnum):
    MAPPED = "mapped"
    PRESERVED_UNMAPPED = "preserved_unmapped"


class FieldMapping(SchemaModel):
    """How one part of the source payload was (or was not) used."""

    source_pointer: str
    source_value_digest: Sha256Digest
    transformation_id: str
    transformation_version: str
    target: str | None
    status: MappingStatus
    # Why a field was not mapped, when there is more to say (2.6.0).
    note: str | None = None


class InteropReceipt(SchemaModel):
    schema_version: str = SCHEMA_VERSION
    receipt_id: Identifier
    received_at: UtcDatetime
    tenant_id: Identifier
    profile_id: str
    adapter_version: str
    schema_artifact_digest: Sha256Digest
    status: ReceiptStatus
    # The original payload exactly as received, and its digest.
    payload: str
    payload_digest: Sha256Digest
    # From the payload, when it could be read.
    source_event_id: str | None = None
    source_revision: str | None = None
    problems: list[str] = Field(default_factory=list)
    mapping: list[FieldMapping] = Field(default_factory=list)
    # Set when the payload was processed into an incident.
    incident_id: Identifier | None = None
    platform_source_event_id: Identifier | None = None
    assessment_id: Identifier | None = None

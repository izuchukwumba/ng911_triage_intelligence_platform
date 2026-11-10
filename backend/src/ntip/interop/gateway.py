"""The EIDO import gateway: a trust boundary, not part of any NG911 call path.

Responsibilities, in order (design v1.2, section 3B.3):

1. Only the configured profile is accepted; payload size is bounded.
2. Every payload gets an immutable receipt holding the exact bytes and digest.
3. An unsupported ``eidoVersion`` is rejected; a payload that fails the pinned
   schema is quarantined. Neither reaches the parser or any model.
4. Idempotency per (tenant, EIDO ``$id``, ``lastUpdateTimeStamp``): a resend
   returns the original receipt; the same revision with different content is
   a conflict.
5. Revisions are new events, never rewrites. A revision older than one
   already processed is kept but not reprocessed (no silent rollback).
6. Only notes not seen in earlier revisions become new narrative, so a
   revision that resends the whole incident does not duplicate it.
7. The advisory assessment is produced by the normal pipeline and stays
   separate from the EIDO, which is never modified (ADR-INT-002).

The gateway is asynchronous with respect to any external system: it returns
a receipt and never sits in a call-routing or call-handling path.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ntip.interop.eido.adapter import map_eido
from ntip.interop.eido.profile import ADAPTER_VERSION, PROFILE, EidoProfile
from ntip.interop.eido.validate import validate
from ntip.interop.receipts import InteropReceipt, ReceiptStatus
from ntip.pipeline import Pipeline
from ntip.schema.base import sha256_digest
from ntip.schema.source import SourceType

MAX_PAYLOAD_BYTES = 512_000
_PROCESSED = {ReceiptStatus.ACCEPTED, ReceiptStatus.ACCEPTED_NO_NARRATIVE}


class UnsupportedProfile(Exception):
    pass


class PayloadTooLarge(Exception):
    pass


class RevisionConflict(Exception):
    """Same EIDO id and revision as an earlier submission, different content."""


@dataclass(frozen=True)
class GatewayResult:
    receipt: InteropReceipt
    replayed: bool = False


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _notes(payload: str) -> set[tuple[str, str]]:
    eido = json.loads(payload)
    return {
        (str(n.get("$id")), sha256_digest(str(n.get("notesActionComments", "")).strip()))
        for n in eido.get("notesComponent", [])
    }


class EidoGateway:
    def __init__(self, pipeline: Pipeline, profile: EidoProfile = PROFILE) -> None:
        self.pipeline = pipeline
        self.profile = profile

    def _receipt(
        self, raw: bytes, tenant_id: str, status: ReceiptStatus, **fields: Any
    ) -> InteropReceipt:
        return InteropReceipt(
            receipt_id=self.pipeline.new_id("rcpt"),
            received_at=self.pipeline.clock(),
            tenant_id=tenant_id,
            profile_id=self.profile.profile_id,
            adapter_version=ADAPTER_VERSION,
            schema_artifact_digest=self.profile.schema_artifact_digest,
            status=status,
            # Invalid UTF-8 cannot be kept as text; the digest is always of the raw bytes.
            payload=raw.decode("utf-8", errors="replace"),
            payload_digest=sha256_digest(raw),
            **fields,
        )

    def _store(self, receipt: InteropReceipt) -> GatewayResult:
        self.pipeline.store.append([receipt])
        return GatewayResult(receipt)

    def ingest(
        self, raw: bytes, *, tenant_id: str, profile_id: str, correlation_id: str
    ) -> GatewayResult:
        if profile_id != self.profile.profile_id:
            raise UnsupportedProfile(profile_id)
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise PayloadTooLarge(len(raw))

        def reject(status: ReceiptStatus, problems: list[str], **ids: Any) -> GatewayResult:
            return self._store(self._receipt(raw, tenant_id, status, problems=problems, **ids))

        try:
            eido = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as err:
            return reject(ReceiptStatus.QUARANTINED, [f"not JSON: {err}"[:300]])
        if not isinstance(eido, dict):
            return reject(ReceiptStatus.QUARANTINED, ["not a JSON object"])

        revision = eido.get("lastUpdateTimeStamp")
        identity: dict[str, Any] = {
            "source_event_id": str(eido["$id"]) if "$id" in eido else None,
            "source_revision": str(revision) if revision else None,
        }
        version = eido.get("eidoVersion")
        if version != self.profile.eido_version:
            supported = f"{self.profile.profile_id} accepts {self.profile.eido_version!r}"
            problem = f"eidoVersion {version!r} is not supported; {supported}"
            return reject(ReceiptStatus.UNSUPPORTED_VERSION, [problem], **identity)
        problems = validate(eido, self.profile)
        if problems:
            messages = [f"{p.pointer}: {p.message}" for p in problems[:50]]
            return reject(ReceiptStatus.QUARANTINED, messages, **identity)

        mapping = map_eido(eido)
        digest = sha256_digest(raw)
        earlier = self.pipeline.store.interop_receipts(tenant_id, mapping.eido_id)
        processed = [
            r for r in earlier if r.status in _PROCESSED or r.status is ReceiptStatus.OUT_OF_ORDER
        ]

        same_revision = [r for r in processed if r.source_revision == mapping.revision]
        if same_revision:
            if same_revision[0].payload_digest == digest:
                return GatewayResult(same_revision[0], replayed=True)
            raise RevisionConflict(f"{mapping.eido_id} @ {mapping.revision}")

        fields = {**identity, "mapping": mapping.fields}
        this_time = _parse_time(mapping.revision)
        processed_times = [
            _parse_time(r.source_revision or "") for r in processed if r.status in _PROCESSED
        ]
        if this_time is not None and any(t is not None and t > this_time for t in processed_times):
            return self._store(self._receipt(raw, tenant_id, ReceiptStatus.OUT_OF_ORDER, **fields))

        seen: set[tuple[str, str]] = set()
        for r in processed:
            seen |= _notes(r.payload)
        new_notes = [n for n in mapping.notes if (n.note_id, sha256_digest(n.text)) not in seen]
        if not new_notes:
            return self._store(
                self._receipt(raw, tenant_id, ReceiptStatus.ACCEPTED_NO_NARRATIVE, **fields)
            )

        existing = next((r.incident_id for r in earlier if r.incident_id), None)
        result = self.pipeline.ingest(
            "\n".join(n.text for n in new_notes),
            incident_id=existing,
            # One external incident always maps to the same platform incident,
            # and the same id from another tenant maps to a different one.
            new_incident_id=None if existing else _incident_id(tenant_id, mapping.eido_id),
            source_type=SourceType.EIDO_IMPORT,
            correlation_id=correlation_id,
        )
        accepted = self._receipt(
            raw,
            tenant_id,
            ReceiptStatus.ACCEPTED,
            **fields,
            incident_id=result.incident_id,
            platform_source_event_id=result.source_event_id,
            assessment_id=result.assessment.assessment_id,
        )
        return self._store(accepted)


def _incident_id(tenant_id: str, eido_id: str) -> str:
    return "inc_eido_" + sha256_digest(f"{tenant_id}\n{eido_id}").removeprefix("sha256:")[:24]

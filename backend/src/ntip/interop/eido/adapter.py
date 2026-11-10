"""Map a validated EIDO to what the platform can use (design v1.2, section 3B.4).

Only one transformation exists so far, and it is deliberately narrow: the
free-text ``notesComponent[].notesActionComments`` become narrative for the
rules parser, one note at a time, in payload order. Notes are agent-entered,
so the narrative's attribution is unspecified, never "caller said".

Every other top-level component is recorded as preserved but unmapped. The
original payload is kept on the receipt, so nothing is discarded, and nothing
the platform derives is written back into the EIDO (ADR-INT-002).
"""

import json
from dataclasses import dataclass
from typing import Any

from ntip.interop.eido.profile import ADAPTER_VERSION
from ntip.interop.receipts import FieldMapping, MappingStatus
from ntip.schema.base import sha256_digest

NOTES_TRANSFORMATION = "eido-notes-to-narrative"
NOTES_TRANSFORMATION_VERSION = "1.0.0"
# Prologue fields read for identity and ordering, not mapped into the incident.
_IDENTITY = {"$id", "lastUpdateTimeStamp", "eidoVersion"}


@dataclass(frozen=True)
class Note:
    note_id: str
    text: str


@dataclass(frozen=True)
class EidoMapping:
    eido_id: str
    revision: str
    notes: list[Note]
    fields: list[FieldMapping]


def _digest(value: Any) -> str:
    return sha256_digest(json.dumps(value, sort_keys=True, ensure_ascii=False))


def map_eido(eido: dict[str, Any]) -> EidoMapping:
    """Map a payload that has already passed schema validation."""
    fields: list[FieldMapping] = []
    notes: list[Note] = []
    for i, note in enumerate(eido.get("notesComponent", [])):
        text = str(note.get("notesActionComments", "")).strip()
        pointer = f"/notesComponent/{i}/notesActionComments"
        if text:
            notes.append(Note(note_id=str(note.get("$id", f"note-{i}")), text=text))
        fields.append(
            FieldMapping(
                source_pointer=pointer,
                source_value_digest=_digest(note.get("notesActionComments")),
                transformation_id=NOTES_TRANSFORMATION,
                transformation_version=NOTES_TRANSFORMATION_VERSION,
                target="SourceEvent.text" if text else None,
                status=MappingStatus.MAPPED if text else MappingStatus.PRESERVED_UNMAPPED,
            )
        )
    for key in sorted(eido):
        if key in _IDENTITY or key == "notesComponent":
            continue
        fields.append(
            FieldMapping(
                source_pointer=f"/{key.replace('~', '~0').replace('/', '~1')}",
                source_value_digest=_digest(eido[key]),
                transformation_id="none",
                transformation_version=ADAPTER_VERSION,
                target=None,
                status=MappingStatus.PRESERVED_UNMAPPED,
            )
        )
    return EidoMapping(
        eido_id=str(eido["$id"]),
        revision=str(eido["lastUpdateTimeStamp"]),
        notes=notes,
        fields=fields,
    )

"""Map a validated EIDO to what the platform can use (design v1.2, section 3B.4).

Two transformations exist, both deliberately narrow:

- ``notesComponent[].notesActionComments`` become narrative for the rules
  parser, one note at a time, in payload order. Notes are agent-entered, so
  the narrative's attribution is unspecified, never "caller said".
- ``locationComponent[].locationByValue`` (PIDF-LO) becomes a *supplied*
  location: a civic address and/or point, kept apart from anything a caller
  said and unverified until a person or reference data confirms it. A
  location the adapter cannot fully read is preserved, with the reason, not
  guessed at. ``locationByReferenceUrl`` is never dereferenced.

Every other component, persons included (data minimisation: triage does not
need identities), is recorded as preserved but unmapped. The original payload
is kept on the receipt, so nothing is discarded, and nothing the platform
derives is written back into the EIDO (ADR-INT-002).
"""

import json
from dataclasses import dataclass
from typing import Any

from ntip.interop.eido.pidf import UnreadablePidf, parse_pidf_lo
from ntip.interop.eido.profile import ADAPTER_VERSION
from ntip.interop.receipts import FieldMapping, MappingStatus
from ntip.schema.base import sha256_digest
from ntip.schema.source import MAX_SUPPLIED_LOCATIONS, SuppliedLocation

NOTES_TRANSFORMATION = "eido-notes-to-narrative"
NOTES_TRANSFORMATION_VERSION = "1.0.0"
LOCATION_TRANSFORMATION = "eido-pidf-lo-to-supplied-location"
LOCATION_TRANSFORMATION_VERSION = "1.0.0"
# Prologue fields read for identity and ordering, not mapped into the incident.
_IDENTITY = {"$id", "lastUpdateTimeStamp", "eidoVersion"}


@dataclass(frozen=True)
class Note:
    note_id: str
    text: str


@dataclass(frozen=True)
class MappedLocation:
    # (location $id, digest of its PIDF-LO): identifies it across revisions.
    key: tuple[str, str]
    supplied: SuppliedLocation


@dataclass(frozen=True)
class EidoMapping:
    eido_id: str
    revision: str
    notes: list[Note]
    fields: list[FieldMapping]
    locations: list[MappedLocation]


def _digest(value: Any) -> str:
    return sha256_digest(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _pointer(*parts: str | int) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _locations(eido: dict[str, Any]) -> tuple[list[MappedLocation], list[FieldMapping]]:
    mapped: list[MappedLocation] = []
    fields: list[FieldMapping] = []

    def record(pointer: str, value: Any, target: str | None, note: str | None = None) -> None:
        fields.append(
            FieldMapping(
                source_pointer=pointer,
                source_value_digest=_digest(value),
                transformation_id=LOCATION_TRANSFORMATION if target else "none",
                transformation_version=(
                    LOCATION_TRANSFORMATION_VERSION if target else ADAPTER_VERSION
                ),
                target=target,
                status=MappingStatus.MAPPED if target else MappingStatus.PRESERVED_UNMAPPED,
                note=note,
            )
        )

    for i, component in enumerate(eido.get("locationComponent", [])):
        for key in sorted(component):
            pointer = _pointer("locationComponent", i, key)
            value = component[key]
            if key == "locationByValue":
                try:
                    pidf = parse_pidf_lo(str(value))
                except UnreadablePidf as err:
                    record(pointer, value, None, f"PIDF-LO not mapped: {err}"[:300])
                    continue
                if len(mapped) >= MAX_SUPPLIED_LOCATIONS:
                    record(pointer, value, None, "too many locations in one EIDO")
                    continue
                description = component.get("locationDescriptionText")
                mapped.append(
                    MappedLocation(
                        key=(str(component.get("$id", i)), _digest(value)),
                        supplied=SuppliedLocation(
                            origin=pointer,
                            civic_address=pidf.civic_address,
                            coordinates=pidf.coordinates,
                            description=str(description)[:1000] if description else None,
                        ),
                    )
                )
                record(pointer, value, "SourceEvent.supplied_locations")
            elif key.endswith("ReferenceUrl"):
                record(pointer, value, None, "references are never dereferenced")
            elif key not in _IDENTITY | {"updatedByAgencyReference"}:
                record(pointer, value, None)
    return mapped, fields


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
    locations, location_fields = _locations(eido)
    fields += location_fields
    for key in sorted(eido):
        if key in _IDENTITY or key in {"notesComponent", "locationComponent"}:
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
        locations=locations,
    )

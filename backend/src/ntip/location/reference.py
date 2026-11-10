"""Location level L3: check addresses against a GIS reference layer (design v1.2, 8.3).

The reference is a Site/Structure Address Point layer in the field names of
NENA's NG9-1-1 GIS Data Model (NENA-STA-006.3, Apache-2.0 templates), read
from CSV. A reported or supplied civic address that matches exactly one
address point gets a ``geocoded`` companion candidate: the reference's full
address and coordinates, marked ``reference_validated`` with the layer and
the point's NGUID as its source. The original candidate is left as it was.

An address that matches several points (e.g. the same street and number in
two municipalities, with no municipality said) or none still requires a
person to verify it. Matching confirms that an address exists in the
reference, not that the caller is there, and it never affects priority: it
only settles whether the location still needs verifying.

The committed layer (``data/gis``) is synthetic. A real deployment would
load its authority's own layer, under that data's licence.
"""

import csv
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ntip.parser.locations import normalise_street
from ntip.schema.base import CivicAddress, Coordinates
from ntip.schema.canonical import (
    Extractor,
    ExtractorKind,
    Incident,
    LocationCandidate,
    LocationRole,
    LocationValidation,
)

MATCHER_VERSION = "1.0.0"
MATCHER = Extractor(
    kind=ExtractorKind.RULE, extractor_id="gis-reference-matcher", version=MATCHER_VERSION
)
# Required in a SiteStructureAddressPoint layer by NENA-STA-006.3, plus the
# address and position fields matching needs.
REQUIRED_FIELDS = ("DiscrpAgID", "DateUpdate", "NGUID", "Country", "A1",
                   "Add_Number", "St_Name", "Latitude", "Longitude")  # fmt: skip


class InvalidReference(ValueError):
    pass


class MatchStatus(StrEnum):
    VALIDATED = "validated"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    INCOMPLETE = "incomplete"  # no house number or street to match on


@dataclass(frozen=True)
class AddressPoint:
    nguid: str
    house_number: str
    street: str
    municipality: str | None
    postal_community: str | None
    region: str
    postal_code: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Match:
    status: MatchStatus
    point: AddressPoint | None = None
    candidates: int = 0


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


@dataclass(frozen=True)
class ReferenceLayer:
    name: str
    digest: str
    points: tuple[AddressPoint, ...]

    @property
    def source(self) -> str:
        return f"{self.name}@{self.digest[:19]}"

    @classmethod
    def load(cls, path: Path) -> "ReferenceLayer":
        raw = path.read_bytes()
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        missing = [f for f in REQUIRED_FIELDS if rows and f not in rows[0]]
        if not rows or missing:
            raise InvalidReference(f"{path.name}: missing NENA fields {missing or 'all rows'}")
        points = []
        for number, row in enumerate(rows, start=2):
            try:
                parts = (row.get("St_PreDir"), row["St_Name"], row.get("St_PosTyp"),
                         row.get("St_PosDir"))  # fmt: skip
                street = " ".join(p for p in map(_clean, parts) if p)
                points.append(
                    AddressPoint(
                        nguid=row["NGUID"].strip(),
                        house_number=f"{row['Add_Number'].strip()}{row.get('AddNum_Suf') or ''}",
                        street=street,
                        municipality=_clean(row.get("A3")),
                        postal_community=_clean(row.get("Post_Comm")),
                        region=row["A1"].strip(),
                        postal_code=_clean(row.get("Post_Code")),
                        latitude=float(row["Latitude"]),
                        longitude=float(row["Longitude"]),
                    )
                )
            except (KeyError, ValueError) as err:
                raise InvalidReference(f"{path.name} line {number}: {err}") from None
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        return cls(name=path.stem, digest=digest, points=tuple(points))

    def match(self, address: CivicAddress) -> Match:
        if not address.house_number or not address.street:
            return Match(MatchStatus.INCOMPLETE)
        number = address.house_number.strip().lower()
        street = normalise_street(address.street)
        found = [
            p for p in self.points
            if p.house_number.lower() == number and normalise_street(p.street) == street
        ]  # fmt: skip
        locality = (address.locality or "").strip().lower()
        if locality:
            found = [p for p in found
                     if locality in {(p.municipality or "").lower(),
                                     (p.postal_community or "").lower()}]  # fmt: skip
        if address.postal_code:
            found = [p for p in found if p.postal_code == address.postal_code.strip()]
        if not found:
            return Match(MatchStatus.NOT_FOUND)
        if len(found) > 1:
            return Match(MatchStatus.AMBIGUOUS, candidates=len(found))
        return Match(MatchStatus.VALIDATED, found[0], 1)


def validate_locations(incident: Incident, layer: ReferenceLayer) -> Incident:
    """The incident with a reference-validated companion for each matched address."""
    added: list[LocationCandidate] = []
    for candidate in incident.locations:
        if candidate.role is LocationRole.GEOCODED or candidate.civic_address is None:
            continue
        match = layer.match(candidate.civic_address)
        if match.status is not MatchStatus.VALIDATED or match.point is None:
            continue
        point = match.point
        added.append(
            LocationCandidate(
                location_id=f"{candidate.location_id}_ref",
                role=LocationRole.GEOCODED,
                raw_text=f"Reference match for {candidate.location_id}",
                civic_address=CivicAddress(
                    house_number=point.house_number,
                    street=point.street,
                    unit=candidate.civic_address.unit,
                    floor=candidate.civic_address.floor,
                    locality=point.municipality or point.postal_community,
                    region=point.region,
                    postal_code=point.postal_code,
                ),
                coordinates=Coordinates(lat=point.latitude, lng=point.longitude),
                extractor=MATCHER,
                validation=LocationValidation.REFERENCE_VALIDATED,
                validation_source=f"{layer.source}:{point.nguid}",
            )
        )
    if not added:
        return incident
    # Re-validated, so the incident's own checks (unique ids, ...) still hold.
    document = incident.model_dump()
    document["locations"] = [*document["locations"], *(c.model_dump() for c in added)]
    return Incident.model_validate(document)

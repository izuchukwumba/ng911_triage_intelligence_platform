"""Read a PIDF-LO location carried by value in an EIDO (``locationByValue``).

PIDF-LO (RFC 4119, profiled by RFC 5491) wraps either a civic address (RFC
5139 ``civicAddress``) or a geodetic shape (GML ``Point``, or a ``Circle``
whose radius is the uncertainty). Only those are read here. Anything else,
including polygons and ellipses, is left unmapped rather than guessed at.

The input is untrusted XML from another organisation, so documents with a
DOCTYPE or entity declarations are refused outright (no entity expansion, no
external resources), and nothing is ever dereferenced.
"""

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pydantic import ValidationError

from ntip.schema.base import CivicAddress, Coordinates

MAX_PIDF_CHARS = 20_000
_GML = "http://www.opengis.net/gml"
_METRES = {"urn:ogc:def:uom:EPSG::9001", "m", "metre", "meter"}


class UnreadablePidf(ValueError):
    pass


@dataclass(frozen=True)
class PidfLocation:
    civic_address: CivicAddress | None
    coordinates: Coordinates | None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first(root: ET.Element, name: str) -> ET.Element | None:
    return next((e for e in root.iter() if _local(e.tag) == name), None)


def _text(root: ET.Element, name: str) -> str | None:
    element = _first(root, name)
    value = " ".join((element.text or "").split()) if element is not None else ""
    return value or None


def _civic(root: ET.Element) -> CivicAddress | None:
    civic = _first(root, "civicAddress")
    if civic is None:
        return None

    def part(name: str) -> str | None:
        return _text(civic, name)

    street_parts = [part("PRD"), part("RD") or part("A6"), part("STS"), part("POD")]
    street = " ".join(p for p in street_parts if p) or None
    number = "".join(p for p in (part("HNO"), part("HNS")) if p) or None
    address = CivicAddress(
        house_number=number,
        street=street,
        unit=part("UNIT"),
        floor=part("FLR"),
        locality=part("A3"),
        region=part("A1"),
        postal_code=part("PC"),
        landmark=part("LMK"),
    )
    return address if address.model_dump(exclude_none=True) else None


def _coordinates(root: ET.Element) -> Coordinates | None:
    shape = next((e for e in root.iter() if _local(e.tag) in {"Point", "Circle"}), None)
    if shape is None:
        return None
    pos = _text(shape, "pos")
    if pos is None:
        raise UnreadablePidf(f"{_local(shape.tag)} without gml:pos")
    try:
        lat, lng = (float(v) for v in pos.split())
    except ValueError:
        raise UnreadablePidf(f"gml:pos {pos[:40]!r} is not 'latitude longitude'") from None
    srs = shape.get("srsName", "urn:ogc:def:crs:EPSG::4326")
    if not srs.endswith(("4326", "4979")):
        raise UnreadablePidf(f"unsupported coordinate reference system {srs[:80]!r}")
    uncertainty = None
    if _local(shape.tag) == "Circle":
        radius = _first(shape, "radius")
        if radius is None or radius.get("uom") not in _METRES:
            raise UnreadablePidf("circle radius missing or not in metres")
        try:
            uncertainty = float(radius.text or "")
        except ValueError:
            raise UnreadablePidf("circle radius is not a number") from None
        if not math.isfinite(uncertainty) or uncertainty <= 0:
            raise UnreadablePidf("circle radius must be positive")
    try:
        return Coordinates(lat=lat, lng=lng, uncertainty_m=uncertainty)
    except ValidationError as err:
        raise UnreadablePidf(f"coordinates out of range: {err.errors()[0]['msg']}") from None


def parse_pidf_lo(document: str) -> PidfLocation:
    """The civic address and/or point in a PIDF-LO document.

    Raises UnreadablePidf for anything not safely and fully understood.
    """
    if len(document) > MAX_PIDF_CHARS:
        raise UnreadablePidf("document too large")
    if re.search(r"<!(DOCTYPE|ENTITY)", document, re.IGNORECASE):
        raise UnreadablePidf("DOCTYPE and entity declarations are not accepted")
    try:
        root = ET.fromstring(document)
    except ET.ParseError as err:
        raise UnreadablePidf(f"not well-formed XML: {err}") from None
    location = PidfLocation(civic_address=_civic(root), coordinates=_coordinates(root))
    if location.civic_address is None and location.coordinates is None:
        raise UnreadablePidf("no civic address, point or circle found")
    return location

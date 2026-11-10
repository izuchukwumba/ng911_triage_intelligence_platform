"""Reported-location extraction.

Finds every location the speaker mentions (numbered civic addresses,
intersections, route references, street names, landmarks), each with the span
it was quoted from and the components that are still missing. Nothing here is
validated and no coordinates are produced: a spoken address is a *reported*
location until something authoritative confirms it (design v1.2, section 8).
"""

import re
from dataclasses import dataclass, field

from ntip.schema.base import CivicAddress

_SUFFIX = (
    r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|court|ct"
    r"|place|pl|circle|cir|highway|hwy|parkway|pkwy|terrace|ter|trail|trl|loop|alley)"
)
# Abbreviated street suffixes and their full form, so "Main St" and "Main Street"
# are recognised as the same street.
STREET_SUFFIXES = {
    "st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
    "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "cir": "circle",
    "hwy": "highway", "pkwy": "parkway", "ter": "terrace", "trl": "trail",
}  # fmt: skip
_NAME = r"[A-Za-z][\w'’]*"
_ORDINAL = r"\d+(?:st|nd|rd|th)"
_DIRECTION = r"(?:[NSEW]\.?|north|south|east|west)"

_NUMBERED = re.compile(
    rf"(?<![\w-])(?P<number>\d+[A-Za-z]?)\s+"
    rf"(?P<street>(?:{_DIRECTION}\s+)?(?:(?:{_ORDINAL}|{_NAME})\s+){{1,3}}?{_SUFFIX})(?!\w)",
    re.IGNORECASE,
)
# Spanish order: "Calle Pino 789"
_NUMBERED_ES = re.compile(
    r"(?<!\w)(?P<street>(?:calle|avenida|av\.|carrera|camino)\s+[\wáéíóúñ]+"
    r"(?:\s+[\wáéíóúñ]+)?)\s+(?P<number>\d+)(?!\w)",
    re.IGNORECASE,
)
_STREET_SIDE = rf"(?:{_ORDINAL}|{_NAME})(?:\s+{_SUFFIX})?"
_INTERSECTION = re.compile(
    rf"(?<!\w)(?:(?:corner|intersection)\s+of\s+)?"
    rf"(?P<a>{_STREET_SIDE})\s+(?:and|&)\s+(?P<b>{_STREET_SIDE})(?!\w)",
    re.IGNORECASE,
)
_ROUTE = re.compile(
    r"(?<!\w)(?P<street>(?:route|highway|hwy|interstate|state road|county road|i-)\s*\d+)(?!\w)",
    re.IGNORECASE,
)
_STREET_ONLY = re.compile(
    rf"(?<!\w)(?:on|near|at|along|off)\s+(?:the\s+)?"
    rf"(?P<street>(?:{_DIRECTION}\s+)?(?:(?:{_ORDINAL}|{_NAME})\s+){{1,2}}?{_SUFFIX})(?!\w)",
    re.IGNORECASE,
)
_LANDMARK = re.compile(
    r"(?<!\w)(?:near|at|by|outside|behind|in front of|across from)\s+"
    r"(?P<landmark>(?:the\s+)?(?:[A-Za-z][\w'’]*\s+){0,4}?"
    r"(?:park|school|hospital|mall|plaza|center|centre|station|church|clinic|parking lot"
    r"|library|stadium|bridge|overpass|bus stop|store|market|bank|hotel|restaurant))(?!\w)",
    re.IGNORECASE,
)
_UNIT = re.compile(
    r"(?<!\w)(?:apartment|apt\.?|unit|suite|ste\.?|room|#)\s*(?P<unit>[A-Za-z]?\d+[A-Za-z]?|[A-Za-z])(?!\w)",
    re.IGNORECASE,
)
_FLOOR = re.compile(
    r"(?<!\w)(?P<floor>\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|top|ground)"
    r"\s+floor(?!\w)",
    re.IGNORECASE,
)
_POSTAL = re.compile(r"(?<!\d)(?P<zip>\d{5})(?:-\d{4})?(?!\d)")

# Words that look like street names in the intersection pattern but are not.
_NOT_STREETS = {
    "he",
    "she",
    "it",
    "they",
    "we",
    "i",
    "you",
    "him",
    "her",
    "them",
    "there",
    "here",
    "this",
    "that",
    "blood",
    "smoke",
    "fire",
    "help",
    "please",
    "now",
    "then",
    "me",
}

# How far either side of an address a unit or floor may sit and still belong to it.
_ATTACH_WINDOW = 30


@dataclass(frozen=True)
class ExtractedLocation:
    start: int
    end: int
    kind: str  # numbered | intersection | route | street | landmark
    civic_address: CivicAddress
    missing_fields: list[str] = field(default_factory=list)

    def raw_text(self, text: str) -> str:
        return text[self.start : self.end]


def _overlaps(start: int, end: int, taken: list[tuple[int, int]]) -> bool:
    return any(start < t_end and t_start < end for t_start, t_end in taken)


def _is_street_side(side: str) -> bool:
    words = side.lower().split()
    if re.fullmatch(_ORDINAL, words[0]):
        return True
    if len(words) > 1 and re.fullmatch(_SUFFIX, words[-1]):
        return True
    # A bare name only counts when capitalised, e.g. "Main and Elm".
    return side[0].isupper() and words[0] not in _NOT_STREETS


def _attach(text: str, start: int, end: int, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """A unit/floor mention just before or after an address, in the same sentence."""
    lo = max(0, start - _ATTACH_WINDOW)
    hi = min(len(text), end + _ATTACH_WINDOW)
    for m in pattern.finditer(text, lo, hi):
        between = text[m.end() : start] if m.end() <= start else text[end : m.start()]
        if not re.search(r"[.!?]", between):
            return m
    return None


def _missing(address: CivicAddress, kind: str) -> list[str]:
    missing = []
    if kind == "landmark":
        missing.append("street")
    if kind in {"route", "street", "landmark"} and address.house_number is None:
        missing.append("house_number")
    if address.locality is None:
        missing.append("locality")
    if address.region is None:
        missing.append("region")
    return missing


def extract_locations(text: str) -> list[ExtractedLocation]:
    found: list[ExtractedLocation] = []
    taken: list[tuple[int, int]] = []

    def add(start: int, end: int, kind: str, **parts: str | None) -> None:
        unit = _attach(text, start, end, _UNIT) if kind == "numbered" else None
        floor = _attach(text, start, end, _FLOOR) if kind == "numbered" else None
        postal = _POSTAL.search(text, end, min(len(text), end + 40))
        span_start = min([start] + [m.start() for m in (unit, floor) if m])
        span_end = max([end] + [m.end() for m in (unit, floor) if m])
        address = CivicAddress(
            unit=unit.group("unit") if unit else None,
            floor=floor.group("floor") if floor else None,
            postal_code=postal.group("zip") if postal and kind == "numbered" else None,
            **parts,
        )
        found.append(
            ExtractedLocation(span_start, span_end, kind, address, _missing(address, kind))
        )
        taken.append((span_start, span_end))

    for m in _NUMBERED.finditer(text):
        add(m.start(), m.end(), "numbered", house_number=m.group("number"),
            street=m.group("street"))  # fmt: skip
    for m in _NUMBERED_ES.finditer(text):
        if not _overlaps(m.start(), m.end(), taken):
            add(m.start(), m.end(), "numbered", house_number=m.group("number"),
                street=m.group("street"))  # fmt: skip
    for m in _INTERSECTION.finditer(text):
        a, b = m.group("a"), m.group("b")
        if _overlaps(m.start(), m.end(), taken):
            continue
        if not (_is_street_side(a) and _is_street_side(b)):
            continue
        add(m.start(), m.end(), "intersection", street=f"{a} & {b}")
    for m in _ROUTE.finditer(text):
        if not _overlaps(m.start(), m.end(), taken):
            add(m.start("street"), m.end("street"), "route", street=m.group("street"))
    for m in _STREET_ONLY.finditer(text):
        if not _overlaps(m.start("street"), m.end("street"), taken):
            add(m.start("street"), m.end("street"), "street", street=m.group("street"))
    for m in _LANDMARK.finditer(text):
        if not _overlaps(m.start("landmark"), m.end("landmark"), taken):
            add(m.start("landmark"), m.end("landmark"), "landmark",
                landmark=m.group("landmark"))  # fmt: skip

    return sorted(found, key=lambda loc: loc.start)


def normalise_street(street: str) -> str:
    """Lower-case, single-spaced, with a final abbreviated suffix spelled out."""
    words = street.lower().replace(".", "").split()
    if words and words[-1] in STREET_SUFFIXES:
        words[-1] = STREET_SUFFIXES[words[-1]]
    return " ".join(words)

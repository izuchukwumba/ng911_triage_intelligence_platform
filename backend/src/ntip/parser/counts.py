"""Victim count extraction.

The count is a Fact, never a bare number: a transcript that does not mention
how many people are involved yields ``not_reported`` (the TypeScript parser
defaulted to 1), "several people" yields ``unknown``, and two different stated
counts yield ``conflicting`` with both candidates kept.
"""

import re

from ntip.parser.context import analyse
from ntip.parser.text import Match
from ntip.schema.base import Evidence, Fact, FactStatus, SourceSpan
from ntip.schema.canonical import Polarity

_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a dozen": 12,
    "dozen": 12, "twenty": 20,
    "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}  # fmt: skip
_NUMBER = r"(?:\d{1,3}|" + "|".join(sorted(map(re.escape, _NUMBERS), key=len, reverse=True)) + ")"

_PEOPLE = (
    r"(?:people|persons|victims|individuals|patients|adults|kids|children|men|women"
    r"|guys|bodies|passengers|personas|víctimas|heridos|heridas|niños)"
)
_CASUALTY = r"(?:injured|hurt|wounded|shot|dead|down|bleeding|trapped|unconscious)"

# "five people", "five or six people", "at least 3 victims", "two injured"
_COUNT = re.compile(
    rf"(?<!\w)(?:at least\s+|about\s+|around\s+|maybe\s+)?"
    rf"(?P<low>{_NUMBER})(?:\s*(?:or|to|-|o)\s*(?P<high>{_NUMBER}))?"
    rf"\s+(?:(?:more\s+)?{_PEOPLE}|{_CASUALTY})(?!\w)",
    re.IGNORECASE,
)

_INDEFINITE = re.compile(
    rf"(?<!\w)(?:multiple|several|many|a lot of|lots of|a bunch of|a few|some"
    rf"|a crowd of|varias|varios|muchas|muchos)\s+(?:{_PEOPLE}|{_CASUALTY})(?!\w)"
    r"|(?<!\w)(?:people down|mass casualty)(?!\w)",
    re.IGNORECASE,
)


def _value(token: str) -> int:
    return int(token) if token.isdigit() else _NUMBERS[token.lower()]


def _quote(text: str, source_event_id: str, start: int, end: int) -> Evidence:
    return Evidence(
        source_event_id=source_event_id,
        span=SourceSpan(start=start, end=end),
        text=text[start:end],
    )


def victim_count(text: str, source_event_id: str) -> Fact[int]:
    stated: list[tuple[int, Evidence]] = []
    for m in _COUNT.finditer(text):
        if analyse(text, Match(m.start(), m.end(), m.group(0))).polarity is Polarity.NEGATED:
            continue
        low = _value(m.group("low"))
        high = _value(m.group("high")) if m.group("high") else low
        # A range is planned for at its upper bound.
        stated.append((max(low, high), _quote(text, source_event_id, m.start(), m.end())))

    values = sorted({value for value, _ in stated})
    quotes = [quote for _, quote in stated]
    if len(values) == 1:
        return Fact[int](status=FactStatus.REPORTED, value=values[0], evidence=quotes)
    if len(values) > 1:
        return Fact[int](status=FactStatus.CONFLICTING, candidates=values, evidence=quotes)

    indefinite = [
        _quote(text, source_event_id, m.start(), m.end()) for m in _INDEFINITE.finditer(text)
    ]
    if indefinite:
        return Fact[int](status=FactStatus.UNKNOWN, evidence=indefinite)
    return Fact[int](status=FactStatus.NOT_REPORTED)

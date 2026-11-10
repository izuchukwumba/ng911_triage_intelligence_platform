"""Phrase matching and clause segmentation on raw source text.

All offsets refer to the original, unmodified text so that evidence spans
quote exactly what was received. Matching is case-insensitive and anchored on
word boundaries: "od" must not match inside "blood", and "hit" must not match
inside "white" (the TypeScript parser used substring matching and misfired on
both).
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

_APOSTROPHE = "['’]"


def phrase_pattern(phrases: Iterable[str]) -> re.Pattern[str]:
    """Compile phrases into one word-bounded, case-insensitive alternation.

    Longer phrases are tried first so "not breathing" wins over "breathing",
    and any run of whitespace in the text matches a single space in a phrase.
    """
    unique = sorted({p.strip().lower() for p in phrases if p.strip()}, key=len, reverse=True)
    if not unique:
        return re.compile(r"(?!x)x")  # matches nothing
    parts = [re.escape(p).replace(r"\ ", r"\s+").replace("'", _APOSTROPHE) for p in unique]
    return re.compile(rf"(?<!\w)(?:{'|'.join(parts)})(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    text: str


def find_all(pattern: re.Pattern[str], text: str) -> list[Match]:
    return [Match(m.start(), m.end(), m.group(0)) for m in pattern.finditer(text)]


# Clauses end at sentence punctuation, line breaks and contrastive
# conjunctions: in "he was not breathing earlier but is now", "earlier" belongs
# with "not breathing", while "is now" starts a new clause.
_CLAUSE_BREAK = re.compile(
    r"[.!?;\n]+|(?<!\w)(?:but|however|although|though|whereas|pero|aunque)(?!\w)",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"[.!?\n]+")


@dataclass(frozen=True)
class Segment:
    start: int
    end: int


def _segment_around(breaks: re.Pattern[str], text: str, start: int, end: int) -> Segment:
    seg_start = 0
    seg_end = len(text)
    for m in breaks.finditer(text):
        if m.end() <= start:
            seg_start = m.end()
        elif m.start() >= end:
            seg_end = m.start()
            break
    return Segment(seg_start, seg_end)


def clause_around(text: str, start: int, end: int) -> Segment:
    """The clause containing the range ``[start, end)``."""
    return _segment_around(_CLAUSE_BREAK, text, start, end)


def sentence_around(text: str, start: int, end: int) -> Segment:
    """The sentence containing the range ``[start, end)``."""
    return _segment_around(_SENTENCE_BREAK, text, start, end)


_WORD = re.compile(r"[\w'’]+")


def last_words(text: str, count: int) -> str:
    """The final ``count`` words of ``text``, joined by single spaces."""
    return " ".join(w.lower() for w in _WORD.findall(text)[-count:])


def words(text: str) -> Iterator[str]:
    for w in _WORD.findall(text):
        yield w.lower()

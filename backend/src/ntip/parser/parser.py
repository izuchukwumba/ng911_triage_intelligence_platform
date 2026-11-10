"""Assemble a canonical Incident from source events (baseline B0)."""

import re
from collections.abc import Sequence
from datetime import datetime
from functools import cache

from ntip.parser.classify import classify, detect_language
from ntip.parser.context import analyse
from ntip.parser.counts import victim_count
from ntip.parser.lexicon import OBSERVATION_CUES
from ntip.parser.locations import extract_locations
from ntip.parser.text import find_all, phrase_pattern
from ntip.schema.base import Evidence, Fact, FactStatus, SourceSpan
from ntip.schema.canonical import (
    Conflict,
    ConflictKind,
    Extractor,
    ExtractorKind,
    Incident,
    LocationCandidate,
    LocationRole,
    Observation,
    Polarity,
    Temporality,
)
from ntip.schema.source import SourceEvent

PARSER_ID = "rules-parser"
PARSER_VERSION = "1.1.0"
EXTRACTOR = Extractor(kind=ExtractorKind.RULE, extractor_id=PARSER_ID, version=PARSER_VERSION)


@cache
def _cue_pattern(code: str, language: str) -> re.Pattern[str]:
    return phrase_pattern(OBSERVATION_CUES[code].get(language, []))


def _quote(source: SourceEvent, start: int, end: int) -> Evidence:
    return Evidence(
        source_event_id=source.source_event_id,
        span=SourceSpan(start=start, end=end),
        text=source.text[start:end],
    )


def _observations(source: SourceEvent, languages: list[str]) -> list[Observation]:
    """One observation per distinct (code, context) in this source, quoting its first hit."""
    seen: dict[tuple[str, Polarity, Temporality, str], Observation] = {}
    for code in OBSERVATION_CUES:
        for language in languages:
            for match in find_all(_cue_pattern(code, language), source.text):
                ctx = analyse(source.text, match)
                key = (code, ctx.polarity, ctx.temporality, ctx.attribution)
                if key in seen:
                    continue
                seen[key] = Observation(
                    observation_id="pending",
                    code=code,
                    polarity=ctx.polarity,
                    temporality=ctx.temporality,
                    attribution=ctx.attribution,
                    evidence=_quote(source, match.start, match.end),
                    extractor=EXTRACTOR,
                )
    return list(seen.values())


def _merge_counts(facts: list[Fact[int]]) -> Fact[int]:
    stated = [f for f in facts if f.status in {FactStatus.REPORTED, FactStatus.CONFLICTING}]
    if stated:
        values = sorted({v for f in stated for v in ([f.value] if f.value else f.candidates)})
        evidence = [e for f in stated for e in f.evidence]
        if len(values) == 1:
            return Fact[int](status=FactStatus.REPORTED, value=values[0], evidence=evidence)
        return Fact[int](status=FactStatus.CONFLICTING, candidates=values, evidence=evidence)
    unknown = [f for f in facts if f.status is FactStatus.UNKNOWN]
    if unknown:
        return Fact[int](
            status=FactStatus.UNKNOWN, evidence=[e for f in unknown for e in f.evidence]
        )
    return Fact[int](status=FactStatus.NOT_REPORTED)


def _is_current_affirmation(o: Observation) -> bool:
    return o.polarity is Polarity.AFFIRMED and o.temporality is Temporality.CURRENT


def _observation_conflicts(observations: list[Observation]) -> list[Conflict]:
    conflicts = []
    for code in dict.fromkeys(o.code for o in observations):
        current = [
            o for o in observations if o.code == code and o.temporality is Temporality.CURRENT
        ]
        affirmed = [o.observation_id for o in current if o.polarity is Polarity.AFFIRMED]
        negated = [o.observation_id for o in current if o.polarity is Polarity.NEGATED]
        if affirmed and negated:
            conflicts.append(
                Conflict(
                    conflict_id="pending",
                    kind=ConflictKind.OBSERVATION_POLARITY,
                    code=code,
                    observation_ids=affirmed + negated,
                )
            )
    return conflicts


def _location_conflicts(locations: list[LocationCandidate]) -> list[Conflict]:
    """Different numbered addresses for the same incident (e.g. a corrected address)."""
    numbered: dict[tuple[str, str], list[str]] = {}
    for loc in locations:
        address = loc.civic_address
        if address and address.house_number and address.street:
            key = (address.house_number.lower(), address.street.lower())
            numbered.setdefault(key, []).append(loc.location_id)
    if len(numbered) < 2:
        return []
    ids = [loc_id for group in numbered.values() for loc_id in group]
    return [Conflict(conflict_id="pending", kind=ConflictKind.LOCATION_MISMATCH, location_ids=ids)]


def parse(sources: Sequence[SourceEvent], *, derived_at: datetime) -> Incident:
    """Interpret one or more source events of the same incident, in order.

    The output is deterministic for the same inputs: identifiers are assigned
    by position, so replaying a stored source sequence reproduces the record.
    """
    if not sources:
        raise ValueError("at least one source event is required")
    incident_ids = {s.incident_id for s in sources}
    if len(incident_ids) != 1:
        raise ValueError(f"source events belong to different incidents: {sorted(incident_ids)}")

    combined = "\n".join(s.text for s in sources)
    language = detect_language(combined)
    languages = ["en", "es"] if language == "es" else ["en"]

    observations: list[Observation] = []
    locations: list[LocationCandidate] = []
    counts: list[Fact[int]] = []
    for source in sources:
        found = sorted(
            _observations(source, languages), key=lambda o: (o.evidence.span.start, o.code)
        )
        observations.extend(found)
        for extracted in extract_locations(source.text):
            locations.append(
                LocationCandidate(
                    location_id="pending",
                    role=LocationRole.REPORTED,
                    raw_text=extracted.raw_text(source.text),
                    civic_address=extracted.civic_address,
                    evidence=_quote(source, extracted.start, extracted.end),
                    extractor=EXTRACTOR,
                    missing_fields=extracted.missing_fields,
                )
            )
        counts.append(victim_count(source.text, source.source_event_id))

    count = _merge_counts(counts)
    has_multiple = any(
        o.code == "MULTIPLE_VICTIMS" and _is_current_affirmation(o) for o in observations
    )
    if count.status is FactStatus.REPORTED and (count.value or 0) >= 2 and not has_multiple:
        # A stated count of two or more is itself a multiple-victim cue.
        observations.append(
            Observation(
                observation_id="pending",
                code="MULTIPLE_VICTIMS",
                polarity=Polarity.AFFIRMED,
                evidence=count.evidence[0],
                extractor=EXTRACTOR,
            )
        )

    observations = [
        o.model_copy(update={"observation_id": f"obs_{i}"}) for i, o in enumerate(observations, 1)
    ]
    locations = [
        loc.model_copy(update={"location_id": f"loc_{i}"}) for i, loc in enumerate(locations, 1)
    ]
    conflicts = [
        c.model_copy(update={"conflict_id": f"conf_{i}"})
        for i, c in enumerate(
            _observation_conflicts(observations) + _location_conflicts(locations), 1
        )
    ]

    return Incident(
        incident_id=sources[0].incident_id,
        source_event_ids=[s.source_event_id for s in sources],
        derived_at=derived_at,
        classification=classify(combined, language),
        observations=observations,
        locations=locations,
        victim_count=count,
        conflicts=conflicts,
        language=language,
    )

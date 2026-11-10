"""Language detection and provisional domain/subtype classification."""

import re
from collections import Counter
from dataclasses import dataclass
from functools import cache

from ntip.parser.context import analyse
from ntip.parser.lexicon import (
    DOMAIN_KEYWORDS,
    DOMAIN_PRECEDENCE,
    LANGUAGE_MARKERS,
    SUBTYPES,
)
from ntip.parser.text import find_all, phrase_pattern
from ntip.schema.canonical import Classification, IncidentDomain, Polarity, Temporality

SUPPORTED_LANGUAGES = ("en", "es")


@cache
def _pattern(phrases: tuple[str, ...]) -> re.Pattern[str]:
    return phrase_pattern(phrases)


def _hits(text: str, phrases: list[str]) -> list[str]:
    return [m.text for m in find_all(_pattern(tuple(phrases)), text)]


def detect_language(text: str) -> str | None:
    """'en', 'es', or None when there is no signal either way."""
    scores = {lang: len(_hits(text, markers)) for lang, markers in LANGUAGE_MARKERS.items()}
    if scores["es"] == 0 and scores["en"] == 0:
        return None
    # Spanish markers are more specific than English function words, so Spanish
    # wins ties once there is more than one Spanish hit.
    if scores["es"] > scores["en"] or (scores["es"] == scores["en"] and scores["es"] >= 2):
        return "es"
    return "en"


def _languages(language: str | None) -> list[str]:
    # English phrases are always checked; Spanish ones when Spanish is detected.
    return ["en", "es"] if language == "es" else ["en"]


def _counts(text: str, phrases: list[str]) -> int:
    """Matches that are neither negated nor merely hypothetical."""
    count = 0
    for match in find_all(_pattern(tuple(phrases)), text):
        context = analyse(text, match)
        if context.polarity is Polarity.NEGATED:
            continue
        if context.temporality is Temporality.HYPOTHETICAL:
            continue
        count += 1
    return count


@dataclass(frozen=True)
class DomainScores:
    scores: dict[IncidentDomain, int]

    @property
    def total(self) -> int:
        return sum(self.scores.values())


def domain_scores(text: str, language: str | None) -> DomainScores:
    scores: Counter[IncidentDomain] = Counter()
    for domain, by_language in DOMAIN_KEYWORDS.items():
        for lang in _languages(language):
            scores[domain] += _counts(text, by_language.get(lang, []))
    # A hazardous-materials call often mentions fire words ("gas", "fumes");
    # do not let those outvote the hazmat signal.
    if scores[IncidentDomain.HAZMAT]:
        scores[IncidentDomain.FIRE] = max(
            0, scores[IncidentDomain.FIRE] - scores[IncidentDomain.HAZMAT]
        )
    return DomainScores({d: scores[d] for d in DOMAIN_PRECEDENCE})


def classify(text: str, language: str | None) -> Classification:
    result = domain_scores(text, language)
    best = max(result.scores.values(), default=0)
    if best == 0:
        return Classification(domain=IncidentDomain.UNKNOWN, heuristic_confidence=0.1)

    # Ties are broken by DOMAIN_PRECEDENCE (scene safety first).
    domain = next(d for d in DOMAIN_PRECEDENCE if result.scores[d] == best)
    share = best / result.total
    # One unopposed hit lands near 0.6; a dominant, well-supported domain
    # approaches 0.9. Heuristic only, never a probability.
    support = min(1.0, best / 4)
    confidence = round(min(0.9, 0.3 + 0.4 * share + 0.2 * support), 3)
    return Classification(
        domain=domain,
        subtype=classify_subtype(text, domain),
        heuristic_confidence=confidence,
    )


def classify_subtype(text: str, domain: IncidentDomain) -> str | None:
    for subtype, phrases in SUBTYPES.get(domain, {}).items():
        if _counts(text, phrases):
            return subtype
    return None

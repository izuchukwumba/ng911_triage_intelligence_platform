"""Verify model candidates against the source before they are used.

A candidate is accepted only if its source event is part of the request, its
span lies inside that text, the span quotes exactly the evidence it claims,
and its code is one the platform knows. Anything else is unsupported and is
rejected, never repaired (design v1.2, section 3A.6: "no fabricated facts").
"""

from collections.abc import Mapping
from dataclasses import dataclass

from ntip.ml.contract import Candidate, InferenceResponse
from ntip.parser.lexicon import OBSERVATION_CUES
from ntip.schema.base import Evidence
from ntip.schema.canonical import Extractor, ExtractorKind, Observation

KNOWN_CODES = frozenset(OBSERVATION_CUES)


@dataclass(frozen=True)
class Rejection:
    candidate: Candidate
    reason: str


@dataclass(frozen=True)
class Verified:
    observations: list[Observation]
    rejections: list[Rejection]


def _problem(candidate: Candidate, sources: Mapping[str, str]) -> str | None:
    text = sources.get(candidate.source_event_id)
    if text is None:
        return "unknown source event"
    if candidate.code not in KNOWN_CODES:
        return f"unknown code {candidate.code}"
    if candidate.span.end > len(text):
        return "span outside the source text"
    if text[candidate.span.start : candidate.span.end] != candidate.evidence_text:
        return "evidence text does not match the source span"
    return None


def verify(response: InferenceResponse, sources: Mapping[str, str]) -> Verified:
    """Split candidates into verified observations and rejections.

    ``sources`` maps source event id to its text. Verified observations are
    marked as model-extracted, carry the model's version, and keep the
    model's score as ``heuristic_confidence`` (it is not a probability).
    """
    extractor = Extractor(
        kind=ExtractorKind.MODEL, extractor_id=response.model_id, version=response.model_version
    )
    observations: list[Observation] = []
    rejections: list[Rejection] = []
    for i, candidate in enumerate(response.candidates, 1):
        problem = _problem(candidate, sources)
        if problem:
            rejections.append(Rejection(candidate, problem))
            continue
        observations.append(
            Observation(
                observation_id=f"obs_m{i}",
                code=candidate.code,
                polarity=candidate.polarity,
                temporality=candidate.temporality,
                evidence=Evidence(
                    source_event_id=candidate.source_event_id,
                    span=candidate.span,
                    text=candidate.evidence_text,
                ),
                extractor=extractor,
                heuristic_confidence=candidate.confidence,
            )
        )
    return Verified(observations, rejections)

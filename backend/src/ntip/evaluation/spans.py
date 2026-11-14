"""Evidence-span and cue-status metrics (ML layer design, sections 4.1 and 9).

Scored only on cases that carry label schema 2.0 cue annotations with
evidence (generator 2.x, and adjudicated labels once they exist). Author
labels without spans are not scored here, so every earlier report is
unchanged.

A *mention* is one cue code in one case, whatever its status: a system that
says "no fire" mentions ``FIRE_REPORTED`` as negated. The gold side has one
mention per annotated code. A system may quote several stretches for a code;
the one overlapping the gold span, if any, is the one scored.

- **Span exact**: the system quotes exactly the gold characters.
- **Span overlap**: the system's quote shares at least one character with
  the gold span, in the same message.
- Precision is over the system's mentions, recall over the gold mentions.
- **Status accuracy**: over codes both sides mention, whether the system's
  status (affirmed, uncertain, negated, historical, hypothetical) equals the
  label's. The systems have no "retracted" status, so a retracted label
  always counts as a status error; that is reported, not hidden.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ntip.evaluation.dataset import CueStatus, EvalCase
from ntip.evaluation.metrics import PRF, confusion, rate
from ntip.schema.canonical import Incident, Observation, Polarity, Temporality

STATUSES = [s.value for s in CueStatus]


@dataclass(frozen=True)
class Mention:
    code: str
    status: str
    message: int
    start: int
    end: int

    def overlaps(self, other: "Mention") -> bool:
        return self.message == other.message and self.start < other.end and other.start < self.end

    def same_span(self, other: "Mention") -> bool:
        return (self.message, self.start, self.end) == (other.message, other.start, other.end)


def observation_status(observation: Observation) -> str:
    """The label-schema status a system's observation corresponds to."""
    if observation.temporality is Temporality.HISTORICAL:
        return CueStatus.HISTORICAL.value
    if observation.temporality is Temporality.HYPOTHETICAL:
        return CueStatus.HYPOTHETICAL.value
    if observation.polarity is Polarity.NEGATED:
        return CueStatus.NEGATED.value
    if observation.polarity is Polarity.UNCERTAIN:
        return CueStatus.UNCERTAIN.value
    return CueStatus.AFFIRMED.value


def predicted_mentions(incident: Incident, source_ids: Sequence[str]) -> list[Mention]:
    """Every observation that quotes one of the case's messages."""
    index = {source_id: i for i, source_id in enumerate(source_ids)}
    return [
        Mention(
            o.code,
            observation_status(o),
            index[o.evidence.source_event_id],
            o.evidence.span.start,
            o.evidence.span.end,
        )
        for o in incident.observations
        if o.evidence.source_event_id in index
    ]


def gold_mentions(case: EvalCase) -> list[Mention] | None:
    """None when the case has no evidence spans to score against."""
    annotations = case.labels.cue_annotations
    if not annotations or any(a.evidence is None for a in annotations):
        return None
    return [
        Mention(a.code, a.status.value, a.evidence.message, a.evidence.start, a.evidence.end)
        for a in annotations
        if a.evidence is not None
    ]


@dataclass
class _Scored:
    """One case's comparison, ready to be counted or resampled."""

    gold: int
    predicted: int
    exact: int
    overlap: int
    statuses: list[tuple[str, str]]  # (gold, predicted) for codes both mention


def _compare(gold: list[Mention], predicted: list[Mention], relevant: set[str]) -> _Scored:
    gold = [g for g in gold if g.code in relevant]
    by_code: dict[str, list[Mention]] = {}
    for p in predicted:
        if p.code in relevant:
            by_code.setdefault(p.code, []).append(p)
    exact = overlap = 0
    statuses = []
    for g in gold:
        candidates = by_code.get(g.code, [])
        if not candidates:
            continue
        best = next((p for p in candidates if p.overlaps(g)), candidates[0])
        exact += any(p.same_span(g) for p in candidates)
        overlap += best.overlaps(g)
        statuses.append((g.status, best.status))
    return _Scored(len(gold), len(by_code), exact, overlap, statuses)


def score_spans(
    pairs: Sequence[tuple[EvalCase, list[Mention]]], relevant: set[str], *, seed: int
) -> dict[str, Any] | None:
    """Span and status metrics over the annotated cases; None if there are none."""
    scored = []
    for case, predicted in pairs:
        labelled = gold_mentions(case)
        if labelled is not None:
            scored.append(_compare(labelled, predicted, relevant))
    if not scored:
        return None
    gold = sum(s.gold for s in scored)
    n_predicted = sum(s.predicted for s in scored)
    exact = sum(s.exact for s in scored)
    overlap = sum(s.overlap for s in scored)
    statuses = [pair for s in scored for pair in s.statuses]
    return {
        "annotated_cases": len(scored),
        "gold_mentions": gold,
        "predicted_mentions": n_predicted,
        "span_exact": PRF(exact, n_predicted - exact, gold - exact).as_dict(),
        "span_overlap": PRF(overlap, n_predicted - overlap, gold - overlap).as_dict(),
        "status_accuracy": rate([g == p for g, p in statuses], seed=seed).as_dict(),
        "status_confusion": confusion(statuses, STATUSES),
    }

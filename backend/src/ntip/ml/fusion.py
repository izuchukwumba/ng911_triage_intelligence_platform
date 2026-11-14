"""Combine the rules baseline with verified model hypotheses.

Design v1.2, sections 3A.3 and 3A.6:

- ``rules_only``: the rules incident, unchanged.
- ``ml_shadow``: the rules incident, unchanged; the model output is recorded
  elsewhere for evaluation and is never shown or used.
- ``hybrid_review``: the rules observations plus every verified model
  observation. A model never removes or overrides a rules finding. When the
  two disagree about a cue (one found it live, the other did not), both are
  kept and a MODEL_RULE_DISAGREEMENT conflict sends it to a human, so a
  critical signal is never averaged away.

If the model failed, the result is the rules incident marked ``degraded``.

Fusion policies are versioned and recorded on the incident (ML layer design 7):

- **1.0.0** (default): every verified model observation is added, as above.
- **2.0.0**: as 1.0.0, except that a cue **only the model reports as live**,
  and that is **not critical**, is held back from the record and listed as a
  suggestion with its evidence. It does not change priority and raises no
  review action. A critical cue the model alone found is still added, so it
  still raises priority, and its disagreement conflict still asks a human to
  confirm it: a critical signal is never held back. A model never removes or
  overrides a rules finding under either policy.
"""

from functools import cache

from ntip.ml.verify import Verified
from ntip.schema.advisory import SeverityBand
from ntip.schema.canonical import (
    Conflict,
    ConflictKind,
    Incident,
    InferenceInfo,
    InferenceMode,
    InferenceStatus,
    ModelSuggestion,
    Observation,
    Polarity,
    Temporality,
)
from ntip.triage.ruleset import DEFAULT_RULESET, load_ruleset

FUSION_POLICIES = ("1.0.0", "2.0.0")
DEFAULT_FUSION_POLICY = "1.0.0"


@cache
def critical_codes(ruleset_name: str = DEFAULT_RULESET) -> frozenset[str]:
    """Codes that make an incident critical on their own in the ruleset."""
    return frozenset(
        code
        for rule in load_ruleset(ruleset_name).rules
        if rule.severity is SeverityBand.CRITICAL and len(rule.all_of) == 1
        for code in rule.all_of
    )


def _live(o: Observation) -> bool:
    return o.polarity is not Polarity.NEGATED and o.temporality is Temporality.CURRENT


def _disagreements(
    rules: list[Observation], model: list[Observation], abstained: set[str], start: int
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    codes = {o.code for o in rules + model}
    for code in sorted(codes):
        if code in abstained:
            continue
        rules_live = [o.observation_id for o in rules if o.code == code and _live(o)]
        model_live = [o.observation_id for o in model if o.code == code and _live(o)]
        if bool(rules_live) == bool(model_live):
            continue
        conflicts.append(
            Conflict(
                conflict_id=f"conf_{start + len(conflicts)}",
                kind=ConflictKind.MODEL_RULE_DISAGREEMENT,
                code=code,
                observation_ids=rules_live or model_live,
            )
        )
    return conflicts


def fuse(
    rules_incident: Incident,
    mode: InferenceMode,
    *,
    verified: Verified | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    abstained_codes: list[str] | None = None,
    failure: str | None = None,
    policy: str = DEFAULT_FUSION_POLICY,
    critical: frozenset[str] | None = None,
) -> Incident:
    if policy not in FUSION_POLICIES:
        raise ValueError(f"unknown fusion policy {policy!r}; known: {FUSION_POLICIES}")
    abstained = sorted(set(abstained_codes or []))
    if mode is InferenceMode.RULES_ONLY:
        info = InferenceInfo(mode=mode, status=InferenceStatus.DISABLED)
        return rules_incident.model_copy(update={"inference": info})

    if failure is not None or verified is None:
        info = InferenceInfo(
            mode=mode,
            status=InferenceStatus.DEGRADED,
            model_id=model_id,
            model_version=model_version,
            detail=failure or "no model output",
        )
        return rules_incident.model_copy(update={"inference": info})

    info = InferenceInfo(
        mode=mode,
        status=InferenceStatus.OK,
        model_id=model_id,
        model_version=model_version,
        accepted_candidates=len(verified.observations),
        rejected_candidates=len(verified.rejections),
        abstained_codes=abstained,
    )
    if mode is InferenceMode.ML_SHADOW:
        return rules_incident.model_copy(update={"inference": info})

    added = list(verified.observations)
    if policy != "1.0.0":
        critical = critical_codes() if critical is None else critical
        rules_live = {o.code for o in rules_incident.observations if _live(o)}
        held = [
            o for o in added if _live(o) and o.code not in rules_live and o.code not in critical
        ]
        added = [o for o in added if o not in held]
        info = info.model_copy(
            update={
                "fusion_policy": policy,
                "suggestions": [
                    ModelSuggestion(
                        code=o.code,
                        evidence=o.evidence,
                        heuristic_confidence=o.heuristic_confidence,
                    )
                    for o in held
                ],
            }
        )

    conflicts = _disagreements(
        rules_incident.observations,
        added,
        set(abstained),
        start=len(rules_incident.conflicts) + 1,
    )
    # Re-validate through the model constructor so references are checked.
    return Incident.model_validate(
        {
            **rules_incident.model_dump(),
            "observations": [o.model_dump() for o in rules_incident.observations]
            + [o.model_dump() for o in added],
            "conflicts": [c.model_dump() for c in rules_incident.conflicts + conflicts],
            "inference": info.model_dump(),
        }
    )

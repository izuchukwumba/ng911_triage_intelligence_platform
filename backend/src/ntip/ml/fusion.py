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
"""

from ntip.ml.verify import Verified
from ntip.schema.canonical import (
    Conflict,
    ConflictKind,
    Incident,
    InferenceInfo,
    InferenceMode,
    InferenceStatus,
    Observation,
    Polarity,
    Temporality,
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
) -> Incident:
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

    conflicts = _disagreements(
        rules_incident.observations,
        verified.observations,
        set(abstained),
        start=len(rules_incident.conflicts) + 1,
    )
    # Re-validate through the model constructor so references are checked.
    return Incident.model_validate(
        {
            **rules_incident.model_dump(),
            "observations": [o.model_dump() for o in rules_incident.observations]
            + [o.model_dump() for o in verified.observations],
            "conflicts": [c.model_dump() for c in rules_incident.conflicts + conflicts],
            "inference": info.model_dump(),
        }
    )

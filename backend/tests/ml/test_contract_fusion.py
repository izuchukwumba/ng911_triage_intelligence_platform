from datetime import UTC, datetime
from typing import Any

import pytest

from ntip.ml.contract import Candidate, InferenceResponse
from ntip.ml.fusion import fuse
from ntip.ml.verify import verify
from ntip.parser.parser import parse
from ntip.schema.advisory import ReviewAction
from ntip.schema.base import SourceSpan
from ntip.schema.canonical import (
    ConflictKind,
    ExtractorKind,
    Incident,
    InferenceMode,
    InferenceStatus,
    provenance_errors,
)
from ntip.schema.source import SourceEvent
from ntip.triage.engine import assess

AT = datetime(2026, 11, 9, 12, tzinfo=UTC)
# Misspelled, so the rules parser cannot see the cue; a model might.
TEXT = "My father is not breathign and I can't wake him. We are at 12 Oak Street."


def source(text: str = TEXT) -> SourceEvent:
    return SourceEvent.from_text(
        source_event_id="evt_1", incident_id="inc_1", received_at=AT, text=text
    )


def candidate(phrase: str, cue: str, text: str = TEXT, **overrides: Any) -> Candidate:
    start = text.index(phrase)
    fields: dict[str, Any] = {
        "code": cue,
        "polarity": "affirmed",
        "source_event_id": "evt_1",
        "span": SourceSpan(start=start, end=start + len(phrase)),
        "evidence_text": phrase,
        "confidence": 0.9,
    }
    return Candidate(**{**fields, **overrides})


def response(*candidates: Candidate, **overrides: Any) -> InferenceResponse:
    fields: dict[str, Any] = {"request_id": "req_1", "model_id": "fake-model",
                              "model_version": "0.1.0", "candidates": list(candidates),
                              "runtime_ms": 3.0}  # fmt: skip
    return InferenceResponse(**{**fields, **overrides})


def rules_incident(text: str = TEXT) -> Incident:
    return parse([source(text)], derived_at=AT)


class TestVerify:
    def test_accepts_a_grounded_candidate_as_model_observation(self) -> None:
        result = verify(response(candidate("not breathign", "NOT_BREATHING")), {"evt_1": TEXT})
        [obs] = result.observations
        assert obs.extractor.kind is ExtractorKind.MODEL
        assert obs.extractor.version == "0.1.0"
        assert obs.heuristic_confidence == 0.9
        assert result.rejections == []

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"evidence_text": "not breathing"}, "does not match"),  # fabricated quote
            ({"span": SourceSpan(start=500, end=510)}, "outside"),
            ({"source_event_id": "evt_9"}, "unknown source"),
            ({"code": "TELEPORTATION"}, "unknown code"),
        ],
    )
    def test_rejects_unsupported_candidates(self, overrides: dict[str, Any], reason: str) -> None:
        bad = candidate("not breathign", "NOT_BREATHING", **overrides)
        result = verify(response(bad), {"evt_1": TEXT})
        assert result.observations == []
        assert reason in result.rejections[0].reason


class TestFusion:
    def test_rules_only_ignores_the_model(self) -> None:
        fused = fuse(rules_incident(), InferenceMode.RULES_ONLY)
        assert fused.inference is not None
        assert fused.inference.status is InferenceStatus.DISABLED
        assert fused.observations == rules_incident().observations

    def test_shadow_records_but_does_not_use_model_output(self) -> None:
        verified = verify(response(candidate("not breathign", "NOT_BREATHING")), {"evt_1": TEXT})
        fused = fuse(rules_incident(), InferenceMode.ML_SHADOW, verified=verified,
                     model_id="fake-model", model_version="0.1.0")  # fmt: skip
        assert fused.observations == rules_incident().observations
        assert fused.inference is not None
        assert (fused.inference.status, fused.inference.accepted_candidates) == ("ok", 1)

    def test_failure_degrades_visibly_to_rules(self) -> None:
        fused = fuse(rules_incident(), InferenceMode.HYBRID_REVIEW, failure="timeout after 2s")
        assert fused.inference is not None
        assert fused.inference.status is InferenceStatus.DEGRADED
        assert fused.inference.detail == "timeout after 2s"
        assert fused.observations == rules_incident().observations

    def test_hybrid_adds_model_findings_and_flags_disagreement(self) -> None:
        verified = verify(response(candidate("not breathign", "NOT_BREATHING")), {"evt_1": TEXT})
        fused = fuse(rules_incident(), InferenceMode.HYBRID_REVIEW, verified=verified,
                     model_id="fake-model", model_version="0.1.0")  # fmt: skip

        model_obs = [o for o in fused.observations if o.extractor.kind is ExtractorKind.MODEL]
        assert [o.code for o in model_obs] == ["NOT_BREATHING"]
        disagreements = [
            c for c in fused.conflicts if c.kind is ConflictKind.MODEL_RULE_DISAGREEMENT
        ]
        assert {c.code for c in disagreements} >= {"NOT_BREATHING"}
        assert provenance_errors(fused, {"evt_1": source()}) == []

    def test_hybrid_never_removes_a_rules_finding(self) -> None:
        text = "He is not breathing at 12 Oak Street."
        rules = rules_incident(text)
        fused = fuse(rules, InferenceMode.HYBRID_REVIEW, verified=verify(response(), {}),
                     model_id="m", model_version="1")  # fmt: skip
        assert [o for o in fused.observations if o.extractor.kind is ExtractorKind.RULE] == (
            rules.observations
        )
        # The model missed what the rules found: that is a disagreement too.
        [conflict] = fused.conflicts
        assert (conflict.kind, conflict.code) == (
            ConflictKind.MODEL_RULE_DISAGREEMENT,
            "NOT_BREATHING",
        )

    def test_abstained_codes_are_not_disagreements(self) -> None:
        text = "He is not breathing at 12 Oak Street."
        fused = fuse(
            rules_incident(text),
            InferenceMode.HYBRID_REVIEW,
            verified=verify(response(), {}),
            model_id="m",
            model_version="1",
            abstained_codes=["NOT_BREATHING"],
        )
        assert fused.conflicts == []
        assert fused.inference is not None
        assert fused.inference.abstained_codes == ["NOT_BREATHING"]


def test_model_only_serious_cue_raises_severity_but_needs_confirmation() -> None:
    rules_assessment = assess(rules_incident(), assessment_id="a", assessed_at=AT)
    verified = verify(response(candidate("not breathign", "NOT_BREATHING")), {"evt_1": TEXT})
    fused = fuse(rules_incident(), InferenceMode.HYBRID_REVIEW, verified=verified,
                 model_id="fake-model", model_version="0.1.0")  # fmt: skip
    hybrid = assess(fused, assessment_id="a", assessed_at=AT)

    assert rules_assessment.severity_band != "critical"  # the misspelling hid the cue
    assert hybrid.severity_band == "critical"
    assert ReviewAction.CONFIRM_CRITICAL_REPORT in hybrid.review_actions
    assert ReviewAction.RESOLVE_CONFLICT in hybrid.review_actions
    assert any(r.rule_id == "P-REVIEW-006" for r in hybrid.reasons)


class TestFusionPolicy2:
    """Fusion 2.0.0: non-critical model-only cues are suggestions (ML layer design 7)."""

    FALL = "She fell on the sidewalk and her hip hurts. We are at 12 Oak Street."

    def _fused(self, text: str, *candidates: Candidate, policy: str) -> Incident:
        verified = verify(response(*candidates), {"evt_1": text})
        return fuse(
            rules_incident(text),
            InferenceMode.HYBRID_REVIEW,
            verified=verified,
            model_id="fake-model",
            model_version="0.1.0",
            policy=policy,
        )

    def test_a_non_critical_model_only_cue_is_a_suggestion(self) -> None:
        fall = candidate("fell on the sidewalk", "FALL_FROM_HEIGHT", self.FALL)
        v1 = self._fused(self.FALL, fall, policy="1.0.0")
        v2 = self._fused(self.FALL, fall, policy="2.0.0")
        rules = assess(rules_incident(self.FALL), assessment_id="a", assessed_at=AT)

        assert "FALL_FROM_HEIGHT" in {o.code for o in v1.observations}
        assert v1.inference is not None and v1.inference.fusion_policy is None
        assert "FALL_FROM_HEIGHT" not in {o.code for o in v2.observations}
        assert v2.inference is not None and v2.inference.fusion_policy == "2.0.0"
        [suggestion] = v2.inference.suggestions
        assert suggestion.code == "FALL_FROM_HEIGHT"
        assert suggestion.evidence.text == "fell on the sidewalk"
        # Priority is the rules' priority, and no conflict asks for review.
        hybrid = assess(v2, assessment_id="a", assessed_at=AT)
        assert hybrid.advisory_priority == rules.advisory_priority
        assert "FALL_FROM_HEIGHT" not in {c.code for c in v2.conflicts}

    def test_a_critical_model_only_cue_still_raises_priority_for_confirmation(self) -> None:
        fused = self._fused(TEXT, candidate("not breathign", "NOT_BREATHING"), policy="2.0.0")
        hybrid = assess(fused, assessment_id="a", assessed_at=AT)
        assert fused.inference is not None and fused.inference.suggestions == []
        assert hybrid.severity_band == "critical"
        assert ReviewAction.CONFIRM_CRITICAL_REPORT in hybrid.review_actions

    def test_a_cue_the_rules_also_found_is_added_as_before(self) -> None:
        text = "There is smoke in the kitchen. We are at 12 Oak Street."
        fused = self._fused(text, candidate("smoke", "SMOKE_REPORTED", text), policy="2.0.0")
        assert fused.inference is not None and fused.inference.suggestions == []
        assert [o.code for o in fused.observations].count("SMOKE_REPORTED") == 2

    def test_an_unknown_policy_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown fusion policy"):
            fuse(rules_incident(), InferenceMode.HYBRID_REVIEW, policy="9.9.9")

"""Label schema 2.0: cue statuses, evidence spans and location components."""

import json
from pathlib import Path
from typing import Any

import pytest

from ntip.evaluation.dataset import (
    CaseUncertainty,
    CueStatus,
    EvalCase,
    TextSpan,
    dump_case,
    load_dataset,
)
from ntip.evaluation.runner import REPO_ROOT

MESSAGE = (
    "He was not breathing earlier but he is breathing now. There's no fire. We're at 9 Pine Road."
)


def case(**labels: Any) -> dict[str, Any]:
    return {
        "case_id": "a", "split": "dev", "family": "f", "messages": [MESSAGE],
        "label_source": "author",
        "labels": {"domain": "ems", "severity": "elevated", "priority": "P2",
                   "location": "present", **labels},
    }  # fmt: skip


def span(quote: str) -> dict[str, Any]:
    return TextSpan.find([MESSAGE], 0, quote).model_dump()


ANNOTATIONS = [
    {"code": "NOT_BREATHING", "status": "historical", "evidence": span("not breathing earlier")},
    {"code": "FIRE_REPORTED", "status": "negated", "evidence": span("no fire")},
]


def test_cue_lists_are_derived_from_annotations() -> None:
    labels = EvalCase.model_validate(case(cue_annotations=ANNOTATIONS)).labels
    assert labels.cues == []
    assert labels.absent_cues == ["FIRE_REPORTED", "NOT_BREATHING"]


@pytest.mark.parametrize(
    ("status", "live"),
    [("affirmed", True), ("uncertain", True), ("negated", False), ("historical", False),
     ("hypothetical", False), ("retracted", False)],
)  # fmt: skip
def test_only_affirmed_and_uncertain_cues_are_live(status: str, live: bool) -> None:
    raw = case(cue_annotations=[{"code": "NOT_BREATHING", "status": status}])
    labels = EvalCase.model_validate(raw).labels
    assert (labels.cues == ["NOT_BREATHING"]) is live
    assert (labels.absent_cues == ["NOT_BREATHING"]) is not live
    assert CueStatus(status) is not None


def test_given_cue_lists_must_agree_with_annotations() -> None:
    with pytest.raises(ValueError, match="disagree"):
        EvalCase.model_validate(case(cue_annotations=ANNOTATIONS, cues=["NOT_BREATHING"]))
    consistent = case(cue_annotations=ANNOTATIONS, absent_cues=["NOT_BREATHING", "FIRE_REPORTED"])
    assert EvalCase.model_validate(consistent).labels.cues == []


def test_a_cue_is_annotated_once() -> None:
    twice = [ANNOTATIONS[0], {**ANNOTATIONS[0], "status": "affirmed"}]
    with pytest.raises(ValueError, match="only once"):
        EvalCase.model_validate(case(cue_annotations=twice))


def test_evidence_must_match_the_message_exactly() -> None:
    wrong = {**span("no fire"), "text": "no fira"}
    annotation = {"code": "FIRE_REPORTED", "status": "negated", "evidence": wrong}
    with pytest.raises(ValueError, match="does not match"):
        EvalCase.model_validate(case(cue_annotations=[annotation]))
    missing_message = {**span("no fire"), "message": 3}
    with pytest.raises(ValueError, match="does not exist"):
        EvalCase.model_validate(
            case(cue_annotations=[{"code": "FIRE_REPORTED", "status": "negated",
                                   "evidence": missing_message}])
        )  # fmt: skip


def test_a_span_must_fit_its_text() -> None:
    with pytest.raises(ValueError, match="does not fit"):
        TextSpan(message=0, start=0, end=3, text="He was")


def test_find_is_exact_and_never_fuzzy() -> None:
    assert TextSpan.find([MESSAGE], 0, "9 Pine Road").start == MESSAGE.index("9 Pine Road")
    with pytest.raises(ValueError, match="verbatim"):
        TextSpan.find([MESSAGE], 0, "9 pine road")


def test_location_components_are_checked() -> None:
    components = {"house_number": span("9"), "street": span("Pine Road")}
    labels = EvalCase.model_validate(case(location_components=components)).labels
    assert labels.location_components is not None
    assert set(labels.location_components.spans()) == {"house_number", "street"}
    with pytest.raises(ValueError, match="street"):
        EvalCase.model_validate(
            case(location_components={"street": {**span("Pine Road"), "text": "Pine Lane"}})
        )


def test_a_v2_case_round_trips(tmp_path: Path) -> None:
    raw = case(cue_annotations=ANNOTATIONS, case_uncertainty="clear",
               location_components={"street": span("Pine Road")})  # fmt: skip
    path = tmp_path / "cases.jsonl"
    path.write_text(dump_case(EvalCase.model_validate(raw)) + "\n", encoding="utf-8")
    [loaded] = load_dataset(path).cases
    assert loaded.labels.case_uncertainty is CaseUncertainty.CLEAR
    assert loaded == EvalCase.model_validate(raw)


def test_existing_datasets_load_unchanged() -> None:
    for name in ("curated.jsonl", "generated-1.0.0-seed42.jsonl"):
        path = REPO_ROOT / "data" / "eval" / name
        dataset = load_dataset(path)
        assert all(c.labels.cue_annotations is None for c in dataset.cases)
        # Re-serialising v1 records adds no schema 2.0 field.
        v2 = {"cue_annotations", "location_components", "case_uncertainty"}
        assert all(not v2 & json.loads(dump_case(c))["labels"].keys() for c in dataset.cases)

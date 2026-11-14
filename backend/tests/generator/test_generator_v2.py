"""Generator 2.0: coverage, evidence spans and reproducibility."""

from collections import Counter

import pytest

from ntip.evaluation.dataset import LIVE_STATUSES, EvalCase, LabelSource, load_dataset
from ntip.generator.__main__ import path_for, render
from ntip.generator.generate_v2 import GENERATOR_VERSION, generate, marked_codes
from ntip.generator.scenarios_v2 import SITUATIONS
from ntip.parser.lexicon import OBSERVATION_CUES

N, SEED = 2010, 42


@pytest.fixture(scope="module")
def cases() -> list[EvalCase]:
    return list(generate(N, SEED))


def test_every_phrasing_marks_exactly_its_family_cues() -> None:
    for s in SITUATIONS:
        for template in (*s.phrasings, *s.spanish, s.denial or "", s.past or ""):
            if template:
                marked = marked_codes(template)
                assert sorted(marked) == sorted(s.cues), (s.family, template)


def test_families_are_broad_and_cover_every_code_in_training_and_test() -> None:
    assert len(SITUATIONS) >= 60
    assert all(len(s.phrasings) >= 3 for s in SITUATIONS)
    train = {c for s in SITUATIONS if s.split.value != "test" for c in s.cues}
    test = {c for s in SITUATIONS if s.split.value == "test" for c in s.cues}
    assert train == test
    # Caller-state codes are not labelled; child and several people come from perturbations.
    unlabelled = {"CALLER_HIGH_DISTRESS", "CALLER_LOCATION_UNKNOWN", "POSSIBLE_PRANK"}
    labelled = set(OBSERVATION_CUES) - unlabelled - {"CHILD_INVOLVED", "MULTIPLE_VICTIMS"}
    assert train == labelled


def test_same_seed_same_cases(cases: list[EvalCase]) -> None:
    assert list(generate(50, SEED)) == cases[:50]
    assert list(generate(50, SEED + 1)) != cases[:50]


def test_every_cue_has_evidence_that_matches_the_text(cases: list[EvalCase]) -> None:
    for case in cases:
        assert case.label_source is LabelSource.GENERATOR
        annotations = case.labels.cue_annotations or []
        assert {a.code for a in annotations} == set(case.labels.cues) | set(case.labels.absent_cues)
        for a in annotations:
            assert a.evidence is not None, (case.case_id, a.code)
            # EvalCase validation already checks the span against the message.
            assert a.evidence.text.strip() == a.evidence.text


def test_statuses_follow_the_variant(cases: list[EvalCase]) -> None:
    for case in cases:
        statuses = {a.code: a.status.value for a in case.labels.cue_annotations or []}
        family_codes = {a.code for a in case.labels.cue_annotations or []} - {
            "CHILD_INVOLVED", "MULTIPLE_VICTIMS", "INJURY_REPORTED"}  # fmt: skip
        if "negated" in case.notes:
            assert {statuses[c] for c in family_codes} <= {"negated"}
            assert case.labels.severity in ("low", "elevated")
        if "past" in case.notes:
            assert {statuses[c] for c in family_codes} <= {"historical"}
        if "uncertain" in case.notes and statuses:  # families without cues have none
            assert "uncertain" in statuses.values()
        live = {a.code for a in case.labels.cue_annotations or [] if a.status in LIVE_STATUSES}
        assert live == set(case.labels.cues)


def test_location_components_match_the_location_label(cases: list[EvalCase]) -> None:
    for case in cases:
        components = case.labels.location_components
        if case.labels.location == "missing":
            assert components is None
        if case.labels.location == "conflicting":
            assert components is not None
            assert all(s.message == 1 for s in components.spans().values())


def test_covers_the_perturbations(cases: list[EvalCase]) -> None:
    variants = Counter(v for c in cases for v in c.notes.split("; ")[1].split(", "))
    for name in ("plain", "child", "negated", "past", "uncertain", "second_hand", "multiple",
                 "corrected_address", "disfluent", "misspelled", "spanish",
                 "speech_recognition"):  # fmt: skip
        assert variants[name] > 10, name


def test_committed_dataset_matches_the_generator() -> None:
    path = path_for(SEED, GENERATOR_VERSION)
    assert path.read_text("utf-8").replace("\r\n", "\n") == render(N, SEED, GENERATOR_VERSION), (
        "Regenerate with `python -m ntip.generator --generator 2.0.0 --n 2010 --seed 42`."
    )
    dataset = load_dataset(path)  # also rejects family leakage and bad spans
    assert len(dataset.cases) == N

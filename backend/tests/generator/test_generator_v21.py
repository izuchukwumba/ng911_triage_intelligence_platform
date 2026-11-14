"""Generator 2.1: the four additions, and that generator 2.0 is unchanged."""

import re
from collections import Counter

import pytest

from ntip.evaluation.dataset import LIVE_STATUSES, CueStatus, EvalCase, Split, load_dataset
from ntip.generator.__main__ import path_for, render
from ntip.generator.generate_v2 import marked_codes
from ntip.generator.generate_v21 import GENERATOR_VERSION, generate
from ntip.generator.scenarios import ADULTS, CHILDREN
from ntip.generator.scenarios_v21 import (
    NEW_SITUATIONS,
    PRONOUNS,
    REASSURANCES,
    SITUATIONS,
    SPANISH_KIN,
)

N, SEED = 2010, 42


@pytest.fixture(scope="module")
def cases() -> list[EvalCase]:
    return list(generate(N, SEED))


def _variants(case: EvalCase) -> list[str]:
    return case.notes.split("; ")[1].split(", ")


def test_new_phrasings_mark_exactly_their_cues() -> None:
    for s in NEW_SITUATIONS:
        for template in (*s.phrasings, *s.spanish, s.denial or "", s.past or ""):
            if template:
                assert sorted(marked_codes(template)) == sorted(s.cues), (s.family, template)
    for r in REASSURANCES:
        for template in r.phrasings:
            assert marked_codes(template) == [r.code], template


def test_every_person_has_a_pronoun() -> None:
    assert set(PRONOUNS) == set(ADULTS) | set(CHILDREN)


def test_family_names_are_unique() -> None:
    families = [s.family for s in SITUATIONS]
    assert len(families) == len(set(families))


def test_reassurances_are_negated_and_never_contradict_a_live_cue(cases: list[EvalCase]) -> None:
    reassured = [c for c in cases if "reassured" in _variants(c)]
    assert len(reassured) > 100
    codes: Counter[str] = Counter()
    for case in reassured:
        annotations = case.labels.cue_annotations or []
        negated = [a for a in annotations if a.status is CueStatus.NEGATED]
        assert len(negated) == 1, case.case_id
        codes[negated[0].code] += 1
        assert negated[0].code not in case.labels.cues
        assert {a.code for a in annotations if a.status in LIVE_STATUSES} == set(case.labels.cues)
    assert set(codes) == {r.code for r in REASSURANCES}
    # Training data has each denial, not only test data.
    train = {
        a.code
        for c in reassured
        if c.split is not Split.TEST
        for a in c.labels.cue_annotations or []
        if a.status is CueStatus.NEGATED
    }
    assert train == set(codes)


def test_shouting_is_all_capitals(cases: list[EvalCase]) -> None:
    shouted = [c for c in cases if "shouting" in _variants(c)]
    assert len(shouted) > 50
    assert all(c.messages[0] == c.messages[0].upper() for c in shouted)


def test_not_breathing_appears_alone_in_training(cases: list[EvalCase]) -> None:
    train = [c for c in cases if c.split is not Split.TEST and "NOT_BREATHING" in c.labels.cues]
    alone = [c for c in train if not {"UNCONSCIOUS", "DROWNING"} & set(c.labels.cues)]
    assert len(alone) >= 15
    # And unconscious patients are sometimes reported as breathing.
    assert any(
        "UNCONSCIOUS" in c.labels.cues and "NOT_BREATHING" in c.labels.absent_cues for c in cases
    )


def test_spanish_family_words_vary_and_only_children_are_child_involved(
    cases: list[EvalCase],
) -> None:
    words: Counter[str] = Counter()
    for case in cases:
        if "spanish" not in _variants(case):
            continue
        if m := re.search(r"\b[Mm]i (\w+)", case.messages[0]):
            word = m.group(1)
            words[word] += 1
            is_child = word in ("hijo", "hija", "bebé")
            assert ("CHILD_INVOLVED" in case.labels.cues) == is_child, case.case_id
    kin = set(SPANISH_KIN["m"] + SPANISH_KIN["f"])
    assert len(set(words) & kin) >= 10


def test_same_seed_same_cases(cases: list[EvalCase]) -> None:
    assert list(generate(50, SEED)) == cases[:50]
    assert all(c.case_id.startswith("g21s") for c in cases[:50])


def test_committed_dataset_matches_the_generator() -> None:
    path = path_for(SEED, GENERATOR_VERSION)
    assert path.read_text("utf-8").replace("\r\n", "\n") == render(N, SEED, GENERATOR_VERSION), (
        "Regenerate with `python -m ntip.generator --generator 2.1.0 --n 2010 --seed 42`."
    )
    dataset = load_dataset(path)  # also rejects family leakage and bad spans
    assert len(dataset.cases) == N

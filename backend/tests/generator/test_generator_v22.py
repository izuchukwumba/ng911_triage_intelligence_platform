"""Generator 2.2: every labelled code in dev, regression and test."""

import pytest

from ntip.evaluation.dataset import EvalCase, Split, load_dataset
from ntip.generator.__main__ import path_for, render
from ntip.generator.generate_v2 import marked_codes
from ntip.generator.generate_v22 import GENERATOR_VERSION, generate
from ntip.generator.scenarios_v22 import NEW_SITUATIONS, SITUATIONS
from ntip.parser.lexicon import OBSERVATION_CUES

N, SEED = 2610, 42
# Caller-state codes are not labelled; child and several people come from perturbations.
LABELLED = set(OBSERVATION_CUES) - {
    "CALLER_HIGH_DISTRESS",
    "CALLER_LOCATION_UNKNOWN",
    "POSSIBLE_PRANK",
    "CHILD_INVOLVED",
    "MULTIPLE_VICTIMS",
}


@pytest.fixture(scope="module")
def cases() -> list[EvalCase]:
    return list(generate(N, SEED))


def test_new_phrasings_mark_exactly_their_cues() -> None:
    for s in NEW_SITUATIONS:
        for template in (*s.phrasings, *s.spanish, s.denial or "", s.past or ""):
            if template:
                assert sorted(marked_codes(template)) == sorted(s.cues), (s.family, template)
            if not s.personal:
                assert "{who}" not in template.lower(), (s.family, template)


def test_every_labelled_code_is_in_every_split() -> None:
    families = [s.family for s in SITUATIONS]
    assert len(families) == len(set(families))
    for split in Split:
        codes = {c for s in SITUATIONS if s.split is split for c in s.cues}
        assert codes == LABELLED, (split.value, sorted(LABELLED - codes))


def test_every_code_has_enough_calls_on_each_training_split(cases: list[EvalCase]) -> None:
    for split in (Split.DEV, Split.REGRESSION):
        for code in LABELLED:
            n = sum(code in c.labels.cues for c in cases if c.split is split)
            assert n >= 15, (split.value, code, n)


def test_same_seed_same_cases(cases: list[EvalCase]) -> None:
    assert list(generate(50, SEED)) == cases[:50]
    assert all(c.case_id.startswith("g22s") for c in cases[:50])


def test_committed_dataset_matches_the_generator() -> None:
    path = path_for(SEED, GENERATOR_VERSION)
    assert path.read_text("utf-8").replace("\r\n", "\n") == render(N, SEED, GENERATOR_VERSION), (
        "Regenerate with `python -m ntip.generator --generator 2.2.0 --n 2610 --seed 42`."
    )
    assert len(load_dataset(path).cases) == N  # also rejects family leakage and bad spans

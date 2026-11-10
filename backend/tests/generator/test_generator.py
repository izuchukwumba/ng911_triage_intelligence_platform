from collections import Counter

from ntip.evaluation.dataset import EvalCase, LabelSource, load_dataset
from ntip.generator.__main__ import path_for, render
from ntip.generator.generate import generate
from ntip.generator.scenarios import SITUATIONS


def cases(n: int = 340, seed: int = 7) -> list[EvalCase]:
    return list(generate(n, seed))


def test_same_seed_same_cases() -> None:
    assert cases(seed=3) == cases(seed=3)
    assert cases(seed=3) != cases(seed=4)


def test_labels_are_marked_as_generator_intended() -> None:
    assert {c.label_source for c in cases()} == {LabelSource.GENERATOR}


def test_every_family_stays_in_one_split() -> None:
    splits: dict[str, set[str]] = {}
    for case in cases():
        splits.setdefault(case.family, set()).add(case.split)
    assert all(len(s) == 1 for s in splits.values())


def test_covers_every_family_and_the_main_perturbations() -> None:
    generated = cases()
    assert {c.family for c in generated} == {s.family for s in SITUATIONS}
    variants = Counter(v for c in generated for v in c.notes.split("; ")[1].split(", "))
    for name in ("plain", "child", "negated", "past", "uncertain", "second_hand", "multiple",
                 "corrected_address", "disfluent", "misspelled", "spanish"):  # fmt: skip
        assert variants[name] > 0, name


def test_label_consistency() -> None:
    for case in cases():
        labels = case.labels
        if "negated" in case.notes or "past" in case.notes:
            assert labels.absent_cues, case.case_id
        if "child" in case.notes:
            assert "CHILD_INVOLVED" in labels.cues
        if labels.location == "conflicting":
            assert len(case.messages) == 2
        if labels.victim_count is not None:
            assert "MULTIPLE_VICTIMS" in labels.cues


def test_committed_dataset_matches_the_generator() -> None:
    path = path_for(42)
    assert path.read_text("utf-8").replace("\r\n", "\n") == render(510, 42), (
        "Regenerate with `python -m ntip.generator --n 510 --seed 42` and commit."
    )
    assert len(load_dataset(path).cases) == 510

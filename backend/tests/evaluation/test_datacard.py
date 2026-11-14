"""Dataset cards: every dataset has one, and its generated section is current."""

from pathlib import Path

import pytest

from ntip.evaluation.datacard import BEGIN, END, cards, render, statistics
from ntip.evaluation.dataset import load_dataset
from ntip.evaluation.runner import REPO_ROOT

DATA = REPO_ROOT / "data" / "eval"


def test_every_dataset_has_an_up_to_date_card() -> None:
    pairs = cards(DATA)
    assert {d.name for d, _ in pairs} == {p.name for p in DATA.glob("*.jsonl")}
    for dataset, card in pairs:
        text = card.read_text("utf-8").replace("\r\n", "\n")
        assert text == render(text, load_dataset(dataset)), (
            f"{card.name} is stale: run `python -m ntip.evaluation.datacard`"
        )
        for heading in ("## Summary", "## How it was made", "## Uses", "## Limitations"):
            assert heading in text, (card.name, heading)


def test_a_dataset_without_a_card_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "new.jsonl").write_text("", "utf-8")
    with pytest.raises(FileNotFoundError, match=r"new.jsonl has no card"):
        cards(tmp_path)


def test_render_replaces_only_the_generated_section() -> None:
    dataset = load_dataset(DATA / "curated.jsonl")
    card = f"# Card\n\nprose\n\n{BEGIN}\nold\n{END}\n\nmore prose\n"
    out = render(card, dataset)
    assert out.startswith("# Card\n\nprose\n\n") and out.endswith(f"{END}\n\nmore prose\n")
    assert statistics(dataset) in out and "old" not in out
    with pytest.raises(ValueError, match="no stats markers"):
        render("# no markers", dataset)

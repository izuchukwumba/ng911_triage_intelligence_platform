"""B1e: training data, the model directory's manifest, and grounded inference.

Training tests build a tiny random encoder locally, so they need no network;
they check the plumbing, not the model's quality. Quality is measured by the
evaluation reports from a real training run. Tests needing PyTorch skip when
the ``ml-encoder`` extra is not installed.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from ntip.ml.b1e import CODES, Example, clause_texts, load_examples, targets
from ntip.ml.contract import InferenceMessage, InferenceRequest


def write_dataset(path: Path) -> Path:
    def case(case_id: str, split: str, text: str, cues: list[str], absent: list[str]) -> str:
        return json.dumps({
            "case_id": case_id, "split": split, "family": case_id, "messages": [text],
            "label_source": "generator",
            "labels": {"domain": "fire", "severity": "elevated", "priority": "P2",
                       "location": "present", "cues": cues, "absent_cues": absent},
        })  # fmt: skip

    lines = [
        case("a", "dev", "The kitchen is on fire. We are at 4 Oak Street.", ["FIRE_REPORTED"], []),
        case("b", "regression", "There is no fire, just a smell of gas.",
             ["HAZARDOUS_ENVIRONMENT"], ["FIRE_REPORTED"]),
        case("c", "dev", "My dad is not breathing!", ["NOT_BREATHING"], []),
        case("t", "test", "Held-out text that must never be trained on.", ["FIRE_REPORTED"], []),
    ]  # fmt: skip
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_training_examples_come_from_dev_and_regression_only(tmp_path: Path) -> None:
    examples, digest = load_examples(write_dataset(tmp_path / "d.jsonl"), ("dev", "regression"))
    assert len(examples) == 3
    assert all("Held-out" not in c for e in examples for c in e.clauses)
    assert digest.startswith("sha256:")
    denial = examples[1]
    assert denial.live == {"HAZARDOUS_ENVIRONMENT"} and denial.absent == {"FIRE_REPORTED"}


def test_clauses_split_a_call() -> None:
    clauses = clause_texts(["The kitchen is on fire, but nobody is hurt. Send help."])
    assert len(clauses) >= 2
    assert all(c == c.strip() and c for c in clauses)


def test_targets_are_live_codes_then_absent_codes() -> None:
    example = Example(["x"], frozenset({"FIRE_REPORTED"}), frozenset({"NOT_BREATHING"}))
    vector = targets(example)
    assert len(vector) == 2 * len(CODES)
    assert vector[CODES.index("FIRE_REPORTED")] == 1.0
    assert vector[len(CODES) + CODES.index("NOT_BREATHING")] == 1.0
    assert sum(vector) == 2.0


# --- needs the ml-encoder extra ---------------------------------------------


@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    from ntip.ml.train_b1e import train

    root = tmp_path_factory.mktemp("b1e")
    base = root / "base"
    base.mkdir()
    words = "the kitchen is on fire we are at oak street there no just a smell of gas my dad not "
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *sorted(set(words.split())), ".", ","]
    (base / "vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")
    transformers.DistilBertTokenizerFast(str(base / "vocab.txt")).save_pretrained(base)
    config = transformers.DistilBertConfig(
        vocab_size=len(vocab), dim=16, n_layers=1, n_heads=2, hidden_dim=32,
        max_position_embeddings=64,
    )  # fmt: skip
    transformers.DistilBertModel(config).save_pretrained(base)

    out = root / "model"
    manifest = train(
        write_dataset(root / "d.jsonl"),
        out,
        base_model=str(base),
        revision=None,
        params={"epochs": 1, "batch_calls": 2},
        device="cpu",
        log=lambda _: None,
    )
    return out, manifest


def test_training_writes_a_manifest_of_every_file(trained: tuple[Path, dict[str, Any]]) -> None:
    out, manifest = trained
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert manifest["training_data"]["calls"] == 3  # the test case was not read
    assert manifest["training_data"]["splits"] == ["dev", "regression"]
    assert manifest["codes"] == list(CODES)
    assert "head.safetensors" in manifest["files"]
    assert any(name.startswith("encoder/") for name in manifest["files"])
    assert manifest["environment"]["device"] == "cpu"


def test_the_model_loads_and_every_candidate_is_grounded(
    trained: tuple[Path, dict[str, Any]],
) -> None:
    from ntip.ml.b1e import B1eModel
    from ntip.ml.verify import verify

    out, manifest = trained
    model = B1eModel(out)
    assert model.model_version == manifest["model_version"]
    text = "The kitchen is on fire. My dad is not breathing."
    request = InferenceRequest(
        request_id="r", incident_id="i",
        messages=[InferenceMessage(source_event_id="e1", text=text)],
    )  # fmt: skip
    response = model.infer(request)
    assert response.calibrated is False
    for candidate in response.candidates:
        assert text[candidate.span.start : candidate.span.end] == candidate.evidence_text
    verified = verify(response, {"e1": text})
    assert verified.rejections == []
    # Deterministic on CPU: the same input gives the same scores.
    assert model.cue_scores(request.messages) == model.cue_scores(request.messages)


def test_a_changed_file_is_refused(trained: tuple[Path, dict[str, Any]], tmp_path: Path) -> None:
    import shutil

    from ntip.ml.b1e import B1eModel, InvalidModel

    out, _ = trained
    copy = tmp_path / "copy"
    shutil.copytree(out, copy)
    head = copy / "head.safetensors"
    head.write_bytes(head.read_bytes() + b"\0")
    with pytest.raises(InvalidModel, match=r"head\.safetensors"):
        B1eModel(copy)
    (copy / "manifest.json").unlink()
    with pytest.raises(InvalidModel, match="manifest"):
        B1eModel(copy)


def test_training_refuses_a_non_empty_output(
    trained: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    from ntip.ml.train_b1e import train

    out, _ = trained
    with pytest.raises(FileExistsError):
        train(write_dataset(tmp_path / "d.jsonl"), out, base_model="unused")


def test_training_reads_only_the_chosen_development_splits(tmp_path: Path) -> None:
    from ntip.ml.train_b1e import train

    for splits in ((), ("test",), ("dev", "test")):
        with pytest.raises(ValueError, match="may read only"):
            train(write_dataset(tmp_path / "d.jsonl"), tmp_path / "m", splits=splits)

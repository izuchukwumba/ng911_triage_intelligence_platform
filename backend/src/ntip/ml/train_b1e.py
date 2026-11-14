"""Train B1e and write a model directory with a manifest.

    python -m ntip.ml.train_b1e --dataset ../data/eval/generated-1.0.0-seed42.jsonl --out b1e

Runs on CPU or a GPU (a free Colab or Kaggle T4 trains it in minutes; see
``notebooks/train_b1e.ipynb``). Only the dev and regression splits are read;
test data never reaches training. Hyperparameters are fixed in advance, and
there is no early stopping on any evaluation data.

The output directory holds the fine-tuned encoder, the scoring head and
``manifest.json``: the base model and revision, the training data digest,
hyperparameters, seed, hardware, library versions, git commit and the sha256
of every file. ``B1eModel`` refuses a directory that does not match it.
"""

import argparse
import json
import platform
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ntip.ml.b1e import (
    BASE_MODEL,
    BASE_REVISION,
    CODES,
    ENCODER_DIR,
    HEAD_FILE,
    MANIFEST,
    MODEL_ID,
    MODEL_SERIES,
    build_scorer,
    file_digests,
    load_examples,
    targets,
    weights_digest,
)

TRAINING_SPLITS = ("dev", "regression")
SEED = 20261113
PARAMS: dict[str, Any] = {
    "epochs": 6,
    "batch_calls": 8,
    "learning_rate": 5e-5,
    "weight_decay": 0.01,
    "warmup_fraction": 0.1,
    "max_length": 64,
}


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def train(
    dataset: Path,
    out: Path,
    *,
    base_model: str = BASE_MODEL,
    revision: str | None = BASE_REVISION,
    params: dict[str, Any] | None = None,
    seed: int = SEED,
    device: str | None = None,
    log: Any = print,
) -> dict[str, Any]:
    import numpy as np
    import torch
    import transformers
    from safetensors.torch import save_file
    from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

    params = {**PARAMS, **(params or {})}
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} is not empty")
    examples, data_digest = load_examples(dataset, TRAINING_SPLITS)
    if not examples:
        raise ValueError(f"no training examples in the {TRAINING_SPLITS} splits of {dataset}")

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(base_model, revision=revision)
    encoder = AutoModel.from_pretrained(base_model, revision=revision)
    scorer = build_scorer(encoder).to(device)
    optimiser = torch.optim.AdamW(
        scorer.parameters(), lr=params["learning_rate"], weight_decay=params["weight_decay"]
    )
    batches_per_epoch = -(-len(examples) // params["batch_calls"])
    steps = batches_per_epoch * params["epochs"]
    schedule = get_linear_schedule_with_warmup(  # type: ignore[no-untyped-call,unused-ignore]
        optimiser, int(steps * params["warmup_fraction"]), steps
    )
    loss_fn = torch.nn.BCEWithLogitsLoss()
    order = random.Random(seed)

    scorer.train()
    started = datetime.now(UTC)
    for epoch in range(params["epochs"]):
        indices = list(range(len(examples)))
        order.shuffle(indices)
        total = 0.0
        for b in range(0, len(indices), params["batch_calls"]):
            batch = [examples[i] for i in indices[b : b + params["batch_calls"]]]
            clauses = [c for e in batch for c in e.clauses]
            inputs = tokenizer(
                clauses,
                padding=True,
                truncation=True,
                max_length=params["max_length"],
                return_tensors="pt",
            ).to(device)
            logits = scorer(**inputs)
            # Multiple-instance pooling: each call's logit is its best clause's.
            pooled, start = [], 0
            for example in batch:
                end = start + len(example.clauses)
                pooled.append(logits[start:end].max(dim=0).values)
                start = end
            target = torch.tensor([targets(e) for e in batch], device=device)
            loss = loss_fn(torch.stack(pooled), target)
            optimiser.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(scorer.parameters(), 1.0)
            optimiser.step()
            schedule.step()
            total += float(loss.detach()) * len(batch)
        log(f"epoch {epoch + 1}/{params['epochs']}: loss {total / len(examples):.4f}")

    out.mkdir(parents=True, exist_ok=True)
    scorer.to("cpu")
    encoder.save_pretrained(out / ENCODER_DIR)
    tokenizer.save_pretrained(out / ENCODER_DIR)
    head: Any = scorer.head
    save_file({k: v.contiguous() for k, v in head.state_dict().items()}, str(out / HEAD_FILE))

    files = file_digests(out)
    digest = weights_digest(files)
    manifest = {
        "model_id": MODEL_ID,
        "model_version": f"{MODEL_SERIES}+{digest.removeprefix('sha256:')[:12]}",
        "base_model": {"id": base_model, "revision": revision},
        "codes": list(CODES),
        "training_data": {
            "path": dataset.name,
            "digest": data_digest,
            "splits": list(TRAINING_SPLITS),
            "calls": len(examples),
        },
        "params": params,
        "seed": seed,
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": device,
            "gpu": torch.cuda.get_device_name(0) if device.startswith("cuda") else None,
            "platform": platform.platform(),
        },
        "git_commit": _git_commit(),
        "trained_at": started.isoformat(),
        "files": files,
        "weights_digest": digest,
    }
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {out} ({manifest['model_version']})")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the B1e encoder model.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", help="cpu or cuda (default: cuda when available)")
    args = parser.parse_args(argv)
    try:
        train(args.dataset, args.out, device=args.device)
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

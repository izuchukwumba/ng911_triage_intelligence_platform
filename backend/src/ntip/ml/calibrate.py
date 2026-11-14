"""Calibrate B1e's scores and choose a threshold per cue (ML layer design 6, milestone ML-9).

Fitted on data the model did not train on: the generated dataset's
**regression** split, for a model trained with ``--split dev``. Test data is
refused.

    python -m ntip.ml.calibrate --model b1e --dataset ../data/eval/generated-2.1.0-seed42.jsonl \\
        --split regression --out b1e-calibration.json

Method, fixed before fitting:

1. **Temperature scaling.** One temperature ``T`` for all cues, chosen on a
   grid to minimise the negative log-likelihood of the labels:
   ``calibrated = sigmoid(logit(score) / T)``.
2. **A threshold per cue**, on the calibrated scores:
   - a *critical* cue (critical on its own in the ruleset) takes the highest
     threshold that still finds at least ``CRITICAL_RECALL`` of its labelled
     cases, because a missed critical cue costs more than a false one;
   - any other cue takes the lowest threshold whose findings are right at
     least ``TARGET_PRECISION`` of the time (selective risk at most 10%).
     If no threshold reaches that, the cue is never proposed;
   - a cue with fewer than ``MIN_POSITIVES`` labelled cases keeps the
     default threshold, and the file says so.

The calibration file is bound to one model by its weights digest. It records
the data digest, the method and its targets, and every threshold with the
counts behind it. ``B1eModel`` refuses a file made for another model.
"""

import argparse
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ntip.evaluation.calibration import summarise

CALIBRATION_FORMAT = "ntip-calibration/1"
TARGET_PRECISION = 0.9
CRITICAL_RECALL = 0.95
MIN_POSITIVES = 10
DEFAULT_THRESHOLD = 0.5
ALLOWED_SPLITS = ("dev", "regression")
# Codes the labelling guide does not label: their thresholds are left alone.
UNLABELLED = frozenset({"CALLER_HIGH_DISTRESS", "CALLER_LOCATION_UNKNOWN", "POSSIBLE_PRANK"})
_TEMPERATURES = [round(0.25 * 1.1**i, 4) for i in range(45)]  # 0.25 to about 16
_EPS = 1e-6


def _logit(p: float) -> float:
    p = min(max(p, _EPS), 1 - _EPS)
    return math.log(p / (1 - p))


def scale(score: float, temperature: float) -> float:
    return 1 / (1 + math.exp(-_logit(score) / temperature))


def fit_temperature(pairs: Sequence[tuple[float, bool]]) -> float:
    def nll(t: float) -> float:
        total = 0.0
        for score, label in pairs:
            p = min(max(scale(score, t), _EPS), 1 - _EPS)
            total -= math.log(p if label else 1 - p)
        return total

    return min(_TEMPERATURES, key=nll)


def _threshold(
    scored: Sequence[tuple[float, bool]], critical: bool
) -> tuple[float | None, dict[str, Any]]:
    positives = sum(label for _, label in scored)
    info: dict[str, Any] = {"positives": positives, "negatives": len(scored) - positives}
    if positives < MIN_POSITIVES:
        info["rule"] = f"fewer than {MIN_POSITIVES} labelled cases: default threshold"
        return DEFAULT_THRESHOLD, info
    candidates = sorted({s for s, _ in scored}, reverse=True)

    def at(t: float) -> tuple[int, int]:
        found = [label for s, label in scored if s >= t]
        return sum(found), len(found)

    if critical:
        info["rule"] = f"critical: highest threshold with recall >= {CRITICAL_RECALL}"
        for t in candidates:  # descending: the first that reaches the recall is the highest
            tp, _ = at(t)
            if tp / positives >= CRITICAL_RECALL:
                return _record(t, at(t), positives, info)
        return _record(candidates[-1], at(candidates[-1]), positives, info)

    info["rule"] = f"lowest threshold with precision >= {TARGET_PRECISION}"
    best: float | None = None
    for t in candidates:  # descending; keep the lowest that still meets the precision
        tp, n = at(t)
        if n and tp / n >= TARGET_PRECISION:
            best = t
    if best is None:
        info["rule"] += ": not reachable, never proposed"
        return None, info
    return _record(best, at(best), positives, info)


def _record(
    t: float, counts: tuple[int, int], positives: int, info: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    tp, n = counts
    info.update(precision=round(tp / n, 4) if n else None, recall=round(tp / positives, 4))
    return round(t, 6), info


@dataclass
class Calibration:
    model_version: str
    weights_digest: str
    temperature: float
    thresholds: dict[str, float | None]
    document: dict[str, Any]

    def score(self, raw: float) -> float:
        return scale(raw, self.temperature)

    def threshold(self, code: str) -> float | None:
        return self.thresholds.get(code, DEFAULT_THRESHOLD)

    @classmethod
    def load(cls, path: Path) -> "Calibration":
        document = json.loads(path.read_text("utf-8"))
        if document.get("format") != CALIBRATION_FORMAT:
            raise ValueError(f"{path} is not a calibration file")
        return cls(
            model_version=document["model_version"],
            weights_digest=document["weights_digest"],
            temperature=float(document["temperature"]),
            thresholds={c: x["threshold"] for c, x in document["codes"].items()},
            document=document,
        )


def fit(
    scores: Sequence[dict[str, float]],
    labels: Sequence[set[str]],
    critical: frozenset[str],
) -> dict[str, Any]:
    """The temperature, per-cue thresholds and before/after calibration figures."""
    codes = sorted(c for c in scores[0] if c not in UNLABELLED) if scores else []
    pairs = [(s[c], c in live) for s, live in zip(scores, labels, strict=True) for c in codes]
    temperature = fit_temperature(pairs)
    out: dict[str, Any] = {}
    for code in codes:
        scored = [
            (scale(s[code], temperature), code in live)
            for s, live in zip(scores, labels, strict=True)
        ]
        threshold, info = _threshold(scored, code in critical)
        out[code] = {"threshold": threshold, "critical": code in critical, **info}
    after = [(scale(s, temperature), y) for s, y in pairs]
    return {
        "temperature": temperature,
        "codes": out,
        "fit_quality": {"before": summarise(pairs), "after": summarise(after)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    from ntip.evaluation.dataset import Split, load_dataset
    from ntip.ml.b1e import B1eModel
    from ntip.ml.contract import InferenceMessage
    from ntip.ml.fusion import critical_codes

    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", required=True, choices=ALLOWED_SPLITS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    model = B1eModel(args.model)
    trained_on = model.manifest["training_data"]["splits"]
    if args.split in trained_on:
        parser.error(f"the model was trained on {trained_on}; calibrate on a split it never saw")
    dataset = load_dataset(args.dataset)
    cases = dataset.split(Split(args.split))
    scores = [
        model.cue_scores(
            [
                InferenceMessage(source_event_id=f"evt_{i}", text=m)
                for i, m in enumerate(c.messages, 1)
            ]
        )
        for c in cases
    ]
    fitted = fit(scores, [set(c.labels.cues) for c in cases], critical_codes())
    document = {
        "format": CALIBRATION_FORMAT,
        "model_version": model.model_version,
        "weights_digest": model.manifest["weights_digest"],
        "data": {"path": dataset.path, "digest": dataset.digest, "split": args.split,
                 "calls": len(cases)},
        "method": {"temperature": "single, grid search on negative log-likelihood",
                   "target_precision": TARGET_PRECISION, "critical_recall": CRITICAL_RECALL,
                   "min_positives": MIN_POSITIVES, "default_threshold": DEFAULT_THRESHOLD},
        **fitted,
    }  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    never = sorted(c for c, x in fitted["codes"].items() if x["threshold"] is None)
    print(f"temperature {fitted['temperature']}; {len(fitted['codes'])} cues; "
          f"never proposed: {never or 'none'} -> {args.out}")  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

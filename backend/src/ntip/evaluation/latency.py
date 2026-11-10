"""Processing latency on specified hardware (design v1.2, sections 10.5 and 13.3).

Measures end-to-end ingest (parse, optional model, assess, store) through the
pipeline with an in-memory store, for each inference mode, over the curated
dataset's messages. Reports p50/p95/p99 and the machine it ran on. These are
measurements, not targets: section 13.3 asks for a baseline before any target
is set.

    python -m ntip.evaluation.latency --repeat 5
"""

import argparse
import json
import platform
import statistics
import time
from pathlib import Path
from typing import Any

from ntip.evaluation.dataset import load_dataset
from ntip.evaluation.runner import REPO_ROOT, _git_commit
from ntip.ml.extractors import ModelExtractor
from ntip.pipeline import Pipeline
from ntip.schema.canonical import InferenceMode
from ntip.store import InMemoryEventStore


def _percentiles(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)

    def at(q: float) -> float:
        return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 2)

    return {
        "p50": at(0.5),
        "p95": at(0.95),
        "p99": at(0.99),
        "mean": round(statistics.mean(ordered), 2),
    }


def measure(
    texts: list[str], mode: InferenceMode, model: ModelExtractor | None, repeat: int
) -> dict[str, Any]:
    pipeline = Pipeline(store=InMemoryEventStore(), inference_mode=mode, extractor=model)
    pipeline.ingest(texts[0])  # warm caches (lexicon patterns, rulesets)
    samples = []
    for _ in range(repeat):
        for text in texts:
            started = time.perf_counter()
            pipeline.ingest(text)
            samples.append((time.perf_counter() - started) * 1000)
    return {
        "mode": mode,
        "model": model.model_id if model else None,
        "requests": len(samples),
        "latency_ms": _percentiles(samples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "evaluation" / "results")
    args = parser.parse_args()
    dataset = load_dataset(REPO_ROOT / "data" / "eval" / "curated.jsonl")
    texts = [" ".join(c.messages) for c in dataset.cases]

    runs = [measure(texts, InferenceMode.RULES_ONLY, None, args.repeat)]
    try:
        from ntip.ml.b1 import B1Model

        b1 = B1Model()
        runs.append(measure(texts, InferenceMode.HYBRID_REVIEW, b1, args.repeat))
    except ImportError:
        pass  # the "ml" extra is not installed

    result = {
        "git_commit": _git_commit(),
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "setup": "Pipeline with in-memory store, in-process model, one request at a time",
        "runs": runs,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "latency.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["| Mode | Model | Requests | p50 ms | p95 ms | p99 ms |", "|---|---|---|---|---|---|"]
    for r in runs:
        lat = r["latency_ms"]
        lines.append(
            f"| {r['mode']} | {r['model'] or '-'} | {r['requests']} | {lat['p50']} | "
            f"{lat['p95']} | {lat['p99']} |"
        )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

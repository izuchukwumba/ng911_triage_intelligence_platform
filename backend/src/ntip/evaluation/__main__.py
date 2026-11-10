"""Evaluate the rules baseline on a labelled dataset.

    python -m ntip.evaluation                                  # dev + regression splits
    python -m ntip.evaluation --split test --out ../docs/evaluation/results
    python -m ntip.evaluation --split regression --gate        # CI safety gate

``--gate`` exits with status 2 when any case expected at P0 is predicted
lower: critical omissions must never be merged silently (design v1.2, 14.2).
"""

import argparse
import json
from pathlib import Path

from ntip.evaluation.dataset import Split, load_dataset
from ntip.evaluation.report import to_markdown
from ntip.evaluation.runner import REPO_ROOT, evaluate

DEFAULT_DATASET = REPO_ROOT / "data" / "eval" / "curated.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--split", action="append", choices=[s.value for s in Split])
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--out", type=Path, help="directory for report.json and report.md")
    parser.add_argument("--gate", action="store_true", help="fail on any critical under-triage")
    args = parser.parse_args()

    splits = [Split(s) for s in (args.split or ["dev", "regression"])]
    result = evaluate(load_dataset(args.dataset), splits, seed=args.seed)
    markdown = to_markdown(result)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        # Versioned names keep earlier baselines next to new results.
        m = result["manifest"]
        stem = f"b0-{m['parser'].rsplit('-', 1)[-1]}-{m['ruleset']['name']}-{'-'.join(splits)}"
        (args.out / f"{stem}.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        (args.out / f"{stem}.md").write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)

    missed = result["metrics"]["critical_undertriage"]["cases"]
    if args.gate and missed:
        print(f"GATE FAILED: critical under-triage in {missed}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

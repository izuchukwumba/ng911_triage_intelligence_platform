"""Write a generated dataset.

python -m ntip.generator --n 510 --seed 42            # data/eval/generated-1.0.0-seed42.jsonl
python -m ntip.generator --n 510 --seed 42 --check    # exit 1 if the file differs
"""

import argparse
from pathlib import Path

from ntip.evaluation.dataset import dump_case
from ntip.evaluation.runner import REPO_ROOT
from ntip.generator.generate import GENERATOR_VERSION, generate


def path_for(seed: int) -> Path:
    return REPO_ROOT / "data" / "eval" / f"generated-{GENERATOR_VERSION}-seed{seed}.jsonl"


def render(n: int, seed: int) -> str:
    return "\n".join(dump_case(case) for case in generate(n, seed)) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--n", type=int, default=510)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = path_for(args.seed)
    text = render(args.n, args.seed)
    if args.check:
        same = path.exists() and path.read_text("utf-8").replace("\r\n", "\n") == text
        print("up to date" if same else f"stale: {path.name}")
        return 0 if same else 1
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

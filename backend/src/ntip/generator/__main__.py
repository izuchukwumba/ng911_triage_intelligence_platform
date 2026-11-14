"""Write a generated dataset.

python -m ntip.generator --n 510 --seed 42                              # generated-1.0.0-seed42
python -m ntip.generator --generator 2.0.0 --n 2010 --seed 42           # generated-2.0.0-seed42
python -m ntip.generator --generator 2.0.0 --n 2010 --seed 42 --check   # exit 1 if it differs
"""

import argparse
from collections.abc import Callable, Iterator
from pathlib import Path

from ntip.evaluation.dataset import EvalCase, dump_case
from ntip.evaluation.runner import REPO_ROOT
from ntip.generator import generate as v1
from ntip.generator import generate_v2 as v2

GENERATORS: dict[str, Callable[[int, int], Iterator[EvalCase]]] = {
    v1.GENERATOR_VERSION: v1.generate,
    v2.GENERATOR_VERSION: v2.generate,
}


def path_for(seed: int, version: str = v1.GENERATOR_VERSION) -> Path:
    return REPO_ROOT / "data" / "eval" / f"generated-{version}-seed{seed}.jsonl"


def render(n: int, seed: int, version: str = v1.GENERATOR_VERSION) -> str:
    return "\n".join(dump_case(case) for case in GENERATORS[version](n, seed)) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--generator", choices=sorted(GENERATORS), default=v1.GENERATOR_VERSION)
    parser.add_argument("--n", type=int, default=510)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = path_for(args.seed, args.generator)
    text = render(args.n, args.seed, args.generator)
    if args.check:
        same = path.exists() and path.read_text("utf-8").replace("\r\n", "\n") == text
        print("up to date" if same else f"stale: {path.name}")
        return 0 if same else 1
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

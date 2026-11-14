"""Generator 2.1: generator 2.0 plus the variants in ``scenarios_v21``.

Generator 2.0 is unchanged, so ``generated-2.0.0-seed42.jsonl`` and every
report built on it stay reproducible.
"""

from collections.abc import Iterator

from ntip.evaluation.dataset import EvalCase
from ntip.generator import generate_v2
from ntip.generator.scenarios_v21 import SITUATIONS

GENERATOR_VERSION = "2.1.0"


def generate(n: int, seed: int) -> Iterator[EvalCase]:
    """``n`` cases, cycling through families; identical for the same seed."""
    return generate_v2.generate(
        n, seed, situations=SITUATIONS, version=GENERATOR_VERSION, extras=True
    )

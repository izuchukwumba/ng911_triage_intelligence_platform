"""Generator 2.2: generator 2.1 plus families that put every cue code in both
training splits (``scenarios_v22``). Generators 2.0 and 2.1 are unchanged."""

from collections.abc import Iterator

from ntip.evaluation.dataset import EvalCase
from ntip.generator import generate_v2
from ntip.generator.scenarios_v22 import SITUATIONS

GENERATOR_VERSION = "2.2.0"


def generate(n: int, seed: int) -> Iterator[EvalCase]:
    """``n`` cases, cycling through families; identical for the same seed."""
    return generate_v2.generate(
        n, seed, situations=SITUATIONS, version=GENERATOR_VERSION, extras=True
    )

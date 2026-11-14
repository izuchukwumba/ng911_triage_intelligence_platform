"""Calibration: temperature, per-cue thresholds, and the calibration file."""

import json
import random
from pathlib import Path

import pytest

from ntip.ml.calibrate import (
    CALIBRATION_FORMAT,
    DEFAULT_THRESHOLD,
    Calibration,
    _threshold,
    fit,
    fit_temperature,
    scale,
)


def test_an_overconfident_model_gets_a_temperature_above_one() -> None:
    rng = random.Random(1)
    # Scores of 0.99 / 0.01 that are right only 70% of the time.
    pairs = [(0.99, rng.random() < 0.7) for _ in range(300)]
    pairs += [(0.01, rng.random() < 0.3) for _ in range(300)]
    t = fit_temperature(pairs)
    assert t > 1
    assert 0.6 < scale(0.99, t) < 0.8  # pulled towards the observed 70%


def test_scaling_keeps_the_order_of_scores() -> None:
    assert scale(0.2, 2.0) < scale(0.5, 2.0) < scale(0.9, 2.0)
    assert scale(0.5, 2.0) == pytest.approx(0.5)


def _scored(positives: list[float], negatives: list[float]) -> list[tuple[float, bool]]:
    return [(s, True) for s in positives] + [(s, False) for s in negatives]


def test_a_critical_cue_keeps_its_recall() -> None:
    positives = [0.9] * 18 + [0.4, 0.2]  # 20 labelled cases
    threshold, info = _threshold(_scored(positives, [0.5, 0.3]), critical=True)
    assert threshold == 0.4  # 19/20 = 0.95 recall; 0.9 alone would give 0.9
    assert info["recall"] == 0.95


def test_another_cue_takes_the_lowest_threshold_that_is_precise_enough() -> None:
    positives = [0.95] * 9 + [0.6] * 3
    negatives = [0.7, 0.5, 0.4]
    threshold, info = _threshold(_scored(positives, negatives), critical=False)
    # At 0.6: 12 right of 13 found (0.92); at 0.5: 12 of 14 (0.86).
    assert threshold == 0.6 and info["precision"] == round(12 / 13, 4)


def test_an_imprecise_cue_is_never_proposed_and_a_rare_one_keeps_the_default() -> None:
    threshold, info = _threshold(_scored([0.6] * 10, [0.9] * 10), critical=False)
    assert threshold is None and "never proposed" in info["rule"]
    threshold, info = _threshold(_scored([0.9] * 3, [0.1] * 50), critical=False)
    assert threshold == DEFAULT_THRESHOLD and info["positives"] == 3


def test_fit_covers_labelled_codes_only() -> None:
    scores = [
        {"NOT_BREATHING": 0.9, "POSSIBLE_PRANK": 0.2},
        {"NOT_BREATHING": 0.1, "POSSIBLE_PRANK": 0.8},
    ]
    fitted = fit(scores, [{"NOT_BREATHING"}, set()], frozenset({"NOT_BREATHING"}))
    assert set(fitted["codes"]) == {"NOT_BREATHING"}
    assert fitted["codes"]["NOT_BREATHING"]["critical"] is True
    assert {"before", "after"} == set(fitted["fit_quality"])


def test_a_calibration_file_loads_and_is_checked(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(
        json.dumps(
            {
                "format": CALIBRATION_FORMAT,
                "model_version": "0.1.0+abc",
                "weights_digest": "sha256:x",
                "temperature": 2.0,
                "codes": {
                    "FIRE_REPORTED": {"threshold": None},
                    "NOT_BREATHING": {"threshold": 0.3},
                },
            }
        ),
        "utf-8",
    )
    calibration = Calibration.load(path)
    assert calibration.threshold("FIRE_REPORTED") is None
    assert calibration.threshold("NOT_BREATHING") == 0.3
    assert calibration.threshold("SMOKE_REPORTED") == DEFAULT_THRESHOLD
    assert calibration.score(0.5) == pytest.approx(0.5)
    path.write_text("{}", "utf-8")
    with pytest.raises(ValueError, match="not a calibration file"):
        Calibration.load(path)


def test_a_critical_threshold_never_falls_below_the_floor() -> None:
    from ntip.ml.calibrate import CRITICAL_FLOOR

    positives = [0.9] * 5 + [0.05] * 15  # recall 0.95 would need 0.05
    threshold, info = _threshold(_scored(positives, [0.2] * 5), critical=True)
    assert threshold == CRITICAL_FLOOR and "floor applied" in info["rule"]
    assert info["recall"] == 0.25

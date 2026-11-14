# Comparison on data/eval/curated.jsonl (dev, regression)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `fcf93334ef8d96b1fd37fd025703a72d8026ac04` · dataset `sha256:6694a761e9861011c85e9cacd4d065099f36778aed82c6c341833c5b688c26f7` · parser `rules-parser-1.5.0` · engine `triage-engine-1.2.0` · ruleset `research-1.2.0` · B1 `1.0.0+a20d70dfc761` · B1e `0.1.0+30718f35865b` · seed `20261109`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention | B1e only | Hybrid B0+B1e | Hybrid B0+B1e (fusion 2) |
|---|---|---|---|---|---|---|---|
| Critical-cue sensitivity | 1.000 (15/15) | 0.667 (10/15) | 1.000 (15/15) | 1.000 (15/15) | 0.600 (9/15) | 1.000 (15/15) | 1.000 (15/15) |
| Critical under-triage | 0.000 (0/13) | 0.308 (4/13) | 0.000 (0/13) | 0.000 (0/13) | 0.385 (5/13) | 0.000 (0/13) | 0.000 (0/13) |
| Priority exact | 0.833 (25/30) | 0.533 (16/30) | 0.800 (24/30) | 0.733 (22/30) | 0.433 (13/30) | 0.733 (22/30) | 0.767 (23/30) |
| Under-triage (any) | 0.033 (1/30) | 0.333 (10/30) | 0.033 (1/30) | 0.033 (1/30) | 0.300 (9/30) | 0.033 (1/30) | 0.033 (1/30) |
| Over-triage (any) | 0.133 (4/30) | 0.133 (4/30) | 0.167 (5/30) | 0.233 (7/30) | 0.267 (8/30) | 0.233 (7/30) | 0.200 (6/30) |
| Cue micro precision | 0.973 | 0.5938 | 0.72 | 0.5714 | 0.7778 | 0.8372 | 0.9231 |
| Cue micro recall | 0.973 | 0.5135 | 0.973 | 0.973 | 0.5676 | 0.973 | 0.973 |
| Cue micro F1 | 0.973 | 0.5507 | 0.8276 | 0.72 | 0.6562 | 0.9 | 0.9474 |
| Denied/past cues treated as live | 0 | 0 | 0 | 1 | 0 | 0 | 0 |

## B1 calibration (cue scores vs labels)

420 (case, cue) pairs, 30 positive. Brier 0.0495, ECE 0.0953, AURC 0.0151, selective risk {'50%': 0.0095, '80%': 0.0238, '100%': 0.0571}.

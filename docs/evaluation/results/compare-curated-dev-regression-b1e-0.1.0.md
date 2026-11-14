# Comparison on data/eval/curated.jsonl (dev, regression)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `c65bbcfc786b27846e6dfe26b3dbd80c24fc22b8` · dataset `sha256:efe6e09839147de8fdecc7b9d7f2441a1439fbc4e38782747f027d8d7698283c` · parser `rules-parser-1.4.0` · engine `triage-engine-1.2.0` · ruleset `research-1.1.0` · B1 `1.0.0+f764c2172d5a` · seed `20261109`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention | B1e only | Hybrid B0+B1e |
|---|---|---|---|---|---|---|
| Critical-cue sensitivity | 1.000 (15/15) | 0.667 (10/15) | 1.000 (15/15) | 1.000 (15/15) | 0.533 (8/15) | 1.000 (15/15) |
| Critical under-triage | 0.000 (0/13) | 0.308 (4/13) | 0.000 (0/13) | 0.000 (0/13) | 0.385 (5/13) | 0.000 (0/13) |
| Priority exact | 0.867 (26/30) | 0.567 (17/30) | 0.833 (25/30) | 0.767 (23/30) | 0.500 (15/30) | 0.833 (25/30) |
| Under-triage (any) | 0.000 (0/30) | 0.300 (9/30) | 0.000 (0/30) | 0.000 (0/30) | 0.333 (10/30) | 0.000 (0/30) |
| Over-triage (any) | 0.133 (4/30) | 0.133 (4/30) | 0.167 (5/30) | 0.233 (7/30) | 0.167 (5/30) | 0.167 (5/30) |
| Cue micro precision | 0.9714 | 0.5938 | 0.7083 | 0.5574 | 0.5517 | 0.7083 |
| Cue micro recall | 1.0 | 0.5588 | 1.0 | 1.0 | 0.4706 | 1.0 |
| Cue micro F1 | 0.9855 | 0.5758 | 0.8293 | 0.7158 | 0.5079 | 0.8293 |
| Denied/past cues treated as live | 0 | 0 | 0 | 1 | 1 | 1 |

## B1 calibration (cue scores vs labels)

420 (case, cue) pairs, 30 positive. Brier 0.0495, ECE 0.0953, AURC 0.0151, selective risk {'50%': 0.0095, '80%': 0.0238, '100%': 0.0571}.

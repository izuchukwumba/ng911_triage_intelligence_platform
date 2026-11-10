# Comparison on data/eval/curated.jsonl (test)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `c97a7420ab0656cbd074b82a18338840232438be` · dataset `sha256:efe6e09839147de8fdecc7b9d7f2441a1439fbc4e38782747f027d8d7698283c` · parser `rules-parser-1.3.0` · engine `triage-engine-1.2.0` · ruleset `research-1.1.0` · B1 `1.0.0+f764c2172d5a` · seed `20261109`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention |
|---|---|---|---|---|
| Critical-cue sensitivity | 0.857 (6/7) | 0.571 (4/7) | 0.857 (6/7) | 0.857 (6/7) |
| Critical under-triage | 0.222 (2/9) | 0.333 (3/9) | 0.000 (0/9) | 0.000 (0/9) |
| Priority exact | 0.800 (16/20) | 0.550 (11/20) | 0.800 (16/20) | 0.750 (15/20) |
| Under-triage (any) | 0.100 (2/20) | 0.300 (6/20) | 0.000 (0/20) | 0.000 (0/20) |
| Over-triage (any) | 0.100 (2/20) | 0.150 (3/20) | 0.200 (4/20) | 0.250 (5/20) |
| Cue micro precision | 1.0 | 0.7059 | 0.7872 | 0.6607 |
| Cue micro recall | 0.9211 | 0.6316 | 0.9737 | 0.9737 |
| Cue micro F1 | 0.9589 | 0.6667 | 0.8706 | 0.7872 |
| Denied/past cues treated as live | 0 | 1 | 1 | 1 |

## B1 calibration (cue scores vs labels)

280 (case, cue) pairs, 33 positive. Brier 0.052, ECE 0.0659, AURC 0.009, selective risk {'50%': 0.0, '80%': 0.0179, '100%': 0.0679}.

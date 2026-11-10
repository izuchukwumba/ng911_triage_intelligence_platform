# Comparison on data/eval/generated-1.0.0-seed42.jsonl (test)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `c97a7420ab0656cbd074b82a18338840232438be` · dataset `sha256:a064e9dbe885a3448314e654c2650c7e20b6e200c29c1b26c45f1bea9b045555` · parser `rules-parser-1.3.0` · engine `triage-engine-1.2.0` · ruleset `research-1.1.0` · B1 `1.0.0+f764c2172d5a` · seed `20261109`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention |
|---|---|---|---|---|
| Critical-cue sensitivity | 1.000 (27/27) | 0.148 (4/27) | 1.000 (27/27) | 1.000 (27/27) |
| Critical under-triage | 0.000 (0/47) | 0.894 (42/47) | 0.000 (0/47) | 0.000 (0/47) |
| Priority exact | 0.862 (181/210) | 0.148 (31/210) | 0.771 (162/210) | 0.705 (148/210) |
| Under-triage (any) | 0.014 (3/210) | 0.657 (138/210) | 0.009 (2/210) | 0.009 (2/210) |
| Over-triage (any) | 0.124 (26/210) | 0.195 (41/210) | 0.219 (46/210) | 0.286 (60/210) |
| Cue micro precision | 0.9818 | 0.6727 | 0.8677 | 0.6915 |
| Cue micro recall | 0.989 | 0.2721 | 0.989 | 0.989 |
| Cue micro F1 | 0.9853 | 0.3874 | 0.9244 | 0.8139 |
| Denied/past cues treated as live | 0 | 2 | 2 | 2 |

## B1 calibration (cue scores vs labels)

2940 (case, cue) pairs, 133 positive. Brier 0.0362, ECE 0.0958, AURC 0.0079, selective risk {'50%': 0.0109, '80%': 0.0111, '100%': 0.0323}.

## Slices (cue micro F1 / critical-cue sensitivity)

| Slice | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention |
|---|---|---|---|---|
| child | 1.0 / 1.0 (n=16) | 0.7246 / 0.0 (n=16) | 0.9885 / 1.0 (n=16) | 0.9556 / 1.0 (n=16) |
| disfluent | 0.9615 / 1.0 (n=21) | 0.2941 / 0.0 (n=21) | 0.9091 / 1.0 (n=21) | 0.8197 / 1.0 (n=21) |
| misspelled | 0.8235 / 1.0 (n=12) | 0.3077 / 0.0 (n=12) | 0.7368 / 1.0 (n=12) | 0.6364 / 1.0 (n=12) |
| multiple | 1.0 / 1.0 (n=16) | 0.8182 / 0.0 (n=16) | 1.0 / 1.0 (n=16) | 0.972 / 1.0 (n=16) |
| past | None / None (n=14) | None / None (n=14) | None / None (n=14) | None / None (n=14) |
| plain | 0.9872 / 1.0 (n=74) | 0.2453 / 0.0 (n=74) | 0.8953 / 1.0 (n=74) | 0.7586 / 1.0 (n=74) |
| second_hand | 0.9855 / 1.0 (n=24) | 0.3721 / 0.0 (n=24) | 0.9855 / 1.0 (n=24) | 0.9315 / 1.0 (n=24) |
| spanish | 1.0 / 1.0 (n=11) | 0.3077 / 1.0 (n=11) | 0.9 / 1.0 (n=11) | 0.6667 / 1.0 (n=11) |
| uncertain | 0.9867 / 1.0 (n=53) | 0.3469 / 0.0 (n=53) | 0.9427 / 1.0 (n=53) | 0.8457 / 1.0 (n=53) |

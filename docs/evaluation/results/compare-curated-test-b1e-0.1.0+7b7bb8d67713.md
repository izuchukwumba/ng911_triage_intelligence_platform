# Comparison on data/eval/curated.jsonl (test)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `7e580895f3a0a10dd00be4dba13112a371f1d62e` · dataset `sha256:6694a761e9861011c85e9cacd4d065099f36778aed82c6c341833c5b688c26f7` · parser `rules-parser-1.5.0` · engine `triage-engine-1.2.0` · ruleset `research-1.2.0` · B1 `1.0.0+f764c2172d5a` · B1e `0.1.0+7b7bb8d67713` · seed `20261109` · pre-registration `docs/evaluation/preregistration/ml-10-frozen-comparison.md` `sha256:f5f5013b2ff11209fbc5cf43a268530c361a369d64786e5fb7610df2dbec05b4`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention | B1e only | Hybrid B0+B1e | Hybrid B0+B1e (fusion 2) | Hybrid B0+B1e without abstention |
|---|---|---|---|---|---|---|---|---|
| Critical-cue sensitivity | 0.857 (6/7) | 0.571 (4/7) | 0.857 (6/7) | 0.857 (6/7) | 0.857 (6/7) | 1.000 (7/7) | 1.000 (7/7) | 1.000 (7/7) |
| Critical under-triage | 0.222 (2/9) | 0.333 (3/9) | 0.000 (0/9) | 0.000 (0/9) | 0.222 (2/9) | 0.000 (0/9) | 0.111 (1/9) | 0.000 (0/9) |
| Priority exact | 0.800 (16/20) | 0.550 (11/20) | 0.800 (16/20) | 0.750 (15/20) | 0.750 (15/20) | 0.900 (18/20) | 0.850 (17/20) | 0.900 (18/20) |
| Under-triage (any) | 0.100 (2/20) | 0.300 (6/20) | 0.000 (0/20) | 0.000 (0/20) | 0.150 (3/20) | 0.000 (0/20) | 0.050 (1/20) | 0.000 (0/20) |
| Over-triage (any) | 0.100 (2/20) | 0.150 (3/20) | 0.200 (4/20) | 0.250 (5/20) | 0.100 (2/20) | 0.100 (2/20) | 0.100 (2/20) | 0.100 (2/20) |
| Cue micro precision | 1.0 | 0.7059 | 0.7917 | 0.6667 | 0.9 | 0.9268 | 0.9737 | 0.9048 |
| Cue micro recall | 0.9231 | 0.6154 | 0.9744 | 0.9744 | 0.6923 | 0.9744 | 0.9487 | 0.9744 |
| Cue micro F1 | 0.96 | 0.6575 | 0.8736 | 0.7917 | 0.7826 | 0.95 | 0.961 | 0.9383 |
| Denied/past cues treated as live | 0 | 1 | 1 | 1 | 1 | 1 | 0 | 1 |

## B1 calibration (cue scores vs labels)

280 (case, cue) pairs, 33 positive. Brier 0.052, ECE 0.0659, AURC 0.009, selective risk {'50%': 0.0, '80%': 0.0179, '100%': 0.0679}.

## Paired comparisons (A vs B, same cases)

McNemar columns: cases only A got right / cases only B got right, exact two-sided p. Differences are A minus B with a 95% paired bootstrap interval.

| A vs B | P0 calls given P0 | Priority exact | Δ critical under-triage | Δ critical-cue sensitivity | Δ cue F1 | Δ under-triage | Δ over-triage |
|---|---|---|---|---|---|---|---|
| B1 only vs B0 rules | 1 / 2 (p=1) | 2 / 7 (p=0.18) | +0.111 [-0.286, +0.500] | -0.286 [-0.667, +0.000] | -0.302 [-0.389, -0.226] | +0.200 [-0.050, +0.400] | +0.050 [-0.100, +0.250] |
| Hybrid B0+B1 vs B0 rules | 2 / 0 (p=0.5) | 2 / 2 (p=1) | -0.222 [-0.556, +0.000] | +0.000 [+0.000, +0.000] | -0.086 [-0.155, -0.014] | -0.100 [-0.250, +0.000] | +0.100 [+0.000, +0.250] |
| Hybrid without abstention vs B0 rules | 2 / 0 (p=0.5) | 2 / 3 (p=1) | -0.222 [-0.556, +0.000] | +0.000 [+0.000, +0.000] | -0.168 [-0.252, -0.081] | -0.100 [-0.250, +0.000] | +0.150 [+0.000, +0.300] |
| B1e only vs B0 rules | 2 / 2 (p=1) | 2 / 3 (p=1) | +0.000 [-0.444, +0.444] | +0.000 [-0.400, +0.429] | -0.177 [-0.291, -0.070] | +0.050 [-0.150, +0.250] | +0.000 [+0.000, +0.000] |
| Hybrid B0+B1e vs B0 rules | 2 / 0 (p=0.5) | 2 / 0 (p=0.5) | -0.222 [-0.556, +0.000] | +0.143 [+0.000, +0.444] | -0.010 [-0.050, +0.031] | -0.100 [-0.250, +0.000] | +0.000 [+0.000, +0.000] |
| Hybrid B0+B1e (fusion 2) vs B0 rules | 1 / 0 (p=1) | 1 / 0 (p=1) | -0.111 [-0.375, +0.000] | +0.143 [+0.000, +0.444] | +0.001 [+0.000, +0.006] | -0.050 [-0.150, +0.000] | +0.000 [+0.000, +0.000] |
| Hybrid B0+B1e without abstention vs B0 rules | 2 / 0 (p=0.5) | 2 / 0 (p=0.5) | -0.222 [-0.556, +0.000] | +0.143 [+0.000, +0.444] | -0.022 [-0.068, +0.025] | -0.100 [-0.250, +0.000] | +0.000 [+0.000, +0.000] |
| Hybrid B0+B1e vs Hybrid B0+B1 | 0 / 0 (p=1) | 2 / 0 (p=0.5) | +0.000 [+0.000, +0.000] | +0.143 [+0.000, +0.444] | +0.076 [+0.035, +0.117] | +0.000 [+0.000, +0.000] | -0.100 [-0.250, +0.000] |

## Run cost and verification

Wall time per call on the machine that ran the report, parser and triage included.

| System | p50 ms | p95 ms | CPU s | Candidates rejected by span verification |
|---|---|---|---|---|
| B0 rules | 1.04 | 23.84 | 0.11 | n/a |
| B1 only | 4.76 | 10.56 | 0.16 | 0 |
| Hybrid B0+B1 | 5.62 | 7.26 | 0.19 | 0 |
| Hybrid without abstention | 5.08 | 8.28 | 0.16 | 0 |
| B1e only | 23.19 | 118.43 | 8.69 | 0 |
| Hybrid B0+B1e | 35.24 | 70.72 | 9.44 | 0 |
| Hybrid B0+B1e (fusion 2) | 29.96 | 50.27 | 8.73 | 0 |
| Hybrid B0+B1e without abstention | 24.82 | 52.74 | 8.55 | 0 |

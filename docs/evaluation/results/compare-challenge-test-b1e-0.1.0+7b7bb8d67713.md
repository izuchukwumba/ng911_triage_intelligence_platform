# Comparison on data/eval/challenge-1.0.0.jsonl (test)

> Synthetic data. B1 was trained only on the generated dev + regression splits and has never seen these cases unless they come from those splits.

Commit `7e580895f3a0a10dd00be4dba13112a371f1d62e` · dataset `sha256:febf06e3533051dd11382e36c4c209b626d9a81b8255fb562e2eeea71dbaac43` · parser `rules-parser-1.5.0` · engine `triage-engine-1.2.0` · ruleset `research-1.2.0` · B1 `1.0.0+f764c2172d5a` · B1e `0.1.0+7b7bb8d67713` · seed `20261109` · pre-registration `docs/evaluation/preregistration/ml-10-frozen-comparison.md` `sha256:f5f5013b2ff11209fbc5cf43a268530c361a369d64786e5fb7610df2dbec05b4`

| Metric | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention | B1e only | Hybrid B0+B1e | Hybrid B0+B1e (fusion 2) | Hybrid B0+B1e without abstention |
|---|---|---|---|---|---|---|---|---|
| Critical-cue sensitivity | 0.600 (9/15) | 0.533 (8/15) | 0.733 (11/15) | 0.733 (11/15) | 0.400 (6/15) | 0.600 (9/15) | 0.600 (9/15) | 0.600 (9/15) |
| Critical under-triage | 0.421 (8/19) | 0.526 (10/19) | 0.263 (5/19) | 0.263 (5/19) | 0.526 (10/19) | 0.263 (5/19) | 0.421 (8/19) | 0.263 (5/19) |
| Priority exact | 0.457 (32/70) | 0.357 (25/70) | 0.471 (33/70) | 0.429 (30/70) | 0.386 (27/70) | 0.443 (31/70) | 0.429 (30/70) | 0.457 (32/70) |
| Under-triage (any) | 0.200 (14/70) | 0.286 (20/70) | 0.114 (8/70) | 0.100 (7/70) | 0.243 (17/70) | 0.114 (8/70) | 0.200 (14/70) | 0.100 (7/70) |
| Over-triage (any) | 0.343 (24/70) | 0.357 (25/70) | 0.414 (29/70) | 0.471 (33/70) | 0.371 (26/70) | 0.443 (31/70) | 0.371 (26/70) | 0.443 (31/70) |
| Cue micro precision | 0.7727 | 0.5192 | 0.6129 | 0.4597 | 0.6094 | 0.6211 | 0.7286 | 0.566 |
| Cue micro recall | 0.6538 | 0.3462 | 0.7308 | 0.7308 | 0.5 | 0.7564 | 0.6538 | 0.7692 |
| Cue micro F1 | 0.7083 | 0.4154 | 0.6667 | 0.5644 | 0.5493 | 0.6821 | 0.6892 | 0.6522 |
| Denied/past cues treated as live | 4 | 8 | 9 | 11 | 11 | 12 | 5 | 14 |

## B1 calibration (cue scores vs labels)

980 (case, cue) pairs, 51 positive. Brier 0.0493, ECE 0.0928, AURC 0.0161, selective risk {'50%': 0.0122, '80%': 0.0204, '100%': 0.05}.

## Paired comparisons (A vs B, same cases)

McNemar columns: cases only A got right / cases only B got right, exact two-sided p. Differences are A minus B with a 95% paired bootstrap interval.

| A vs B | P0 calls given P0 | Priority exact | Δ critical under-triage | Δ critical-cue sensitivity | Δ cue F1 | Δ under-triage | Δ over-triage |
|---|---|---|---|---|---|---|---|
| B1 only vs B0 rules | 3 / 5 (p=0.727) | 12 / 19 (p=0.281) | +0.105 [-0.182, +0.400] | -0.067 [-0.333, +0.227] | -0.293 [-0.411, -0.171] | +0.086 [-0.029, +0.200] | +0.014 [-0.086, +0.114] |
| Hybrid B0+B1 vs B0 rules | 3 / 0 (p=0.25) | 6 / 5 (p=1) | -0.158 [-0.333, +0.000] | +0.133 [+0.000, +0.333] | -0.042 [-0.097, +0.013] | -0.086 [-0.157, -0.029] | +0.071 [+0.014, +0.143] |
| Hybrid without abstention vs B0 rules | 3 / 0 (p=0.25) | 6 / 8 (p=0.791) | -0.158 [-0.333, +0.000] | +0.133 [+0.000, +0.333] | -0.144 [-0.210, -0.076] | -0.100 [-0.186, -0.029] | +0.129 [+0.057, +0.214] |
| B1e only vs B0 rules | 2 / 4 (p=0.688) | 10 / 15 (p=0.424) | +0.105 [-0.143, +0.357] | -0.200 [-0.400, +0.000] | -0.159 [-0.278, -0.042] | +0.043 [-0.057, +0.157] | +0.029 [-0.071, +0.129] |
| Hybrid B0+B1e vs B0 rules | 3 / 0 (p=0.25) | 6 / 7 (p=1) | -0.158 [-0.333, +0.000] | +0.000 [+0.000, +0.000] | -0.026 [-0.092, +0.034] | -0.086 [-0.157, -0.029] | +0.100 [+0.043, +0.171] |
| Hybrid B0+B1e (fusion 2) vs B0 rules | 0 / 0 (p=1) | 0 / 2 (p=0.5) | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.019 [-0.040, -0.004] | +0.000 [+0.000, +0.000] | +0.029 [+0.000, +0.071] |
| Hybrid B0+B1e without abstention vs B0 rules | 3 / 0 (p=0.25) | 7 / 7 (p=1) | -0.158 [-0.333, +0.000] | +0.000 [+0.000, +0.000] | -0.056 [-0.129, +0.013] | -0.100 [-0.171, -0.043] | +0.100 [+0.043, +0.171] |
| Hybrid B0+B1e vs Hybrid B0+B1 | 2 / 2 (p=1) | 6 / 8 (p=0.791) | +0.000 [-0.210, +0.200] | -0.133 [-0.333, +0.000] | +0.015 [-0.044, +0.078] | +0.000 [-0.071, +0.086] | +0.029 [-0.043, +0.100] |

## Run cost and verification

Wall time per call on the machine that ran the report, parser and triage included.

| System | p50 ms | p95 ms | CPU s | Candidates rejected by span verification |
|---|---|---|---|---|
| B0 rules | 0.75 | 1.85 | 0.73 | n/a |
| B1 only | 4.61 | 5.47 | 0.98 | 0 |
| Hybrid B0+B1 | 5.07 | 6.72 | 1.05 | 0 |
| Hybrid without abstention | 4.7 | 5.77 | 1.03 | 0 |
| B1e only | 32.82 | 62.22 | 36.31 | 0 |
| Hybrid B0+B1e | 30.92 | 51.05 | 33.94 | 0 |
| Hybrid B0+B1e (fusion 2) | 32.21 | 55.54 | 34.22 | 0 |
| Hybrid B0+B1e without abstention | 32.41 | 58.09 | 35.11 | 0 |

## Slices (cue micro F1 / critical-cue sensitivity)

| Slice | B0 rules | B1 only | Hybrid B0+B1 | Hybrid without abstention | B1e only | Hybrid B0+B1e | Hybrid B0+B1e (fusion 2) | Hybrid B0+B1e without abstention |
|---|---|---|---|---|---|---|---|---|
| adversarial | 0.5 / 0.6667 (n=10) | 0.2857 / 0.6667 (n=10) | 0.4 / 0.6667 (n=10) | 0.3636 / 0.6667 (n=10) | 0.5333 / 0.6667 (n=10) | 0.4 / 0.6667 (n=10) | 0.4211 / 0.6667 (n=10) | 0.3636 / 0.6667 (n=10) |
| compound | 0.8085 / 0.75 (n=10) | 0.4324 / 0.25 (n=10) | 0.7917 / 0.75 (n=10) | 0.7037 / 0.75 (n=10) | 0.619 / 0.25 (n=10) | 0.84 / 0.75 (n=10) | 0.8085 / 0.75 (n=10) | 0.84 / 0.75 (n=10) |
| figurative | 0.2222 / None (n=10) | None / None (n=10) | 0.2222 / None (n=10) | 0.125 / None (n=10) | 0.6667 / None (n=10) | 0.4615 / None (n=10) | 0.2222 / None (n=10) | 0.4 / None (n=10) |
| hearsay | 0.7059 / 0.6667 (n=10) | 0.5333 / 0.6667 (n=10) | 0.7368 / 0.6667 (n=10) | 0.6667 / 0.6667 (n=10) | 0.7059 / 0.6667 (n=10) | 0.8 / 0.6667 (n=10) | 0.7059 / 0.6667 (n=10) | 0.7619 / 0.6667 (n=10) |
| negation | 0.9167 / None (n=10) | 0.4167 / None (n=10) | 0.7742 / None (n=10) | 0.6667 / None (n=10) | 0.5714 / None (n=10) | 0.8889 / None (n=10) | 0.9167 / None (n=10) | 0.8387 / None (n=10) |
| noisy | 0.6667 / 0.4 (n=10) | 0.5 / 0.6 (n=10) | 0.7368 / 0.8 (n=10) | 0.6512 / 0.8 (n=10) | 0.4828 / 0.2 (n=10) | 0.6667 / 0.4 (n=10) | 0.6452 / 0.4 (n=10) | 0.6667 / 0.4 (n=10) |
| past_hypothetical | None / None (n=10) | None / None (n=10) | None / None (n=10) | None / None (n=10) | None / None (n=10) | None / None (n=10) | None / None (n=10) | None / None (n=10) |

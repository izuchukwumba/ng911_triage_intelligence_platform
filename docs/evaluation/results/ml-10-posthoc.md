# ML-10 post-hoc analyses (exploratory)

> Not pre-registered. These analyses reproduce the ML-10 systems case by case and add
> statistics requested in review. They do not change any pre-registered decision.

Pre-registration `sha256:f5f5013b2ff11209fbc5cf43a268530c361a369d64786e5fb7610df2dbec05b4`.

## generated: 810 calls, 27 families (19 with P0 calls)

Reproduction of `compare-generated-test-b1e-0.1.0+7b7bb8d67713.json`: **matches exactly**.

| System | P0 missed | False P0 | Over-triage | Cue F1 | Denied/past live | PPV of P0 at 35% / 10% / 5% prevalence |
|---|---|---|---|---|---|---|
| B0 rules | 84/285 | 0 | 77 | 0.7864 | 23 | 1.00 / 1.00 / 1.00 |
| Hybrid B0+B1 | 60/285 | 22 | 110 | 0.7614 | 43 | 0.91 / 0.68 / 0.50 |
| B1e only | 133/285 | 25 | 99 | 0.7102 | 20 | 0.86 / 0.55 / 0.37 |
| Hybrid B0+B1e | 47/285 | 31 | 106 | 0.8493 | 36 | 0.88 / 0.61 / 0.43 |
| Hybrid B0+B1 (refit on generator 2.2) | 55/285 | 29 | 104 | 0.83 | 59 | 0.89 / 0.62 / 0.43 |

Priority error sources:

- B0 rules: over: cue error 18, over: cues right (rubric/engine) 59, under: cue error 256
- Hybrid B0+B1: over: cue error 71, over: cues right (rubric/engine) 39, under: cue error 206
- B1e only: over: cue error 42, over: cues right (rubric/engine) 57, under: cue error 314, under: cues right (rubric/engine) 8
- Hybrid B0+B1e: over: cue error 54, over: cues right (rubric/engine) 52, under: cue error 139
- Hybrid B0+B1 (refit on generator 2.2): over: cue error 54, over: cues right (rubric/engine) 50, under: cue error 166

| A vs B | P0: clustered McNemar (A-only / B-only, X², p) | Families A / B better (sign test p) | Δ P0 missed, family bootstrap | Δ cue F1, family bootstrap | Δ over-triage, family bootstrap |
|---|---|---|---|---|---|
| Hybrid B0+B1e vs B0 rules | 37 / 0, X²=5.9264, p=0.0149 (11 of 19 families discordant) | 11 / 0 (p=0.000977) | -0.130 [-0.233, -0.050] | +0.063 [+0.028, +0.103] | +0.036 [+0.005, +0.079] |
| Hybrid B0+B1e vs Hybrid B0+B1 | 20 / 7, X²=2.4493, p=0.118 (9 of 19 families discordant) | 7 / 2 (p=0.18) | -0.046 [-0.122, +0.004] | +0.088 [+0.058, +0.126] | -0.005 [-0.051, +0.047] |
| Hybrid B0+B1e vs Hybrid B0+B1 (refit on generator 2.2) | 10 / 2, X²=2.9091, p=0.0881 (6 of 19 families discordant) | 5 / 1 (p=0.219) | -0.028 [-0.065, -0.003] | +0.019 [-0.000, +0.038] | +0.003 [-0.026, +0.030] |
| Hybrid B0+B1 (refit on generator 2.2) vs Hybrid B0+B1 | 14 / 9, X²=0.3333, p=0.564 (9 of 19 families discordant) | 7 / 2 (p=0.18) | -0.018 [-0.089, +0.038] | +0.069 [+0.039, +0.108] | -0.007 [-0.049, +0.032] |

## curated: 20 calls, 20 families (9 with P0 calls)

Reproduction of `compare-curated-test-b1e-0.1.0+7b7bb8d67713.json`: **matches exactly**.

| System | P0 missed | False P0 | Over-triage | Cue F1 | Denied/past live | PPV of P0 at 35% / 10% / 5% prevalence |
|---|---|---|---|---|---|---|
| B0 rules | 2/9 | 1 | 2 | 0.96 | 0 | 0.82 / 0.49 / 0.31 |
| Hybrid B0+B1 | 0/9 | 3 | 4 | 0.8736 | 1 | 0.66 / 0.29 / 0.16 |
| B1e only | 2/9 | 1 | 2 | 0.7826 | 1 | 0.82 / 0.49 / 0.31 |
| Hybrid B0+B1e | 0/9 | 1 | 2 | 0.95 | 1 | 0.86 / 0.55 / 0.37 |
| Hybrid B0+B1 (refit on generator 2.2) | 1/9 | 2 | 3 | 0.8941 | 1 | 0.72 / 0.35 / 0.20 |

Priority error sources:

- B0 rules: over: cues right (rubric/engine) 2, under: cue error 2
- Hybrid B0+B1: over: cue error 3, over: cues right (rubric/engine) 1
- B1e only: over: cue error 1, over: cues right (rubric/engine) 1, under: cue error 3
- Hybrid B0+B1e: over: cue error 1, over: cues right (rubric/engine) 1
- Hybrid B0+B1 (refit on generator 2.2): over: cue error 2, over: cues right (rubric/engine) 1, under: cue error 1

| A vs B | P0: clustered McNemar (A-only / B-only, X², p) | Families A / B better (sign test p) | Δ P0 missed, family bootstrap | Δ cue F1, family bootstrap | Δ over-triage, family bootstrap |
|---|---|---|---|---|---|
| Hybrid B0+B1e vs B0 rules | 2 / 0, X²=2.0, p=0.157 (2 of 9 families discordant) | 2 / 0 (p=0.5) | -0.222 [-0.556, +0.000] | -0.010 [-0.050, +0.031] | +0.000 [+0.000, +0.000] |
| Hybrid B0+B1e vs Hybrid B0+B1 | 0 / 0, X²=0.0, p=1 (0 of 9 families discordant) | 0 / 0 (p=1) | +0.000 [+0.000, +0.000] | +0.076 [+0.035, +0.117] | -0.100 [-0.250, +0.000] |
| Hybrid B0+B1e vs Hybrid B0+B1 (refit on generator 2.2) | 1 / 0, X²=1.0, p=0.317 (1 of 9 families discordant) | 1 / 0 (p=1) | -0.111 [-0.375, +0.000] | +0.056 [+0.013, +0.105] | -0.050 [-0.150, +0.000] |
| Hybrid B0+B1 (refit on generator 2.2) vs Hybrid B0+B1 | 0 / 1, X²=1.0, p=0.317 (1 of 9 families discordant) | 0 / 1 (p=1) | +0.111 [+0.000, +0.375] | +0.021 [-0.043, +0.079] | -0.050 [-0.150, +0.000] |

## challenge: 70 calls, 70 families (19 with P0 calls)

Reproduction of `compare-challenge-test-b1e-0.1.0+7b7bb8d67713.json`: **matches exactly**.

| System | P0 missed | False P0 | Over-triage | Cue F1 | Denied/past live | PPV of P0 at 35% / 10% / 5% prevalence |
|---|---|---|---|---|---|---|
| B0 rules | 8/19 | 5 | 24 | 0.7083 | 4 | 0.76 / 0.40 / 0.24 |
| Hybrid B0+B1 | 5/19 | 11 | 29 | 0.6667 | 9 | 0.65 / 0.28 / 0.15 |
| B1e only | 10/19 | 5 | 26 | 0.5493 | 11 | 0.72 / 0.35 / 0.20 |
| Hybrid B0+B1e | 5/19 | 9 | 31 | 0.6821 | 12 | 0.69 / 0.32 / 0.18 |
| Hybrid B0+B1 (refit on generator 2.2) | 2/19 | 10 | 28 | 0.6778 | 13 | 0.71 / 0.34 / 0.19 |

Priority error sources:

- B0 rules: over: cue error 10, over: cues right (rubric/engine) 14, under: cue error 14
- Hybrid B0+B1: over: cue error 17, over: cues right (rubric/engine) 12, under: cue error 8
- B1e only: over: cue error 19, over: cues right (rubric/engine) 7, under: cue error 17
- Hybrid B0+B1e: over: cue error 24, over: cues right (rubric/engine) 7, under: cue error 8
- Hybrid B0+B1 (refit on generator 2.2): over: cue error 20, over: cues right (rubric/engine) 8, under: cue error 7

| A vs B | P0: clustered McNemar (A-only / B-only, X², p) | Families A / B better (sign test p) | Δ P0 missed, family bootstrap | Δ cue F1, family bootstrap | Δ over-triage, family bootstrap |
|---|---|---|---|---|---|
| Hybrid B0+B1e vs B0 rules | 3 / 0, X²=3.0, p=0.0833 (3 of 19 families discordant) | 3 / 0 (p=0.25) | -0.158 [-0.333, +0.000] | -0.026 [-0.092, +0.034] | +0.100 [+0.043, +0.171] |
| Hybrid B0+B1e vs Hybrid B0+B1 | 2 / 2, X²=0.0, p=1 (4 of 19 families discordant) | 2 / 2 (p=1) | +0.000 [-0.210, +0.200] | +0.015 [-0.044, +0.078] | +0.029 [-0.043, +0.100] |
| Hybrid B0+B1e vs Hybrid B0+B1 (refit on generator 2.2) | 0 / 3, X²=3.0, p=0.0833 (3 of 19 families discordant) | 0 / 3 (p=0.25) | +0.158 [+0.000, +0.333] | +0.004 [-0.052, +0.060] | +0.043 [-0.014, +0.100] |
| Hybrid B0+B1 (refit on generator 2.2) vs Hybrid B0+B1 | 3 / 0, X²=3.0, p=0.0833 (3 of 19 families discordant) | 3 / 0 (p=0.25) | -0.158 [-0.333, +0.000] | +0.011 [-0.041, +0.064] | -0.014 [-0.057, +0.029] |

## Latency benchmark

810 calls, 50 warm-up calls, 3 repeats. Machine: {'platform': 'Windows-11-10.0.26300-SP0', 'processor': 'Intel64 Family 6 Model 186 Stepping 2, GenuineIntel', 'cpu_count': 20, 'python': '3.12.10', 'torch_threads': 14}.

| System | Run | p50 ms | p95 ms | p99 ms | max ms |
|---|---|---|---|---|---|
| B0 rules | 1 | 0.61 | 0.95 | 1.06 | 1.21 |
| B0 rules | 2 | 0.62 | 0.96 | 1.06 | 1.4 |
| B0 rules | 3 | 0.61 | 0.91 | 1.08 | 1.47 |
| Hybrid B0+B1e | 1 | 24.38 | 39.07 | 47.38 | 78.32 |
| Hybrid B0+B1e | 2 | 25.51 | 40.86 | 50.82 | 68.18 |
| Hybrid B0+B1e | 3 | 25.15 | 39.94 | 49.26 | 68.0 |

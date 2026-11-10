# Evaluation: B0-rules on dev, regression splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `43261a813eb834a73c7a3d7f6f9c0b3d375f1f6c` |
| Dataset | `data/eval/curated.jsonl` (`sha256:e581a2280a2579b226cf3d12f973af456fab4ddae2183b2e0cef8c931fdbcbfc`) |
| Parser / engine | `rules-parser-1.1.0` / `triage-engine-1.0.0` |
| Ruleset | `research-1.0.0` (`sha256:8f2637172d4e395686b22e54b40e38e97c3a1b9b8a98ea824bbddfa839a29c87`) |
| Schema | `2.0.0` |
| Python / lockfile | `3.12.10` / `sha256:f3a97a72ddc4ebb0b90f1fd11a3eb7f03d4f9dc26fa973056de6714bcacb466f` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (30 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 1.000 (15/15; 95% CI 1.000 to 1.000) |
| Critical under-triage (expected P0, predicted lower) | 0.000 (0/13; 95% CI 0.000 to 0.000) |
| Priority exact agreement | 0.800 (24/30; 95% CI 0.633 to 0.933) |
| Under-triage (any) | 0.067 (2/30; 95% CI 0.000 to 0.167) |
| Over-triage (any) | 0.133 (4/30; 95% CI 0.033 to 0.267) |
| Severity band exact | 0.800 (24/30; 95% CI 0.633 to 0.933) |
| Domain accuracy | 0.967 (29/30; 95% CI 0.900 to 1.000) |
| Location status accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Victim count accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Cue extraction micro P / R / F1 | 0.9706 / 1.0 / 0.9851 (F1 95% CI 0.9434 to 1.0) |
| Denied/past cues treated as live | 0 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 13 | 0 | 0 | 0 | 0 | 0 |
| **P1** | 0 | 3 | 0 | 0 | 0 | 0 |
| **P2** | 0 | 1 | 2 | 2 | 0 | 0 |
| **P3** | 0 | 0 | 0 | 5 | 0 | 0 |
| **P4** | 0 | 1 | 1 | 1 | 1 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 3 | 0 | 0 | 1.0 | 1.0 |
| ACTIVE_VIOLENCE | 1 | 0 | 0 | 1.0 | 1.0 |
| BREATHING_DIFFICULTY | 1 | 0 | 0 | 1.0 | 1.0 |
| CARDIAC_SYMPTOMS | 2 | 0 | 0 | 1.0 | 1.0 |
| CHILD_INVOLVED | 2 | 0 | 0 | 1.0 | 1.0 |
| FIRE_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| FIRE_SPREADING | 1 | 0 | 0 | 1.0 | 1.0 |
| INJURY_REPORTED | 3 | 0 | 0 | 1.0 | 1.0 |
| NOT_BREATHING | 8 | 0 | 0 | 1.0 | 1.0 |
| OCCUPANTS_TRAPPED | 1 | 0 | 0 | 1.0 | 1.0 |
| SMOKE_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| UNCONSCIOUS | 6 | 0 | 0 | 1.0 | 1.0 |
| WEAPON_PRESENT | 3 | 1 | 0 | 0.75 | 1.0 |

## Failures (6 cases)

- `fx-008`: priority P3 != P2
- `fx-021`: priority P1 != P2
- `fx-022`: spurious cues ['WEAPON_PRESENT']; priority P1 != P4
- `cu-103`: priority P3 != P4
- `cu-104`: priority P3 != P2
- `cu-119`: priority P2 != P4; domain unknown != ems

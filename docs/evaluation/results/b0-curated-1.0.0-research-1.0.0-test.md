# Evaluation: B0-rules on test splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `601797198e8b8f9022fa08e49f7fbc13a7c6d31d` |
| Dataset | `data/eval/curated.jsonl` (`sha256:e581a2280a2579b226cf3d12f973af456fab4ddae2183b2e0cef8c931fdbcbfc`) |
| Parser / engine | `rules-parser-1.0.0` / `triage-engine-1.0.0` |
| Ruleset | `research-1.0.0` (`sha256:8f2637172d4e395686b22e54b40e38e97c3a1b9b8a98ea824bbddfa839a29c87`) |
| Schema | `2.0.0` |
| Python / lockfile | `3.12.10` / `sha256:f3a97a72ddc4ebb0b90f1fd11a3eb7f03d4f9dc26fa973056de6714bcacb466f` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (20 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 0.857 (6/7; 95% CI 0.571 to 1.000) |
| Critical under-triage (expected P0, predicted lower) | 0.222 (2/9; 95% CI 0.000 to 0.556) |
| Priority exact agreement | 0.800 (16/20; 95% CI 0.600 to 0.950) |
| Under-triage (any) | 0.100 (2/20; 95% CI 0.000 to 0.250) |
| Over-triage (any) | 0.100 (2/20; 95% CI 0.000 to 0.250) |
| Severity band exact | 0.800 (16/20; 95% CI 0.600 to 0.950) |
| Domain accuracy | 0.850 (17/20; 95% CI 0.650 to 1.000) |
| Location status accuracy | 1.000 (20/20; 95% CI 1.000 to 1.000) |
| Victim count accuracy | 0.900 (18/20; 95% CI 0.750 to 1.000) |
| Cue extraction micro P / R / F1 | 1.0 / 0.9211 / 0.9589 (F1 95% CI 0.9118 to 1.0) |
| Denied/past cues treated as live | 0 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 7 | 2 | 0 | 0 | 0 | 0 |
| **P1** | 0 | 7 | 0 | 0 | 0 | 0 |
| **P2** | 1 | 0 | 2 | 0 | 0 | 0 |
| **P3** | 0 | 1 | 0 | 0 | 0 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 2 | 0 | 0 | 1.0 | 1.0 |
| ACTIVE_VIOLENCE | 2 | 0 | 0 | 1.0 | 1.0 |
| CHILD_INVOLVED | 3 | 0 | 0 | 1.0 | 1.0 |
| EXPLOSION_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| FIRE_REPORTED | 4 | 0 | 0 | 1.0 | 1.0 |
| FIRE_SPREADING | 1 | 0 | 0 | 1.0 | 1.0 |
| HAZARDOUS_ENVIRONMENT | 2 | 0 | 0 | 1.0 | 1.0 |
| INJURY_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| MULTIPLE_VICTIMS | 3 | 0 | 2 | 1.0 | 0.6 |
| NOT_BREATHING | 1 | 0 | 1 | 1.0 | 0.5 |
| OCCUPANTS_TRAPPED | 3 | 0 | 0 | 1.0 | 1.0 |
| OVERDOSE | 3 | 0 | 0 | 1.0 | 1.0 |
| SEIZURE | 1 | 0 | 0 | 1.0 | 1.0 |
| SMOKE_REPORTED | 2 | 0 | 0 | 1.0 | 1.0 |
| STROKE_SYMPTOMS | 1 | 0 | 0 | 1.0 | 1.0 |
| UNCONSCIOUS | 2 | 0 | 0 | 1.0 | 1.0 |
| WEAPON_PRESENT | 3 | 0 | 0 | 1.0 | 1.0 |

## Failures (7 cases)

- `fx-016`: missed cues ['MULTIPLE_VICTIMS']; victims None != 5
- `fx-019`: missed cues ['NOT_BREATHING']; priority P1 != P0
- `cu-111`: domain unknown != ems
- `cu-118`: missed cues ['MULTIPLE_VICTIMS']; priority P1 != P0; victims None != 'unknown'
- `cu-121`: domain unknown != ems
- `cu-122`: priority P1 != P3
- `cu-123`: priority P0 != P2; domain unknown != fire

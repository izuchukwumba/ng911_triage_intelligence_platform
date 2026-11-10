# Evaluation: B0-rules on dev, regression splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `eeaa228636b48a51adfef83c58ead252a93ec976` |
| Dataset | `data/eval/curated.jsonl` (`sha256:efe6e09839147de8fdecc7b9d7f2441a1439fbc4e38782747f027d8d7698283c`) |
| Parser / engine | `rules-parser-1.3.0` / `triage-engine-1.1.0` |
| Ruleset | `research-1.1.0` (`sha256:8f94610df1e285ca6c0c84e28e17ac80759f7bda03e50c716a09756a6406bf72`) |
| Schema | `2.0.0` |
| Python / lockfile | `3.12.10` / `sha256:f3a97a72ddc4ebb0b90f1fd11a3eb7f03d4f9dc26fa973056de6714bcacb466f` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (30 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 1.000 (15/15; 95% CI 1.000 to 1.000) |
| Critical under-triage (expected P0, predicted lower) | 0.000 (0/13; 95% CI 0.000 to 0.000) |
| Priority exact agreement | 0.867 (26/30; 95% CI 0.733 to 0.967) |
| Under-triage (any) | 0.000 (0/30; 95% CI 0.000 to 0.000) |
| Over-triage (any) | 0.133 (4/30; 95% CI 0.033 to 0.267) |
| Severity band exact | 0.867 (26/30; 95% CI 0.733 to 0.967) |
| Domain accuracy | 0.967 (29/30; 95% CI 0.900 to 1.000) |
| Location status accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Victim count accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Cue extraction micro P / R / F1 | 0.9714 / 1.0 / 0.9855 (F1 95% CI 0.9455 to 1.0) |
| Denied/past cues treated as live | 0 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 13 | 0 | 0 | 0 | 0 | 0 |
| **P1** | 0 | 3 | 0 | 0 | 0 | 0 |
| **P2** | 0 | 1 | 4 | 0 | 0 | 0 |
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
| UNABLE_TO_GET_UP | 1 | 0 | 0 | 1.0 | 1.0 |
| UNCONSCIOUS | 6 | 0 | 0 | 1.0 | 1.0 |
| WEAPON_PRESENT | 3 | 1 | 0 | 0.75 | 1.0 |

## Failures (4 cases)

- `fx-021`: priority P1 != P2
- `fx-022`: spurious cues ['WEAPON_PRESENT']; priority P1 != P4
- `cu-103`: priority P3 != P4
- `cu-119`: priority P2 != P4; domain unknown != ems

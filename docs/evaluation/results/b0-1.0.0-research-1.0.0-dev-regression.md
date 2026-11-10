# Evaluation: B0-rules on dev, regression splits

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

## Results (30 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 0.867 (13/15; 95% CI 0.667 to 1.000) |
| Critical under-triage (expected P0, predicted lower) | 0.077 (1/13; 95% CI 0.000 to 0.231) |
| Priority exact agreement | 0.667 (20/30; 95% CI 0.500 to 0.833) |
| Under-triage (any) | 0.100 (3/30; 95% CI 0.000 to 0.233) |
| Over-triage (any) | 0.233 (7/30; 95% CI 0.100 to 0.400) |
| Severity band exact | 0.667 (20/30; 95% CI 0.500 to 0.833) |
| Domain accuracy | 0.833 (25/30; 95% CI 0.700 to 0.967) |
| Location status accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Victim count accuracy | 1.000 (30/30; 95% CI 1.000 to 1.000) |
| Cue extraction micro P / R / F1 | 0.9355 / 0.8788 / 0.9062 (F1 95% CI 0.7869 to 0.9756) |
| Denied/past cues treated as live | 1 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 12 | 0 | 1 | 0 | 0 | 0 |
| **P1** | 0 | 3 | 0 | 0 | 0 | 0 |
| **P2** | 0 | 1 | 2 | 2 | 0 | 0 |
| **P3** | 0 | 0 | 3 | 2 | 0 | 0 |
| **P4** | 0 | 2 | 0 | 1 | 1 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 3 | 0 | 0 | 1.0 | 1.0 |
| ACTIVE_VIOLENCE | 1 | 0 | 0 | 1.0 | 1.0 |
| BREATHING_DIFFICULTY | 1 | 0 | 0 | 1.0 | 1.0 |
| CARDIAC_SYMPTOMS | 2 | 1 | 0 | 0.6667 | 1.0 |
| CHILD_INVOLVED | 2 | 0 | 0 | 1.0 | 1.0 |
| FIRE_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| FIRE_SPREADING | 1 | 0 | 0 | 1.0 | 1.0 |
| INJURY_REPORTED | 1 | 0 | 2 | 1.0 | 0.3333 |
| NOT_BREATHING | 7 | 0 | 1 | 1.0 | 0.875 |
| OCCUPANTS_TRAPPED | 1 | 0 | 0 | 1.0 | 1.0 |
| SMOKE_REPORTED | 1 | 0 | 0 | 1.0 | 1.0 |
| UNCONSCIOUS | 5 | 0 | 1 | 1.0 | 0.8333 |
| WEAPON_PRESENT | 3 | 1 | 0 | 0.75 | 1.0 |

## Failures (12 cases)

- `fx-008`: missed cues ['INJURY_REPORTED']; priority P3 != P2
- `fx-012`: missed cues ['INJURY_REPORTED']
- `fx-013`: domain unknown != other
- `fx-017`: priority P2 != P3; domain unknown != ems
- `fx-021`: priority P1 != P2
- `fx-022`: spurious cues ['WEAPON_PRESENT']; priority P1 != P4
- `cu-103`: priority P3 != P4
- `cu-104`: priority P3 != P2
- `cu-116`: priority P2 != P3; domain unknown != ems
- `cu-119`: spurious cues ['CARDIAC_SYMPTOMS']; denied/past cues treated as live ['CARDIAC_SYMPTOMS']; priority P1 != P4
- `cu-120`: priority P2 != P3; domain unknown != police
- `cu-126`: missed cues ['NOT_BREATHING', 'UNCONSCIOUS']; priority P2 != P0; domain unknown != ems

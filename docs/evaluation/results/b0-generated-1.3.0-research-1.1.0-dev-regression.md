# Evaluation: B0-rules on dev, regression splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `eeaa228636b48a51adfef83c58ead252a93ec976` |
| Dataset | `data/eval/generated-1.0.0-seed42.jsonl` (`sha256:a064e9dbe885a3448314e654c2650c7e20b6e200c29c1b26c45f1bea9b045555`) |
| Parser / engine | `rules-parser-1.3.0` / `triage-engine-1.1.0` |
| Ruleset | `research-1.1.0` (`sha256:8f94610df1e285ca6c0c84e28e17ac80759f7bda03e50c716a09756a6406bf72`) |
| Schema | `2.0.0` |
| Python / lockfile | `3.12.10` / `sha256:f3a97a72ddc4ebb0b90f1fd11a3eb7f03d4f9dc26fa973056de6714bcacb466f` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (300 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 0.985 (67/68; 95% CI 0.956 to 1.000) |
| Critical under-triage (expected P0, predicted lower) | 0.009 (1/109; 95% CI 0.000 to 0.028) |
| Priority exact agreement | 0.937 (281/300; 95% CI 0.910 to 0.963) |
| Under-triage (any) | 0.010 (3/300; 95% CI 0.000 to 0.023) |
| Over-triage (any) | 0.053 (16/300; 95% CI 0.027 to 0.080) |
| Severity band exact | 0.927 (278/300; 95% CI 0.893 to 0.957) |
| Domain accuracy | 0.883 (265/300; 95% CI 0.847 to 0.920) |
| Location status accuracy | 0.990 (297/300; 95% CI 0.977 to 1.000) |
| Victim count accuracy | 0.993 (298/300; 95% CI 0.983 to 1.000) |
| Cue extraction micro P / R / F1 | 1.0 / 0.9782 / 0.989 (F1 95% CI 0.9817 to 0.9949) |
| Denied/past cues treated as live | 0 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 108 | 0 | 1 | 0 | 0 | 0 |
| **P1** | 0 | 108 | 2 | 0 | 0 | 0 |
| **P2** | 0 | 0 | 46 | 0 | 0 | 0 |
| **P3** | 0 | 0 | 0 | 19 | 0 | 0 |
| **P4** | 0 | 0 | 16 | 0 | 0 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 29 | 0 | 1 | 1.0 | 0.9667 |
| CARDIAC_SYMPTOMS | 27 | 0 | 1 | 1.0 | 0.9643 |
| CHILD_INVOLVED | 34 | 0 | 1 | 1.0 | 0.9714 |
| FIRE_REPORTED | 29 | 0 | 1 | 1.0 | 0.9667 |
| HAZARDOUS_ENVIRONMENT | 26 | 0 | 1 | 1.0 | 0.963 |
| INJURY_REPORTED | 60 | 0 | 0 | 1.0 | 1.0 |
| MULTIPLE_VICTIMS | 36 | 0 | 2 | 1.0 | 0.9474 |
| NOT_BREATHING | 19 | 0 | 0 | 1.0 | 1.0 |
| OCCUPANTS_TRAPPED | 30 | 0 | 0 | 1.0 | 1.0 |
| OVERDOSE | 30 | 0 | 0 | 1.0 | 1.0 |
| SEIZURE | 30 | 0 | 0 | 1.0 | 1.0 |
| SMOKE_REPORTED | 26 | 0 | 2 | 1.0 | 0.9286 |
| UNCONSCIOUS | 18 | 0 | 1 | 1.0 | 0.9474 |
| WEAPON_PRESENT | 54 | 0 | 0 | 1.0 | 1.0 |

## Failures (42 cases)

- `g42-0037`: priority P2 != P4; domain unknown != police
- `g42-0039`: priority P2 != P4; domain unknown != ems
- `g42-0056`: priority P2 != P4; domain unknown != ems
- `g42-0073`: domain unknown != ems
- `g42-0079`: priority P2 != P4; domain unknown != fire
- `g42-0081`: priority P2 != P4; domain unknown != hazmat
- `g42-0107`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P0
- `g42-0115`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g42-0117`: domain unknown != ems
- `g42-0122`: priority P2 != P4; domain unknown != police
- `g42-0156`: priority P2 != P4; domain unknown != police
- `g42-0158`: domain unknown != ems
- `g42-0206`: location missing != present
- `g42-0209`: domain unknown != ems
- `g42-0231`: missed cues ['MULTIPLE_VICTIMS']; victims None != 5
- `g42-0249`: missed cues ['SMOKE_REPORTED']; domain unknown != fire
- `g42-0258`: priority P2 != P4; domain unknown != police
- `g42-0277`: domain unknown != ems
- `g42-0287`: domain unknown != ems
- `g42-0299`: missed cues ['FIRE_REPORTED']; domain ems != fire
- `g42-0304`: priority P2 != P4; domain unknown != ems
- `g42-0317`: priority P2 != P4; domain unknown != fire
- `g42-0326`: priority P2 != P4; domain unknown != police
- `g42-0336`: domain unknown != hazmat
- `g42-0338`: domain unknown != ems
- `g42-0342`: domain ems != police
- `g42-0343`: priority P2 != P4; domain unknown != police
- `g42-0353`: priority P2 != P4; domain unknown != hazmat
- `g42-0355`: priority P2 != P4; domain unknown != ems
- `g42-0359`: domain ems != police
- `g42-0376`: missed cues ['ACTIVE_BLEEDING']
- `g42-0387`: priority P2 != P4; domain unknown != hazmat
- `g42-0402`: missed cues ['SMOKE_REPORTED']; domain unknown != fire
- `g42-0411`: location present != missing
- `g42-0425`: missed cues ['CHILD_INVOLVED']; domain unknown != ems
- `g42-0440`: priority P2 != P4; domain unknown != ems
- `g42-0457`: domain unknown != ems
- `g42-0474`: domain unknown != ems; location missing != present
- `g42-0476`: missed cues ['UNCONSCIOUS']
- `g42-0491`: missed cues ['MULTIPLE_VICTIMS']; priority P2 != P1; victims None != 3
- `g42-0498`: domain unknown != ems
- `g42-0508`: domain unknown != ems

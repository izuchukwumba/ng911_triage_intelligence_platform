# Evaluation: B0-rules on dev, regression splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `e202593004e5a0e75ffab0d7e2448172b79e3fab` |
| Dataset | `data/eval/generated-1.0.0-seed42.jsonl` (`sha256:a064e9dbe885a3448314e654c2650c7e20b6e200c29c1b26c45f1bea9b045555`) |
| Parser / engine | `rules-parser-1.2.0` / `triage-engine-1.1.0` |
| Ruleset | `research-1.1.0` (`sha256:8f94610df1e285ca6c0c84e28e17ac80759f7bda03e50c716a09756a6406bf72`) |
| Schema | `2.0.0` |
| Python / lockfile | `3.12.10` / `sha256:f3a97a72ddc4ebb0b90f1fd11a3eb7f03d4f9dc26fa973056de6714bcacb466f` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (300 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 0.926 (63/68; 95% CI 0.853 to 0.985) |
| Critical under-triage (expected P0, predicted lower) | 0.083 (9/109; 95% CI 0.037 to 0.138) |
| Priority exact agreement | 0.870 (261/300; 95% CI 0.833 to 0.907) |
| Under-triage (any) | 0.077 (23/300; 95% CI 0.047 to 0.107) |
| Over-triage (any) | 0.053 (16/300; 95% CI 0.027 to 0.080) |
| Severity band exact | 0.860 (258/300; 95% CI 0.820 to 0.900) |
| Domain accuracy | 0.740 (222/300; 95% CI 0.690 to 0.790) |
| Location status accuracy | 0.990 (297/300; 95% CI 0.977 to 1.000) |
| Victim count accuracy | 0.993 (298/300; 95% CI 0.983 to 1.000) |
| Cue extraction micro P / R / F1 | 1.0 / 0.9279 / 0.9626 (F1 95% CI 0.9488 to 0.9763) |
| Denied/past cues treated as live | 0 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 100 | 0 | 9 | 0 | 0 | 0 |
| **P1** | 0 | 96 | 14 | 0 | 0 | 0 |
| **P2** | 0 | 0 | 46 | 0 | 0 | 0 |
| **P3** | 0 | 0 | 0 | 19 | 0 | 0 |
| **P4** | 0 | 0 | 16 | 0 | 0 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 29 | 0 | 1 | 1.0 | 0.9667 |
| CARDIAC_SYMPTOMS | 27 | 0 | 1 | 1.0 | 0.9643 |
| CHILD_INVOLVED | 31 | 0 | 4 | 1.0 | 0.8857 |
| FIRE_REPORTED | 29 | 0 | 1 | 1.0 | 0.9667 |
| HAZARDOUS_ENVIRONMENT | 26 | 0 | 1 | 1.0 | 0.963 |
| INJURY_REPORTED | 60 | 0 | 0 | 1.0 | 1.0 |
| MULTIPLE_VICTIMS | 36 | 0 | 2 | 1.0 | 0.9474 |
| NOT_BREATHING | 19 | 0 | 0 | 1.0 | 1.0 |
| OCCUPANTS_TRAPPED | 26 | 0 | 4 | 1.0 | 0.8667 |
| OVERDOSE | 30 | 0 | 0 | 1.0 | 1.0 |
| SEIZURE | 14 | 0 | 16 | 1.0 | 0.4667 |
| SMOKE_REPORTED | 26 | 0 | 2 | 1.0 | 0.9286 |
| UNCONSCIOUS | 18 | 0 | 1 | 1.0 | 0.9474 |
| WEAPON_PRESENT | 54 | 0 | 0 | 1.0 | 1.0 |

## Failures (90 cases)

- `g42-0007`: missed cues ['CHILD_INVOLVED', 'SEIZURE']; priority P2 != P0; domain unknown != ems
- `g42-0009`: domain unknown != ems
- `g42-0024`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0037`: priority P2 != P4; domain unknown != police
- `g42-0039`: priority P2 != P4; domain unknown != ems
- `g42-0041`: missed cues ['SEIZURE']; priority P2 != P0
- `g42-0056`: priority P2 != P4; domain unknown != ems
- `g42-0061`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0
- `g42-0073`: domain unknown != ems
- `g42-0075`: domain unknown != ems
- `g42-0079`: priority P2 != P4; domain unknown != fire
- `g42-0081`: priority P2 != P4; domain unknown != hazmat
- `g42-0092`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0107`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P0
- `g42-0111`: domain unknown != ems
- `g42-0115`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g42-0117`: domain unknown != ems
- `g42-0122`: priority P2 != P4; domain unknown != police
- `g42-0145`: domain unknown != ems
- `g42-0156`: priority P2 != P4; domain unknown != police
- `g42-0158`: domain unknown != ems
- `g42-0160`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0162`: domain unknown != ems
- `g42-0175`: domain unknown != ems
- `g42-0177`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0194`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0196`: domain unknown != ems
- `g42-0197`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0
- `g42-0206`: location missing != present
- `g42-0209`: domain unknown != ems
- `g42-0211`: domain unknown != ems
- `g42-0213`: domain unknown != ems
- `g42-0226`: domain unknown != ems
- `g42-0231`: missed cues ['MULTIPLE_VICTIMS']; victims None != 5
- `g42-0245`: domain unknown != ems
- `g42-0249`: missed cues ['SMOKE_REPORTED']; domain unknown != fire
- `g42-0258`: priority P2 != P4; domain unknown != police
- `g42-0262`: domain unknown != ems
- `g42-0277`: domain unknown != ems
- `g42-0279`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0281`: domain unknown != ems
- `g42-0287`: domain unknown != ems
- `g42-0298`: domain unknown != ems
- `g42-0299`: missed cues ['FIRE_REPORTED']; domain ems != fire
- `g42-0304`: priority P2 != P4; domain unknown != ems
- `g42-0313`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0315`: domain unknown != ems
- `g42-0317`: priority P2 != P4; domain unknown != fire
- `g42-0326`: priority P2 != P4; domain unknown != police
- `g42-0330`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0332`: domain unknown != ems
- `g42-0336`: domain unknown != hazmat
- `g42-0338`: domain unknown != ems
- `g42-0342`: domain ems != police
- `g42-0343`: priority P2 != P4; domain unknown != police
- `g42-0347`: missed cues ['CHILD_INVOLVED', 'SEIZURE']; priority P2 != P0; domain unknown != ems
- `g42-0353`: priority P2 != P4; domain unknown != hazmat
- `g42-0355`: priority P2 != P4; domain unknown != ems
- `g42-0359`: domain ems != police
- `g42-0362`: domain unknown != ems
- `g42-0364`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0366`: domain unknown != ems
- `g42-0367`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0
- `g42-0376`: missed cues ['ACTIVE_BLEEDING']
- `g42-0379`: domain unknown != ems
- `g42-0383`: domain unknown != ems
- `g42-0387`: priority P2 != P4; domain unknown != hazmat
- `g42-0398`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0400`: domain unknown != ems
- `g42-0402`: missed cues ['SMOKE_REPORTED']; domain unknown != fire
- `g42-0411`: location present != missing
- `g42-0415`: missed cues ['CHILD_INVOLVED', 'SEIZURE']; priority P2 != P0; domain unknown != ems
- `g42-0417`: domain unknown != ems
- `g42-0425`: missed cues ['CHILD_INVOLVED']; domain unknown != ems
- `g42-0432`: domain unknown != ems
- `g42-0434`: domain unknown != ems
- `g42-0435`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0
- `g42-0440`: priority P2 != P4; domain unknown != ems
- `g42-0447`: domain unknown != ems
- `g42-0449`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0451`: domain unknown != ems
- `g42-0457`: domain unknown != ems
- `g42-0466`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g42-0468`: domain unknown != ems
- `g42-0474`: domain unknown != ems; location missing != present
- `g42-0476`: missed cues ['UNCONSCIOUS']
- `g42-0491`: missed cues ['MULTIPLE_VICTIMS']; priority P2 != P1; victims None != 3
- `g42-0498`: domain unknown != ems
- `g42-0502`: domain unknown != ems
- `g42-0508`: domain unknown != ems

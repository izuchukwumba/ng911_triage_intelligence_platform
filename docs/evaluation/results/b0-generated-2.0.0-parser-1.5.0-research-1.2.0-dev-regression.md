# Evaluation: B0-rules on dev, regression splits

> Synthetic, author-labelled data. These numbers describe this dataset only; they are not evidence of real-world dispatch accuracy (design v1.2, section 16.3).

## Reproducibility

| Item | Value |
|---|---|
| Git commit | `6da0afac2cca0df7ae2dbff9b5bbd85f27f8ea23` |
| Dataset | `data/eval/generated-2.0.0-seed42.jsonl` (`sha256:fb4290e8dfb580db23e6c1f34f7b380ddf518cfc557a46d2b10e6c22530a8f48`) |
| Parser / engine | `rules-parser-1.5.0` / `triage-engine-1.2.0` |
| Ruleset | `research-1.2.0` (`sha256:69fdb910c1a9f4ec5a0672482cd39352683d9778cffd706c694efcb48b4e44b2`) |
| Schema | `2.6.0` |
| Python / lockfile | `3.12.10` / `sha256:9a0736a7c87bec1d86d14dc5fd57d431c56995a9dcda3735c04da78de223f020` |
| Seed / bootstrap | `20261109` / percentile, 2000 resamples, 95% |

## Results (1188 cases)

| Metric | Value |
|---|---|
| Critical-cue sensitivity | 0.686 (129/188; 95% CI 0.617 to 0.750) |
| Critical under-triage (expected P0, predicted lower) | 0.305 (102/334; 95% CI 0.258 to 0.356) |
| Priority exact agreement | 0.638 (758/1188; 95% CI 0.610 to 0.665) |
| Under-triage (any) | 0.265 (315/1188; 95% CI 0.242 to 0.290) |
| Over-triage (any) | 0.097 (115/1188; 95% CI 0.081 to 0.115) |
| Severity band exact | 0.621 (738/1188; 95% CI 0.593 to 0.649) |
| Domain accuracy | 0.539 (640/1188; 95% CI 0.510 to 0.567) |
| Location status accuracy | 0.969 (1151/1188; 95% CI 0.959 to 0.979) |
| Victim count accuracy | 0.981 (1165/1188; 95% CI 0.973 to 0.987) |
| Cue extraction micro P / R / F1 | 0.9577 / 0.7561 / 0.8451 (F1 95% CI 0.8297 to 0.8596) |
| Denied/past cues treated as live | 1 |

## Priority confusion (rows: expected, columns: predicted)

| | P0 | P1 | P2 | P3 | P4 | none |
|---|---|---|---|---|---|---|
| **P0** | 232 | 11 | 51 | 40 | 0 | 0 |
| **P1** | 23 | 320 | 172 | 28 | 0 | 0 |
| **P2** | 0 | 0 | 189 | 13 | 0 | 0 |
| **P3** | 0 | 0 | 30 | 17 | 0 | 0 |
| **P4** | 0 | 0 | 50 | 12 | 0 | 0 |

## Per-cue extraction

| Cue | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| ACTIVE_BLEEDING | 45 | 0 | 14 | 1.0 | 0.7627 |
| ACTIVE_VIOLENCE | 19 | 4 | 7 | 0.8261 | 0.7308 |
| ALLERGIC_REACTION | 22 | 0 | 4 | 1.0 | 0.8462 |
| BREATHING_DIFFICULTY | 36 | 0 | 20 | 1.0 | 0.6429 |
| BURN_INJURY | 23 | 0 | 1 | 1.0 | 0.9583 |
| CARDIAC_SYMPTOMS | 6 | 0 | 25 | 1.0 | 0.1935 |
| CHILDBIRTH | 27 | 0 | 4 | 1.0 | 0.871 |
| CHILD_INVOLVED | 143 | 6 | 5 | 0.9597 | 0.9662 |
| DIABETIC_EMERGENCY | 24 | 0 | 7 | 1.0 | 0.7742 |
| DROWNING | 16 | 0 | 14 | 1.0 | 0.5333 |
| ELECTROCUTION | 28 | 0 | 1 | 1.0 | 0.9655 |
| EXPLOSION_REPORTED | 21 | 0 | 9 | 1.0 | 0.7 |
| FALL_FROM_HEIGHT | 20 | 0 | 10 | 1.0 | 0.6667 |
| FIRE_REPORTED | 113 | 1 | 0 | 0.9912 | 1.0 |
| FIRE_SPREADING | 13 | 0 | 11 | 1.0 | 0.5417 |
| HAZARDOUS_ENVIRONMENT | 19 | 0 | 37 | 1.0 | 0.3393 |
| INJURY_REPORTED | 147 | 11 | 13 | 0.9304 | 0.9187 |
| INTRUDER_PRESENT | 10 | 0 | 17 | 1.0 | 0.3704 |
| MISSING_PERSON | 20 | 0 | 10 | 1.0 | 0.6667 |
| MULTIPLE_VICTIMS | 86 | 19 | 3 | 0.819 | 0.9663 |
| NOT_BREATHING | 49 | 0 | 7 | 1.0 | 0.875 |
| OCCUPANTS_TRAPPED | 29 | 0 | 31 | 1.0 | 0.4833 |
| OVERDOSE | 13 | 0 | 18 | 1.0 | 0.4194 |
| POISONING | 26 | 0 | 2 | 1.0 | 0.9286 |
| SEIZURE | 15 | 0 | 16 | 1.0 | 0.4839 |
| SELF_HARM_RISK | 12 | 0 | 15 | 1.0 | 0.4444 |
| SMOKE_REPORTED | 26 | 0 | 1 | 1.0 | 0.963 |
| STROKE_SYMPTOMS | 9 | 0 | 20 | 1.0 | 0.3103 |
| TRAFFIC_COLLISION | 31 | 0 | 25 | 1.0 | 0.5536 |
| UNABLE_TO_GET_UP | 30 | 3 | 0 | 0.9091 | 1.0 |
| UNCONSCIOUS | 51 | 9 | 21 | 0.85 | 0.7083 |
| WEAPON_PRESENT | 71 | 0 | 19 | 1.0 | 0.7889 |

## Failures (658 cases)

- `g2s42-0002`: missed cues ['CHILD_INVOLVED']
- `g2s42-0003`: missed cues ['UNCONSCIOUS']; priority P2 != P0
- `g2s42-0004`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-0006`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-0007`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-0009`: domain unknown != ems
- `g2s42-0011`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0013`: missed cues ['DIABETIC_EMERGENCY']; priority P2 != P1; domain unknown != ems
- `g2s42-0015`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-0017`: priority P2 != P4; domain unknown != ems
- `g2s42-0026`: domain unknown != police
- `g2s42-0027`: priority P3 != P4
- `g2s42-0029`: priority P2 != P4; domain unknown != police
- `g2s42-0031`: spurious cues ['ACTIVE_VIOLENCE']; domain police != ems
- `g2s42-0038`: domain unknown != ems
- `g2s42-0047`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-0054`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0058`: domain unknown != fire
- `g2s42-0060`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-0061`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0063`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0069`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0070`: priority P2 != P4; domain unknown != ems
- `g2s42-0073`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0077`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0081`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-0083`: domain unknown != ems
- `g2s42-0085`: domain unknown != ems
- `g2s42-0089`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P2 != P0; domain unknown != police
- `g2s42-0092`: missed cues ['WEAPON_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0093`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; victims 2 != None
- `g2s42-0095`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0097`: priority P3 != P4; domain unknown != ems
- `g2s42-0099`: domain unknown != police
- `g2s42-0101`: missed cues ['ACTIVE_BLEEDING']; priority P2 != P1; domain unknown != ems
- `g2s42-0104`: domain unknown != ems
- `g2s42-0106`: missed cues ['DROWNING']
- `g2s42-0112`: priority P2 != P4; domain unknown != ems
- `g2s42-0113`: domain ems != police
- `g2s42-0124`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-0126`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-0127`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0130`: priority P2 != P3; domain unknown != police
- `g2s42-0132`: location missing != present
- `g2s42-0136`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-0139`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P2 != P0; domain unknown != ems
- `g2s42-0143`: domain unknown != ems
- `g2s42-0149`: domain hazmat != ems
- `g2s42-0153`: spurious cues ['CHILD_INVOLVED']; priority P0 != P1; domain unknown != ems
- `g2s42-0155`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P3 != P0; domain unknown != police
- `g2s42-0158`: domain unknown != police
- `g2s42-0159`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police
- `g2s42-0161`: priority P2 != P4; domain unknown != police
- `g2s42-0163`: missed cues ['SELF_HARM_RISK']; priority P3 != P0; domain unknown != ems
- `g2s42-0165`: domain unknown != police
- `g2s42-0167`: domain unknown != ems
- `g2s42-0179`: domain ems != police
- `g2s42-0181`: missed cues ['TRAFFIC_COLLISION']; priority P2 != P1
- `g2s42-0184`: location missing != present
- `g2s42-0186`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0192`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-0193`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0195`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0196`: priority P2 != P3; domain unknown != police
- `g2s42-0200`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0201`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0202`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0204`: location missing != present
- `g2s42-0207`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0209`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0213`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-0215`: priority P2 != P4; domain unknown != ems
- `g2s42-0217`: domain unknown != ems
- `g2s42-0219`: spurious cues ['CHILD_INVOLVED']; priority P0 != P1; domain unknown != ems
- `g2s42-0221`: missed cues ['WEAPON_PRESENT']; domain ems != police
- `g2s42-0223`: priority P2 != P4; domain unknown != police
- `g2s42-0224`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0225`: priority P3 != P4; location missing != present
- `g2s42-0227`: domain unknown != police
- `g2s42-0229`: priority P2 != P4; domain unknown != ems
- `g2s42-0231`: domain ems != police; victims None != 3
- `g2s42-0244`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-0245`: priority P3 != P4; domain ems != police
- `g2s42-0247`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2; domain unknown != ems
- `g2s42-0248`: location missing != present
- `g2s42-0256`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-0258`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-0266`: location missing != present
- `g2s42-0267`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0268`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0271`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0273`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0275`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0277`: missed cues ['DIABETIC_EMERGENCY']; priority P3 != P0; domain unknown != ems
- `g2s42-0281`: domain unknown != ems
- `g2s42-0283`: missed cues ['ALLERGIC_REACTION']; priority P2 != P1; domain unknown != ems
- `g2s42-0285`: location missing != present
- `g2s42-0290`: domain unknown != police
- `g2s42-0291`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police
- `g2s42-0293`: domain unknown != police
- `g2s42-0295`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-0300`: priority P2 != P4; domain unknown != ems
- `g2s42-0302`: missed cues ['ELECTROCUTION']; priority P3 != P0; domain unknown != ems
- `g2s42-0304`: missed cues ['DROWNING', 'NOT_BREATHING']; priority P2 != P0; domain unknown != ems
- `g2s42-0308`: domain unknown != ems
- `g2s42-0311`: domain ems != police
- `g2s42-0313`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-0318`: spurious cues ['FIRE_REPORTED']; denied/past cues treated as live ['FIRE_REPORTED']; priority P2 != P4
- `g2s42-0322`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-0324`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-0325`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0327`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0328`: priority P2 != P3; domain unknown != police
- `g2s42-0333`: domain unknown != ems
- `g2s42-0334`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0343`: missed cues ['DIABETIC_EMERGENCY']; priority P2 != P1; domain unknown != ems
- `g2s42-0347`: domain unknown != ems
- `g2s42-0353`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P3 != P0; domain unknown != police
- `g2s42-0355`: domain unknown != police
- `g2s42-0356`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0359`: domain unknown != police
- `g2s42-0361`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-0363`: missed cues ['MISSING_PERSON']; priority P2 != P1; domain ems != police
- `g2s42-0365`: missed cues ['ACTIVE_BLEEDING']; priority P3 != P0; domain unknown != ems
- `g2s42-0370`: missed cues ['DROWNING']
- `g2s42-0376`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-0377`: domain ems != police
- `g2s42-0379`: missed cues ['INJURY_REPORTED']; domain unknown != ems
- `g2s42-0388`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-0390`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-0393`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0399`: domain unknown != ems
- `g2s42-0400`: priority P2 != P4; domain unknown != ems
- `g2s42-0403`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P2 != P0; domain unknown != ems
- `g2s42-0405`: missed cues ['SEIZURE']; priority P2 != P0
- `g2s42-0407`: missed cues ['STROKE_SYMPTOMS']; priority P3 != P0; domain unknown != ems
- `g2s42-0411`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-0413`: domain unknown != ems
- `g2s42-0419`: missed cues ['WEAPON_PRESENT']; priority P1 != P0; domain ems != police
- `g2s42-0422`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0425`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0427`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-0429`: domain unknown != police
- `g2s42-0431`: missed cues ['ACTIVE_BLEEDING']; priority P2 != P1; domain unknown != ems
- `g2s42-0442`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-0443`: domain ems != police
- `g2s42-0445`: missed cues ['TRAFFIC_COLLISION']; priority P2 != P1
- `g2s42-0448`: priority P2 != P4; domain unknown != fire
- `g2s42-0453`: priority P2 != P4; domain unknown != fire
- `g2s42-0454`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire; location present != missing
- `g2s42-0456`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-0459`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1; location present != missing
- `g2s42-0460`: priority P2 != P3; domain unknown != police
- `g2s42-0464`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0465`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0466`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-0468`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0469`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0471`: domain unknown != ems
- `g2s42-0473`: missed cues ['STROKE_SYMPTOMS']; priority P3 != P0; domain unknown != ems
- `g2s42-0477`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-0479`: domain hazmat != ems
- `g2s42-0487`: domain unknown != police
- `g2s42-0488`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0491`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0493`: domain unknown != ems
- `g2s42-0495`: missed cues ['CHILD_INVOLVED', 'MISSING_PERSON']; priority P2 != P1; domain unknown != police; location present != missing
- `g2s42-0504`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-0506`: domain unknown != ems
- `g2s42-0509`: priority P2 != P4; domain unknown != police
- `g2s42-0516`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0522`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-0525`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1; location present != missing
- `g2s42-0526`: priority P2 != P3; domain unknown != police
- `g2s42-0531`: domain unknown != ems
- `g2s42-0534`: domain unknown != ems
- `g2s42-0535`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-0537`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0539`: priority P2 != P4; domain unknown != ems
- `g2s42-0541`: missed cues ['DIABETIC_EMERGENCY']; priority P2 != P0
- `g2s42-0545`: domain unknown != ems
- `g2s42-0554`: location missing != present
- `g2s42-0555`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police
- `g2s42-0557`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0559`: domain unknown != ems
- `g2s42-0561`: missed cues ['MISSING_PERSON']; domain unknown != police
- `g2s42-0564`: priority P2 != P4; domain unknown != ems
- `g2s42-0572`: domain unknown != ems
- `g2s42-0574`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-0575`: domain unknown != police; location present != conflicting
- `g2s42-0588`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-0589`: priority P2 != P4; domain unknown != hazmat
- `g2s42-0591`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0592`: priority P2 != P3; domain unknown != police
- `g2s42-0596`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0597`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0598`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0603`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0605`: domain unknown != ems
- `g2s42-0609`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-0611`: domain unknown != ems
- `g2s42-0613`: missed cues ['ALLERGIC_REACTION']; priority P2 != P1; domain unknown != ems
- `g2s42-0620`: missed cues ['WEAPON_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0621`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police; location present != missing
- `g2s42-0623`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0629`: domain unknown != ems
- `g2s42-0634`: missed cues ['DROWNING']
- `g2s42-0641`: domain unknown != police
- `g2s42-0648`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0652`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-0654`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-0655`: priority P2 != P4; domain unknown != hazmat
- `g2s42-0657`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0658`: priority P2 != P3; domain unknown != police
- `g2s42-0663`: domain unknown != ems
- `g2s42-0666`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0667`: missed cues ['CARDIAC_SYMPTOMS', 'MULTIPLE_VICTIMS']; priority P3 != P0; victims None != 2
- `g2s42-0669`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0671`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0675`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-0677`: domain unknown != ems
- `g2s42-0683`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P2 != P0; domain unknown != police
- `g2s42-0685`: domain unknown != police
- `g2s42-0687`: priority P2 != P4; domain unknown != police
- `g2s42-0689`: priority P2 != P4; domain unknown != police
- `g2s42-0691`: domain unknown != ems
- `g2s42-0695`: missed cues ['ACTIVE_BLEEDING']; priority P3 != P0; domain unknown != ems
- `g2s42-0696`: domain unknown != ems
- `g2s42-0707`: domain unknown != police
- `g2s42-0714`: priority P3 != P4
- `g2s42-0718`: domain unknown != fire
- `g2s42-0720`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-0721`: priority P2 != P4; domain unknown != hazmat
- `g2s42-0723`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0724`: priority P2 != P3; domain unknown != police
- `g2s42-0729`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0730`: domain unknown != ems
- `g2s42-0733`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-0735`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0737`: priority P3 != P4; domain unknown != ems
- `g2s42-0741`: missed cues ['OVERDOSE']; priority P2 != P0
- `g2s42-0743`: missed cues ['POISONING']; priority P2 != P1; domain unknown != ems
- `g2s42-0745`: location missing != present
- `g2s42-0747`: spurious cues ['CHILD_INVOLVED']; priority P0 != P1; domain unknown != ems
- `g2s42-0752`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0753`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; victims 2 != None
- `g2s42-0755`: priority P2 != P4; domain unknown != police
- `g2s42-0757`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-0759`: domain unknown != police
- `g2s42-0761`: domain unknown != ems
- `g2s42-0768`: missed cues ['FALL_FROM_HEIGHT']; priority P3 != P1
- `g2s42-0772`: priority P2 != P4; domain unknown != ems
- `g2s42-0773`: priority P2 != P4; domain unknown != police
- `g2s42-0775`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-0786`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-0789`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1; location present != missing
- `g2s42-0790`: priority P2 != P3; domain unknown != police
- `g2s42-0795`: domain unknown != ems
- `g2s42-0796`: domain unknown != ems
- `g2s42-0799`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-0803`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0807`: missed cues ['OVERDOSE']; priority P2 != P0
- `g2s42-0809`: domain unknown != ems
- `g2s42-0813`: missed cues ['CHILDBIRTH']; priority P2 != P1; domain unknown != ems
- `g2s42-0819`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; victims 2 != None
- `g2s42-0821`: domain unknown != police
- `g2s42-0823`: domain unknown != ems
- `g2s42-0825`: domain unknown != police
- `g2s42-0827`: domain unknown != ems
- `g2s42-0828`: priority P2 != P4; domain unknown != ems
- `g2s42-0830`: domain unknown != ems
- `g2s42-0834`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-0838`: priority P2 != P4; domain unknown != ems
- `g2s42-0839`: domain ems != police
- `g2s42-0841`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-0850`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire; location missing != present
- `g2s42-0852`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-0853`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0861`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-0862`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0865`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0867`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-0869`: domain unknown != ems
- `g2s42-0873`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-0875`: domain unknown != ems
- `g2s42-0877`: priority P2 != P4; domain unknown != ems
- `g2s42-0881`: missed cues ['ACTIVE_BLEEDING']; priority P1 != P0
- `g2s42-0884`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0885`: domain unknown != police
- `g2s42-0887`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0889`: domain unknown != ems
- `g2s42-0898`: missed cues ['DROWNING']; domain unknown != ems
- `g2s42-0900`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-0904`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-0905`: domain ems != police
- `g2s42-0907`: missed cues ['INJURY_REPORTED']; domain unknown != ems
- `g2s42-0912`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0918`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-0919`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0921`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-0922`: priority P2 != P3; domain unknown != police
- `g2s42-0927`: domain unknown != ems
- `g2s42-0928`: domain unknown != ems
- `g2s42-0930`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-0931`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-0933`: missed cues ['SEIZURE']; priority P3 != P0; domain unknown != ems
- `g2s42-0935`: domain unknown != ems
- `g2s42-0941`: domain unknown != ems
- `g2s42-0950`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-0951`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; victims 2 != None
- `g2s42-0953`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-0955`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems; location present != conflicting
- `g2s42-0959`: domain unknown != ems
- `g2s42-0962`: location missing != present
- `g2s42-0964`: missed cues ['DROWNING', 'NOT_BREATHING']; priority P2 != P0; domain unknown != ems
- `g2s42-0966`: missed cues ['MULTIPLE_VICTIMS']; priority P1 != P0; victims None != 2
- `g2s42-0971`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-0973`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-0978`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-0984`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-0985`: priority P2 != P4; domain unknown != hazmat
- `g2s42-0987`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-0988`: priority P2 != P3; domain unknown != police
- `g2s42-0990`: missed cues ['UNCONSCIOUS']; domain unknown != ems
- `g2s42-0993`: missed cues ['UNCONSCIOUS']; priority P1 != P0
- `g2s42-0994`: priority P2 != P4; domain unknown != ems
- `g2s42-0996`: priority P2 != P4; domain unknown != ems
- `g2s42-0997`: missed cues ['CARDIAC_SYMPTOMS']; priority P1 != P0
- `g2s42-1001`: domain unknown != ems
- `g2s42-1003`: missed cues ['DIABETIC_EMERGENCY']; priority P2 != P1; domain unknown != ems
- `g2s42-1011`: missed cues ['CHILDBIRTH']; spurious cues ['CHILD_INVOLVED']; priority P3 != P1; domain unknown != ems; location missing != present
- `g2s42-1013`: missed cues ['WEAPON_PRESENT']; priority P1 != P0; domain ems != police
- `g2s42-1015`: missed cues ['WEAPON_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1016`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-1019`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1021`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1023`: missed cues ['MISSING_PERSON']; domain unknown != police; location present != missing
- `g2s42-1025`: priority P2 != P4; domain unknown != ems
- `g2s42-1028`: domain unknown != ems
- `g2s42-1037`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1039`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2; domain unknown != ems
- `g2s42-1048`: domain unknown != fire
- `g2s42-1050`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-1051`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1059`: domain unknown != ems
- `g2s42-1060`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-1062`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-1063`: missed cues ['CARDIAC_SYMPTOMS']; priority P3 != P0; domain unknown != ems
- `g2s42-1067`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1073`: domain unknown != ems
- `g2s42-1075`: priority P2 != P4; domain unknown != ems
- `g2s42-1079`: missed cues ['WEAPON_PRESENT']; priority P1 != P0; domain ems != police
- `g2s42-1081`: domain unknown != police
- `g2s42-1085`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1087`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1091`: missed cues ['ACTIVE_BLEEDING']; priority P2 != P1; domain unknown != ems
- `g2s42-1098`: missed cues ['FALL_FROM_HEIGHT']; priority P3 != P0; location missing != present
- `g2s42-1102`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-1103`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1105`: missed cues ['INJURY_REPORTED']; domain unknown != ems
- `g2s42-1110`: priority P3 != P4
- `g2s42-1114`: domain unknown != fire
- `g2s42-1116`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1117`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1120`: priority P2 != P3; domain unknown != police
- `g2s42-1122`: missed cues ['NOT_BREATHING']
- `g2s42-1125`: missed cues ['CHILD_INVOLVED']; domain unknown != ems
- `g2s42-1126`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-1131`: domain unknown != ems
- `g2s42-1133`: domain unknown != ems
- `g2s42-1139`: domain unknown != ems
- `g2s42-1143`: missed cues ['CHILDBIRTH']; priority P2 != P1; domain unknown != ems
- `g2s42-1148`: domain unknown != police
- `g2s42-1151`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1153`: domain unknown != ems
- `g2s42-1155`: missed cues ['MISSING_PERSON']; priority P2 != P1; domain ems != police
- `g2s42-1157`: domain unknown != ems
- `g2s42-1160`: domain unknown != ems
- `g2s42-1166`: domain unknown != ems
- `g2s42-1169`: domain ems != police; location missing != present
- `g2s42-1171`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1176`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-1182`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1191`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-1192`: priority P2 != P4; domain unknown != ems
- `g2s42-1199`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1203`: missed cues ['OVERDOSE']; priority P2 != P0
- `g2s42-1205`: domain unknown != ems
- `g2s42-1207`: priority P2 != P4; domain unknown != ems; location missing != present
- `g2s42-1211`: missed cues ['WEAPON_PRESENT']; domain ems != police
- `g2s42-1213`: priority P2 != P4; domain unknown != police
- `g2s42-1214`: domain unknown != police
- `g2s42-1217`: domain unknown != police
- `g2s42-1219`: priority P2 != P4; domain unknown != ems
- `g2s42-1223`: domain unknown != ems
- `g2s42-1226`: domain unknown != ems
- `g2s42-1228`: missed cues ['DROWNING']; domain unknown != ems
- `g2s42-1234`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-1235`: domain unknown != police
- `g2s42-1237`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1240`: missed cues ['SMOKE_REPORTED']; domain unknown != fire
- `g2s42-1242`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-1246`: location present != missing
- `g2s42-1248`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-1249`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1251`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-1252`: priority P2 != P3; domain unknown != police
- `g2s42-1254`: missed cues ['NOT_BREATHING', 'UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-1257`: domain unknown != ems
- `g2s42-1258`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-1260`: domain unknown != ems
- `g2s42-1261`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1263`: location missing != present
- `g2s42-1269`: missed cues ['OVERDOSE']; priority P2 != P0
- `g2s42-1275`: spurious cues ['CHILD_INVOLVED']; priority P0 != P1; domain unknown != ems
- `g2s42-1277`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P3 != P0; domain unknown != police
- `g2s42-1280`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-1281`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; victims 2 != None
- `g2s42-1283`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1285`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1296`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-1301`: domain ems != police
- `g2s42-1303`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1308`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-1311`: location missing != present
- `g2s42-1314`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-1315`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1317`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1318`: priority P2 != P3; domain unknown != police
- `g2s42-1323`: domain unknown != ems
- `g2s42-1324`: domain unknown != ems
- `g2s42-1331`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1337`: domain unknown != ems
- `g2s42-1341`: domain unknown != ems
- `g2s42-1343`: domain ems != police
- `g2s42-1346`: domain unknown != police
- `g2s42-1347`: domain unknown != police
- `g2s42-1349`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1351`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1353`: missed cues ['MISSING_PERSON']; domain unknown != police
- `g2s42-1356`: priority P2 != P4; domain unknown != ems
- `g2s42-1358`: priority P2 != P4; domain unknown != ems
- `g2s42-1364`: domain unknown != ems
- `g2s42-1367`: domain unknown != police
- `g2s42-1374`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-1378`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-1380`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire; location missing != present
- `g2s42-1381`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1383`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-1384`: priority P2 != P3; domain unknown != police
- `g2s42-1386`: location missing != present
- `g2s42-1390`: missed cues ['BREATHING_DIFFICULTY']; priority P3 != P0; domain unknown != ems
- `g2s42-1393`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1395`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1397`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1401`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-1403`: domain unknown != ems
- `g2s42-1405`: missed cues ['ALLERGIC_REACTION']; priority P2 != P1; domain unknown != ems
- `g2s42-1407`: domain unknown != ems
- `g2s42-1412`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; location missing != present; victims 2 != None
- `g2s42-1413`: priority P3 != P4
- `g2s42-1415`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1417`: domain unknown != ems
- `g2s42-1419`: missed cues ['CHILD_INVOLVED', 'MISSING_PERSON']; priority P2 != P1; domain unknown != police
- `g2s42-1421`: missed cues ['CHILD_INVOLVED']; priority P1 != P0
- `g2s42-1426`: missed cues ['DROWNING']
- `g2s42-1433`: domain unknown != police
- `g2s42-1438`: priority P2 != P4; domain unknown != fire
- `g2s42-1444`: domain unknown != fire
- `g2s42-1446`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-1447`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1449`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1450`: priority P2 != P3; domain unknown != police
- `g2s42-1454`: location missing != present
- `g2s42-1455`: missed cues ['MULTIPLE_VICTIMS']; victims None != 4
- `g2s42-1458`: domain unknown != ems
- `g2s42-1459`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-1461`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1463`: domain unknown != ems
- `g2s42-1469`: domain unknown != ems
- `g2s42-1471`: priority P2 != P4; domain unknown != ems
- `g2s42-1473`: missed cues ['CHILDBIRTH']; priority P2 != P1; domain unknown != ems
- `g2s42-1475`: missed cues ['WEAPON_PRESENT']; domain ems != police
- `g2s42-1477`: domain unknown != police
- `g2s42-1478`: missed cues ['WEAPON_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1481`: domain unknown != police
- `g2s42-1483`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1485`: missed cues ['MISSING_PERSON']; domain unknown != police
- `g2s42-1487`: domain unknown != ems
- `g2s42-1490`: domain unknown != ems
- `g2s42-1494`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-1499`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1501`: missed cues ['TRAFFIC_COLLISION']; priority P2 != P1
- `g2s42-1512`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-1515`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-1516`: priority P2 != P3; domain unknown != police
- `g2s42-1521`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-1524`: domain unknown != ems
- `g2s42-1525`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1527`: domain unknown != ems
- `g2s42-1529`: missed cues ['STROKE_SYMPTOMS']; spurious cues ['UNABLE_TO_GET_UP']; priority P2 != P1; domain unknown != ems
- `g2s42-1531`: missed cues ['DIABETIC_EMERGENCY']; priority P2 != P1; domain unknown != ems
- `g2s42-1533`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-1537`: domain unknown != ems
- `g2s42-1543`: spurious cues ['ACTIVE_VIOLENCE']
- `g2s42-1544`: missed cues ['WEAPON_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1547`: domain unknown != police
- `g2s42-1551`: domain unknown != police
- `g2s42-1556`: domain unknown != ems
- `g2s42-1558`: missed cues ['DROWNING', 'NOT_BREATHING']; priority P2 != P0
- `g2s42-1560`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P1; domain unknown != ems
- `g2s42-1562`: domain unknown != ems
- `g2s42-1565`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1567`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1570`: priority P2 != P4; domain unknown != fire
- `g2s42-1578`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1579`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1581`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1; location present != missing
- `g2s42-1582`: priority P2 != P3; domain unknown != police
- `g2s42-1584`: missed cues ['UNCONSCIOUS']; domain unknown != ems
- `g2s42-1587`: missed cues ['UNCONSCIOUS']; priority P2 != P0
- `g2s42-1588`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P0
- `g2s42-1591`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1593`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1595`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1599`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-1601`: priority P2 != P4; domain unknown != ems
- `g2s42-1611`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police
- `g2s42-1613`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1615`: domain unknown != ems
- `g2s42-1617`: missed cues ['MISSING_PERSON']; domain unknown != police
- `g2s42-1619`: missed cues ['ACTIVE_BLEEDING']; priority P3 != P0; domain unknown != ems
- `g2s42-1620`: priority P2 != P4; domain unknown != ems
- `g2s42-1630`: missed cues ['INJURY_REPORTED']; priority P2 != P3; domain unknown != ems
- `g2s42-1631`: priority P2 != P4; domain unknown != police
- `g2s42-1633`: missed cues ['INJURY_REPORTED']; domain unknown != ems
- `g2s42-1638`: priority P3 != P4
- `g2s42-1642`: domain unknown != fire
- `g2s42-1644`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1647`: location missing != present
- `g2s42-1648`: priority P2 != P3; domain unknown != police
- `g2s42-1650`: missed cues ['UNCONSCIOUS']
- `g2s42-1654`: domain unknown != ems
- `g2s42-1657`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-1661`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P0
- `g2s42-1667`: domain unknown != ems
- `g2s42-1669`: missed cues ['ALLERGIC_REACTION']; priority P2 != P0
- `g2s42-1673`: missed cues ['ACTIVE_BLEEDING', 'WEAPON_PRESENT']; priority P2 != P0; domain unknown != police
- `g2s42-1676`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-1679`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1681`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1683`: domain unknown != police
- `g2s42-1685`: priority P2 != P4; domain unknown != ems
- `g2s42-1688`: domain unknown != ems
- `g2s42-1690`: missed cues ['DROWNING', 'NOT_BREATHING']; priority P2 != P0; domain unknown != ems
- `g2s42-1697`: domain ems != police
- `g2s42-1699`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1700`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0
- `g2s42-1710`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1711`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1713`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1714`: priority P2 != P3; domain unknown != police
- `g2s42-1719`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-1720`: priority P2 != P4; domain unknown != ems
- `g2s42-1723`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1725`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1727`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1729`: missed cues ['DIABETIC_EMERGENCY']; priority P3 != P0; domain unknown != ems
- `g2s42-1733`: missed cues ['POISONING']; priority P2 != P1; domain unknown != ems
- `g2s42-1735`: domain unknown != ems
- `g2s42-1739`: missed cues ['WEAPON_PRESENT']; priority P1 != P0; domain ems != police
- `g2s42-1741`: missed cues ['WEAPON_PRESENT']; spurious cues ['ACTIVE_VIOLENCE']
- `g2s42-1743`: priority P3 != P4
- `g2s42-1745`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police
- `g2s42-1747`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1752`: missed cues ['BURN_INJURY']; priority P3 != P1
- `g2s42-1756`: missed cues ['DROWNING', 'NOT_BREATHING']; priority P2 != P0; domain unknown != ems
- `g2s42-1758`: missed cues ['FALL_FROM_HEIGHT']; priority P2 != P0
- `g2s42-1760`: location missing != present
- `g2s42-1763`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police; location present != missing
- `g2s42-1765`: missed cues ['INJURY_REPORTED']; domain unknown != ems
- `g2s42-1770`: priority P3 != P4
- `g2s42-1776`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1779`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1780`: priority P2 != P3; domain unknown != police
- `g2s42-1785`: domain unknown != ems
- `g2s42-1786`: domain unknown != ems
- `g2s42-1789`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-1793`: missed cues ['STROKE_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1797`: missed cues ['OVERDOSE']; priority P3 != P0; domain unknown != ems
- `g2s42-1799`: domain hazmat != ems
- `g2s42-1807`: priority P2 != P4; domain unknown != police
- `g2s42-1809`: domain unknown != police
- `g2s42-1811`: domain unknown != police
- `g2s42-1813`: missed cues ['SELF_HARM_RISK']; priority P3 != P0; domain unknown != ems
- `g2s42-1817`: domain unknown != ems
- `g2s42-1820`: domain unknown != ems
- `g2s42-1822`: missed cues ['DROWNING']
- `g2s42-1826`: domain unknown != ems
- `g2s42-1829`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1836`: missed cues ['FIRE_SPREADING']; priority P2 != P1
- `g2s42-1838`: location missing != present
- `g2s42-1842`: missed cues ['OCCUPANTS_TRAPPED']; spurious cues ['UNCONSCIOUS']; domain ems != fire
- `g2s42-1851`: missed cues ['UNCONSCIOUS']; priority P2 != P0; domain unknown != ems
- `g2s42-1852`: domain unknown != ems
- `g2s42-1855`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-1857`: missed cues ['SEIZURE']; priority P3 != P0; domain unknown != ems
- `g2s42-1859`: missed cues ['STROKE_SYMPTOMS']; spurious cues ['UNABLE_TO_GET_UP']; priority P2 != P1; domain unknown != ems
- `g2s42-1863`: missed cues ['OVERDOSE']; priority P1 != P0
- `g2s42-1874`: domain unknown != police
- `g2s42-1877`: missed cues ['INTRUDER_PRESENT']; priority P2 != P1; domain unknown != police; location missing != present
- `g2s42-1879`: missed cues ['SELF_HARM_RISK']; priority P2 != P1; domain unknown != ems
- `g2s42-1883`: missed cues ['ACTIVE_BLEEDING']; priority P3 != P0; domain unknown != ems
- `g2s42-1886`: domain unknown != ems
- `g2s42-1888`: missed cues ['DROWNING']
- `g2s42-1895`: domain ems != police
- `g2s42-1897`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1902`: priority P3 != P4
- `g2s42-1906`: missed cues ['EXPLOSION_REPORTED']; priority P2 != P1; domain unknown != fire
- `g2s42-1908`: missed cues ['OCCUPANTS_TRAPPED']; priority P2 != P0; domain unknown != fire
- `g2s42-1911`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-1917`: domain unknown != ems
- `g2s42-1918`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-1920`: domain unknown != ems
- `g2s42-1921`: missed cues ['CARDIAC_SYMPTOMS']; priority P2 != P1; domain unknown != ems
- `g2s42-1923`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1925`: missed cues ['STROKE_SYMPTOMS']; spurious cues ['UNABLE_TO_GET_UP']; priority P1 != P0
- `g2s42-1931`: domain unknown != ems
- `g2s42-1933`: priority P2 != P4; domain unknown != ems
- `g2s42-1940`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-1941`: missed cues ['ACTIVE_VIOLENCE']; spurious cues ['MULTIPLE_VICTIMS']; priority P2 != P1; domain unknown != police; victims 2 != None
- `g2s42-1943`: domain unknown != police
- `g2s42-1945`: spurious cues ['ACTIVE_VIOLENCE']; domain police != ems
- `g2s42-1947`: missed cues ['MISSING_PERSON']; priority P2 != P1; domain ems != police
- `g2s42-1950`: priority P2 != P4; domain unknown != ems
- `g2s42-1954`: missed cues ['DROWNING']; domain unknown != ems
- `g2s42-1956`: missed cues ['FALL_FROM_HEIGHT']; priority P3 != P1
- `g2s42-1960`: priority P2 != P4; domain unknown != ems
- `g2s42-1961`: missed cues ['TRAFFIC_COLLISION']; domain unknown != police
- `g2s42-1963`: missed cues ['TRAFFIC_COLLISION']; priority P3 != P2
- `g2s42-1972`: domain unknown != fire
- `g2s42-1974`: missed cues ['OCCUPANTS_TRAPPED']; priority P3 != P0; domain ems != fire
- `g2s42-1975`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P2 != P1; domain unknown != hazmat
- `g2s42-1977`: missed cues ['HAZARDOUS_ENVIRONMENT']; priority P3 != P1
- `g2s42-1978`: priority P2 != P3; domain unknown != police
- `g2s42-1983`: domain unknown != ems
- `g2s42-1984`: domain unknown != ems
- `g2s42-1986`: missed cues ['BREATHING_DIFFICULTY']; priority P2 != P1; domain unknown != ems
- `g2s42-1987`: missed cues ['CARDIAC_SYMPTOMS']; spurious cues ['INJURY_REPORTED']; priority P3 != P1; domain unknown != ems
- `g2s42-1989`: missed cues ['SEIZURE']; priority P2 != P1; domain unknown != ems
- `g2s42-1991`: missed cues ['STROKE_SYMPTOMS']; priority P3 != P0; domain unknown != ems
- `g2s42-1995`: missed cues ['OVERDOSE']; priority P2 != P1; domain unknown != ems
- `g2s42-1997`: domain unknown != ems
- `g2s42-1999`: domain unknown != ems
- `g2s42-2001`: spurious cues ['CHILD_INVOLVED']; priority P0 != P1; domain unknown != ems
- `g2s42-2006`: spurious cues ['MULTIPLE_VICTIMS']; priority P0 != P1; domain unknown != police; victims 2 != None
- `g2s42-2007`: missed cues ['ACTIVE_VIOLENCE']; priority P2 != P1; domain unknown != police
- `g2s42-2009`: domain unknown != police

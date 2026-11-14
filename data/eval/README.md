# Evaluation datasets

All data here is **synthetic**. No real emergency calls are included or may be added
(design v1.2, ADR-006).

## `curated.jsonl`

50 hand-written cases, one JSON object per line (`ntip.evaluation.dataset.EvalCase`):

- 23 ported from the TypeScript-era `data/fixtures/sample-incidents.json`
  (`fx-*`), re-labelled under the [labelling guide](../../docs/evaluation/labelling-guide.md)
- 27 new edge cases (`cu-*`) for negation, tense, hearsay, uncertainty,
  address corrections, follow-up messages, Spanish, children and multiple victims

| Split | Purpose | Cases | Families |
|---|---|---|---|
| `dev` | Inspect freely while developing rules or models | 15 | 15 |
| `regression` | Must not get worse; the CI safety gate runs here | 15 | 14 |
| `test` | Held out; only looked at when reporting results | 20 | 20 |

Splits are assigned per **family** (a scenario and its paraphrases), and
`load_dataset` rejects any family that appears in more than one split, so
paraphrases cannot leak from development data into the test set (§3A.7).

### Provenance and limitations

- `label_source: "author"`: every label was written by the project author, who also
  wrote the rules parser. Labels are therefore **not independent**, and no
  inter-annotator agreement has been measured. Independent annotation is an open
  task (design v1.2, §3A.7 and open question 7).
- The ported fixtures were visible while the parser was developed. The `cu-*`
  test cases were written after the parser and have not been used to change it.
- Severity and priority labels follow the project's research rubric. They are
  **not** a validated dispatch protocol and have not been reviewed by
  public-safety practitioners.
- 50 cases are far too few for narrow confidence intervals; every reported rate
  includes its counts and a bootstrap interval for that reason.

## `generated-1.0.0-seed42.jsonl`

510 cases from `python -m ntip.generator --n 510 --seed 42` (generator 1.0.0):
17 scenario families with perturbations for location form, children and
multiple victims, uncertainty, hearsay, denial, past tense, disfluency,
misspellings, address corrections and Spanish. A test fails if the file no
longer matches the generator.

- `label_source: "generator"`: labels are **generator-intended**, computed from
  the labelling rubric and the template, not checked by a person (design v1.2,
  §12.3). Treat results on this set as a stress test, not as accuracy.
- Template families are not shared with `curated.jsonl`, so the curated set
  stays outside the generator's families.
- Predates labelling guide v2.1 (DDL-021) and is kept unchanged so earlier
  reports stay reproducible: its "fell down the stairs" family has no
  `FALL_FROM_HEIGHT` label. B1 is still trained on it, as a stable baseline.

## `generated-2.0.0-seed42.jsonl`

2,010 cases from `python -m ntip.generator --generator 2.0.0 --n 2010 --seed 42`
(generator 2.0.0, ML layer design §4.3). The training data for B1e.

| | Generator 1.0.0 | Generator 2.0.0 |
|---|---|---|
| Scenario families | 17 | 66 (dev 20, regression 19, test 27) |
| Base phrasings | 51 (3 per family) | 279 (3 to 6 per family), plus denials, past-tense and Spanish versions |
| Cue codes | 20, six of them only in test families | 32 (labelling guide v2.1), every one in both a training and a test family |
| Training calls (dev + regression) | 300 | 1,188 |
| Labels | Cue lists | Label schema 2.0: each cue's status and exact evidence span, and the location components the caller gave |
| Perturbations | Location form, child, several people, uncertainty, hearsay, denial, past tense, disfluency, misspelling, address correction, Spanish | The same, plus a speech-recognition-style variant (lower case, no punctuation, homophones) |

- Evidence spans are kept through every perturbation: a misspelled cue word
  stays inside its span, and a filler inserted inside a cue phrase becomes
  part of the evidence, as written.
- Labels are generator-intended, as for 1.0.0. The phrasings were written by
  the project author, without reference to the rules' phrase lists, and the
  rules were not changed to fit them: results on this set measure how the
  rules cope with phrasing they were not written for.

## `generated-2.1.0-seed42.jsonl`

2,010 cases from `python -m ntip.generator --generator 2.1.0 --n 2010 --seed 42`. This is generator 2.0 with four additions, each closing a gap that B1e showed on curated dev (`ntip/generator/scenarios_v21.py`). It is B1e's training data from model version 0.2 on. Generator 2.0.0 and its dataset are unchanged.

| Addition | Why | In the data |
|---|---|---|
| A denial of a cue that is not part of the call ("Nobody is hurt.", "There's no fire.", "She is still conscious.", "He is still breathing."), labelled `negated` | B1e scored "nobody is hurt" and "there is no fire" as live: 2.0 never denied a cue on its own | 330 calls (`reassured`) |
| An all-capitals variant | B1e missed "HE IS NOT BREATHING"; no 2.0 call was in capitals | 105 calls (`shouting`) |
| A training family with `NOT_BREATHING` alone, and unconscious patients reported as still breathing | Every 2.0 training call with `NOT_BREATHING` also had `UNCONSCIOUS` or `DROWNING`, and B1e learned to add `UNCONSCIOUS` | 67 families (dev 21) |
| Spanish family words drawn at random, keeping their gender | Each 2.0 Spanish phrasing named one fixed person, and B1e read "mi esposo" as a child | 15 family words |

Only "hijo", "hija" and "bebé" are labelled `CHILD_INVOLVED`.

The additions were written after looking at B1e's errors on curated dev. Curated dev is therefore no longer an independent check of these four patterns; the test splits are.

## Running

```sh
cd backend
python -m ntip.evaluation                                   # dev + regression
python -m ntip.evaluation --split test --out ../docs/evaluation/results
python -m ntip.evaluation --split regression --gate         # exit 2 on critical under-triage
python -m ntip.evaluation --dataset ../data/eval/generated-2.0.0-seed42.jsonl     --split dev --split regression                          # rules on generator 2.0
```

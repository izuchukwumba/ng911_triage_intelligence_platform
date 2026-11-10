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

## Running

```sh
cd backend
python -m ntip.evaluation                                   # dev + regression
python -m ntip.evaluation --split test --out ../docs/evaluation/results
python -m ntip.evaluation --split regression --gate         # exit 2 on critical under-triage
```

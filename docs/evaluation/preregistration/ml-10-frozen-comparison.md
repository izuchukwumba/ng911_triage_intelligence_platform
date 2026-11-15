# Pre-registration: ML-10 frozen comparison (1.0)

**Status:** fixed before the run. Written and merged before any system is
run on the data below for this comparison. The run's reports record this
file's digest (`compare --preregistration`). Any change after the merge is a
deviation and is reported with the results.

This follows the ML layer design §8 and the hypotheses of design v1.2 §3A.8.
The ML-4 gate is re-checked here: no increase in critical-cue false
negatives on a frozen test set.

## 1. Systems (frozen)

| System | What it is | Frozen as |
|---|---|---|
| **B0 rules** | Rules parser and triage engine | parser `rules-parser-1.5.0`, engine `triage-engine-1.2.0`, ruleset `research-1.2.0` (`sha256:69fdb910c1a9f4ec5a0672482cd39352683d9778cffd706c694efcb48b4e44b2`) |
| **B1** | n-gram linear model | `1.0.0+f764c2172d5a` (training data `sha256:a064e9dbe885a3448314e654c2650c7e20b6e200c29c1b26c45f1bea9b045555`). B1 is refitted when it loads, and its digest depends on the environment; the version above is the reference machine's |
| **B1e** | Fine-tuned multilingual encoder | `0.1.0+7b7bb8d67713`, weights `sha256:7b7bb8d6771359754a08b04e1807de9c64ba8bbdc007f6218fa6f181cce26792`, trained on generator 2.2 dev + regression ([manifest](../results/b1e-0.1.0+7b7bb8d67713-manifest.json)). Uncalibrated (DDL-022) |
| **Hybrids** | Rules plus a model's verified candidates | Fusion policy `1.0.0`, the default (DDL-022) |

`compare` also runs these systems:
- B1 only and B1e only;
- both hybrids without abstention;
- the B1e hybrid under fusion policy `2.0.0`, which was not adopted (DDL-022) and is reported for completeness only.

The code is the commit at which this file is merged. B2 is not run: ML-7
was not authorised.

## 2. Data

| Dataset | Split | Calls | Labelled P0 | Digest | Role |
|---|---|---|---|---|---|
| `generated-2.2.0-seed42.jsonl` | test | 810 | 285 | `sha256:fc839b30cf1a8863d9689ae677f4dc94c666a8274889a53fbadc40e234394858` | **Primary.** 27 families no model trained on |
| `curated.jsonl` | test | 20 | 9 | `sha256:6694a761e9861011c85e9cacd4d065099f36778aed82c6c341833c5b688c26f7` | Secondary |
| `challenge-1.0.0.jsonl` | test | 70 | 19 | `sha256:febf06e3533051dd11382e36c4c209b626d9a81b8255fb562e2eeea71dbaac43` | Secondary, by kind |

Labels are generator-intended (generated) or the author's (curated,
challenge). Results against each label source are reported separately and
never pooled (§8.7).

**What has already been seen.**
- **Curated test** was run once before, at ML-3, for B0 and B1 with
  parser 1.3.0 ([report](../results/compare-curated-test.md)). It has not
  been used to change the rules. It has never been run with B1e.
- **Generator test families** were written by the author, who also wrote the
  rules. The rules were not tuned to any generated set. No system has been
  run on any generated test split.
- **The challenge set** has not been run by any system.

## 3. Hypotheses, measures and decision rules

All on the **primary** data unless stated. "Hybrid" means Hybrid B0+B1e
under fusion 1.0.0.

| # | Question | Measure | Passes when |
|---|---|---|---|
| H1 | Safety gate (ML-4): does fusion add unsafe omissions? | Critical under-triage: labelled-P0 calls not given P0 | Hybrid ≤ B0 on **each** of the three test sets |
| H2 | Does B1e help on urgent calls? | McNemar's exact test on labelled-P0 calls given P0, Hybrid vs B0 | Hybrid ahead, two-sided p < 0.025 |
| H3 | Does fusion improve extraction? | Cue micro F1, Hybrid − B0, 95% paired bootstrap interval | Interval entirely above 0 |
| H4 | Is the cost in over-triage tolerable? | Over-triage rate, Hybrid − B0 | Increase of at most 0.10 (point estimate) |
| H5 | Is B1e better than B1 in the hybrid? | McNemar's exact test on labelled-P0 calls given P0, Hybrid B0+B1e vs Hybrid B0+B1 | B1e ahead, two-sided p < 0.025 |
| H6 | Is inference practical? | p95 wall time per call, Hybrid, on the reference machine | Under 150 ms (ML layer design §5.3). A target: a miss is reported, not a failed comparison |

**Multiplicity.** H2 and H5 are the two significance tests, each at 0.025
(Bonferroni, family-wise 0.05). H1, H3 and H4 are decision rules on counts
and intervals, not tests.

**Interpretation, fixed now:**
- **H1 fails:** the hybrid is not safe to recommend. That is reported as the
  main finding, whatever else passes.
- **H1 passes and H2 fails:** B1e adds no demonstrated benefit on urgent
  calls.
- **H4 fails:** the benefit costs more over-triage than tolerated. It is
  reported alongside H2, never instead of it.

Fusion policy 1.0.0 never lowers a priority, so H1 is expected to hold by
construction. It is checked because a conflict between rules and model
could still change an assessment.

## 4. Reported for every system (descriptive, no decision)

- Critical-cue sensitivity and critical under-triage.
- Exact priority, under-triage and over-triage, each with a 95% interval.
- Cue micro precision, recall and F1, and per code.
- Denied or past cues reported live.
- Evidence spans and status, where labels have them.
- Severity, domain, location and victim count.
- Slices:
  - generator variants: negation, past, uncertainty, hearsay ("second hand"), Spanish, misspelling, speech recognition, corrected address, children, several victims;
  - the challenge set's seven kinds and its tags, each with at least ten cases.
- Paired comparisons of every system with B0, and of Hybrid B0+B1e with Hybrid B0+B1 (§8.3).
- Wall time per call (p50, p95) and CPU time.

## 5. Ablations (§8.5)

| Ablation | How |
|---|---|
| Without abstention | Hybrid B0+B1 and Hybrid B0+B1e without abstention (candidate threshold lowered to the abstention threshold) |
| Without rules fusion | B1 only and B1e only |
| Without span verification | Not run as a system. The report counts candidates that span verification rejected. If the count is 0, removing verification changes nothing on that data |
| Without calibration | Not applicable: no calibration is applied (DDL-022) |
| Without location handling | Not run. No model proposes locations in this version, so location handling is identical in every system; location accuracy is reported |

## 6. Procedure

1. Merge this file. Its digest is computed by `compare` from the merged
   file.
2. Check the B1e model directory against its manifest (`B1eModel` refuses
   any mismatch). Its version must be `0.1.0+7b7bb8d67713`.
3. Run once, from `backend/`, at the merge commit, on the reference machine
   (the author's laptop CPU):

   ```sh
   P=../docs/evaluation/preregistration/ml-10-frozen-comparison.md
   python -m ntip.evaluation.compare --dataset ../data/eval/generated-2.2.0-seed42.jsonl --split test --with-b1e B1E_DIR --preregistration $P
   python -m ntip.evaluation.compare --dataset ../data/eval/curated.jsonl --split test --with-b1e B1E_DIR --preregistration $P
   python -m ntip.evaluation.compare --dataset ../data/eval/challenge-1.0.0.jsonl --split test --with-b1e B1E_DIR --preregistration $P
   ```

4. Publish every report as produced, with the decision for H1 to H6, in the
   results README and a decision-log entry.

Rules for the run:
- A run that fails before writing its report may be restarted with no
  change.
- A finished run is never repeated, except to reproduce it.
- Nothing is tuned on these results. Any later system needs a new
  pre-registration, and new test data for anything these results informed.
- Results are published whether they pass or fail.

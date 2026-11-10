# Evaluation results

Reports produced by `python -m ntip.evaluation`. Each has a JSON and a Markdown
version, and each records the git commit, dataset digest, ruleset digest,
versions and seed needed to reproduce it.

| Report | Parser / ruleset | Data | Notes |
|---|---|---|---|
| [1.0.0 dev+regression](b0-curated-1.0.0-research-1.0.0-dev-regression.md) | 1.0.0 / research-1.0.0 | curated dev + regression (30) | First development view |
| [1.0.0 test](b0-curated-1.0.0-research-1.0.0-test.md) | 1.0.0 / research-1.0.0 | curated test (20) | **Held-out baseline.** Recorded once; its failures are not used to change the parser |
| [1.1.0 dev+regression](b0-curated-1.1.0-research-1.0.0-dev-regression.md) | 1.1.0 / research-1.0.0 | curated dev + regression (30) | After closing the regression miss; CI gate enabled |
| [1.2.0 dev+regression](b0-curated-1.2.0-research-1.1.0-dev-regression.md) | 1.2.0 / research-1.1.0 | curated dev + regression (30), labelling guide v1.1 | Rubric gaps closed; no under-triage |

## First baseline (B0, curated v1)

- On the regression split, one expected-P0 case is under-triaged:
  `cu-126` ("I'm not sure if he's breathing … won't answer me"), where neither
  the uncertain breathing cue nor "won't answer" is recognised. This is the
  first gap the CI safety gate will hold closed once fixed.
- On the held-out test split, 2 of 9 expected-P0 cases are under-triaged
  (critical under-triage 0.222, 95% CI 0.000–0.556). They are left as they are, so
  this report remains an honest held-out baseline for comparing B1/B2.
- Over-triage concentrates on cues the rules cannot grade (minor bleeding,
  retracted or past events), which the rubric places lower.

These are measurements on 50 author-labelled synthetic cases. They are not
evidence of real-world dispatch performance (design v1.2, §16.3).

`../benchmark-report-v0.2.0.md` describes the retired TypeScript scorer and is
kept for history.

## Parser 1.1.0 (dev + regression only)

Changes were driven only by dev and regression failures. Critical-cue
sensitivity 15/15 (was 13/15), critical under-triage 0/13 (was 1/13), cue
micro F1 0.985 (was 0.906), priority agreement 0.800 (was 0.667). The
remaining failures are triage-rubric gaps (older adult unable to get up, a
recovered critical event, retractions and past events), not extraction
errors. The held-out test split has not been re-run.

## Parser 1.2.0 + ruleset research-1.1.0 (dev + regression only)

Priority agreement 0.867 (26/30), under-triage 0/30, critical under-triage 0/13.
All four remaining disagreements are **over-triage**, the safe direction, and
are kept deliberately:

- `fx-021`, `fx-022`, `cu-103`: a threat that has left, a retracted report and
  a past hearsay event. Lowering priority from what a caller says happened (or
  "takes back") is a judgement left to the human reviewer; the engine adds
  review actions instead.
- `cu-119`: a hypothetical cardiac event is assessed "undetermined" (P2), not low.


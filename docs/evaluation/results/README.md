# Evaluation results

Reports produced by `python -m ntip.evaluation`. Each has a JSON and a Markdown
version, and each records the git commit, dataset digest, ruleset digest,
versions and seed needed to reproduce it.

| Report | System | Data | Notes |
|---|---|---|---|
| [b0-dev-regression.md](b0-dev-regression.md) | B0 rules (parser 1.0.0, ruleset research-1.0.0) | curated dev + regression (30) | Development view; failures here may drive changes |
| [b0-test.md](b0-test.md) | same | curated test (20) | Held-out baseline. Recorded once; its failures are **not** used to change the parser |

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

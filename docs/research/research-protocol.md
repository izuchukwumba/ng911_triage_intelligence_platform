# Research protocol (v1.0)

**For:** prospective practitioner reviewers, academic collaborators and the
ethics board that would review the human study.
**Status:** protocol drafted; no study has been run, and no participant has
been recruited.
**Implements:** design v1.2 §16 (research questions, study design, claims
ladder), §10.5 (human factors), §3A.8 (pre-registered hypotheses) and the
external reviews of Phase V (§3B) and milestone ML-5 (§3A.10).

## 1. Summary

The platform is a research prototype that reads synthetic emergency-call
text and suggests an advisory priority, showing the exact words behind each
suggestion. A person always makes the decision. It is not used, and is not
fit for use, in a real emergency communications centre.

This protocol defines three pieces of research that need people other than
the author:

| Study | Question | Who takes part | Effort for each person |
|---|---|---|---|
| A. Practitioner review | Are the rubric, scenarios and outputs sensible to people who do the job? | 3 to 5 experienced practitioners | About 3 hours, remote |
| B. Explanation study | Do evidence-linked explanations help reviewers understand and correctly override suggestions, compared with a score alone? | 16 to 24 telecommunicators or trainees | About 75 minutes, one session |
| C. Independent re-evaluation | Do the published results hold when an outside engineer reruns them against independently annotated labels? | 1 or 2 engineers | About 1 day |

Study A comes first: its findings may change the rubric, and study B should
use the rubric after that change.

## 2. Research questions

From design v1.2 §16.1:

- **RQ1:** Does provenance-aware structured extraction improve the
  correctness of incident facts compared with a keyword baseline on a held-out
  synthetic corpus?
- **RQ2:** Does keeping severity separate from location quality reduce unsafe
  downgrades when the location is incomplete?
- **RQ3:** Does version-pinned replay make changes in advisory decisions
  reproducible and explainable?
- **RQ4:** Do evidence-linked explanations improve human reviewer
  comprehension compared with score-only displays, in a controlled study?

RQ1 to RQ3 are answered by the platform's own evaluation harness
(`docs/evaluation/results/`). Their weakness is that the labels are the
author's; the [annotation protocol](annotation-protocol.md) fixes that, and
study C checks the result independently. RQ4 needs study B.

## 3. Study A: practitioner review

### Purpose

Get documented, independent judgement from practitioners on whether:

1. the research rubric's priorities (labelling guide §2) are defensible;
2. the synthetic scenarios are realistic enough to learn from;
3. the platform's suggestions and explanations make sense, and where they
   would mislead;
4. anything the platform does would be unsafe if it were ever used for real.

### Participants

Three to five people, each with five or more years in emergency
communications or emergency response, preferably including at least one
supervisor or trainer and one person with medical-dispatch protocol
experience. They may be recruited through professional associations, a
local emergency communications centre's training staff, or a university
public-safety programme. People who annotated cases (annotation protocol)
may also review, but their review is reported separately.

### Materials

- The labelling guide and a two-page summary of the platform.
- A recorded walk-through (about 15 minutes) of the dashboard: queue, incident
  detail with evidence, review and override, replay.
- 30 synthetic cases with the platform's suggestion and explanation,
  chosen to include the platform's known failures (missed critical cues,
  over-triage, denial and past-tense cases, ambiguous locations).
- A structured questionnaire (below).

### Questionnaire

For each of the 30 cases:

| Question | Response |
|---|---|
| What priority would you give this call? | P0 to P4 |
| Is the platform's suggestion acceptable? | Acceptable / too high / too low / wrong for another reason |
| Does the explanation show the right reasons? | Yes / partly / no, with a comment |
| Could this output mislead a reviewer? | Yes / no, with a comment |

Overall (free text, each question optional):

1. Which parts of the rubric would you change, and why?
2. Which scenarios felt unrealistic?
3. What would have to be true before something like this could be tested
   with real (de-identified) data?
4. Any safety concern not covered above.

### Outputs

- A review report in `docs/research/reviews/`, quoting reviewers
  pseudonymously (named only with their written agreement), with every
  concern listed and the project's response to each.
- Rubric changes, if any, as a new labelling guide version and a decision-log
  entry.
- Agreement between reviewers' priorities and the rubric's, reported like the
  annotation round's practitioner fields.

This is a review, not an endorsement, and is reported as "received
documented expert feedback" (design v1.2 §16.3). It must not be described as
validation, adoption or approval by any reviewer's employer.

## 4. Study B: explanation study (RQ4)

### Design

A within-subjects experiment with two conditions:

| Condition | What the reviewer sees for each incident |
|---|---|
| **Evidence** (the platform as built) | The transcript with the supporting words highlighted, the suggested priority, the reasons ("Why this recommendation?") and any unresolved verification questions |
| **Score only** | The transcript and the suggested priority, with no highlighting or reasons |

Each participant reviews 24 synthetic incidents, 12 in each condition, in two
blocks. The order of conditions and the assignment of incidents to
conditions are counterbalanced across participants (a balanced Latin square),
so each incident appears equally often in both conditions.

In each block, **4 of the 12 suggestions are deliberately wrong** (2 too high,
2 too low, including at least one missed critical cue). Participants are told
in advance that suggestions may be wrong, but not how many.

### Task

For each incident, the participant:

1. reads it and either accepts the suggested priority or overrides it, giving
   a reason, using the platform's normal review controls;
2. answers two comprehension questions (for example "What did the caller say
   that makes this urgent?", "Is the location confirmed?"), multiple choice,
   with the transcript still visible.

After each block: the NASA Task Load Index (workload) and a five-item trust
questionnaire. At the end: the System Usability Scale and a short interview.

### Measures

| Measure | Definition |
|---|---|
| **Override accuracy** (primary) | Of the deliberately wrong suggestions, the share the participant overrides in the right direction |
| Unnecessary overrides | Of the correct suggestions, the share overridden |
| Comprehension | Share of comprehension questions answered correctly |
| Task time | Seconds from opening an incident to submitting the review |
| Workload | NASA-TLX raw score per block |
| Trust | Trust questionnaire score per block |
| Missed critical cues caught | Of seeded missed-critical-cue cases, the share raised to P0 |

### Hypotheses (registered before data collection)

- **H1:** override accuracy is higher in the evidence condition than in the
  score-only condition.
- **H2:** comprehension is higher in the evidence condition.
- **H3:** unnecessary overrides are not higher in the evidence condition
  (non-inferiority margin: 5 percentage points).
- **H4 (exploratory):** task time, workload and trust differ between
  conditions; no direction predicted.

### Analysis

- H1 and H2: mixed-effects logistic regression per trial, with condition, block
  order and incident difficulty as fixed effects and random intercepts for
  participant and incident. The effect is reported as an odds ratio with a 95%
  confidence interval.
- H3: one-sided test against the margin, same model.
- Task time: mixed-effects linear model on log time.
- No outcome is analysed before data collection ends. Participants who do
  not finish both blocks are reported and excluded from the primary analysis.

**Sample size.** With 16 to 24 participants and 8 deliberately wrong
suggestions each, the study can detect only large effects (roughly a 20 to 25
percentage-point difference in override accuracy). It is a pilot study, and
it is reported as one: a null result does not show the conditions are
equivalent.

### Participants

Practising telecommunicators are the target group. Trainees from a
telecommunicator course, or students on a public-safety programme, are a
fallback; if they are used, every result is labelled as coming from that
group. Exclusions: anyone who has worked on this project, and anyone who took
part in study A.

### Materials and set-up

- Incidents are synthetic, written for the study, and not taken from any
  dataset the platform was developed on.
- The study runs on a laptop using the platform's dashboard against a local
  instance with a study build: a score-only display mode, participant ids and
  per-trial timing. These features do not exist yet and are listed in the
  [ML layer design](../design/ml-layer-design-v1.0.md) as prerequisite work
  (RP-E1).
- Sessions are in person or by screen sharing, with the researcher present.
  The interview is audio-recorded only with consent, and transcribed without
  names.

## 5. Study C: independent re-evaluation

After the annotation round, one or two engineers who have not contributed to
the repository:

1. clone a tagged release on a clean machine;
2. follow `backend/README.md` and the release notes to reproduce the
   evaluation reports against the adjudicated labels;
3. report whether the aggregate figures match, what was unclear, and
   anything that did not work.

Their report is published in `docs/research/reviews/` with the release it
checked. This meets milestone ML-5's gate ("another engineer can reproduce
published aggregate findings") and answers open question 10.

## 6. Ethics and data protection

- **No real call data** is used in any study. All incidents are synthetic.
- **Study B is human-subjects research.** It must be reviewed by an
  institutional review board (IRB) or an equivalent ethics committee before
  recruitment, normally through an academic partner. Study A collects
  professional opinions and may qualify as exempt, but the board, not the
  project, decides that.
- **Consent:** written informed consent before taking part, covering
  purpose, procedure, time, recording, data use, publication and the right to
  withdraw at any time without giving a reason.
- **Data kept:** pseudonymous participant ids, responses, timings and
  questionnaire scores. Names and contact details are kept separately by the
  coordinator, and deleted when the study ends unless the person wants to be
  acknowledged.
- **Employer neutrality:** participants take part as individuals. No result
  is presented as the view of their employer or agency.
- **Wellbeing:** synthetic incidents can still describe distressing events.
  Participants are told this in advance, may skip any incident, and receive
  the contact details of a support service.
- **Compensation:** set by the project owner and the ethics board, paid
  whether or not the participant finishes.

## 7. Pre-registration

Before recruiting for study B, the hypotheses, measures, analysis plan,
exclusion rules and sample size in section 4 are registered with a public
time-stamped service (for example OSF Registries), and the registration link
is added to this document. Any later deviation is reported with the results.

## 8. What the results can and cannot support

From design v1.2 §16.3:

| After | It is fair to say | It is not fair to say |
|---|---|---|
| Annotation round | Results measured against independently annotated, adjudicated labels, with stated agreement | That the labels are a validated dispatch standard |
| Study A | Received documented feedback from named or described practitioners | That practitioners or their agencies endorse or adopted the platform |
| Study B | Measured effect of explanations on a small sample of reviewers using synthetic incidents | That it improves real dispatch decisions or outcomes |
| Study C | Another engineer reproduced the published results | That the results generalise to real calls |

Negative and null results are published with the same prominence as positive
ones.

## 9. What is needed to start

| Need | Owner | Blocks |
|---|---|---|
| Decide budget for participant and reviewer compensation | Project owner | A, B, annotation |
| Find an academic partner with an ethics board | Project owner | B (and A if the board requires it) |
| Recruit 3 to 5 practitioner reviewers | Project owner | A |
| Run the annotation round | Coordinator | C, and final RQ1 results |
| Build the study features (RP-E1) | Engineering | B |
| Write the 24 study incidents and comprehension questions, reviewed by a study A participant | Project owner | B |
| Register study B | Project owner | B recruitment |

## 10. Suggested order and timeline

1. Recruit practitioner reviewers and annotators (weeks 1 to 4).
2. Run the annotation round (weeks 3 to 8) and study A (weeks 5 to 8) in
   parallel.
3. Update the rubric if study A requires it; re-run the evaluation against
   adjudicated labels (weeks 8 to 10).
4. Ethics review, study features and pre-registration for study B (weeks 6 to
   12).
5. Run study B (weeks 12 to 16), then study C on the release that includes
   adjudicated labels.
6. Write up all results, including negative ones (weeks 16 to 20).

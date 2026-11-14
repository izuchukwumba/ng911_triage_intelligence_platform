# Independent annotation protocol (v1.0)

**For:** the independent annotators and the adjudicator who label the
platform's evaluation cases, and the coordinator who runs the round.
**Status:** ready to run; annotators not yet recruited.
**Implements:** design v1.2 §3A.7 (independent annotation by at least two
qualified reviewers, adjudication, inter-annotator agreement) and open
questions 6 and 7 (§18).

Every case you will see is **synthetic**: written by the project author or
produced by a generator. No real emergency call, caller or patient is
involved, and you will never be asked to provide one.

## 1. Why this is needed

Every label in the platform's evaluation data was written by the person who
also wrote the system being evaluated, or computed by a generator from the
same rubric. Results measured against those labels show the system agrees
with its author, not that it is right. Independent labels from qualified
people are what turn the platform's results from self-assessment into
evidence (design v1.2 §16.3).

The round has two goals:

1. **Label agreement:** do two qualified people, working separately under the
   same written rubric, give the same labels? Fields where they do not are
   fields the rubric does not define well enough.
2. **Rubric validity:** does the research rubric's priority match the
   priority an experienced practitioner would give? The rubric is the
   author's, not a dispatch protocol, and has not been reviewed by
   practitioners (open question 6).

## 2. Roles

| Role | Who | Does |
|---|---|---|
| Annotator (two or more) | A qualified practitioner (section 3) who did not help build the system | Labels every case independently |
| Adjudicator | A third qualified practitioner, ideally the most experienced | Resolves disagreements and records why |
| Coordinator | The project owner or someone they appoint | Prepares workbooks, answers rubric questions in writing, collects files, computes agreement |

The project author may coordinate but **may not annotate or adjudicate**:
their labels are the ones being checked.

## 3. Who can annotate

At least one of:

- two or more years as a 9-1-1 telecommunicator, call-taker or dispatcher;
- current or recent emergency medical, fire or police dispatch certification
  (for example EMD, EFD or EPD);
- two or more years as a paramedic, EMT, emergency nurse, firefighter or
  police officer who takes or acts on emergency calls.

Annotators should read English fluently. Spanish reading ability is useful:
a minority of cases are in Spanish or mix the two (section 6.6).

Record each person's qualification category and years of experience, not
their name, in the round's records. Names are kept only if the person
chooses to be acknowledged.

**Conflicts of interest:** anyone who contributed code, cases or labels to
this repository, or who has a commercial interest in a competing product,
should not annotate. Declare anything that might look like a conflict to the
coordinator.

## 4. What will be labelled

| Set | Cases | Purpose |
|---|---|---|
| Training set | 6 cases from `curated.jsonl`, `dev` split | Worked through together during training; not scored |
| Pilot set | 10 cases from `generated-1.0.0-seed42.jsonl`, `dev` split | Labelled independently, then discussed; not scored |
| Main set | All 50 curated cases, minus the 6 used for training, plus 156 generated cases | Labelled independently; scored and adjudicated |

The 156 generated cases are drawn as a stratified sample: up to 10 per
scenario family across all 17 families and all three splits, with the
perturbations (denial, past tense, uncertainty, hearsay, Spanish,
misspellings, children, multiple victims, address corrections) represented
in proportion. The coordinator records the sampling seed and the list of
case ids before the round starts, and the list does not change once
annotation begins.

Cases are shown in a **different random order to each annotator**.

**Blinding.** Annotators must not see:

- the existing labels, case notes, family names or split names;
- anything the platform produced for the case (priorities, cues, evidence);
- each other's labels, until adjudication.

The workbook shows only a neutral case number and the messages.

**Estimated effort:** about 2 minutes per case after the pilot, so roughly
7 to 8 hours for the main set, plus 2 hours for training and the pilot.
Annotators can work in sessions of any length; a break every hour helps
consistency.

## 5. Procedure

1. **Training (about 1 hour, together).** The coordinator walks through this
   protocol and the [labelling guide](../evaluation/labelling-guide.md) using
   the 6 training cases.
2. **Pilot (about 30 minutes, separately).** Each annotator labels the 10
   pilot cases alone.
3. **Pilot review (about 30 minutes, together).** Compare pilot labels and
   discuss every disagreement. If the rubric itself was the cause, the
   coordinator records a clarification in writing and sends it to everyone.
   Clarifications are added to the labelling guide's change log after the
   round, so the published guide matches what annotators used.
4. **Main round (separately).** Annotators label the main set without
   talking to each other about cases. Questions about the rubric go to the
   coordinator, who answers in writing to **all** annotators.
5. **Agreement.** The coordinator computes agreement (section 8) before
   adjudication, so the published figures describe independent work.
6. **Adjudication.** The adjudicator sees both annotators' labels for every
   case where they differ, decides the final label, and writes one sentence
   saying why.
   - `python -m ntip.evaluation.adjudication sheet` lists only the
     disputed cases, with the messages and each annotator's labels.
   - The adjudicator fills in a `decision` for each case: an annotator's
     name, or `own` if neither label fits. For `own`, they label the case
     themselves in a label sheet with annotator `ADJ`. Every row also needs
     a `reason`.
   - `python -m ntip.evaluation.adjudication apply` writes the dataset
     records, with `label_source: "adjudicated"`. It refuses a missing
     decision, a missing reason or an unknown annotator.

Do not change labels after submitting them, except through adjudication.

## 6. What to label for each case

The [labelling guide](../evaluation/labelling-guide.md) is the rubric. Apply
it as written, even where you would decide differently in practice: section
6.7 is where your own judgement goes. If the rubric is unclear or seems
wrong, label as best you can and note it in `rubric_concern`.

Label **what the caller reported**, not what is medically or operationally
true. "I think he's not breathing" is a report of not breathing, stated with
uncertainty.

### 6.1 Cues

For each cue code in the labelling guide that the caller mentions, record:

| Field | Values |
|---|---|
| `code` | A code from the labelling guide's table |
| `status` | `affirmed` (stated as happening now), `uncertain` (the caller is unsure: "I think", "maybe"), `negated` (denied: "no fire"), `historical` (happened earlier and has stopped), `hypothetical` ("if he…"), `retracted` (taken back: "false alarm") |
| `evidence` | The shortest exact words from the message that support the cue, copied as written, including spelling mistakes |

Record a cue even when it is denied, past or hypothetical. The status is
what matters. A cue mentioned twice needs one entry, with the evidence that
best shows its final status.

How this maps to the existing labels: `affirmed` and `uncertain` cues are
the case's `cues`; `negated`, `historical`, `hypothetical` and `retracted`
cues are its `absent_cues`.

### 6.2 Domain, severity and priority

Use the labelling guide's sections 2 and 5. Priority follows from severity
by the table in section 2; do not set it separately.

### 6.3 Location

- `location`: `present`, `missing` or `conflicting`, as in the labelling
  guide.
- `location_components` (new): the exact words the caller used for each
  part they gave: `house_number`, `street`, `unit` (apartment, floor, room),
  `intersection`, `landmark`, `locality` (town, city, area). Leave a part
  empty when it was not given. Do not correct, complete or look anything up.
- If the caller corrects an address ("sorry, I mean 14 Elm, not 41"), record
  the final address and set `location` to `conflicting` only when the two
  addresses are never reconciled.

### 6.4 Victim count

A number when one is stated (a range counts as its upper bound),
`unknown` when several people are mentioned without a number, and empty when
it is not mentioned.

### 6.5 Overall certainty

`case_uncertainty`: `clear` when you are confident of every label above,
`some_doubt` when at least one label was a judgement call, `cannot_tell` when
the transcript does not support a confident label.

### 6.6 Language

Label Spanish and mixed-language cases the same way. Copy evidence in the
original language. If you cannot read a case, mark it `skipped_language`
rather than guessing; skipped cases are reported, not counted as
disagreements.

### 6.7 Your own judgement (practitioner fields)

These fields are about the rubric, not the transcript. They are never used as
training data, and they are reported separately.

| Field | Values |
|---|---|
| `practitioner_priority` | The priority (P0 to P4, same meanings as the rubric) you believe the call should get in practice, regardless of the rubric |
| `realism` | 1 (not plausible as a real call) to 5 (very plausible) |
| `rubric_concern` | Free text: where the rubric's answer differs from yours, or the rubric was unclear. Leave empty if none |
| `comment` | Anything else about the case |

## 7. Workbook format

One row per case and cue, in a spreadsheet or CSV:

| Column | Example |
|---|---|
| `case_number` | 0137 |
| `annotator` | A2 |
| `cue_code` | NOT_BREATHING |
| `cue_status` | historical |
| `evidence` | was not breathing earlier |
| `domain` | ems |
| `severity` | elevated |
| `location` | present |
| `house_number` / `street` / `unit` / `intersection` / `landmark` / `locality` | 9 / Pine Road / / / / |
| `victim_count` | 1 |
| `case_uncertainty` | clear |
| `practitioner_priority` | P2 |
| `realism` | 4 |
| `rubric_concern`, `comment` | |

Case-level columns are repeated on each cue row of the same case. A case
with no cues has one row with `cue_code` empty.

The coordinator converts the returned workbooks into dataset records with
`label_source: "adjudicated"` after adjudication. Three commands do the
mechanical work (`backend/src/ntip/evaluation/annotation.py`):

1. **`sample`** fixes the round's cases. It writes a *round file* that maps
   neutral four-digit case numbers to case ids and records each dataset's
   digest. Only the coordinator keeps it.
2. **`export`** writes two CSV files per annotator. `A1-cases.csv` holds the
   case numbers and messages, in an order unique to that annotator.
   `A1-labels.csv` is the label sheet with the columns above. Neither file
   names a case id, family, split, label or platform output.
3. **`import`** reads the returned label sheets and checks them. It refuses
   to run if a dataset has changed since sampling. It checks every value
   and every case's repeated columns. Each quoted `evidence` and location
   part must occur verbatim in the case's messages, and it becomes an exact
   span. Every problem is reported with its spreadsheet row number, and
   nothing is written until the sheet is clean. Practitioner fields are kept
   apart from the labels.

```sh
cd backend
python -m ntip.evaluation.annotation sample --round R1 --seed <seed> --all ../data/eval/curated.jsonl --exclude <training case ids> --stratified ../data/eval/generated-2.1.0-seed42.jsonl --per-family 3 --out <private dir>/R1.json
python -m ntip.evaluation.annotation export --round <private dir>/R1.json --annotator A1 --annotator A2 --out <private dir>/R1
python -m ntip.evaluation.annotation import --round <private dir>/R1.json --workbook A1-labels.csv --workbook A2-labels.csv --out <private dir>/R1/imported
```

### Worked example

> "He was not breathing earlier but he is breathing now, he's awake and
> talking. We're at 9 Pine Road."

| Field | Label | Why |
|---|---|---|
| Cue | `NOT_BREATHING`, `historical`, "was not breathing earlier" | Reported as past and resolved |
| Domain | `ems` | A medical call |
| Severity | `elevated` | No current critical cue; a critical event in the past (labelling guide v1.1) |
| Location | `present`; house number "9", street "Pine Road" | An address is given |
| Victim count | 1 | One person is described |

## 8. Agreement measures

Computed on the main set from the annotators' independent labels, before
adjudication. With more than two annotators, Krippendorff's alpha replaces
Cohen's kappa.

| Field | Measure |
|---|---|
| Each cue code (present/absent) | Cohen's kappa, with the number of cases where either annotator reported it |
| Cue status | Kappa over cues both annotators recorded |
| Evidence | Token-overlap F1 between the two quotes; exact-match rate |
| Domain | Cohen's kappa |
| Severity | Krippendorff's alpha (ordinal) and exact agreement |
| Priority | Exact agreement; within-one-level agreement |
| Location and components | Kappa for `location`; exact match per component |
| Victim count | Exact agreement |
| Practitioner priority vs rubric priority | Agreement per annotator, and the direction of every difference |

Every figure is reported with its count and a bootstrap 95% confidence
interval (2,000 resamples by case, seed recorded).

**Pre-declared interpretation** (Landis and Koch's commonly used bands, fixed
before the round):

- kappa or alpha of 0.80 or more: labels for that field are used as
  reference labels;
- 0.60 to 0.79: used, with the agreement reported next to every result
  that depends on them;
- below 0.60: the field is **not** used as a reference label. The rubric for
  it is revised and the field is labelled again in a later round.

Low agreement is a finding, not a failure to hide. All figures are
published, including the poor ones.

`python -m ntip.evaluation.agreement <imported>/A1.jsonl <imported>/A2.jsonl --out <dir>`
computes every measure above from the imported label sheets and writes
`agreement.json` and `agreement.md`. Each figure comes with its count, a
bootstrap interval and its band. The implementation is checked against
Krippendorff's published worked example.

## 9. What happens to the labels

- **Adjudicated labels become the reference labels** for the evaluation sets,
  with `label_source: "adjudicated"`. Earlier author labels are kept in the
  repository history; the differences between author and adjudicated labels
  are reported, because they measure how far the author's labels could be
  trusted.
- **Held-out data stays held out.** Annotating test cases does not expose them
  to system development: annotators are not developers. The project author
  must not use adjudicated test labels to change rules, prompts or models;
  only dev and regression labels may guide development.
- **Practitioner fields** feed the rubric review in the
  [research protocol](research-protocol.md) (study A). They are not used as
  labels.
- **Published data:** the adjudicated labels, the agreement report and each
  annotator's pseudonymous labels are published with the dataset. Free-text
  comments are published only with the annotator's agreement.
- **Credit:** annotators who wish to be named are acknowledged in the dataset
  card and any paper that uses the labels.

## 10. Practical terms (to be set by the project owner)

- Compensation and how it is paid.
- Deadline for the main round (suggested: three weeks after the pilot).
- How files are exchanged (a shared folder only the coordinator and that
  annotator can see).
- Whether an institution's ethics review is needed. Labelling synthetic text
  is not usually human-subjects research, but the practitioner fields are
  opinions; if the results will be published through a university, ask its
  review board for a determination first (see the
  [research protocol](research-protocol.md), section 6).

## 11. Checklist for the coordinator

- [ ] Annotators and adjudicator recruited; qualifications and conflicts recorded
- [ ] Main-set case list and sampling seed recorded before starting
- [ ] Blinded workbooks generated, each with its own case order
- [ ] Training and pilot held; written clarifications sent to everyone
- [ ] Main round returned; agreement computed before adjudication
- [ ] Adjudication complete, with a reason for every changed label
- [ ] Labelling guide change log updated; dataset records updated as `adjudicated`
- [ ] Agreement report published in `docs/evaluation/results/`
- [ ] Evaluation re-run against adjudicated labels (dev, regression; test only as a frozen-release run)

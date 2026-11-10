# Labelling guide (v1.0)

How to label a synthetic case in `data/eval/*.jsonl` so that labels are
consistent and can be checked by a second annotator (design v1.2, §3A.7).
Labels describe **what was reported**, not what is medically or operationally
true.

## 1. Cues (`labels.cues`, `labels.absent_cues`)

List every cue from the table below that the caller reports **as happening now**,
whether stated with certainty or uncertainty ("I think he's not breathing",
"I'm not sure if he's breathing" both count). The list must be exhaustive for
these codes.

Put a cue in `absent_cues` when it is mentioned but **denied** ("no fire"),
**in the past** ("he wasn't breathing earlier, he is now"), **hypothetical**
("he might have a heart attack if…") or **retracted** ("false alarm").

| Code | Report it when the caller says… |
|---|---|
| `NOT_BREATHING` | not breathing, no pulse, heart stopped, or is unsure whether the person is breathing |
| `UNCONSCIOUS` | unconscious, unresponsive, won't wake up, not moving, collapsed, won't answer |
| `OCCUPANTS_TRAPPED` | people trapped or inside a burning/collapsed structure or vehicle |
| `WEAPON_PRESENT` | a gun, knife or other weapon, or a shooting/stabbing |
| `ACTIVE_BLEEDING` | bleeding or blood from a person |
| `ACTIVE_VIOLENCE` | fighting, assault, someone being hit or threatened |
| `CARDIAC_SYMPTOMS` | heart attack, cardiac arrest, chest pain/pressure |
| `BREATHING_DIFFICULTY` | trouble breathing, choking, gasping |
| `SEIZURE` / `STROKE_SYMPTOMS` / `OVERDOSE` | the condition or its typical description |
| `FIRE_REPORTED` / `SMOKE_REPORTED` / `FIRE_SPREADING` / `EXPLOSION_REPORTED` | as named |
| `HAZARDOUS_ENVIRONMENT` | gas smell or leak, chemicals, fumes, carbon monoxide |
| `INJURY_REPORTED` | an injury or pain not covered above |
| `MULTIPLE_VICTIMS` | two or more people affected |
| `CHILD_INVOLVED` | a baby, toddler or child (an explicit age under 18 also counts) |

## 2. Severity and priority (`labels.severity`, `labels.priority`)

Research rubric, applied in order. Priority follows from severity
(critical→P0, high→P1, elevated→P2, standard→P3, low→P4, undetermined→P2).

| Severity | When |
|---|---|
| critical | An immediate threat to life: not breathing, unconscious, people trapped, weapon with bleeding; or a *high* situation involving a child or multiple victims |
| high | A serious current condition: weapon, active violence, significant bleeding, cardiac or breathing symptoms, seizure, stroke, overdose, spreading fire, explosion, hazardous materials |
| elevated | Fire or smoke without the above; an older person unable to get up; entrapment with no hazard; a threat that has left the scene |
| standard | A matter for emergency services with no serious condition (minor injury, minor bleeding, property crime, welfare check) |
| low | No current emergency: prank, retraction, past event, hypothetical |
| undetermined | The nature of the call cannot be told from the transcript |

Missing or uncertain **location never changes severity** (ADR-004, DDL-011).

## 3. Location (`labels.location`)

`present` if the caller gives any address, intersection, road or landmark;
`conflicting` if they give two different addresses; otherwise `missing`.

## 4. Victim count (`labels.victim_count`)

A number when one is stated (a range counts as its upper bound), `"unknown"`
when several people are mentioned without a number, omitted when not mentioned.

## 5. Domain (`labels.domain`)

The primary service: `police`, `fire`, `ems`, `hazmat`; `other` for non-emergency
calls such as pranks; `unknown` when it cannot be told.

# NG911-Aligned Emergency Triage Intelligence Platform
## Full Implementation Plan, Design Rationale, and Feature Goals

## 1. Project Purpose

### Core mission
This project is an **NG911-aligned decision-support platform** for emergency incident triage, prioritization, and post-incident review.

It is **not** a replacement for 911 dispatchers, a full NG911 core-services implementation, or a direct claim of standards compliance. The intended role is narrower and more credible:

- take in emergency-call-like inputs
- convert them into structured incident objects
- score and prioritize them in an explainable way
- present them to a human operator
- preserve an audit trail for replay, evaluation, and training

### Why this project exists
Emergency response systems are moving toward more structured, IP-based, GIS-aware workflows. However, modernization of transport and routing infrastructure does not automatically solve the downstream intelligence problems:

- emergency inputs are messy, incomplete, and emotionally noisy
- prioritization decisions are often inconsistent under time pressure
- location quality is variable
- incident review and training require traceability
- simulation and evaluation environments are often weak or ad hoc

This project targets that gap.

### Main goal
The main goal is to build a **credible decision-support layer** that improves three things:

1. **Interpretation**  
   Convert messy input into a structured representation of what is happening.

2. **Prioritization**  
   Produce an urgency score and rank incidents using transparent, reviewable logic.

3. **Accountability and learning**  
   Preserve the complete decision chain so incidents can be replayed, reviewed, and improved over time.

---

## 2. Positioning and Scope

### Correct positioning
The correct public description of the project is:

> This project simulates an NG911-aligned decision-support layer for emergency call triage, prioritization, and post-incident analysis.

### Important scope boundaries
The project should **not** claim:

- full NG911 compliance
- direct ESInet implementation
- direct SIP/i3 core call routing support
- replacement of dispatchers or PSAP decision-makers
- autonomous dispatching

### Why this positioning is important
This scope makes the project more credible for engineers, reviewers, and immigration narratives. It shows awareness of real emergency infrastructure constraints while focusing on an area where an individual engineer can produce a serious contribution: operational intelligence and review tooling.

---

## 3. Primary Design Principles

Every system decision should be guided by these principles.

### 3.1 Human-in-the-loop by default
This system supports human operators. It does not replace them.

**Reasoning**
Emergency response is high-stakes and context-sensitive. A realistic system must assist rather than fully automate. Human-in-the-loop design also improves credibility and aligns with operational reality.

**Implications**
- every score should be explainable
- the UI should surface evidence, not just outputs
- override and review workflows should be visible in future versions

---

### 3.2 Structured before intelligent
The project should prioritize robust structured incident modeling before advanced ML.

**Reasoning**
Most weak emergency-AI projects start by chasing model sophistication without designing the right operational object model. The structured incident object is the backbone of ingestion, ranking, UI, audit, evaluation, and possible integrations.

**Implications**
- schema design is phase-one critical
- parser quality is defined by field usefulness, not fancy NLP
- downstream systems depend on consistent normalized outputs

---

### 3.3 Deterministic before probabilistic
The first prioritization engine should be rule-based and explainable.

**Reasoning**
Reviewability matters more than raw predictive complexity in early versions. Deterministic logic lets the system generate clear reason codes, supports auditability, and is easier to test and defend.

**Implications**
- use weighted scoring rules first
- expose reason codes in all outputs
- add ML later only as an optional enhancement

---

### 3.4 Replayability is a first-class feature
Replay and audit are not “nice to have.” They are central.

**Reasoning**
Without replay, the project looks like a demo app. With replay, it starts to look like operational infrastructure and a training/evaluation environment.

**Implications**
- store raw input and transformed outputs
- version the scoring logic
- support deterministic re-runs on past incidents

---

### 3.5 Location quality matters
Location should be handled as a structured confidence-bearing field, not a string pasted into the record.

**Reasoning**
In emergency response, bad location data can damage triage quality. The system should visibly model dispatchable-location quality and uncertainty.

**Implications**
- represent address and coordinate data separately
- include completeness and confidence scores
- penalize uncertainty where appropriate

---

### 3.6 Build one flagship platform, not scattered mini-projects
This project should live in a monorepo with modular components.

**Reasoning**
The project is meant to look like a coherent infrastructure platform, not a bag of disconnected demos. A monorepo supports a stronger technical story and a stronger petition narrative.

**Implications**
- apps, services, packages, docs, and infra should live together
- internal modules should be reusable but not fragmented too early

---

## 4. High-Level System Architecture

The system can be understood as a pipeline:

1. **Input / ingestion**
2. **Normalization**
3. **Incident structuring**
4. **Prioritization**
5. **Presentation**
6. **Audit and replay**
7. **Evaluation**

### Pipeline view

```text
Input Stream / Transcript / JSON
            ↓
      Ingestion Service
            ↓
 Transcript-to-Incident Parser
            ↓
   Structured Incident Object
            ↓
   Prioritization / Scoring Engine
            ↓
     Dashboard + Operator Review
            ↓
    Audit Store + Replay Engine
            ↓
      Evaluation / Benchmarking
```

### Why this architecture
This pipeline cleanly separates concerns:

- ingestion handles incoming data shape
- parser handles semantic conversion
- schema stabilizes representation
- prioritizer handles urgency
- dashboard supports human review
- audit and replay support accountability
- evaluation supports iteration and evidence of improvement

This also maps well to how infrastructure systems are typically decomposed.

---

## 5. Recommended Monorepo Structure

```text
ng911-triage-intelligence/
  apps/
    dashboard/
    simulator/
  services/
    ingestion-api/
    transcript-parser/
    prioritization-engine/
    audit-service/
  packages/
    incident-schema/
    location-validator/
    test-data-generator/
    replay-engine/
    shared-types/
  data/
    fixtures/
    generated/
  docs/
    architecture/
    standards-alignment/
    design-decisions/
    evaluation/
  infra/
    docker/
    scripts/
  .github/
    workflows/
```

### Why this structure
This layout communicates maturity immediately.

- `apps/` contains user-facing surfaces
- `services/` contains operational system logic
- `packages/` contains reusable core modules
- `data/` contains fixtures and generated simulation inputs
- `docs/` makes the project understandable and serious
- `infra/` shows reproducibility and deployment awareness

This is better than multiple repos at this stage because it keeps one clear project identity.

---

## 6. Core Features and Full Implementation Details

# Feature 1: Incident Schema

## Goal
Create the canonical structured representation of an emergency incident.

## Why this feature exists
The entire system depends on a stable object model. Without a strong schema, every downstream module becomes fragile and inconsistent.

## What the schema should include

### Top-level fields
- `incident_id`
- `received_at`
- `source_type`
- `raw_input`
- `incident`
- `location`
- `caller_context`
- `triage`
- `audit`

### Example structure
```json
{
  "incident_id": "uuid",
  "received_at": "2026-04-11T20:00:00Z",
  "source_type": "transcript",
  "raw_input": {
    "text": "someone has been shot near 5th street and is bleeding badly"
  },
  "incident": {
    "domain": "police",
    "subtype": "shooting",
    "summary": "Possible shooting with severe bleeding reported near 5th street",
    "severity_indicators": [
      "weapon_present",
      "active_bleeding"
    ],
    "victim_count_estimate": 1,
    "confidence": 0.89
  },
  "location": {
    "address_text": "near 5th street",
    "lat": null,
    "lng": null,
    "location_confidence": 0.44,
    "dispatchable_location_score": 0.31,
    "validation_notes": [
      "address incomplete"
    ]
  },
  "caller_context": {
    "caller_id_hash": null,
    "language_hint": "en",
    "background_noise_level": null
  },
  "triage": {
    "priority_score": null,
    "priority_tier": null,
    "reason_codes": []
  },
  "audit": {
    "schema_version": "0.1.0",
    "parser_version": "0.1.0",
    "scoring_version": null
  }
}
```

## Decision rationale
The schema is divided into domains so the project can evolve cleanly:
- raw input stays preserved
- incident meaning is separated from location quality
- triage output is separated from parsing output
- audit metadata is always attached

This separation allows reprocessing, replay, and scoring logic upgrades without corrupting the original record.

## Notes to consider
- schema versioning is mandatory
- nullable fields are acceptable early on
- preserve raw input even if parsing fails
- avoid overfitting the schema to only one incident type

## Contribution to main goal
This feature serves all three main goals:
- interpretation through normalized structure
- prioritization through machine-readable fields
- accountability through versioned audit metadata

---

# Feature 2: Transcript-to-Incident Parser

## Goal
Convert raw transcript-like text into a structured incident object.

## Why this feature exists
Emergency inputs are often unstructured. The parser is the translation layer between human messiness and operational system logic.

## Initial implementation strategy
Start with a rules-first parser.

### Parsing stages
1. text normalization
2. keyword and phrase extraction
3. domain classification
4. subtype classification
5. severity cue extraction
6. victim-count estimation
7. summary generation
8. confidence estimation

## Example parsing logic
Input:
> “my brother is not breathing please help we are at 123 oak street”

Output:
- domain: `ems`
- subtype: `respiratory_distress`
- severity indicators:
  - not_breathing
  - immediate_medical_emergency
- address text:
  - `123 oak street`

## Why rules-first was chosen
A deterministic parser gives you:
- transparency
- quick implementation
- stable debugging
- clear testability

It also prevents the project from becoming blocked by model research.

## Potential parser components
- keyword dictionaries
- phrase patterns
- severity maps
- address extraction heuristics
- confidence scoring heuristics
- summary template generator

## Relevant notes
- confidence should be attached to parser outputs
- preserve uncertainty instead of pretending certainty
- parser should not mutate raw input
- in future, optional LLM assistance can be plugged in behind the same interface

## Contribution to main goal
This feature directly supports:
- interpretation of messy emergency inputs
- normalized downstream prioritization
- auditability of extraction behavior

---

# Feature 3: Prioritization Engine

## Goal
Assign urgency scores and rank incidents in an explainable way.

## Why this feature exists
The platform’s central decision-support value comes from helping humans quickly understand what appears most urgent.

## Initial implementation strategy
Use a weighted rule engine.

### Example scoring factors
- weapon mentioned
- active violence
- severe bleeding
- unconscious / not breathing
- child involved
- multiple victims
- fire spread
- hazardous environment
- location uncertainty penalty
- low confidence penalty
- prank / non-emergency indicators

### Example output
```json
{
  "priority_score": 0.94,
  "priority_tier": "P0",
  "reason_codes": [
    "WEAPON_PRESENT",
    "ACTIVE_BLEEDING",
    "HIGH_SEVERITY_MEDICAL"
  ]
}
```

## Why deterministic scoring was chosen first
Because the system must be defensible. In high-stakes domains, a score with explicit reason codes is more useful than a black-box probability without operational explanation.

## Suggested implementation details
- scoring config in a versioned file
- additive and subtractive weights
- optional threshold-based escalation rules
- reason codes tied to every major score contribution
- tie-breaking rules for equal scores

## Relevant notes
- the score should not pretend to be objective truth
- reason codes must be preserved in the audit trail
- scoring logic should be versioned independently
- future ML models can be layered as “advisory signals” rather than replacing explainability

## Contribution to main goal
This feature is the direct engine of prioritization and the most visible decision-support component.

---

# Feature 4: Ingestion API

## Goal
Expose the platform through service endpoints rather than one-off scripts.

## Why this feature exists
Once the parser and prioritizer exist, the system needs a realistic interface for:
- dashboards
- simulators
- tests
- future integrations

## Suggested endpoints
- `POST /ingest`
- `POST /score`
- `GET /incidents/:id`
- `GET /incidents`
- `POST /replay`
- `GET /health`

## Why this decision was made
An API boundary makes the project feel and behave like infrastructure, not a classroom assignment. It also decouples frontends and simulators from backend implementation details.

## Notes
- no need for production-grade auth in the first phase
- response objects should preserve full reason-code data
- API contracts should be documented
- consider OpenAPI later for polish

## Contribution to main goal
The API turns the core logic into an operational platform and enables the UI and simulation workflows.

---

# Feature 5: Dashboard

## Goal
Give a human operator a clear view of ranked incidents, evidence, and reasoning.

## Why this feature exists
A dashboard is essential for two reasons:
1. operational realism
2. communicability to non-technical reviewers

## Core screens
- incident queue
- ranked priority list
- incident details panel
- parser evidence panel
- reason-code panel
- replay panel

## Why this feature matters strategically
A lot of technical reviewers and immigration reviewers will understand a system much faster from a polished UI than from backend code. The dashboard makes the project legible.

## Recommended dashboard sections

### Queue view
- incident id
- domain
- subtype
- score
- priority tier
- time received

### Incident details view
- raw transcript
- generated summary
- severity indicators
- location quality
- parser confidence

### Triage view
- priority score
- reason codes
- scoring version
- confidence caveats

## Notes
- the dashboard does not need enterprise-grade styling
- clarity beats beauty
- reason-code transparency should be visually obvious
- replay controls should be included as soon as possible

## Contribution to main goal
This feature supports human-in-the-loop interpretation and prioritization, and it makes accountability features visible.

---

# Feature 6: Audit Service

## Goal
Persist the complete transformation chain for every incident.

## Why this feature exists
Without an audit store, the system cannot support serious review, traceability, or deterministic re-analysis.

## What should be stored
- raw input
- normalized incident object
- parser outputs
- score outputs
- reason codes
- timestamps
- schema version
- parser version
- scoring version

## Storage choice
Use PostgreSQL or Supabase/Postgres early on.

## Why this decision was made
A relational database provides enough structure for reliable querying without unnecessary infrastructure complexity.

## Notes
- do not overwrite historical scoring results without versioning
- preserve original timestamps
- preserve both machine summary and raw transcript
- maintain immutable incident records where possible

## Contribution to main goal
This is the backbone of accountability and post-incident analysis.

---

# Feature 7: Replay Engine

## Goal
Re-run prior incidents or streams to evaluate system behavior.

## Why this feature exists
Replay is what elevates this project from a triage demo into something that resembles operations, evaluation, and training infrastructure.

## Replay modes
1. single-incident replay
2. chronological stream replay
3. compare scoring-version replay

## Important replay capabilities
- deterministic reprocessing
- side-by-side comparison of outputs
- ability to inspect why ranking changed
- support for stress-test scenarios

## Why this decision was made
In emergency settings, post-incident review and simulation matter. Replay supports:
- training
- regression testing
- scoring revisions
- system credibility

## Notes
- replay should preserve original order and timing metadata
- version comparisons are highly valuable
- replay datasets should include both clean and ambiguous incidents

## Contribution to main goal
This feature directly supports the “review and improve” pillar.

---

# Feature 8: Test Data Generator

## Goal
Generate synthetic emergency scenarios at volume.

## Why this feature exists
The system needs data for demos, testing, replay, and evaluation. Writing all cases by hand does not scale.

## Scenario types
- shooting
- stabbing
- house fire
- vehicle crash
- robbery
- unconscious person
- breathing difficulty
- domestic violence
- suspicious package
- welfare check

## Generator controls
- severity level
- location completeness
- number of victims
- amount of ambiguity
- amount of emotional noise
- false-alarm likelihood

## Why this decision was made
Synthetic data makes it possible to:
- benchmark the system
- test edge cases
- drive dashboard demos
- simulate incident streams

## Notes
- generated data should still look realistic
- include ambiguity and incompleteness
- store seeds for reproducibility where possible

## Contribution to main goal
This feature supports evaluation, testing, and replay, which in turn strengthen prioritization and accountability.

---

# Feature 9: Location Validator

## Goal
Assess quality and usability of incident location information.

## Why this feature exists
Emergency response depends heavily on location quality. A transcript may indicate high severity but still have poor dispatchability if the location is vague.

## What it should do
- detect whether an address appears complete
- score dispatchable-location quality
- capture coordinate availability
- attach validation notes
- contribute penalties or uncertainty signals to triage

## Why this decision was made
Location is a real operational constraint. Modeling it explicitly makes the project feel much more grounded in actual emergency workflows.

## Notes
- location quality should influence score confidence, not just incident severity
- keep a distinction between severity and dispatchability
- vague locations should be visible in UI and logs

## Contribution to main goal
This feature improves both interpretation and prioritization by grounding urgency in response feasibility.

---

# Feature 10: Evaluation Harness

## Goal
Measure system behavior over defined scenarios and compare versions.

## Why this feature exists
A serious system needs evaluation beyond “it seems to work.”

## Metrics to track
- classification accuracy on labeled synthetic sets
- reason-code consistency
- score stability
- ranking quality
- latency
- false high-priority rate
- false low-priority rate

## Why this decision was made
The project needs a credible way to show improvement over time. Evaluation turns development into evidence.

## Notes
- do not over-claim statistical validity
- use scenario-based evaluation honestly
- compare baseline vs revised scoring logic

## Contribution to main goal
This feature reinforces prioritization quality and demonstrates disciplined iteration.

---

## 7. Suggested Technology Choices

### Backend
- Node.js + TypeScript or Python + FastAPI

### Recommendation
Use **Node.js + TypeScript** for the API and dashboard-facing services if you want stack consistency and speed across the monorepo.

Use Python only if you strongly prefer it for parser experimentation or future evaluation tooling.

### Frontend
- React
- optional Next.js or Vite

### Database
- PostgreSQL
- Supabase is acceptable for velocity

### Shared package tooling
- TypeScript packages for schema, shared types, and validator modules

### Why these choices
The project benefits from:
- fast iteration
- clear typing
- modular packaging
- relatively low operational overhead

Avoid unnecessary complexity like Kubernetes, event buses, or distributed tracing early on unless required later.

---

## 8. Development Phases

## Phase 1: Core intelligence
Build:
- incident schema
- parser
- prioritization engine
- CLI or simple API

### Goal
Show end-to-end incident structuring and scoring.

---

## Phase 2: Operational realism
Build:
- ingestion API
- dashboard
- audit store
- replay engine

### Goal
Show that the platform resembles decision-support infrastructure rather than a script.

---

## Phase 3: Evaluation and realism
Build:
- test-data generator
- location validator
- evaluation harness
- polished docs

### Goal
Show serious system maturity and repeatability.

---

## Phase 4: Visibility and packaging
Build:
- articles
- public demo
- architecture docs
- standards-alignment doc
- narrative summary

### Goal
Turn technical work into public and petition-friendly evidence.

---

## 9. Important Non-Goals

To stay focused, the project should avoid becoming any of the following too early:

- a perfect ASR platform
- a full GIS product
- a dispatch-routing engine
- a production telephony stack
- a deep-learning research project
- a mobile-first product
- a compliance-certification effort

These can distract from the main value proposition.

---

## 10. Risks and How to Avoid Them

### Risk: Overengineering too early
**Avoid by**
- starting rule-based
- using a simple database
- keeping infra lean

### Risk: Weak narrative due to feature sprawl
**Avoid by**
- forcing every feature to map to interpretation, prioritization, or review

### Risk: Looking like a toy
**Avoid by**
- adding replay
- adding audit
- adding location-quality modeling

### Risk: Making inflated claims
**Avoid by**
- using “NG911-aligned” rather than “NG911-compliant”
- clearly stating scope boundaries

### Risk: Getting stuck on ML
**Avoid by**
- shipping a deterministic baseline first
- treating ML as optional iteration, not prerequisite

---

## 11. How Each Feature Maps to the Main Goal

### Interpretation
- incident schema
- transcript parser
- location validator

### Prioritization
- scoring engine
- reason codes
- dashboard ranking view

### Accountability and learning
- audit service
- replay engine
- evaluation harness
- test-data generator

This mapping should remain visible in the README and docs so the project always feels coherent.

---

## 12. Documentation Requirements

The repository should include at least the following documents:

- `README.md`  
  Project summary, architecture, quick start, screenshots, scope boundaries

- `docs/architecture/system-overview.md`  
  Detailed architecture and data flow

- `docs/design-decisions/decision-log.md`  
  Why key decisions were made

- `docs/standards-alignment/ng911-alignment.md`  
  Honest explanation of what “aligned” means and what it does not mean

- `docs/evaluation/evaluation-plan.md`  
  Metrics and replay/evaluation methodology

### Why this matters
Documentation is not just polish. It is part of the evidence that the project is serious, deliberate, and professionally conceived.

---

## 13. Public-Facing Narrative

A strong public-facing explanation is:

> This project is an NG911-aligned decision-support platform that converts emergency-call-like inputs into structured incident objects, prioritizes them using explainable scoring logic, and preserves replayable audit trails for training, evaluation, and post-incident analysis.

### Why this narrative works
It is:
- ambitious but credible
- operational, not hype-driven
- clearly useful
- appropriately scoped

---

## 14. Final Guidance

The project should always feel like **one coherent platform** rather than many disconnected experiments.

Before adding any new feature, ask:

1. Does this improve interpretation?
2. Does this improve prioritization?
3. Does this improve accountability or review?
4. Does this make the platform look more like real decision-support infrastructure?

If the answer is no, it is probably not the right feature right now.

The best version of this project is not the one with the most AI. It is the one that most clearly demonstrates:

- operational understanding
- disciplined system design
- explainable decision support
- structured thinking about public-safety workflows
- credible engineering depth over time

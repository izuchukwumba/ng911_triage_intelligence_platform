# NG911 Triage Intelligence Platform

A research platform for turning emergency-call-like narratives into structured,
evidence-linked incident records, with an **advisory** urgency assessment, a
human in the loop, an append-only audit trail and reproducible evaluation. It
sits downstream of NG911 incident-data exchange and can import NENA EIDO
objects; it never routes calls or dispatches anything.

> **SIMULATION ONLY.** Synthetic data, advisory output. Not certified for
> emergency operations, not a substitute for trained telecommunicators or
> approved dispatch protocols, and not NG911 or i3 compliant
> ([what "NG911-aligned" means here](docs/standards-alignment/ng911-alignment.md)).

**Stack:** Python 3.12 (FastAPI, Pydantic v2, PostgreSQL, scikit-learn) ·
React + TypeScript (Vite) · Docker Compose · GitHub Actions

---

## What it does

| | |
|---|---|
| **Interprets** | A rules parser (baseline B0) extracts cues such as *not breathing* or *weapon* with polarity (stated / denied / uncertain), tense (current / past / hypothetical) and attribution, plus victim counts and every reported location. **Every fact quotes the exact span of the source it came from.** |
| **Assesses** | A versioned, pinned ruleset sets severity **only from reported conditions**. Missing location, uncertainty, contradictions and possible pranks add *review actions* for a human; they never lower urgency ([DDL-011](docs/design-decisions/decision-log.md), [DDL-013](docs/design-decisions/decision-log.md)). |
| **Keeps people in charge** | Operators see the evidence, why each rule fired, and confirm, correct or override. Overrides are stored next to the machine's assessment, never in place of it. |
| **Is accountable** | Source events, incident versions, assessments, reviews, model outputs and audit events are append-only; PostgreSQL triggers reject updates and deletes. Replay checks that stored assessments reproduce exactly and compares rulesets. |
| **Uses ML carefully** | Optional models (B1: a small scikit-learn classifier; B2: Claude with structured output, opt-in) only *propose* candidates. A candidate counts only if its quote matches the source; models can add findings but never remove one; a serious cue found only by a model needs human confirmation; a model failure falls back to rules. |
| **Interoperates** | An import-only gateway accepts NENA EIDO objects of one pinned edition (NENA-STA-021.1b), validated against NENA's own schema, with receipts, quarantine, idempotency and tenant isolation. |
| **Measures itself** | Labelled synthetic datasets, a scenario generator, metrics with confidence intervals, calibration, ML comparisons, latency, and a CI gate that fails any change that under-triages a critical case. |

Design: [technical design v1.2](docs/design/technical-design-v1.2.md) ·
architecture: [system overview](docs/architecture/system-overview.md) ·
safety: [safety case](docs/safety/safety-case.md), [threat model](docs/safety/threat-model.md) ·
decisions: [decision log](docs/design-decisions/decision-log.md) ·
status against the design: [traceability matrix](docs/traceability-matrix.md)

---

## Quick start

### Everything in containers

```sh
docker compose -f infra/docker/docker-compose.yml up --build
```

- Dashboard: <http://localhost:8080> (enter a development token such as
  `dev-operator`; see `NTIP_API_TOKENS` in the compose file)
- API docs: <http://localhost:8000/docs>

This starts PostgreSQL, runs migrations, and starts the backend, the optional
inference service and the dashboard. To try the ML path:

```sh
NTIP_MODEL=b1-tfidf-logreg NTIP_INFERENCE_MODE=hybrid_review \
  docker compose -f infra/docker/docker-compose.yml up --build
```

### Local development

```sh
# backend (Python 3.12)
cd backend
uv sync --extra dev --extra ml          # or: pip install -e ".[dev,ml]"
NTIP_AUTH_DISABLED=1 uvicorn ntip.api:create_app --factory --reload   # in-memory store, no auth

# dashboard
cd apps/dashboard
npm ci && npm run dev                   # http://localhost:5173, proxies to :8000
```

Details, configuration and the full API table: [backend/README.md](backend/README.md).

### Try it

```sh
# with the compose stack, use one of its development tokens, e.g. NTIP_TOKEN=dev-operator
curl -X POST localhost:8000/v1/incidents -H "Authorization: Bearer $NTIP_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text": "My wife is not breathing. I do not know where I am.", "synthetic": true}'
```

returns P0 with the review actions *confirm the critical report* and *verify
the location*: the missing address triggers verification, not a lower priority.

---

## Evaluation and results

```sh
cd backend
python -m ntip.evaluation                                   # B0 on curated dev + regression
python -m ntip.evaluation --split regression --gate         # the CI safety gate
python -m ntip.evaluation.compare --dataset ../data/eval/curated.jsonl --split test   # B0 vs B1 vs hybrid
python -m ntip.evaluation.latency                           # processing latency
python -m ntip.generator --n 510 --seed 42                  # regenerate the synthetic stress set
```

Every report records the git commit, dataset digest, ruleset digest, versions
and seed. Highlights from [docs/evaluation/results](docs/evaluation/results/README.md)
(synthetic data, author- or generator-written labels):

- Rules baseline on the curated dev + regression splits: critical-cue
  sensitivity 15/15, no under-triage, cue F1 0.99.
- On the held-out curated test split, hybrid rules + B1 removes both critical
  under-triages the rules make (2/9 → 0/9), at the cost of more over-triage;
  B1 alone generalises poorly. `rules_only` stays the default ([DDL-014](docs/design-decisions/decision-log.md)).
- B2 (Claude) has an adapter and tests but **has not been evaluated**: running
  it calls a paid external API and needs the owner's authorisation.

---

## What it is not, and what has not been shown

| Shown here | Not shown |
|---|---|
| A working research prototype with tests | Fitness for live emergency use |
| Performance on specified synthetic cases | Accuracy on real calls or operators |
| Validation against one pinned EIDO edition | EIDO, NENA-STA-024 or i3 conformance or certification |
| Author- and generator-written labels | Independent annotation or practitioner review |

Labelling guide and dataset limitations: [docs/evaluation/labelling-guide.md](docs/evaluation/labelling-guide.md),
[data/eval/README.md](data/eval/README.md). Standards referred to and the limit
of each claim: [source register](docs/standards-alignment/source-register.md).

---

## Repository layout

```text
backend/                Python backend (package ntip): API, parser, triage, ML, interop, evaluation
  schemas/              Published JSON Schema contracts (v1, v2)
  openapi.json          Published OpenAPI document
apps/dashboard/         Operator dashboard (React + TypeScript, generated API types)
data/eval/              Curated and generated labelled synthetic datasets
data/interop/eido/      Synthetic EIDO fixtures
docs/                   Design, architecture, decisions, safety, evaluation, ML, standards
infra/docker/           Compose stack
.github/workflows/      CI: backend (with PostgreSQL and the safety gate), dashboard,
                        container smoke test, dependency and secret scanning; release
```

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md);
releases and their notes: [docs/releases](docs/releases/README.md).

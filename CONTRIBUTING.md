# Contributing

## Project scope

This project is a decision-support platform for emergency call triage, not a general-purpose emergency communications system. Before contributing a feature, check that it improves at least one of:

1. **Interpretation** — the quality of structured incident extraction
2. **Prioritization** — the accuracy and explainability of urgency scoring
3. **Accountability** — the auditability, replayability, and reviewability of decisions

If a proposed change does not map to one of these three goals, it is probably out of scope.

---

## Getting started

### Prerequisites
- Node.js >= 18
- npm >= 8

### Install and build

```bash
npm install
npm run build
```

### Run tests

```bash
npm test
```

### Start the API

```bash
cd services/ingestion-api
npm run dev
```

### Start the dashboard

```bash
cd apps/dashboard
npm run dev
# → http://localhost:5173
```

### Run evaluation

```bash
cd packages/evaluation-harness
npx ts-node src/cli.ts
```

---

## Repository structure

```
packages/
  incident-schema/        Zod-validated types — edit carefully, downstream impact is high
  location-validator/     Location quality scoring
  test-data-generator/    Synthetic scenario generation
  evaluation-harness/     Accuracy measurement and scoring version comparison
services/
  transcript-parser/      NLP pipeline — keyword dicts, negation, language detection
  prioritization-engine/  Weighted rule scorer + versioned config
  ingestion-api/          Express REST API + store adapters
apps/
  dashboard/              React operator dashboard (Vite)
data/
  fixtures/               Labeled evaluation scenarios (do not delete)
docs/
  architecture/
  design-decisions/
  standards-alignment/
  evaluation/
infra/
  docker/                 docker-compose.yml + Dockerfile
```

---

## Key conventions

### Schema changes
Any change to `packages/incident-schema/src/index.ts` that modifies existing field types (not adding optional fields) is a **breaking change**. Bump `SCHEMA_VERSION` and update the design decision log.

### Scoring config changes
Do not edit `scoring-rules.json` without bumping `scoring_version`. Every stored incident record carries the version that produced its score. Changing weights without bumping breaks audit traceability.

Run the comparison CLI before and after any scoring config change:

```bash
cd packages/evaluation-harness
npx ts-node src/compare-versions.ts \
  --baseline ../../services/prioritization-engine/config/scoring-rules.json \
  --revised  ./my-candidate-config.json
```

### Parser keyword additions
When adding keywords to `services/transcript-parser/src/keywords.ts`:
- Test that new keywords do not trigger on negated forms
- Run the full evaluation harness to check for regressions
- Add a fixture to `data/fixtures/sample-incidents.json` if the keyword covers a new scenario type

### Tests
New logic in packages and services should have corresponding tests in `__tests__/`. Tests must not mock the parser or scorer — use the real implementations with controlled inputs.

### TypeScript
- Strict mode is on. No `any` without a comment explaining why.
- Avoid `as` type assertions in production code paths.

---

## Pull request checklist

- [ ] Tests pass (`npm test`)
- [ ] TypeScript compiles cleanly (`npm run typecheck`)
- [ ] If schema changed: `SCHEMA_VERSION` bumped
- [ ] If scoring config changed: `scoring_version` bumped and comparison CLI run
- [ ] Evaluation harness passes with no regressions (`cd packages/evaluation-harness && npx ts-node src/cli.ts`)
- [ ] Change maps to interpretation, prioritization, or accountability

---

## Scope boundaries

The following are explicitly **not** in scope and contributions in these areas will not be merged:

- SIP/i3 call routing implementation
- Full ESInet infrastructure
- Production telephony or audio transcription
- Autonomous dispatch logic (the system must remain human-in-the-loop)
- Compliance certification claims

See [docs/standards-alignment/ng911-alignment.md](docs/standards-alignment/ng911-alignment.md).

# Archive: TypeScript-era documents

These documents describe the original TypeScript backend (weighted scorer,
scoring rulesets 0.2.0/0.3.0, Express API), which was retired in favour of the
Python backend (DDL-012). They are kept unchanged as a record of how the
project evolved and are **not** a description of the current system.

| Document | Superseded by |
|---|---|
| `benchmark-report-v0.2.0.md` | `docs/evaluation/results/` (curated, generated and ML comparison reports) |
| `evaluation-plan.md` | `docs/evaluation/labelling-guide.md`, `data/eval/README.md`, design v1.2 §3A.8 and §10 |
| `replay-workflow.md` | Replay runs (`POST /v1/replay-runs`, dashboard Replay tab) and `docs/architecture/system-overview.md` |
| `reason-code-taxonomy.md` | Versioned rulesets in `backend/src/ntip/triage/rulesets/` and DDL-013 |

# Threat model

Scope: the research platform as deployed by `infra/docker/docker-compose.yml`
on a developer machine or isolated lab, holding synthetic data only (design
v1.2, §13.1). It is not hardened for, and must not be connected to, any live
emergency system.

## Assets

Stored source events and incidents, assessments and reviews, the audit trail,
evaluation integrity (datasets, rulesets, reports), interop credentials, and
the B2 API credential when B2 is enabled.

## Threats and controls

| Threat | Control in place | Gap / next step |
|---|---|---|
| Malicious or oversized input, request floods | Pydantic validation with `extra="forbid"`; transcript ≤ 20,000 chars; interop payload ≤ 512 KB; EIDO schema validation and quarantine; per-client rate limit (default 600/min, 429 with `Retry-After`) | The rate limit is per process; a multi-process deployment needs a shared counter |
| Prompt injection via transcripts | Rules only extract; B2 treats the transcript as delimited data, output is schema-constrained and every claim must quote the source exactly | Model-side behaviour cannot be proven; mitigated by verification and human review |
| Model-output laundering (an unsupported claim presented as fact) | Span verification rejects ungrounded candidates; model observations are marked `model`; a serious model-only cue needs human confirmation | — |
| Log or error leakage of transcripts | Errors never echo submitted values or stack traces; correlation ids instead. Logs are JSON written by this code base: requests are logged by route template, and exceptions by type only, so transcript text never reaches them (`tests/api/test_observability.py`) | Third-party libraries could still log input if configured to debug level |
| Unauthorised access | `/v1`: bearer tokens with roles (viewer, operator, analyst, admin), constant-time comparison; the server refuses to start without tokens unless authentication is explicitly disabled; reviews and replays are attributed to the token's principal. Interop: per-tenant tokens, fail closed, tenant-scoped receipts. Tenants: every incident and replay run belongs to one tenant; other tenants get 404, as for a missing incident (DDL-017) | Static tokens only (no expiry, rotation or SSO) |
| Audit tampering | Append-only store; PostgreSQL triggers reject UPDATE/DELETE/TRUNCATE; digests on records and audit events; the API connects as a restricted role (`ntip_app`: SELECT and INSERT only, owns nothing, so it cannot remove the triggers), checked in tests and in the container smoke test | The table owner or a superuser can still drop triggers; keep those credentials out of the application. Lawful erasure (owner only) removes rows by design and leaves a tombstone (DDL-019) |
| Evaluation tampering | Datasets, rulesets and the EIDO schema are pinned by sha256; reports record commit and digests | — |
| Supply chain | Locked dependencies (`uv.lock`, `package-lock.json`); third-party schema fetched only from a pinned commit and verified; CI runs pip-audit and npm audit on every change | Scans cover known advisories only |
| Data sent to a third party | B2 is off unless `NTIP_B2_ALLOW_EXTERNAL=1`; only synthetic data exists | Real data would need authorisation, privacy review and contracts (§3B.6) |
| Inadvertent connection to real systems | No telephony, routing or dispatch code exists; interop is import-only with no writeback; simulation banner in the UI; the deployment mode is explicit (`NTIP_DEPLOYMENT_MODE` accepts only `simulation`, anything else refuses to start) and stated on every API response (`X-NTIP-Mode`), in liveness and in metrics | — |
| Secrets in the repository | Defaults are local-development values; `.env` is git-ignored; CI runs gitleaks over the full history | — |

## Privacy and retention (§9.3)

Only synthetic data is accepted (`synthetic: true` is mandatory).

Audit immutability does not override lawful deletion (DDL-019). The
application can only append. Erasure is a separate, owner-run procedure
(`python -m ntip.store.retention`):
- It selects by incident or by a retention period, optionally per tenant, and
  only reports unless told to execute.
- It removes an incident with everything derived from it and its EIDO payloads,
  in one transaction under the incident's lock.
- It leaves a content-free tombstone (what, when, by whom, why) in an
  append-only `erasures` table.

Deletion is possible only inside a transaction that has set
`ntip.erasure_id`, and the application role has no DELETE privilege at all.

No retention period is configured by default, because the data is
synthetic. A deployment holding any authorised real data must set one and
schedule the procedure, after its own privacy and legal review (§9.3).

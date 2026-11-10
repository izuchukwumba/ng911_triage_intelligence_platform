# Stream replay (7 messages, ruleset `research-1.1.0`, engine `1.2.0`)

> Synthetic messages on a simulated clock. Advisory output for research only.

| t | Incident | Priority | Band | Queue after (most urgent first) |
|---|---|---|---|---|
| 00:00 | A | P2 | elevated | A |
| 00:20 | B | P2 | elevated | A > B |
| 00:45 | A | P0 | critical | A > B |
| 01:00 | C | P2 | undetermined | A > B > C |
| 01:30 | B | P0 | critical | A > B > C |
| 02:10 | D | P1 | high | A > B > D > C |
| 02:30 | C | P4 | low | A > B > D > C |

| Incident | Time to P0 |
|---|---|
| A | 00:45 |
| B | 01:10 |
| C | never |
| D | never |

## Candidate `research-1.0.0` vs `research-1.1.0`

> Illustrative difference only; not a validated improvement.

| Step | t | Incident | Baseline | Candidate | Lowers |
|---|---|---|---|---|---|
| 2 | 00:20 | B | P2 | P3 | **yes** |

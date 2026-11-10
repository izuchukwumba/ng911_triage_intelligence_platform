# Review: Texas A&M `ng911-dev` and this platform

Design v1.2 (§3B, Phase IV) asks whether the platform can be exercised with
Texas A&M's NG9-1-1 conformance and interoperability test tooling. This note
records what that tooling covers and what follows for this platform.

Reviewed: 2026-11-10, [tamu-edu/ng911-dev](https://github.com/tamu-edu/ng911-dev)
at commit `73ba4f279378d3083a566e228f32ddc28345be67` (2026-10-12), MIT licence,
maintained by the Texas A&M Center for Applied Communications and Networks
(CACN). Nothing from it is copied into this repository.

## What it tests

Conformance of NG9-1-1 i3 **functional elements**, mostly by replaying SIP and
HTTP exchanges (SIPp scenarios, packet captures) against an implementation
under test. Test descriptions by element:

| Element | Test descriptions |
|---|---|
| Border Control Function (BCF) | 14 |
| Bridging (BRIDGE) | 7 |
| Call Handling Functional Element (CHFE) | 20 |
| Emergency Call Routing / Location Validation (ECRF-LVF) | 13 |
| Emergency Services Routing Proxy (ESRP) | 21 |
| Location Information Server (LIS) | 5 |
| Logging Service (LOG) | 12 |
| Policy Store (PS) | 11 |
| Interoperability (INTEROP) | 1 |

## Where EIDO appears

Only as **logging-service event types**. `TD_LOG_004` checks that a NENA
Logging Service answers `GET /LogEvents` for event types including
`EidoLogEvent`. The suite's log-event checks also define the dereference-factory
query and response, denied and transmission-error EIDO log events. The suite
has no tests of:
- EIDO payload validity against NENA-STA-021;
- NENA-STA-024 conveyance (WebSocket subscribe/notify, or dereference by
  reference);
- any consumer of EIDOs.

## What follows for this platform

- **No test in the suite applies to this platform.** It is not an i3
  functional element: no SIP, no call routing, no ESInet interface and no
  NENA Logging Service. It is an import-only, advisory consumer of EIDOs
  ([NG911 alignment](ng911-alignment.md)). Running the suite against it
  would test nothing it implements.
- What this platform implements in this area is covered by its own
  verification matrix ([interop verification](interop-verification.md)):
  EIDO validation against NENA's pinned schema, the INT-001 to INT-012 import
  tests, and the NENA-STA-024 subscriber tests.
- A possible future link: if the platform ever wrote to a NENA Logging Service,
  its EIDO receipts could be emitted as `EidoLogEvent`s, and `ng911-dev`'s
  logging checks would then become relevant. This is not planned; the
  platform writes nothing back to external systems (ADR-INT-002).

No claim is made of passing, or having run, any `ng911-dev` test.

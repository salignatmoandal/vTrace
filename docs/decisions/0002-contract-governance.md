# Decision 0002 — Public contract governance

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related specs:** [spec 0001](../specs/0001-system-overview.md), [spec 0003](../specs/0003-event-schema.md), [spec 0004](../specs/0004-clock-and-metrics.md), [spec 0006](../specs/0006-lifecycle-and-cancellation.md)
- **Replaces:** —

## Context

vTrace is an observation tool: its consumers (CLI, tests, future
dashboard and OTel export) depend on the stability of the trace
contract. If the contract drifts implicitly in the code, consumers break
without notice.

## Decision

Any change to a public contract — event model, metric catalog, clock
semantics, lifecycle states, export format — goes through a spec update
then a decision record. Code does not get ahead of the contract.

## Consequences

Contract changes are traceable and enforceable. The cost is a
spec/decision cycle for every contract evolution; acceptable for a tool
whose value is contract reliability.

## Alternatives

- **Implicit contract in the code.** Rejected: silent drift, unannounced
  breakage.
- **Contract versioned by semver only.** Rejected as the sole mechanism:
  a version number does not describe the semantics of the change.

## Related specs

spec 0001 (overview), spec 0003 (events), spec 0004 (clock/metrics),
spec 0006 (lifecycle).

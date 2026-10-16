# Decision 0003 — MVP scope

- **Status:** Proposed
- **Date:** 2026-10-16
- **Related specs:** [spec 0009](../specs/0009-mvp-and-roadmap.md), [spec 0001](../specs/0001-system-overview.md)
- **Replaces:** —

## Context

An MVP that tries to do everything (dashboard, OTel, critical path,
benchmark) validates nothing. vTrace must first prove it reconstructs a
faithful timeline for one turn.

## Decision

The MVP is: one turn, a faithful timeline, a JSON export, a CLI report.
Out of scope: cloud, authentication, multi-tenant, dashboard,
OpenTelemetry export, leaderboard, automated recommendations,
distributed critical path.

## Consequences

The P1 slice is small and demonstrable. Critical path, benchmark, and
dashboard come later, each on an already-validated contract.

## Alternatives

- **Broad MVP including the dashboard.** Rejected: the dashboard is a
  consumer of the trace document; building it before the document
  inverts the dependency.
- **MVP including the critical path.** Rejected: critical path requires
  causal edges, which require an already-proven event model.

## Related specs

spec 0009 (MVP and roadmap), spec 0001 (overview).

# Decision 0005 — No inferred causality by proximity

- **Status:** Proposed
- **Date:** 2026-10-16
- **Related specs:** [spec 0003](../specs/0003-event-schema.md), [spec 0006](../specs/0006-lifecycle-and-cancellation.md), [spec 0007](../specs/0007-causal-graph.md)
- **Replaces:** —

## Context

In a concurrent pipeline, two events close in time are not necessarily
causal. Inferring a dependency from temporal proximity produces a
plausible but false critical path.

## Decision

No causal edge is inferred from timestamp proximity. Only explicit
edges count: `parent_id`, `queued`/`started` pair, cancellation pair. If
the information is insufficient, the analyzer reports an incomplete
result rather than fabricating a path.

## Consequences

The critical path (P4) will be conservative and credible. The cost is a
sometimes `unavailable` path; that is preferable to a false path.

## Alternatives

- **Heuristic inference by time window.** Rejected: plausible but
  unverifiable.
- **Inference with a confidence score.** Rejected for the MVP:
  confidence masks the absence of evidence.

## Related specs

spec 0003 (event schema; `sequence_number` is not causality), spec 0006
(explicit cancellation), spec 0007 (causal graph).

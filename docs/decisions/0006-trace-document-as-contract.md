# Decision 0006 — The trace document is the contract

- **Status:** Proposed
- **Date:** 2026-10-16
- **Related specs:** [spec 0001](../specs/0001-system-overview.md), [spec 0003](../specs/0003-event-schema.md)
- **Replaces:** —

## Context

vTrace has several consumers: CLI, tests, future dashboard, future OTel
export. If each depends on internal collector objects, any internal
change breaks everything. The stable contract must be the exported
document, not the implementation.

## Decision

The trace document (JSON, validatable against
[`docs/schema/trace.schema.json`](../schema/trace.schema.json)) is the
contract between the collector, the CLI, and future consumers. The
dashboard and OTel export will be consumers of this document, not
sources of truth.

## Consequences

The collector can change language or internal representation (decision
0001) without breaking consumers. The dashboard never becomes a
dependency of profiling.

## Alternatives

- **Python API as the contract.** Rejected: ties consumers to the live
  Python object.
- **Proprietary binary format.** Rejected for the MVP: readability and
  validatability take precedence.

## Related specs

spec 0001 (overview), spec 0003 (event schema).

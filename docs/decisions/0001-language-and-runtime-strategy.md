# Decision 0001 — Language and runtime strategy (Rust core at P1)

- **Status:** Proposed
- **Date:** 2026-10-16
- **Related specs:** [spec 0001](../specs/0001-system-overview.md), [spec 0005](../specs/0005-collector-and-concurrency.md)
- **Replaces:** former ADR-0003 (Python-first runtime, Rust deferred) — superseded
- **Supersedes:** —

## Context

The brief's initial hypothesis was a hybrid Rust/Python implementation.
An earlier decision (former ADR-0003, "Python-first runtime, Rust
deferred") argued that the critical path of a voice turn is STT, LLM,
and TTS — not a handful of profiling events — and that introducing Rust
from the first commit would cost PyO3, maturin, timestamp semantics at
the FFI boundary, and dual tooling, with no measured benefit. It
deferred any Cargo workspace until a benchmark (P4) or a second
language justified a Rust core.

That decision has been re-evaluated. The user has decided to accept the
tooling cost of a hybrid Rust/Python implementation from P1, to get a
single strongly-typed core from the start, with Python as the adapter
and CLI layer. The rejected alternative (Rust core from the first
commit) is now adopted, behind the existing trace-document contract.

## Decision

Adopt a Rust core (`vtrace-core`) at P1, behind the existing
trace-document contract (decision 0006). Add `vtrace-python` (PyO3)
bindings and a Python adapter/CLI layer. Keep the trace document as the
contract. Enforce layering with `cargo xtask layers` and correctness
with `cargo xtask ci`, both behind a single `just ci` entry point.

The future boundary, if it evolves: `vtrace-core` (schema, clock,
buffer, validator), `vtrace-analysis`, `vtrace-python`. These crates
exist as skeletons today; production logic is gated on P0 acceptance.

## Consequences

One strongly-typed core from P1; the contract has one implementation,
not two. The collector can change internally without breaking
consumers, because the trace document is the contract (decision 0006).

Cost: PyO3/maturin tooling and FFI timestamp discipline from P1.
Mitigated by: `i64` ns + `clock_domain` string at the boundary, the
per-crate `#![deny]` lint wall, and the single `just ci` gate. The risk
of unmeasured overhead remains; it will be measured in P5, not assumed
(invariant: no performance claim without a benchmark executed).

## Alternatives

- **Python-first, Rust deferred** (former ADR-0003). Superseded by this
  decision. Kept as history: it was correct for an empty repo with no
  measured benefit, and was superseded once the user accepted the
  tooling cost for a single strongly-typed core.
- **Rust only, no Python.** Rejected: Python is the better user-facing
  and Hugging Face integration surface.
- **Two independent implementations.** Rejected: breaks the
  single-contract guarantee (decision 0006).

## Related specs

spec 0001 (system overview), spec 0005 (collector and concurrency).

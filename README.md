# vTrace

Performance profiling for real-time Voice AI. vTrace reconstructs the
timeline of a voice turn and shows where time is spent: compute, queue
wait, streaming overlap, cancellation propagation. It does not replace
STT, LLM, or TTS; it is a specialized observation layer for real-time
voice runtimes.

## Status

P0 contracts are **Accepted**. Implementation has reached **P4**
(causal analysis). See [`docs/roadmap.md`](docs/roadmap.md) and
[`docs/phases/`](docs/phases/) for the academic phase notes (P1–P6).

## Documentation

- [`docs/specs/`](docs/specs/) — Specifications: enforceable design
  decisions and contracts.
- [`docs/decisions/`](docs/decisions/) — Decision records: accepted
  architectural decisions.
- [`docs/roadmap.md`](docs/roadmap.md) — Roadmap P0 through P7.
- [`docs/phases/`](docs/phases/) — Academic notes for phases P1–P6
  (problem, definition, literature, deliverable).
- [`docs/schema/trace.schema.json`](docs/schema/trace.schema.json) —
  Machine-readable trace document contract.
- [`AGENTS.md`](AGENTS.md) — Permanent invariants for agents.

## Repository layout

```
vTrace/
├── crates/          ← Rust workspace (core, analysis, python bindings)
├── py-vtrace/        ← Python package (adapters, CLI, validator, tests)
│   ├── src/vtrace/
│   └── tests/
├── fixtures/         ← shared deterministic trace fixtures
├── docs/             ← specs, decisions, roadmap, schema
└── xtask/            ← repository gates (cargo xtask ci)
```

## Philosophy

Prefer correctness, observability, reproducibility, and developer
experience over premature optimization. No performance claim is made
without an executed benchmark. Every contract decision is a proposal
until explicitly validated.

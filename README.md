# vTrace

Performance profiling for real-time Voice AI.

vTrace reconstructs the timeline of a voice turn and shows where time
is spent: compute, queue wait, streaming overlap, cancellation, and
explicit causal paths. It does not replace STT, LLM, or TTS — it is a
specialized observation layer for real-time voice runtimes.

## Status

| Phase | Goal | Status |
|---|---|---|
| P0 | Architecture and contracts | **Accepted** |
| P1 | Minimal trace reconstruction | Done |
| P2 | Streaming and queues (multi-producer) | Done |
| P3 | Lifecycle reliability | Done |
| P4 | Causal analysis (critical paths) | Done |
| P5 | Benchmarking and overhead | Upcoming |
| P6 | Hugging Face speech-to-speech hooks | Adapters-first bridge + fixture; upstream pending |
| P7 | Developer experience (dashboard / OTel) | Later |

No overhead or latency claim is published before **P5**. Current demos
use fixtures, a mock pipeline, and a model-free s2s-shaped interrupt
turn (`just report-s2s`). Live hooks inside Hugging Face
`speech-to-speech` are still pending.

## What it measures

From a validatable JSON **trace document**:

- **Compute** — stage durations from explicit event pairs
  (`started` → `completed` / `first_token` / `first_audio`, …)
- **Queue / handoff** — wait between `queued` and `started` when hooks
  exist
- **Overlap** — concurrent stage intervals (streaming)
- **Lifecycle anomalies** — orphans, double terminals, inconsistent
  cancels
- **Critical paths** — root→leaf chains on a DAG of *explicit* edges
  only (`parent_id`, lifecycle, queue pairs, cancel pairs). No edge
  inferred from timestamp proximity.

By default it does **not** collect raw audio, transcripts, prompts, or
model responses.

## Architecture

```
Voice pipeline ──record()──► Collector (bounded) ──► Trace document (JSON)
                                                         │
                    ┌────────────────────────────────────┤
                    ▼                                    ▼
              vtrace report                    future consumers
         (compute / queue /                   (OTel export, UI)
          overlap / lifecycle /
          critical paths)
```

| Layer | Crate / package | Role |
|---|---|---|
| L0 | `vtrace-core` | Schema, clock, bounded collector |
| L1 | `vtrace-analysis` | Causal DAG, critical-path extraction |
| L2 | `vtrace-python` + `py-vtrace` | PyO3 bindings, adapters, CLI |

The **trace document** is the contract between collector, CLI, and
consumers — not internal objects.

## Quick start

Prerequisites: Rust toolchain, [`uv`](https://github.com/astral-sh/uv),
[`just`](https://github.com/casey/just).

```bash
# Build native extension + install the Python package (dev)
cd py-vtrace && uv sync && uv run maturin develop

# Report on the acceptance fixture
just report
# or: cd py-vtrace && uv run vtrace report ../fixtures/traces/one-turn.json

# P6: #714-shaped interrupt turn (s2s bridge, model-free)
just report-s2s

# Full gate (Rust + Python + schema)
just ci
```

See [`docs/integrations/speech-to-speech.md`](docs/integrations/speech-to-speech.md)
for the HF hook map.

## Repository layout

```
vTrace/
├── crates/
│   ├── vtrace-core/       # L0 — events, clock, collector
│   ├── vtrace-analysis/   # L1 — causal graph, critical paths
│   └── vtrace-python/     # L2 — PyO3 (_vtrace)
├── py-vtrace/             # Python package (adapters, CLI, tests)
├── fixtures/traces/       # Deterministic acceptance fixtures
├── docs/
│   ├── specs/             # Enforceable contracts (0001–0009)
│   ├── decisions/         # Accepted architectural decisions
│   ├── phases/            # Academic notes P1–P6
│   ├── schema/            # trace.schema.json
│   └── roadmap.md
├── xtask/                 # cargo xtask ci / layers / docgen
└── AGENTS.md              # Invariants for human and AI agents
```

## Documentation

- [`docs/roadmap.md`](docs/roadmap.md) — Phases P0–P7
- [`docs/phases/`](docs/phases/) — Academic notes (problem, literature,
  deliverable) for P1–P6
- [`docs/specs/`](docs/specs/) — Specifications
- [`docs/decisions/`](docs/decisions/) — Decision records
- [`docs/schema/trace.schema.json`](docs/schema/trace.schema.json) —
  Machine-readable document contract
- [`AGENTS.md`](AGENTS.md) — Permanent engineering invariants

## Philosophy

Correctness and observability first; no silent loss of critical
events; no invented causality; no performance claim without an
executed benchmark. Contracts are proposed until Accepted — code does
not get ahead of the specs.

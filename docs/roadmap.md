# vTrace — Roadmap

- **Last reviewed:** 2026-10-16 · **Last updated:** 2026-10-16 · **Change:** P6 adapters-first slice (`vtrace.integrations.s2s`, #714-shaped fixture, integration doc). Next: wire live s2s hooks or P5.

Incremental phasing. Each phase has a goal, tasks, dependencies,
acceptance criteria, risks, and a demonstrable deliverable. The
authoritative phase definitions live in
[`docs/specs/0009-mvp-and-roadmap.md`](specs/0009-mvp-and-roadmap.md);
this file is the one-page summary.

No phase produces performance numbers before **P5**. Earlier phases
establish correctness and reproducibility.

## P0 — Architecture and contracts

- **Goal.** Fix the contracts (events, clock, lifecycle, export) before
  any production code.
- **Tasks.** Specs 0001–0009, decisions 0001–0006, JSON schema, agent
  templates, AGENTS.md.
- **Dependencies.** None.
- **Acceptance criteria.** A reviewer can implement the collector and
  the export without reinventing the schema. Illegal transitions and
  silent losses are explicitly named in the specs.
- **Risks.** Premature over-specification. Mitigation: `Proposed`
  status, amendable.
- **Demonstrable deliverable.** This `docs/` folder.

## P1 — Minimal trace reconstruction

- **Goal.** Reconstruct a faithful timeline of one voice turn and export
  it, with a Rust core behind the same trace document (decision 0001).
- **Tasks.**
  1. Rust core (`vtrace-core`): schema, clock, bounded collector,
     lifecycle validation, document assembly — behind the contract of
     specs 0003/0004/0006.
  2. `cargo xtask ci` + `cargo xtask layers` gates; per-crate
     `#![deny]` lint wall; `unsafe_code = "forbid"`.
  3. PyO3 bindings (`vtrace-python`): expose `Clock` and `record()` to
     Python; Python adapters and CLI consume the bindings.
  4. Schema validation of the trace document; manual clock; domain
     tests.
  5. Turn context, spans, JSON export, text CLI report on a
     model-free fixture.
- **Dependencies.** P0 accepted.
- **Acceptance criteria.** A replayable fixture produces a
  deterministic trace. The CLI report distinguishes compute, queue, and
  overlap. Loss of a critical event is visible in the export.
  `cargo xtask layers` is green (no upward dep, no UI crate below the
  UI layer).
- **Risks.** Conflating `tts.first_audio` and playback start.
  Mitigation: metrics named by explicit event pairs, distinct (spec
  0004). FFI timestamp semantics. Mitigation: `i64` ns + `clock_domain`
  string, never a raw `Instant` across the FFI (spec 0001).
- **Demonstrable deliverable.** `vtrace report` on a fixture trace, with
  the Rust collector behind it. This is the smallest publishable
  version.

## P2 — Streaming and queues

- **Goal.** Measure handoffs, buffering, and overlapping stages.
- **Tasks.** Concurrent producers, buffer saturation, queue-wait
  timestamps, streaming-overlap timeline.
- **Dependencies.** P1.
- **Acceptance criteria.** Deterministic concurrency tests (fixed
  seed). `completeness` reflects any loss. No orphaned task after
  shutdown.
- **Risks.** Test non-determinism. Mitigation: manual clock and
  controlled scheduling.
- **Demonstrable deliverable.** Green concurrency test suite.

## P3 — Lifecycle reliability

- **Goal.** Track cancellation, failures, and cleanup.
- **Tasks.** Cancellation during generation, late events, duplicate
  terminals, clean shutdown, resource cleanup.
- **Dependencies.** P2.
- **Acceptance criteria.** State transitions validated; no illegal
  transition accepted; cancellation requested ≠ cancellation
  completed.
- **Risks.** Orphaned tasks. Mitigation: structured-concurrency
  ownership (spec 0006).
- **Demonstrable deliverable.** Lifecycle-validated trace.

## P4 — Causal analysis

- **Goal.** Identify the dependencies that determine the observed
  latency, per objective.
- **Tasks.** Explicit dependency graph, paths for TTFT, TTFA,
  first-audible, turn completion, uncertainty report when edges are
  missing.
- **Dependencies.** P2, P3.
- **Acceptance criteria.** The critical path invents no edge (decision
  0005). Distinct objectives yield distinct paths.
- **Risks.** Causal inference by proximity. Mitigation: decision 0005,
  explicit edges only.
- **Demonstrable deliverable.** Critical path report on a
  reconstructed trace.

## P5 — Benchmarking and overhead

- **Goal.** Measure overhead and regressions reproducibly.
- **Tasks.** Baseline vs candidate, repetitions, hardware/software
  metadata, separation of profiler overhead / model variability.
- **Dependencies.** P1, P2.
- **Acceptance criteria.** Variance documented. No published number
  without a protocol and repetitions (spec 0008).
- **Risks.** Measurement noise on Apple Silicon (MPS, warmup, CPU
  load). Mitigation: explicit warmup, repetitions, median and
  percentiles.
- **Demonstrable deliverable.** Baseline vs candidate comparison
  report.

## P6 — Hugging Face integration

- **Goal.** Demonstrate value in `huggingface/speech-to-speech`.
- **Tasks.** Audit existing code, identify instrumentation points,
  minimal non-invasive upstream PR.
- **Dependencies.** P1, P2, ideally P4.
- **Acceptance criteria.** No claim about current instrumentation
  before reading the code. Instrumentation toggleable on and off.
- **Risks.** Dependence on volatile internal details. Mitigation:
  instrumentation on stable points, small PR.
- **Demonstrable deliverable.** Trace of a real turn via the
  integration.

## P7 — Developer experience

- **Goal.** CLI, local visualization, optional Hugging Face Space.
- **Tasks.** Local dashboard (consumers of the trace document),
  optional OTel export, optional HF Space.
- **Dependencies.** P4, P6.
- **Acceptance criteria.** The core remains usable without the
  dashboard. The dashboard is not a source of truth (decision 0006).
- **Risks.** Making the dashboard a dependency of profiling.
  Mitigation: decision 0006.
- **Demonstrable deliverable.** Local dashboard reading a trace
  document.

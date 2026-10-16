# vTrace Specification 0008 — Testing and Benchmarks

- **Status:** Accepted
- **Date:** 2026-10-16
- **Depends on:** all other specs

## 1. Purpose

Define the test layers and the benchmark protocol so every acceptance
criterion maps to an executable test or benchmark, and every
performance claim references reproducible measurements.

## 2. Problem statement

A profiler's value is only as good as its own correctness and its
measured overhead. Without deterministic tests, concurrency coverage,
and a reproducible benchmark protocol, claims are anecdotes. Mean
latency hides tails.

## 3. Key concepts

- **Deterministic test**: manual clock, fixed fixture.
- **Property test**: generated input sequences preserving invariants.
- **Concurrency test**: fixed seed, controlled scheduling.
- **Performance test**: baseline vs candidate, repeated.
- **Percentiles**: p50, p95, p99; mean is insufficient.

## 4. Functional requirements

- Every spec invariant MUST map to at least one executable test.
- Unit tests MUST cover clock arithmetic, event validation, identity,
  state transitions, serialization.
- Property tests MUST cover event ordering, valid transitions, and
  invariant preservation across generated sequences.
- Concurrency tests MUST cover concurrent producers, saturation,
  races, shutdown, and cancellation propagation.
- Integration tests MUST run a full pipeline with deterministic mock
  STT/LLM/TTS components.
- Performance tests MUST measure collector overhead, allocation
  pressure, throughput, p95 latency impact, and memory bounds.
- Compatibility tests MUST cover schema evolution and the
  Rust/Python interface contract.

## 5. Non-functional requirements

- Tests MUST be deterministic by default (manual clock, fixed seed).
- Performance tests MUST NOT run in the default `ci` gate; they run in
  a separate `bench` target.

## 6. Technical design

### Test layers

| Layer | What | Tool | Determinism |
|---|---|---|---|
| Unit | schema, clock, lifecycle, serialization | Rust `#[test]`, pytest | manual clock |
| Property | ordering, transitions, invariants | `proptest` | seeded |
| Concurrency | producers, saturation, shutdown, cancel | Rust `#[test]` + harness | fixed seed |
| Integration | full mock pipeline | pytest + fixture | manual clock |
| Performance | overhead, p95, memory | `cargo bench` / criterion | repeated |
| Compatibility | schema version, FFI contract | Rust + pytest | fixed |

### Benchmark protocol (P5)

- **Baseline**: pipeline without vTrace. **Candidate**: same pipeline
  with vTrace enabled.
- **Warmup**: explicit, discarded runs; not counted.
- **Repetitions**: a fixed count; results are p50/p95/p99, not single
  runs.
- **Hardware/software metadata**: recorded (CPU, MPS, OS, model
  revision, backend).
- **Separation**: profiler overhead vs model variability MUST be
  reported separately.
- **Raw results**: preserved; statistical reporting only.
- **Acceptance threshold**: none until variance is characterized; a
  threshold, if set, MUST be a decision.

### Overhead methodology

`instrumentation_overhead_ns` is measured as the added cost of
`record()` per event, baseline vs candidate, repeated. vTrace MUST NOT
assume Rust eliminates overhead; the cost MUST be measured.

## 7. Contracts and data structures

Benchmark results are a separate artifact, NOT part of the trace
document. A benchmark report includes: hardware/software metadata,
repetition count, p50/p95/p99, and the raw-result path.

## 8. Invariants

- Every performance claim references reproducible measurements.
- No benchmark number is published without a protocol and
  repetitions.
- Profiler overhead and model variability are reported separately.

## 9. Failure modes

- Single-run latency treated as a result: mitigation, repetitions +
  percentiles.
- Warmup counted: mitigation, explicit discarded warmup.
- MPS contention noise: mitigation, warmup, repeated runs, documented
  load.
- Overhead attributed to the model: mitigation, baseline vs candidate
  isolation.

## 10. Test and acceptance criteria

- `cargo xtask ci` is green (fmt, clippy, test, layers, validate).
- `uv run pytest` is green.
- A concurrency test with a fixed seed is reproducible across runs.
- A benchmark report has metadata, repetitions, and percentiles.

## 11. Alternatives considered

- **Single-run benchmarks**: rejected — hides tails and noise.
- **CI-enforced performance threshold from day one**: rejected —
  variance must be characterized first.

## 12. Open questions

- Which benchmark harness (criterion)? Suggested: criterion when Rust
  perf tests land at P5.
- Should performance tests run in CI or nightly? Suggested: nightly,
  not on every PR.

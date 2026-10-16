# P5 — Benchmarking and Overhead

- **Status (implementation):** Upcoming (not started)
- **Depends on:** P1–P4 (stable contracts)
- **Specs:** 0008 (performance evaluation)
- **Decisions:** AGENTS.md invariant 6 (no claim without an executed
  benchmark)

## 1. Scientific problem

An observability tool that **perturbs** the system it measures is
self-defeating: reported latencies become artifacts of the profiler.
In interactive voice pipelines, budgets are often on the order of
hundreds of milliseconds end-to-end ([Chen et al., 2026,
arXiv:2601.11141](https://arxiv.org/abs/2601.11141); [Purwar &
Choudhary, 2025, arXiv:2509.20971](https://arxiv.org/abs/2509.20971)).
An overhead of a few milliseconds *per event* can therefore be
material.

Moreover, **mean** latency hides the *tail* that users experience.
Service profiling must target percentiles (p50 / p95 / p99), not the
average alone ([Wodislawski & Morrison, 2026,
arXiv:2610.04615](https://arxiv.org/abs/2610.04615) — *PonyTail*).

## 2. Operational definition

**P5** is the phase that **measures**, under a reproducible protocol:

1. **Profiler overhead** — cost of `record()` / collector / export
   relative to an uninstrumented baseline;
2. **A/B comparison** — same workload with vs without vTrace (or
   between configurations);
3. **Percentile reporting** — p50, p95, p99 (and optionally higher),
   never a lone mean as the sole claim.

**P5 is not:** a marketing claim of “near-zero overhead” without
numbers; a micro-benchmark that does not represent a voice turn.

## 3. Foundations

### Tail latency

PonyTail argues for *profiling and improving* the service tail
([Wodislawski & Morrison, 2026](https://arxiv.org/abs/2610.04615)).
vTrace itself is a potential source of tail inflation if the collector
blocks or allocates on the hot path — hence the P1–P2 design
constraints, *validated* only in P5.

### RTF and voice components

i-LAVA decomposes RTF by stage ([Purwar & Choudhary,
2025](https://arxiv.org/abs/2509.20971)). P5 must therefore report
overhead **in the same units** (ns/event, ms/turn, Δp99) so results
are comparable to those breakdowns.

### Evidence-based completion

AGENTS.md: *no performance claim without an executed benchmark*. Until
P5 runs, any overhead figure is an **expectation**, not an
**observation**.

## 4. vTrace contracts

| Element | Role in P5 |
|---|---|
| Spec 0008 | Protocol, seeds, percentiles, A/B |
| Spec 0005 | Hot-path invariants to *verify*, not assume |
| Manual / monotonic clocks | Reproducibility of synthetic benches |

## 5. Method and deliverable (planned)

- Fixed-seed workloads (synthetic turns + optional mock pipeline).
- Criteria: `cargo bench` / Criterion (Rust) and/or Python harness.
- Artifact: table of percentiles + Δ vs baseline, attached to the
  task summary.
- **Deliverable:** executed numbers; reproducibility of the run
  (seed, command, environment).

## 6. Status and limits

Not implemented. Do not cite overhead percentages for vTrace until
this phase has produced measured evidence.

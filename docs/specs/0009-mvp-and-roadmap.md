# vTrace Specification 0009 — MVP and Roadmap

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related decisions:** [0003 (MVP scope)](../decisions/0003-mvp-scope.md), [0001 (runtime strategy)](../decisions/0001-language-and-runtime-strategy.md)
- **Supersedes (content):** `docs/roadmap.md` (folded here; the roadmap file is kept as the one-page summary)

## 1. Purpose

Define the MVP scope, the incremental roadmap P0–P7, and the smallest
publishable version.

## 2. Problem statement

An MVP that tries to do everything validates nothing. vTrace must first
prove it reconstructs one faithful timeline before adding streaming,
causal analysis, benchmarks, and integration.

## 3. Key concepts

- **MVP**: one complete voice turn reconstructed as an ordered event
  timeline, exported as JSON, with a CLI text report.
- **Smallest publishable version**: the P1 deliverable above.

## 4. Functional requirements (MVP)

1. A documented event schema (spec 0003).
2. Monotonic timestamp recording with domains (spec 0004).
3. Bounded event collection (spec 0005).
4. Turn-level correlation (spec 0006).
5. STT/LLM/TTS instrumentation adapters.
6. Basic queue-wait measurement where hooks exist.
7. Structured JSON export.
8. CLI timeline report.
9. Deterministic tests.
10. A reproducible example without a model.

## 5. Non-functional requirements (MVP)

- No cloud, no auth, no multi-tenant, no dashboard, no OTel, no
  leaderboard, no automated recommendations, no distributed critical
  path.

## 6. Technical design

### Roadmap

| Phase | Goal | Depends on | Deliverable | Non-goals |
|---|---|---|---|---|
| P0 | Specification and contracts | — | This `docs/specs/` set | Production code |
| P1 | Minimal trace reconstruction | P0 | One turn → timeline → JSON → CLI report | Causal graph, benchmarks |
| P2 | Streaming and queues | P1 | Handoff and overlap measurement | Critical path |
| P3 | Lifecycle reliability | P2 | Cancellation, failures, cleanup | Causal graph |
| P4 | Causal analysis | P2, P3 | Dependency graph + critical paths | Benchmarks |
| P5 | Benchmarking and overhead | P1, P2 | Baseline vs candidate, overhead | HF integration |
| P6 | Hugging Face integration | P1, P2, P4 | Trace of a real turn in `speech-to-speech` | Dashboard |
| P7 | Developer experience | P4, P6 | CLI, local visualization, optional HF Space | Cloud features |

### Smallest publishable version

The P1 deliverable: `vtrace report` on a fixture trace, with the Rust
collector behind it and the Python adapter in front. Nothing else
ships.

## 7. Contracts and data structures

Each phase's acceptance criteria map to tests in spec 0008. A phase is
done when its acceptance tests are green and evidence is attached
(AGENTS.md).

## 8. Invariants

- No production code before P0 is `Accepted`.
- No performance number before P5.
- The MVP MUST NOT include the dashboard, OTel, or causal analysis.

## 9. Failure modes

- MVP scope creep (adding the dashboard early): mitigation, the
  dashboard is a consumer of the document, built after the document.
- Causal analysis before the event model is proven: mitigation, P4
  after P1/P2.

## 10. Test and acceptance criteria

- P0: a reviewer can implement the collector from the specs without
  reinventing the schema.
- P1: a fixture produces a deterministic trace; the CLI report
  distinguishes compute, queue, and overlap.
- Each phase: `cargo xtask ci` green + phase-specific tests green.

## 11. Alternatives considered

- **Broad MVP (dashboard + OTel)**: rejected — inverts the dependency.
- **MVP with critical path**: rejected — needs proven event model
  first.

## 12. Open questions

- Does P6 instrument `speech-to-speech` via adapters or via a small
  upstream PR? Decidable after the P6 code audit.

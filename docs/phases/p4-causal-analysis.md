# P4 — Causal Analysis

- **Status (implementation):** Complete
- **Depends on:** P1–P3
- **Specs:** 0007 (critical path), 0003 (parent_id, pairs)
- **Decisions:** 0005 (no invented causality), 0006

## 1. Scientific problem

Optimizing a voice pipeline requires knowing **which chain of stages**
dominates wall-clock time for a given turn. Component-level scheduling
literature shows that end-to-end latency is often the composition of
heterogeneous components, with bottlenecks concentrated on *stragglers*
([Han et al., 2015, arXiv:1511.02960](https://arxiv.org/abs/1511.02960)).

The scientific risk is **false causality**: inferring “A caused B”
because timestamps are close. In concurrent systems, that inference is
logically invalid ([Crafa & Russo, 2013,
arXiv:1303.1384](https://arxiv.org/abs/1303.1384)).

## 2. Operational definition

**P4** builds a **causal DAG** whose vertices are events and whose
edges are *only*:

1. **Parent entry** — `parent_id` on a `*.started` or `*.queued`
   (entry into a child span);
2. **Same-span lifecycle** — `started` → intermediate → terminal;
3. **Queue pair** — `*.queued` → `*.started` (same family);
4. **Cancel pair** — `*.cancel_requested` → `*.cancelled`.

From that DAG, P4 extracts **distinct root→leaf paths**, each with a
duration and a confidence:

| `PathConfidence` | Meaning |
|---|---|
| `complete` | Continuous chain of explicit edges |
| `partial` | Path truncated; missing edges |
| `unavailable` | Missing endpoint or disconnected component |

**P4 is not:** inferring STT→LLM because STT ended “just before” LLM
started; ranking paths by statistical significance (out of scope).

## 3. Foundations

### Causality vs concurrency

Crafa & Russo formalize that *ex post* execution-trace analysis must
separate *causal* order from *concurrent* order. Decision 0005 is the
vTrace operationalization of that principle: *prefer an incomplete
result over a false one*.

### Critical path and latency composition

Predictive Component-level Scheduling (PCS) frames latency as a
composition of components ([Han et al., 2015](https://arxiv.org/abs/1511.02960)).
P4 exposes *observed* compositions; it does not schedule them.

### Parent semantics

Only `started` / `queued` carry an entry edge from the parent. A
terminal (`llm.completed`) with `parent_id=turn` does **not** create
`turn.started → llm.completed` — that would invent a leap over the
child’s lifecycle.

## 4. vTrace contracts

| Element | Role in P4 |
|---|---|
| Spec 0007 | Critical path API; confidence labels |
| Decision 0005 | Explicit edges only |
| `vtrace-analysis` (L1) | Rust DAG + path extraction |
| PyO3 `critical_paths` | Bridge to Python / CLI |

## 5. Method and deliverable

- Rust: `graph.rs`, `path.rs`; deny `unwrap` in production.
- Python: `causal.py` + *Critical path* report section.
- Acceptance tests: complete path; missing edge → `partial` /
  `unavailable`; no proximity edge.
- **Deliverable:** list of paths with duration and confidence; honest
  on fixtures without queue hooks.

## 6. Status and limits

Implemented. On a pipeline instrumented only with `started` /
`first_*` / `completed`, paths are often **partial** — that is
expected, not a bug. Full `complete` paths require `parent_id` and
queue hooks (P6).

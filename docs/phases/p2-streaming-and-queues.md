# P2 — Streaming and Queues

- **Status (implementation):** Complete (multi-producer collector)
- **Depends on:** P1
- **Specs:** 0002, 0005, 0008 (concurrency tests)
- **Decisions:** 0005 (no inference), 0006

## 1. Scientific problem

Modern voice pipelines are **concurrent**: VAD, STT, LLM, TTS, and
playback run on distinct threads, connected by queues. Real-time
*spoken dialogue* systems target sub-second end-to-end latency and
interleaved text–audio streaming ([Chen et al., 2026,
arXiv:2601.11141](https://arxiv.org/abs/2601.11141)). In that regime,
two phenomena dominate measurement error:

1. **Handoff / queue wait** — time between a producer’s completion and
   a consumer’s start;
2. **Overlap** — temporal overlap of stages (streaming), which makes
   naïve summation of durations incorrect.

A *single-producer* collector or an unbounded queue (as in some open
reference stacks) can neither guarantee concurrent safety nor make
saturation *observable*.

## 2. Operational definition

**P2** establishes that the collector:

1. accepts **multiple producers** without corrupting the document;
2. remains **bounded** (finite memory) and **non-blocking** on
   `record()`;
3. makes any loss visible (`dropped_*`, `completeness`);
4. exposes enough events to measure handoff and overlap *when hooks
   exist* (`*.queued`, started / first_* / completed pairs).

**P2 is not:** cancel semantics (P3), the critical path (P4), or
overhead measurement (P5).

## 3. Foundations

### Concurrency and queues

In multi-component systems, end-to-end service latency is often
dominated by a *straggler* or by queue composition ([Han et al., 2015,
arXiv:1511.02960](https://arxiv.org/abs/1511.02960)). P2 provides the
observation infrastructure for those queues *without* applying
backpressure to the pipeline (invariant: the profiler does not change
application semantics).

### Low-latency streaming

Streaming audio models document latencies on the order of tens to
hundreds of milliseconds ([Quamer & Gutierrez-Osuna, 2024,
arXiv:2406.09277](https://arxiv.org/abs/2406.09277)). At that scale, a
`record()` that blocks or allocates heavily on the hot path is
unacceptable (spec 0005).

### Visible loss

A *silent drop* policy hides lifecycle events. P2 requires: droppable
events rejected and counted; critical events evict a droppable if one
exists, otherwise `dropped_critical` and `completeness: partial`.

## 4. vTrace contracts

| Element | Role in P2 |
|---|---|
| Spec 0005 | Multi-producer, `try_push`, critical eviction, `shutdown` |
| Spec 0002 | STT/LLM/TTS/playback overlap as a measurement object |
| Spec 0003 | Optional `producer_id`; `sequence` *per producer* |
| Spec 0008 | Fixed-seed concurrency tests |

## 5. Method and deliverable

- Thread-safe collector (short `threading.Lock`; timestamp *before*
  the lock).
- Concurrency test suite (parallel producers, saturation, bounded
  shutdown).
- **Deliverable:** green concurrency suite; document remains
  validatable after multi-thread stress.

## 6. Status and limits

Implemented in the Python collector (P2 slice). `queue.*` events are
emitted *only* if the instrumented pipeline exposes hooks — P2
prepares the measurement; P6 activates it on a real pipeline.

# vTrace Specification 0005 — Collector and Concurrency

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related decisions:** [0006 (trace document as contract)](../decisions/0006-trace-document-as-contract.md)
- **Supersedes (content):** former RFC-0002 buffer policy, folded here
- **Depends on:** [0003 (event schema)](0003-event-schema.md), [0004 (clock)](0004-clock-and-metrics.md)

## 1. Purpose

Define the concurrent event ingestion model: bounded memory,
non-blocking recording, overflow behavior, loss reporting, and graceful
shutdown.

## 2. Problem statement

A voice pipeline has multiple concurrent producers (VAD, STT, LLM, TTS,
playback) on different threads. An unbounded collector grows without
limit; a silently dropping collector hides lost lifecycle events. The
reference (`huggingface/speech-to-speech`) uses unbounded
`queue.Queue` and has no overflow policy — vTrace MUST be bounded and
MUST report loss.

## 3. Key concepts

- **Producer**: a thread/task calling `record()`.
- **Bounded buffer**: fixed capacity; overflow is explicit.
- **Critical vs droppable**: critical events are never silently lost
  (spec 0003).
- **Backpressure**: the collector MUST NOT apply backpressure to the
  pipeline; it MUST drop or evict instead, to keep `record()` non-blocking.
- **Completeness**: `complete` | `partial`; `partial` when a critical
  event is lost.

## 4. Functional requirements

- `record()` MUST be synchronous and non-blocking: timestamp on the
  caller's thread, then `try_push`.
- The buffer MUST be bounded; memory MUST NOT grow unbounded.
- On overflow:
  - a droppable event MUST be rejected and `dropped_total` incremented;
  - a critical event MUST evict the oldest droppable event if one
    exists; otherwise `dropped_critical` incremented and
    `completeness: partial`.
- A critical event MUST NEVER be silently lost.
- `shutdown()` MUST drain pending events or mark the trace `partial`
  with the reason; it MUST NOT block forever.
- The collector MUST support multiple concurrent producers safely.

## 5. Non-functional requirements

- `record()` MUST NOT allocate heavily, take contended locks, or
  encode JSON on the caller's path.
- The collector MUST NOT be on the audio callback's hot path beyond a
  single `now_ns()` + `try_push`.

## 6. Technical design

### Ingestion

```
record(event):
    t = clock.now_ns()        # caller thread, before queue
    event.timestamp_ns = t
    if not buffer.try_push(event):
        if event is droppable:
            dropped_total += 1
        else:
            if buffer.evict_oldest_droppable():
                buffer.push(event)
            else:
                dropped_critical += 1
                completeness = partial
```

### Single vs multi-producer

Multi-producer is required (VAD, STT, LLM, TTS, playback are
concurrent). Each producer has its own `sequence` counter; `sequence`
breaks ties and detects reorderings, it does NOT impose a global order.

### Export

`export()` produces the flat JSON document (decision 0006). Export
failure (disk full, permission) MUST be reported to the caller and MUST
NOT corrupt the in-memory trace.

## 7. Contracts and data structures

Document header: `completeness`, `dropped_total`, `dropped_critical`,
`clock_domains`. See `trace.schema.json`.

## 8. Invariants

- Buffers are bounded.
- Critical-event loss is observable.
- `record()` does not block.
- The collector does not alter application semantics (invariant 1).

## 9. Failure modes

| Scenario | Expected behavior |
|---|---|
| Concurrent producers | safe; `sequence` per producer |
| Buffer saturation | droppable rejected; critical evicts or `partial` |
| Exporter unavailable | reported; trace intact in memory |
| Shutdown with pending events | drain or `partial` with reason |
| Clock-domain mismatch | timestamps keep their domain; cross-domain metric `unavailable` |

## 10. Test and acceptance criteria

- A saturated buffer rejects a droppable event and keeps a critical one.
- A lost critical event sets `completeness: partial` and
  `dropped_critical > 0`.
- Concurrent producers (fixed seed) produce a valid, ordered document.
- `shutdown()` terminates within a bounded time.

## 11. Alternatives considered

- **Unbounded queue (like the reference)**: rejected — unbounded
  memory, no loss reporting.
- **Backpressure on the pipeline**: rejected — would alter application
  semantics (invariant 1).
- **Sampling**: MAY be added later, but MUST NOT be the default for
  lifecycle events.

## 12. Open questions

- Default buffer size and critical-event quota? Policy fixed; numbers are
  parameters.
- Should `queue.*` events be emitted by default or only where hooks
  exist? Suggested: only where hooks exist.

# vTrace Specification 0003 — Event Schema

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related decisions:** [0005 (no inferred causality)](../decisions/0005-no-inferred-causality.md), [0006 (trace document as contract)](../decisions/0006-trace-document-as-contract.md), [0004 (privacy default)](../decisions/0004-privacy-default.md)
- **Supersedes (content):** former RFC-0002 (event model), folded here by migration
- **Machine-readable contract:** [`docs/schema/trace.schema.json`](../schema/trace.schema.json)

## 1. Purpose

Define the event schema: identity, fields, families, versioning, and the
effect of missing, duplicated, and reordered events on trace
reconstruction.

## 2. Problem statement

Without a stable event identity and ordering, two collectors or two
consumers diverge silently. The schema is the contract that prevents
that (decision 0006).

## 3. Key concepts

- **Event identity**: `event_id` is unique within a trace.
- **Ordering**: `(clock_domain, timestamp_ns, sequence)`. `sequence`
  breaks ties and detects reorderings; it is NOT causality.
- **Causality**: only `parent_id` and explicit pairs (`queued`/`started`,
  cancellation) are edges (decision 0005).
- **Event class**: critical-lifecycle (never silently dropped) vs
  droppable under pressure.

## 4. Functional requirements

- Every event MUST carry: `schema_version`, `event_id`, `trace_id`,
  `turn_id`, `span_id`, `component`, `name`, `timestamp_ns`,
  `clock_domain`, `sequence`.
- `generation_id`, `task_id`, `producer_id`, `correlation_id`,
  `parent_id`, `response_id`, `session_id`, `attributes` MAY be
  present and are optional unless stated.
- The collector MUST distinguish critical-lifecycle from droppable
  events (spec 0005).
- The document MUST validate against `trace.schema.json`.

## 5. Non-functional requirements

- `record()` MUST NOT encode JSON on the caller's path.
- Schema validation MUST be cheap enough for a test fixture; it is not
  on the hot path.

## 6. Technical design

### Field map (alias strategy)

The brief lists extra identity fields. They are added as **aliases** so
the existing schema is extended, not broken:

| Brief field | Status | Maps to / role |
|---|---|---|
| `trace_id` | **required** | alias of `session_id`; the trace identity |
| `session_id` | optional | retained; `trace_id` is canonical |
| `generation_id` | optional | alias of `response_id`; a distinct attempt in a turn |
| `task_id` | optional | alias of `span_id`; the task identity |
| `producer_id` | optional | paired with `sequence`; the producing thread/handler |
| `correlation_id` | optional | cross-system linking (attribute) |
| `parent_id` | optional | explicit parent; a causal edge |
| `event_type` | optional | alias of `name` (kept as `name` canonical) |

`trace_id` becomes required; all other additions are optional aliases.

### Event families

| Family | Component | Events |
|---|---|---|
| Audio capture | `audio` | `audio.frame` (droppable), `audio.started`, `audio.stopped` |
| VAD | `vad` | `vad.speech_started`, `vad.speech_ended` |
| STT | `stt` | `stt.queued`, `stt.started`, `stt.partial_result` (droppable), `stt.completed`, `stt.failed` |
| LLM | `llm` | `llm.queued`, `llm.started`, `llm.first_token`, `llm.completed`, `llm.failed` |
| TTS | `tts` | `tts.queued`, `tts.started`, `tts.first_audio`, `tts.completed`, `tts.failed` |
| Queue | `queue` | `queue.enqueued`, `queue.dequeued` (when hooks exist) |
| Playback | `playback` | `playback.buffered`, `playback.started`, `playback.completed` |
| Cancellation | `turn`/`*` | `cancel.requested`, `cancel.acknowledged`, `*.cancelled` |
| Errors | `*` | `*.failed`, `turn.timed_out` |
| Runtime lifecycle | `collector`/`turn` | `collector.started`, `collector.shutdown`, `collector.dropped_critical`, `turn.started`, `turn.completed`, `turn.failed`, `turn.cancelled` |

### Critical vs droppable

- **Critical** (never silently dropped): `turn.*`, `cancel.*`,
  `*.queued`/`*.started`/`*.completed`/`*.failed`/`*.cancelled`,
  `*.first_token`/`*.first_audio`, `playback.started`,
  `collector.*`.
- **Droppable**: `stt.partial_result`, `*.progress`, `*.chunk`,
  `audio.frame`.

### Example event

```json
{
  "schema_version": "1.0",
  "event_id": "evt_007",
  "trace_id": "sess_1",
  "turn_id": "turn_42",
  "generation_id": "response_12",
  "span_id": "span_tts",
  "parent_id": "span_turn",
  "component": "tts",
  "name": "tts.first_audio",
  "timestamp_ns": 800000000,
  "clock_domain": "monotonic:12345",
  "sequence": 6,
  "attributes": { "backend": "kokoro" }
}
```

## 7. Contracts and data structures

Schema versioning: `schema_version` is a string `MAJOR.MINOR`. A MINOR
bump adds optional fields or events; a MAJOR bump may break consumers and
MUST be accompanied by a new decision. The validator MUST reject a
document whose `schema_version` major exceeds the supported one.

## 8. Invariants

- An event has an `event_id` and an order; never a bare causality.
- No metric without an explicit event pair (spec 0004).
- `completeness` reflects any critical-event loss (spec 0005).
- The document is serializable without live objects.
- No voice content in `attributes` (decision 0004).

## 9. Failure modes

- **Missing event**: a metric endpoint absent → metric is
  `unavailable` with the reason; never substituted.
- **Duplicated event**: same `event_id` twice → kept, flagged
  `duplicate_event`; ordering preserved.
- **Reordered event**: `sequence` out of order within a domain → kept,
  flagged `reordered`; the analyzer MUST NOT reorder silently, it
  MUST report and use `(timestamp_ns, sequence)` for analysis order.
- **Late event after terminal**: kept, flagged `late_after_terminal`
  (spec 0006).

## 10. Test and acceptance criteria

- The schema validates a minimal document and rejects one missing
  `timestamp_ns`, `clock_domain`, or `trace_id`.
- A duplicated `event_id` is flagged, not dropped.
- A document with events out of `(timestamp_ns, sequence)` order is
  flagged `reordered`.
- A `trace_id` is required (alias rule).

## 11. Alternatives considered

- **All brief fields as first-class distinct fields**: rejected — breaks
  the existing schema and adds redundancy; aliases extend without
  breaking.
- **Minimal schema, add fields only when a consumer needs them**:
  rejected for `trace_id` (needed now for trace identity); adopted for
  the rest, which stay optional.

## 12. Open questions

- Should `correlation_id` be a top-level field or an attribute? Suggested:
  attribute, promoted when a consumer requires it.
- Should `queue.*` events be emitted by default or only where hooks exist?
  Suggested: only where hooks exist (spec 0005).

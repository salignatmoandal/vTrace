# vTrace Specification 0006 — Lifecycle and Cancellation

- **Status:** Proposed
- **Date:** 2026-10-16
- **Related decisions:** [0005 (no inferred causality)](../decisions/0005-no-inferred-causality.md)
- **Supersedes (content):** former RFC-0004 (lifecycle), folded here
- **Depends on:** [0003 (event schema)](0003-event-schema.md)

## 1. Purpose

Define turn and task lifecycle states, cancellation propagation, illegal
transitions, and the handling of late and duplicate terminal events.

## 2. Problem statement

The reference pipeline cancels via a generation counter
(`cancel_scope.py`): downstream handlers detect stale work with
`is_stale(gen)`. Cancellation request, acknowledgement, and completion
are NOT separate timestamped events. This hides propagation latency and
tasks that keep running after cancellation. vTrace MUST model
cancellation as a lifecycle, not a flag.

## 3. Key concepts

- **Turn**: one user utterance + response; terminal is unique.
- **Task**: a unit of work (`queued` → `started` → terminal); multiple
  per turn allowed when `generation_id`/`span_id` distinguishes them.
- **Cancellation request vs acknowledgement vs completion**: three
  distinct events.
- **Structured concurrency**: the profiler records, it does NOT cancel
  user tasks (invariant 1).

## 4. Functional requirements

- Turn states: `started` then a single terminal among `completed`,
  `failed`, `cancelled`, `timed_out`.
- `cancel.requested` is NOT a turn state. `turn.cancelled` means the
  turn's cancellation is confirmed.
- Task states: `queued` → `started` → task terminal (`completed`,
  `failed`, `cancelled`).
- VAD MUST remain fronts (`vad.speech_started`/`vad.speech_ended`), NOT
  a forced span.
- The lifecycle tracker MUST detect and flag:
  - `duplicate_terminal` (second terminal for a turn);
  - `late_after_terminal` (event after a terminal);
  - `orphaned_after_cancel` (task with no terminal after
    `cancel.requested`);
  - `invalid_transition` (e.g. `completed` → `failed`).
- Anomalies MUST be kept in the trace and signaled, NEVER silently
  corrected.
- `timed_out` MUST be emitted by the instrumented pipeline, not by
  vTrace.

## 5. Non-functional requirements

- Lifecycle validation MUST NOT block `record()`; it runs on analysis,
  not on the hot path.

## 6. Technical design

### Turn state machine

```
started --> completed
started --> failed
started --> cancelled
started --> timed_out
```

### Cancellation flow

```
cancel.requested
  --> cancel.acknowledged   (receipt confirmed)
  --> *.cancelled           (task effective stop confirmed)
  --> turn.cancelled        (turn stop confirmed)
```

`cancel_latency_ms` measures `cancel.requested` →
`cancel.acknowledged` or `*.cancelled` (spec 0004). A task that keeps
running after `cancel.requested` is flagged `orphaned_after_cancel`.

### Representation

Cancellation, failure, and timeout are states BOTH turn and task: a
`timed_out` turn MAY contain `cancelled` tasks. vTrace MUST NOT force
a single shared state machine.

## 7. Contracts and data structures

State is derived from events; the tracker does NOT store mutable
runtime state beyond what events say. The trace document is the source
of truth (decision 0006).

## 8. Invariants

- A turn has at most one terminal; a second is kept and flagged.
- `cancel.requested` is not a terminal.
- The profiler cancels no user task.
- An illegal transition is signaled, not silently corrected.
- VAD is not forced into `queued/started/completed`.

## 9. Failure modes

- Task running after `cancel.requested`: `orphaned_after_cancel`.
- Duplicate terminal read as resume: the turn does NOT reopen;
  `duplicate_terminal`.
- Late event deleted for cleanliness: kept, `late_after_terminal`.
- VAD forced into a span: mitigation, explicit fronts.

## 10. Test and acceptance criteria

- Two `turn.completed` → `duplicate_terminal`, turn does not reopen.
- Event after `turn.cancelled` → kept, `late_after_terminal`.
- Task with no terminal after `cancel.requested` →
  `orphaned_after_cancel`.
- `completed` → `failed` → `invalid_transition`.

## 11. Alternatives considered

- **Single state machine for all**: rejected — VAD, turn, task differ.
- **`cancel.requested` as terminal**: rejected — conflates request
  and confirmation; hides propagation latency (the thing vTrace
  measures).

## 12. Open questions

- Should `orphaned_after_cancel` have a grace window before flagging?
  Suggested: no — flag immediately, let the report explain.

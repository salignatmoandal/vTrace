# vTrace Specification 0004 — Clock and Metrics

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related decisions:** [0002 (contract governance)](../decisions/0002-contract-governance.md)
- **Supersedes (content):** former RFC-0003 (clock) and the former RFC-0002 metric catalog, folded here

## 1. Purpose

Define clock semantics and the metric catalog: every metric is a pair of
events with explicit start and end, a unit, and a missing-data behavior.

## 2. Problem statement

`time.perf_counter_ns()` is monotonic within a process; two monotonic
clocks from different processes are NOT comparable. Comparing
inter-domain timestamps as if they shared a clock is a silent error. Mean
latency hides tail behavior.

## 3. Key concepts

- **Monotonic clock**: `now_ns()` non-decreasing within a domain.
- **Clock domain**: the identity of a clock instance; stored with every
  timestamp.
- **Manual clock**: deterministic, advances explicitly; for tests.
- **Resolution vs precision**: stored resolution is the nanosecond;
  real precision is the OS's and MUST be documented, not claimed.
- **Metric**: a duration or instant defined by an explicit event pair.

## 4. Functional requirements

- Every timestamp MUST carry its `clock_domain`.
- A duration MUST be computed only within a single domain; a cross-domain
  subtraction MUST fail or return `unavailable`.
- `MonotonicClock` domain MUST be frozen at collector startup
  (`monotonic:{pid}` per instance, not per PID alone).
- `ManualClock` MUST be reproducible for a given advance sequence.
- No inter-process timestamp comparison in the MVP.

## 5. Non-functional requirements

- `now_ns()` MUST be cheap (no syscall storm); the collector MUST NOT
  measure on the audio callback beyond the single `now_ns()` call.

## 6. Technical design

### Clock abstraction

```python
class Clock(Protocol):
    def domain(self) -> str: ...
    def now_ns(self) -> int: ...
```

- `MonotonicClock`: `time.perf_counter_ns()`, domain `monotonic:{pid}`.
- `ManualClock`: domain `manual:*`.

### FFI boundary

Timestamps cross the Rust/Python FFI as `i64` ns + `clock_domain`
string. A raw `std::time::Instant` MUST NOT cross the FFI.

### Metric catalog

| Metric | Start | End | Unit | Missing-data |
|---|---|---|---|---|
| `stt_latency_ms` | `stt.started` | `stt.completed` | ms | `unavailable` |
| `llm_ttft_ms` | `llm.started` | `llm.first_token` | ms | `unavailable` |
| `tts_ttfa_ms` | `tts.started` | `tts.first_audio` | ms | `unavailable` |
| `time_to_audible_ms` | `vad.speech_ended` | `playback.started` | ms | `unavailable` if no playback hook |
| `e2e_latency_ms` | `turn.started` | `turn.completed` | ms | `unavailable` |
| `queue_wait_ms` | `queue.enqueued` (or `*.queued`) | `*.started` | ms | `unavailable` if no enqueue hook |
| `tts_rtf` | (audio produced / synthesis time) | — | ratio | `unavailable` until audio duration is an attribute |
| `cancel_latency_ms` | `cancel.requested` | `cancel.acknowledged` or `*.cancelled` | ms | `unavailable` |
| `dropped_events_total` | export counter | — | count | 0 if none |
| `instrumentation_overhead_ns` | measured by benchmark (spec 0008) | — | ns | `unavailable` until P5 |

`tts_ttfa_ms` (first synthesized), first submission, and
`time_to_audible_ms` (first audible) are distinct. `time_to_audible_ms`
MUST be `unavailable` when no playback hook confirms audibility; it MUST
NOT be substituted with `tts_ttfa_ms` (decision 0005).

`tts_rtf` is defined but MUST NOT be computed until audio duration is an
explicit attribute; it MUST NOT be estimated.

## 7. Contracts and data structures

Metric results are returned with a status: `ok(value)` | `unavailable(reason)`
| `ambiguous(reason)`. Aggregation (p50/95/99) is defined in spec 0008 and
MUST NOT be computed on a single run.

## 8. Invariants

- Every timestamp carries its `clock_domain`.
- No duration across two domains.
- `MonotonicClock` domain frozen at startup.
- `ManualClock` reproducible.
- No metric without an explicit event pair.

## 9. Failure modes

- Silent cross-domain subtraction: mitigation, validation + test.
- Resolution/precision confusion: mitigation, explicit doc.
- Domain reused after restart: mitigation, domain frozen per collector
  instance; document exports the domains used.

## 10. Test and acceptance criteria

- `ManualClock` produces a deterministic event sequence.
- A cross-domain subtraction returns `unavailable`, not a number.
- A metric missing an endpoint returns `unavailable`.
- `time_to_audible_ms` is `unavailable` without `playback.started`.

## 11. Alternatives considered

- **Wall clock**: rejected — not monotonic, NTP-sensitive.
- **PTP/NTP multi-process sync**: rejected for MVP — no demonstrated use
  case; cross-process correlation, if needed, uses shared IDs.

## 12. Open questions

- Expose effective clock resolution in the document? Suggested: no for
  MVP, documented in prose.

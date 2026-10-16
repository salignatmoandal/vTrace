"""Bounded event collector — the hot path.

The collector records events without blocking. It timestamps BEFORE
the queue (spec 0005) and uses try_push into a bounded buffer. When
the buffer is full, the event is dropped and counted (never silent —
invariant 9: visible loss).

Design:
- Single-producer for P1. Multi-producer with locks arrives in P2/P3.
- The clock is the Rust `Clock` via PyO3 (vtrace._vtrace).
- Events are stored as dicts (the trace document contract, decision 0006).
- `flush()` assembles the `TraceDocument` and returns it as a dict.

Non-goals (P1):
- No multi-producer locking.
- No background export thread.
- No JSON encoding on the record() path.
"""

from __future__ import annotations

from typing import Any

# Components allowed by the event schema (spec 0003).
_VALID_COMPONENTS = frozenset({"vad", "stt", "llm", "tts", "playback", "turn", "collector"})


class Collector:
    """A bounded event collector for one voice turn.

    Parameters
    ----------
    clock:
        A `vtrace.Clock` (Rust, via PyO3) providing `now_ns()` and `domain`.
    session_id:
        Session identifier shared across turns.
    turn_id:
        The turn this collector records.
    capacity:
        Maximum number of events in the buffer. When full, new events
        are dropped and counted (try_push semantics, spec 0005).
    schema_version:
        Document contract version. Must match across all events.
    """

    def __init__(
        self,
        clock: Any,
        session_id: str,
        turn_id: str,
        capacity: int = 4096,
        schema_version: str = "1.0",
    ) -> None:
        self._clock = clock
        self._session_id = session_id
        self._turn_id = turn_id
        self._capacity = capacity
        self._schema_version = schema_version

        self._buffer: list[dict[str, Any]] = []
        self._sequence: int = 0
        self._dropped_total: int = 0
        self._dropped_critical: int = 0

    @property
    def domain(self) -> str:
        """The clock domain of this collector."""
        return self._clock.domain

    @property
    def dropped_total(self) -> int:
        """Total events rejected (buffer full)."""
        return self._dropped_total

    @property
    def dropped_critical(self) -> int:
        """Critical events lost (never silent)."""
        return self._dropped_critical

    @property
    def completeness(self) -> str:
        """`partial` if any critical event was dropped, else `complete`."""
        return "partial" if self._dropped_critical > 0 else "complete"

    @property
    def event_count(self) -> int:
        """Number of events currently in the buffer."""
        return len(self._buffer)

    def record(
        self,
        component: str,
        name: str,
        span_id: str,
        parent_span_id: str | None = None,
        response_id: str | None = None,
        critical: bool = True,
        **attributes: Any,
    ) -> str | None:
        """Record an event. Returns the event_id, or None if dropped.

        This is the hot path (spec 0005). It MUST NOT:
        - block on I/O,
        - encode JSON,
        - allocate heavily.

        It timestamps BEFORE the queue and uses try_push (check capacity,
        drop+count if full, else push).
        """
        if component not in _VALID_COMPONENTS:
            raise ValueError(
                f"invalid component {component!r}; must be one of {sorted(_VALID_COMPONENTS)}"
            )

        # Timestamp BEFORE the queue (spec 0005).
        timestamp_ns = self._clock.now_ns()

        # try_push: check capacity, drop+count if full.
        if len(self._buffer) >= self._capacity:
            self._dropped_total += 1
            if critical:
                self._dropped_critical += 1
            return None

        event_id = f"evt_{self._sequence:06d}"
        event: dict[str, Any] = {
            "schema_version": self._schema_version,
            "event_id": event_id,
            "session_id": self._session_id,
            "turn_id": self._turn_id,
            "span_id": span_id,
            "component": component,
            "name": name,
            "timestamp_ns": timestamp_ns,
            "clock_domain": self._clock.domain,
            "sequence": self._sequence,
        }
        if response_id is not None:
            event["response_id"] = response_id
        if parent_span_id is not None:
            event["parent_span_id"] = parent_span_id
        if attributes:
            event["attributes"] = dict(attributes)

        self._buffer.append(event)
        self._sequence += 1
        return event_id

    def flush(self) -> dict[str, Any]:
        """Assemble and return the trace document.

        Returns a dict matching `TraceDocument` (spec 0003,
        decision 0006). The buffer is NOT cleared; call `clear()` to
        reset.
        """
        return {
            "schema_version": self._schema_version,
            "clock_domains": [self._clock.domain],
            "completeness": self.completeness,
            "dropped_total": self._dropped_total,
            "dropped_critical": self._dropped_critical,
            "events": list(self._buffer),
        }

    def clear(self) -> None:
        """Clear the buffer and reset counters. For reuse."""
        self._buffer.clear()
        self._sequence = 0
        self._dropped_total = 0
        self._dropped_critical = 0

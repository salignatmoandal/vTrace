"""Bounded event collector — the hot path (P2: multi-producer).

The collector records events without blocking. It timestamps BEFORE
the queue (spec 0005) and uses try_push into a bounded buffer. When
the buffer is full:
  - a droppable event is rejected and ``dropped_total`` incremented;
  - a critical event evicts the oldest droppable event if one exists;
  - if no droppable event exists, ``dropped_critical`` is incremented
    and ``completeness`` becomes ``partial`` (invariant 9: visible loss).

P2 changes (spec 0005):
- **Thread-safe**: a short ``threading.Lock`` around buffer mutation
  and counter updates. ``now_ns()`` is called BEFORE the lock so the
  audio callback thread never contends.
- **Per-producer sequence**: each producer (thread) has its own
  ``sequence`` counter. ``sequence`` breaks ties, it does NOT impose
  a global order. ``producer_id`` identifies the producer (optional,
  only included in the event when explicitly passed).
- **Critical event eviction**: a critical event evicts the oldest
  droppable event rather than being dropped.
- **``shutdown()``**: marks the collector closed; subsequent
  ``record()`` calls are rejected.

Design:
- Multi-producer via ``threading.Lock`` (P2). A lock-free Rust
  implementation may arrive if P5 benchmarks show contention.
- The clock is the Rust ``Clock`` via PyO3 (vtrace._vtrace).
- Events are stored as dicts (the trace document contract, decision 0006).
- ``flush()`` assembles the ``TraceDocument`` and returns it as a dict.
- Internal fields prefixed with ``_`` are stripped on ``flush()``.

Non-goals (P2):
- No background export thread.
- No JSON encoding on the record() path.
"""

from __future__ import annotations

import threading
from typing import Any

# Components allowed by the event schema (spec 0003).
_VALID_COMPONENTS = frozenset({"vad", "stt", "llm", "tts", "playback", "turn", "collector"})


class Collector:
    """A bounded, thread-safe event collector for one voice turn.

    Parameters
    ----------
    clock:
        A ``vtrace.Clock`` (Rust, via PyO3) providing ``now_ns()`` and
        ``domain``.
    session_id:
        Session identifier shared across turns.
    turn_id:
        The turn this collector records.
    capacity:
        Maximum number of events in the buffer. When full, droppable
        events are rejected; critical events evict the oldest droppable
        (spec 0005).
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
        self._lock = threading.Lock()
        self._event_counter: int = 0  # global, for event_id uniqueness
        self._sequences: dict[str, int] = {}  # producer_id → next sequence
        self._dropped_total: int = 0
        self._dropped_critical: int = 0
        self._shutdown: bool = False

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
        """``partial`` if any critical event was dropped, else ``complete``."""
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
        producer_id: str | None = None,
        **attributes: Any,
    ) -> str | None:
        """Record an event. Returns the event_id, or None if dropped.

        This is the hot path (spec 0005). It MUST NOT:
        - block on I/O,
        - encode JSON,
        - allocate heavily,
        - take contended locks for long.

        It timestamps BEFORE the lock (caller thread), then acquires a
        short lock around buffer mutation and counter updates.
        """
        if component not in _VALID_COMPONENTS:
            raise ValueError(
                f"invalid component {component!r}; must be one of {sorted(_VALID_COMPONENTS)}"
            )

        # Timestamp BEFORE the lock (spec 0005).
        timestamp_ns = self._clock.now_ns()

        # Default producer_id from thread identity (internal only;
        # not included in the event unless explicitly passed).
        internal_pid = producer_id if producer_id is not None else str(threading.get_ident())

        with self._lock:
            if self._shutdown:
                return None

            seq = self._sequences.get(internal_pid, 0)

            # try_push: check capacity, drop/evict if full.
            if len(self._buffer) >= self._capacity:
                if not critical:
                    # Droppable event: reject and count.
                    self._dropped_total += 1
                    return None
                # Critical event: try to evict the oldest droppable.
                evicted = self._evict_oldest_droppable()
                if evicted:
                    self._dropped_total += 1
                    # Room is now available; fall through to push.
                else:
                    # No droppable to evict: lose the critical event.
                    self._dropped_total += 1
                    self._dropped_critical += 1
                    return None

            event_id = f"evt_{self._event_counter:06d}"
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
                "sequence": seq,
            }
            if producer_id is not None:
                event["producer_id"] = producer_id
            if response_id is not None:
                event["response_id"] = response_id
            if parent_span_id is not None:
                event["parent_span_id"] = parent_span_id
            if attributes:
                event["attributes"] = dict(attributes)

            # Internal: track droppability (stripped on flush).
            event["_droppable"] = not critical

            self._buffer.append(event)
            self._sequences[internal_pid] = seq + 1
            self._event_counter += 1
            return event_id

    def _evict_oldest_droppable(self) -> bool:
        """Find and remove the oldest droppable event.

        Returns True if an event was evicted, False if the buffer
        contains no droppable events.
        """
        for i, ev in enumerate(self._buffer):
            if ev.get("_droppable", False):
                self._buffer.pop(i)
                return True
        return False

    def flush(self) -> dict[str, Any]:
        """Assemble and return the trace document.

        Returns a dict matching ``TraceDocument`` (spec 0003,
        decision 0006). Internal fields (prefixed with ``_``) are
        stripped. The buffer is NOT cleared; call ``clear()`` to reset.
        """
        with self._lock:
            events = [{k: v for k, v in ev.items() if not k.startswith("_")} for ev in self._buffer]
            return {
                "schema_version": self._schema_version,
                "clock_domains": [self._clock.domain],
                "completeness": self.completeness,
                "dropped_total": self._dropped_total,
                "dropped_critical": self._dropped_critical,
                "events": events,
            }

    def shutdown(self) -> None:
        """Mark the collector as shut down.

        Subsequent ``record()`` calls are rejected (return None).
        The buffer is NOT cleared; call ``flush()`` to get the document.
        """
        with self._lock:
            self._shutdown = True

    def clear(self) -> None:
        """Clear the buffer and reset counters. For reuse."""
        with self._lock:
            self._buffer.clear()
            self._event_counter = 0
            self._sequences.clear()
            self._dropped_total = 0
            self._dropped_critical = 0
            self._shutdown = False

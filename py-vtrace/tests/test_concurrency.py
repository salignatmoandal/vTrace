"""P2 concurrency tests — multi-producer, eviction, shutdown (spec 0005).

Tests are deterministic where possible (manual clock). Concurrent
stress tests check thread-safety and buffer saturation, not
ordering (concurrent producers may interleave non-deterministically;
spec 0003 says reordered events are kept and flagged, not rejected).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from vtrace import Collector, ManualClock


def _make_collector(capacity: int = 4096) -> Collector:
    clock = ManualClock("manual:p2-test", 0, 1)
    return Collector(clock, "sess_p2", "turn_p2", capacity=capacity)


# --- Thread safety ----------------------------------------------------------


def test_concurrent_producers_all_events_present() -> None:
    """N threads each record M events; all N*M events must be present."""
    n_producers = 4
    n_events = 100
    collector = _make_collector(capacity=n_producers * n_events + 100)

    def producer(pid: str) -> None:
        for _i in range(n_events):
            collector.record(
                "stt",
                "stt.partial_result",
                f"span_{pid}",
                producer_id=pid,
                critical=False,
            )

    with ThreadPoolExecutor(max_workers=n_producers) as pool:
        futures = [pool.submit(producer, f"p{j}") for j in range(n_producers)]
        for f in futures:
            f.result()

    doc = collector.flush()
    assert len(doc["events"]) == n_producers * n_events
    assert doc["dropped_total"] == 0
    assert doc["completeness"] == "complete"


def test_concurrent_producers_no_crash() -> None:
    """High-concurrency stress: no exception, no deadlock."""
    collector = _make_collector(capacity=8192)
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        for _i in range(50):
            collector.record(
                "llm", "llm.first_token", "span_llm", producer_id=f"t{threading.get_ident()}"
            )

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert collector.event_count > 0


# --- Per-producer sequence --------------------------------------------------


def test_per_producer_sequence_independent() -> None:
    """Each producer gets its own 0, 1, 2, ... sequence."""
    collector = _make_collector()

    collector.record("stt", "stt.started", "span_stt", producer_id="A")
    collector.record("stt", "stt.started", "span_stt", producer_id="B")
    collector.record("stt", "stt.started", "span_stt", producer_id="A")
    collector.record("stt", "stt.started", "span_stt", producer_id="B")

    doc = collector.flush()
    by_pid: dict[str, list[int]] = {}
    for ev in doc["events"]:
        by_pid.setdefault(ev["producer_id"], []).append(ev["sequence"])

    assert by_pid["A"] == [0, 1]
    assert by_pid["B"] == [0, 1]


def test_producer_id_included_only_when_passed() -> None:
    """producer_id is NOT in the event when not explicitly passed."""
    collector = _make_collector()
    collector.record("turn", "turn.started", "span_turn")
    doc = collector.flush()
    assert "producer_id" not in doc["events"][0]


# --- Critical event eviction ------------------------------------------------


def test_critical_evicts_oldest_droppable() -> None:
    """A critical event evicts the oldest droppable when buffer is full."""
    collector = _make_collector(capacity=3)

    # Fill with droppable events.
    collector.record("stt", "stt.partial_result", "span_stt", critical=False)
    collector.record("stt", "stt.partial_result", "span_stt", critical=False)
    collector.record("stt", "stt.partial_result", "span_stt", critical=False)
    assert collector.event_count == 3

    # Critical event: should evict the oldest droppable.
    eid = collector.record("turn", "turn.started", "span_turn", critical=True)
    assert eid is not None
    assert collector.event_count == 3  # evicted one, added one
    assert collector.dropped_total == 1
    assert collector.dropped_critical == 0
    assert collector.completeness == "complete"

    # The critical event should be in the buffer; the first droppable gone.
    doc = collector.flush()
    names = [ev["name"] for ev in doc["events"]]
    assert "turn.started" in names
    # Only 2 partial_result events remain (1 evicted).
    assert names.count("stt.partial_result") == 2


def test_critical_lost_when_no_droppable() -> None:
    """A critical event is lost when buffer is full of critical events."""
    collector = _make_collector(capacity=2)

    collector.record("turn", "turn.started", "span_turn", critical=True)
    collector.record("turn", "turn.completed", "span_turn", critical=True)
    assert collector.event_count == 2

    # Another critical: no droppable to evict → lost.
    eid = collector.record("stt", "stt.started", "span_stt", critical=True)
    assert eid is None
    assert collector.dropped_total == 1
    assert collector.dropped_critical == 1
    assert collector.completeness == "partial"


def test_droppable_rejected_when_full() -> None:
    """A droppable event is rejected when buffer is full (no eviction)."""
    collector = _make_collector(capacity=2)

    collector.record("turn", "turn.started", "span_turn", critical=True)
    collector.record("turn", "turn.completed", "span_turn", critical=True)

    # Droppable: rejected, no eviction.
    eid = collector.record("stt", "stt.partial_result", "span_stt", critical=False)
    assert eid is None
    assert collector.dropped_total == 1
    assert collector.dropped_critical == 0
    assert collector.completeness == "complete"


# --- Shutdown ---------------------------------------------------------------


def test_shutdown_rejects_subsequent_records() -> None:
    """After shutdown(), record() returns None."""
    collector = _make_collector()
    collector.record("turn", "turn.started", "span_turn")
    assert collector.event_count == 1

    collector.shutdown()

    eid = collector.record("turn", "turn.completed", "span_turn")
    assert eid is None
    assert collector.event_count == 1  # no new event


def test_shutdown_terminates_quickly() -> None:
    """shutdown() does not block."""
    collector = _make_collector()
    collector.record("turn", "turn.started", "span_turn")

    done = threading.Event()

    def do_shutdown() -> None:
        collector.shutdown()
        done.set()

    t = threading.Thread(target=do_shutdown)
    t.start()
    assert done.wait(timeout=2.0), "shutdown() did not terminate within 2s"
    t.join(timeout=1.0)


def test_flush_strips_internal_fields() -> None:
    """Internal _droppable field is not in the flushed document."""
    collector = _make_collector()
    collector.record("turn", "turn.started", "span_turn", critical=True)
    collector.record("stt", "stt.partial_result", "span_stt", critical=False)

    doc = collector.flush()
    for ev in doc["events"]:
        assert "_droppable" not in ev
        for key in ev:
            assert not key.startswith("_")


def test_clear_resets_sequences_and_shutdown() -> None:
    """clear() resets per-producer sequences and the shutdown flag."""
    collector = _make_collector(capacity=5)
    collector.record("stt", "stt.started", "span_stt", producer_id="A")
    collector.record("stt", "stt.started", "span_stt", producer_id="A")
    collector.shutdown()

    collector.clear()

    # After clear, record works again and sequence restarts at 0.
    eid = collector.record("stt", "stt.started", "span_stt", producer_id="A")
    assert eid is not None
    doc = collector.flush()
    assert doc["events"][0]["sequence"] == 0

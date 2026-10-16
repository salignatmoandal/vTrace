"""Collector tests: bounded buffer, try_push, visible loss.

Proves the collector records events without blocking, drops when
full, and reports loss visibly (invariant 9).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vtrace import ManualClock
from vtrace.collector import Collector

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def test_record_returns_event_id() -> None:
    """record() returns a non-None event_id when not dropped."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1")
    eid = c.record(component="turn", name="turn.started", span_id="sp1")
    assert eid is not None
    assert eid.startswith("evt_")


def test_record_stores_event() -> None:
    """record() stores the event with correct fields."""
    clock = ManualClock("manual:test", 1000, 100)
    c = Collector(clock, session_id="s1", turn_id="t1")
    c.record(
        component="stt",
        name="stt.started",
        span_id="sp_stt",
        parent_span_id="sp_turn",
        backend="fixture",
    )
    doc = c.flush()
    ev = doc["events"][0]
    assert ev["component"] == "stt"
    assert ev["name"] == "stt.started"
    assert ev["timestamp_ns"] == 1000
    assert ev["clock_domain"] == "manual:test"
    assert ev["sequence"] == 0
    assert ev["parent_span_id"] == "sp_turn"
    assert ev["attributes"] == {"backend": "fixture"}


def test_timestamp_before_queue() -> None:
    """Timestamp is taken before the push, not after."""
    clock = ManualClock("manual:test", 0, 100)
    c = Collector(clock, session_id="s1", turn_id="t1")
    # First call: timestamp=0, then clock advances to 100.
    # Second call: timestamp=100, then clock advances to 200.
    c.record(component="turn", name="turn.started", span_id="sp1")
    c.record(component="turn", name="turn.completed", span_id="sp1")
    doc = c.flush()
    assert doc["events"][0]["timestamp_ns"] == 0
    assert doc["events"][1]["timestamp_ns"] == 100


def test_buffer_full_drops_and_counts() -> None:
    """When the buffer is full, events are dropped and counted."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1", capacity=3)
    # Fill the buffer.
    for _ in range(3):
        result = c.record(component="turn", name="turn.started", span_id="sp1")
        assert result is not None
    # This one should be dropped.
    result = c.record(component="turn", name="turn.started", span_id="sp1")
    assert result is None
    assert c.dropped_total == 1
    assert c.dropped_critical == 1
    assert c.completeness == "partial"


def test_non_critical_drop_not_in_critical() -> None:
    """Non-critical drops increment dropped_total but not dropped_critical."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1", capacity=1)
    c.record(component="turn", name="turn.started", span_id="sp1")
    # Non-critical event dropped.
    c.record(component="turn", name="turn.started", span_id="sp1", critical=False)
    assert c.dropped_total == 1
    assert c.dropped_critical == 0
    assert c.completeness == "complete"


def test_flush_produces_valid_document() -> None:
    """flush() produces a document that passes the Rust validator."""
    from vtrace._vtrace import validate

    clock = ManualClock("manual:test", 0, 1000000)
    c = Collector(clock, session_id="sess_1", turn_id="turn_42")
    c.record(component="turn", name="turn.started", span_id="span_turn")
    c.record(
        component="stt",
        name="stt.started",
        span_id="span_stt",
        parent_span_id="span_turn",
    )
    c.record(
        component="stt",
        name="stt.completed",
        span_id="span_stt",
        parent_span_id="span_turn",
    )
    c.record(
        component="turn",
        name="turn.completed",
        span_id="span_turn",
    )
    doc = c.flush()
    json_str = json.dumps(doc)
    validate(json_str)  # must not raise


def test_invalid_component_rejected() -> None:
    """record() rejects an invalid component."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1")
    with pytest.raises(ValueError, match="invalid component"):
        c.record(component="invalid", name="x", span_id="sp1")


def test_clear_resets_state() -> None:
    """clear() resets the buffer and counters."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1", capacity=2)
    c.record(component="turn", name="turn.started", span_id="sp1")
    c.record(component="turn", name="turn.started", span_id="sp1")
    c.record(component="turn", name="turn.started", span_id="sp1")  # dropped
    assert c.dropped_total == 1
    c.clear()
    assert c.event_count == 0
    assert c.dropped_total == 0
    assert c.completeness == "complete"


def test_sequence_increments() -> None:
    """Each event gets a unique, incrementing sequence number."""
    clock = ManualClock("manual:test", 0, 1)
    c = Collector(clock, session_id="s1", turn_id="t1")
    c.record(component="turn", name="a", span_id="sp1")
    c.record(component="turn", name="b", span_id="sp1")
    c.record(component="turn", name="c", span_id="sp1")
    doc = c.flush()
    seqs = [ev["sequence"] for ev in doc["events"]]
    assert seqs == [0, 1, 2]

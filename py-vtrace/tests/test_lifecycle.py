"""P3 lifecycle tests — acceptance criteria from spec 0006 §10.

- Two ``turn.completed`` → ``duplicate_terminal``, turn does not reopen.
- Event after ``turn.cancelled`` → kept, ``late_after_terminal``.
- Task with no terminal after ``cancel.requested`` →
  ``orphaned_after_cancel``.
- ``completed`` → ``failed`` → ``invalid_transition``.
"""

from __future__ import annotations

from typing import Any

from vtrace.lifecycle import analyze_lifecycle
from vtrace.mock_pipeline import run_mock_turn
from vtrace.report import generate_report


def _ev(
    event_id: str,
    name: str,
    *,
    component: str | None = None,
    span_id: str = "span_turn",
    parent_span_id: str | None = None,
    sequence: int = 0,
    timestamp_ns: int = 0,
) -> dict[str, Any]:
    if component is None:
        component = name.split(".", 1)[0]
        if component == "cancel":
            component = "turn"
    ev: dict[str, Any] = {
        "schema_version": "1.0",
        "event_id": event_id,
        "session_id": "sess_1",
        "turn_id": "turn_1",
        "span_id": span_id,
        "component": component,
        "name": name,
        "timestamp_ns": timestamp_ns,
        "clock_domain": "manual:test",
        "sequence": sequence,
    }
    if parent_span_id is not None:
        ev["parent_span_id"] = parent_span_id
    return ev


def _doc(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "clock_domains": ["manual:test"],
        "completeness": "complete",
        "dropped_total": 0,
        "dropped_critical": 0,
        "events": events,
    }


def test_happy_path_no_anomalies() -> None:
    """A clean turn.started → turn.completed has no anomalies."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev("e1", "turn.completed", sequence=1, timestamp_ns=100),
            ]
        )
    )
    assert report.ok
    assert report.turn_state == "turn.completed"
    assert not report.cancel_requested


def test_fixture_mock_pipeline_ok() -> None:
    """The mock pipeline (fixture timeline) has a clean lifecycle."""
    report = analyze_lifecycle(run_mock_turn())
    assert report.ok
    assert report.turn_state == "turn.completed"


def test_duplicate_terminal_two_completed() -> None:
    """Two turn.completed → duplicate_terminal; turn does not reopen."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev("e1", "turn.completed", sequence=1, timestamp_ns=100),
                _ev("e2", "turn.completed", sequence=2, timestamp_ns=200),
            ]
        )
    )
    kinds = [a.kind for a in report.anomalies]
    assert "duplicate_terminal" in kinds
    assert report.turn_state == "turn.completed"  # not reopened
    dup = [a for a in report.anomalies if a.kind == "duplicate_terminal"][0]
    assert dup.event_id == "e2"


def test_invalid_transition_completed_to_failed() -> None:
    """completed → failed → invalid_transition (+ duplicate_terminal)."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev("e1", "turn.completed", sequence=1, timestamp_ns=100),
                _ev("e2", "turn.failed", sequence=2, timestamp_ns=200),
            ]
        )
    )
    kinds = {a.kind for a in report.anomalies}
    assert "duplicate_terminal" in kinds
    assert "invalid_transition" in kinds
    assert report.turn_state == "turn.completed"  # first terminal wins


def test_late_after_terminal() -> None:
    """Event after turn.cancelled → kept, late_after_terminal."""
    events = [
        _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
        _ev("e1", "turn.cancelled", sequence=1, timestamp_ns=100),
        _ev(
            "e2",
            "stt.started",
            component="stt",
            span_id="span_stt",
            parent_span_id="span_turn",
            sequence=2,
            timestamp_ns=200,
        ),
    ]
    doc = _doc(events)
    report = analyze_lifecycle(doc)
    # Event is kept in the document.
    assert len(doc["events"]) == 3
    kinds = [a.kind for a in report.anomalies]
    assert "late_after_terminal" in kinds
    late = [a for a in report.anomalies if a.kind == "late_after_terminal"][0]
    assert late.event_id == "e2"


def test_orphaned_after_cancel() -> None:
    """Task with no terminal after cancel.requested → orphaned_after_cancel."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev(
                    "e1",
                    "llm.started",
                    component="llm",
                    span_id="span_llm",
                    parent_span_id="span_turn",
                    sequence=1,
                    timestamp_ns=10,
                ),
                _ev("e2", "cancel.requested", sequence=2, timestamp_ns=20),
                # No llm.cancelled / llm.completed — orphaned.
                _ev("e3", "turn.cancelled", sequence=3, timestamp_ns=30),
            ]
        )
    )
    kinds = [a.kind for a in report.anomalies]
    assert "orphaned_after_cancel" in kinds
    orphan = [a for a in report.anomalies if a.kind == "orphaned_after_cancel"][0]
    assert orphan.span_id == "span_llm"
    assert report.cancel_requested


def test_cancel_with_task_terminal_not_orphaned() -> None:
    """Task that reaches *.cancelled after cancel.requested is not orphaned."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev(
                    "e1",
                    "llm.started",
                    component="llm",
                    span_id="span_llm",
                    parent_span_id="span_turn",
                    sequence=1,
                    timestamp_ns=10,
                ),
                _ev("e2", "cancel.requested", sequence=2, timestamp_ns=20),
                _ev("e3", "cancel.acknowledged", sequence=3, timestamp_ns=25),
                _ev(
                    "e4",
                    "llm.cancelled",
                    component="llm",
                    span_id="span_llm",
                    parent_span_id="span_turn",
                    sequence=4,
                    timestamp_ns=30,
                ),
                _ev("e5", "turn.cancelled", sequence=5, timestamp_ns=40),
            ]
        )
    )
    kinds = [a.kind for a in report.anomalies]
    assert "orphaned_after_cancel" not in kinds
    assert report.cancel_requested
    assert report.cancel_acknowledged
    assert report.turn_state == "turn.cancelled"


def test_cancel_requested_is_not_turn_terminal() -> None:
    """cancel.requested does not change turn_state to a terminal."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev("e1", "cancel.requested", sequence=1, timestamp_ns=10),
            ]
        )
    )
    assert report.turn_state == "started"
    assert report.cancel_requested


def test_vad_fronts_not_forced_into_span() -> None:
    """VAD speech_started/ended are fronts — no task orphan / terminal logic."""
    report = analyze_lifecycle(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev(
                    "e1",
                    "vad.speech_started",
                    component="vad",
                    span_id="span_vad",
                    sequence=1,
                    timestamp_ns=10,
                ),
                _ev(
                    "e2",
                    "vad.speech_ended",
                    component="vad",
                    span_id="span_vad",
                    sequence=2,
                    timestamp_ns=20,
                ),
                _ev("e3", "cancel.requested", sequence=3, timestamp_ns=30),
                _ev("e4", "turn.cancelled", sequence=4, timestamp_ns=40),
            ]
        )
    )
    kinds = [a.kind for a in report.anomalies]
    assert "orphaned_after_cancel" not in kinds


def test_report_includes_lifecycle_section() -> None:
    """CLI report surfaces the Lifecycle section."""
    text = generate_report(run_mock_turn())
    assert "Lifecycle:" in text
    assert "turn_state:" in text
    assert "anomalies:           none" in text
    assert "Cancellation:" in text
    assert "cancel_latency_ms" in text


def test_report_surfaces_duplicate_terminal() -> None:
    text = generate_report(
        _doc(
            [
                _ev("e0", "turn.started", sequence=0, timestamp_ns=0),
                _ev("e1", "turn.completed", sequence=1, timestamp_ns=100),
                _ev("e2", "turn.completed", sequence=2, timestamp_ns=200),
            ]
        )
    )
    assert "duplicate_terminal" in text

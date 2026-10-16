"""P4 causal analysis tests — acceptance criteria from spec 0007."""

from __future__ import annotations

import json
from pathlib import Path

from vtrace.causal import critical_paths, format_critical_paths
from vtrace.mock_pipeline import run_mock_turn
from vtrace.report import generate_report

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def test_fixture_paths_partial_without_queue() -> None:
    doc = json.loads(FIXTURE.read_text())
    paths = critical_paths(doc)
    by_obj = {p["objective"]: p for p in paths}
    assert by_obj["ttft"]["confidence"] == "partial"
    assert any("missing queue edge" in r for r in by_obj["ttft"]["reasons"])
    assert by_obj["time_to_audible"]["confidence"] == "unavailable"


def test_distinct_objectives() -> None:
    paths = critical_paths(run_mock_turn())
    ends = {p["objective"]: (p["hops"][-1]["name"] if p["hops"] else None) for p in paths}
    assert ends["ttft"] == "llm.first_token"
    assert ends["ttfa"] == "tts.first_audio"
    assert ends["turn_completion"] == "turn.completed"
    assert ends["ttft"] != ends["ttfa"]


def test_same_timestamp_no_inferred_edge() -> None:
    """Two same-timestamp events without explicit link → no fabricated path hop."""
    doc = {
        "schema_version": "1.0",
        "clock_domains": ["manual:test"],
        "completeness": "complete",
        "dropped_total": 0,
        "dropped_critical": 0,
        "events": [
            {
                "schema_version": "1.0",
                "event_id": "e0",
                "session_id": "s",
                "turn_id": "t",
                "span_id": "span_turn",
                "component": "turn",
                "name": "turn.started",
                "timestamp_ns": 100,
                "clock_domain": "manual:test",
                "sequence": 0,
            },
            {
                "schema_version": "1.0",
                "event_id": "e1",
                "session_id": "s",
                "turn_id": "t",
                "span_id": "span_a",
                "component": "stt",
                "name": "stt.partial_result",
                "timestamp_ns": 100,
                "clock_domain": "manual:test",
                "sequence": 1,
            },
            {
                "schema_version": "1.0",
                "event_id": "e2",
                "session_id": "s",
                "turn_id": "t",
                "span_id": "span_b",
                "component": "llm",
                "name": "llm.first_token",
                "timestamp_ns": 100,
                "clock_domain": "manual:test",
                "sequence": 2,
            },
        ],
    }
    paths = critical_paths(doc)
    ttft = next(p for p in paths if p["objective"] == "ttft")
    # Path may be trivial [llm.first_token] but must NOT invent e1 → e2.
    hop_ids = [h["event_id"] for h in ttft["hops"]]
    assert "e1" not in hop_ids


def test_report_includes_critical_paths() -> None:
    text = generate_report(json.loads(FIXTURE.read_text()))
    assert "Critical paths (explicit edges only):" in text
    assert "ttft" in text
    assert "partial" in text


def test_format_critical_paths() -> None:
    paths = critical_paths(run_mock_turn())
    text = format_critical_paths(paths)
    assert "ttft" in text
    assert "path:" in text or "reason:" in text

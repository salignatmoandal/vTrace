"""P6 — speech-to-speech bridge and #714-shaped interrupt demo."""

from __future__ import annotations

import json
from pathlib import Path

from vtrace._vtrace import ManualClock
from vtrace._vtrace import validate as rust_validate

from vtrace.collector import Collector
from vtrace.integrations.s2s import S2STurnBridge, run_s2s_shaped_turn
from vtrace.lifecycle import analyze_lifecycle
from vtrace.report import generate_report

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "fixtures" / "traces" / "s2s-interrupt-turn.json"


def test_bridge_records_structural_events_only() -> None:
    clock = ManualClock("manual:bridge", 0, 0)
    c = Collector(clock, "sess", "turn")
    b = S2STurnBridge(c)
    clock.set(0)
    b.on_turn_started()
    clock.set(10)
    b.on_speech_ended()
    clock.set(20)
    b.on_stt_started()
    clock.set(30)
    b.on_stt_completed(backend="test")
    doc = b.flush()
    names = [e["name"] for e in doc["events"]]
    assert names == [
        "turn.started",
        "vad.speech_ended",
        "stt.started",
        "stt.completed",
    ]
    # No voice content attributes.
    for ev in doc["events"]:
        attrs = ev.get("attributes") or {}
        for key in attrs:
            assert key not in ("transcript", "audio", "prompt", "text", "response")


def test_interrupt_demo_validates_and_matches_fixture() -> None:
    doc = run_s2s_shaped_turn(interrupted=True)
    rust_validate(json.dumps(doc))
    assert doc["completeness"] == "complete"
    names = [e["name"] for e in doc["events"]]
    assert "vad.speech_ended" in names
    assert "tts.first_audio" in names
    assert "vad.speech_started" in names  # barge-in
    assert "cancel.requested" in names
    assert "turn.cancelled" in names
    barge = next(e for e in doc["events"] if e["name"] == "vad.speech_started")
    assert barge["attributes"]["barge_in"] is True

    assert _FIXTURE.is_file(), f"missing fixture {_FIXTURE}"
    fixture = json.loads(_FIXTURE.read_text())
    assert [e["name"] for e in fixture["events"]] == names
    assert [e["timestamp_ns"] for e in fixture["events"]] == [
        e["timestamp_ns"] for e in doc["events"]
    ]


def test_interrupt_lifecycle_sees_cancel() -> None:
    doc = run_s2s_shaped_turn(interrupted=True)
    report = analyze_lifecycle(doc)
    assert report.cancel_requested is True
    assert report.turn_state == "turn.cancelled"


def test_happy_path_completes() -> None:
    doc = run_s2s_shaped_turn(interrupted=False)
    rust_validate(json.dumps(doc))
    report = analyze_lifecycle(doc)
    assert report.turn_state == "turn.completed"
    assert report.cancel_requested is False


def test_interrupt_report_mentions_cancel() -> None:
    doc = run_s2s_shaped_turn(interrupted=True)
    text = generate_report(doc)
    assert "cancel" in text.lower()

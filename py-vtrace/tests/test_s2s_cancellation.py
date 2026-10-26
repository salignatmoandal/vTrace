"""P6 failure paths: an observed cancel request proves no effective stop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vtrace._vtrace import ManualClock
from vtrace._vtrace import validate as rust_validate

from vtrace.causal import critical_paths
from vtrace.collector import Collector
from vtrace.integrations.s2s import S2STurnBridge
from vtrace.lifecycle import analyze_lifecycle
from vtrace.report import generate_report
from vtrace.validate import validate_document

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/traces/s2s-unconfirmed-cancel.json"


def _unconfirmed_cancel() -> dict[str, Any]:
    clock = ManualClock("manual:s2s-unconfirmed-cancel", 0, 0)
    bridge = S2STurnBridge(
        Collector(clock, "sess_s2s", "turn_s2s_unconfirmed_cancel"),
        response_id="response_1",
        producer_id="s2s-test",
    )
    # LLM and TTS are both active when the user interrupts. No hook has
    # confirmed acknowledgement, task termination, or playback start.
    for timestamp, callback in (
        (0, bridge.on_turn_started),
        (50_000_000, bridge.on_speech_ended),
        (60_000_000, bridge.on_llm_started),
        (100_000_000, bridge.on_llm_first_token),
        (110_000_000, bridge.on_tts_started),
        (200_000_000, bridge.on_tts_first_audio),
        (250_000_000, bridge.on_barge_in),
        (260_000_000, bridge.on_cancel_requested),
    ):
        clock.set(timestamp)
        callback()
    return bridge.flush()


def test_request_only_is_not_acknowledgement_or_completion() -> None:
    doc = _unconfirmed_cancel()
    before = json.dumps(doc, sort_keys=True)
    lifecycle = analyze_lifecycle(doc)
    assert lifecycle.turn_state == "started"
    assert lifecycle.cancel_requested is True
    assert lifecycle.cancel_acknowledged is False
    assert {(a.kind, a.span_id) for a in lifecycle.anomalies} == {
        ("orphaned_after_cancel", "span_llm"),
        ("orphaned_after_cancel", "span_tts"),
    }
    report = generate_report(doc)
    assert "cancel_latency_ms     unavailable" in report
    assert "time_to_audible_ms    unavailable" in report
    assert "orphaned_after_cancel" in report
    paths = {p["objective"]: p for p in critical_paths(doc)}
    assert paths["turn_completion"]["confidence"] == "unavailable"
    assert paths["ttfa"]["confidence"] == "partial"
    assert json.dumps(doc, sort_keys=True) == before  # analysis preserves evidence
    # Collection completeness concerns loss, not task/turn completion.
    assert doc["completeness"] == "complete"
    assert doc["dropped_critical"] == 0


def test_request_only_fixture_is_reproducible_and_valid() -> None:
    doc = _unconfirmed_cancel()
    assert doc == _unconfirmed_cancel()
    assert doc == json.loads(_FIXTURE.read_text())
    rust_validate(json.dumps(doc))
    validate_document(_FIXTURE)


def test_barge_in_does_not_request_cancellation() -> None:
    clock = ManualClock("manual:s2s-barge", 0, 0)
    bridge = S2STurnBridge(Collector(clock, "sess", "turn"))
    bridge.on_turn_started()
    clock.set(10)
    bridge.on_barge_in()
    doc = bridge.flush()
    assert [e["name"] for e in doc["events"]] == ["turn.started", "vad.speech_started"]
    lifecycle = analyze_lifecycle(doc)
    assert lifecycle.turn_state == "started"
    assert lifecycle.cancel_requested is False


def test_acknowledgement_does_not_terminate_tasks() -> None:
    clock = ManualClock("manual:s2s-ack", 0, 10)
    bridge = S2STurnBridge(Collector(clock, "sess", "turn"))
    bridge.on_turn_started()
    bridge.on_llm_started()
    bridge.on_cancel_requested()
    bridge.on_cancel_acknowledged()
    lifecycle = analyze_lifecycle(bridge.flush())
    assert lifecycle.turn_state == "started"
    assert lifecycle.cancel_acknowledged is True
    assert [(a.kind, a.span_id) for a in lifecycle.anomalies] == [
        ("orphaned_after_cancel", "span_llm")
    ]


def test_completion_callbacks_preserve_identity_and_observation_time() -> None:
    clock = ManualClock("manual:s2s-completion", 0, 0)
    bridge = S2STurnBridge(
        Collector(clock, "sess", "turn"),
        turn_span_id="custom_turn",
        response_id="response_2",
        producer_id="handler",
    )
    bridge.on_turn_started()
    bridge.on_llm_started()
    bridge.on_tts_started()
    clock.set(100)
    llm_id = bridge.on_llm_completed()
    clock.set(200)
    tts_id = bridge.on_tts_completed()
    clock.set(300)
    bridge.on_turn_completed()
    doc = bridge.flush()
    terminals = [e for e in doc["events"] if e["event_id"] in (llm_id, tts_id)]
    assert [(e["name"], e["span_id"], e["timestamp_ns"]) for e in terminals] == [
        ("llm.completed", "span_llm", 100),
        ("tts.completed", "span_tts", 200),
    ]
    for event in terminals:
        assert event["parent_span_id"] == "custom_turn"
        assert event["response_id"] == "response_2"
        assert event["producer_id"] == "handler"
        assert "attributes" not in event
    assert analyze_lifecycle(doc).ok
    rust_validate(json.dumps(doc))


def test_lost_cancellation_is_visible() -> None:
    clock = ManualClock("manual:s2s-loss", 0, 10)
    bridge = S2STurnBridge(Collector(clock, "sess", "turn", capacity=2))
    bridge.on_turn_started()
    bridge.on_llm_started()
    assert bridge.on_cancel_requested() is None
    assert bridge.on_llm_cancelled() is None
    doc = bridge.flush()
    assert doc["completeness"] == "partial"
    assert doc["dropped_total"] == 2
    assert doc["dropped_critical"] == 2
    assert "2 critical lost" in generate_report(doc)
    rust_validate(json.dumps(doc))

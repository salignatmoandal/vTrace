"""Tests for B4 adapters and mock pipeline.

Proves the adapters produce a trace that matches the fixture
event-for-event and validates against the Rust contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from vtrace._vtrace import validate as rust_validate

from vtrace.mock_pipeline import run_mock_turn

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def _fixture_events() -> list[dict]:
    doc = json.loads(FIXTURE.read_text())
    return doc["events"]


def _mock_events() -> list[dict]:
    return run_mock_turn()["events"]


def test_mock_turn_validates_against_rust() -> None:
    """The mock pipeline output validates via the Rust contract."""
    doc = run_mock_turn()
    rust_validate(json.dumps(doc))


def test_mock_turn_is_complete() -> None:
    """No critical events dropped (invariant 9)."""
    doc = run_mock_turn()
    assert doc["completeness"] == "complete"
    assert doc["dropped_critical"] == 0
    assert doc["dropped_total"] == 0


def test_mock_event_count_matches_fixture() -> None:
    assert len(_mock_events()) == len(_fixture_events())


def test_mock_event_names_match_fixture() -> None:
    mock_names = [ev["name"] for ev in _mock_events()]
    fixture_names = [ev["name"] for ev in _fixture_events()]
    assert mock_names == fixture_names


def test_mock_timestamps_match_fixture() -> None:
    mock_ts = [ev["timestamp_ns"] for ev in _mock_events()]
    fixture_ts = [ev["timestamp_ns"] for ev in _fixture_events()]
    assert mock_ts == fixture_ts


def test_mock_sequences_match_fixture() -> None:
    mock_seq = [ev["sequence"] for ev in _mock_events()]
    fixture_seq = [ev["sequence"] for ev in _fixture_events()]
    assert mock_seq == fixture_seq


def test_mock_components_match_fixture() -> None:
    mock_comp = [ev["component"] for ev in _mock_events()]
    fixture_comp = [ev["component"] for ev in _fixture_events()]
    assert mock_comp == fixture_comp


def test_mock_span_ids_match_fixture() -> None:
    mock_spans = [(ev["span_id"], ev.get("parent_span_id")) for ev in _mock_events()]
    fixture_spans = [(ev["span_id"], ev.get("parent_span_id")) for ev in _fixture_events()]
    assert mock_spans == fixture_spans


def test_mock_clock_domain_matches_fixture() -> None:
    doc = run_mock_turn()
    assert doc["clock_domains"] == ["manual:turn-42"]
    for ev in doc["events"]:
        assert ev["clock_domain"] == "manual:turn-42"


def test_mock_has_one_turn_terminal() -> None:
    """A turn has exactly one terminal (spec 0006)."""
    events = _mock_events()
    terminals = [
        ev
        for ev in events
        if ev["component"] == "turn"
        and ev["name"] in ("turn.completed", "turn.failed", "turn.cancelled", "turn.timed_out")
    ]
    assert len(terminals) == 1
    assert terminals[0]["name"] == "turn.completed"


def test_stt_attributes_preserved() -> None:
    """The stt.completed event carries its attributes (spec 0003)."""
    events = _mock_events()
    stt_completed = [ev for ev in events if ev["name"] == "stt.completed"][0]
    assert stt_completed["attributes"] == {"backend": "fixture"}

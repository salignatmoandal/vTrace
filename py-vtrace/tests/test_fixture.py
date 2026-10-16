"""Acceptance test: the fixture trace conforms to the contract.

This is the vTrace analog of SoundCraft's `agent_tasks.rs`: the contract
is proven by a real trace, not a mock. The fixture uses a manual clock
(spec 0004) so the result is deterministic.
"""

from __future__ import annotations

from pathlib import Path

import vtrace.validate as validate

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def test_fixture_validates_against_schema() -> None:
    validate.validate_document(FIXTURE)


def test_fixture_is_complete() -> None:
    import json

    document = json.loads(FIXTURE.read_text())
    assert document["completeness"] == "complete"
    assert document["dropped_critical"] == 0


def test_fixture_has_one_turn_terminal() -> None:
    import json

    document = json.loads(FIXTURE.read_text())
    terminals = [
        ev
        for ev in document["events"]
        if ev["component"] == "turn"
        and ev["name"] in ("turn.completed", "turn.failed", "turn.cancelled", "turn.timed_out")
    ]
    assert len(terminals) == 1, "a turn must have exactly one terminal (spec 0006)"
    assert terminals[0]["name"] == "turn.completed"


def test_ttfa_and_playback_are_distinct() -> None:
    import json

    document = json.loads(FIXTURE.read_text())
    by_name = {ev["name"]: ev for ev in document["events"]}
    # tts.first_audio and playback.started must be distinct events
    # with first_audio before playback (spec 0003).
    assert "tts.first_audio" in by_name
    assert "playback.started" in by_name
    assert by_name["tts.first_audio"]["timestamp_ns"] <= by_name["playback.started"]["timestamp_ns"]

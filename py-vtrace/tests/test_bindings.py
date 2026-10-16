"""Bridge tests: Python calls the Rust typed contract via PyO3.

These prove the FFI bridge works: Python can create a Clock, call
now_ns(), and validate a trace document through the Rust validator.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def test_native_module_importable() -> None:
    """The Rust extension _vtrace is importable."""
    import vtrace._vtrace

    assert hasattr(vtrace._vtrace, "validate")
    assert hasattr(vtrace._vtrace, "MonotonicClock")
    assert hasattr(vtrace._vtrace, "ManualClock")


def test_validate_accepts_valid_fixture() -> None:
    """The Rust validator accepts the one-turn fixture."""
    from vtrace._vtrace import validate

    json_str = FIXTURE.read_text()
    validate(json_str)  # must not raise


def test_validate_rejects_missing_timestamp() -> None:
    """The Rust validator rejects an event without timestamp_ns."""
    from vtrace._vtrace import validate

    bad = (
        '{"schema_version":"1.0","clock_domains":["t"],'
        '"completeness":"complete","dropped_total":0,"dropped_critical":0,'
        '"events":[{"schema_version":"1.0","event_id":"e1","session_id":"s",'
        '"turn_id":"t","span_id":"sp","component":"turn","name":"turn.started",'
        '"clock_domain":"t","sequence":0}]}'
    )
    with pytest.raises(ValueError):
        validate(bad)


def test_monotonic_clock_non_decreasing() -> None:
    """MonotonicClock.now_ns() is non-decreasing."""
    from vtrace import MonotonicClock

    clock = MonotonicClock("mono:test")
    a = clock.now_ns()
    b = clock.now_ns()
    assert b >= a
    assert clock.domain == "mono:test"


def test_manual_clock_advances() -> None:
    """ManualClock advances by step_ns on each call."""
    from vtrace import ManualClock

    clock = ManualClock("manual:test", 1000, 500)
    assert clock.now_ns() == 1000
    assert clock.now_ns() == 1500
    assert clock.now_ns() == 2000
    assert clock.domain == "manual:test"


def test_manual_clock_set() -> None:
    """ManualClock.set() overrides the next timestamp."""
    from vtrace import ManualClock

    clock = ManualClock("manual:test", 0, 1)
    clock.set(9999)
    assert clock.now_ns() == 9999

"""Tests for B5 CLI report.

Proves the report distinguishes compute, queue, and overlap
(spec 0009, P1 acceptance criterion) on the fixture.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from vtrace.cli import main as cli_main
from vtrace.mock_pipeline import run_mock_turn
from vtrace.report import generate_report

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "traces" / "one-turn.json"


def _fixture_doc() -> dict:
    return json.loads(FIXTURE.read_text())


def test_report_contains_timeline() -> None:
    report = generate_report(_fixture_doc())
    assert "Timeline:" in report
    assert "turn.started" in report
    assert "turn.completed" in report


def test_report_contains_compute_metrics() -> None:
    report = generate_report(_fixture_doc())
    assert "Compute (stage durations):" in report
    assert "e2e_latency_ms" in report
    assert "stt_latency_ms" in report
    assert "llm_ttft_ms" in report
    assert "tts_ttfa_ms" in report


def test_report_stt_latency_correct() -> None:
    """stt.started at 1ms, stt.completed at 310ms → 309ms."""
    report = generate_report(_fixture_doc())
    assert "stt_latency_ms        309.00 ms" in report


def test_report_llm_ttft_correct() -> None:
    """llm.started at 320ms, llm.first_token at 600ms → 280ms."""
    report = generate_report(_fixture_doc())
    assert "llm_ttft_ms           280.00 ms" in report


def test_report_tts_ttfa_correct() -> None:
    """tts.started at 610ms, tts.first_audio at 800ms → 190ms."""
    report = generate_report(_fixture_doc())
    assert "tts_ttfa_ms           190.00 ms" in report


def test_report_e2e_latency_correct() -> None:
    """turn.started at 0, turn.completed at 2400ms → 2400ms."""
    report = generate_report(_fixture_doc())
    assert "e2e_latency_ms        2400.00 ms" in report


def test_report_time_to_audible_unavailable() -> None:
    """No vad.speech_ended → time_to_audible is unavailable (spec 0004)."""
    report = generate_report(_fixture_doc())
    assert "time_to_audible_ms    unavailable (no vad.speech_ended)" in report


def test_report_contains_queue_section() -> None:
    report = generate_report(_fixture_doc())
    assert "Queue (handoff between stages):" in report
    assert "stt → llm" in report
    assert "llm → tts" in report
    assert "tts → playback" in report


def test_report_handoff_stt_to_llm_correct() -> None:
    """stt.completed at 310ms, llm.started at 320ms → 10ms handoff."""
    report = generate_report(_fixture_doc())
    assert "stt → llm             10.00 ms" in report


def test_report_handoff_llm_to_tts_correct() -> None:
    """llm.first_token at 600ms, tts.started at 610ms → 10ms handoff."""
    report = generate_report(_fixture_doc())
    assert "llm → tts             10.00 ms" in report


def test_report_handoff_tts_to_playback_correct() -> None:
    """tts.first_audio at 800ms, playback.started at 920ms → 120ms."""
    report = generate_report(_fixture_doc())
    assert "tts → playback        120.00 ms" in report


def test_report_contains_overlap_section() -> None:
    report = generate_report(_fixture_doc())
    assert "Overlap (streaming between stages):" in report
    assert "stt ∥ llm" in report
    assert "llm ∥ tts" in report
    assert "tts ∥ playback" in report


def test_report_overlap_zero_for_sequential_fixture() -> None:
    """The fixture has no streaming overlap — all stages are sequential."""
    report = generate_report(_fixture_doc())
    assert "stt ∥ llm             0.00 ms" in report
    assert "llm ∥ tts             0.00 ms" in report


def test_report_completeness_shown() -> None:
    report = generate_report(_fixture_doc())
    assert "complete" in report
    assert "0 dropped" in report
    assert "0 critical lost" in report


def test_report_from_mock_pipeline() -> None:
    """The report works on the mock pipeline output too."""
    report = generate_report(run_mock_turn())
    assert "stt_latency_ms        309.00 ms" in report
    assert "e2e_latency_ms        2400.00 ms" in report


def test_cli_report_on_fixture() -> None:
    """``vtrace report <fixture>`` exits 0 and prints the report."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = cli_main(["report", str(FIXTURE)])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert rc == 0
    assert "vTrace Report" in output


def test_cli_no_args_returns_usage() -> None:
    rc = cli_main([])
    assert rc == 0


def test_cli_unknown_command_returns_2() -> None:
    rc = cli_main(["frobnicate"])
    assert rc == 2


def test_cli_missing_file_returns_1() -> None:
    rc = cli_main(["report", "/nonexistent/trace.json"])
    assert rc == 1


def test_cli_report_prints_compute_section() -> None:
    """The CLI prints the compute section to stdout."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = cli_main(["report", str(FIXTURE)])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    assert rc == 0
    assert "Compute (stage durations):" in output
    assert "stt_latency_ms" in output

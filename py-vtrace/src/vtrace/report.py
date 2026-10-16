"""Trace report generator (P1-3c, B5).

Reads a trace document (dict) and produces a text report that
distinguishes compute, queue (handoff), and overlap — the P1
acceptance criterion (spec 0009).

Metrics follow spec 0004: every metric is an explicit event pair.
A metric missing an endpoint is ``unavailable`` with the reason —
never substituted (decision 0005, invariant: no metric without an
explicit event pair).

The "handoff" between stages (e.g. ``stt.completed`` →
``llm.started``) is reported separately from the spec-defined
``queue_wait_ms`` (which requires ``*.queued`` events). The fixture
has no queue hooks, so ``queue_wait_ms`` is ``unavailable``; the
handoff is still measurable and useful.
"""

from __future__ import annotations

from typing import Any

from vtrace.lifecycle import analyze_lifecycle, format_lifecycle

_MS = 1_000_000  # ns per ms


def _ms(ns: int) -> float:
    """Nanoseconds → milliseconds (2 decimal places)."""
    return round(ns / _MS, 2)


def _events_by_name(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index events by name. Last occurrence wins (duplicates are kept)."""
    return {ev["name"]: ev for ev in events}


def _metric(
    events: dict[str, dict[str, Any]],
    start_name: str,
    end_name: str,
    label: str,
) -> str:
    """Compute a duration metric from an explicit event pair.

    Returns a formatted string: ``"123.45 ms"`` or
    ``"unavailable (reason)"`` if an endpoint is missing.
    """
    start = events.get(start_name)
    end = events.get(end_name)
    if start is None:
        return f"unavailable (no {start_name})"
    if end is None:
        return f"unavailable (no {end_name})"
    duration_ns = end["timestamp_ns"] - start["timestamp_ns"]
    return f"{_ms(duration_ns):.2f} ms"


def _handoff(
    events: dict[str, dict[str, Any]],
    end_name: str,
    start_name: str,
) -> str:
    """Gap between one stage's end and the next stage's start.

    Returns ``"unavailable (reason)"`` if either event is missing,
    or ``"0.00 ms"`` if they overlap (negative gap).
    """
    end = events.get(end_name)
    start = events.get(start_name)
    if end is None:
        return f"unavailable (no {end_name})"
    if start is None:
        return f"unavailable (no {start_name})"
    gap_ns = start["timestamp_ns"] - end["timestamp_ns"]
    if gap_ns < 0:
        return f"{_ms(gap_ns):.2f} ms (overlap)"
    return f"{_ms(gap_ns):.2f} ms"


def _overlap(
    events: dict[str, dict[str, Any]],
    a_start: str,
    a_end: str,
    b_start: str,
    b_end: str,
) -> str:
    """Compute the overlap between two stage intervals.

    Each stage is defined by a start and end event. If either stage
    is missing an endpoint, the overlap is ``unavailable``. If the
    stages do not overlap, returns ``"0.00 ms"``.
    """
    a_s = events.get(a_start)
    a_e = events.get(a_end)
    b_s = events.get(b_start)
    b_e = events.get(b_end)
    missing = [
        name
        for name, ev in [(a_start, a_s), (a_end, a_e), (b_start, b_s), (b_end, b_e)]
        if ev is None
    ]
    if missing:
        return f"unavailable (no {', '.join(missing)})"
    assert a_s is not None and a_e is not None
    assert b_s is not None and b_e is not None
    start = max(a_s["timestamp_ns"], b_s["timestamp_ns"])
    end = min(a_e["timestamp_ns"], b_e["timestamp_ns"])
    overlap_ns = end - start
    if overlap_ns <= 0:
        return "0.00 ms"
    return f"{_ms(overlap_ns):.2f} ms"


def generate_report(doc: dict[str, Any]) -> str:
    """Generate a text report from a trace document.

    The report distinguishes compute (stage durations), queue
    (handoff between stages), and overlap (streaming overlap between
    stages) — the P1 acceptance criterion (spec 0009).
    """
    events = doc["events"]
    by_name = _events_by_name(events)
    domain = doc["clock_domains"][0] if doc["clock_domains"] else "?"
    completeness = doc["completeness"]
    dropped = doc["dropped_total"]
    dropped_crit = doc["dropped_critical"]

    lines: list[str] = []
    lines.append("vTrace Report")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Clock domain:     {domain}")
    lines.append(
        f"Completeness:     {completeness} ({dropped} dropped, {dropped_crit} critical lost)"
    )
    lines.append(f"Events:           {len(events)}")
    lines.append("")

    # Timeline
    lines.append("Timeline:")
    for ev in events:
        ts = ev["timestamp_ns"]
        seq = ev["sequence"]
        name = ev["name"]
        lines.append(f"  #{seq:<3d} {name:<22s} t={ts:>15,d} ns")
    lines.append("")

    # Compute metrics (spec 0004)
    lines.append("Compute (stage durations):")
    lines.append(
        f"  e2e_latency_ms        {_metric(by_name, 'turn.started', 'turn.completed', 'e2e')}"
    )
    lines.append(
        f"  stt_latency_ms        {_metric(by_name, 'stt.started', 'stt.completed', 'stt')}"
    )
    lines.append(
        f"  llm_ttft_ms           {_metric(by_name, 'llm.started', 'llm.first_token', 'llm')}"
    )
    lines.append(
        f"  tts_ttfa_ms           {_metric(by_name, 'tts.started', 'tts.first_audio', 'tts')}"
    )
    lines.append(
        f"  time_to_audible_ms    {_metric(by_name, 'vad.speech_ended', 'playback.started', 'tta')}"
    )
    lines.append("")

    # Queue / handoff (gaps between stages)
    lines.append("Queue (handoff between stages):")
    lines.append(f"  stt → llm             {_handoff(by_name, 'stt.completed', 'llm.started')}")
    lines.append(f"  llm → tts             {_handoff(by_name, 'llm.first_token', 'tts.started')}")
    lines.append(
        f"  tts → playback        {_handoff(by_name, 'tts.first_audio', 'playback.started')}"
    )
    lines.append("")

    # Overlap (streaming)
    lines.append("Overlap (streaming between stages):")
    ov_stt_llm = _overlap(by_name, "stt.started", "stt.completed", "llm.started", "llm.first_token")
    lines.append(f"  stt ∥ llm             {ov_stt_llm}")
    ov_llm_tts = _overlap(
        by_name, "llm.started", "llm.first_token", "tts.started", "tts.first_audio"
    )
    lines.append(f"  llm ∥ tts             {ov_llm_tts}")
    ov_tts_pb = _overlap(
        by_name, "tts.started", "tts.first_audio", "playback.started", "playback.started"
    )
    lines.append(f"  tts ∥ playback        {ov_tts_pb}")
    lines.append("")

    # Lifecycle (P3, spec 0006) — analysis only, never mutates the document.
    lifecycle = analyze_lifecycle(doc)
    lines.append(format_lifecycle(lifecycle))

    # cancel_latency_ms: cancel.requested → cancel.acknowledged or *.cancelled
    cancel_end = "cancel.acknowledged"
    if "cancel.acknowledged" not in by_name:
        # Prefer the earliest *.cancelled if present.
        cancelled = [ev for ev in events if ev["name"].endswith(".cancelled")]
        cancel_end = cancelled[0]["name"] if cancelled else "cancel.acknowledged"
    lines.append("")
    lines.append("Cancellation:")
    lines.append(
        f"  cancel_latency_ms     {_metric(by_name, 'cancel.requested', cancel_end, 'cancel')}"
    )

    return "\n".join(lines)

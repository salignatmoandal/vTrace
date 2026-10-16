"""Mock voice pipeline that reproduces the fixture trace (P1-3b, B4).

A deterministic, model-free simulation of one voice turn. Uses a
``ManualClock`` (step 0 so ``now_ns()`` returns the set value without
advancing) and the B4 adapters. The resulting trace matches
``fixtures/traces/one-turn.json`` event-for-event.

The pipeline is NOT a real STT/LLM/TTS engine — it advances the clock
to simulate compute durations. Its purpose is to prove the adapters
produce a complete, valid trace document.
"""

from __future__ import annotations

from typing import Any

from vtrace._vtrace import ManualClock
from vtrace.adapters import trace_llm, trace_playback, trace_stt, trace_tts
from vtrace.collector import Collector

# Fixture timeline (ns) — matches fixtures/traces/one-turn.json.
_T_TURN_STARTED = 0
_T_STT_STARTED = 1_000_000
_T_STT_COMPLETED = 310_000_000
_T_LLM_STARTED = 320_000_000
_T_LLM_FIRST_TOKEN = 600_000_000
_T_TTS_STARTED = 610_000_000
_T_TTS_FIRST_AUDIO = 800_000_000
_T_PLAYBACK_STARTED = 920_000_000
_T_TURN_COMPLETED = 2_400_000_000

_SESSION_ID = "sess_1"
_TURN_ID = "turn_42"
_DOMAIN = "manual:turn-42"
_SPAN_TURN = "span_turn"
_SPAN_STT = "span_stt"
_SPAN_LLM = "span_llm"
_SPAN_TTS = "span_tts"
_SPAN_PLAYBACK = "span_playback"


def run_mock_turn() -> dict[str, Any]:
    """Run one mock voice turn and return the trace document dict.

    The document is validated against the Rust contract inside the
    test suite (``test_adapters``).
    """
    clock = ManualClock(_DOMAIN, 0, 0)
    collector = Collector(clock, _SESSION_ID, _TURN_ID)

    # turn.started at t=0
    clock.set(_T_TURN_STARTED)
    collector.record("turn", "turn.started", _SPAN_TURN)

    # STT: started at 1ms, completed at 310ms (309ms compute)
    clock.set(_T_STT_STARTED)
    with trace_stt(collector, _SPAN_STT, _SPAN_TURN):
        clock.set(_T_STT_COMPLETED)
        collector.record(
            "stt",
            "stt.completed",
            _SPAN_STT,
            parent_span_id=_SPAN_TURN,
            backend="fixture",
        )

    # LLM: started at 320ms, first_token at 600ms (streaming, no completed)
    clock.set(_T_LLM_STARTED)
    with trace_llm(collector, _SPAN_LLM, _SPAN_TURN):
        clock.set(_T_LLM_FIRST_TOKEN)
        collector.record(
            "llm",
            "llm.first_token",
            _SPAN_LLM,
            parent_span_id=_SPAN_TURN,
        )

    # TTS: started at 610ms, first_audio at 800ms (streaming, no completed)
    clock.set(_T_TTS_STARTED)
    with trace_tts(collector, _SPAN_TTS, _SPAN_TURN):
        clock.set(_T_TTS_FIRST_AUDIO)
        collector.record(
            "tts",
            "tts.first_audio",
            _SPAN_TTS,
            parent_span_id=_SPAN_TURN,
        )

    # playback: started at 920ms (no completed in fixture)
    clock.set(_T_PLAYBACK_STARTED)
    with trace_playback(collector, _SPAN_PLAYBACK, _SPAN_TURN):
        pass

    # turn.completed at 2400ms
    clock.set(_T_TURN_COMPLETED)
    collector.record("turn", "turn.completed", _SPAN_TURN)

    return collector.flush()

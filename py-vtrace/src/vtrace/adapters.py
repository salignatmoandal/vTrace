"""Pipeline instrumentation adapters (P1-3b, B4).

Thin context managers that emit the lifecycle events for each stage
of a voice turn: STT, LLM, TTS, playback. Each adapter emits
`<component>.started` on enter. The body is responsible for emitting
intermediate events (`llm.first_token`, `tts.first_audio`) and terminal
events (`stt.completed`, `*.completed`) — a streaming pipeline may
not complete a stage before the turn ends, so the adapter does NOT
auto-emit `*.completed` on exit.

Causality is explicit (decision 0005): each stage carries
`parent_span_id` pointing to the turn span. No edge is inferred from
temporal proximity.

Usage (mock pipeline)::

    clock = ManualClock("manual:turn-42", 0, 0)
    c = Collector(clock, "sess_1", "turn_42")

    c.record("turn", "turn.started", "span_turn")
    with trace_stt(c, "span_stt", "span_turn"):
        # ... STT compute ...
        c.record("stt", "stt.completed", "span_stt",
                 parent_span_id="span_turn", backend="fixture")
    with trace_llm(c, "span_llm", "span_turn"):
        # ... LLM compute ...
        c.record("llm", "llm.first_token", "span_llm",
                 parent_span_id="span_turn")
    # ...

Non-goals (P1):
- No real audio capture or VAD.
- No streaming chunk events (P2).
- No cancellation hooks (P3).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def trace_stt(
    collector: Any,
    span_id: str,
    parent_span_id: str,
) -> Iterator[None]:
    """Instrument an STT stage.

    Emits ``stt.started`` on enter. The body should emit
    ``stt.completed`` (or ``stt.failed``) when the stage finishes.
    """
    collector.record("stt", "stt.started", span_id, parent_span_id=parent_span_id)
    yield


@contextmanager
def trace_llm(
    collector: Any,
    span_id: str,
    parent_span_id: str,
) -> Iterator[None]:
    """Instrument an LLM stage.

    Emits ``llm.started`` on enter. The body should emit
    ``llm.first_token`` when the first token arrives and
    ``llm.completed`` (or ``llm.failed``) when generation finishes.
    In a streaming pipeline the stage may not finish before the turn
    ends — that is valid and visible in the trace.
    """
    collector.record("llm", "llm.started", span_id, parent_span_id=parent_span_id)
    yield


@contextmanager
def trace_tts(
    collector: Any,
    span_id: str,
    parent_span_id: str,
) -> Iterator[None]:
    """Instrument a TTS stage.

    Emits ``tts.started`` on enter. The body should emit
    ``tts.first_audio`` when the first audio chunk is synthesized and
    ``tts.completed`` (or ``tts.failed``) when synthesis finishes.
    """
    collector.record("tts", "tts.started", span_id, parent_span_id=parent_span_id)
    yield


@contextmanager
def trace_playback(
    collector: Any,
    span_id: str,
    parent_span_id: str,
) -> Iterator[None]:
    """Instrument a playback stage.

    Emits ``playback.started`` on enter (only when a playback hook
    confirms effective start — spec 0002). The body should emit
    ``playback.completed`` when playback finishes.
    """
    collector.record("playback", "playback.started", span_id, parent_span_id=parent_span_id)
    yield

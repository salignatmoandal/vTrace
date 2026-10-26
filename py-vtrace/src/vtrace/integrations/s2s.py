"""Hugging Face speech-to-speech bridge (P6, adapters-first).

Maps the structural lifecycle of a voice turn onto a vTrace
``Collector``. Designed against the HF ``speech-to-speech`` surfaces
audited for P6:

- ``BaseHandler`` process / emit loop (stage started / first output)
- response latency fields (``stt``, ``llm``, ``tts_ttfa``, ``e2e``)
  as *documentation of boundaries*, not as a silent reconstruction
  of absolute timestamps from durations alone
- ``CancelScope`` / barge-in (``cancel.requested`` → ``*.cancelled``)
- issue `#714` proposed timeline (speech end → STT → LLM → TTS →
  interrupt → cancel → audio stop)

This module does **not** import ``speech_to_speech``. Callers wire
``S2STurnBridge`` methods at stable hook points, or use
``run_s2s_shaped_turn`` for a model-free demo.

Non-goals:
- No audio / transcript / prompt / model text in attributes
  (decision 0004).
- No invented causality between stages (decision 0005).
- No upstream fork; optional HF PR is a later delivery.
"""

from __future__ import annotations

from typing import Any

from vtrace._vtrace import ManualClock
from vtrace.adapters import trace_llm, trace_playback, trace_stt, trace_tts
from vtrace.collector import Collector

_SPAN_TURN = "span_turn"
_SPAN_VAD = "span_vad"
_SPAN_STT = "span_stt"
_SPAN_LLM = "span_llm"
_SPAN_TTS = "span_tts"
_SPAN_PLAYBACK = "span_playback"


class S2STurnBridge:
    """Callback surface for one speech-to-speech turn.

    Each ``on_*`` method records one structural event. Timestamps come
    from the collector clock at call time — callers that need
    deterministic tests should drive a ``ManualClock``.
    """

    def __init__(
        self,
        collector: Collector,
        *,
        turn_span_id: str = _SPAN_TURN,
        response_id: str | None = None,
        producer_id: str | None = None,
    ) -> None:
        self._c = collector
        self._turn = turn_span_id
        self._response_id = response_id
        self._producer_id = producer_id
        self._stt = _SPAN_STT
        self._llm = _SPAN_LLM
        self._tts = _SPAN_TTS
        self._playback = _SPAN_PLAYBACK
        self._vad = _SPAN_VAD

    def _rec(
        self,
        component: str,
        name: str,
        span_id: str,
        *,
        parent: str | None = None,
        **attributes: Any,
    ) -> str | None:
        return self._c.record(
            component,
            name,
            span_id,
            parent_span_id=parent,
            response_id=self._response_id,
            producer_id=self._producer_id,
            **attributes,
        )

    # --- turn / speech -------------------------------------------------

    def on_turn_started(self) -> str | None:
        return self._rec("turn", "turn.started", self._turn)

    def on_speech_ended(self) -> str | None:
        """VAD confirmed end of user speech (``speech.ended`` in #714)."""
        return self._rec(
            "vad",
            "vad.speech_ended",
            self._vad,
            parent=self._turn,
        )

    def on_barge_in(self) -> str | None:
        """User interruption detected while assistant audio may still play.

        Emits ``vad.speech_started`` with ``barge_in=True``. Does not
        imply cancel by itself — call ``on_cancel_requested`` when the
        pipeline actually requests cancellation.
        """
        return self._rec(
            "vad",
            "vad.speech_started",
            self._vad,
            parent=self._turn,
            barge_in=True,
        )

    # --- STT -----------------------------------------------------------

    def on_stt_started(self) -> str | None:
        return self._rec("stt", "stt.started", self._stt, parent=self._turn)

    def on_stt_completed(self, *, backend: str | None = None) -> str | None:
        attrs: dict[str, Any] = {}
        if backend is not None:
            attrs["backend"] = backend
        return self._rec(
            "stt",
            "stt.completed",
            self._stt,
            parent=self._turn,
            **attrs,
        )

    # --- LLM -----------------------------------------------------------

    def on_llm_started(self) -> str | None:
        return self._rec("llm", "llm.started", self._llm, parent=self._turn)

    def on_llm_first_token(self) -> str | None:
        return self._rec(
            "llm",
            "llm.first_token",
            self._llm,
            parent=self._turn,
        )

    def on_llm_completed(self) -> str | None:
        """Generation finished; first token alone does not confirm completion."""
        return self._rec("llm", "llm.completed", self._llm, parent=self._turn)

    def on_llm_cancelled(self) -> str | None:
        return self._rec(
            "llm",
            "llm.cancelled",
            self._llm,
            parent=self._turn,
        )

    # --- TTS -----------------------------------------------------------

    def on_tts_started(self) -> str | None:
        return self._rec("tts", "tts.started", self._tts, parent=self._turn)

    def on_tts_first_audio(self) -> str | None:
        """First model/provider audio chunk (``tts_ttfa`` boundary)."""
        return self._rec(
            "tts",
            "tts.first_audio",
            self._tts,
            parent=self._turn,
        )

    def on_tts_completed(self) -> str | None:
        """Synthesis finished; first audio alone does not confirm completion."""
        return self._rec("tts", "tts.completed", self._tts, parent=self._turn)

    def on_tts_cancelled(self) -> str | None:
        return self._rec(
            "tts",
            "tts.cancelled",
            self._tts,
            parent=self._turn,
        )

    # --- playback / audio output ---------------------------------------

    def on_playback_started(self) -> str | None:
        return self._rec(
            "playback",
            "playback.started",
            self._playback,
            parent=self._turn,
        )

    def on_playback_stopped(self) -> str | None:
        """Server-side audio output stopped (not client render latency)."""
        return self._rec(
            "playback",
            "playback.completed",
            self._playback,
            parent=self._turn,
        )

    # --- cancel --------------------------------------------------------

    def on_cancel_requested(self) -> str | None:
        return self._rec("turn", "cancel.requested", self._turn)

    def on_cancel_acknowledged(self) -> str | None:
        return self._rec("turn", "cancel.acknowledged", self._turn)

    def on_turn_cancelled(self) -> str | None:
        return self._rec("turn", "turn.cancelled", self._turn)

    def on_turn_completed(self) -> str | None:
        return self._rec("turn", "turn.completed", self._turn)

    def flush(self) -> dict[str, Any]:
        return self._c.flush()


# Deterministic interrupt demo timeline (ns), ManualClock step 0.
# Shared prefix through first audio; then either cancel or complete.
_T0 = 0
_T_SPEECH_ENDED = 50_000_000
_T_STT_STARTED = 55_000_000
_T_STT_COMPLETED = 280_000_000
_T_LLM_STARTED = 290_000_000
_T_LLM_FIRST = 450_000_000
_T_TTS_STARTED = 460_000_000
_T_TTS_FIRST = 620_000_000
_T_PLAYBACK = 700_000_000
# Interrupt branch
_T_BARGE = 900_000_000
_T_CANCEL_REQ = 910_000_000
_T_CANCEL_ACK = 920_000_000
_T_LLM_CANCEL = 940_000_000
_T_TTS_CANCEL = 950_000_000
_T_PLAYBACK_STOP_I = 980_000_000
_T_TURN_CANCEL = 1_000_000_000
# Happy-path branch (strictly after first audio / playback start)
_T_LLM_DONE = 800_000_000
_T_TTS_DONE = 1_100_000_000
_T_PLAYBACK_STOP_H = 1_200_000_000
_T_TURN_DONE = 1_300_000_000

_SESSION = "sess_s2s"
_TURN = "turn_s2s_interrupt"
_DOMAIN = "manual:s2s-interrupt"


def run_s2s_shaped_turn(*, interrupted: bool = True) -> dict[str, Any]:
    """Model-free turn shaped like HF speech-to-speech + #714.

    When ``interrupted`` is True, the timeline includes barge-in and
    cancel propagation. When False, stages complete normally (no
    cancel) — useful for a happy-path report.
    """
    clock = ManualClock(_DOMAIN, 0, 0)
    collector = Collector(clock, _SESSION, _TURN)
    bridge = S2STurnBridge(collector, producer_id="s2s-demo")

    clock.set(_T0)
    bridge.on_turn_started()

    clock.set(_T_SPEECH_ENDED)
    bridge.on_speech_ended()

    clock.set(_T_STT_STARTED)
    with trace_stt(collector, _SPAN_STT, _SPAN_TURN):
        clock.set(_T_STT_COMPLETED)
        bridge.on_stt_completed(backend="s2s-demo")

    clock.set(_T_LLM_STARTED)
    with trace_llm(collector, _SPAN_LLM, _SPAN_TURN):
        clock.set(_T_LLM_FIRST)
        bridge.on_llm_first_token()

    clock.set(_T_TTS_STARTED)
    with trace_tts(collector, _SPAN_TTS, _SPAN_TURN):
        clock.set(_T_TTS_FIRST)
        bridge.on_tts_first_audio()

    clock.set(_T_PLAYBACK)
    with trace_playback(collector, _SPAN_PLAYBACK, _SPAN_TURN):
        if interrupted:
            clock.set(_T_BARGE)
            bridge.on_barge_in()
            clock.set(_T_CANCEL_REQ)
            bridge.on_cancel_requested()
            clock.set(_T_CANCEL_ACK)
            bridge.on_cancel_acknowledged()
            clock.set(_T_LLM_CANCEL)
            bridge.on_llm_cancelled()
            clock.set(_T_TTS_CANCEL)
            bridge.on_tts_cancelled()
            clock.set(_T_PLAYBACK_STOP_I)
            bridge.on_playback_stopped()
            clock.set(_T_TURN_CANCEL)
            bridge.on_turn_cancelled()
        else:
            # Streaming overlap: LLM may still be open after TTS started.
            clock.set(_T_LLM_DONE)
            bridge.on_llm_completed()
            clock.set(_T_TTS_DONE)
            bridge.on_tts_completed()
            clock.set(_T_PLAYBACK_STOP_H)
            bridge.on_playback_stopped()
            clock.set(_T_TURN_DONE)
            bridge.on_turn_completed()

    return bridge.flush()

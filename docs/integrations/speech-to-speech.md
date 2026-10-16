# Integration — Hugging Face `speech-to-speech` (P6)

- **Status:** Adapters-first bridge landed in vTrace; live hooks in the
  HF tree are **not** merged upstream yet.
- **Approach.** Prefer a thin callback bridge in this repo over an
  immediate upstream PR (spec 0009 open question). Upstream PR remains
  optional once the demo and hook map are stable.
- **Related:** roadmap P6; phase note
  [`docs/phases/p6-huggingface-integration.md`](../phases/p6-huggingface-integration.md);
  HF issue
  [#714](https://github.com/huggingface/speech-to-speech/issues/714).

## What landed here

| Artifact | Role |
|---|---|
| `vtrace.integrations.s2s.S2STurnBridge` | Callback API → `Collector` |
| `run_s2s_shaped_turn()` | Model-free demo (#714 interrupt shape) |
| `fixtures/traces/s2s-interrupt-turn.json` | Acceptance fixture |
| `just report-s2s` | CLI report on that fixture |

## Hook map (stable surfaces)

Wire `S2STurnBridge` methods at these points; do **not** capture
content (decision 0004).

| s2s surface | Bridge call | vTrace event |
|---|---|---|
| VAD speech end | `on_speech_ended` | `vad.speech_ended` |
| STT handler enter / final | `on_stt_started` / `on_stt_completed` | `stt.*` |
| LLM generate start / first token | `on_llm_started` / `on_llm_first_token` | `llm.*` |
| TTS first yielded audio (`tts_ttfa`) | `on_tts_first_audio` | `tts.first_audio` |
| Playback / output start | `on_playback_started` | `playback.started` |
| Barge-in / interrupt detected | `on_barge_in` | `vad.speech_started` + `barge_in` |
| CancelScope request / ack | `on_cancel_requested` / `on_cancel_acknowledged` | `cancel.*` |
| Stage discard on cancel | `on_llm_cancelled` / `on_tts_cancelled` | `*.cancelled` |
| Audio output stopped | `on_playback_stopped` | `playback.completed` |
| Turn terminal | `on_turn_cancelled` / `on_turn_completed` | `turn.*` |

Natural code anchors in
[`huggingface/speech-to-speech`](https://github.com/huggingface/speech-to-speech):

- `baseHandler.py` — `process` / emit loop, cancel-scope stale drop
- Realtime response latency tracker (#539 / #590) — stage boundaries
- `CancelScope` / speculative turn ownership — cancel pairs

## Latency aggregates vs timeline

s2s already logs `stt`, `llm`, `tts_ttfa`, `e2e` (#590). Those
durations **overlap** and are not an additive breakdown. vTrace does
**not** reverse-engineer absolute event timestamps from durations
alone (that would invent a timeline). Prefer emitting events at the
hook; use aggregates as cross-checks only.

## Demo

```bash
just report-s2s
# or:
cd py-vtrace && uv run vtrace report ../fixtures/traces/s2s-interrupt-turn.json
```

## Limits

- No dependency on installing `speech-to-speech` inside vTrace CI.
- Live instrumentation requires a toggleable wrapper or a small
  upstream PR — out of scope for this adapters-first slice.
- No overhead claim until P5.

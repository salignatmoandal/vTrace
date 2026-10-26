# P6 cancellation evidence

Reviewed: 2026-10-26. Scope: model-free adapter acceptance tests, not live
HF integration or a performance measurement.

## Why this slice

[HF issue #714](https://github.com/huggingface/speech-to-speech/issues/714)
is open as checked on 2026-10-26. Its maintainer response asks whether
interrupt diagnostics justify implementation complexity, given that
streaming handlers may be in different states at interruption. This
supports testing a narrow observable distinction before adding more hooks:
a cancel request is different from an effective stage stop.

The bridge uses existing events and lifecycle semantics from
[spec 0006](../specs/0006-lifecycle-and-cancellation.md). The new
`on_llm_completed()` and `on_tts_completed()` callbacks emit the already
supported terminal events with the bridge's producer, response and parent
identity. First token and first audio remain intermediate observations.
No trace schema, metric or state transition changes are introduced.

## Reproducible comparison

From the repository root:

```bash
cd py-vtrace
uv run pytest -q tests/test_s2s_bridge.py tests/test_s2s_cancellation.py
uv run vtrace report ../fixtures/traces/s2s-interrupt-turn.json
uv run vtrace report ../fixtures/traces/s2s-unconfirmed-cancel.json
uv run python -m vtrace.validate ../fixtures/traces/s2s-unconfirmed-cancel.json
```

Both fixtures use explicit manual-clock observations. Their times are
synthetic acceptance data, not measured runtime latency.

| Evidence | Confirmed interrupt fixture | Unconfirmed cancel fixture |
|---|---|---|
| Cancel requested | yes | yes |
| Cancel acknowledged | yes | no |
| Turn state | `turn.cancelled` | `started` |
| LLM/TTS terminal | `*.cancelled` | absent; `orphaned_after_cancel` |
| Cancel latency | available from explicit pair | `unavailable` |
| Playback observation | present | absent; audibility unavailable |
| Critical event loss | none | none |

`completeness: complete` means no critical event was lost. It does not
mean that a turn completed or cancellation succeeded. The unconfirmed
fixture deliberately retains open stages. The tests also cover barge-in
without cancellation, acknowledgement without task termination, callback
identity, and visible critical loss under buffer saturation.

## Requirements for the live follow-up

- Record request, acknowledgement and each stage terminal only where
  the pipeline confirms that observation. A request hook must not emit
  acknowledgement or stage-stop events automatically.
- Keep cancellation ownership scoped to its session/turn/response.
  A process-wide last-cancel timestamp cannot identify the target turn.
- Record playback separately from first synthesized audio. Missing
  playback hooks leave audibility unavailable.
- Preserve missing events and explicit-edge uncertainty. Aggregate
  durations alone do not establish causal links between stages.
- Export pending observations at shutdown without labelling all open
  tasks cancelled. Exit alone does not confirm task termination.

Python's [`atexit` documentation](https://docs.python.org/3/library/atexit.html)
states that callbacks run at normal interpreter shutdown, with exceptions
for unhandled signals, fatal interpreter errors and `os._exit()`. A shutdown
export is therefore best effort, and is not proof of cancellation.

Next acceptance step: obtain a real interrupted-turn trace with separate
request and effective-stop observations, instrumentation enabled/disabled,
and no voice content. That requires an actual HF runtime test; the fixtures
and unit tests here do not establish live compatibility. P6 remains open.
P5 overhead and throughput measurements remain separate work.

## Observed validation (2026-10-26)

- `just ci`: passed, including Rust fmt/clippy/tests/layers, Ruff,
  Pyright (0 errors), 88 Python tests and acceptance schema validation.
- Focused bridge/cancellation suite: 11 passed, including six new tests.
- `vtrace report` and `python -m vtrace.validate` succeeded for both
  `fixtures/traces/s2s-interrupt-turn.json` and
  `fixtures/traces/s2s-unconfirmed-cancel.json`.

These results establish deterministic adapter behavior. They do not
measure profiler overhead or prove a real microphone/barge-in session.

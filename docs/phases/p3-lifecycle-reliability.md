# P3 — Lifecycle Reliability

- **Status (implementation):** Complete
- **Depends on:** P1, P2
- **Specs:** 0002 (§ lifecycle), 0003 (cancel / barge-in), 0006
  (terminals)
- **Decisions:** 0004 (no voice content), 0005

## 1. Scientific problem

In an interactive voice agent, the user may **interrupt** (barge-in)
or the system may **cancel** a stage in flight. Without a formal
lifecycle model, two failures are common:

1. **False negatives:** an interrupted turn is reported as a “normal”
   success;
2. **False positives:** latency is computed on a phantom path
   (work that was cancelled but still counted).

Real-time stacks (e.g. HF speech-to-speech) already introduce
`CancelScope` and turn-latency stores: the *engineering* recognition
exists; what is missing is a **trace contract** that makes anomalies
auditable *ex post*.

## 2. Operational definition

**P3** reconstructs, from events alone, the *state* of each span
(`stt`, `llm`, `tts`, `playback`, `turn`) and detects **anomalies**:

| Anomaly | Meaning |
|---|---|
| `orphan_started` | `started` without `completed` / `cancelled` / `failed` |
| `orphan_completed` | terminal without `started` |
| `double_terminal` | two terminals for the same span |
| `inconsistent_cancel` | cancel without a coherent pair |

Analysis runs **off the hot path** (`record()` stays non-blocking).

**P3 is not:** inventing causal edges between stages (P4); measuring
profiler overhead (P5).

## 3. Foundations

### Explicit cancel vs temporal proximity

In concurrent systems, *causal* order is not *temporal* order ([Crafa
& Russo, 2013, arXiv:1303.1384](https://arxiv.org/abs/1303.1384)). P3
therefore relies only on *named* events (`*.cancelled`,
`*.cancel_requested`, `barge_in`), never on “A finished ~ before B
started”.

### Privacy and content

Decision 0004 forbids collecting audio / transcript / prompt by
default. Lifecycle (who cancelled whom) is *structural* metadata —
compatible with privacy constraints while remaining diagnostic.

## 4. vTrace contracts

| Element | Role in P3 |
|---|---|
| Spec 0002 | Incomplete / cancelled / interrupted paths |
| Spec 0003 | Cancel / barge-in event families |
| Spec 0006 | Terminals: `completed` / `cancelled` / `failed` / `interrupted` |
| Decision 0005 | No edge from proximity |

## 5. Method and deliverable

- `lifecycle.py`: finite-state reconstruction + anomaly list.
- Report section: *Lifecycle anomalies*.
- Deterministic tests (manual clock): orphan, double terminal, cancel
  pair.
- **Deliverable:** anomalies listed; incomplete path remains
  exportable (`completeness: partial`).

## 6. Status and limits

Implemented. Limit: without cancel instrumentation in the target
pipeline, P3 reports *absence of evidence*, not *absence of cancel*.

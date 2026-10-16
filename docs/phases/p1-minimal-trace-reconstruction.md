# P1 — Minimal Trace Reconstruction

- **Status (implementation):** Complete (MVP)
- **Depends on:** P0 (contracts Accepted)
- **Specs:** 0001, 0003, 0004, 0005 (bounds), 0006 (terminals), 0009
- **Decisions:** 0001, 0003, 0004, 0006

## 1. Scientific problem

A real-time voice pipeline (STT → LLM → TTS → playback) produces a
*perceived* latency that cannot be reduced to a single scalar. Recent
work on *voice-to-voice* architectures shows that latency levers are
**component-specific**: ASR, dialogue management, and TTS contribute
unequally to the Real-Time Factor (RTF), with TTS often dominant
([Purwar & Choudhary, 2025, arXiv:2509.20971](https://arxiv.org/abs/2509.20971)).

Without faithful reconstruction of an **event timeline**, optimization
remains anecdotal: one cannot tell *where* time was spent, nor whether
measurement boundaries are comparable across runs.

## 2. Operational definition

**P1** establishes that one can:

1. **Observe** a speech turn as an ordered sequence of timestamped
   events within an explicit clock domain;
2. **Export** that observation as a validatable JSON document (the
   *contract*);
3. **Report** compute, handoff, and overlap from *explicit event
   pairs*, never invented metrics.

**P1 is not:** a causal graph (P4), an overhead benchmark (P5), or
integration with a real HF pipeline (P6).

## 3. Foundations

### Observability via traces

The industrial *distributed tracing* paradigm (e.g. Dapper) separates
*instrumentation* from *analysis*: truth is a collection of exported
events / spans, not the collector’s internal state. vTrace adopts the
same separation: the trace document is the contract (decision 0006).

### Audio measurement boundaries

Spec 0002 requires distinguishing *first synthesized audio*
(`tts.first_audio`), *device submission*, and *audible start*
(`playback.started`). Conflating these instants corrupts
*time-to-audible* — a classic error in low-latency streaming systems
([Quamer & Gutierrez-Osuna, 2024,
arXiv:2406.09277](https://arxiv.org/abs/2406.09277)).

### Pipeline vs E2E

Cascaded architectures (ASR then NLU/LLM then TTS) suffer cascade
error and additive latency; E2E approaches change that profile
([Desot et al., 2022, arXiv:2207.08179](https://arxiv.org/abs/2207.08179)).
P1 provides a shared language to *compare* those profiles without
presupposing the architecture.

## 4. vTrace contracts

| Element | Role in P1 |
|---|---|
| Event schema (0003) | Identity, `sequence`, STT/LLM/TTS families |
| Clock (0004) | `now_ns` + `clock_domain`; manual clock for tests |
| Bounded collector (0005) | Non-blocking `record()`; visible loss |
| JSON document (0006) | Contract consumable by CLI / tests |
| Rust runtime + Python facade (dec. 0001) | Typed core; user-facing adapters in Python |

## 5. Method and deliverable

- **Deterministic fixture** (`fixtures/traces/one-turn.json`) + manual
  clock.
- **CLI** `vtrace report`: compute / queue (handoff) / overlap.
- **Acceptance criterion:** a replayable fixture yields a
  deterministic trace; loss of a critical event is visible
  (`completeness`, `dropped_critical`).

**Demonstrable deliverable:** `vtrace report` on a fixture — the
smallest publishable version (spec 0009).

## 6. Status and limits

Implemented: `vtrace-core`, PyO3 bindings, collector, adapters, mock
pipeline, CLI report. Assumed limit: single-producer at the origin of
P1; multi-producer formalized in P2.

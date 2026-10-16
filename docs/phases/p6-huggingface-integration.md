# P6 — Hugging Face Integration

- **Status (implementation):** Upcoming (s2s audit done; hooks not
  landed)
- **Depends on:** P1–P4 (instrumentation + analysis); P5 recommended
  before production claims
- **Specs:** 0002 (voice boundaries), 0009 (demo), roadmap P6
- **Decisions:** 0004 (privacy), 0006 (document as contract)

## 1. Scientific problem

Open-source reference stacks for *speech-to-speech* (e.g. Hugging Face
`speech-to-speech`) already implement STT / LLM / TTS, cancel scopes,
and informal latency stores. What they typically lack is a **shared,
validatable contract** of events and clocks that lets an external
observer:

1. compare two runs without reading proprietary logs;
2. distinguish synthesis, device submission, and audible start;
3. export a document consumable by analysis tools (critical path,
   lifecycle).

Real-time E2E dialogue systems publish sub-second targets and
streaming semantics ([Chen et al., 2026,
arXiv:2601.11141](https://arxiv.org/abs/2601.11141)). Integration must
respect those budgets: hooks must remain off the critical synthesis
path as much as possible (cf. P5).

## 2. Operational definition

**P6** connects vTrace to a **real** HF voice pipeline by:

1. placing **adapters** on documented lifecycle points (`BaseHandler`,
   queue boundaries, TTS / playback callbacks, `CancelScope`);
2. exporting a turn as a JSON document conforming to
   `docs/schema/trace.schema.json`;
3. demonstrating a **demo** (spec 0009): fixture or live turn →
   `vtrace report` with compute / handoff / overlap / critical path /
   anomalies.

**P6 is not:** forking HF to change model quality; collecting
transcripts or audio by default (decision 0004); claiming OTel
compatibility as the primary contract (decision 0006 — OTel remains a
*future export*).

## 3. Foundations

### Streaming spoken dialogue

Chroma 1.0 and related systems motivate *end-to-end* measurement of
spoken dialogue ([Chen et al., 2026](https://arxiv.org/abs/2601.11141)).
P6 is the empirical activation of P1–P4 metrics on such a stack.

### Privacy

Decision 0004: no raw audio, transcription, prompt, or model response
in `attributes` by default. HF integration must emit **structural**
events (started / first_token / first_audio / cancelled), not content.

### Audit (prior work)

The HF `speech-to-speech` audit identified: `BaseHandler`,
`CancelScope`, `TurnLatencyStore`, and queue boundaries as natural
hook points — aligned with P2–P3 event families.

## 4. vTrace contracts

| Element | Role in P6 |
|---|---|
| Spec 0002 | STT / LLM / TTS / playback boundaries |
| Spec 0009 | Demo: one turn → report |
| Adapters (`adapters.py`) | Thin wrappers already used on the mock pipeline |
| Schema | Validation of every exported document |

## 5. Method and deliverable (planned)

- Minimal patches / wrappers around HF handlers (no content capture).
- Replayable demo script + optional live turn.
- Gate: schema validation + `vtrace report` on the produced document.
- **Deliverable:** a partner can run the demo and answer: *where is
  time spent on this turn?*

## 6. Status and limits

Audit complete; instrumentation not landed. Until P6, demos use the
**mock pipeline** (P1). Live adoption remains gated on hooks +, for
any overhead claim, on P5.

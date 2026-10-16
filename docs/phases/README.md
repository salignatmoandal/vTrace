# Phases P1–P6 — Academic notes

- **Last reviewed:** 2026-10-16
- **Purpose.** Present, in an academic register, the *problem*,
  *definition*, *foundations*, *deliverable*, and *status* of each
  vTrace roadmap phase (P1 through P6).
- **Primary sources.** Specs `0001`–`0009`, decisions `0001`–`0006`,
  [`docs/roadmap.md`](../roadmap.md).
- **Secondary sources.** Literature (arXiv and related corpus) cited
  in each note and in the bibliography below.

These notes do **not** replace the specs: they *interpret* them for a
reader (researcher, reviewer, partner) who needs the *why* before the
*how*.

| Phase | Note | Implementation status (2026-10-16) |
|---|---|---|
| P1 | [Minimal trace reconstruction](p1-minimal-trace-reconstruction.md) | Done (MVP) |
| P2 | [Streaming and queues](p2-streaming-and-queues.md) | Done (multi-producer) |
| P3 | [Lifecycle reliability](p3-lifecycle-reliability.md) | Done |
| P4 | [Causal analysis](p4-causal-analysis.md) | Done |
| P5 | [Benchmarking and overhead](p5-benchmarking-and-overhead.md) | Upcoming |
| P6 | [Hugging Face integration](p6-huggingface-integration.md) | Adapters-first bridge + fixture; upstream hooks pending |

## Common structure of each note

1. **Scientific problem** — what question the phase addresses.
2. **Operational definition** — what the phase *is* and *is not*.
3. **Foundations and literature** — academic / industrial anchors.
4. **vTrace contracts** — relevant specs and decisions.
5. **Method and deliverable** — completion criterion.
6. **Status and limits** — what is proven vs expected.

## Selective bibliography (arXiv)

Retrieved via the arXiv index (2026-10-16). Links point to
`https://arxiv.org/abs/<id>`.

| Ref. | Title | Link | Relevance to vTrace |
|---|---|---|---|
| Purwar & Choudhary, 2025 | *i-LAVA: Insights on Low Latency Voice-2-Voice Architecture for Agents* | [2509.20971](https://arxiv.org/abs/2509.20971) | ASR / dialogue / TTS breakdown; RTF lever (often TTS) — motivates P1 metrics and P5 overhead. |
| Chen et al., 2026 | *FlashLabs Chroma 1.0: Real-Time End-to-End Spoken Dialogue* | [2601.11141](https://arxiv.org/abs/2601.11141) | Sub-second latency targets; text–audio streaming — motivates P2 overlap and P6. |
| Crafa & Russo, 2013 | *Causality in concurrent systems* | [1303.1384](https://arxiv.org/abs/1303.1384) | Causality vs concurrency; *ex post* execution-trace analysis — motivates P4 / decision 0005. |
| Wodislawski & Morrison, 2026 | *PonyTail: Profiling and Improving Service Tail Latency* | [2610.04615](https://arxiv.org/abs/2610.04615) | Profiling the *tail* (p99) rather than the mean — motivates P5 percentiles. |
| Han et al., 2015 | *PCS: Predictive Component-level Scheduling for Reducing Tail Latency* | [1511.02960](https://arxiv.org/abs/1511.02960) | End-to-end latency as composition of components; bottlenecks often stragglers — motivates P4 distinct paths. |
| Quamer & Gutierrez-Osuna, 2024 | *End-to-end streaming model for low-latency speech anonymization* | [2406.09277](https://arxiv.org/abs/2406.09277) | Low-latency streaming (tens–hundreds of ms) — context for P2 / P6. |
| Desot et al., 2022 | *End-to-End Spoken Language Understanding* | [2207.08179](https://arxiv.org/abs/2207.08179) | Pipeline cascade error ASR→NLU vs E2E — analogy for measuring each boundary (P1). |

### Industrial references (non-arXiv, context)

- Sigelman et al., *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure* (Google, 2010) — *trace document* and span paradigm.
- OpenTelemetry Specification — span export and semantics; vTrace treats OTel as a *future consumer*, not as the contract (decision 0006).

## How to cite this folder

> vTrace Project. *Phases P1–P6 — Academic phase notes.* Technical
> documentation, 2026. Specs 0001–0009; decisions 0001–0006.

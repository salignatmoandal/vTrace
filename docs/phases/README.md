# Phases P1–P6 — Documentation académique

- **Last reviewed:** 2026-10-16
- **Purpose.** Exposer, sur un ton académique, le *problème*, la *définition*,
  les *fondements*, le *livrable* et le *statut* de chaque phase du roadmap
  vTrace (P1 à P6).
- **Sources primaires.** Specs `0001`–`0009`, décisions `0001`–`0006`,
  [`docs/roadmap.md`](../roadmap.md).
- **Sources secondaires.** Littérature (arXiv et corpus voisin) citée
  dans chaque fiche et dans la bibliographie ci-dessous.

Ces fiches ne remplacent pas les specs : elles les *interprètent* pour
un lecteur (chercheur, reviewer, partenaire) qui cherche le *pourquoi*
avant le *comment*.

| Phase | Fiche | Statut d’implémentation (2026-10-16) |
|---|---|---|
| P1 | [Minimal trace reconstruction](p1-minimal-trace-reconstruction.md) | Fait (MVP) |
| P2 | [Streaming and queues](p2-streaming-and-queues.md) | Fait (multi-producer) |
| P3 | [Lifecycle reliability](p3-lifecycle-reliability.md) | Fait |
| P4 | [Causal analysis](p4-causal-analysis.md) | Fait |
| P5 | [Benchmarking and overhead](p5-benchmarking-and-overhead.md) | À venir |
| P6 | [Hugging Face integration](p6-huggingface-integration.md) | À venir (audit s2s effectué) |

## Structure commune de chaque fiche

1. **Problème scientifique** — quelle question la phase adresse.
2. **Définition opérationnelle** — ce que la phase *est* et *n’est pas*.
3. **Fondements et littérature** — ancrage académique / industriel.
4. **Contrats vTrace** — specs et décisions concernées.
5. **Méthode et livrable** — critère de complétion.
6. **Statut et limites** — ce qui est prouvé vs attendu.

## Bibliographie sélective (arXiv)

Consultée via l’index arXiv (2026-10-16). Les liens pointent vers
`https://arxiv.org/abs/<id>`.

| Réf. | Titre | Lien | Pertinence pour vTrace |
|---|---|---|---|
| Purwar & Choudhary, 2025 | *i-LAVA: Insights on Low Latency Voice-2-Voice Architecture for Agents* | [2509.20971](https://arxiv.org/abs/2509.20971) | Décomposition ASR / dialogue / TTS ; levier RTF (surtout TTS) — motive P1 métriques et P5 overhead. |
| Chen et al., 2026 | *FlashLabs Chroma 1.0: Real-Time End-to-End Spoken Dialogue* | [2601.11141](https://arxiv.org/abs/2601.11141) | Object cible sub-seconde ; streaming text–audio — motive P2 overlap et P6. |
| Crafa & Russo, 2013 | *Causality in concurrent systems* | [1303.1384](https://arxiv.org/abs/1303.1384) | Causalité vs concurrence ; analyse *ex post* de traces d’exécution — motive P4 / décision 0005. |
| Wodislawski & Morrison, 2026 | *PonyTail: Profiling and Improving Service Tail Latency* | [2610.04615](https://arxiv.org/abs/2610.04615) | Profiling du *tail* (p99) plutôt que de la moyenne — motive P5 percentiles. |
| Han et al., 2015 | *PCS: Predictive Component-level Scheduling for Reducing Tail Latency* | [1511.02960](https://arxiv.org/abs/1511.02960) | Latence de queue = composition de composants ; le goulot est souvent un straggler — motive P4 chemins distincts. |
| Quamer & Gutierrez-Osuna, 2024 | *End-to-end streaming model for low-latency speech anonymization* | [2406.09277](https://arxiv.org/abs/2406.09277) | Streaming à faible latence (dizaines–centaines de ms) — contexte P2 / P6. |
| Desot et al., 2022 | *End-to-End Spoken Language Understanding* | [2207.08179](https://arxiv.org/abs/2207.08179) | Cascade d’erreurs pipeline ASR→NLU vs E2E — analogie pour mesurer chaque frontière (P1). |

### Références industrielles (hors arXiv, contexte)

- Sigelman et al., *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure* (Google, 2010) — paradigme du *trace document* et des spans.
- OpenTelemetry Specification — export et sémantique de spans ; vTrace traite OTel comme *consommateur futur*, non comme contrat (décision 0006).

## Comment citer ce dossier

> vTrace Project. *Phases P1–P6 — Academic phase notes.* Technical
> documentation, 2026. Specs 0001–0009; decisions 0001–0006.

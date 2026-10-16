# P4 — Causal Analysis

- **Status (implementation):** Complete
- **Depends on:** P2, P3
- **Specs:** 0007 (primaire), 0003, 0005, 0006
- **Decisions:** 0005 (centrale)

## 1. Problème scientifique

Une timeline ordonnée n’est pas un **graphe de dépendances**. Sommer
les durées de stages sous-estime (ou surestime) la latence lorsque les
stages se chevauchent. Inversement, inférer une arête parce que deux
événements sont proches dans le temps produit un chemin critique
*plausible mais faux* — particulièrement dangereux en concurrence
([Crafa & Russo, 2013, arXiv:1303.1384](https://arxiv.org/abs/1303.1384)).

Les objectifs de latence d’un tour vocal sont **multiples** et non
interchangeables :

| Objectif | Événement terminal typique |
|---|---|
| TTFT | `llm.first_token` |
| TTFA | `tts.first_audio` |
| Time-to-audible | `playback.started` (après `vad.speech_ended`) |
| Fin de tour | `turn.completed` (ou autre terminal) |

Les systèmes multi-composants rappellent que la latence globale est
souvent celle du chemin le plus long dans un graphe de dépendances,
pas la somme des moyennes ([Han et al., 2015,
arXiv:1511.02960](https://arxiv.org/abs/1511.02960)).

## 2. Définition opérationnelle

**P4** construit un **DAG** à partir d’arêtes *explicites uniquement* :

- `parent_span_id` (entrée de span enfant) ;
- chaîne de lifecycle *same-span* ;
- `*.queued` → `*.started` ;
- `cancel.requested` → `*.cancelled`.

Puis calcule, **par objectif**, un chemin critique avec confiance
`complete | partial | unavailable`. L’absence d’évidence produit
`partial` / `unavailable` **avec raison**, jamais un chemin fabriqué
(décision 0005).

**P4 n’est pas :** un export OTel, ni un benchmark (P5).

## 3. Fondements

### Graphe vs timeline

La spec 0007 formalise la séparation : la timeline répond à « dans
quel ordre ? » ; le DAG répond à « qu’est-ce qui *doit* précéder
quoi ? ». Les deux coexistent dans le rapport CLI.

### Conservatisme épistémique

Préférer un résultat incomplet à une fausse certitude est un choix
méthodologique aligné sur la validation causale : on ne masque pas le
manque d’évidence derrière un score de confiance opaque (alternative
rejetée en spec 0007).

## 4. Contrats vTrace

| Élément | Rôle en P4 |
|---|---|
| Spec 0007 | `build_graph`, `critical_path(objective)` |
| Décision 0005 | Interdit l’inférence par proximité |
| Crate `vtrace-analysis` (L1) | Implémentation typée ; exposée via PyO3 |

## 5. Méthode et livrable

- Rust : `vtrace-analysis::{build_graph, critical_paths}`.
- Python : `vtrace.causal` + section « Critical paths » du rapport.
- Sur la fixture sans `*.queued` : chemins **partial** avec
  `missing queue edge` — résultat *attendu*, non un échec.
- **Livrable :** rapport de chemin critique sur une trace reconstruite.

## 6. Statut et limites

Implémenté. Limite : sans hooks de file (P6), les chemins restent
souvent `partial` — c’est la preuve que le système refuse de mentir.

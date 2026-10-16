# P1 — Minimal Trace Reconstruction

- **Status (implementation):** Complete (MVP)
- **Depends on:** P0 (contracts Accepted)
- **Specs:** 0001, 0003, 0004, 0005 (bornes), 0006 (terminaux), 0009
- **Decisions:** 0001, 0003, 0004, 0006

## 1. Problème scientifique

Un pipeline voix temps réel (STT → LLM → TTS → playback) produit une
latence *perçue* qui n’est pas réductible à un unique scalaire. La
littérature récente sur les architectures *voice-to-voice* montre que
les leviers de latence sont **composants-spécifiques** : ASR, gestion
de dialogue et TTS contribuent inégalement au *Real-Time Factor*
(RTF), le TTS étant souvent dominant
([Purwar & Choudhary, 2025, arXiv:2509.20971](https://arxiv.org/abs/2509.20971)).

Sans reconstruction fidèle d’une **timeline d’événements**, toute
optimisation reste une anecdote : on ne sait pas *où* le temps a été
dépensé, ni si les frontières de mesure sont comparables d’un run à
l’autre.

## 2. Définition opérationnelle

**P1** est la phase qui établit qu’on peut :

1. **Observer** un tour de parole comme une séquence ordonnée
   d’événements horodatés dans un domaine d’horloge explicite ;
2. **Exporter** cette observation comme un document JSON validable
   (le *contrat*) ;
3. **Rapporter** compute, handoff et overlap à partir de *paires
   d’événements explicites*, jamais de métriques inventées.

**P1 n’est pas :** un graphe causal (P4), un benchmark d’overhead
(P5), ni une intégration à un pipeline HF réel (P6).

## 3. Fondements

### Observabilité par traces

Le paradigme industriel du *distributed tracing* (ex. Dapper) sépare
l’*instrumentation* de l’*analyse* : la vérité est une collection
d’événements / spans exportés, pas l’état interne du collecteur.
vTrace adopte la même séparation : le document de trace est le contrat
(décision 0006).

### Frontières de mesure audio

La spec 0002 exige de distinguer *premier audio synthétisé*
(`tts.first_audio`), *soumission au device*, et *début audible*
(`playback.started`). Conflater ces instants fausse la notion de
*time-to-audible* — erreur classique dans les systèmes streaming
basse latence ([Quamer & Gutierrez-Osuna, 2024,
arXiv:2406.09277](https://arxiv.org/abs/2406.09277)).

### Pipeline vs E2E

Les architectures en cascade (ASR puis NLU/LLM puis TTS) subissent un
effet de *cascade d’erreurs* et de latences additives ; les approches
E2E modifient ce profil ([Desot et al., 2022,
arXiv:2207.08179](https://arxiv.org/abs/2207.08179)). P1 fournit le
langage commun pour *comparer* ces profils sans présupposer
l’architecture.

## 4. Contrats vTrace

| Élément | Rôle en P1 |
|---|---|
| Schéma d’événements (0003) | Identité, `sequence`, familles STT/LLM/TTS |
| Horloge (0004) | `now_ns` + `clock_domain` ; horloge manuelle pour tests |
| Collecteur borné (0005) | `record()` non bloquant ; perte visible |
| Document JSON (0006) | Contrat consommable par CLI / tests |
| Runtime Rust + façade Python (déc. 0001) | Cœur typé ; adaptateurs utilisateur en Python |

## 5. Méthode et livrable

- **Fixture déterministe** (`fixtures/traces/one-turn.json`) + horloge
  manuelle.
- **CLI** `vtrace report` : compute / queue (handoff) / overlap.
- **Critère d’acceptance :** une fixture rejouable produit une trace
  déterministe ; la perte d’un événement critique est visible
  (`completeness`, `dropped_critical`).

**Livrable démontrable :** `vtrace report` sur une fixture — plus petite
version publiable (spec 0009).

## 6. Statut et limites

Implémenté : `vtrace-core`, bindings PyO3, collecteur, adaptateurs,
mock pipeline, CLI report. Limite assumée : single-producer à
l’origine de P1 ; multi-producteur formalisé en P2.

# P5 — Benchmarking and Overhead

- **Status (implementation):** Not started
- **Depends on:** P1, P2 (idéalement traces stables)
- **Specs:** 0008 (primaire), 0004 (`instrumentation_overhead_ns`)
- **Decisions:** aucune nouvelle décision requise a priori ; un seuil
  d’acceptance, s’il existe, **doit** passer par une décision (0008)

## 1. Problème scientifique

Dès qu’un outil d’instrumentation existe, deux questions empiriques
s’imposent :

1. **Quel est le coût de l’observation ?** (`record()` ajoute-t-il
   une latence ou une pression mémoire non négligeable ?)
2. **Un changement (modèle, backend, config) est-il une régression ?**

Sans protocole, les réponses sont des *anecdotes* : un run unique, une
moyenne qui masque la queue, un mélange entre variabilité du modèle et
overhead du profiler. La littérature sur le *tail latency* insiste sur
les percentiles (p95/p99) plutôt que sur la moyenne
([Wodislawski & Morrison, 2026, arXiv:2610.04615](https://arxiv.org/abs/2610.04615) ;
[Han et al., 2015, arXiv:1511.02960](https://arxiv.org/abs/1511.02960)).

Dans le domaine voice-to-voice, optimiser le RTF exige d’isoler le
levier dominant (souvent TTS)
([Purwar & Choudhary, 2025, arXiv:2509.20971](https://arxiv.org/abs/2509.20971))
— ce qui suppose des mesures **répétées** et **comparables**.

## 2. Définition opérationnelle

**P5** est la phase qui définit et exécute un **protocole de
benchmark** :

| Élément | Contenu |
|---|---|
| Baseline | Pipeline *sans* vTrace (ou instrumentation off) |
| Candidate | Même pipeline *avec* vTrace |
| Warmup | Runs explicites, exclus des statistiques |
| Répétitions | Nombre fixe ; reporting p50 / p95 / p99 |
| Métadonnées | CPU / MPS / OS / versions modèles / backends |
| Séparation | Overhead profiler vs variabilité modèle |
| Artefact | Rapport de comparaison (hors document de trace) |

**P5 n’est pas :** l’intégration HF (P6). Les benches ne tournent
**pas** dans le gate `ci` par défaut (spec 0008) — cible `bench`
séparée.

## 3. Fondements

### Mesure vs affirmation

Invariant du projet : *aucune claim de performance sans benchmark
exécuté*. Cela s’oppose à l’hypothèse « Rust élimine l’overhead » :
l’overhead doit être **mesuré** (`instrumentation_overhead_ns`).

### Noise sur accélérateurs hétérogènes

Sur Apple Silicon (MPS), warmup et charge CPU introduisent du bruit.
Le protocole exige de le documenter plutôt que de le nier — aligné
avec les bonnes pratiques de reporting de latence de service.

## 4. Contrats vTrace

| Élément | Rôle en P5 |
|---|---|
| Spec 0008 | Couches de test ; protocole ; percentiles |
| Spec 0004 | Métrique d’overhead comme paire baseline/candidate |
| Décision 0002 | Seuil d’acceptance = décision explicite |

## 5. Méthode et livrable (cible)

- Harness type `cargo bench` / Criterion (ouvert en 0008) et/ou
  protocole Python pour le hot path `record()`.
- Rapport baseline vs candidate avec métadonnées et chemin vers les
  résultats bruts.
- **Livrable démontrable :** rapport de comparaison reproductible.

## 6. Statut et limites

Non implémenté. Dépend de P1–P2 pour un collecteur stable ; un pipeline
réel (P6) enrichit les benches « modèle », mais l’overhead *pur* du
collecteur peut être mesuré dès P5 sur un mock.

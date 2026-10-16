# P2 — Streaming and Queues

- **Status (implementation):** Complete (multi-producer collector)
- **Depends on:** P1
- **Specs:** 0002, 0005, 0008 (concurrency tests)
- **Decisions:** 0005 (pas d’inférence), 0006

## 1. Problème scientifique

Les pipelines voix modernes sont **concurrents** : VAD, STT, LLM, TTS
et playback s’exécutent sur des threads distincts, reliés par des files.
Les systèmes *spoken dialogue* temps réel visent une latence
bout-en-bout sub-seconde et un *streaming* text–audio entrelacé
([Chen et al., 2026, arXiv:2601.11141](https://arxiv.org/abs/2601.11141)).
Dans ce régime, deux phénomènes dominent l’erreur de mesure :

1. **Handoff / file d’attente** — le temps entre la fin d’un producteur
   et le début d’un consommateur ;
2. **Overlap** — le chevauchement temporel des stages (streaming), qui
   rend incorrecte toute somme naïve des durées.

Un collecteur *single-producer* ou une file non bornée (comme dans
certaines références open-source) ne permet ni de garantir la sûreté
concurrente, ni de rendre la saturation *observable*.

## 2. Définition opérationnelle

**P2** établit que le collecteur :

1. accepte **plusieurs producteurs** sans corrompre le document ;
2. reste **borné** (mémoire finie) et **non bloquant** sur `record()` ;
3. rend visible toute perte (`dropped_*`, `completeness`) ;
4. expose assez d’événements pour mesurer handoff et overlap *lorsque
   les hooks existent* (`*.queued`, paires started/first_*/completed).

**P2 n’est pas :** la sémantique de cancel (P3), ni le chemin critique
(P4), ni la mesure d’overhead (P5).

## 3. Fondements

### Concurrence et files

En systèmes distribués / multi-composants, la latence de service
globale est souvent dominée par un *straggler* ou par la composition
des files ([Han et al., 2015, arXiv:1511.02960](https://arxiv.org/abs/1511.02960)).
P2 pose l’infrastructure d’observation de ces files *sans* appliquer de
backpressure au pipeline (invariant : le profiler ne change pas la
sémantique applicative).

### Streaming basse latence

Les modèles audio streaming documentent des latences de l’ordre de
dizaines à centaines de millisecondes
([Quamer & Gutierrez-Osuna, 2024, arXiv:2406.09277](https://arxiv.org/abs/2406.09277)).
À cette échelle, un `record()` qui bloque ou alloue lourdement sur le
chemin chaud est inacceptable (spec 0005).

### Perte visible

Une politique *drop silencieux* masque les événements de lifecycle.
P2 impose : événement droppable rejeté et compté ; événement critique
évince un droppable s’il existe, sinon `dropped_critical` et
`completeness: partial`.

## 4. Contrats vTrace

| Élément | Rôle en P2 |
|---|---|
| Spec 0005 | Multi-producer, `try_push`, eviction critique, `shutdown` |
| Spec 0002 | Overlap STT/LLM/TTS/playback comme objet de mesure |
| Spec 0003 | `producer_id` optionnel ; `sequence` *par producteur* |
| Spec 0008 | Tests de concurrence à graine fixe |

## 5. Méthode et livrable

- Collecteur thread-safe (`threading.Lock` court ; timestamp *avant*
  le verrou).
- Suite de tests concurrence (producteurs parallèles, saturation,
  shutdown borné).
- **Livrable :** suite de tests concurrence verte ; document toujours
  validable après stress multi-thread.

## 6. Statut et limites

Implémenté côté Python collector (P2 slice). Les événements `queue.*`
ne sont émis *que* si le pipeline instrumenté expose des hooks — P2
prépare la mesure, P6 l’active sur un pipeline réel.

# P3 — Lifecycle Reliability

- **Status (implementation):** Complete
- **Depends on:** P2
- **Specs:** 0006 (primaire), 0003, 0004 (`cancel_latency_ms`)
- **Decisions:** 0005

## 1. Problème scientifique

Dans un agent vocal interactif, l’utilisateur *interrompt* (barge-in).
Les runtimes de référence encodent souvent l’annulation par un
**compteur de génération** (`is_stale(gen)`) sans événements distincts
pour *demande*, *accusé de réception* et *arrêt effectif*. Cette
compression masque :

1. la **latence de propagation** du cancel ;
2. les tâches qui **continuent** après la demande (orphelins) ;
3. les **terminaux illégaux** (second `turn.completed`, transition
   `completed → failed`).

Sans modèle de lifecycle, on ne peut pas distinguer « le tour est
annulé » (état) de « une demande d’annulation a été émise » (signal).

## 2. Définition opérationnelle

**P3** définit et *vérifie* :

1. les états de **tour** : `started` puis un unique terminal parmi
   `completed | failed | cancelled | timed_out` ;
2. les états de **tâche** (STT/LLM/TTS/playback) : `queued → started →`
   terminal ;
3. le flux de cancel : `cancel.requested` → `cancel.acknowledged` →
   `*.cancelled` → `turn.cancelled` ;
4. les **anomalies** signalées sans réécriture silencieuse des
   événements : `duplicate_terminal`, `late_after_terminal`,
   `orphaned_after_cancel`, `invalid_transition`.

L’analyse s’exécute **hors** du chemin chaud (`record()`).

**P3 n’est pas :** l’inférence de causalité (P4), ni le branchement
s2s (P6).

## 3. Fondements

### Causalité et traces d’exécution

L’analyse *ex post* de traces concurrentes est un objet d’étude
distinct de la causalité philosophique « interventionniste » : on
dispose d’un journal ordonné d’actions, et on reconstruit des
dépendances déclarées ([Crafa & Russo, 2013,
arXiv:1303.1384](https://arxiv.org/abs/1303.1384)). P3 s’inscrit dans
cette tradition : **dériver l’état depuis les événements**, ne pas
corriger le journal.

### Fiabilité perçue vs latence moyenne

Les services interactifs se jugent sur le *tail* et sur les échecs de
lifecycle (tour qui « ne meurt pas »), pas seulement sur la moyenne
([Wodislawski & Morrison, 2026, arXiv:2610.04615](https://arxiv.org/abs/2610.04615)).
Un LLM orphelin après barge-in est un bug de *fiabilité*, visible
uniquement si `cancel.requested` et l’absence de terminal coexistent
dans la trace.

## 4. Contrats vTrace

| Élément | Rôle en P3 |
|---|---|
| Spec 0006 | Automate de tour ; cancel ≠ terminal ; anomalies nommées |
| Spec 0004 | `cancel_latency_ms` = paire explicite d’événements |
| Décision 0005 | Pas d’arête inventée pour « expliquer » un orphan |

## 5. Méthode et livrable

- Module `lifecycle.py` : `analyze_lifecycle(doc) → LifecycleReport`.
- Intégration au rapport CLI (section Lifecycle + Cancellation).
- Tests d’acceptance alignés sur spec 0006 §10.
- **Livrable :** trace *lifecycle-validated* — anomalies signalées,
  événements conservés.

## 6. Statut et limites

Implémenté. Limite : pas de fenêtre de grâce pour
`orphaned_after_cancel` (choix documenté dans la spec : flag immédiat).
Les hooks d’émission de `cancel.*` dans un pipeline réel relèvent de
P6.

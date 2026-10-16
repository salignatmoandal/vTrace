# P6 — Hugging Face Integration

- **Status (implementation):** Not started (code audit of
  `huggingface/speech-to-speech` completed in engineering notes)
- **Depends on:** P1, P2 ; idéalement P4
- **Specs:** 0009, 0001, 0005, 0006
- **Decisions:** 0001 (Python comme surface HF), 0004 (privacy), 0006

## 1. Problème scientifique

Les contrats et l’analyse (P1–P4) sont nécessaires mais insuffisants
pour démontrer la *valeur* : il faut une trace d’un **vrai tour** dans
un pipeline de référence. Le candidat naturel est
[`huggingface/speech-to-speech`](https://github.com/huggingface/speech-to-speech)
— cascade VAD → STT → LLM → TTS, threads + files, protocole Realtime,
utilisé en production (ex. robots Reachy Mini).

La littérature sur les agents *spoken dialogue* temps réel fixe des
cibles de latence sub-seconde et des architectures streaming
([Chen et al., 2026, arXiv:2601.11141](https://arxiv.org/abs/2601.11141) ;
[Purwar & Choudhary, 2025, arXiv:2509.20971](https://arxiv.org/abs/2509.20971)).
Sans instrumentation sur un tel système, vTrace reste un validateur de
fixtures.

## 2. Définition opérationnelle

**P6** consiste à :

1. **Auditer** le code s2s (handlers, `CancelScope`, `TurnLatencyStore`)
   *avant* toute claim ;
2. Identifier des **points d’instrumentation stables** (idéal :
   `BaseHandler._run_loop`, hooks optionnels `on_event`) ;
3. Livrer une intégration **non invasive** (PR upstream minimal ou
   adaptateur toggleable) ;
4. Produire une **trace réelle** validée + `vtrace report`.

**P6 n’est pas :** un dashboard (P7), ni l’adoption d’OTel comme
contrat interne (décision 0006 : OTel = export futur).

## 3. Fondements

### Instrumentation non invasive

Modifier un pipeline concurrent sans en changer la sémantique rejoint
l’invariant 1 de vTrace : le profiler **observe**, il n’annule pas et
n’impose pas de backpressure. Les hooks `None` par défaut garantissent
un overhead nul lorsque désactivés — prérequis pour P5 *et* pour
l’acceptation upstream.

### Privacy by default

Aucun contenu vocal (audio, transcript, prompt, réponse modèle) n’est
collecté par défaut (décision 0004) — contrainte renforcée dès qu’on
touche un pipeline conversationnel réel.

### Concurrence réelle

s2s valide le besoin P2 (multi-producer) et P3 (cancel par génération).
L’audit a montré : `perf_counter` local, `TurnLatencyStore` (durées),
mais pas de document de trace ni de perte visible — exactement l’écart
que vTrace comble.

## 4. Contrats vTrace

| Élément | Rôle en P6 |
|---|---|
| Spec 0009 | Livrable : trace d’un tour réel |
| Spec 0005 / 0006 | Collecteur multi-thread + cancel lifecycle |
| Décision 0001 | Python = surface d’intégration HF |

## 5. Méthode et livrable (cible)

1. Spike : monkey-patch / hooks sur un tour local `speech-to-speech local`.
2. PR upstream optionnel : `on_event` sur `BaseHandler` (off by default).
3. Export JSON → `vtrace validate` + `vtrace report` (+ chemins P4).
4. **Livrable :** trace d’un tour réel via l’intégration.

## 6. Statut et limites

Audit GitHub effectué ; code d’intégration non mergé. Risque principal :
dépendance à des détails internes volatils — mitigation : instrumenter
des points stables (`BaseHandler`), PR petit, feature-flag.

---
name: adversarial-review
description: Adversarial review of a vTrace change that looks for invariant violations. Use after a contract or implementation change.
---

# adversarial-review

Skill: adversarial review of a vTrace change.

## When to use

- After a contract (spec/decision) or implementation change.
- Before declaring a task complete.

## Procedure

For each change, actively look for the following violations.

1. **Illegal transitions.** A turn with two terminals? A task
   `completed` → `failed`? A `cancel.requested` treated as terminal?
   (spec 0006)
2. **Silent losses.** A critical event lost without
   `completeness: partial` or `dropped_critical`? (spec 0003)
3. **Ambiguous metrics.** An `e2e` metric without an explicit pair? A
   conflation of `tts.first_audio` / `playback.started`? An estimated
   `tts.rtf`? (spec 0004)
4. **Inferred causality.** A causal edge deduced from temporal
   proximity without `parent_id` or an explicit pair? (decision 0005)
5. **Cross-domain clock.** A duration computed across two
   `clock_domain` values? (spec 0004)
6. **Captured voice content.** Audio, a transcription, a prompt, or a
   response in `attributes`? (decision 0004)
7. **Blocked audio path.** A `record()` that encodes JSON, that
   allocates heavily, or that waits on the queue? (spec 0005)
8. **Unmeasured claim.** A performance claim without an executed
   benchmark? (AGENTS.md)

## Deliverable

A list of violations found, each citing the violated invariant and the
file/line concerned. If no violation: say so explicitly, do not hedge.

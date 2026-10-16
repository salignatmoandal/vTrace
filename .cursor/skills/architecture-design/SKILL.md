---
name: architecture-design
description: Reusable procedure to add or amend a spec or decision in vTrace. Use before any change to a public contract.
---

# architecture-design

Skill: add or amend a spec or decision in vTrace.

## When to use

- Before adding, modifying, or removing an element of a public
  contract (event, metric, clock, lifecycle state, export format).
- Before re-evaluating a rejected alternative.

## Procedure

1. **Identify the contract touched.** Cite the relevant spec and
   decision.
2. **Check the repo state.** Do not assume; read the code and existing
   docs.
3. **Choose the vehicle.**
   - New design decision → spec in `docs/specs/`.
   - Accepted architectural decision → decision in
     `docs/decisions/`, linked to a spec.
   - Amendment → new spec referencing the old one; old one moved to
     `Amended`.
4. **Write from the template.**
   - Spec: the 12-section structure (Purpose … Open questions), per
     existing specs.
   - Decision: `docs/decisions/TEMPLATE.md` (Nygard style).
5. **Mandatory coverage**: context, objectives, non-objectives,
   proposal, alternatives, invariants, failure modes, test
   consequences, open questions.
6. **Update the indexes**: `docs/specs/` (cross-references) and
   `docs/decisions/README.md`.
7. **Initial status `Proposed`.** The transition to `Accepted` is an
   explicit act after human review.
8. **If the contract is machine-readable**: update
   `docs/schema/trace.schema.json` and reference the spec.

## Anti-patterns

- Modifying a contract directly in the code without a spec.
- Rewriting an existing decision instead of creating a new one that
  supersedes it (`Superseded`).
- Omitting failure modes to look more convincing.
- Inventing a performance measurement to justify the decision.

## Deliverable

A spec or decision file with status `Proposed`, updated index,
template respected, rejected alternatives kept.

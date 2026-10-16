# AGENTS.md — vTrace

Permanent instructions for any agent (human or AI) working on vTrace.
These rules are invariants, not suggestions.

## Invariants

1. **Read before changing.** Before modifying a public contract (event,
   metric, clock, state, export), read the relevant specs in
   `docs/specs/` and decisions in `docs/decisions/`.
2. **The contract precedes the code.** Any contract change goes through
   a spec update then a decision record (decision 0002). Code does not
   get ahead of the contract.
3. **No rejected alternative.** Do not implement an alternative
   explicitly rejected in a decision without a new spec that
   re-evaluates it.
4. **No voice content by default.** No raw audio, transcription, prompt,
   or model response is collected by default (decision 0004).
5. **No invented causality.** No causal edge inferred from temporal
   proximity (decision 0005). Prefer an incomplete result over a false
   one.
6. **No performance claim without an executed benchmark.** No claim of
   overhead, latency, or throughput without a benchmark actually run
   (phase P5). Distinguish observed result from expected result.
7. **Minimal changes.** One concern per change. No unsolicited
   refactoring. Respect the module boundaries from spec 0001.
8. **Deterministic test for every contract change.** A contract change
   comes with a deterministic test (manual clock) that proves the
   invariant holds.
9. **Visible loss.** No silent loss of a critical event. Any loss shows
   up in `completeness` and `dropped_critical` (spec 0003).
10. **The trace document is the contract.** Consumers depend on the JSON
    document, not on internal objects (decision 0006).

## Start every session here

1. Read `AGENTS.md` (this file) and `plan/STATUS.md` if it exists
   (current phase, next task, blocked items). `plan/` is gitignored and
   local-only.
2. Read [`docs/roadmap.md`](docs/roadmap.md) for phase, status, and the
   revision history header. Pick work from the current phase's tasks.
3. Before changing a contract, read the relevant spec in `docs/specs/`
   and decision in `docs/decisions/`.
4. Work autonomously; do not stop to ask unless a decision is genuinely
   the user's.

## Evidence-based completion

A task is done only when evidence exists, not when it "looks right".
Before declaring a task complete, an agent must:

- Run `just ci` (the single gate: Rust `cargo xtask ci` + Python
  ruff/pyright/pytest + schema validation). It must be green.
- For a contract change: show a deterministic test (manual clock) passing.
- For a trace change: run `vtrace report` on a fixture and validate it
  against `docs/schema/trace.schema.json`.
- Attach the evidence (command output, fixture path) to the task
  summary. Distinguish observed results from expected results; never
  invent measurements.

## Keeping docs current

When a milestone lands, update the `Last reviewed / Last updated /
Change` header and the revision history of `docs/roadmap.md`, and close
or shrink the matching open question in the relevant spec. Generated
docs (under `docs/generated/` if any) come from `cargo xtask docgen`,
not from hand editing.

## Current phase

P3 complete (lifecycle analysis). Next: P4 — Causal analysis.
P0 is **Accepted**; P1 MVP and P2 multi-producer are done.
See [`docs/roadmap.md`](docs/roadmap.md).

## Available skills

- [`architecture-design`](.cursor/skills/architecture-design/SKILL.md)
  — add or amend a spec/decision.
- [`adversarial-review`](.cursor/skills/adversarial-review/SKILL.md) —
  review that looks for invariant violations.

The `rust-runtime-engineering`, `voice-pipeline-integration`,
`critical-path-analysis`, and `performance-evaluation` skills are
**deferred**: not created until the corresponding phase has started.
See [`docs/agents/skills.md`](docs/agents/skills.md).

## Worktrees

No agent parallelization before contracts are accepted. Afterwards,
one worktree per stable interface, plus a review agent that does not
code the same surface. See
[`docs/agents/worktrees.md`](docs/agents/worktrees.md).

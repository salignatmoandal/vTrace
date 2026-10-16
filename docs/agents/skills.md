# Agent skills — vTrace

List of planned agent skills and their status. A skill is created only
when the corresponding phase starts. Do not create a skill "to have more
instructions".

## Active (P0)

| Skill | File | Role |
|---|---|---|
| `architecture-design` | [`.cursor/skills/architecture-design/SKILL.md`](../../.cursor/skills/architecture-design/SKILL.md) | Add or amend an RFC/ADR |
| `adversarial-review` | [`.cursor/skills/adversarial-review/SKILL.md`](../../.cursor/skills/adversarial-review/SKILL.md) | Adversarial review of a change |

## Deferred

| Skill | Creation phase | Intended role |
|---|---|---|
| `rust-runtime-engineering` | P3 or P4, if Rust arrives | Rust conventions, FFI, timestamp semantics |
| `voice-pipeline-integration` | P5 | Non-invasive instrumentation of voice pipelines |
| `critical-path-analysis` | P3 | Explicit dependency graph, per-objective paths |
| `performance-evaluation` | P4 | Benchmark protocol, variance, overhead |

A deferred skill must not be invoked before it is created. An agent that
needs one must first create it via the `architecture-design` skill, then
use it.

# Task template — vTrace

Any implementation or research task must define the following fields
before starting. A task without acceptance criteria is not startable.

## Fields

- **Goal.** One sentence. The intended effect, not the activity.
- **Ownership.** One responsible agent. One distinct review agent.
- **Dependencies.** Tasks, specs, decisions, interfaces this task
  depends on.
- **Inputs.** What must exist or be read before starting.
- **Non-objectives.** What the task does not do, to prevent scope
  expansion.
- **Acceptance criteria.** Verifiable. Preferably deterministic tests.
- **Tests.** Which tests accompany the task. For a contract change: a
  deterministic test (manual clock).
- **Deliverables.** Files produced or modified.

## Example (P1, ticket 1)

- **Goal.** Validate a trace document against the schema and provide a
  deterministic manual clock.
- **Ownership.** Agent A; review Agent D.
- **Dependencies.** P0 accepted; spec 0003; spec 0004.
- **Inputs.** `docs/schema/trace.schema.json`, spec 0003, spec 0004.
- **Non-objectives.** No collector, no adapters, no CLI.
- **Acceptance criteria.** A minimal document validates; a document
  without `timestamp_ns` is rejected; a cross-domain subtraction
  fails.
- **Tests.** Unit tests on the schema and the manual clock.
- **Deliverables.** `vtrace.clock` module, `vtrace.document` module
  (validation).

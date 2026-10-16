# Review and CI — vTrace

## P0 — No CI

No code to validate. Review is human: a reviewer checks that RFCs and
ADRs are consistent, that failure modes are named, and that rejected
alternatives are kept. The transition from `Proposed` to `Accepted`
happens here.

## P1 — Minimal CI on the contract

When Python code appears:

- `pytest` on contract tests (schema, clock, lifecycle, collector).
- `ruff` for linting.
- `pyright` for typing.

CI validates the **contract**, not performance. No performance test is
added before P4.

## P4 — Benchmark CI

At P4, a dedicated workflow runs the benchmark protocol (warmup,
repetitions, median and percentiles) and publishes a report. No automatic
failure threshold until variance is characterized.

## Review order

1. The review agent applies `adversarial-review`.
2. Invariant violations block integration.
3. Open questions do not block, but must be tracked.

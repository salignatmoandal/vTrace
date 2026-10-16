# vTrace Decisions

Decisions (Architecture Decision Records, Nygard style) record
**accepted** architectural decisions. They are short, dated, and linked
to the specifications in `docs/specs/`.

A spec proposes. A decision records. A spec with status `Proposed` has
no decision yet; it becomes `Accepted` when the corresponding decision
is created.

## Statuses

| Status | Meaning |
|---|---|
| `Proposed` | Decision proposed, pending human validation. |
| `Accepted` | Active decision. |
| `Superseded` | Replaced by a newer decision (referenced). |
| `Deprecated` | Obsolete. |

## Template

See [`TEMPLATE.md`](TEMPLATE.md). Nygard style, short: context,
decision, consequences, alternatives, related specs.

## Index

| Decision | Title | Status |
|---|---|---|
| [0001](0001-language-and-runtime-strategy.md) | Language and runtime strategy (Rust core at P1) | Proposed |
| [0002](0002-contract-governance.md) | Public contract governance | Proposed |
| [0003](0003-mvp-scope.md) | MVP scope | Proposed |
| [0004](0004-privacy-default.md) | Voice content excluded by default | Proposed |
| [0005](0005-no-inferred-causality.md) | No inferred causality by proximity | Proposed |
| [0006](0006-trace-document-as-contract.md) | The trace document is the contract | Proposed |

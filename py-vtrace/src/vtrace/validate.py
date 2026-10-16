"""Validate a trace document against the vTrace JSON schema.

This is the one piece of real Python in the P0 harness: it lets an agent
prove a fixture conforms to the contract (spec 0003, decision 0006) before any
collector exists. Used by `just validate` and `cargo xtask validate`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "schema" / "trace.schema.json"


def load_schema() -> dict:
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


def validate_document(path: str | Path) -> None:
    """Validate the trace document at *path* against the schema.

    Raises ``jsonschema.ValidationError`` on a contract violation, or
    ``FileNotFoundError`` if the file is missing. Exits non-zero on
    failure when run as a script.
    """
    doc_path = Path(path)
    with doc_path.open() as f:
        document = json.load(f)
    if jsonschema is None:
        raise RuntimeError("jsonschema is not installed; run `uv sync`")
    schema = load_schema()
    jsonschema.validate(instance=document, schema=schema)

    # Structural invariants beyond the schema (spec 0003, spec 0004).
    domains = set(document["clock_domains"])
    for ev in document["events"]:
        if ev["clock_domain"] not in domains:
            raise ValueError(
                f"event {ev['event_id']} uses clock_domain "
                f"{ev['clock_domain']!r} not listed in clock_domains"
            )
    # Ordering invariant: within a domain, (timestamp_ns, sequence) is
    # non-decreasing. sequence breaks ties, not causality (spec 0003).
    by_domain: dict[str, list] = {}
    for ev in document["events"]:
        by_domain.setdefault(ev["clock_domain"], []).append(ev)
    for domain, evs in by_domain.items():
        # Document order within the domain.
        ordered = list(evs)
        # Sort by (timestamp_ns, sequence) and check it matches document order.
        key_sorted = sorted(ordered, key=lambda e: (e["timestamp_ns"], e["sequence"]))
        if key_sorted != ordered:
            raise ValueError(
                f"events in domain {domain!r} are not in (timestamp_ns, sequence) order"
            )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m vtrace.validate <trace.json>", file=sys.stderr)
        return 2
    try:
        validate_document(argv[0])
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        print(f"validate: FAIL {exc}", file=sys.stderr)
        return 1
    print("validate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

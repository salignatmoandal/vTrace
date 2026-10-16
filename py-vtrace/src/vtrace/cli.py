"""CLI entry point — ``vtrace report <trace.json>`` (P1-3c, B5).

Reads a trace document, validates it against the Rust contract,
and prints a text report distinguishing compute, queue, and overlap
(spec 0009, P1 acceptance criterion).

Usage::

    vtrace report <trace.json>
    python -m vtrace.cli report <trace.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from vtrace._vtrace import validate as rust_validate
from vtrace.report import generate_report


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help"):
        print("usage: vtrace report <trace.json>")
        return 0

    if argv[0] != "report":
        print(f"unknown command: {argv[0]!r}", file=sys.stderr)
        print("usage: vtrace report <trace.json>", file=sys.stderr)
        return 2

    if len(argv) < 2:
        print("usage: vtrace report <trace.json>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    raw = path.read_text()
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    # Validate against the Rust contract before reporting.
    try:
        rust_validate(raw)
    except ValueError as exc:
        print(f"validate: FAIL {exc}", file=sys.stderr)
        return 1

    print(generate_report(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

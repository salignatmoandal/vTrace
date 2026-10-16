"""Causal analysis facade (P4, spec 0007).

Delegates to the Rust ``vtrace-analysis`` crate via PyO3. The document
is never mutated. No edge is inferred from timestamp proximity
(decision 0005).
"""

from __future__ import annotations

import json
from typing import Any

from vtrace._vtrace import critical_paths as _rust_critical_paths


def critical_paths(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-objective critical paths for a trace document."""
    return _rust_critical_paths(json.dumps(doc))


def format_critical_paths(paths: list[dict[str, Any]]) -> str:
    """Format critical-path results for the CLI report."""
    lines: list[str] = []
    lines.append("Critical paths (explicit edges only):")
    if not paths:
        lines.append("  (none)")
        return "\n".join(lines)

    for p in paths:
        obj = p.get("objective", "?")
        conf = p.get("confidence", "?")
        duration = p.get("duration_ns")
        if duration is None:
            dur_s = "n/a"
        else:
            dur_s = f"{duration / 1_000_000:.2f} ms"
        lines.append(f"  {obj:<18s} {conf:<12s} duration={dur_s}")
        hops = p.get("hops") or []
        if hops:
            chain = " → ".join(h.get("name", "?") for h in hops)
            lines.append(f"    path: {chain}")
        for reason in p.get("reasons") or []:
            lines.append(f"    reason: {reason}")
    return "\n".join(lines)

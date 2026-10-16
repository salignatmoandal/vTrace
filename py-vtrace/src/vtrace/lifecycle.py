"""Lifecycle analysis — cancellation, terminals, anomalies (P3).

Runs on a flushed trace document, NEVER on the ``record()`` hot path
(spec 0006 §5). The document is the source of truth (decision 0006);
this analyzer derives turn/task state from events and flags anomalies
without deleting or rewriting them.

Anomalies (spec 0006):
- ``duplicate_terminal`` — second terminal for a turn
- ``late_after_terminal`` — event after a turn terminal
- ``orphaned_after_cancel`` — task with no terminal after
  ``cancel.requested``
- ``invalid_transition`` — illegal state change (e.g. completed → failed)

Cancellation is a lifecycle, not a flag:
``cancel.requested`` → ``cancel.acknowledged`` → ``*.cancelled`` →
``turn.cancelled``. ``cancel.requested`` is NOT a turn terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Turn terminals (spec 0006). cancel.requested is NOT among them.
_TURN_TERMINALS = frozenset(
    {
        "turn.completed",
        "turn.failed",
        "turn.cancelled",
        "turn.timed_out",
    }
)

# Task terminal suffixes (component.* except turn / vad / collector).
_TASK_TERMINAL_SUFFIXES = frozenset({"completed", "failed", "cancelled"})

# Components that are tasks with queued/started/terminal lifecycle.
# VAD stays fronts (speech_started / speech_ended), not a forced span.
_TASK_COMPONENTS = frozenset({"stt", "llm", "tts", "playback"})


@dataclass(frozen=True)
class Anomaly:
    """A lifecycle anomaly. Events are kept; this only signals."""

    kind: str
    event_id: str
    detail: str
    span_id: str | None = None


@dataclass
class LifecycleReport:
    """Result of analyzing a trace document's lifecycle."""

    turn_state: str
    """Derived turn state: ``none`` | ``started`` | a terminal name."""

    cancel_requested: bool
    cancel_acknowledged: bool
    anomalies: list[Anomaly] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no anomalies were flagged."""
        return len(self.anomalies) == 0


def _suffix(name: str) -> str:
    if "." not in name:
        return name
    return name.rsplit(".", 1)[-1]


def _is_task_terminal(component: str, name: str) -> bool:
    if component not in _TASK_COMPONENTS:
        return False
    return _suffix(name) in _TASK_TERMINAL_SUFFIXES


def _is_task_started(component: str, name: str) -> bool:
    if component not in _TASK_COMPONENTS:
        return False
    return _suffix(name) in {"queued", "started"}


def analyze_lifecycle(doc: dict[str, Any]) -> LifecycleReport:
    """Derive turn/task lifecycle and flag anomalies (spec 0006).

    Events are never removed or rewritten. Anomalies are returned in
    the report so consumers (CLI, tests) can signal them.
    """
    events: list[dict[str, Any]] = list(doc.get("events", []))
    anomalies: list[Anomaly] = []

    turn_state = "none"
    turn_terminal_event_id: str | None = None
    turn_terminal_index: int | None = None

    cancel_requested = False
    cancel_acknowledged = False
    cancel_requested_index: int | None = None

    # span_id → {started: bool, terminal: str | None, started_index: int}
    tasks: dict[str, dict[str, Any]] = {}

    for i, ev in enumerate(events):
        name = ev["name"]
        eid = ev["event_id"]
        component = ev["component"]
        span_id = ev["span_id"]

        # --- Late after turn terminal (non-terminals only) ----------------
        # Turn terminals after the first are duplicate_terminal (below).
        # Everything else after a terminal is late_after_terminal — kept
        # in the document, only flagged here (spec 0006).
        if (
            turn_terminal_index is not None
            and i > turn_terminal_index
            and name not in _TURN_TERMINALS
        ):
            anomalies.append(
                Anomaly(
                    kind="late_after_terminal",
                    event_id=eid,
                    detail=(f"{name} after turn terminal {turn_state} ({turn_terminal_event_id})"),
                    span_id=span_id,
                )
            )

        # --- Cancellation flow (not a turn state) -------------------------
        if name == "cancel.requested":
            cancel_requested = True
            cancel_requested_index = i
            continue
        if name == "cancel.acknowledged":
            cancel_acknowledged = True
            continue

        # --- Turn lifecycle -----------------------------------------------
        if name == "turn.started":
            if turn_state == "none":
                turn_state = "started"
            elif turn_state in _TURN_TERMINALS:
                # Restart after terminal is illegal; flag, do not reopen.
                anomalies.append(
                    Anomaly(
                        kind="invalid_transition",
                        event_id=eid,
                        detail=f"turn.started after turn already {turn_state}",
                        span_id=span_id,
                    )
                )
            continue

        if name in _TURN_TERMINALS:
            if turn_state == "started":
                turn_state = name
                turn_terminal_event_id = eid
                turn_terminal_index = i
            elif turn_state in _TURN_TERMINALS:
                # Second terminal: never reopen; always duplicate.
                anomalies.append(
                    Anomaly(
                        kind="duplicate_terminal",
                        event_id=eid,
                        detail=(
                            f"second terminal {name} after {turn_state} "
                            f"({turn_terminal_event_id}); turn not reopened"
                        ),
                        span_id=span_id,
                    )
                )
                if name != turn_state:
                    anomalies.append(
                        Anomaly(
                            kind="invalid_transition",
                            event_id=eid,
                            detail=f"{turn_state} → {name}",
                            span_id=span_id,
                        )
                    )
            elif turn_state == "none":
                # Terminal without started — record state, flag invalid.
                anomalies.append(
                    Anomaly(
                        kind="invalid_transition",
                        event_id=eid,
                        detail=f"{name} without turn.started",
                        span_id=span_id,
                    )
                )
                turn_state = name
                turn_terminal_event_id = eid
                turn_terminal_index = i
            continue

        # --- Task lifecycle (span_id scoped) ------------------------------
        if component in _TASK_COMPONENTS:
            task = tasks.setdefault(
                span_id,
                {"started": False, "terminal": None, "started_index": None},
            )
            if _is_task_started(component, name):
                task["started"] = True
                if task["started_index"] is None:
                    task["started_index"] = i
                if task["terminal"] is not None:
                    anomalies.append(
                        Anomaly(
                            kind="invalid_transition",
                            event_id=eid,
                            detail=(
                                f"{name} after task already {task['terminal']} on span {span_id}"
                            ),
                            span_id=span_id,
                        )
                    )
            elif _is_task_terminal(component, name):
                if task["terminal"] is None:
                    task["terminal"] = name
                else:
                    anomalies.append(
                        Anomaly(
                            kind="duplicate_terminal",
                            event_id=eid,
                            detail=(
                                f"second task terminal {name} after "
                                f"{task['terminal']} on span {span_id}"
                            ),
                            span_id=span_id,
                        )
                    )
                    if name != task["terminal"]:
                        anomalies.append(
                            Anomaly(
                                kind="invalid_transition",
                                event_id=eid,
                                detail=(f"{task['terminal']} → {name} on span {span_id}"),
                                span_id=span_id,
                            )
                        )

    # --- Orphaned after cancel --------------------------------------------
    # Flag immediately (no grace window — spec 0006 open question).
    if cancel_requested and cancel_requested_index is not None:
        for span_id, task in tasks.items():
            if not task["started"]:
                continue
            if task["terminal"] is not None:
                continue
            # Task started but never reached a terminal after cancel.
            # Prefer the started event id if we can find it.
            orphan_eid = "unknown"
            for ev in events:
                if ev["span_id"] == span_id and _is_task_started(ev["component"], ev["name"]):
                    orphan_eid = ev["event_id"]
                    break
            anomalies.append(
                Anomaly(
                    kind="orphaned_after_cancel",
                    event_id=orphan_eid,
                    detail=(f"span {span_id} has no terminal after cancel.requested"),
                    span_id=span_id,
                )
            )

    return LifecycleReport(
        turn_state=turn_state,
        cancel_requested=cancel_requested,
        cancel_acknowledged=cancel_acknowledged,
        anomalies=anomalies,
    )


def format_lifecycle(report: LifecycleReport) -> str:
    """Format a lifecycle report as text for the CLI."""
    lines: list[str] = []
    lines.append("Lifecycle:")
    lines.append(f"  turn_state:          {report.turn_state}")
    lines.append(f"  cancel.requested:    {'yes' if report.cancel_requested else 'no'}")
    lines.append(f"  cancel.acknowledged: {'yes' if report.cancel_acknowledged else 'no'}")
    if report.ok:
        lines.append("  anomalies:           none")
    else:
        lines.append(f"  anomalies:           {len(report.anomalies)}")
        for a in report.anomalies:
            span = f" span={a.span_id}" if a.span_id else ""
            lines.append(f"    - {a.kind}: {a.detail} [{a.event_id}]{span}")
    return "\n".join(lines)

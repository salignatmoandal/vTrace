"""vTrace — Python adapter and CLI layer.

The native extension `_vtrace` (built from the Rust crate
`vtrace-python`) provides the typed contract: `MonotonicClock`,
`ManualClock`, and `validate`. The Python layer adds the collector,
adapters, and the CLI on top.

Note: `validate` is accessed via `vtrace._vtrace.validate` to avoid
clashing with the `vtrace.validate` Python module (schema validation).
"""

from vtrace._vtrace import ManualClock, MonotonicClock
from vtrace.adapters import trace_llm, trace_playback, trace_stt, trace_tts
from vtrace.causal import critical_paths
from vtrace.collector import Collector
from vtrace.lifecycle import Anomaly, LifecycleReport, analyze_lifecycle

__version__ = "0.0.0"

__all__ = [
    "Anomaly",
    "Collector",
    "LifecycleReport",
    "ManualClock",
    "MonotonicClock",
    "analyze_lifecycle",
    "critical_paths",
    "trace_llm",
    "trace_playback",
    "trace_stt",
    "trace_tts",
]

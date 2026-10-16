"""vTrace — Python adapter and CLI layer.

The native extension `_vtrace` (built from the Rust crate
`vtrace-python`) provides the typed contract: `MonotonicClock`,
`ManualClock`, and `validate`. The Python layer adds the collector,
adapters, and the CLI on top.

Note: `validate` is accessed via `vtrace._vtrace.validate` to avoid
clashing with the `vtrace.validate` Python module (schema validation).
"""

from vtrace._vtrace import ManualClock, MonotonicClock
from vtrace.collector import Collector

__version__ = "0.0.0"

__all__ = ["Collector", "ManualClock", "MonotonicClock"]

"""Optional integration bridges (P6).

These modules do not import Hugging Face ``speech-to-speech``. They
expose callback surfaces that an upstream adapter or a thin wrapper
can call. Structural events only (decision 0004).
"""

from vtrace.integrations.s2s import S2STurnBridge, run_s2s_shaped_turn

__all__ = ["S2STurnBridge", "run_s2s_shaped_turn"]

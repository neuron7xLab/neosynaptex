"""MFN Self-Reading Architecture — read-only introspection + narrow recovery channel.

Five layers:
  1. SelfModel        — every step: what is the system now?
  2. CoherenceMonitor — every N steps: is the system intact?
  3. InterpretabilityLayer — window W: why is the system in this state?
  4. PhaseValidator   — every 100 steps: is the system degrading?
  5. RecoveryProtocol — the ONLY writer: corrects {Theta, PID} when needed

Architectural law:
  gamma is an OUTPUT of health. Never an input to Recovery.
  Recovery reads: free_energy, betti_numbers, D_box, lyapunov_spectrum.
  Recovery writes: Theta, PID parameters via ThermodynamicKernel.

Ref: Vasylenko (2026) NFI Platform
"""

from .coherence_monitor import CoherenceMonitor, CoherenceReport
from .interpretability import InterpretabilityLayer, InterpretabilityTrace
from .loop import SelfReadingConfig, SelfReadingLoop, SelfReadingReport
from .phase_validator import MFNPhase, PhaseReport, PhaseValidator
from .recovery import RecoveryAction, RecoveryMode, RecoveryProtocol
from .self_model import SelfModel, SelfModelSnapshot

__all__ = [
    "CoherenceMonitor",
    "CoherenceReport",
    "InterpretabilityLayer",
    "InterpretabilityTrace",
    "MFNPhase",
    "PhaseReport",
    "PhaseValidator",
    "RecoveryAction",
    "RecoveryMode",
    "RecoveryProtocol",
    "SelfModel",
    "SelfModelSnapshot",
    "SelfReadingConfig",
    "SelfReadingLoop",
    "SelfReadingReport",
]

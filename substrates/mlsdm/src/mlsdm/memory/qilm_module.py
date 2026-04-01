from typing import Any

import numpy as np


class QILM:
    def __init__(self) -> None:
        self.memory: list[np.ndarray] = []
        self.phases: list[float | Any] = []

    def entangle_phase(self, event_vector: np.ndarray, phase: float | Any | None = None) -> None:
        if not isinstance(event_vector, np.ndarray):
            raise TypeError("event_vector must be a NumPy array.")

        vec = event_vector.astype(float)
        self.memory.append(vec)
        if phase is None:
            phase = float(np.random.rand())
        self.phases.append(phase)

    def retrieve(self, phase: float | Any, tolerance: float = 0.1) -> list[np.ndarray]:
        if tolerance < 0:
            raise ValueError("Tolerance must be non-negative.")
        # Note: memory and phases are kept in sync by entangle_phase method
        # Using strict=False for backward compatibility, but lengths should match
        results: list[np.ndarray] = []
        for v, ph in zip(self.memory, self.phases, strict=False):
            if isinstance(ph, (float, int)) and isinstance(phase, (float, int)):
                if abs(float(ph) - float(phase)) <= tolerance:
                    results.append(v)
            elif ph == phase:
                results.append(v)
        return results

    def to_dict(self) -> dict[str, Any]:
        return {"memory": [m.tolist() for m in self.memory], "phases": self.phases}

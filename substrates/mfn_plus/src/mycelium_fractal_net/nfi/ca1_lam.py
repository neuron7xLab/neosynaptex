"""CA1TemporalBuffer — minimal CA1-LAM analogue for trajectory memory.

Ring buffer of MFNSnapshot. Tracks trajectory geometry in (F, B0, D_box) space.
Does NOT compute gamma. Does NOT read gamma.
Only geometry of sequential states matters.

Ref: Vasylenko (2026)
     O'Keefe & Nadel (1978) — hippocampal place/time cells
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from mycelium_fractal_net.tau_control.types import MFNSnapshot

__all__ = ["CA1TemporalBuffer", "TemporalSummary"]


@dataclass
class TemporalSummary:
    """Compressed temporal summary from CA1 buffer.

    mean_free_energy: average F over buffer window
    betti_trajectory: sequence of betti_0 values (trajectory shape)
    phase_stability: std of normalized state vectors (low = stable phase)
    n_samples: how many snapshots contributed
    """

    mean_free_energy: float
    betti_trajectory: list[int]
    phase_stability: float
    n_samples: int


class CA1TemporalBuffer:
    """Ring buffer of MFNSnapshot for temporal context.

    capacity: maximum number of snapshots retained (default 64)

    Methods:
        push(snapshot) — add a snapshot to the buffer
        compress() -> TemporalSummary — statistical summary of buffer
        coherence_score() -> float [0,1] — cosine similarity between consecutive states

    Architectural invariant: no gamma computation, no gamma reading.
    """

    __slots__ = ("_buf", "_capacity")

    def __init__(self, capacity: int = 64) -> None:
        self._capacity = capacity
        self._buf: deque[MFNSnapshot] = deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._buf)

    def push(self, snapshot: MFNSnapshot) -> None:
        """Append snapshot to ring buffer."""
        self._buf.append(snapshot)

    def _to_vector(self, snap: MFNSnapshot) -> np.ndarray:
        """Project snapshot into normalized (F, B0, D_box) space.

        # APPROXIMATION: log-scale for free_energy (gradient energy spans orders
        # of magnitude), linear for betti_0 and d_box.
        """
        f = snap.free_energy if snap.free_energy is not None else 1.0
        b = float(snap.betti_0) if snap.betti_0 is not None else 0.0
        d = snap.d_box if snap.d_box is not None else 1.0
        return np.array([
            np.log1p(abs(f)) / 10.0,  # log-scale: gradient energy varies widely
            b / 50.0,                  # APPROXIMATION: betti_0 scale ~50
            d / 2.0,                   # APPROXIMATION: d_box in [0, 2]
        ], dtype=np.float64)

    def compress(self) -> TemporalSummary:
        """Compress buffer into a TemporalSummary."""
        if len(self._buf) == 0:
            return TemporalSummary(
                mean_free_energy=0.0,
                betti_trajectory=[],
                phase_stability=0.0,
                n_samples=0,
            )

        energies = [
            s.free_energy for s in self._buf if s.free_energy is not None
        ]
        bettis = [
            s.betti_0 for s in self._buf if s.betti_0 is not None
        ]

        vectors = np.array([self._to_vector(s) for s in self._buf])
        phase_stability = float(np.mean(np.std(vectors, axis=0))) if len(vectors) > 1 else 0.0

        return TemporalSummary(
            mean_free_energy=float(np.mean(energies)) if energies else 0.0,
            betti_trajectory=list(bettis),
            phase_stability=phase_stability,
            n_samples=len(self._buf),
        )

    def coherence_score(self) -> float:
        """Trajectory smoothness via displacement vector alignment.

        Measures how consistently the system moves through (F, B0, D_box) space.
        Cosine similarity between CONSECUTIVE DISPLACEMENT vectors, not states.

        - 2 snapshots → 1 displacement, no comparison possible → 0.5 (neutral)
        - 3+ snapshots → mean cosine similarity of consecutive displacements
        - Smooth monotonic trajectory → ~1.0
        - Oscillating / reversing → ~0.0
        - Random walk → ~0.5

        Returns 0.0 if fewer than 2 snapshots.
        Range: [0, 1] (clipped).
        """
        n = len(self._buf)
        if n < 2:
            return 0.0
        if n == 2:
            return 0.5  # single displacement, no trend information

        vectors = [self._to_vector(s) for s in self._buf]

        # Compute displacement vectors: d_i = v_{i+1} - v_i
        displacements = [vectors[i + 1] - vectors[i] for i in range(n - 1)]

        # Cosine similarity between consecutive displacements
        similarities: list[float] = []
        for i in range(1, len(displacements)):
            a, b = displacements[i - 1], displacements[i]
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a < 1e-12 or norm_b < 1e-12:
                # Zero displacement = system stalled; treat as neutral
                similarities.append(0.5)
                continue
            cos_sim = float(np.dot(a, b) / (norm_a * norm_b))
            # Map from [-1, 1] to [0, 1]: aligned=1.0, opposed=0.0
            similarities.append((cos_sim + 1.0) / 2.0)

        raw = float(np.mean(similarities))
        return float(np.clip(raw, 0.0, 1.0))

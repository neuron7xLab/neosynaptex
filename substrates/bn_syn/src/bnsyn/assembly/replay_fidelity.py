"""Replay fidelity tracking — compare wake vs replay assembly structure."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .detector import AssemblyDetector, AssemblyDetectionResult, Float64Array


@dataclass(frozen=True)
class ReplayFidelityResult:
    """Quantitative comparison between wake and replay assemblies."""

    mean_cosine_similarity: float
    temporal_correlation: float
    assembly_reactivation_rate: float
    per_assembly_fidelity: dict[int, float]
    phase: str  # "wake" | "light_sleep" | "deep_sleep" | "rem"


class ReplayFidelityTracker:
    """Track replay fidelity by comparing wake vs sleep assemblies.

    Parameters
    ----------
    detector : AssemblyDetector
        The assembly detector whose buffer will be snapshotted and compared.
    """

    def __init__(self, detector: AssemblyDetector) -> None:
        self._detector = detector
        self._wake_result: AssemblyDetectionResult | None = None

    def snapshot_wake_state(self) -> None:
        """Detect assemblies on the current buffer and store as the wake reference."""
        self._wake_result = self._detector.detect()

    def measure_replay_fidelity(self, phase: str) -> ReplayFidelityResult:
        """Detect assemblies on the current buffer and compare to the wake snapshot.

        Parameters
        ----------
        phase : str
            Sleep-cycle phase label, e.g. ``"light_sleep"``.

        Returns
        -------
        ReplayFidelityResult
        """
        if self._wake_result is None:
            raise RuntimeError(
                "snapshot_wake_state() must be called before measure_replay_fidelity()"
            )

        replay_result = self._detector.detect()

        wake_assemblies = self._wake_result.assemblies
        replay_assemblies = replay_result.assemblies

        # --- Edge case: no wake assemblies ---
        if len(wake_assemblies) == 0:
            return ReplayFidelityResult(
                mean_cosine_similarity=0.0,
                temporal_correlation=0.0,
                assembly_reactivation_rate=0.0,
                per_assembly_fidelity={},
                phase=phase,
            )

        # --- Cosine similarity: best match per wake assembly ---
        per_assembly_fidelity: dict[int, float] = {}
        cosine_sims: list[float] = []
        reactivated = 0

        for wa in wake_assemblies:
            best_cos = 0.0
            for ra in replay_assemblies:
                cos = _cosine_similarity(wa.weights, ra.weights)
                if cos > best_cos:
                    best_cos = cos
            per_assembly_fidelity[wa.index] = best_cos
            cosine_sims.append(best_cos)
            if best_cos > 0.5:
                reactivated += 1

        mean_cosine = float(np.mean(cosine_sims)) if cosine_sims else 0.0
        reactivation_rate = reactivated / len(wake_assemblies)

        # --- Temporal correlation between activation traces ---
        temporal_corrs: list[float] = []
        wake_traces = self._wake_result.activation_traces
        replay_traces = replay_result.activation_traces

        for wa in wake_assemblies:
            if wa.index not in wake_traces:
                continue
            wt = wake_traces[wa.index]
            # Find best-matching replay assembly by cosine
            best_ra_idx: int | None = None
            best_cos = 0.0
            for ra in replay_assemblies:
                cos = _cosine_similarity(wa.weights, ra.weights)
                if cos > best_cos:
                    best_cos = cos
                    best_ra_idx = ra.index
            if best_ra_idx is not None and best_ra_idx in replay_traces:
                rt = replay_traces[best_ra_idx]
                # Truncate to same length
                min_len = min(len(wt), len(rt))
                if min_len >= 2:
                    corr = float(np.corrcoef(wt[:min_len], rt[:min_len])[0, 1])
                    if not np.isnan(corr):
                        temporal_corrs.append(corr)

        temporal_correlation = float(np.mean(temporal_corrs)) if temporal_corrs else 0.0

        return ReplayFidelityResult(
            mean_cosine_similarity=mean_cosine,
            temporal_correlation=temporal_correlation,
            assembly_reactivation_rate=reactivation_rate,
            per_assembly_fidelity=per_assembly_fidelity,
            phase=phase,
        )


def _cosine_similarity(a: Float64Array, b: Float64Array) -> float:
    """Compute cosine similarity between two vectors (absolute value)."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    # Use absolute value since eigenvectors can have arbitrary sign
    return float(np.abs(np.dot(a, b)) / (norm_a * norm_b))

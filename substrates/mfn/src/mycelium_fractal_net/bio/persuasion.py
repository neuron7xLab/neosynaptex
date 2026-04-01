"""Persuasion — Active inference + intervention classification + persuadability.

Ref: Friston & Levin (2015) "Knowing one's place" Interface Focus
     Levin (2019) "The Computational Boundary of a Self" Front.Psychol.
     Fields & Levin (2022) "Competency in navigating arbitrary spaces"

Core equations:
    F = E_q[ln q(s) - ln p(o,s)]           [variational free energy]
    π* = argmin_π E_q[G(π)]                 [expected free energy → policy]
    G(π) = KL[q(o|π) || p(o)] + H[q(o|π)]  [pragmatic + epistemic value]

Intervention hierarchy (Levin 2019):
    Level 0 — FORCE:     Direct state override
    Level 1 — SETPOINT:  Modify target attractor
    Level 2 — SIGNAL:    Provide gradient information
    Level 3 — PERSUADE:  Reshape free energy landscape

Persuadability via controllability Gramian:
    W_c = ∫₀ᵀ e^{At} B B^T e^{A^T t} dt
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import expm

__all__ = [
    "FieldActiveInference",
    "FreeEnergyResult",
    "InterventionClassifier",
    "InterventionLevel",
    "PersuadabilityAnalyzer",
    "PersuadabilityResult",
]


class InterventionLevel(enum.IntEnum):
    """Levin's hierarchy of intervention sophistication."""

    FORCE = 0
    SETPOINT = 1
    SIGNAL = 2
    PERSUADE = 3


@dataclass(frozen=True)
class FreeEnergyResult:
    """Variational free energy decomposition for a morphogenetic field."""

    free_energy: float
    accuracy: float
    complexity: float
    expected_free_energy: float
    pragmatic_value: float
    epistemic_value: float
    field_shape: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "free_energy": round(self.free_energy, 6),
            "accuracy": round(self.accuracy, 6),
            "complexity": round(self.complexity, 6),
            "expected_free_energy": round(self.expected_free_energy, 6),
            "pragmatic_value": round(self.pragmatic_value, 6),
            "epistemic_value": round(self.epistemic_value, 6),
            "field_shape": list(self.field_shape),
        }


@dataclass(frozen=True)
class PersuadabilityResult:
    """Controllability analysis for morphogenetic persuadability."""

    persuadability_score: float
    controllability_rank: int
    gramian_trace: float
    gramian_det_log: float
    intervention_level: InterventionLevel
    n_controllable_modes: int
    total_modes: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "persuadability_score": round(self.persuadability_score, 6),
            "controllability_rank": self.controllability_rank,
            "gramian_trace": round(self.gramian_trace, 6),
            "gramian_det_log": round(self.gramian_det_log, 6),
            "intervention_level": self.intervention_level.name,
            "n_controllable_modes": self.n_controllable_modes,
            "total_modes": self.total_modes,
        }


class FieldActiveInference:
    """Active inference for morphogenetic fields (Friston-Levin 2015).

    Computes variational free energy of a field state relative to a
    target morphology, decomposed into accuracy (data fit) and
    complexity (deviation from prior beliefs).
    """

    def __init__(
        self,
        target_field: np.ndarray,
        prior_precision: float = 1.0,
        likelihood_precision: float = 10.0,
    ) -> None:
        self.target = target_field.astype(np.float64)
        self.prior_precision = prior_precision
        self.likelihood_precision = likelihood_precision
        self._target_mean = float(np.mean(self.target))
        self._target_std = float(np.std(self.target)) + 1e-12

    def compute_free_energy(
        self,
        current_field: np.ndarray,
        predicted_field: np.ndarray | None = None,
    ) -> FreeEnergyResult:
        """Compute variational free energy F = -accuracy + complexity.

        Args:
            current_field: Current morphogenetic field state
            predicted_field: Model's prediction of next state (for G)
        """
        obs = current_field.astype(np.float64)
        N, M = obs.shape

        # Accuracy: -E_q[ln p(o|s)] ≈ likelihood precision × MSE
        mse = float(np.mean((obs - self.target) ** 2))
        accuracy = -self.likelihood_precision * mse

        # Complexity: KL[q(s) || p(s)] ≈ prior precision × deviation from prior
        obs_mean = float(np.mean(obs))
        obs_std = float(np.std(obs)) + 1e-12
        kl_mean = 0.5 * self.prior_precision * (obs_mean - self._target_mean) ** 2
        kl_var = 0.5 * (
            (obs_std / self._target_std) ** 2 - 1.0 + 2.0 * np.log(self._target_std / obs_std)
        )
        complexity = kl_mean + max(kl_var, 0.0)

        free_energy = -accuracy + complexity

        # Expected free energy G (if prediction available)
        if predicted_field is not None:
            pred = predicted_field.astype(np.float64)
            pred_mse = float(np.mean((pred - self.target) ** 2))
            pragmatic = self.likelihood_precision * pred_mse
            # Epistemic: entropy of predicted distribution
            pred_std = float(np.std(pred)) + 1e-12
            epistemic = float(np.log(pred_std))
            efg = pragmatic + epistemic
        else:
            pragmatic = 0.0
            epistemic = 0.0
            efg = free_energy  # Default: G ≈ F

        return FreeEnergyResult(
            free_energy=free_energy,
            accuracy=accuracy,
            complexity=complexity,
            expected_free_energy=efg,
            pragmatic_value=pragmatic,
            epistemic_value=epistemic,
            field_shape=(N, M),
        )


class InterventionClassifier:
    """Classify interventions along Levin's hierarchy.

    Based on how the intervention modifies the system:
      FORCE:    Directly sets field values (|delta| > threshold)
      SETPOINT: Modifies attractor position
      SIGNAL:   Adds gradient information
      PERSUADE: Reshapes energy landscape curvature
    """

    def __init__(
        self,
        force_threshold: float = 0.5,
        setpoint_threshold: float = 0.1,
        signal_threshold: float = 0.01,
    ) -> None:
        self.force_threshold = force_threshold
        self.setpoint_threshold = setpoint_threshold
        self.signal_threshold = signal_threshold

    def classify(
        self,
        field_before: np.ndarray,
        field_after: np.ndarray,
    ) -> InterventionLevel:
        """Classify an intervention by its effect on the field."""
        delta = field_after.astype(np.float64) - field_before.astype(np.float64)
        max_change = float(np.max(np.abs(delta)))
        rms_change = float(np.sqrt(np.mean(delta**2)))

        if max_change > self.force_threshold:
            return InterventionLevel.FORCE

        # Check if mean shifted significantly (setpoint change)
        mean_shift = abs(float(np.mean(field_after) - np.mean(field_before)))
        if mean_shift > self.setpoint_threshold:
            return InterventionLevel.SETPOINT

        # Check gradient structure
        grad_before = np.gradient(field_before.astype(np.float64))
        grad_after = np.gradient(field_after.astype(np.float64))
        grad_change = sum(
            float(np.sqrt(np.mean((ga - gb) ** 2)))
            for ga, gb in zip(grad_after, grad_before, strict=True)
        )

        if rms_change > self.signal_threshold and grad_change > self.signal_threshold:
            return InterventionLevel.SIGNAL

        return InterventionLevel.PERSUADE

    def classify_with_detail(
        self,
        field_before: np.ndarray,
        field_after: np.ndarray,
    ) -> dict[str, Any]:
        """Classify with full diagnostic detail."""
        delta = field_after.astype(np.float64) - field_before.astype(np.float64)
        level = self.classify(field_before, field_after)
        return {
            "level": level.name,
            "level_value": int(level),
            "max_change": round(float(np.max(np.abs(delta))), 6),
            "rms_change": round(float(np.sqrt(np.mean(delta**2))), 6),
            "mean_shift": round(abs(float(np.mean(field_after) - np.mean(field_before))), 6),
            "affected_fraction": round(float(np.mean(np.abs(delta) > 1e-6)), 4),
        }


class PersuadabilityAnalyzer:
    """Compute persuadability via controllability Gramian.

    The controllability Gramian W_c measures how easily the system
    can be steered to arbitrary states. High W_c trace → high
    persuadability (system is responsive to subtle interventions).

    W_c = ∫₀ᵀ e^{At} B B^T e^{A^T t} dt

    where A is the linearized field dynamics and B is the input matrix.
    """

    def __init__(
        self,
        horizon: float = 1.0,
        n_integration_steps: int = 50,
        rank_threshold: float = 1e-6,
    ) -> None:
        self.horizon = horizon
        self.n_steps = n_integration_steps
        self.rank_threshold = rank_threshold

    def compute(
        self,
        A: np.ndarray,
        B: np.ndarray,
    ) -> PersuadabilityResult:
        """Compute controllability Gramian and persuadability score.

        Args:
            A: (n, n) system dynamics matrix (linearized)
            B: (n, m) input/control matrix
        """
        n = A.shape[0]
        dt = self.horizon / self.n_steps
        W_c = np.zeros((n, n), dtype=np.float64)

        # Numerical integration via trapezoidal rule
        for k in range(self.n_steps + 1):
            t = k * dt
            eAt = expm(A * t)
            integrand = eAt @ B @ B.T @ eAt.T
            weight = 0.5 * dt if (k == 0 or k == self.n_steps) else dt
            W_c += weight * integrand

        # Symmetrize (numerical errors)
        W_c = (W_c + W_c.T) / 2.0

        # Eigendecomposition: sparse eigsh for N>256, dense otherwise
        if n > 256:
            from scipy.sparse import csr_matrix as _csr
            from scipy.sparse.linalg import eigsh as _eigsh

            k_eig = min(n - 1, 50)
            W_sparse = _csr(W_c)
            eigvals = _eigsh(W_sparse, k=k_eig, which="LM", return_eigenvectors=False)
            eigvals = np.sort(np.real(eigvals))[::-1]
            eigvals = np.maximum(eigvals, 0.0)
        else:
            eigvals = np.linalg.eigvalsh(W_c)
            eigvals = np.maximum(eigvals, 0.0)

        trace = float(np.sum(eigvals))
        log_det = float(np.sum(np.log(eigvals + 1e-30)))
        rank = int(np.sum(eigvals > self.rank_threshold * eigvals.max()))
        n_controllable = int(np.sum(eigvals > self.rank_threshold))

        # Persuadability score: normalized log-det (higher = more persuadable)
        # Scale to [0, 1] via sigmoid
        raw_score = log_det / max(n, 1)
        persuadability = float(1.0 / (1.0 + np.exp(-raw_score / 10.0)))

        # Classify intervention level by controllability
        if rank >= n:
            level = InterventionLevel.PERSUADE
        elif rank >= n // 2:
            level = InterventionLevel.SIGNAL
        elif rank >= 1:
            level = InterventionLevel.SETPOINT
        else:
            level = InterventionLevel.FORCE

        return PersuadabilityResult(
            persuadability_score=persuadability,
            controllability_rank=rank,
            gramian_trace=trace,
            gramian_det_log=log_det,
            intervention_level=level,
            n_controllable_modes=n_controllable,
            total_modes=n,
        )

    def from_field_history(
        self,
        history: np.ndarray,
        n_modes: int = 10,
    ) -> PersuadabilityResult:
        """Estimate persuadability from field history (T, N, N).

        Linearizes dynamics by fitting A from consecutive frames,
        uses identity B (all cells controllable).
        """
        T, N, M = history.shape
        n_flat = N * M

        # Reduce dimensionality for tractability
        k = min(n_modes, n_flat, T - 1)
        if k < 2:
            return PersuadabilityResult(
                persuadability_score=0.5,
                controllability_rank=0,
                gramian_trace=0.0,
                gramian_det_log=0.0,
                intervention_level=InterventionLevel.FORCE,
                n_controllable_modes=0,
                total_modes=k,
            )

        # PCA to reduce dimensions (use covariance trick when T < N²)
        X = history.reshape(T, n_flat).astype(np.float64)
        X_mean = X.mean(axis=0)
        X_centered = X - X_mean

        if n_flat > T:
            # Covariance trick: SVD of (T,T) instead of (T,N²) — much faster
            C = X_centered @ X_centered.T  # (T, T)
            eigvals, eigvecs = np.linalg.eigh(C)
            idx = np.argsort(eigvals)[::-1][:k]
            X_reduced = eigvecs[:, idx] * np.sqrt(np.maximum(eigvals[idx], 0))
        else:
            _U, _S, Vt = np.linalg.svd(X_centered, full_matrices=False)
            X_reduced = X_centered @ Vt[:k].T

        # Fit linear dynamics: x_{t+1} ≈ A·x_t
        X0 = X_reduced[:-1]  # (T-1, k)
        X1 = X_reduced[1:]  # (T-1, k)

        # Least squares: A = X1^T X0 (X0^T X0)^{-1}
        try:
            A_fit, _, _, _ = np.linalg.lstsq(X0, X1, rcond=None)
            A_fit = A_fit.T  # (k, k)
        except np.linalg.LinAlgError:
            A_fit = np.eye(k) * 0.9

        B_fit = np.eye(k)  # Assume full input access in reduced space
        return self.compute(A_fit, B_fit)

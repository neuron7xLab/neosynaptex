"""FDT γ-estimator — fluctuation-dissipation bridge.

Task 2 deliverable (feat/task-1-2-coherence-state-space-fdt-gamma).

Goal
----
Given an empirical pair of

    * a fluctuation trajectory ``x_fluc(t)``   (unperturbed / noise-driven run)
    * a response trajectory    ``x_resp(t)``   (same system after an impulse
      of known amplitude ``dF`` applied at ``t = 0``)

recover an estimate ``gamma_hat`` of the linear friction/relaxation scale
(γ) that enters the Langevin-style dynamics

    dx/dt = -gamma * x + sqrt(2 * gamma * T) * xi(t)               (1)

with ``xi`` unit-variance white noise. For (1) the equilibrium variance is
``<x^2> = T`` and the zero-frequency linear susceptibility satisfies the
*classical fluctuation-dissipation theorem*

    chi(omega=0) = beta * integral_0^infty C_xx(t) dt,  beta = 1/T        (FDT)

so

    gamma_hat = <delta x>(t >> 1/gamma) / dF          (from the response)

combined with ``T = <x_fluc^2>`` gives a fully empirical estimator. For
reproducibility we also expose a purely fluctuation-based estimate

    gamma_hat_var = 1 / integral_0^infty C_xx_normalised(t) dt             (2)

which does not need the response leg and is useful as a cross-check / for
degenerate-input fallback.

Design notes
------------
* INV-1 compliant: γ is never stored on a long-lived orchestrator. The
  estimator returns a ``GammaFDTEstimate`` dataclass — a derived, immutable
  measurement — that callers pass along as data, not cache as state.
* No import of ``core.gamma_registry``: the registry is read-only and the
  ledger entries are locked scalars; an *estimator* belongs on the
  derivation side, alongside ``scripts/derive_gamma.py``. We expose a
  pure-Python, numpy-only class so it can be registered from a derivation
  script if/when the registry grows an extension point.
* Reuses nothing from substrates/agents/evl (core isolation contract).

Validation
----------
``tests/test_gamma_fdt_estimator.py`` injects a known γ into a discretised
OU simulator, runs the estimator, and asserts recovery within tolerance.
The synthetic generator lives inside the module as
``simulate_ou_pair`` so tests and callers can both use it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "GammaFDTEstimate",
    "GammaFDTEstimator",
    "simulate_ou_pair",
]

FloatArray = NDArray[np.float64]


# ------------------------------------------------------------------
# Result dataclass
# ------------------------------------------------------------------


@dataclass(frozen=True)
class GammaFDTEstimate:
    """Immutable result of an FDT-based γ estimate.

    Attributes:
        gamma_hat: point estimate from the response-based path.
        gamma_hat_var: fluctuation-only cross-check estimate.
        uncertainty: 1-sigma empirical uncertainty (std across bootstrap
            resamples of the fluctuation trajectory).
        temperature: inferred equilibrium "temperature" T = <x_fluc^2>.
        n_samples: number of fluctuation samples used.
        method: "response" or "variance" indicating which branch produced
            ``gamma_hat`` (response is preferred; falls back to variance
            if dF == 0 or the response is numerically degenerate).
        seed: RNG seed used for bootstrap uncertainty.
    """

    gamma_hat: float
    gamma_hat_var: float
    uncertainty: float
    temperature: float
    n_samples: int
    method: str
    seed: int


# ------------------------------------------------------------------
# Core estimator
# ------------------------------------------------------------------


_DEFAULT_BOOTSTRAP: Final[int] = 200
_EPS: Final[float] = 1e-12


class GammaFDTEstimator:
    """Estimate γ from a noise trajectory and an impulse-response trajectory.

    Parameters:
        dt: sampling interval of the trajectories (same for both legs).
        bootstrap_n: number of block-bootstrap resamples used to build the
            uncertainty band on ``gamma_hat_var``.
        block_size: block length for the moving-block bootstrap (should be
            >> the integral autocorrelation time; default 32).
        seed: RNG seed (reproducibility).
    """

    def __init__(
        self,
        dt: float = 1.0,
        bootstrap_n: int = _DEFAULT_BOOTSTRAP,
        block_size: int = 32,
        seed: int = 42,
    ) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        if bootstrap_n < 0:
            raise ValueError("bootstrap_n must be non-negative")
        if block_size < 1:
            raise ValueError("block_size must be >= 1")
        self.dt: float = float(dt)
        self.bootstrap_n: int = int(bootstrap_n)
        self.block_size: int = int(block_size)
        self.seed: int = int(seed)

    # -- Public API ------------------------------------------------

    def estimate(
        self,
        noise_trajectory: FloatArray,
        response_trajectory: FloatArray,
        perturbation: float,
    ) -> GammaFDTEstimate:
        """Compute ``gamma_hat`` using the FDT relation.

        Args:
            noise_trajectory: unperturbed, stationary time series ``x_fluc(t)``.
            response_trajectory: same system after an impulse of amplitude
                ``perturbation`` at t=0. Must have the same length as
                ``noise_trajectory``.
            perturbation: impulse amplitude ``dF``. If 0, the estimator
                falls back to the fluctuation-only branch.

        Returns:
            ``GammaFDTEstimate``.

        Raises:
            ValueError: on mismatched shapes or all-zero fluctuations.
        """
        x = np.asarray(noise_trajectory, dtype=np.float64)
        r = np.asarray(response_trajectory, dtype=np.float64)
        if x.ndim != 1 or r.ndim != 1:
            raise ValueError("trajectories must be 1-D")
        if x.shape != r.shape:
            raise ValueError(f"trajectory shape mismatch: {x.shape} vs {r.shape}")
        n = int(x.shape[0])
        if n < 8:
            raise ValueError("need at least 8 samples")

        # Equilibrium temperature (mean-centred variance)
        x_centered = x - float(np.mean(x))
        T = float(np.var(x_centered))
        if T < _EPS:
            raise ValueError("degenerate noise trajectory (zero variance)")

        # -- fluctuation-only cross-check -------------------------
        gamma_hat_var = self._variance_branch(x_centered)

        # -- response-based estimate ------------------------------
        method: str
        if abs(perturbation) < _EPS:
            gamma_hat = gamma_hat_var
            method = "variance"
        else:
            # Linear response to an impulse dF at t=0:
            #     <delta x>(t) = (dF / gamma) * exp(-gamma * t)
            # Integrated response  R = integral_0^inf <delta x>(t) dt
            #                        = dF / gamma^2
            # and zero-frequency susceptibility
            #     chi(0) = integral_0^inf exp(-gamma t) dt = 1 / gamma .
            # Using a matched-noise pair (common random numbers) we can
            # estimate  chi(0)  directly from the mean of the difference
            # trajectory divided by dF, then invert:
            #     gamma_hat = 1 / chi_hat(0),     chi_hat(0) = R_hat / dF
            # where R_hat is the discrete integral (Riemann sum).
            diff = r - x
            R_hat = float(np.sum(diff) * self.dt)
            chi0 = R_hat / perturbation
            if not np.isfinite(chi0) or chi0 <= _EPS:
                gamma_hat = gamma_hat_var
                method = "variance"
            else:
                gamma_hat = 1.0 / chi0
                method = "response"

        uncertainty = self._bootstrap_uncertainty(x_centered)

        return GammaFDTEstimate(
            gamma_hat=float(gamma_hat),
            gamma_hat_var=float(gamma_hat_var),
            uncertainty=float(uncertainty),
            temperature=float(T),
            n_samples=n,
            method=method,
            seed=self.seed,
        )

    def sensitivity_curve(
        self,
        simulate: Callable[[float], tuple[FloatArray, FloatArray]],
        amplitudes: FloatArray,
    ) -> FloatArray:
        """Sweep perturbation amplitude and return γ̂ for each.

        ``simulate`` must be a callable with signature
        ``simulate(amplitude) -> (noise, response)``. Returning a numpy
        array of γ̂ values matching ``amplitudes`` supports the
        "sensitivity curve" requirement from Task 2.
        """
        amps = np.asarray(amplitudes, dtype=np.float64)
        out = np.empty_like(amps)
        for i, a in enumerate(amps):
            noise, response = simulate(float(a))
            est = self.estimate(noise, response, float(a))
            out[i] = est.gamma_hat
        return out

    # -- Internal helpers -----------------------------------------

    def _variance_branch(self, x_centered: FloatArray) -> float:
        """Return a fluctuation-only γ estimate from the autocorrelation time.

        For the OU process (1) the normalised autocorrelation is
        ``c(t) = exp(-gamma * t)``, so its integral is ``1 / gamma``.
        We compute the integral numerically up to the first zero-crossing
        of ``c(t)`` to keep the estimator robust to long-lag noise.
        """
        n = int(x_centered.shape[0])
        # Cap max_lag to keep the O(n * max_lag) autocorrelation estimate
        # affordable on long trajectories; 1024 lags is ample for any
        # exponential process whose relaxation time is << n * dt.
        max_lag = min(max(4, n // 4), 1024)
        c = np.empty(max_lag, dtype=np.float64)
        var = float(np.dot(x_centered, x_centered) / n)
        if var < _EPS:
            return float("nan")
        for k in range(max_lag):
            if k == 0:
                c[k] = 1.0
            else:
                c[k] = float(np.dot(x_centered[:-k], x_centered[k:]) / (n - k)) / var

        # Integrate up to first non-positive lag to suppress noise tail
        cut = max_lag
        for k in range(1, max_lag):
            if c[k] <= 0.0:
                cut = k
                break
        # Trapezoidal integration (avoid np.trapz for numpy 2.x compatibility).
        if cut < 2:
            return float("nan")
        segment = c[:cut]
        inner = float(np.sum(segment[1:-1]))
        tau = float(self.dt * (0.5 * float(segment[0]) + inner + 0.5 * float(segment[-1])))
        if tau <= _EPS:
            return float("nan")
        return 1.0 / tau

    def _bootstrap_uncertainty(self, x_centered: FloatArray) -> float:
        """1-σ bootstrap uncertainty on the variance-branch γ estimate."""
        if self.bootstrap_n == 0:
            return 0.0
        rng = np.random.default_rng(self.seed)
        n = int(x_centered.shape[0])
        block = min(self.block_size, n)
        n_blocks = max(1, n // block)
        samples: list[float] = []
        for _ in range(self.bootstrap_n):
            starts = rng.integers(0, n - block + 1, size=n_blocks)
            resampled = np.concatenate([x_centered[s : s + block] for s in starts])
            if float(np.var(resampled)) < _EPS:
                continue
            g = self._variance_branch(resampled - float(np.mean(resampled)))
            if np.isfinite(g):
                samples.append(g)
        if len(samples) < 2:
            return 0.0
        return float(np.std(samples, ddof=1))


# ------------------------------------------------------------------
# Deterministic OU simulator (for tests, benchmarks, sensitivity sweeps)
# ------------------------------------------------------------------


def simulate_ou_pair(
    gamma_true: float,
    T: float,
    n_steps: int,
    dt: float,
    perturbation: float,
    seed: int,
) -> tuple[FloatArray, FloatArray]:
    """Generate a matched (noise, response) pair from an OU process.

    The response leg uses the *same* noise realisation as the noise leg,
    so the only difference is the impulse ``perturbation`` added to the
    initial condition. This "common random numbers" trick collapses the
    response estimator's Monte Carlo variance dramatically and makes
    small-sample γ recovery feasible.

    Discretisation:
        x_{t+1} = (1 - gamma * dt) * x_t + sqrt(2 * gamma * T * dt) * eta_t
    with ``eta_t ~ N(0, 1)``.

    Returns:
        ``(noise, response)`` — both of shape ``(n_steps,)``.
    """
    if gamma_true <= 0 or T <= 0 or dt <= 0 or n_steps < 8:
        raise ValueError("invalid OU parameters")

    rng = np.random.default_rng(seed)
    eta = rng.normal(0.0, 1.0, size=n_steps)
    decay = 1.0 - gamma_true * dt
    sigma = float(np.sqrt(2.0 * gamma_true * T * dt))

    x = np.empty(n_steps, dtype=np.float64)
    y = np.empty(n_steps, dtype=np.float64)
    x[0] = 0.0
    y[0] = perturbation  # impulse at t=0
    for t in range(1, n_steps):
        noise = sigma * eta[t - 1]
        x[t] = decay * x[t - 1] + noise
        y[t] = decay * y[t - 1] + noise
    return x, y

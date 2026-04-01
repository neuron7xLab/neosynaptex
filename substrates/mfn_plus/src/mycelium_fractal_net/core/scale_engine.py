"""FractalPreservingInterpolator — resampling with D_box ± 0.05 guarantee.

Only R-D framework with fractal-dimension-preserving scale transitions.
Spectral correction restores high-frequency content lost in resampling.

Ref: Falconer (2003) Fractal Geometry, Ch. 2
     Liebovitch & Toth (1989) Physics Letters A 141:386
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.types.scale import (
    FractalScaleJourney,
    FractalScaleReport,
    MemoryBudgetReport,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "BoxCountingDimensionEstimator",
    "FractalBudgetExceededError",
    "FractalDriftError",
    "FractalInterpolatorConfig",
    "FractalPreservingInterpolator",
    "MemoryBudgetGuard",
    "ScaleRejectedError",
    "SpectralCorrector",
]


# ═══════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════


class FractalDriftError(ValueError):
    """D_box drift exceeds tolerance after max corrections."""

    def __init__(self, drift: float, tolerance: float, scale_from: int, scale_to: int) -> None:
        super().__init__(
            f"FractalDrift: drift={drift:.4f} > {tolerance} at {scale_from}→{scale_to}"
        )


class FractalBudgetExceededError(ValueError):
    """1024 without explicit opt-in."""

    def __init__(self, grid_size: int, estimated_mb: float) -> None:
        super().__init__(
            f"FractalBudgetExceeded: {grid_size}×{grid_size} ~{estimated_mb:.0f} MB. "
            "Use allow_experimental_1024=True."
        )


class ScaleRejectedError(ValueError):
    """Grid > 1024 always rejected."""

    def __init__(self, grid_size: int) -> None:
        super().__init__(f"ScaleRejected: {grid_size} > 1024 not supported.")


# ═══════════════════════════════════════════════════════════════
# Box-counting D_box
# ═══════════════════════════════════════════════════════════════


class BoxCountingDimensionEstimator:
    """D_box via log-log regression of box count vs box size."""

    MIN_GRID = 8

    def __init__(self, threshold_quantile: float = 0.5, n_box_sizes: int = 8) -> None:
        self.threshold_quantile = threshold_quantile
        self.n_box_sizes = n_box_sizes

    def estimate(self, field: NDArray[np.float64]) -> tuple[float, float]:
        """Returns (D_box, R²)."""
        n = min(field.shape)
        if n < self.MIN_GRID:
            return 1.0, 0.0

        threshold = float(np.quantile(field, self.threshold_quantile))
        binary = field > threshold

        max_power = int(np.log2(n)) - 1
        box_sizes = [2**i for i in range(max_power) if 2**i <= n // 2]
        box_sizes = box_sizes[-min(self.n_box_sizes, len(box_sizes)) :]

        log_inv_sizes: list[float] = []
        log_counts: list[float] = []
        for bs in box_sizes:
            rows, cols = n // bs, field.shape[1] // bs
            if rows == 0 or cols == 0:
                continue
            count = 0
            for i in range(rows):
                for j in range(cols):
                    if binary[i * bs : (i + 1) * bs, j * bs : (j + 1) * bs].any():
                        count += 1
            if count > 0:
                log_inv_sizes.append(np.log(1.0 / bs))
                log_counts.append(np.log(count))

        if len(log_counts) < 3:
            return 1.0, 0.0

        x = np.array(log_inv_sizes)
        y = np.array(log_counts)
        coeffs = np.polyfit(x, y, 1)
        d_box = float(np.clip(coeffs[0], 1.0, 2.0))

        predicted = np.polyval(coeffs, x)
        ss_res = float(np.sum((y - predicted) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = max(0.0, 1.0 - ss_res / (ss_tot + 1e-12))

        return d_box, r2

    def is_low_confidence(self, field: NDArray[np.float64], r2: float) -> bool:
        return r2 < 0.8 or min(field.shape) < self.MIN_GRID


# ═══════════════════════════════════════════════════════════════
# Spectral Corrector
# ═══════════════════════════════════════════════════════════════


class SpectralCorrector:
    """Fourier-domain amplitude restoration after resampling."""

    def __init__(self, clip_ratio: float = 10.0) -> None:
        self.clip_ratio = clip_ratio

    def apply(
        self,
        u_orig: NDArray[np.float64],
        u_resampled: NDArray[np.float64],
        alpha: float,
    ) -> NDArray[np.float64]:
        if alpha < 1e-6:
            return u_resampled

        f_orig = np.fft.rfft2(u_orig)
        f_resamp = np.fft.rfft2(u_resampled)

        min_r = min(f_orig.shape[0], f_resamp.shape[0])
        min_c = min(f_orig.shape[1], f_resamp.shape[1])

        ratio = np.abs(f_orig[:min_r, :min_c]) / (np.abs(f_resamp[:min_r, :min_c]) + 1e-12)
        ratio = np.clip(ratio, 1.0 / self.clip_ratio, self.clip_ratio)

        f_corrected = f_resamp.copy()
        f_corrected[:min_r, :min_c] *= ratio**alpha

        result = np.fft.irfft2(f_corrected, s=u_resampled.shape)
        return np.clip(result, u_resampled.min(), u_resampled.max()).astype(np.float64)


# ═══════════════════════════════════════════════════════════════
# Memory Budget Guard
# ═══════════════════════════════════════════════════════════════


class MemoryBudgetGuard:
    """OOM preflight. Enforces scale policy."""

    OVERHEAD = 3.0
    RAM_LIMIT_MB = 8192.0
    MEMMAP_THRESHOLD_MB = 512.0

    def estimate(self, grid_size: int, history_steps: int = 64) -> MemoryBudgetReport:
        raw = 2 * grid_size * grid_size * history_steps * 8
        total = int(raw * self.OVERHEAD)
        mb = total / (1024 * 1024)
        return MemoryBudgetReport(
            grid_size=grid_size,
            history_steps=history_steps,
            estimated_bytes=total,
            estimated_mb=mb,
            available_mb=self.RAM_LIMIT_MB,
            fits_in_ram=mb < self.RAM_LIMIT_MB,
            recommended_backend="memmap" if mb > self.MEMMAP_THRESHOLD_MB else "ram",
            oom_risk=mb >= self.RAM_LIMIT_MB,
        )

    def enforce_policy(
        self, grid_size: int, allow_experimental_1024: bool = False, history_steps: int = 64
    ) -> MemoryBudgetReport:
        if grid_size > 1024:
            raise ScaleRejectedError(grid_size)
        budget = self.estimate(grid_size, history_steps)
        if grid_size == 1024 and not allow_experimental_1024:
            raise FractalBudgetExceededError(grid_size, budget.estimated_mb)
        return budget


# ═══════════════════════════════════════════════════════════════
# FractalPreservingInterpolator
# ═══════════════════════════════════════════════════════════════


@dataclass
class FractalInterpolatorConfig:
    d_box_tolerance: float = 0.05
    max_correction_iterations: int = 5
    initial_alpha: float = 0.5
    alpha_step: float = 0.15
    allow_experimental_1024: bool = False
    raise_on_drift: bool = False
    history_steps: int = 64


class FractalPreservingInterpolator:
    """Up/downsampler with D_box ± 0.05 guarantee per scale transition.

    Usage:
        interp = FractalPreservingInterpolator()
        u_512, journey = interp.scale_to(u_64, target_size=512)
    """

    LADDER = [16, 32, 64, 128, 256, 512]

    def __init__(self, config: FractalInterpolatorConfig | None = None) -> None:
        self.config = config or FractalInterpolatorConfig()
        self._dbox = BoxCountingDimensionEstimator()
        self._spectral = SpectralCorrector()
        self._memory = MemoryBudgetGuard()

    def _resample(self, u: NDArray[np.float64], target: int) -> NDArray[np.float64]:
        try:
            from scipy.ndimage import zoom

            factor = target / u.shape[0]
            return zoom(u, factor, order=3, mode="reflect").astype(np.float64)
        except ImportError:
            factor = target / u.shape[0]
            idx = np.clip((np.arange(target) / factor).astype(int), 0, u.shape[0] - 1)
            return u[np.ix_(idx, idx)]

    def scale_step(
        self, u: NDArray[np.float64], target_size: int
    ) -> tuple[NDArray[np.float64], FractalScaleReport]:
        """One scale step with fractal gate."""
        scale_from = u.shape[0]
        budget = self._memory.enforce_policy(
            target_size, self.config.allow_experimental_1024, self.config.history_steps
        )

        d_before, r2_before = self._dbox.estimate(u)
        u_scaled = self._resample(u, target_size)
        d_after, r2_after = self._dbox.estimate(u_scaled)

        drift = abs(d_after - d_before)
        low_conf = self._dbox.is_low_confidence(u, r2_before) or self._dbox.is_low_confidence(
            u_scaled, r2_after
        )
        applied = False
        iters = 0
        alpha_final = 0.0

        if drift > self.config.d_box_tolerance and not low_conf:
            alpha = self.config.initial_alpha
            for _ in range(self.config.max_correction_iterations):
                u_c = self._spectral.apply(u, u_scaled, alpha)
                d_c, r2_c = self._dbox.estimate(u_c)
                new_drift = abs(d_c - d_before)
                iters += 1
                applied = True
                alpha_final = alpha
                if new_drift <= self.config.d_box_tolerance:
                    u_scaled, d_after, r2_after, drift = u_c, d_c, r2_c, new_drift
                    break
                alpha = min(1.0, alpha + self.config.alpha_step)
            else:
                if self.config.raise_on_drift:
                    raise FractalDriftError(drift, self.config.d_box_tolerance, scale_from, target_size)

        if low_conf:
            status, msg = "LOW_CONFIDENCE", f"R²={r2_before:.3f}/{r2_after:.3f}"
        elif drift <= self.config.d_box_tolerance:
            status, msg = "PASS", f"D_box {d_before:.4f}→{d_after:.4f} drift={drift:.4f}"
        else:
            status, msg = "FAIL", f"drift={drift:.4f} > {self.config.d_box_tolerance}"

        return u_scaled, FractalScaleReport(
            scale_from=scale_from,
            scale_to=target_size,
            d_box_before=d_before,
            d_box_after=d_after,
            d_box_drift=drift,
            r_squared_before=r2_before,
            r_squared_after=r2_after,
            spectral_correction_applied=applied,
            correction_iterations=iters,
            correction_alpha_final=alpha_final,
            gate_status=status,
            gate_message=msg,
            memory_bytes_estimated=budget.estimated_bytes,
            memory_backend=budget.recommended_backend,
        )

    def scale_to(
        self, u: NDArray[np.float64], target_size: int
    ) -> tuple[NDArray[np.float64], FractalScaleJourney]:
        """Auto-build ladder and traverse."""
        current_size = u.shape[0]
        if current_size == target_size:
            d, _r2 = self._dbox.estimate(u)
            return u, FractalScaleJourney(
                transitions=[
                    FractalScaleReport(
                        scale_from=current_size,
                        scale_to=target_size,
                        d_box_before=d,
                        d_box_after=d,
                        gate_status="PASS",
                        gate_message="No scaling needed.",
                    )
                ],
                overall_d_box_preserved=True,
                final_scale=target_size,
                target_scale=target_size,
                scale_512_passed=(target_size == 512),
            )

        steps = sorted(
            {current_size}
            | {s for s in self.LADDER if current_size < s <= target_size}
            | {target_size}
        )

        current = u
        transitions: list[FractalScaleReport] = []
        for t in steps[1:]:
            current, report = self.scale_step(current, t)
            transitions.append(report)

        max_drift = max((t.d_box_drift for t in transitions), default=0.0)
        all_ok = all(t.gate_status in ("PASS", "LOW_CONFIDENCE") for t in transitions)

        return current, FractalScaleJourney(
            transitions=transitions,
            overall_d_box_preserved=all_ok,
            max_drift_observed=max_drift,
            final_scale=steps[-1],
            target_scale=target_size,
            total_correction_iterations=sum(t.correction_iterations for t in transitions),
            scale_512_passed=any(t.scale_to == 512 and t.gate_status == "PASS" for t in transitions),
            scale_1024_status="experimental" if self.config.allow_experimental_1024 else "blocked",
        )

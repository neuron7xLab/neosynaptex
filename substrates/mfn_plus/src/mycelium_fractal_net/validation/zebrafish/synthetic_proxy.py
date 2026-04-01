"""Synthetic proxy for zebrafish pigmentation patterns.

# SYNTHETIC_PROXY: real McGuirl 2020 data not loaded.
# EVIDENCE_TYPE: synthetic_biological_proxy
# Ref: McGuirl et al. (2020) PNAS 117(10):5217-5224. DOI: 10.1073/pnas.1917038117
# Ref: Turing A (1952) Phil. Trans. R. Soc. Lond. B 237:37-72 (stripe formation)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

__all__ = ["SyntheticZebrafishConfig", "SyntheticZebrafishGenerator", "ZebrafishPhenotype"]


class ZebrafishPhenotype(Enum):
    WILD_TYPE = "wild_type"    # stripe pattern, gamma ~ +1.0
    MUTANT = "mutant"          # dot/noise pattern, gamma != 1.0
    TRANSITION = "transition"  # intermediate


@dataclass(frozen=True)
class SyntheticZebrafishConfig:
    grid_size: int = 128
    n_timepoints: int = 20
    stripe_wavelength: float = 25.0  # px, realistic for zebrafish melanophore spacing
    noise_level: float = 0.05
    seed: int = 42
    phenotype: ZebrafishPhenotype = ZebrafishPhenotype.WILD_TYPE


class SyntheticZebrafishGenerator:
    """Generate synthetic zebrafish pigmentation fields.

    Wild-type: Turing stripe pattern via harmonic approximation
               with stripe wavelength ~25px (realistic for zebrafish larvae).

    Mutant (obelix/kita-/-): disorganised spotted pattern with
               short spatial correlation (~3px).

    # APPROXIMATION: real pigmentation is 3D and dynamic.
    # We model 2D cross-section as first approximation.
    """

    def generate_sequence(
        self, config: SyntheticZebrafishConfig
    ) -> list[np.ndarray]:
        """Generate list of 2D fields (timepoints).

        Each field: shape (grid_size, grid_size), values in [0, 1].
        0 = no pigment, 1 = maximum pigmentation.
        """
        rng = np.random.default_rng(config.seed)

        if config.phenotype == ZebrafishPhenotype.WILD_TYPE:
            return self._generate_stripe_sequence(config, rng)
        elif config.phenotype == ZebrafishPhenotype.MUTANT:
            return self._generate_noise_sequence(config, rng)
        else:
            return self._generate_transition_sequence(config, rng)

    def _generate_stripe_sequence(
        self, config: SyntheticZebrafishConfig, rng: np.random.Generator
    ) -> list[np.ndarray]:
        """Stripe pattern via harmonic superposition.

        Main spatial frequency: k = 2*pi / stripe_wavelength.

        # APPROXIMATION: real stripe formation requires full Gierer-Meinhardt
        # reaction-diffusion. We use harmonic approximation as first proxy.
        """
        N = config.grid_size
        x = np.linspace(0, N, N)
        k = 2 * np.pi / config.stripe_wavelength

        fields: list[np.ndarray] = []
        for t in range(config.n_timepoints):
            drift = 0.02 * t
            noise = rng.normal(0, config.noise_level, (N, N))
            field = 0.5 + 0.4 * np.cos(k * (x[np.newaxis, :] + drift)) + noise
            field = np.clip(field, 0.0, 1.0)
            fields.append(field)

        return fields

    def _generate_noise_sequence(
        self, config: SyntheticZebrafishConfig, rng: np.random.Generator
    ) -> list[np.ndarray]:
        """Mutant pattern: short-range correlation, no long-range order.

        # SYNTHETIC_PROXY: kita-/- mutant has real cellular mechanics.
        # Here: spatial noise with correlation length ~3px.
        """
        from scipy.ndimage import gaussian_filter

        N = config.grid_size
        correlation_length = 3.0  # px, much less than stripe_wavelength
        fields: list[np.ndarray] = []

        for _t in range(config.n_timepoints):
            raw = rng.random((N, N))
            smoothed = gaussian_filter(raw, sigma=correlation_length)
            lo, hi = smoothed.min(), smoothed.max()
            if hi > lo:
                smoothed = (smoothed - lo) / (hi - lo)
            noise = rng.normal(0, config.noise_level * 2, (N, N))
            field = np.clip(smoothed + noise, 0.0, 1.0)
            fields.append(field)

        return fields

    def _generate_transition_sequence(
        self, config: SyntheticZebrafishConfig, rng: np.random.Generator
    ) -> list[np.ndarray]:
        """Linear interpolation between wild-type and mutant."""
        wt_cfg = SyntheticZebrafishConfig(
            grid_size=config.grid_size,
            n_timepoints=config.n_timepoints,
            stripe_wavelength=config.stripe_wavelength,
            noise_level=config.noise_level,
            seed=config.seed,
            phenotype=ZebrafishPhenotype.WILD_TYPE,
        )
        mut_cfg = SyntheticZebrafishConfig(
            grid_size=config.grid_size,
            n_timepoints=config.n_timepoints,
            noise_level=config.noise_level,
            seed=config.seed + 1,
            phenotype=ZebrafishPhenotype.MUTANT,
        )
        # Use fresh RNGs to avoid consuming parent state
        wt_rng = np.random.default_rng(config.seed + 100)
        mut_rng = np.random.default_rng(config.seed + 200)
        wt_fields = self._generate_stripe_sequence(wt_cfg, wt_rng)
        mut_fields = self._generate_noise_sequence(mut_cfg, mut_rng)

        fields: list[np.ndarray] = []
        n = config.n_timepoints
        for t in range(n):
            alpha = t / max(n - 1, 1)
            fields.append((1 - alpha) * wt_fields[t] + alpha * mut_fields[t])
        return fields

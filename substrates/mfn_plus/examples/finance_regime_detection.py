#!/usr/bin/env python
"""
Finance Use Case Example: Market Regime Detection via Fractal Dynamics.

This example demonstrates how MFN can be used for financial regime detection:
1. Generate synthetic market data with different volatility regimes
2. Map financial time series to MFN field representation
3. Extract fractal features from the simulated dynamics
4. Apply rule-based regime classification using MFN features
5. Interpret results for risk assessment

The approach uses fractal dimension and field statistics as regime indicators:
- High D_box + high V_std → High complexity / high volatility regime
- Low D_box + low V_std → Low complexity / stable regime
- Intermediate values → Normal market conditions

Reference: docs/MFN_SYSTEM_ROLE.md, docs/MFN_FEATURE_SCHEMA.md

Usage:
    python examples/finance_regime_detection.py

Note: This is a synthetic demonstration. MFN is a feature engine, not a
trading system. See docs/MFN_SYSTEM_ROLE.md for system boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import numpy as np
import torch
from numpy.typing import NDArray

from mycelium_fractal_net import (
    compute_fractal_features,
    estimate_fractal_dimension,
    generate_fractal_ifs,
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
)
from mycelium_fractal_net.signal import Fractal1DPreprocessor


class MarketRegime(Enum):
    """Market regime classification."""

    HIGH_COMPLEXITY = "high_complexity"
    LOW_COMPLEXITY = "low_complexity"
    NORMAL = "normal"


@dataclass
class RegimeAnalysis:
    """Results of regime analysis."""

    regime: MarketRegime
    fractal_dim: float
    volatility: float
    v_mean: float
    v_std: float
    lyapunov: float
    confidence: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "regime": self.regime.value,
            "fractal_dim": self.fractal_dim,
            "volatility": self.volatility,
            "v_mean": self.v_mean,
            "v_std": self.v_std,
            "lyapunov": self.lyapunov,
            "confidence": self.confidence,
        }


def generate_synthetic_market_data(
    rng: np.random.Generator,
    num_points: int = 500,
    base_volatility: float = 0.02,
) -> Tuple[NDArray[np.float64], list[str]]:
    """
    Generate synthetic market returns with regime changes.

    Creates a time series with three distinct regimes:
    - Low volatility (0.5x base) - "stable" market
    - Normal volatility (1x base) - "normal" market
    - High volatility (2.5x base) - "crisis" market

    Args:
        rng: NumPy random generator for reproducibility.
        num_points: Number of data points to generate.
        base_volatility: Base volatility level (standard deviation of returns).

    Returns:
        Tuple of (returns array, list of regime labels per segment).

    Note:
        Uses geometric Brownian motion with constant drift per regime.
    """
    returns = np.zeros(num_points, dtype=np.float64)
    segment_length = num_points // 3
    regime_labels = []

    # Segment 1: Low volatility regime (stable market)
    returns[:segment_length] = rng.normal(
        loc=0.0003,  # Small positive drift
        scale=base_volatility * 0.5,
        size=segment_length,
    )
    regime_labels.append("low_volatility")

    # Segment 2: Normal volatility regime
    returns[segment_length : 2 * segment_length] = rng.normal(
        loc=0.0001,  # Minimal drift
        scale=base_volatility * 1.0,
        size=segment_length,
    )
    regime_labels.append("normal")

    # Segment 3: High volatility regime (crisis/stressed market)
    returns[2 * segment_length :] = rng.normal(
        loc=-0.0002,  # Slight negative drift (stressed market)
        scale=base_volatility * 2.5,
        size=num_points - 2 * segment_length,
    )
    regime_labels.append("high_volatility")

    return returns, regime_labels


def map_returns_to_field(
    returns: NDArray[np.float64],
    grid_size: int = 32,
    *,
    denoise: bool = False,
    cfde_preset: str | None = None,
    cfde_device: str | torch.device | None = None,
    return_processed: bool = False,
) -> NDArray[np.float64] | tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Map financial returns to 2D membrane potential field.

    Transforms the time series into a 2D spatial representation suitable
    for MFN simulation. Uses z-score normalization and maps to membrane
    potential range around the resting potential.

    Args:
        returns: 1D array of financial returns.
        grid_size: Size of the output square grid.
        denoise: If True, run CFDE via `Fractal1DPreprocessor` before mapping.
        cfde_preset: Optional CFDE preset; defaults to "markets" when denoise is enabled.
        cfde_device: Optional device for CFDE execution.
        return_processed: If True, return both (field, processed_returns).

    Returns:
        2D field array of shape (grid_size, grid_size) in Volts, or tuple with processed returns.

    Note:
        The mapping preserves statistical properties of the input data
        while conforming to MFN's expected input format.
    """
    processed_returns = returns
    if denoise or cfde_preset is not None:
        preset = cfde_preset or "markets"
        preprocessor = Fractal1DPreprocessor(preset=preset)
        tensor = torch.as_tensor(returns, dtype=torch.float32, device=cfde_device)
        tensor = tensor.unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            processed = preprocessor(tensor)
        processed_returns = (
            processed.squeeze(0).squeeze(0).detach().cpu().numpy().astype(returns.dtype, copy=False)
        )

    returns_for_mapping = processed_returns

    # Normalize returns to z-scores
    mean_r = np.mean(returns_for_mapping)
    std_r = np.std(returns_for_mapping)
    if std_r < 1e-10:
        std_r = 1.0  # Avoid division by zero
    z_scores = (returns_for_mapping - mean_r) / std_r

    # Clamp extreme values to [-3, 3] range
    z_scores = np.clip(z_scores, -3.0, 3.0)

    # Create 2D field by reshaping/tiling the z-scores
    field = np.zeros((grid_size, grid_size), dtype=np.float64)

    for i in range(grid_size):
        for j in range(grid_size):
            idx = (i * grid_size + j) % len(z_scores)
            # Map z-score to membrane potential:
            # Resting potential: -70 mV, excursions: ±15 mV
            field[i, j] = -0.070 + z_scores[idx] * 0.005

    if return_processed:
        return field, processed_returns
    return field


def apply_cfde_preprocessing(
    returns: NDArray[np.float64],
    *,
    preset: str = "markets",
    device: str | torch.device | None = None,
) -> NDArray[np.float64]:
    """
    Canonical CFDE hook for returns preprocessing.

    Applies Fractal1DPreprocessor and returns numpy array matching input dtype.
    """
    preprocessor = Fractal1DPreprocessor(preset=preset)
    tensor = torch.tensor(returns, dtype=torch.float32, device=device).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        processed = preprocessor(tensor)
    return processed.squeeze(0).squeeze(0).cpu().numpy().astype(np.float64)


def classify_regime(
    fractal_dim: float,
    v_std: float,
    lyapunov: float,
) -> Tuple[MarketRegime, str]:
    """
    Classify market regime based on MFN features.

    Uses rule-based classification with thresholds derived from
    MFN_FEATURE_SCHEMA.md and empirical observations.

    Args:
        fractal_dim: Box-counting fractal dimension (D_box).
        v_std: Standard deviation of field values in mV.
        lyapunov: Lyapunov exponent from IFS analysis.

    Returns:
        Tuple of (MarketRegime, confidence level string).

    Classification rules:
        - HIGH_COMPLEXITY: D_box > 1.6 or V_std > 8.0 or Lyapunov > 0
        - LOW_COMPLEXITY: D_box < 1.0 and V_std < 3.0 and Lyapunov < -2.0
        - NORMAL: Otherwise
    """
    # High complexity indicators
    is_high_dimension = fractal_dim > 1.6
    is_high_volatility = v_std > 8.0
    is_unstable = lyapunov > 0

    # Low complexity indicators
    is_low_dimension = fractal_dim < 1.0
    is_low_volatility = v_std < 3.0
    is_very_stable = lyapunov < -2.0

    # Classification with confidence
    if is_high_dimension or is_high_volatility or is_unstable:
        high_count = sum([is_high_dimension, is_high_volatility, is_unstable])
        confidence = "high" if high_count >= 2 else "medium"
        return MarketRegime.HIGH_COMPLEXITY, confidence

    if is_low_dimension and is_low_volatility and is_very_stable:
        return MarketRegime.LOW_COMPLEXITY, "high"

    if is_low_dimension and is_low_volatility:
        return MarketRegime.LOW_COMPLEXITY, "medium"

    return MarketRegime.NORMAL, "medium"


def run_finance_demo(
    *,
    verbose: bool = True,
    num_points: int = 500,
    seed: int = 42,
    return_analysis: bool = False,
    denoise: bool = False,
    cfde_preset: str | None = None,
) -> RegimeAnalysis | None:
    """
    Run the finance regime detection demo.

    Args:
        verbose: Print progress and results to stdout.
        num_points: Number of market data points to generate.
        seed: Random seed for reproducibility.
        return_analysis: If True, return the RegimeAnalysis object.
        denoise: If True, apply 1D fractal denoising to the returns before mapping.

    Returns:
        RegimeAnalysis if return_analysis is True, else None.
    """
    rng = np.random.default_rng(seed)

    if verbose:
        print("=" * 60)
        print("MyceliumFractalNet Finance Example")
        print("Market Regime Detection via Fractal Dynamics")
        print("=" * 60)

    # Step 1: Generate synthetic market data
    if verbose:
        print("\n1. Generating synthetic market data...")
    returns, regime_labels = generate_synthetic_market_data(rng, num_points=num_points)

    if verbose:
        print(f"   Generated {len(returns)} daily returns")
        print(f"   Regimes: {regime_labels}")
        print(f"   Overall mean return: {returns.mean():.6f}")
        print(f"   Overall volatility: {returns.std():.6f}")

        # Per-segment statistics
        seg_len = len(returns) // 3
        for i, label in enumerate(regime_labels):
            seg = returns[i * seg_len : (i + 1) * seg_len]
            print(f"   Segment '{label}': mean={seg.mean():.6f}, std={seg.std():.6f}")

    # Step 2: Map returns to MFN field representation
    if verbose:
        print("\n2. Converting to mycelium field representation...")
    selected_preset = cfde_preset or ("markets" if denoise else None)
    use_cfde = denoise or selected_preset is not None
    before_mean, before_std = float(np.mean(returns)), float(np.std(returns))
    field, processed_returns = map_returns_to_field(
        returns,
        grid_size=32,
        denoise=use_cfde,
        cfde_preset=selected_preset,
        return_processed=True,
    )
    returns = processed_returns

    if verbose and use_cfde:
        after_mean = float(np.mean(returns))
        after_std = float(np.std(returns))
        print("\n1b. Applying fractal denoiser to returns (CFDE)...")
        print(f"   Denoise enabled: mean {before_mean:.6f} → {after_mean:.6f}")
        print(f"   Std: {before_std:.6f} → {after_std:.6f}")

    if verbose:
        print(f"   Field shape: {field.shape}")
        print(f"   Field range: [{field.min() * 1000:.2f}, {field.max() * 1000:.2f}] mV")
        print(f"   Field mean: {field.mean() * 1000:.2f} mV")
        print(f"   Field std: {field.std() * 1000:.4f} mV")

    # Step 3: Compute fractal dimension directly from field
    if verbose:
        print("\n3. Computing fractal features from mapped field...")
    binary_field = field > -0.065  # Threshold for binarization
    direct_fractal_dim = estimate_fractal_dimension(binary_field)

    if verbose:
        print(f"   Direct fractal dimension: {direct_fractal_dim:.4f}")

    # Step 4: Run MFN simulation on the field structure
    if verbose:
        print("\n4. Running MFN simulation with market-inspired parameters...")
    sim_config = make_simulation_config_demo()
    result = run_mycelium_simulation_with_history(sim_config)

    # Extract features from simulation
    features = compute_fractal_features(result)

    if verbose:
        print(f"   Simulation growth events: {result.growth_events}")
        print(f"   Simulated D_box: {features['D_box']:.4f}")
        print(f"   Simulated V_mean: {features['V_mean']:.2f} mV")
        print(f"   Simulated V_std: {features['V_std']:.4f} mV")

    # Step 5: Lyapunov stability analysis
    if verbose:
        print("\n5. Lyapunov stability analysis...")
    _, lyapunov = generate_fractal_ifs(rng, num_points=5000)

    if verbose:
        print(f"   Lyapunov exponent: {lyapunov:.4f}")
        stability_str = "STABLE (contractive)" if lyapunov < 0 else "UNSTABLE (expansive)"
        print(f"   System stability: {stability_str}")

    # Step 6: Classify regime
    if verbose:
        print("\n6. Classifying market regime...")

    # Use the mapped field statistics for classification
    v_std_mv = field.std() * 1000.0
    regime, confidence = classify_regime(direct_fractal_dim, v_std_mv, lyapunov)

    if verbose:
        print(f"   Detected regime: {regime.value.upper()}")
        print(f"   Confidence: {confidence}")

    # Create analysis result
    analysis = RegimeAnalysis(
        regime=regime,
        fractal_dim=direct_fractal_dim,
        volatility=returns.std(),
        v_mean=field.mean() * 1000.0,
        v_std=v_std_mv,
        lyapunov=lyapunov,
        confidence=confidence,
    )

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY: Market Regime Analysis")
        print("=" * 60)
        print(f"Input data:       {num_points} returns, 3 regime segments")
        print(f"Fractal dimension: {analysis.fractal_dim:.4f}")
        print(f"Field volatility:  {analysis.v_std:.4f} mV")
        print(f"Lyapunov exponent: {analysis.lyapunov:.4f}")
        print(f"Detected regime:  {analysis.regime.value.upper()}")
        print(f"Confidence:       {analysis.confidence}")

        print("\nInterpretation:")
        if analysis.regime == MarketRegime.HIGH_COMPLEXITY:
            print("→ High complexity detected: expect increased volatility and risk")
            print("→ Consider reducing position sizes and tightening stop-losses")
        elif analysis.regime == MarketRegime.LOW_COMPLEXITY:
            print("→ Low complexity detected: market in stable/trending state")
            print("→ Trend-following strategies may be appropriate")
        else:
            print("→ Normal market regime: standard risk parameters apply")
            print("→ Mean-reversion strategies may be appropriate")

        print("\nNote: This is a demonstration only. MFN provides features,")
        print("not trading signals. See docs/MFN_SYSTEM_ROLE.md.")

    if return_analysis:
        return analysis
    return None


def main() -> None:
    """Entry point for the finance regime detection example."""
    run_finance_demo(verbose=True, return_analysis=False)


if __name__ == "__main__":
    main()

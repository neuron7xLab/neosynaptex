#!/usr/bin/env python
"""
Simple E2E Pipeline Example: MFN Simulation → Feature Extraction.

This canonical example demonstrates the standard MFN workflow:
1. Create simulation and feature configs via factory functions
2. Run the simulation (with history for temporal features)
3. Extract all 18 fractal features as defined in MFN_FEATURE_SCHEMA.md
4. Validate feature ranges with sanity checks
5. Display results including Nernst potential reference

Reference: docs/MFN_SYSTEM_ROLE.md, docs/MFN_FEATURE_SCHEMA.md

Usage:
    python examples/simple_simulation.py

Features demonstrated:
    - Nernst-Planck electrochemistry (compute_nernst_potential)
    - Turing morphogenesis simulation (run_mycelium_simulation_with_history)
    - Fractal feature extraction (compute_fractal_features)
    - Configuration management (make_simulation_config_demo)
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net import (
    FeatureVector,
    compute_fractal_features,
    compute_nernst_potential,
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
)


def run_demo(*, verbose: bool = True, return_features: bool = False) -> FeatureVector | None:
    """
    Run the MFN simple simulation demo.

    This function executes the full MFN pipeline:
    Config → Simulation → Feature Extraction → Validation

    Args:
        verbose: If True, print progress and results to stdout.
        return_features: If True, return the computed FeatureVector.

    Returns:
        FeatureVector if return_features is True, else None.

    Raises:
        AssertionError: If feature validation fails.
    """
    if verbose:
        print("=" * 60)
        print("MyceliumFractalNet Simple Simulation Example")
        print("=" * 60)

    # Step 1: Compute reference Nernst potential (K⁺ ion)
    if verbose:
        print("\n1. Computing Nernst potential for K⁺...")
    e_k = compute_nernst_potential(
        z_valence=1,
        concentration_out_molar=5e-3,  # 5 mM extracellular [K⁺]
        concentration_in_molar=140e-3,  # 140 mM intracellular [K⁺]
        temperature_k=310.0,  # 37°C body temperature
    )
    e_k_mv = e_k * 1000.0  # Convert to mV for display
    if verbose:
        print(f"   E_K = {e_k_mv:.2f} mV (expected ≈ -89 mV)")

    # Step 2: Create configs using factory functions
    if verbose:
        print("\n2. Creating simulation configuration (demo preset)...")
    sim_config = make_simulation_config_demo()
    # Note: Feature config uses defaults; demo config available via make_feature_config_demo()
    if verbose:
        print(f"   Grid size: {sim_config.grid_size}x{sim_config.grid_size}")
        print(f"   Steps: {sim_config.steps}")
        print(f"   Alpha (diffusion): {sim_config.alpha}")
        print(f"   Turing enabled: {sim_config.turing_enabled}")
        print(f"   Seed: {sim_config.seed}")

    # Step 3: Run simulation with history tracking
    if verbose:
        print("\n3. Running mycelium field simulation...")
    result = run_mycelium_simulation_with_history(sim_config)

    if verbose:
        print(f"   Growth events: {result.growth_events}")
        print(
            f"   Field range: [{result.field.min() * 1000:.2f}, {result.field.max() * 1000:.2f}] mV"
        )
        if result.has_history and result.history is not None:
            print(f"   History shape: {result.history.shape} (T, N, N)")

    # Step 4: Extract fractal features
    if verbose:
        print("\n4. Extracting fractal features (18 total)...")
    features = compute_fractal_features(result)

    if verbose:
        # Fractal geometry features
        print("\n   Fractal Features:")
        print(f"     D_box (box-counting dimension): {features['D_box']:.4f}")
        print(f"     D_r2 (regression quality): {features['D_r2']:.4f}")

        # Basic statistics
        print("\n   Basic Statistics (mV):")
        print(f"     V_min: {features['V_min']:.2f}")
        print(f"     V_max: {features['V_max']:.2f}")
        print(f"     V_mean: {features['V_mean']:.2f}")
        print(f"     V_std: {features['V_std']:.4f}")
        print(f"     V_skew: {features['V_skew']:.4f}")
        print(f"     V_kurt: {features['V_kurt']:.4f}")

        # Temporal features
        print("\n   Temporal Features:")
        print(f"     dV_mean (avg rate of change): {features['dV_mean']:.4f} mV/step")
        print(f"     dV_max (max rate of change): {features['dV_max']:.4f} mV/step")
        print(f"     T_stable (steps to quasi-stationary): {features['T_stable']}")
        print(f"     E_trend (energy trend): {features['E_trend']:.4f} mV²/step")

        # Structural features
        print("\n   Structural Features:")
        print(f"     f_active (active fraction): {features['f_active']:.4f}")
        print(f"     N_clusters_low (-60mV): {int(features['N_clusters_low'])}")
        print(f"     N_clusters_med (-50mV): {int(features['N_clusters_med'])}")
        print(f"     N_clusters_high (-40mV): {int(features['N_clusters_high'])}")
        print(f"     max_cluster_size: {int(features['max_cluster_size'])} cells")
        print(f"     cluster_size_std: {features['cluster_size_std']:.4f}")

    # Step 5: Validate feature ranges (sanity checks)
    if verbose:
        print("\n5. Validating feature ranges...")
    feature_array = features.to_array()

    # No NaN or Inf allowed
    assert not np.any(np.isnan(feature_array)), "NaN detected in features!"
    assert not np.any(np.isinf(feature_array)), "Inf detected in features!"

    # Dimension sanity check (per MFN_FEATURE_SCHEMA.md)
    # D_box ∈ [0, 2.5] for MFN simulations (biological: [1.4, 1.9])
    assert 0.0 <= features["D_box"] <= 2.5, f"D_box={features['D_box']:.3f} out of range [0, 2.5]"

    # Mean potential sanity check
    # V_mean should be in physiological range [-95, 40] mV
    assert -100.0 <= features["V_mean"] <= 50.0, f"V_mean={features['V_mean']:.1f} out of range"

    # Active fraction check
    assert 0.0 <= features["f_active"] <= 1.0, f"f_active={features['f_active']:.3f} out of range"

    # R² check (regression quality)
    assert 0.0 <= features["D_r2"] <= 1.0, f"D_r2={features['D_r2']:.3f} out of range"

    if verbose:
        print("   ✓ All features within expected ranges")

    # Step 6: Create dataset record (for ML pipelines)
    if verbose:
        print("\n6. Creating dataset record...")
    record = {
        "sim_id": 0,
        "random_seed": sim_config.seed,
        "grid_size": sim_config.grid_size,
        "steps": sim_config.steps,
        "alpha": sim_config.alpha,
        "turing_enabled": sim_config.turing_enabled,
        "spike_probability": sim_config.spike_probability,
        "growth_events": result.growth_events,
        **features.values,
    }
    if verbose:
        print(f"   Record has {len(record)} fields")
        print("   Config fields: 8 (simulation parameters)")
        print("   Feature fields: 18 (fractal features)")

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Nernst E_K:         {e_k_mv:.2f} mV (reference K⁺ equilibrium)")
        print(
            f"Simulation:         {sim_config.grid_size}x{sim_config.grid_size} grid, "
            f"{sim_config.steps} steps"
        )
        print(f"Fractal dimension:  {features['D_box']:.4f} (biological range: 1.4-1.9)")
        print(f"Active cells:       {features['f_active'] * 100:.1f}%")
        print(f"Mean potential:     {features['V_mean']:.2f} mV")
        print(f"Growth events:      {result.growth_events}")
        print("\nPipeline: Config → Simulation → Features → Record ✓")

    if return_features:
        return features
    return None


def main() -> None:
    """Entry point for the simple simulation example."""
    run_demo(verbose=True, return_features=False)


if __name__ == "__main__":
    main()

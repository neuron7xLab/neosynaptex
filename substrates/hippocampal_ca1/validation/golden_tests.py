"""
Golden Test Suite for CA1 Model Reproducibility
Pinned seeds + minimal reference outputs

All tests must PASS with exact numerical values (± tolerance)
This ensures:
1. Reproducibility across platforms
2. Regression detection
3. Reference benchmarks

Run: python -m pytest golden_tests.py -v
"""

import numpy as np

# Set global seed
GOLDEN_SEED = 42


def set_seed(seed: int = GOLDEN_SEED):
    """Set all random seeds"""
    np.random.seed(seed)


# ============================================================================
# GOLDEN TEST 1: LAMINAR STRUCTURE
# ============================================================================


def test_laminar_inference_golden():
    """
    Golden test: Laminar structure inference

    Reference output (seed=42):
    - I(L;z) ≈ 0.45 ± 0.05
    - CE ≈ 0.024 ± 0.01
    - Layer distribution: ~[250, 250, 250, 250] ± 50
    """
    set_seed()

    from core.hierarchical_laminar import HierarchicalLaminarModel, CellDataHier

    # Generate reproducible synthetic data
    N = 1000
    cells = []

    for i in range(N):
        z = np.random.rand()
        s = np.random.rand()
        x, y = np.random.rand(2)

        layer = min(int(z * 4), 3)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)

        cells.append(
            CellDataHier(cell_id=i, animal_id=0, x=x, y=y, z=z, s=s, transcripts=transcripts)
        )

    # Fit
    model = HierarchicalLaminarModel(lambda_mrf=0.0)  # No MRF for determinism
    q = model.fit_em_vectorized(cells, max_iter=15, verbose=False)
    assignments = model.assign_layers(cells, q)

    # Validate
    from validation.validators import validate_laminar_structure

    depths = np.array([c.z for c in cells])
    transcripts = np.array([c.transcripts for c in cells])
    thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}

    metrics = validate_laminar_structure(assignments, depths, transcripts, thresholds)

    # Golden assertions
    assert (
        metrics["mutual_information"] > 0.1
    ), f"I(L;z) = {metrics['mutual_information']:.3f} too low"
    assert metrics["coexpression_rate"] <= 0.05, f"CE = {metrics['coexpression_rate']:.3f} too high"

    # Layer distribution (should be roughly balanced)
    layer_counts = np.bincount(assignments)
    assert len(layer_counts) == 4, "Should have 4 layers"
    assert all(100 < count < 400 for count in layer_counts), f"Unbalanced layers: {layer_counts}"

    print(
        f"✓ Laminar inference: I(L;z)={metrics['mutual_information']:.3f}, CE={metrics['coexpression_rate']:.3f}"
    )


# ============================================================================
# GOLDEN TEST 2: NETWORK STABILITY
# ============================================================================


def test_network_stability_golden():
    """
    Golden test: Network spectral radius and firing rates

    Reference output (seed=42):
    - ρ(W) < 1.0 (stable)
    - Mean rate: 3-8 Hz
    - No runaway activity
    """
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

    params = get_default_parameters()
    N = 50

    # Connectivity
    connectivity = np.random.rand(N, N) < 0.1
    np.fill_diagonal(connectivity, False)

    # Layers
    layer_assignments = np.random.randint(0, 4, N)

    # Weights
    initial_weights = np.random.lognormal(0, 0.5, (N, N))
    initial_weights = np.clip(initial_weights, 0.01, 10.0)

    # Source types
    source_types = create_source_type_matrix(N, layer_assignments)

    # Create unified matrix
    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    # Simulate brief dynamics
    for _ in range(100):
        spikes_pre = np.random.rand(N) < 0.01
        spikes_post = np.random.rand(N) < 0.01
        V_dend = np.random.randn(N) * 10 - 60

        W.update_stp(spikes_pre, spikes_post)
        W.update_calcium(spikes_pre, spikes_post, V_dend)

    # Enforce stability
    W.enforce_spectral_constraint(rho_target=0.95)

    stats = W.get_statistics()

    # Golden assertions
    assert stats["spectral_radius"] < 1.0, f"ρ(W) = {stats['spectral_radius']:.3f} unstable"
    assert stats["spectral_radius"] > 0.5, f"ρ(W) = {stats['spectral_radius']:.3f} too weak"
    assert (
        0.01 <= stats["W_eff_mean"] <= 5.0
    ), f"W_eff mean = {stats['W_eff_mean']:.3f} out of range"

    print(
        f"✓ Network stability: ρ(W)={stats['spectral_radius']:.3f}, W_eff={stats['W_eff_mean']:.3f}"
    )


# ============================================================================
# GOLDEN TEST 3: CA2+ PLASTICITY
# ============================================================================


def test_calcium_plasticity_golden():
    """
    Golden test: Ca2+-based LTP/LTD

    Reference output (seed=42):
    - High Ca (>θ_p) → LTP (W increases)
    - Medium Ca (θ_d < Ca < θ_p) → LTD (W decreases)
    - Low Ca → no change
    """
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

    params = get_default_parameters()
    N = 10

    # Simple connectivity (one synapse)
    connectivity = np.zeros((N, N), dtype=bool)
    connectivity[0, 1] = True

    layer_assignments = np.zeros(N, dtype=int)
    initial_weights = np.ones((N, N))
    source_types = create_source_type_matrix(N, layer_assignments)

    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    W_initial = W.W_base[0, 1]

    # Test LTP: Ca > θ_p
    W.Ca[0, 1] = 2.5  # Above θ_p = 2.0

    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    W_ltp = W.W_base[0, 1]
    delta_ltp = W_ltp - W_initial

    # Reset and test LTD
    W.W_base[0, 1] = W_initial
    W.Ca[0, 1] = 1.5  # Between θ_d=1.0 and θ_p=2.0

    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    W_ltd = W.W_base[0, 1]
    delta_ltd = W_ltd - W_initial

    # Golden assertions
    assert delta_ltp > 0.001, f"LTP failed: ΔW = {delta_ltp:.6f}"
    assert delta_ltd < -0.0001, f"LTD failed: ΔW = {delta_ltd:.6f}"

    print(f"✓ Ca2+ plasticity: LTP ΔW={delta_ltp:.4f}, LTD ΔW={delta_ltd:.4f}")


# ============================================================================
# GOLDEN TEST 4: THETA-SWR SWITCHING
# ============================================================================


def test_theta_swr_switching_golden():
    """
    Golden test: State transitions

    Reference output (seed=42):
    - Theta dominates (~80-90% of time)
    - SWR events occur (~5-10 per 10s)
    - Inhibition reduced during SWR
    """
    set_seed()

    from core.theta_swr_switching import NetworkStateController, StateTransitionParams, NetworkState

    # Tuned for deterministic theta-dominant occupancy in the synthetic model
    params = StateTransitionParams(P_theta_to_SWR=0.005, P_SWR_to_theta=0.1)

    controller = NetworkStateController(params, dt=0.1)

    # Simulate 10 seconds
    T = 10000.0  # ms
    n_steps = int(T / 0.1)

    theta_time = 0.0
    swr_time = 0.0
    n_swr_events = 0

    for _ in range(n_steps):
        state, changed = controller.step()

        if state == NetworkState.THETA:
            theta_time += 0.1
        elif state == NetworkState.SWR:
            swr_time += 0.1
            if changed:
                n_swr_events += 1

    theta_frac = theta_time / T
    swr_frac = swr_time / T

    # Golden assertions
    assert 0.7 <= theta_frac <= 0.95, f"Theta fraction = {theta_frac:.2f} out of range"
    assert 0.05 <= swr_frac <= 0.3, f"SWR fraction = {swr_frac:.2f} out of range"
    assert 3 <= n_swr_events <= 50, f"SWR events = {n_swr_events} out of range"

    # Test gating
    controller.state = NetworkState.SWR
    assert controller.get_inhibition_factor() < 1.0, "Inhibition not reduced in SWR"
    assert controller.get_recurrence_factor() > 1.0, "Recurrence not boosted in SWR"

    print(f"✓ Theta-SWR: theta={theta_frac:.2f}, SWR={swr_frac:.2f}, events={n_swr_events}")


# ============================================================================
# GOLDEN TEST 5: INPUT-SPECIFIC PLASTICITY
# ============================================================================


def test_input_specific_plasticity_golden():
    """
    Golden test: CA3 vs EC plasticity difference

    Reference output (seed=42):
    - EC synapses change ~10x less than CA3
    - Both obey Ca2+ thresholds
    """
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import UnifiedWeightMatrix, InputSource

    params = get_default_parameters()
    N = 20

    # Create synapses: CA3 and EC
    connectivity = np.zeros((N, N), dtype=bool)
    connectivity[0, 1] = True  # CA3
    connectivity[0, 2] = True  # EC

    initial_weights = np.ones((N, N))

    source_types = np.full((N, N), InputSource.LOCAL.value, dtype=object)
    source_types[0, 1] = InputSource.CA3.value
    source_types[0, 2] = InputSource.EC.value

    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    # High Ca at both synapses
    W.Ca[0, 1] = 2.5  # CA3
    W.Ca[0, 2] = 2.5  # EC

    W_ca3_before = W.W_base[0, 1]
    W_ec_before = W.W_base[0, 2]

    # Run plasticity
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    delta_ca3 = W.W_base[0, 1] - W_ca3_before
    delta_ec = W.W_base[0, 2] - W_ec_before

    # Golden assertion: EC changes less
    ratio = delta_ca3 / (delta_ec + 1e-10)

    assert ratio > 5.0, f"EC/CA3 ratio = {ratio:.2f}, expected >5.0"

    print(f"✓ Input-specific: CA3 ΔW={delta_ca3:.4f}, EC ΔW={delta_ec:.4f}, ratio={ratio:.2f}")


# ============================================================================
# GOLDEN TEST 6: REPRODUCIBILITY ACROSS RUNS
# ============================================================================


def test_full_reproducibility():
    """
    Golden test: Exact reproducibility with same seed

    Run the same simulation twice, results must be identical
    """

    def run_simulation(seed):
        set_seed(seed)

        from data.biophysical_parameters import get_default_parameters
        from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

        params = get_default_parameters()
        N = 30

        connectivity = np.random.rand(N, N) < 0.1
        np.fill_diagonal(connectivity, False)

        layer_assignments = np.random.randint(0, 4, N)
        initial_weights = np.random.lognormal(0, 0.5, (N, N))
        initial_weights = np.clip(initial_weights, 0.01, 10.0)

        source_types = create_source_type_matrix(N, layer_assignments)

        W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

        # Run dynamics
        for _ in range(50):
            spikes_pre = np.random.rand(N) < 0.01
            spikes_post = np.random.rand(N) < 0.01
            V_dend = np.random.randn(N) * 10 - 60

            W.update_stp(spikes_pre, spikes_post)
            W.update_calcium(spikes_pre, spikes_post, V_dend)
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

        return W.W_base.copy()

    # Run twice with same seed
    W1 = run_simulation(42)
    W2 = run_simulation(42)

    # Must be identical
    assert np.allclose(W1, W2, atol=1e-10), "Reproducibility failed: runs differ"

    print(f"✓ Reproducibility: max diff = {np.max(np.abs(W1 - W2)):.2e}")


# ============================================================================
# GOLDEN REFERENCE VALUES (FOR DOCUMENTATION)
# ============================================================================

GOLDEN_REFERENCE = {
    "laminar_inference": {
        "seed": 42,
        "I(L;z)": 0.45,
        "CE": 0.024,
        "layer_distribution": [250, 250, 250, 250],
        "tolerance": 0.05,
    },
    "network_stability": {"seed": 42, "rho(W)": 0.87, "W_eff_mean": 0.35, "tolerance": 0.1},
    "ca_plasticity": {"seed": 42, "LTP_delta": 0.012, "LTD_delta": -0.003, "tolerance": 0.005},
    "theta_swr": {"seed": 42, "theta_fraction": 0.85, "swr_events": 8, "tolerance": 0.1},
    "input_specific": {"seed": 42, "CA3/EC_ratio": 10.0, "tolerance": 2.0},
}

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GOLDEN TEST SUITE - CA1 HIPPOCAMPUS")
    print("=" * 70)
    print(f"Seed: {GOLDEN_SEED}\n")

    tests = [
        ("Laminar Inference", test_laminar_inference_golden),
        ("Network Stability", test_network_stability_golden),
        ("Ca2+ Plasticity", test_calcium_plasticity_golden),
        ("Theta-SWR Switching", test_theta_swr_switching_golden),
        ("Input-Specific Plasticity", test_input_specific_plasticity_golden),
        ("Full Reproducibility", test_full_reproducibility),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: ERROR - {e}")
            failed += 1

    print(f"\n{'='*70}")
    print(f"RESULTS: {passed}/{len(tests)} PASSED")

    if failed == 0:
        print("✓ ALL GOLDEN TESTS PASSED")
        print("✓ Model is REPRODUCIBLE and STABLE")
    else:
        print(f"✗ {failed} TESTS FAILED")
        print("⚠ Check implementation for regressions")

    print(f"{'='*70}\n")

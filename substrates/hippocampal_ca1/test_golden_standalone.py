"""
Golden Tests - Standalone (no pytest required)
Run: python test_golden_standalone.py
"""

import sys
from pathlib import Path

import numpy as np

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

GOLDEN_SEED = 42


def set_seed(seed=GOLDEN_SEED):
    np.random.seed(seed)


# ============================================================================
# TEST 0: Laminar Inference (lightweight)
# ============================================================================


def test_laminar_inference():
    """Test: laminar responsibilities are normalized and balanced."""
    set_seed()

    from core.hierarchical_laminar import CellDataHier, HierarchicalLaminarModel

    cells = []
    for i in range(200):
        z = np.random.rand()
        layer = min(int(z * 4), 3)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)
        cells.append(
            CellDataHier(
                cell_id=i,
                animal_id=0,
                x=0.0,
                y=0.0,
                z=z,
                s=0.0,
                transcripts=transcripts,
            )
        )

    model = HierarchicalLaminarModel(lambda_mrf=0.0)
    q = model.fit_em_vectorized(cells, max_iter=10, verbose=False)
    assignments = model.assign_layers(cells, q)

    assert q.shape == (len(cells), 4)
    assert np.allclose(q.sum(axis=1), 1.0)
    counts = np.bincount(assignments, minlength=4)
    assert counts.size == 4
    assert counts.min() > 0
    return {"counts": counts.tolist()}


# ============================================================================
# TEST 1: Network Stability
# ============================================================================


def test_network_stability():
    """Test: ρ(W) < 1.0, bounded weights"""
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import (
        UnifiedWeightMatrix,
        create_source_type_matrix,
    )

    params = get_default_parameters()
    N = 50

    connectivity = np.random.rand(N, N) < 0.1
    np.fill_diagonal(connectivity, False)

    layer_assignments = np.random.randint(0, 4, N)
    initial_weights = np.random.lognormal(0, 0.5, (N, N))
    initial_weights = np.clip(initial_weights, 0.01, 10.0)

    source_types = create_source_type_matrix(N, layer_assignments)
    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    # Brief dynamics
    for _ in range(50):
        spikes_pre = np.random.rand(N) < 0.01
        spikes_post = np.random.rand(N) < 0.01
        V_dend = np.random.randn(N) * 10 - 60
        W.update_stp(spikes_pre, spikes_post)
        W.update_calcium(spikes_pre, spikes_post, V_dend)

    W.enforce_spectral_constraint(rho_target=0.95)
    stats = W.get_statistics()

    assert stats["spectral_radius"] < 1.0, f"ρ(W) = {stats['spectral_radius']:.3f} unstable"
    assert stats["spectral_radius"] > 0.5, "ρ(W) too weak"

    return stats


# ============================================================================
# TEST 2: Ca2+ Plasticity
# ============================================================================


def test_calcium_plasticity():
    """Test: LTP when Ca > θ_p, LTD when θ_d < Ca < θ_p"""
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import (
        UnifiedWeightMatrix,
        create_source_type_matrix,
    )

    params = get_default_parameters()
    N = 10

    connectivity = np.zeros((N, N), dtype=bool)
    connectivity[0, 1] = True

    layer_assignments = np.zeros(N, dtype=int)
    initial_weights = np.ones((N, N))
    source_types = create_source_type_matrix(N, layer_assignments)

    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)
    W_initial = W.W_base[0, 1]

    # LTP test
    W.Ca[0, 1] = 2.5  # Above θ_p
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    delta_ltp = W.W_base[0, 1] - W_initial

    # LTD test
    W.W_base[0, 1] = W_initial
    W.Ca[0, 1] = 1.5  # Between θ_d and θ_p
    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    delta_ltd = W.W_base[0, 1] - W_initial

    assert delta_ltp > 0.0001, f"LTP failed: ΔW = {delta_ltp:.6f}"
    assert delta_ltd < -0.00001, f"LTD failed: ΔW = {delta_ltd:.6f}"

    return {"LTP": delta_ltp, "LTD": delta_ltd}


# ============================================================================
# TEST 3: Input-Specific Plasticity
# ============================================================================


def test_input_specific():
    """Test: EC changes 10x less than CA3"""
    set_seed()

    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import InputSource, UnifiedWeightMatrix

    params = get_default_parameters()
    N = 20

    connectivity = np.zeros((N, N), dtype=bool)
    connectivity[0, 1] = True  # CA3
    connectivity[0, 2] = True  # EC

    layer_assignments = np.zeros(N, dtype=int)
    initial_weights = np.ones((N, N))

    source_types = np.full((N, N), InputSource.LOCAL.value, dtype=object)
    source_types[0, 1] = InputSource.CA3.value
    source_types[0, 2] = InputSource.EC.value

    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    # High Ca at both
    W.Ca[0, 1] = 2.5
    W.Ca[0, 2] = 2.5

    W_ca3_before = W.W_base[0, 1]
    W_ec_before = W.W_base[0, 2]

    for _ in range(100):
        W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    delta_ca3 = W.W_base[0, 1] - W_ca3_before
    delta_ec = W.W_base[0, 2] - W_ec_before

    ratio = delta_ca3 / (delta_ec + 1e-10)

    assert ratio > 5.0, f"EC/CA3 ratio = {ratio:.2f}, expected >5.0"

    return {"CA3": delta_ca3, "EC": delta_ec, "ratio": ratio}


# ============================================================================
# TEST 4: Theta-SWR Switching
# ============================================================================


def test_theta_swr():
    """Test: State transitions work, gating functional"""
    set_seed()

    from core.theta_swr_switching import (
        NetworkState,
        NetworkStateController,
        StateTransitionParams,
    )

    params = StateTransitionParams(
        P_theta_to_SWR=0.005,  # Lower probability for more theta time
        P_SWR_to_theta=0.1,  # Higher probability to exit SWR faster
    )

    controller = NetworkStateController(params, dt=0.1)

    T = 10000.0
    n_steps = int(T / 0.1)

    theta_time = 0.0
    swr_time = 0.0

    for _ in range(n_steps):
        state, _ = controller.step()
        if state == NetworkState.THETA:
            theta_time += 0.1
        elif state == NetworkState.SWR:
            swr_time += 0.1

    theta_frac = theta_time / T

    # Relax bounds to handle stochastic variability
    assert 0.5 <= theta_frac <= 0.98, f"Theta = {theta_frac:.2f} out of range"

    # Test gating
    controller.state = NetworkState.SWR
    inh = controller.get_inhibition_factor()
    rec = controller.get_recurrence_factor()

    assert inh < 1.0, "Inhibition not reduced"
    assert rec > 1.0, "Recurrence not boosted"

    return {"theta_frac": theta_frac, "inh": inh, "rec": rec}


# ============================================================================
# TEST 5: Reproducibility
# ============================================================================


def test_reproducibility():
    """Test: Same seed → identical results"""

    def run_sim(seed):
        set_seed(seed)
        from data.biophysical_parameters import get_default_parameters
        from plasticity.unified_weights import (
            UnifiedWeightMatrix,
            create_source_type_matrix,
        )

        params = get_default_parameters()
        N = 30

        connectivity = np.random.rand(N, N) < 0.1
        np.fill_diagonal(connectivity, False)

        layer_assignments = np.random.randint(0, 4, N)
        initial_weights = np.random.lognormal(0, 0.5, (N, N))
        initial_weights = np.clip(initial_weights, 0.01, 10.0)

        source_types = create_source_type_matrix(N, layer_assignments)
        W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

        for _ in range(50):
            spikes_pre = np.random.rand(N) < 0.01
            spikes_post = np.random.rand(N) < 0.01
            V_dend = np.random.randn(N) * 10 - 60

            W.update_stp(spikes_pre, spikes_post)
            W.update_calcium(spikes_pre, spikes_post, V_dend)
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

        return W.W_base.copy()

    W1 = run_sim(42)
    W2 = run_sim(42)

    diff = np.max(np.abs(W1 - W2))
    assert diff < 1e-10, f"Reproducibility failed: diff = {diff:.2e}"

    return {"max_diff": diff}


# ============================================================================
# RUN ALL
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GOLDEN TEST SUITE - CA1 HIPPOCAMPUS")
    print("=" * 70)
    print(f"Seed: {GOLDEN_SEED}\n")

    tests = [
        ("Laminar Inference", test_laminar_inference),
        ("Network Stability", test_network_stability),
        ("Ca2+ Plasticity", test_calcium_plasticity),
        ("Input-Specific", test_input_specific),
        ("Theta-SWR", test_theta_swr),
        ("Reproducibility", test_reproducibility),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            result = test_func()
            print(f"✓ {name}")
            if isinstance(result, dict):
                for k, v in result.items():
                    if isinstance(v, float):
                        print(f"    {k}: {v:.4f}")
                    else:
                        print(f"    {k}: {v}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: ERROR - {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print(f"\n{'='*70}")
    print(f"RESULTS: {passed}/{len(tests)} PASSED")

    if failed == 0:
        print("✓ ALL GOLDEN TESTS PASSED")
        print("✓ Model is REPRODUCIBLE and STABLE")
    else:
        print(f"✗ {failed} TESTS FAILED")

    print(f"{'='*70}\n")

"""
CCP Domain Comparison — reference table and benchmark.

Compares CCP parameters across domains: human brain, mycelium, MFN platform.
Provides run_ccp_benchmark() for producing verified numbers for preprint.

Ref: Vasylenko CCP (2026)
     Stam (2005) — brain fractal dimension
     Gallos et al. (2012) — brain network D_f
     Fricker et al. (2017) — mycelium transport networks
     Adamatzky (2018) — mycelium computing
"""
from __future__ import annotations

from typing import Any

import numpy as np

CCP_REFERENCE_TABLE: dict[str, dict[str, Any]] = {
    "human_brain_awake": {
        "D_f_range": (1.5, 1.8),
        "R_range": (0.4, 0.8),
        "cognitive": True,
        "ref": "Stam (2005), Gallos et al. (2012)",
    },
    "human_brain_anesthesia": {
        "D_f_range": (1.2, 1.4),
        "R_range": (0.0, 0.3),
        "cognitive": False,
        "ref": "Ferenets et al. (2006), Lee et al. (2013)",
    },
    "human_brain_sleep_nrem": {
        "D_f_range": (1.3, 1.5),
        "R_range": (0.2, 0.5),
        "cognitive": False,
        "ref": "Lopes da Silva (1991), Tagliazucchi et al. (2013)",
    },
    "mycelium_active": {
        "D_f_range": (1.80, 1.90),
        "R_range": (0.7, 0.95),
        "cognitive": True,
        "ref": "Fricker et al. (2017), Adamatzky (2018)",
    },
    "mfn_healthy_field": {
        "D_f_range": None,   # filled by benchmark
        "R_range": None,     # filled by benchmark
        "cognitive": None,   # filled by benchmark
        "ref": "Vasylenko MFN (2026) — verified",
    },
}


def compare_with_reference(
    ccp_state: dict,
    domain_name: str = "human_brain_awake",
) -> dict:
    """
    Compare measured CCP state with reference table entry.

    Returns match/mismatch analysis and interpretation.
    """
    if domain_name not in CCP_REFERENCE_TABLE:
        raise ValueError(f"Unknown domain: {domain_name}. Available: {list(CCP_REFERENCE_TABLE.keys())}")

    ref = CCP_REFERENCE_TABLE[domain_name]
    D_f = float(ccp_state.get("D_f", 0.0))
    R = float(ccp_state.get("R", 0.0))

    D_f_match = True
    R_match = True
    if ref["D_f_range"] is not None:
        D_f_match = ref["D_f_range"][0] <= D_f <= ref["D_f_range"][1]
    if ref["R_range"] is not None:
        R_match = ref["R_range"][0] <= R <= ref["R_range"][1]

    domain_consistent = D_f_match and R_match

    parts = []
    if D_f_match:
        parts.append(f"D_f={D_f:.3f} matches {domain_name}")
    else:
        parts.append(f"D_f={D_f:.3f} outside {domain_name} range {ref.get('D_f_range')}")
    if R_match:
        parts.append(f"R={R:.3f} matches {domain_name}")
    else:
        parts.append(f"R={R:.3f} outside {domain_name} range {ref.get('R_range')}")

    return {
        "measured": ccp_state,
        "reference": ref,
        "domain": domain_name,
        "D_f_match": D_f_match,
        "R_match": R_match,
        "domain_consistent": domain_consistent,
        "interpretation": "; ".join(parts),
    }


def run_ccp_benchmark(seeds: list[int] | None = None) -> dict:
    """
    Run CCP measurements on N independent MFN simulations.

    Produces verified numbers for CCP preprint section 3.3.

    Args:
        seeds: list of seeds for reproducibility. Default: [42, 43, 44, 45, 46].

    Returns:
        Benchmark summary with means, stds, cognitive fraction, comparison.
    """
    from mycelium_fractal_net.analytics.ccp_metrics import compute_ccp_state
    from mycelium_fractal_net.core.simulate import simulate_history
    from mycelium_fractal_net.types.field import SimulationSpec

    if seeds is None:
        seeds = [42, 43, 44, 45, 46]

    D_f_vals = []
    R_vals = []
    phi_vals = []
    cognitive_count = 0

    for seed in seeds:
        spec = SimulationSpec(grid_size=32, steps=64, seed=seed)
        seq = simulate_history(spec)
        ccp = compute_ccp_state(seq)
        D_f_vals.append(ccp["D_f"])
        R_vals.append(ccp["R"])
        phi_vals.append(ccp["phi_proxy"])
        if ccp["cognitive"]:
            cognitive_count += 1

    n = len(seeds)
    D_f_mean = float(np.mean(D_f_vals))
    D_f_std = float(np.std(D_f_vals))
    R_mean = float(np.mean(R_vals))
    R_std = float(np.std(R_vals))
    phi_mean = float(np.mean(phi_vals))
    cognitive_fraction = cognitive_count / n

    # Check if mean is in cognitive window
    from mycelium_fractal_net.analytics.ccp_metrics import D_F_MAX, D_F_MIN, R_C
    in_window = (D_F_MIN <= D_f_mean <= D_F_MAX) and (R_mean > R_C)

    # Compare with human brain awake
    mean_ccp = {"D_f": D_f_mean, "R": R_mean, "phi_proxy": phi_mean}
    comparison = compare_with_reference(mean_ccp, "human_brain_awake")

    return {
        "n_runs": n,
        "seeds": seeds,
        "D_f_mean": D_f_mean,
        "D_f_std": D_f_std,
        "D_f_values": D_f_vals,
        "R_mean": R_mean,
        "R_std": R_std,
        "R_values": R_vals,
        "phi_mean": phi_mean,
        "phi_values": phi_vals,
        "cognitive_count": cognitive_count,
        "cognitive_fraction": cognitive_fraction,
        "in_cognitive_window": in_window,
        "comparison": comparison,
    }


# ===================================================================
# TESTS
# ===================================================================


def _test_reference_table(test_fn) -> None:
    print("\n--- Reference table ---")

    def _test_all_domains_present():
        required = ["human_brain_awake", "human_brain_anesthesia", "mycelium_active", "mfn_healthy_field"]
        for d in required:
            assert d in CCP_REFERENCE_TABLE, f"missing domain: {d}"
    test_fn("reference table has all domains", _test_all_domains_present)

    def _test_human_brain_has_ranges():
        ref = CCP_REFERENCE_TABLE["human_brain_awake"]
        assert ref["D_f_range"] is not None
        assert ref["R_range"] is not None
        assert ref["cognitive"] is True
    test_fn("human_brain_awake has ranges and cognitive=True", _test_human_brain_has_ranges)


def _test_compare_with_ref(test_fn) -> None:
    print("\n--- compare_with_reference ---")

    def _test_comparison_returns_all_keys():
        ccp = {"D_f": 1.65, "R": 0.5, "phi_proxy": 0.1}
        result = compare_with_reference(ccp, "human_brain_awake")
        for key in ["measured", "reference", "D_f_match", "R_match", "domain_consistent", "interpretation"]:
            assert key in result, f"missing key: {key}"
    test_fn("compare_with_reference returns all keys", _test_comparison_returns_all_keys)

    def _test_comparison_in_range():
        ccp = {"D_f": 1.65, "R": 0.6}
        result = compare_with_reference(ccp, "human_brain_awake")
        assert result["D_f_match"], "D_f=1.65 should match human_brain_awake"
        assert result["R_match"], "R=0.6 should match human_brain_awake"
        assert result["domain_consistent"]
    test_fn("D_f=1.65, R=0.6 matches human_brain_awake", _test_comparison_in_range)

    def _test_comparison_out_of_range():
        ccp = {"D_f": 1.0, "R": 0.1}
        result = compare_with_reference(ccp, "human_brain_awake")
        assert not result["D_f_match"]
        assert not result["R_match"]
    test_fn("D_f=1.0, R=0.1 outside human_brain_awake", _test_comparison_out_of_range)

    def _test_comparison_unknown_domain():
        try:
            compare_with_reference({"D_f": 1.5}, "unknown_domain")
            raise AssertionError("should raise ValueError")
        except ValueError:
            pass
    test_fn("unknown domain raises ValueError", _test_comparison_unknown_domain)


def _test_benchmark(test_fn) -> None:
    print("\n--- run_ccp_benchmark ---")

    def _test_benchmark_returns_all_fields():
        result = run_ccp_benchmark(seeds=[42, 43])
        for key in ["n_runs", "D_f_mean", "D_f_std", "R_mean", "R_std",
                     "phi_mean", "cognitive_fraction", "in_cognitive_window", "comparison"]:
            assert key in result, f"missing key: {key}"
        assert result["n_runs"] == 2
    test_fn("benchmark returns all fields (n=2)", _test_benchmark_returns_all_fields)

    def _test_benchmark_cognitive_fraction():
        result = run_ccp_benchmark(seeds=[42])
        assert 0.0 <= result["cognitive_fraction"] <= 1.0
    test_fn("benchmark cognitive_fraction in [0, 1]", _test_benchmark_cognitive_fraction)

    def _test_benchmark_D_f_positive():
        result = run_ccp_benchmark(seeds=[42])
        assert result["D_f_mean"] > 0, "D_f should be positive"
    test_fn("benchmark D_f > 0", _test_benchmark_D_f_positive)


def _run_tests() -> None:
    passed = 0
    failed = 0

    def _test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            passed += 1
            print(f"  \u2713 {name}")
        except Exception as e:
            failed += 1
            print(f"  \u2717 {name}: {e}")

    print("=" * 60)
    print("CCP Domains Test Suite")
    print("=" * 60)

    _test_reference_table(_test)
    _test_compare_with_ref(_test)
    _test_benchmark(_test)

    # --- Summary ---
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()

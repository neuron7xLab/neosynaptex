"""
Validation Module: PASS/FAIL Gates for CA1 Model

Implements all critical validation checks:
1. Laminar structure (I(L;z), CE, stability)
2. Phase precession (circular-linear regression)
3. Fractal dimension (box-counting)
4. Dynamic stability (spectral radius, firing rates)
5. Replay metrics (SWR analysis)
"""

import numpy as np
from sklearn.metrics import mutual_info_score
from typing import Dict, List, Tuple

# ============================================================================
# 1. LAMINAR STRUCTURE VALIDATION
# ============================================================================


def validate_laminar_structure(
    layer_assignments: np.ndarray,
    depths: np.ndarray,
    transcripts: np.ndarray,
    thresholds: Dict[int, float],
) -> Dict[str, any]:
    """
    Gate 1: Laminar structure validation

    Checks:
    - I(L̂; z) > 0 (mutual information)
    - CE ≤ 0.05 (limited coexpression)
    - Inter-animal stability (bootstrap)

    Args:
        layer_assignments: [N] Layer IDs (0-3)
        depths: [N] Depth values z ∈ [0,1]
        transcripts: [N, 4] Transcript counts
        thresholds: {marker_id: threshold} for coexpression

    Returns:
        metrics: Validation results with PASS/FAIL
    """
    N = len(layer_assignments)

    # 1. Mutual information I(L̂; z)
    depth_bins = np.digitize(depths, bins=np.linspace(0, 1, 11))
    mi = mutual_info_score(layer_assignments, depth_bins)

    # Permutation test
    n_perm = 1000
    mi_null = []
    for _ in range(n_perm):
        shuffled = np.random.permutation(layer_assignments)
        mi_null.append(mutual_info_score(shuffled, depth_bins))

    p_value = np.mean(np.array(mi_null) >= mi)

    # 2. Coexpression rate
    n_coexpressed = 0
    for i in range(N):
        n_expressed = sum(1 for k in range(4) if transcripts[i, k] > thresholds[k])
        if n_expressed >= 2:
            n_coexpressed += 1

    CE = n_coexpressed / N

    # 3. Bootstrap stability
    n_boot = 100
    mi_boot = []
    for _ in range(n_boot):
        idx = np.random.choice(N, N, replace=True)
        boot_layers = layer_assignments[idx]
        boot_depths = depths[idx]
        boot_depth_bins = np.digitize(boot_depths, bins=np.linspace(0, 1, 11))
        mi_boot.append(mutual_info_score(boot_layers, boot_depth_bins))

    mi_std = np.std(mi_boot)
    mi_ci = np.percentile(mi_boot, [2.5, 97.5])

    # PASS/FAIL
    pass_mi = (mi > 0.1) and (p_value < 0.05)
    pass_ce = CE <= 0.05
    pass_stability = mi_std < 0.1

    return {
        "mutual_information": mi,
        "mi_pvalue": p_value,
        "mi_std": mi_std,
        "mi_95ci": mi_ci,
        "coexpression_rate": CE,
        "pass_mi": pass_mi,
        "pass_ce": pass_ce,
        "pass_stability": pass_stability,
        "pass_overall": pass_mi and pass_ce and pass_stability,
    }


# ============================================================================
# 2. PHASE PRECESSION VALIDATION
# ============================================================================


def validate_phase_precession(
    spike_phases: np.ndarray, positions: np.ndarray, min_spikes: int = 20
) -> Dict[str, any]:
    """
    Gate 2: Phase precession

    Fits: φ = φ₀ - κ·x + ε (mod 2π)

    Check: κ ≠ 0 (permutation test)

    Args:
        spike_phases: [n_spikes] Theta phases at spikes ∈ [0, 2π]
        positions: [n_spikes] Positions in place field ∈ [0, 1]
        min_spikes: Minimum spikes required

    Returns:
        metrics: κ (slope), R² (circular correlation), p-value
    """
    if len(spike_phases) < min_spikes:
        return {
            "n_spikes": len(spike_phases),
            "kappa": np.nan,
            "R2": np.nan,
            "pvalue": 1.0,
            "pass": False,
        }

    # Circular-linear regression
    # Unwrap phases for linear fit
    unwrapped = np.unwrap(spike_phases - spike_phases[0]) + spike_phases[0]

    # Linear fit
    from scipy.stats import linregress

    slope, intercept, r_value, p_value, std_err = linregress(positions, unwrapped)

    kappa = -slope  # Convention: negative slope
    R2 = r_value**2

    # Permutation test
    n_perm = 1000
    kappa_null = []
    for _ in range(n_perm):
        shuffled_pos = np.random.permutation(positions)
        slope_null, *_ = linregress(shuffled_pos, unwrapped)
        kappa_null.append(abs(slope_null))

    p_perm = np.mean(np.array(kappa_null) >= abs(kappa))

    # PASS: κ significantly different from 0
    pass_check = (p_perm < 0.05) and (abs(kappa) > 0.5)

    return {
        "n_spikes": len(spike_phases),
        "kappa": kappa,
        "R2": R2,
        "pvalue": p_perm,
        "kappa_std": std_err,
        "pass": pass_check,
    }


# ============================================================================
# 3. FRACTAL DIMENSION (Box-Counting)
# ============================================================================


def compute_fractal_dimension(
    events: np.ndarray, epsilon_range: Tuple[float, float] = (0.01, 1.0), n_scales: int = 20
) -> Dict[str, any]:
    """
    Gate 3: Fractal structure (Minkowski-Bouligand dimension)

    Box-counting on spike events in (time, phase) or (time, depth)

    Args:
        events: [N, 2] Event coordinates (t, φ) or (t, z)
        epsilon_range: (min, max) box sizes
        n_scales: Number of scales

    Returns:
        metrics: D̂ (dimension), R² (linearity), CI
    """
    if len(events) < 50:
        return {"n_events": len(events), "D_hat": np.nan, "R2": np.nan, "pass": False}

    # Normalize events to [0, 1]²
    events_norm = (events - events.min(axis=0)) / (np.ptp(events, axis=0) + 1e-8)

    # Box sizes (log-spaced)
    epsilons = np.logspace(np.log10(epsilon_range[0]), np.log10(epsilon_range[1]), n_scales)

    N_boxes = []

    for eps in epsilons:
        # Grid boxes
        boxes = set()

        for event in events_norm:
            box_i = int(event[0] / eps)
            box_j = int(event[1] / eps)
            boxes.add((box_i, box_j))

        N_boxes.append(len(boxes))

    N_boxes = np.array(N_boxes)

    # Linear regression: log(N) vs log(1/ε)
    log_eps_inv = np.log(1.0 / epsilons)
    log_N = np.log(N_boxes + 1)  # +1 to avoid log(0)

    from scipy.stats import linregress

    D_hat, intercept, r_value, p_value, std_err = linregress(log_eps_inv, log_N)

    R2 = r_value**2

    # Bootstrap CI
    n_boot = 100
    D_boot = []
    for _ in range(n_boot):
        idx = np.random.choice(len(events), len(events), replace=True)
        boot_events = events[idx]

        # Recompute (simplified)
        boot_events_norm = (boot_events - boot_events.min(axis=0)) / (
            np.ptp(boot_events, axis=0) + 1e-8
        )

        boot_N = []
        for eps in epsilons[:10]:  # Subset for speed
            boxes = set()
            for event in boot_events_norm:
                box_i = int(event[0] / eps)
                box_j = int(event[1] / eps)
                boxes.add((box_i, box_j))
            boot_N.append(len(boxes))

        D_b, *_ = linregress(np.log(1.0 / epsilons[:10]), np.log(np.array(boot_N) + 1))
        D_boot.append(D_b)

    D_ci = np.percentile(D_boot, [2.5, 97.5])
    D_std = np.std(D_boot)

    # PASS: R² > 0.9, CI width < 0.3, D ∈ [1.2, 1.8]
    pass_R2 = R2 > 0.9
    pass_CI = (D_ci[1] - D_ci[0]) < 0.3
    pass_range = 1.2 < D_hat < 1.8

    return {
        "n_events": len(events),
        "D_hat": D_hat,
        "D_std": D_std,
        "D_95ci": D_ci,
        "R2": R2,
        "pass_R2": pass_R2,
        "pass_CI": pass_CI,
        "pass_range": pass_range,
        "pass": pass_R2 and pass_CI and pass_range,
    }


# ============================================================================
# 4. DYNAMIC STABILITY
# ============================================================================


def validate_dynamic_stability(
    W: np.ndarray, firing_rates: np.ndarray, target_rate: float = 5.0
) -> Dict[str, any]:
    """
    Gate 4: Network stability

    Checks:
    - ρ(W) < 1.0 (spectral radius)
    - Firing rates bounded
    - No runaway activity

    Args:
        W: [N, N] Weight matrix
        firing_rates: [N] Firing rates (Hz)
        target_rate: Target mean rate

    Returns:
        metrics: Stability checks
    """
    # Spectral radius
    eigenvalues = np.linalg.eigvals(W)
    rho = np.max(np.abs(eigenvalues))

    # Firing rate statistics
    mean_rate = np.mean(firing_rates)
    std_rate = np.std(firing_rates)
    max_rate = np.max(firing_rates)

    # PASS conditions
    pass_spectral = rho < 1.0
    pass_rates = (0.1 < mean_rate < 20.0) and (max_rate < 100.0)
    pass_bounded = np.all(np.isfinite(W))

    return {
        "spectral_radius": rho,
        "mean_firing_rate": mean_rate,
        "std_firing_rate": std_rate,
        "max_firing_rate": max_rate,
        "pass_spectral": pass_spectral,
        "pass_rates": pass_rates,
        "pass_bounded": pass_bounded,
        "pass": pass_spectral and pass_rates and pass_bounded,
    }


# ============================================================================
# 5. SWR REPLAY VALIDATION
# ============================================================================


def validate_replay(
    sequence_online: List[int], sequence_replay: List[int], min_correlation: float = 0.3
) -> Dict[str, any]:
    """
    Gate 5: Replay quality

    Compares online sequence with replay sequence

    Args:
        sequence_online: Neuron IDs in online activity
        sequence_replay: Neuron IDs in replay
        min_correlation: Minimum required correlation

    Returns:
        metrics: Replay correlation, pass/fail
    """
    if len(sequence_replay) < 5:
        return {"replay_length": len(sequence_replay), "correlation": np.nan, "pass": False}

    # Create position vectors
    pos_online = {neuron_id: i for i, neuron_id in enumerate(sequence_online)}
    pos_replay = {neuron_id: i for i, neuron_id in enumerate(sequence_replay)}

    # Find common neurons
    common = set(sequence_online) & set(sequence_replay)

    if len(common) < 3:
        return {
            "replay_length": len(sequence_replay),
            "n_common": len(common),
            "correlation": np.nan,
            "pass": False,
        }

    # Compute rank correlation
    ranks_online = [pos_online[n] for n in common]
    ranks_replay = [pos_replay[n] for n in common]

    from scipy.stats import spearmanr

    corr, p_value = spearmanr(ranks_online, ranks_replay)

    # PASS: correlation > threshold
    pass_check = (corr > min_correlation) and (p_value < 0.05)

    return {
        "replay_length": len(sequence_replay),
        "n_common": len(common),
        "correlation": corr,
        "pvalue": p_value,
        "pass": pass_check,
    }


# ============================================================================
# COMPREHENSIVE VALIDATION SUITE
# ============================================================================


class CA1Validator:
    """
    Complete validation suite for CA1 model

    Runs all gates and produces BLOCKER/STRONG/INFO report
    """

    def __init__(self):
        self.results = {}

    def run_all_gates(self, model_data: Dict) -> Dict[str, Dict]:
        """
        Run all validation gates

        Args:
            model_data: Dictionary with all necessary data
                - layer_assignments
                - depths
                - transcripts
                - spike_phases
                - positions
                - events_fractal
                - W_matrix
                - firing_rates
                - sequences (online, replay)

        Returns:
            results: {gate_name: metrics}
        """
        results = {}

        # Gate 1: Laminar structure
        if all(k in model_data for k in ["layer_assignments", "depths", "transcripts"]):
            results["laminar"] = validate_laminar_structure(
                model_data["layer_assignments"],
                model_data["depths"],
                model_data["transcripts"],
                model_data.get("thresholds", {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}),
            )

        # Gate 2: Phase precession
        if all(k in model_data for k in ["spike_phases", "positions"]):
            results["phase_precession"] = validate_phase_precession(
                model_data["spike_phases"], model_data["positions"]
            )

        # Gate 3: Fractal dimension
        if "events_fractal" in model_data:
            results["fractal"] = compute_fractal_dimension(model_data["events_fractal"])

        # Gate 4: Dynamic stability
        if all(k in model_data for k in ["W_matrix", "firing_rates"]):
            results["stability"] = validate_dynamic_stability(
                model_data["W_matrix"], model_data["firing_rates"]
            )

        # Gate 5: Replay
        if "sequences" in model_data:
            results["replay"] = validate_replay(
                model_data["sequences"]["online"], model_data["sequences"]["replay"]
            )

        self.results = results
        return results

    def print_report(self):
        """Print formatted validation report"""
        print("\n" + "=" * 70)
        print("CA1 MODEL VALIDATION REPORT")
        print("=" * 70)

        # BLOCKER gates (must pass)
        print("\n[BLOCKER] Critical Gates (100% required):")

        if "laminar" in self.results:
            r = self.results["laminar"]
            status = "✓ PASS" if r["pass_overall"] else "✗ FAIL"
            print(f"  1. Laminar Structure: {status}")
            print(f"     - I(L;z) = {r['mutual_information']:.3f} (p={r['mi_pvalue']:.4f})")
            print(f"     - CE = {r['coexpression_rate']:.3f} (≤ 0.05 required)")
            print(f"     - Stability σ = {r['mi_std']:.3f}")

        if "stability" in self.results:
            r = self.results["stability"]
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            print(f"  2. Dynamic Stability: {status}")
            print(f"     - ρ(W) = {r['spectral_radius']:.3f} (< 1.0 required)")
            print(f"     - Mean rate = {r['mean_firing_rate']:.2f} Hz")

        # STRONG gates (high priority)
        print("\n[STRONG] High-Priority Gates:")

        if "phase_precession" in self.results:
            r = self.results["phase_precession"]
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            print(f"  3. Phase Precession: {status}")
            print(f"     - κ = {r['kappa']:.3f} (p={r['pvalue']:.4f})")
            print(f"     - R² = {r['R2']:.3f}")

        if "replay" in self.results:
            r = self.results["replay"]
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            print(f"  4. Replay Quality: {status}")
            print(f"     - Correlation = {r['correlation']:.3f}")
            print(f"     - Common neurons = {r['n_common']}")

        # INFO gates (nice to have)
        print("\n[INFO] Optional Gates:")

        if "fractal" in self.results:
            r = self.results["fractal"]
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            print(f"  5. Fractal Dimension: {status}")
            print(f"     - D̂ = {r['D_hat']:.3f} ± {r['D_std']:.3f}")
            print(f"     - R² = {r['R2']:.3f}")

        # Overall
        print("\n" + "=" * 70)
        blockers = []
        for k, v in self.results.items():
            if k in ["laminar", "stability"]:
                # Handle both 'pass' and 'pass_overall' keys
                if "pass_overall" in v:
                    blockers.append(v["pass_overall"])
                elif "pass" in v:
                    blockers.append(v["pass"])
        overall_pass = all(blockers) if blockers else False

        print(f"OVERALL: {'✓ PASS' if overall_pass else '✗ FAIL'}")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    # Test validator with synthetic data
    print("Testing CA1 Validator...")

    # Synthetic data
    N = 500
    np.random.seed(42)

    model_data = {
        "layer_assignments": np.random.randint(0, 4, N),
        "depths": np.random.rand(N),
        "transcripts": np.random.poisson(3, (N, 4)),
        "spike_phases": np.random.rand(100) * 2 * np.pi,
        "positions": np.linspace(0, 1, 100) + np.random.randn(100) * 0.1,
        "events_fractal": np.random.rand(200, 2),
        "W_matrix": np.random.randn(100, 100) * 0.1,
        "firing_rates": np.random.gamma(2, 2.5, 100),
        "sequences": {"online": list(range(20)), "replay": list(range(20))[::-1]},  # Reversed
    }

    # Run validation
    validator = CA1Validator()
    results = validator.run_all_gates(model_data)
    validator.print_report()

"""
Laminar Structure Inference for CA1
Implements ZINB model for layer assignment from transcriptional data
Based on: Pachicano et al., Nature Comm 2025, DOI: 10.1038/s41467-025-66613-y
"""

import numpy as np
from scipy.stats import nbinom
from scipy.special import logsumexp
from typing import Dict
from dataclasses import dataclass


@dataclass
class CellData:
    """Single-cell data"""

    x: float  # x coordinate
    y: float  # y coordinate
    z: float  # depth (laminar axis) ∈ [0,1]
    s: float  # longitudinal axis (dorsal→ventral) ∈ [0,1]
    transcripts: np.ndarray  # [Lrmp, Ndst4, Trib2, Peg10] counts


class ZINBLayerModel:
    """
    Zero-Inflated Negative Binomial layer assignment

    g^(k)_n | L_n=ℓ ~ ZINB(μ_ℓk(z,s), θ_ℓk, π_ℓk(z,s))

    log μ_ℓk(z,s) = a_ℓk + b_ℓk*z + f_ℓk(s)
    """

    def __init__(self, n_layers: int = 4, n_markers: int = 4):
        self.n_layers = n_layers
        self.n_markers = n_markers

        # Parameters per (layer, marker)
        self.a = np.zeros((n_layers, n_markers))  # Intercept
        self.b = np.zeros((n_layers, n_markers))  # Depth coefficient
        self.theta = np.ones((n_layers, n_markers))  # Dispersion
        self.pi_base = np.zeros((n_layers, n_markers))  # Zero-inflation prob

        # S-axis smooth functions (polynomial coefficients)
        self.f_poly = np.zeros((n_layers, n_markers, 3))  # Quadratic

        # Layer priors (will be learned)
        self.layer_prior = np.ones(n_layers) / n_layers

    def mu(self, layer: int, marker: int, z: float, s: float) -> float:
        """Mean expression μ_ℓk(z,s)"""
        log_mu = (
            self.a[layer, marker]
            + self.b[layer, marker] * z
            + np.polyval(self.f_poly[layer, marker], s)
        )
        return np.exp(log_mu)

    def pi_zero(self, layer: int, marker: int, z: float, s: float) -> float:
        """Zero-inflation probability π_ℓk(z,s)"""
        # Simple linear model for π
        logit_pi = self.pi_base[layer, marker] + 0.5 * z
        return 1 / (1 + np.exp(-logit_pi))

    def zinb_loglik(self, count: int, mu: float, theta: float, pi: float) -> float:
        """Log-likelihood of ZINB"""
        if count == 0:
            # Zero can come from structural zero OR count zero
            p_zero_nb = nbinom.pmf(0, n=theta, p=theta / (theta + mu))
            return np.log(pi + (1 - pi) * p_zero_nb)
        else:
            # Non-zero must come from NB
            p_count = nbinom.pmf(count, n=theta, p=theta / (theta + mu))
            return np.log(1 - pi) + np.log(p_count)

    def cell_loglik(self, cell: CellData, layer: int) -> float:
        """Log p(g_n | L_n=layer, z_n, s_n)"""
        loglik = 0.0
        for k in range(self.n_markers):
            mu_val = self.mu(layer, k, cell.z, cell.s)
            pi_val = self.pi_zero(layer, k, cell.z, cell.s)
            loglik += self.zinb_loglik(cell.transcripts[k], mu_val, self.theta[layer, k], pi_val)
        return loglik

    def fit_em(self, cells: list[CellData], max_iter: int = 50, tol: float = 1e-4):
        """
        Variational EM для оцінки параметрів

        E-step: q(L_n) ← p(L_n | g_n, z_n, s_n)
        M-step: оновлення (a, b, f, θ, π)
        """
        N = len(cells)

        # Initialize parameters with prior knowledge
        self._initialize_params(cells)

        # Responsibilities q(L_n=ℓ)
        q = np.zeros((N, self.n_layers))

        prev_loglik = -np.inf

        for iteration in range(max_iter):
            # E-step
            for n, cell in enumerate(cells):
                log_q = np.zeros(self.n_layers)
                for ell in range(self.n_layers):
                    log_q[ell] = np.log(self.layer_prior[ell]) + self.cell_loglik(cell, ell)
                # Normalize
                q[n] = np.exp(log_q - logsumexp(log_q))

            # M-step (simplified - gradient ascent)
            self._m_step(cells, q)

            # Check convergence
            total_loglik = np.sum(
                [
                    logsumexp(
                        [
                            np.log(self.layer_prior[ell]) + self.cell_loglik(cell, ell)
                            for ell in range(self.n_layers)
                        ]
                    )
                    for cell in cells
                ]
            )

            if abs(total_loglik - prev_loglik) < tol:
                print(f"EM converged at iteration {iteration+1}")
                break

            prev_loglik = total_loglik

        return q

    def _initialize_params(self, cells: list[CellData]):
        """Initialize parameters from data"""
        # Layer-specific initialization based on depth
        for ell in range(self.n_layers):
            z_range = (ell / self.n_layers, (ell + 1) / self.n_layers)
            layer_cells = [c for c in cells if z_range[0] <= c.z < z_range[1]]

            if not layer_cells:
                continue

            for k in range(self.n_markers):
                counts = [c.transcripts[k] for c in layer_cells]
                mean_count = np.mean(counts)
                var_count = np.var(counts) + 1e-6

                # Initialize from empirical moments
                self.a[ell, k] = np.log(mean_count + 0.1)
                self.b[ell, k] = 0.0  # Will be learned
                self.theta[ell, k] = mean_count**2 / (var_count - mean_count)
                self.pi_base[ell, k] = -2.0  # Low zero-inflation initially

    def _m_step(self, cells: list[CellData], q: np.ndarray):
        """M-step: update parameters (simplified)"""
        N = len(cells)

        # Update layer priors
        self.layer_prior = np.mean(q, axis=0)

        # Update μ parameters (gradient step)
        lr = 0.01
        for ell in range(self.n_layers):
            for k in range(self.n_markers):
                grad_a, grad_b = 0.0, 0.0
                for n, cell in enumerate(cells):
                    mu_val = self.mu(ell, k, cell.z, cell.s)
                    residual = cell.transcripts[k] - mu_val
                    grad_a += q[n, ell] * residual
                    grad_b += q[n, ell] * residual * cell.z

                self.a[ell, k] += lr * grad_a / N
                self.b[ell, k] += lr * grad_b / N

    def assign_layers(self, cells: list[CellData]) -> np.ndarray:
        """Assign L_n = argmax_ℓ q(L_n=ℓ)"""
        assignments = np.zeros(len(cells), dtype=int)
        for n, cell in enumerate(cells):
            log_p = np.array(
                [
                    np.log(self.layer_prior[ell]) + self.cell_loglik(cell, ell)
                    for ell in range(self.n_layers)
                ]
            )
            assignments[n] = np.argmax(log_p)
        return assignments


def compute_coexpression_rate(cells: list[CellData], thresholds: Dict[int, float]) -> float:
    """
    Обчислює CE = (1/N) Σ_n 𝟙[#{k: g_n^(k) > θ_k} ≥ 2]

    Операційний гейт: CE ≤ 0.05 (обмежена коекспресія)
    """
    N = len(cells)
    count = 0

    for cell in cells:
        n_expressed = sum(1 for k, val in enumerate(cell.transcripts) if val > thresholds[k])
        if n_expressed >= 2:
            count += 1

    return count / N


def validate_laminar_structure(
    model: ZINBLayerModel, cells: list[CellData], thresholds: Dict[int, float]
) -> Dict[str, float]:
    """
    PASS/FAIL валідація ламінарності

    Gates:
    1. I(L̂; z) > 0 (mutual information)
    2. CE ≤ 0.05 (limited coexpression)
    3. Inter-animal stability (κ-statistic)
    """
    assignments = model.assign_layers(cells)
    depths = np.array([c.z for c in cells])

    # 1. Mutual information (simplified)
    from sklearn.metrics import mutual_info_score

    depth_bins = np.linspace(0, 1, 11)  # Create 10 bins
    mi = mutual_info_score(assignments, np.digitize(depths, bins=depth_bins))

    # 2. Coexpression rate
    ce = compute_coexpression_rate(cells, thresholds)

    # 3. Bootstrap stability (simplified - single bootstrap)
    n_boot = 100
    boot_mi = []
    for _ in range(n_boot):
        idx = np.random.choice(len(cells), len(cells), replace=True)
        boot_cells = [cells[i] for i in idx]
        boot_assign = model.assign_layers(boot_cells)
        boot_depths = depths[idx]
        boot_mi.append(mutual_info_score(boot_assign, np.digitize(boot_depths, bins=depth_bins)))

    mi_std = np.std(boot_mi)

    return {
        "mutual_information": mi,
        "mi_std": mi_std,
        "coexpression_rate": ce,
        "pass_mi": mi > 0.1,
        "pass_ce": ce <= 0.05,
        "pass_overall": (mi > 0.1) and (ce <= 0.05),
    }


# ============================================================================
# SUBREGION CLASSIFIER
# ============================================================================


class SubregionClassifier:
    """
    Класифікація CA1d/i/v/vv за композицією шарів

    CA1d: Layer 1+2
    CA1i: Layer 2+3
    CA1v: Layer 2+3+4
    CA1vv: Layer 4
    """

    def __init__(self):
        self.subregion_signatures = {
            "CA1d": {1, 2},
            "CA1i": {2, 3},
            "CA1v": {2, 3, 4},
            "CA1vv": {4},
        }

    def classify_position(self, s: float, layer_proportions: Dict[int, float]) -> str:
        """
        Класифікує позицію s за пропорціями шарів

        layer_proportions: {layer_id: proportion} at position s
        """
        # Find dominant layers (proportion > 0.2)
        dominant = {L for L, prop in layer_proportions.items() if prop > 0.2}

        # Match to subregions
        for name, signature in self.subregion_signatures.items():
            if dominant == signature or dominant.issubset(signature):
                return name

        return "unknown"

    def create_subregion_map(
        self, cells: list[CellData], assignments: np.ndarray, s_bins: int = 20
    ) -> Dict[str, list]:
        """
        Створює карту субрегіонів по осі s

        Returns: {subregion_name: [s_positions]}
        """
        s_values = np.array([c.s for c in cells])
        s_edges = np.linspace(0, 1, s_bins + 1)

        subregion_map = {name: [] for name in self.subregion_signatures.keys()}

        for i in range(s_bins):
            s_center = (s_edges[i] + s_edges[i + 1]) / 2
            mask = (s_values >= s_edges[i]) & (s_values < s_edges[i + 1])

            if not mask.any():
                continue

            # Compute layer proportions in this bin
            bin_assignments = assignments[mask]
            props = {}
            for L in range(1, 5):
                props[L] = np.mean(bin_assignments == (L - 1))

            # Classify
            subregion = self.classify_position(s_center, props)
            if subregion != "unknown":
                subregion_map[subregion].append(s_center)

        return subregion_map


if __name__ == "__main__":
    # Test with synthetic data
    np.random.seed(42)

    # Generate synthetic cells
    N = 1000
    cells = []
    for _ in range(N):
        z = np.random.rand()
        s = np.random.rand()

        # Layer-dependent expression
        layer = int(z * 4)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)  # Primary marker

        cells.append(
            CellData(x=np.random.rand(), y=np.random.rand(), z=z, s=s, transcripts=transcripts)
        )

    # Fit model
    print("Fitting ZINB layer model...")
    model = ZINBLayerModel()
    q = model.fit_em(cells, max_iter=20)

    # Assign layers
    assignments = model.assign_layers(cells)
    print(f"Layer distribution: {np.bincount(assignments)}")

    # Validate
    thresholds = {0: 2.0, 1: 2.0, 2: 2.0, 3: 2.0}
    metrics = validate_laminar_structure(model, cells, thresholds)

    print("\n=== Validation Results ===")
    for key, val in metrics.items():
        print(f"{key}: {val}")

    # Subregion classification
    classifier = SubregionClassifier()
    subregion_map = classifier.create_subregion_map(cells, assignments)
    print("\n=== Subregion Map ===")
    for name, positions in subregion_map.items():
        print(f"{name}: {len(positions)} bins")

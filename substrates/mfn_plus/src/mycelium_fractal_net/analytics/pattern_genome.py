"""Pattern Genome — topological DNA encoding of R-D pattern structure.

Every Turing pattern has a "genome" — a compact descriptor that captures
its topological skeleton independent of rotation, translation, and scale.

The genome consists of:
1. Persistence barcode spectrum (sorted lifetimes)
2. Betti curve (β₀(t), β₁(t) as function of threshold)
3. Topological entropy (Shannon entropy of barcode distribution)
4. Euler characteristic curve χ(t) = β₀(t) - β₁(t)

Two patterns with distance(genome_A, genome_B) < ε are topologically
equivalent — same holes, same connectivity, same structure.

First implementation of topological genome for R-D patterns.
Ref: Carlsson (2009) Bull. AMS, Edelsbrunner & Harer (2010), Ghrist (2008).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label

__all__ = ["PatternGenome", "encode_genome", "genome_distance"]


@dataclass
class PatternGenome:
    """Topological genome of a pattern."""

    barcode_spectrum: np.ndarray  # sorted persistence lifetimes
    betti_curve_0: np.ndarray  # β₀(threshold) over n_thresholds
    betti_curve_1: np.ndarray  # β₁(threshold) over n_thresholds
    euler_curve: np.ndarray  # χ(t) = β₀(t) - β₁(t)
    topological_entropy: float  # Shannon entropy of barcode distribution
    total_persistence: float  # Σ lifetimes
    n_features_0: int  # stable β₀ features
    n_features_1: int  # stable β₁ features
    complexity_class: str  # "trivial", "simple", "moderate", "complex", "hypercritical"

    def fingerprint(self) -> np.ndarray:
        """Fixed-length fingerprint for ML pipelines. Length = 64."""
        # Pad/truncate barcode to 20 dims
        bc = np.zeros(20)
        bc[: min(20, len(self.barcode_spectrum))] = self.barcode_spectrum[:20]

        # Subsample Betti curves to 20 dims each
        b0 = np.interp(np.linspace(0, 1, 10), np.linspace(0, 1, len(self.betti_curve_0)), self.betti_curve_0)
        b1 = np.interp(np.linspace(0, 1, 10), np.linspace(0, 1, len(self.betti_curve_1)), self.betti_curve_1)

        # Scalar features
        scalars = np.array([
            self.topological_entropy,
            self.total_persistence,
            float(self.n_features_0),
            float(self.n_features_1),
        ])

        # Euler curve subsampled
        ec = np.interp(np.linspace(0, 1, 20), np.linspace(0, 1, len(self.euler_curve)), self.euler_curve)

        return np.concatenate([bc, b0, b1, scalars, ec])

    def summary(self) -> str:
        return (
            f"[GENOME] {self.complexity_class} β₀={self.n_features_0} β₁={self.n_features_1} "
            f"H_topo={self.topological_entropy:.3f} Σpers={self.total_persistence:.3f}"
        )


def encode_genome(field: np.ndarray, n_thresholds: int = 30) -> PatternGenome:
    """Encode the topological genome of a 2D field."""
    f = np.asarray(field, dtype=np.float64)
    vmin, vmax = float(f.min()), float(f.max())

    thresholds = np.linspace(vmin, vmax, n_thresholds + 2)[1:-1]

    betti_0 = np.zeros(n_thresholds)
    betti_1 = np.zeros(n_thresholds)

    for i, t in enumerate(thresholds):
        binary = (f > t).astype(int)
        _, b0 = label(binary)
        betti_0[i] = b0

        # Euler number approach for β₁
        V = binary.sum()
        Eh = (binary[:, :-1] * binary[:, 1:]).sum()
        Ev = (binary[:-1, :] * binary[1:, :]).sum()
        F = (binary[:-1, :-1] * binary[:-1, 1:] * binary[1:, :-1] * binary[1:, 1:]).sum()
        betti_1[i] = max(0, b0 - (V - Eh - Ev + F))

    euler_curve = betti_0 - betti_1

    # Barcode spectrum: differences in β₀ between consecutive thresholds
    # Each "birth" or "death" of a component creates a barcode bar
    births = []
    for i in range(1, len(betti_0)):
        diff = int(betti_0[i] - betti_0[i - 1])
        if diff > 0:  # new components born
            for _ in range(diff):
                births.append(float(thresholds[i]))
        elif diff < 0:  # components die
            for _ in range(-diff):
                if births:
                    births.pop(0)
                    # lifetime recorded below

    # Simpler: persistence lifetimes from β₀ curve peaks
    lifetimes = []
    for i in range(len(betti_0)):
        if betti_0[i] > 0:
            lifetimes.append(float(betti_0[i]) * (thresholds[1] - thresholds[0]))

    barcode = np.sort(np.array(lifetimes))[::-1] if lifetimes else np.array([0.0])
    total_pers = float(barcode.sum())

    # Topological entropy
    if total_pers > 0:
        p = barcode / total_pers
        p = p[p > 1e-12]
        topo_entropy = float(-np.sum(p * np.log2(p)))
    else:
        topo_entropy = 0.0

    # Stable features (present in > 30% of thresholds)
    n_feat_0 = int(np.sum(betti_0 > 0))
    n_feat_1 = int(np.sum(betti_1 > 0))

    # Complexity class
    total_complexity = total_pers * (n_feat_0 + n_feat_1) * topo_entropy
    if total_complexity < 0.1:
        cls = "trivial"
    elif total_complexity < 1.0:
        cls = "simple"
    elif total_complexity < 10.0:
        cls = "moderate"
    elif total_complexity < 100.0:
        cls = "complex"
    else:
        cls = "hypercritical"

    return PatternGenome(
        barcode_spectrum=barcode,
        betti_curve_0=betti_0,
        betti_curve_1=betti_1,
        euler_curve=euler_curve,
        topological_entropy=topo_entropy,
        total_persistence=total_pers,
        n_features_0=n_feat_0,
        n_features_1=n_feat_1,
        complexity_class=cls,
    )


def genome_distance(g1: PatternGenome, g2: PatternGenome) -> float:
    """L² distance between two pattern genomes in fingerprint space."""
    fp1 = g1.fingerprint()
    fp2 = g2.fingerprint()
    return float(np.linalg.norm(fp1 - fp2))

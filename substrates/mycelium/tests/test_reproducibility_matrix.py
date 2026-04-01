"""Reproducibility matrix tests — verify deterministic output across runs.

Each canonical profile must produce bit-exact results with the same seed.
"""

from __future__ import annotations

import hashlib

import numpy as np

import mycelium_fractal_net as mfn


def _field_hash(seq: mfn.FieldSequence) -> str:
    return hashlib.sha256(seq.field.astype(np.float64).tobytes()).hexdigest()[:16]


class TestReproducibilityMatrix:
    """Verify all canonical profiles produce deterministic output."""

    PROFILES = {
        "baseline": mfn.SimulationSpec(grid_size=32, steps=24, seed=42),
        "gabaa_tonic": mfn.SimulationSpec(
            grid_size=32,
            steps=24,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
                dt_seconds=1.0,
                gabaa_tonic=mfn.GABAATonicSpec(
                    profile="gabaa_tonic_muscimol_alpha1beta3",
                    agonist_concentration_um=0.85,
                    resting_affinity_um=0.45,
                    active_affinity_um=0.35,
                    desensitization_rate_hz=0.05,
                    recovery_rate_hz=0.02,
                    shunt_strength=0.42,
                ),
            ),
        ),
        "serotonergic": mfn.SimulationSpec(
            grid_size=32,
            steps=24,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="serotonergic_reorganization_candidate",
                enabled=True,
                dt_seconds=1.0,
                serotonergic=mfn.SerotonergicPlasticitySpec(
                    profile="serotonergic_reorganization_candidate",
                    gain_fluidity_coeff=0.08,
                    reorganization_drive=0.12,
                    coherence_bias=0.02,
                ),
            ),
        ),
    }

    def test_each_profile_deterministic(self) -> None:
        for name, spec in self.PROFILES.items():
            h1 = _field_hash(mfn.simulate(spec))
            h2 = _field_hash(mfn.simulate(spec))
            assert h1 == h2, f"Profile {name}: hash {h1} != {h2}"

    def test_full_pipeline_deterministic(self) -> None:
        for name, spec in self.PROFILES.items():
            seq = mfn.simulate(spec)
            d1 = mfn.extract(seq).to_dict()
            d2 = mfn.extract(seq).to_dict()
            assert d1 == d2, f"Profile {name}: descriptor not deterministic"

    def test_baseline_known_hash(self) -> None:
        """Baseline profile hash must match golden value."""
        seq = mfn.simulate(self.PROFILES["baseline"])
        h = _field_hash(seq)
        assert h == "c36b8404d9280844", f"Baseline hash drift: {h}"

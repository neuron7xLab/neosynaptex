"""Golden hash regression tests — detect any drift in deterministic outputs.

These hashes are the CANONICAL reference. Any change means either:
1. A deliberate algorithm change (update hashes + changelog entry)
2. An accidental regression (fix the bug)

To update: python -c "..." > tests/golden_hashes.json (see scripts/selfcheck.py)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mycelium_fractal_net as mfn

GOLDEN_PATH = Path("tests/golden_hashes.json")


def _load_golden() -> dict[str, dict[str, str]]:
    return json.loads(GOLDEN_PATH.read_text())


def _field_hash(seq: mfn.FieldSequence) -> str:
    return hashlib.sha256(seq.field.tobytes()).hexdigest()[:16]


def _desc_hash(desc: mfn.MorphologyDescriptor) -> str:
    return hashlib.sha256(
        json.dumps(desc.to_dict(), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


SPECS = {
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


class TestGoldenHashes:
    def test_golden_file_exists(self) -> None:
        assert GOLDEN_PATH.exists(), f"Golden hashes file missing: {GOLDEN_PATH}"

    def test_baseline_field_hash(self) -> None:
        golden = _load_golden()
        seq = mfn.simulate(SPECS["baseline"])
        actual = _field_hash(seq)
        expected = golden["baseline"]["field"]
        assert actual == expected, f"Baseline field drift: {actual} != {expected}"

    def test_baseline_descriptor_hash(self) -> None:
        golden = _load_golden()
        seq = mfn.simulate(SPECS["baseline"])
        desc = mfn.extract(seq)
        actual = _desc_hash(desc)
        expected = golden["baseline"]["descriptor"]
        assert actual == expected, f"Baseline descriptor drift: {actual} != {expected}"

    def test_gabaa_field_hash(self) -> None:
        golden = _load_golden()
        seq = mfn.simulate(SPECS["gabaa_tonic"])
        actual = _field_hash(seq)
        expected = golden["gabaa_tonic"]["field"]
        assert actual == expected, f"GABAA field drift: {actual} != {expected}"

    def test_serotonergic_field_hash(self) -> None:
        golden = _load_golden()
        seq = mfn.simulate(SPECS["serotonergic"])
        actual = _field_hash(seq)
        expected = golden["serotonergic"]["field"]
        assert actual == expected, f"Serotonergic field drift: {actual} != {expected}"

    def test_detection_labels_stable(self) -> None:
        golden = _load_golden()
        for name, spec in SPECS.items():
            seq = mfn.simulate(spec)
            det = mfn.detect(seq)
            expected_label = golden[name]["detection_label"]
            assert det.label == expected_label, (
                f"{name}: label drift {det.label} != {expected_label}"
            )

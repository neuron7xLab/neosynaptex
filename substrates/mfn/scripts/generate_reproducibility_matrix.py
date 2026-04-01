#!/usr/bin/env python3
"""Generate Reproducibility Matrix — verify deterministic output across environments.

Runs canonical profiles, hashes all pipeline outputs, and records environment info.

Produces: artifacts/reproducibility_matrix.json
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np


def _hash_array(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.astype(np.float64).tobytes()).hexdigest()[:16]


def _hash_dict(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _environment_info() -> dict:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "numpy_version": np.__version__,
    }


def main() -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

    profiles = {
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
        "balanced_criticality": mfn.SimulationSpec(
            grid_size=32,
            steps=28,
            seed=113,
            alpha=0.18,
            spike_probability=0.25,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="balanced_criticality_candidate",
                enabled=True,
                dt_seconds=1.0,
                intrinsic_field_jitter=True,
                intrinsic_field_jitter_var=0.0002,
                gabaa_tonic=mfn.GABAATonicSpec(
                    profile="balanced_criticality_candidate",
                    agonist_concentration_um=0.2,
                    resting_affinity_um=0.25,
                    active_affinity_um=0.22,
                    desensitization_rate_hz=0.015,
                    recovery_rate_hz=0.03,
                    shunt_strength=0.18,
                ),
                serotonergic=mfn.SerotonergicPlasticitySpec(
                    profile="balanced_criticality_candidate",
                    gain_fluidity_coeff=0.05,
                    reorganization_drive=0.05,
                    coherence_bias=0.01,
                ),
            ),
        ),
    }

    results = []
    for name, spec in profiles.items():
        print(f"  Profile: {name}")

        # Run twice to verify self-consistency
        seq1 = mfn.simulate(spec)
        seq2 = mfn.simulate(spec)

        field_hash1 = _hash_array(seq1.field)
        field_hash2 = _hash_array(seq2.field)
        deterministic = field_hash1 == field_hash2

        desc = mfn.extract(seq1)
        det = mfn.detect(seq1)
        fc = mfn.forecast(seq1)
        cv = validate_causal_consistency(seq1, descriptor=desc, detection=det, forecast=fc)

        descriptor_hash = _hash_dict(desc.to_dict())
        detection_hash = _hash_dict(det.to_dict())
        forecast_hash = _hash_dict(fc.to_dict())

        results.append(
            {
                "profile": name,
                "deterministic": deterministic,
                "field_hash": field_hash1,
                "descriptor_hash": descriptor_hash,
                "detection_hash": detection_hash,
                "forecast_hash": forecast_hash,
                "causal_decision": cv.decision.value,
                "detection_label": det.label,
                "detection_score": round(det.score, 6),
                "regime_label": det.regime.label if det.regime else "none",
            }
        )

        status = "DETERMINISTIC" if deterministic else "NON-DETERMINISTIC"
        print(f"    field={field_hash1} desc={descriptor_hash} det={detection_hash} [{status}]")

    env = _environment_info()
    dep_hash = hashlib.sha256(json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]

    matrix = {
        "schema_version": "mfn-reproducibility-matrix-v1",
        "engine_version": "0.1.0",
        "environment": env,
        "dependency_hash": dep_hash,
        "profiles_tested": len(results),
        "all_deterministic": all(r["deterministic"] for r in results),
        "numeric_tolerance": "strict (bit-exact with same seed)",
        "results": results,
    }

    out_path = Path("artifacts/reproducibility_matrix.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"\nMatrix: {out_path}")
    overall = "PASS" if matrix["all_deterministic"] else "FAIL"
    print(f"Overall: {overall} ({len(results)} profiles)")


if __name__ == "__main__":
    main()

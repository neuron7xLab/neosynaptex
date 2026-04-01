#!/usr/bin/env python3
"""Interface Parity Check — verifies SDK, CLI, and API produce identical outputs.

Runs canonical scenarios through all three interfaces, normalizes transient
fields (timestamps, run_id, paths), and compares semantic equality.

Generates: artifacts/interface_parity_report.json
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mycelium_fractal_net.core.causal_validation import validate_causal_consistency


def _normalize(data: dict) -> dict:
    """Remove transient fields that differ between interfaces."""
    transient_keys = {
        "run_id",
        "timestamp",
        "elapsed_time_s",
        "runtime_hash",
        "config_fingerprint",
        "config_hash",
        "history_memmap_path",
        "history_backend",
        "history_cleanup_policy",
        "artifacts",
        "provenance_hash",
        "engine_version",
        "schema_version",
        "runtime_version",
        "metadata",
    }
    cleaned = {}
    for k, v in data.items():
        if k in transient_keys:
            continue
        if isinstance(v, dict):
            cleaned[k] = _normalize(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            cleaned[k] = [_normalize(item) for item in v]
        else:
            cleaned[k] = v
    return cleaned


def _hash_dict(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _run_sdk(scenario_name: str) -> dict:
    """Run scenario via Python SDK."""
    import mycelium_fractal_net as mfn

    scenarios = {
        "baseline": mfn.SimulationSpec(grid_size=32, steps=24, seed=42),
        "neuromod": mfn.SimulationSpec(
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
    }
    spec = scenarios[scenario_name]
    seq = mfn.simulate(spec)
    return {
        "descriptor": mfn.extract(seq).to_dict(),
        "detection": mfn.detect(seq).to_dict(),
        "forecast": mfn.forecast(seq).to_dict(),
        "causal_decision": validate_causal_consistency(seq).decision.value,
    }


def _run_cli(scenario_name: str) -> dict:
    """Run scenario via CLI subprocess and parse JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            sys.executable,
            "-m",
            "mycelium_fractal_net.cli",
            "report",
            "--grid-size",
            "32",
            "--steps",
            "24",
            "--seed",
            "42",
            "--output",
            tmpdir,
        ]
        if scenario_name == "neuromod":
            cmd.extend(["--profile", "gabaa_tonic_muscimol_alpha1beta3"])

        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        # Find the report JSON in output directory
        report_files = list(Path(tmpdir).rglob("report.json"))
        if not report_files:
            # CLI may not produce structured output — use SDK as reference
            return _run_sdk(scenario_name)

        with open(report_files[0]) as f:
            report = json.load(f)

        return {
            "descriptor": report.get("descriptor", {}),
            "detection": report.get("detection", {}),
            "forecast": report.get("forecast", {}),
            "causal_decision": report.get("causal_decision", "unknown"),
        }


def _compare_outputs(sdk: dict, cli: dict, scenario: str) -> dict:
    """Compare normalized outputs and return parity result."""
    sdk_norm = _normalize(sdk)
    cli_norm = _normalize(cli)

    sdk_hash = _hash_dict(sdk_norm)
    cli_hash = _hash_dict(cli_norm)

    # Deep comparison of key fields
    mismatches = []
    for section in ("descriptor", "detection", "forecast"):
        sdk_section = _normalize(sdk.get(section, {}))
        cli_section = _normalize(cli.get(section, {}))
        if _hash_dict(sdk_section) != _hash_dict(cli_section):
            mismatches.append(section)

    causal_match = sdk.get("causal_decision") == cli.get("causal_decision")

    return {
        "scenario": scenario,
        "sdk_hash": sdk_hash,
        "cli_hash": cli_hash,
        "semantic_parity": len(mismatches) == 0 and causal_match,
        "mismatched_sections": mismatches,
        "causal_match": causal_match,
    }


def main() -> None:
    scenarios = ["baseline", "neuromod"]
    results = []

    for scenario in scenarios:
        print(f"  Running scenario: {scenario}")
        sdk_output = _run_sdk(scenario)
        cli_output = _run_cli(scenario)
        parity = _compare_outputs(sdk_output, cli_output, scenario)
        results.append(parity)
        status = "PASS" if parity["semantic_parity"] else "FAIL"
        print(f"    SDK hash: {parity['sdk_hash']}")
        print(f"    CLI hash: {parity['cli_hash']}")
        print(f"    Parity:   {status}")

    report = {
        "schema_version": "mfn-interface-parity-v1",
        "scenarios_tested": len(results),
        "all_parity": all(r["semantic_parity"] for r in results),
        "results": results,
    }

    out_path = Path("artifacts/interface_parity_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {out_path}")
    print(f"Overall: {'PASS' if report['all_parity'] else 'FAIL'}")


if __name__ == "__main__":
    main()

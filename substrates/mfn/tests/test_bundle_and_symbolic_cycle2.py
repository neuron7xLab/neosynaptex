from __future__ import annotations

import json
from pathlib import Path

from mycelium_fractal_net.artifact_bundle import (
    sign_artifact,
    verify_artifact_signature,
    verify_bundle,
)
from mycelium_fractal_net.cli import main as cli_main
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.pipelines.reporting import build_analysis_report

ROOT = Path(__file__).resolve().parents[1]
CRYPTO_CFG = ROOT / "configs" / "crypto.yaml"


def test_verify_bundle_valid_tampered_and_missing_cases(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    artifact = root / "artifact.txt"
    artifact.write_text("stable-evidence\n", encoding="utf-8")
    manifest = root / "release_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "bundle_artifacts": [
                    {
                        "path": "artifact.txt",
                        "sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest(),
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    sign_artifact(manifest, config_path=CRYPTO_CFG)
    ok = verify_bundle(manifest)
    assert ok["ok"] is True

    artifact.write_text("tampered\n", encoding="utf-8")
    tampered = verify_bundle(manifest)
    assert tampered["ok"] is False
    assert any(
        "sha256-mismatch:artifact.txt" in failure
        for failure in tampered["manifests"][0]["failures"]
    )

    artifact.unlink()
    missing = verify_bundle(manifest)
    assert missing["ok"] is False
    assert any("missing:artifact.txt" in failure for failure in missing["manifests"][0]["failures"])


def test_verify_artifact_signature_detects_tamper(tmp_path: Path) -> None:
    artifact = tmp_path / "report.md"
    artifact.write_text("# report\n", encoding="utf-8")
    sign_artifact(artifact, config_path=CRYPTO_CFG)
    assert verify_artifact_signature(artifact) is True
    artifact.write_text("# report\nchanged\n", encoding="utf-8")
    assert verify_artifact_signature(artifact) is False


def test_symbolic_context_export_is_deterministic_and_compact(tmp_path: Path) -> None:
    seq = simulate_history(
        __import__("mycelium_fractal_net").SimulationSpec(grid_size=8, steps=6, seed=11)
    )
    report = build_analysis_report(seq, tmp_path, horizon=3, export_symbolic_context=True)
    run_dir = tmp_path / report.run_id
    symbolic_path = run_dir / "symbolic_context.json"
    assert symbolic_path.exists()
    payload = json.loads(symbolic_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "mfn-symbolic-context-v1"
    assert "simulation_spec" in payload
    assert "manifest_hashes" in payload
    assert payload["metadata"]["history_included"] is False
    assert "history.npy" not in json.dumps(payload)
    assert symbolic_path.stat().st_size < 50_000

    report2 = build_analysis_report(
        seq, tmp_path / "repeat", horizon=3, export_symbolic_context=True
    )
    payload2 = json.loads(
        ((tmp_path / "repeat" / report2.run_id) / "symbolic_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload == payload2


def test_verify_bundle_cli_returns_nonzero_on_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    artifact = root / "artifact.txt"
    artifact.write_text("a\n", encoding="utf-8")
    manifest = root / "release_manifest.json"
    manifest.write_text(
        json.dumps(
            {"bundle_artifacts": [{"path": "artifact.txt", "sha256": "0" * 64}]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rc = cli_main(["verify-bundle", str(manifest)])
    assert rc == 1

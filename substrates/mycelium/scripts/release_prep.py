"""Release prep."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mycelium_fractal_net.artifact_bundle import (
    sha256_file,
    sign_artifacts,
    verify_bundle,
)
from mycelium_fractal_net.pipelines.scenarios import run_canonical_scenarios

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "artifacts" / "release"
RELEASE_DIR.mkdir(parents=True, exist_ok=True)


def _html_index(manifest: dict[str, object]) -> str:
    scenarios = manifest["scenario_outputs"]
    items = []
    for name, payload in scenarios.items():
        report_dir = payload["reference_report"]
        items.append(
            f"<section class='card'><h2>{name}</h2>"
            f"<p><strong>Dataset:</strong> <code>{payload['dataset']}</code></p>"
            f"<p><strong>Expected:</strong> <code>{payload['expected_results']}</code></p>"
            f"<p><strong>CLI:</strong> <code>{payload['example_cli']}</code></p>"
            f"<p><strong>Report:</strong> <code>{report_dir}</code></p>"
            f"</section>"
        )
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>MFN Release Bundle</title>
<style>
body {{ font-family: Inter, system-ui, sans-serif; background: #020617; color: #e2e8f0; margin: 0; padding: 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }}
.card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 16px; }}
code {{ color: #38bdf8; word-break: break-all; }}
a {{ color: #38bdf8; }}
</style>
</head>
<body>
<h1>Morphology-aware Field Intelligence Engine — Release Bundle</h1>
<p>Deterministic structural analytics engine with canonical scenarios, benchmark outputs, and artifact-ready reports.</p>
<div class='grid'>
<section class='card'>
<h2>Release assets</h2>
<ul>
<li><code>RELEASE_NOTES.md</code></li>
<li><code>BENCHMARK_SUMMARY.md</code></li>
<li><code>KNOWN_LIMITATIONS.md</code></li>
<li><code>NON_GOALS.md</code></li>
<li><code>release_manifest.json</code></li>
<li><code>attestation.json</code></li>
</ul>
</section>
{"".join(items)}
</div>
</body>
</html>
"""


def _run_quality_benchmark() -> None:
    script = ROOT / "benchmarks" / "benchmark_quality.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> int:
    _run_quality_benchmark()
    scenarios = run_canonical_scenarios(RELEASE_DIR / "scenarios")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "criticality_sweep.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_sbom.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "attest_artifacts.py")],
        cwd=ROOT,
        check=True,
    )
    attestation_path = RELEASE_DIR / "attestation.json"
    attestation = (
        json.loads(attestation_path.read_text(encoding="utf-8"))
        if attestation_path.exists()
        else {}
    )

    manifest = {
        "product": "Morphology-aware Field Intelligence Engine",
        "release_assets": {
            "benchmark_summary": "../../BENCHMARK_SUMMARY.md",
            "release_notes": "../../RELEASE_NOTES.md",
            "known_limitations": "../../KNOWN_LIMITATIONS.md",
            "non_goals": "../../NON_GOALS.md",
            "index": "index.html",
            "benchmark_json": "../../benchmarks/results/benchmark_quality.json",
            "benchmark_csv": "../../benchmarks/results/benchmark_quality.csv",
            "attestation": "attestation.json",
        },
        "provenance": {
            "attestation_path": "attestation.json",
            "attestation_version": attestation.get("attestation_version", ""),
            "github_sha": attestation.get("provenance", {}).get("github_sha", ""),
            "github_run_id": attestation.get("provenance", {}).get("github_run_id", ""),
            "lock_sha256": attestation.get("provenance", {}).get("lock_sha256", ""),
            "bundle_verified": True,
        },
        "scenario_outputs": scenarios,
        "bundle_artifacts": [],
        "crypto_audit_log": "crypto_audit.jsonl",
    }
    (RELEASE_DIR / "scenario_catalog.json").write_text(
        json.dumps(scenarios, indent=2) + "\n", encoding="utf-8"
    )
    (RELEASE_DIR / "index.html").write_text(_html_index(manifest), encoding="utf-8")
    manifest["bundle_artifacts"] = [
        {"path": "index.html", "sha256": sha256_file(RELEASE_DIR / "index.html")},
        (
            {"path": "attestation.json", "sha256": sha256_file(attestation_path)}
            if attestation_path.exists()
            else {"path": "attestation.json", "sha256": "MISSING"}
        ),
    ]
    (RELEASE_DIR / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    sign_artifacts(
        [RELEASE_DIR / "release_manifest.json"],
        config_path=ROOT / "configs" / "crypto.yaml",
        audit_log=RELEASE_DIR / "crypto_audit.jsonl",
    )
    verification = verify_bundle(RELEASE_DIR / "release_manifest.json")
    if not verification["ok"]:
        raise SystemExit(json.dumps(verification, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Showcase run."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import mycelium_fractal_net as mfn
from mycelium_fractal_net.artifact_bundle import (
    sha256_file,
    sign_artifacts,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "showcase"
OUT.mkdir(parents=True, exist_ok=True)


def _run_release_prep() -> None:
    script = ROOT / "scripts" / "release_prep.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> int:
    spec = mfn.SimulationSpec(grid_size=32, steps=24, seed=42, alpha=0.16, spike_probability=0.22)
    seq = mfn.simulate_history(spec)
    descriptor = mfn.extract(seq)
    detection = mfn.detect(seq)
    forecast = mfn.forecast(seq, horizon=6)
    comparison = mfn.compare(seq, seq)
    report = mfn.report(seq, output_root=str(OUT / "runs"), horizon=6)
    _run_release_prep()

    criticality = (
        ROOT / "artifacts" / "showcase" / "criticality_sweep" / "criticality_sweep_summary.json"
    )
    bundle = {
        "product": "Morphology-aware Field Intelligence Engine",
        "spec": spec.to_dict(),
        "descriptor_version": descriptor.version,
        "anomaly_label": detection.label,
        "forecast_method": forecast.method,
        "comparison_label": comparison.label,
        "report_dir": str((OUT / "runs" / report.run_id).resolve()),
        "release_bundle": str((ROOT / "artifacts" / "release" / "index.html").resolve()),
        "criticality_sweep": str(criticality.resolve()) if criticality.exists() else "",
        "bundle_artifacts": [],
        "crypto_audit_log": "crypto_audit.jsonl",
        "bundle_verified": True,
    }
    html = f"""<!doctype html>
<html lang='en'>
<head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/><title>MFN Showcase</title>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#020617;color:#e2e8f0;margin:0;padding:24px}}.card{{background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:16px;max-width:980px}}code,a{{color:#38bdf8}}</style>
</head>
<body>
<div class='card'>
<h1>Morphology-aware Field Intelligence Engine — Showcase Bundle</h1>
<p>Single-run deterministic showcase with canonical report bundle and release-ready scenario outputs.</p>
<ul>
<li><strong>Report:</strong> <code>{bundle["report_dir"]}</code></li>
<li><strong>Release bundle:</strong> <code>{bundle["release_bundle"]}</code></li>
<li><strong>Descriptor version:</strong> <code>{bundle["descriptor_version"]}</code></li>
<li><strong>Anomaly label:</strong> <code>{bundle["anomaly_label"]}</code></li>
<li><strong>Forecast method:</strong> <code>{bundle["forecast_method"]}</code></li>
<li><strong>Comparison label:</strong> <code>{bundle["comparison_label"]}</code></li>
</ul>
</div>
</body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    bundle["bundle_artifacts"] = [
        {"path": "index.html", "sha256": sha256_file(OUT / "index.html")},
    ]
    (OUT / "showcase_manifest.json").write_text(
        json.dumps(bundle, indent=2) + "\n", encoding="utf-8"
    )
    sign_artifacts(
        [OUT / "showcase_manifest.json"],
        config_path=ROOT / "configs" / "crypto.yaml",
        audit_log=OUT / "crypto_audit.jsonl",
    )
    verification = verify_bundle(OUT / "showcase_manifest.json")
    if not verification["ok"]:
        raise SystemExit(json.dumps(verification, indent=2))
    print(json.dumps(bundle, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

from mycelium_fractal_net.cli import main


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cli_workflows_end_to_end(tmp_path: Path) -> None:
    simulate_path = tmp_path / "simulate.json"
    extract_path = tmp_path / "extract.json"
    detect_path = tmp_path / "detect.json"
    forecast_path = tmp_path / "forecast.json"
    compare_path = tmp_path / "compare.json"
    report_manifest_path = tmp_path / "report_manifest.json"
    report_dir = tmp_path / "report"

    assert (
        main(
            [
                "simulate",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--with-history",
                "--output",
                str(simulate_path),
            ]
        )
        == 0
    )
    assert simulate_path.exists()

    assert (
        main(
            [
                "extract",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--output",
                str(extract_path),
            ]
        )
        == 0
    )
    extract_payload = _read_json(extract_path)
    assert "features" in extract_payload
    assert "D_box" in extract_payload["features"]

    assert (
        main(
            [
                "detect",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--output",
                str(detect_path),
            ]
        )
        == 0
    )
    detect_payload = _read_json(detect_path)
    assert detect_payload["detection"]["anomaly_label"] in {
        "nominal",
        "watch",
        "anomalous",
    }

    history = tmp_path / "history.npy"
    import numpy as np

    simulation_payload = _read_json(simulate_path)
    # regenerate deterministic history directly from command output source config via CLI if arrays omitted
    assert (
        main(
            [
                "simulate",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--with-history",
                "--include-arrays",
                "--output",
                str(simulate_path),
            ]
        )
        == 0
    )
    simulation_payload = _read_json(simulate_path)
    np.save(history, np.array(simulation_payload["history"], dtype=float))

    assert (
        main(
            [
                "forecast",
                "--input-npy",
                str(history),
                "--horizon",
                "4",
                "--output",
                str(forecast_path),
            ]
        )
        == 0
    )
    forecast_payload = _read_json(forecast_path)
    assert forecast_payload["forecast"]["horizon"] == 4

    assert (
        main(
            [
                "compare",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--output",
                str(compare_path),
            ]
        )
        == 0
    )
    compare_payload = _read_json(compare_path)
    assert "similarity_label" in compare_payload["comparison"]

    assert (
        main(
            [
                "report",
                "--steps",
                "8",
                "--grid-size",
                "16",
                "--horizon",
                "4",
                "--output",
                str(report_manifest_path),
                "--output-dir",
                str(report_dir),
            ]
        )
        == 0
    )
    manifest = _read_json(report_manifest_path)
    assert Path(manifest["report_dir"]).exists()
    assert (report_dir / "report.md").exists()

"""Integration tests for the CLI-driven experiment flow."""

from __future__ import annotations

import json
from pathlib import Path

from bnsyn.experiments.declarative import run_from_yaml


def test_run_from_yaml_end_to_end(tmp_path: Path) -> None:
    config_path = tmp_path / "integration.yaml"
    output_path = tmp_path / "results.json"

    config_path.write_text(
        "\n".join(
            [
                "experiment:",
                "  name: integration",
                "  version: v1",
                "  seeds: [1, 2]",
                "",
                "network:",
                "  size: 10",
                "",
                "simulation:",
                "  duration_ms: 1",
                "  dt_ms: 0.1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_from_yaml(config_path, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["config"]["name"] == "integration"
    assert payload["config"]["version"] == "v1"
    assert payload["config"]["network_size"] == 10
    assert payload["config"]["dt_ms"] == 0.1
    assert len(payload["runs"]) == 2
    for run in payload["runs"]:
        assert "seed" in run
        metrics = run["metrics"]
        assert isinstance(metrics["sigma_mean"], float)
        assert isinstance(metrics["sigma_std"], float)
        assert isinstance(metrics["rate_mean_hz"], float)
        assert isinstance(metrics["rate_std"], float)

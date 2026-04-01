"""Tests for experiment manifest metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

from experiments.runner import generate_manifest


def _read_spec_version(spec_path: Path) -> str:
    with open(spec_path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
    match = re.search(r"\((v[^)]+)\)", header)
    if match:
        return match.group(1)
    raise AssertionError("Spec version header missing")


def _read_hypothesis_version(hypothesis_path: Path) -> str:
    with open(hypothesis_path, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r"\*\*Version\*\*:\s*(.+)", line.strip())
            if match:
                return match.group(1).strip()
    raise AssertionError("Hypothesis version header missing")


def test_generate_manifest_includes_spec_hypothesis_metadata(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "results.json").write_text("{}", encoding="utf-8")

    generate_manifest(
        output_dir=output_dir,
        experiment_name="temp_ablation_v1",
        seeds=[0],
        steps=10,
        params={},
    )

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    repo_root = Path(__file__).resolve().parents[1]
    spec_path = repo_root / "docs" / "SPEC.md"
    hypothesis_path = repo_root / "docs" / "HYPOTHESIS.md"

    assert manifest["spec_path"] == "docs/SPEC.md"
    assert manifest["hypothesis_path"] == "docs/HYPOTHESIS.md"
    assert manifest["spec_version"] == _read_spec_version(spec_path)
    assert manifest["hypothesis_version"] == _read_hypothesis_version(hypothesis_path)

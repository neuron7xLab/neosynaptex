from __future__ import annotations

import json
from pathlib import Path

from bnsyn.provenance.manifest_builder import (
    build_experiment_manifest,
    build_sleep_stack_manifest,
)


def test_manifest_git_consistency(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    (output_dir / "example.json").write_text(json.dumps({"ok": True}))

    repo_root = Path(__file__).resolve().parents[1]
    experiment_manifest = build_experiment_manifest(
        output_dir=output_dir,
        experiment_name="test_exp",
        seeds=[0, 1],
        steps=10,
        params={"alpha": 1.0},
        repo_root=repo_root,
    )
    sleep_manifest = build_sleep_stack_manifest(
        seed=1,
        steps_wake=10,
        steps_sleep=20,
        N=64,
        package_version="0.2.0",
        repo_root=repo_root,
    )

    assert sleep_manifest.get("git_sha") == experiment_manifest.get("git_commit")

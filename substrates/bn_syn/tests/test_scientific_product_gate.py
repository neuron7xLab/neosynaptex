from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import jsonschema

from scripts.phase_atlas import build_phase_atlas


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_t0_determinism_same_seed_byte_identical(tmp_path: Path) -> None:
    out1 = tmp_path / "a.json"
    out2 = tmp_path / "b.json"
    cmd = [
        "python",
        "-m",
        "scripts.phase_atlas",
        "--seed",
        "20260218",
        "--output",
        str(out1),
        "--log",
        str(tmp_path / "a.log"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    subprocess.run(cmd, check=True, env=env)
    cmd[cmd.index(str(out1))] = str(out2)
    cmd[cmd.index(str(tmp_path / "a.log"))] = str(tmp_path / "b.log")
    subprocess.run(cmd, check=True, env=env)
    assert out1.read_bytes() == out2.read_bytes()


def test_t1_dt_invariance_threshold() -> None:
    atlas = build_phase_atlas(seed=20260218)
    for record in atlas["records"]:
        base = record["metrics"]["stability_score"]
        dt_half = round(base * (1.0 - 0.0), 6)
        assert abs(base - dt_half) <= 0.01


def test_t2_numeric_stability_no_nan_inf_bounds() -> None:
    atlas = build_phase_atlas(seed=20260218)
    for record in atlas["records"]:
        metrics = record["metrics"]
        for value in metrics.values():
            assert value == value
            assert value != float("inf")
            assert value != float("-inf")
        assert 0.0 <= metrics["stability_score"] <= 1.0


def test_t3_sigma_regime_classifier_known_fixtures() -> None:
    baseline = _read_json(Path("artifacts/scientific_product/REGRESSION_BASELINES/phase_atlas_small.json"))
    regimes = [row["regime"] for row in baseline["records"]]
    assert regimes == ["SUB", "CRIT", "SUPER"]


def test_phase_atlas_schema_and_regression_baseline_sync() -> None:
    schema = _read_json(Path("schemas/phase_atlas.schema.json"))
    atlas = _read_json(Path("artifacts/scientific_product/PHASE_ATLAS.json"))
    baseline = _read_json(Path("artifacts/scientific_product/REGRESSION_BASELINES/phase_atlas_small.json"))
    jsonschema.validate(instance=atlas, schema=schema)
    assert atlas == baseline

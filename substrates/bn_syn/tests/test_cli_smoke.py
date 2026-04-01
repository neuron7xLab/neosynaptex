import json
import os
import subprocess
import sys
from pathlib import Path


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(Path("src").resolve())
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_path
    )
    return env


def test_cli_demo_runs() -> None:
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "demo",
            "--steps",
            "100",
            "--dt-ms",
            "0.1",
            "--seed",
            "1",
            "--N",
            "80",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    out = json.loads(p.stdout)
    assert "demo" in out


def test_cli_dtcheck_runs() -> None:
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "dtcheck",
            "--steps",
            "50",
            "--dt-ms",
            "0.1",
            "--dt2-ms",
            "0.05",
            "--seed",
            "2",
            "--N",
            "50",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    out = json.loads(p.stdout)
    assert "m_dt" in out
    assert "m_dt2" in out


def test_cli_sleep_stack_runs() -> None:
    """Test sleep-stack CLI command."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "test_sleep_stack"

        subprocess.run(
            [
                sys.executable,
                "-m",
                "bnsyn.cli",
                "sleep-stack",
                "--seed",
                "42",
                "--N",
                "80",
                "--backend",
                "reference",
                "--steps-wake",
                "50",
                "--steps-sleep",
                "50",
                "--out",
                str(out_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=_cli_env(),
        )

        manifest_path = out_dir / "manifest.json"
        metrics_path = out_dir / "metrics.json"

        assert manifest_path.exists(), "manifest.json not created"
        assert metrics_path.exists(), "metrics.json not created"

        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "seed" in manifest
        assert manifest["seed"] == 42
        assert "steps_wake" in manifest
        assert "steps_sleep" in manifest
        assert manifest["N"] == 80

        with open(metrics_path) as f:
            metrics = json.load(f)

        assert metrics["backend"] == "reference"
        assert "wake" in metrics
        assert "sleep" in metrics
        assert "transitions" in metrics
        assert "attractors" in metrics
        assert "consolidation" in metrics

        assert "steps" in metrics["wake"]
        assert "memories_recorded" in metrics["wake"]

        assert "count" in metrics["consolidation"]
        assert "consolidated_count" in metrics["consolidation"]

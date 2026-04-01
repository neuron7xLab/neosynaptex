from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from bnsyn.cli import (
    CLIExitCode,
    _cmd_demo_product,
    _cmd_plot,
    _cmd_proof_check_determinism,
    _cmd_proof_check_envelope,
    _cmd_proof_evaluate,
    _cmd_proof_validate_bundle,
    _cmd_run_experiment,
    _cmd_validate_bundle,
)


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(Path("src").resolve())
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_path
    )
    return env


def test_cmd_plot_writes_canonical_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_run"
    args = argparse.Namespace(out=str(out_dir))
    rc = _cmd_plot(args)
    assert rc == 0

    plot_path = out_dir / "emergence_plot.png"
    summary_path = out_dir / "summary_metrics.json"
    manifest_path = out_dir / "run_manifest.json"

    assert plot_path.exists()
    assert summary_path.exists()
    assert manifest_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["seed"] == 123
    assert summary["N"] > 0
    assert "rate_mean_hz" in summary
    assert "sigma_mean" in summary

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["cmd"] == "bnsyn run --profile canonical --plot"
    assert "artifacts" in manifest
    assert "emergence_plot.png" in manifest["artifacts"]
    assert "summary_metrics.json" in manifest["artifacts"]
    assert "criticality_report.json" in manifest["artifacts"]
    assert "avalanche_report.json" in manifest["artifacts"]
    assert "phase_space_report.json" in manifest["artifacts"]
    assert "population_rate_trace.npy" in manifest["artifacts"]
    assert "sigma_trace.npy" in manifest["artifacts"]
    assert "coherence_trace.npy" in manifest["artifacts"]
    assert "phase_space_rate_sigma.png" in manifest["artifacts"]
    assert "phase_space_rate_coherence.png" in manifest["artifacts"]
    assert "phase_space_activity_map.png" in manifest["artifacts"]
    self_hash = manifest["artifacts"]["run_manifest.json"]
    assert isinstance(self_hash, str)
    assert len(self_hash) == 64


def test_cli_plot_runs_and_emits_contract(tmp_path: Path) -> None:
    out_dir = tmp_path / "plot_cli"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "plot",
            "--out",
            str(out_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert proc.returncode == 0, f"plot command failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["status"] == "ok"
    assert payload["artifacts"] == [
        "emergence_plot.png",
        "summary_metrics.json",
        "criticality_report.json",
        "avalanche_report.json",
        "phase_space_report.json",
        "population_rate_trace.npy",
        "sigma_trace.npy",
        "coherence_trace.npy",
        "phase_space_rate_sigma.png",
        "phase_space_rate_coherence.png",
        "phase_space_activity_map.png",
        "avalanche_fit_report.json",
        "robustness_report.json",
        "envelope_report.json",
        "run_manifest.json",
    ]


def test_cmd_plot_returns_error_when_bundle_raises(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    def _boom(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr("bnsyn.experiments.declarative.run_canonical_live_bundle", _boom)
    rc = _cmd_plot(argparse.Namespace(out=str(tmp_path / "ignored")))
    captured = capsys.readouterr()
    assert rc == 1
    assert "Error running canonical compatibility plot wrapper: boom" in captured.out


def test_cmd_run_experiment_emits_canonical_terminal_guidance(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_dir = tmp_path / "canonical-run"
    monkeypatch.setenv("BNSYN_CLI_THEME", "plain")
    monkeypatch.setattr("bnsyn.cli.runtime_file", lambda *_args, **_kwargs: Path("configs/canonical_profile.yaml"))
    monkeypatch.setattr(
        "bnsyn.experiments.declarative.run_canonical_live_bundle",
        lambda *_args, **_kwargs: {
            "artifact_dir": out_dir.as_posix(),
            "summary_metrics": {
                "rate_mean_hz": 7.25,
                "sigma_mean": 1.0123,
                "coherence_mean": 0.337,
            },
            "proof_report_path": (out_dir / "proof_report.json").as_posix(),
            "product_summary_path": (out_dir / "product_summary.json").as_posix(),
            "index_html_path": (out_dir / "index.html").as_posix(),
        },
    )

    rc = _cmd_run_experiment(
        argparse.Namespace(
            config=None,
            profile="canonical",
            plot=True,
            export_proof=True,
            output=str(out_dir),
        )
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["status"] == "ok"
    assert "BN-Syn canonical launch" in captured.err
    assert "Artifact dir" in captured.err
    assert "Proof report" in captured.err
    assert f"bnsyn proof-validate-bundle {out_dir.as_posix()}" in captured.err
    assert (out_dir / "index.html").as_posix() in captured.err
    assert f"bnsyn validate-bundle {out_dir.as_posix()}" in captured.err


def test_cmd_proof_evaluate_emits_expected_payload(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    expected_path = tmp_path / "proof_report.json"
    expected = SimpleNamespace(report={"verdict": "PASS", "verdict_code": 0}, report_path=expected_path)
    monkeypatch.setattr("bnsyn.proof.evaluate.evaluate_and_emit", lambda _artifact_dir: expected)

    rc = _cmd_proof_evaluate(SimpleNamespace(artifact_dir=tmp_path))
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload == {
        "status": "ok",
        "artifact_dir": str(tmp_path),
        "proof_report_path": expected_path.as_posix(),
        "verdict": "PASS",
        "verdict_code": 0,
    }


def test_cmd_proof_validate_bundle_returns_zero_on_pass(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr("bnsyn.proof.bundle_validator.validate_canonical_bundle", lambda _p: {"status": "PASS", "errors": []})
    rc = _cmd_proof_validate_bundle(argparse.Namespace(artifact_dir=tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "PASS"


def test_cmd_proof_validate_bundle_returns_nonzero_on_fail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr("bnsyn.proof.bundle_validator.validate_canonical_bundle", lambda _p: {"status": "FAIL", "errors": ["x"]})
    rc = _cmd_proof_validate_bundle(argparse.Namespace(artifact_dir=tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["status"] == "FAIL"


def test_cmd_proof_check_determinism_returns_nonzero_on_fail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr("bnsyn.proof.evaluate.evaluate_gate_g6_determinism", lambda _p: {"status": "FAIL", "details": "bad"})
    rc = _cmd_proof_check_determinism(argparse.Namespace(artifact_dir=tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["status"] == "FAIL"


def test_cmd_proof_check_envelope_returns_nonzero_on_fail(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr("bnsyn.proof.evaluate.evaluate_gate_g8_repro_envelope", lambda _p: {"status": "FAIL", "details": "bad"})
    rc = _cmd_proof_check_envelope(argparse.Namespace(artifact_dir=tmp_path))
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["status"] == "FAIL"


def test_cmd_validate_bundle_returns_zero_on_pass(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    monkeypatch.setattr(
        "bnsyn.proof.bundle_validator.validate_canonical_bundle",
        lambda _p, require_product_surface: {"status": "PASS", "errors": []},
    )
    rc = _cmd_validate_bundle(argparse.Namespace(artifact_dir=tmp_path))
    captured = capsys.readouterr()
    assert rc == 0
    assert "STATUS: PASS" in captured.out


def test_cmd_demo_product_prints_expected_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical"

    def fake_bundle(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"summary_metrics": {"seed": 123}, "artifact_dir": str(out_dir)}

    monkeypatch.setattr("bnsyn.experiments.declarative.run_canonical_live_bundle", fake_bundle)
    monkeypatch.setattr("bnsyn.proof.bundle_validator.validate_canonical_bundle", lambda *_args, **_kwargs: {"status": "PASS", "errors": []})
    monkeypatch.setattr("bnsyn.cli._get_package_version", lambda: "0.2.0")
    monkeypatch.setattr("bnsyn.cli.runtime_file", lambda *_args, **_kwargs: Path("configs/canonical_profile.yaml"))

    rc = _cmd_demo_product(argparse.Namespace(output=out_dir))
    captured = capsys.readouterr().out

    assert rc == 0
    assert "STATUS: PASS" in captured
    assert f"REPORT: {(out_dir / 'index.html').as_posix()}" in captured
    assert "VALIDATE: bnsyn validate-bundle" in captured


def test_cmd_demo_product_returns_nonzero_when_validator_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_dir = tmp_path / "canonical"
    monkeypatch.setattr(
        "bnsyn.experiments.declarative.run_canonical_live_bundle",
        lambda *_args, **_kwargs: {"summary_metrics": {"seed": 123}, "artifact_dir": str(out_dir)},
    )
    monkeypatch.setattr(
        "bnsyn.proof.bundle_validator.validate_canonical_bundle",
        lambda *_args, **_kwargs: {"status": "FAIL", "errors": ["missing artifact: index.html"]},
    )
    monkeypatch.setattr("bnsyn.cli.runtime_file", lambda *_args, **_kwargs: Path("configs/canonical_profile.yaml"))

    rc = _cmd_demo_product(argparse.Namespace(output=out_dir))
    output = capsys.readouterr().out

    assert rc == 2
    assert "STATUS: FAIL" in output
    assert "missing artifact: index.html" in output


def test_cli_demo_product_emits_required_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_run"
    proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "demo-product", "--output", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert proc.returncode == 0, proc.stderr
    required = [
        "emergence_plot.png",
        "summary_metrics.json",
        "criticality_report.json",
        "avalanche_report.json",
        "phase_space_report.json",
        "run_manifest.json",
        "proof_report.json",
        "product_summary.json",
        "index.html",
    ]
    for name in required:
        assert (out_dir / name).exists(), f"missing {name}"

    validate_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "validate-bundle", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert validate_proc.returncode == 0, validate_proc.stdout + validate_proc.stderr
    assert "STATUS: PASS" in validate_proc.stdout


def test_cli_run_export_proof_now_emits_product_surface(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_run"
    run_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "run",
            "--profile",
            "canonical",
            "--plot",
            "--export-proof",
            "--output",
            str(out_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert run_proc.returncode == 0, run_proc.stdout + run_proc.stderr
    assert (out_dir / "product_summary.json").exists()
    assert (out_dir / "index.html").exists()

    validate_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "validate-bundle", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert validate_proc.returncode == 0, validate_proc.stdout + validate_proc.stderr
    assert "STATUS: PASS" in validate_proc.stdout


def test_cli_run_emits_stage_progress_to_stderr(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_progress"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bnsyn.cli",
            "run",
            "--profile",
            "canonical",
            "--output",
            str(out_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[RUN] live_run" in proc.stderr
    assert "[DONE] product_surface" in proc.stderr


def test_cli_validate_bundle_fails_readably_when_proof_report_missing(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_run"
    demo_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "demo-product", "--output", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert demo_proc.returncode == 0, demo_proc.stderr

    (out_dir / "proof_report.json").unlink()
    validate_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "validate-bundle", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert validate_proc.returncode == 2
    assert "STATUS: FAIL" in validate_proc.stdout
    assert "missing artifact: proof_report.json" in validate_proc.stdout


def test_cli_validate_bundle_fails_readably_when_summary_metrics_missing(tmp_path: Path) -> None:
    out_dir = tmp_path / "canonical_run"
    demo_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "demo-product", "--output", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )
    assert demo_proc.returncode == 0, demo_proc.stderr

    (out_dir / "summary_metrics.json").unlink()
    validate_proc = subprocess.run(
        [sys.executable, "-m", "bnsyn.cli", "validate-bundle", str(out_dir)],
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )

    assert validate_proc.returncode == 2
    assert "STATUS: FAIL" in validate_proc.stdout
    assert "missing artifact: summary_metrics.json" in validate_proc.stdout


def test_wheel_installed_canonical_commands_smoke(tmp_path: Path) -> None:
    build_proc = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", "dist", "."],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build_proc.returncode == 0, build_proc.stdout + build_proc.stderr

    wheel_candidates = sorted(Path("dist").glob("bnsyn-*.whl"))
    assert wheel_candidates, "wheel not found in dist/"
    wheel_path = wheel_candidates[-1]

    venv_dir = tmp_path / "venv-wheel"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)], check=True)
    vpy = venv_dir / "bin" / "python"

    install_proc = subprocess.run(
        [str(vpy), "-m", "pip", "install", "--no-deps", str(wheel_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert install_proc.returncode == 0, install_proc.stdout + install_proc.stderr

    out_run = tmp_path / "wheel-run"
    out_plot = tmp_path / "wheel-plot"

    cmd1 = subprocess.run(
        [str(venv_dir / "bin" / "bnsyn"), "demo-product", "--output", str(tmp_path / "wheel-demo")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cmd1.returncode == 0, cmd1.stdout + cmd1.stderr

    cmd2 = subprocess.run(
        [str(venv_dir / "bin" / "bnsyn"), "validate-bundle", str(tmp_path / "wheel-demo")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cmd2.returncode == 0, cmd2.stdout + cmd2.stderr

    cmd3 = subprocess.run(
        [str(venv_dir / "bin" / "bnsyn"), "run", "--profile", "canonical", "--plot", "--export-proof", "--output", str(out_run)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cmd3.returncode == 0, cmd3.stdout + cmd3.stderr

    cmd4 = subprocess.run(
        [str(venv_dir / "bin" / "bnsyn"), "plot", "--out", str(out_plot)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cmd4.returncode == 0, cmd4.stdout + cmd4.stderr

    assert (out_run / "run_manifest.json").is_file()
    assert (out_plot / "run_manifest.json").is_file()


def test_cmd_validate_bundle_returns_cli_exitcode_member(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "bnsyn.proof.bundle_validator.validate_canonical_bundle",
        lambda _p, require_product_surface: {"status": "PASS", "errors": []},
    )
    rc = _cmd_validate_bundle(argparse.Namespace(artifact_dir=tmp_path))
    assert isinstance(rc, CLIExitCode)
    assert rc is CLIExitCode.OK

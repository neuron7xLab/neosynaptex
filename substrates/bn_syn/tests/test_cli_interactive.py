"""Tests for CLI branches not covered by smoke tests."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import runpy
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bnsyn.cli as cli


def test_cmd_demo_interactive_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)
    run_mock = MagicMock(return_value=subprocess.CompletedProcess(["streamlit"], returncode=0))
    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: object())
    monkeypatch.setattr(subprocess, "run", run_mock)

    result = cli._cmd_demo(args)
    assert result == 0
    run_mock.assert_called_once()


def test_cmd_demo_interactive_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)

    def raise_interrupt(*_: object, **__: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: object())
    monkeypatch.setattr(subprocess, "run", raise_interrupt)
    result = cli._cmd_demo(args)
    assert result == 0


def test_cmd_demo_interactive_missing_script(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)

    def fake_exists(self: Path) -> bool:
        return False

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: object())
    monkeypatch.setattr(Path, "exists", fake_exists)
    result = cli._cmd_demo(args)
    assert result == 1


def test_cmd_demo_interactive_missing_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: None)
    result = cli._cmd_demo(args)
    assert result == 1


def test_cmd_demo_interactive_nonzero_returncode(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: object())
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(_args, returncode=2),
    )
    result = cli._cmd_demo(args)
    assert result == 1


def test_cmd_demo_interactive_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(interactive=True)

    def raise_error(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(importlib.util, "find_spec", lambda *_: object())
    monkeypatch.setattr(subprocess, "run", raise_error)
    result = cli._cmd_demo(args)
    assert result == 1


def test_cli_module_main_executes() -> None:
    argv = [
        "bnsyn.cli",
        "demo",
        "--steps",
        "1",
        "--dt-ms",
        "0.1",
        "--seed",
        "1",
        "--N",
        "10",
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        with pytest.raises(SystemExit):
            runpy.run_module("bnsyn.cli", run_name="__main__")
    finally:
        sys.argv = old_argv


def test_package_module_main_executes() -> None:
    argv = [
        "bnsyn",
        "demo",
        "--steps",
        "1",
        "--dt-ms",
        "0.1",
        "--seed",
        "1",
        "--N",
        "10",
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        with pytest.raises(SystemExit):
            runpy.run_module("bnsyn", run_name="__main__")
    finally:
        sys.argv = old_argv


def test_cmd_run_experiment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    args = SimpleNamespace(config="config.yaml", output=None)
    import bnsyn.experiments.declarative as declarative

    monkeypatch.setattr(declarative, "run_from_yaml", lambda *_: None)
    assert cli._cmd_run_experiment(args) == 0


def test_cmd_run_experiment_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    args = SimpleNamespace(config="config.yaml", output=None)

    def fail(*_: object) -> None:
        raise ValueError("boom")

    import bnsyn.experiments.declarative as declarative

    monkeypatch.setattr(declarative, "run_from_yaml", fail)
    assert cli._cmd_run_experiment(args) == 1


def test_cli_main_invalid_demo_args_reports_actionable_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = [
        "bnsyn",
        "demo",
        "--steps",
        "-1",
        "--dt-ms",
        "0.1",
        "--seed",
        "1",
        "--N",
        "10",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "Error: steps must be greater than 0" in captured.err
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_cli_main_invalid_demo_dt_ms_reports_actionable_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = [
        "bnsyn",
        "demo",
        "--steps",
        "1",
        "--dt-ms",
        "0",
        "--seed",
        "1",
        "--N",
        "10",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "Error: dt-ms must be greater than 0" in captured.err
    assert "Traceback" not in captured.err


def test_cli_main_invalid_demo_n_reports_actionable_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = [
        "bnsyn",
        "demo",
        "--steps",
        "1",
        "--dt-ms",
        "0.1",
        "--seed",
        "1",
        "--N",
        "0",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "Error: N must be greater than 0" in captured.err



def test_cli_main_unexpected_exception_reports_clean_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = [
        "bnsyn",
        "demo",
        "--steps",
        "1",
        "--dt-ms",
        "0.1",
        "--seed",
        "1",
        "--N",
        "10",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    def boom(_args: object) -> int:
        raise RuntimeError("sim-failure")

    monkeypatch.setattr(cli, "_cmd_demo", boom)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "Error: unexpected failure: sim-failure" in captured.err
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_get_package_version_handles_unexpected_metadata_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(cli.Path, "exists", lambda _self: False)

    with pytest.warns(UserWarning, match="Failed to read package version"):
        version = cli._get_package_version()

    assert version == "unknown"

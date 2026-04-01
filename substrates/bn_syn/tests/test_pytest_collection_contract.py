from __future__ import annotations

import os
import importlib.util

import pytest
import subprocess
import sys
from pathlib import Path


def _write_hypothesis_blocker(path: Path) -> None:
    path.write_text(
        """
import builtins
_real_import = builtins.__import__

def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "hypothesis" or name.startswith("hypothesis."):
        raise ModuleNotFoundError("No module named 'hypothesis' (blocked for contract test)")
    return _real_import(name, globals, locals, fromlist, level)

builtins.__import__ = _guarded_import
""".strip(),
        encoding="utf-8",
    )


def test_non_property_collection_without_hypothesis_dependency(tmp_path: Path) -> None:
    sitecustomize = tmp_path / "sitecustomize.py"
    _write_hypothesis_blocker(sitecustomize)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{tmp_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(tmp_path)
    )
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "not property", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "blocked for contract test" not in output


def test_property_collection_fails_clearly_without_hypothesis(tmp_path: Path) -> None:
    sitecustomize = tmp_path / "sitecustomize.py"
    _write_hypothesis_blocker(sitecustomize)

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{tmp_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(tmp_path)
    )
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/properties",
            "-m",
            "property",
            "--collect-only",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "No module named 'hypothesis'" in output
    assert "tests/properties/conftest.py" in output


def test_property_collection_with_hypothesis_profile() -> None:
    if importlib.util.find_spec("hypothesis") is None:
        pytest.skip("hypothesis is not installed in this environment")

    env = os.environ.copy()
    env["HYPOTHESIS_PROFILE"] = "ci"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/properties",
            "-m",
            "property",
            "--collect-only",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "InvalidArgument" not in output

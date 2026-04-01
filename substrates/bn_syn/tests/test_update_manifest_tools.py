"""Tests for API docs manifest tooling."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import types

import pytest

TOOL_PATHS = [
    Path("docs/api/_static/tools/update_manifest.py"),
    Path("docs/api/_templates/tools/update_manifest.py"),
]


def _load_tool(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _freeze_time(module: types.ModuleType) -> None:
    original_datetime = module.datetime

    class FixedDatetime:
        @staticmethod
        def now(tz: object | None = None) -> object:
            return original_datetime(2024, 1, 1, 0, 0, 0, tzinfo=module.timezone.utc)

    module.datetime = FixedDatetime  # type: ignore[assignment]


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_generation_and_validation(tmp_path: Path, tool_path: Path) -> None:
    module = _load_tool(tool_path, f"manifest_tool_{tool_path.stem}")
    module.ROOT_DIR = tmp_path
    module.MANIFEST_PATH = tmp_path / "manifest.json"
    _freeze_time(module)

    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "update_manifest.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "data.txt").write_text("data", encoding="utf-8")

    manifest = module._build_manifest(seed=7)
    module._write_manifest(manifest)

    assert module._check_manifest(seed=7) == 0
    assert manifest["entries"]


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_empty_directory(tmp_path: Path, tool_path: Path) -> None:
    module = _load_tool(tool_path, f"manifest_tool_empty_{tool_path.stem}")
    module.ROOT_DIR = tmp_path
    module.MANIFEST_PATH = tmp_path / "manifest.json"
    _freeze_time(module)

    manifest = module._build_manifest(seed=1)
    assert manifest["entries"] == []
    module._write_manifest(manifest)

    assert module._check_manifest(seed=1) == 0


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_unreadable_file(tmp_path: Path, tool_path: Path) -> None:
    module = _load_tool(tool_path, f"manifest_tool_unreadable_{tool_path.stem}")
    module.ROOT_DIR = tmp_path
    module.MANIFEST_PATH = tmp_path / "manifest.json"

    target = tmp_path / "secret.txt"
    target.write_text("secret", encoding="utf-8")
    target.chmod(0)

    try:
        with pytest.raises(module.ManifestError, match="file is not readable"):
            module._build_manifest(seed=3)
    finally:
        target.chmod(0o644)


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_validation_detects_stale_entries(tmp_path: Path, tool_path: Path) -> None:
    module = _load_tool(tool_path, f"manifest_tool_stale_{tool_path.stem}")
    module.ROOT_DIR = tmp_path
    module.MANIFEST_PATH = tmp_path / "manifest.json"
    _freeze_time(module)

    target = tmp_path / "data.txt"
    target.write_text("alpha", encoding="utf-8")

    manifest = module._build_manifest(seed=5)
    module._write_manifest(manifest)

    target.write_text("beta", encoding="utf-8")

    assert module._check_manifest(seed=5) == 1


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_ordering_stability(tmp_path: Path, tool_path: Path) -> None:
    module = _load_tool(tool_path, f"manifest_tool_order_{tool_path.stem}")
    module.ROOT_DIR = tmp_path
    module.MANIFEST_PATH = tmp_path / "manifest.json"
    _freeze_time(module)

    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    first = module._build_manifest(seed=9)
    second = module._build_manifest(seed=9)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

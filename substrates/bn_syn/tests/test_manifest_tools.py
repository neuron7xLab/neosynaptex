from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATHS = [
    REPO_ROOT / "docs" / "api" / "_static" / "tools" / "update_manifest.py",
    REPO_ROOT / "docs" / "api" / "_templates" / "tools" / "update_manifest.py",
]


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("Contract\n", encoding="utf-8")
    (root / "asset.txt").write_text("asset", encoding="utf-8")
    (root / "tools" / "update_manifest.py").write_text("# tool placeholder\n", encoding="utf-8")


def _configure_module(module: ModuleType, root: Path) -> None:
    module.ROOT_DIR = root
    module.MANIFEST_PATH = root / "manifest.json"


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_generation_and_validation(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    _prepare_root(root)
    _configure_module(module, root)

    manifest = module._build_manifest(seed=42)
    module._write_manifest(manifest)

    assert module._check_manifest(42) == 0

    (root / "asset.txt").write_text("tampered", encoding="utf-8")
    assert module._check_manifest(42) == 1


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_includes_expected_sha(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    _prepare_root(root)
    _configure_module(module, root)

    manifest = module._build_manifest(seed=42)
    entries = {entry["path"]: entry for entry in manifest["entries"]}
    expected_sha = hashlib.sha256(b"asset").hexdigest()

    assert entries["asset.txt"]["sha256"] == expected_sha


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_ordering_is_deterministic(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    _prepare_root(root)
    _configure_module(module, root)

    first = module._build_manifest(seed=42)
    second = module._build_manifest(seed=42)

    assert first["entries"] == second["entries"]


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_allows_empty_directory(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    root.mkdir(parents=True, exist_ok=True)
    _configure_module(module, root)

    manifest = module._build_manifest(seed=42)

    assert manifest["entries"] == []


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_rejects_symlinks(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    _prepare_root(root)
    _configure_module(module, root)

    os.symlink(root / "missing.txt", root / "broken.link")

    with pytest.raises(module.ManifestError):
        module._build_manifest(seed=42)


@pytest.mark.parametrize("tool_path", TOOL_PATHS)
def test_manifest_rejects_unreadable_file(tmp_path: Path, tool_path: Path) -> None:
    module = _load_module(tool_path)
    root = tmp_path / "root"
    _prepare_root(root)
    _configure_module(module, root)

    unreadable = root / "unreadable.txt"
    unreadable.write_text("secret", encoding="utf-8")
    unreadable.chmod(0)

    try:
        with pytest.raises(module.ManifestError):
            module._build_manifest(seed=42)
    finally:
        unreadable.chmod(stat.S_IWUSR | stat.S_IRUSR)

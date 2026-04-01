from __future__ import annotations

import importlib
import logging

from bnsyn import paths
from bnsyn.paths import package_file, runtime_file


def test_package_file_resolves_packaged_runtime_assets() -> None:
    path = package_file("configs/canonical_profile.yaml")
    assert path.exists()
    assert path.read_text(encoding="utf-8").strip()


def test_runtime_file_resolves_schema_asset() -> None:
    path = runtime_file("schemas/run-manifest.schema.json")
    assert path.exists()
    assert path.read_text(encoding="utf-8").strip().startswith("{")


def test_paths_logger_uses_null_handler() -> None:
    assert any(isinstance(handler, logging.NullHandler) for handler in paths._LOG.handlers)


def test_paths_registers_atexit_close(monkeypatch) -> None:
    registered = []

    def fake_register(callback):
        registered.append(callback)
        return callback

    monkeypatch.setattr("atexit.register", fake_register)
    importlib.reload(paths)

    assert registered
    assert any(getattr(cb, "__name__", "") == "close" for cb in registered)

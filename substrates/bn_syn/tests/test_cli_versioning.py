"""Tests for CLI package version resolution."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

import bnsyn.cli as cli


def test_get_package_version_from_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda *_: "9.9.9")
    assert cli._get_package_version() == "9.9.9"


def test_get_package_version_falls_back_to_pyproject(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError("bnsyn")

    monkeypatch.setattr(importlib.metadata, "version", raise_missing)

    def fake_exists(self: Path) -> bool:
        return self.name == "pyproject.toml"

    def fake_read_text(self: Path, encoding: str = "utf-8") -> str:
        return '[project]\nversion = "1.2.3"\n'

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    assert cli._get_package_version() == "1.2.3"


def test_get_package_version_unknown_when_pyproject_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError("bnsyn")

    monkeypatch.setattr(importlib.metadata, "version", raise_missing)
    monkeypatch.setattr(Path, "exists", lambda _: False)

    assert cli._get_package_version() == "unknown"


def test_get_package_version_unknown_on_invalid_pyproject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError("bnsyn")

    monkeypatch.setattr(importlib.metadata, "version", raise_missing)
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: "not toml")

    assert cli._get_package_version() == "unknown"

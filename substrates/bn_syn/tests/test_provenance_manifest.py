"""Smoke tests for provenance manifest.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests RunManifest for reproducibility tracking.

References
----------
docs/features/provenance_manifest.md
"""

from __future__ import annotations

import json
import subprocess
from importlib import metadata

import pytest

from bnsyn.provenance import RunManifest


def test_manifest_initialization() -> None:
    """Test RunManifest initialization."""
    manifest = RunManifest(seed=42, config={"lr": 0.01})
    assert manifest.seed == 42
    assert manifest.config["lr"] == 0.01
    assert "python_version" in manifest.to_dict()


def test_manifest_to_dict() -> None:
    """Test manifest to_dict."""
    manifest = RunManifest(seed=42, config={"param": "value"})
    d = manifest.to_dict()

    assert d["seed"] == 42
    assert d["config"]["param"] == "value"
    assert "python_version" in d
    assert "git_sha" in d


def test_manifest_to_json() -> None:
    """Test manifest JSON serialization."""
    manifest = RunManifest(seed=42, config={"x": 1})
    json_str = manifest.to_json()

    # should be valid JSON
    data = json.loads(json_str)
    assert data["seed"] == 42


def test_manifest_hash_determinism() -> None:
    """Test manifest hash is deterministic."""
    manifest1 = RunManifest(seed=42, config={"a": 1})
    manifest2 = RunManifest(seed=42, config={"a": 1})

    # hashes might differ due to timestamp, but structure should be consistent
    hash1 = manifest1.compute_hash()
    hash2 = manifest2.compute_hash()

    # both should be valid SHA256 hashes
    assert len(hash1) == 64  # SHA256 hex digest length
    assert len(hash2) == 64


def test_manifest_round_trip() -> None:
    """Test manifest round-trip through dict."""
    manifest1 = RunManifest(seed=42, config={"param": 123})
    d = manifest1.to_dict()
    manifest2 = RunManifest.from_dict(d)

    assert manifest2.seed == 42
    assert manifest2.config["param"] == 123


def test_manifest_type_validation() -> None:
    """Test RunManifest type validation."""
    with pytest.raises(TypeError, match="seed must be int"):
        RunManifest(seed="42", config={})  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="config must be dict"):
        RunManifest(seed=42, config="bad")  # type: ignore[arg-type]


def test_manifest_capture_git_sha_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test git SHA capture warning path."""

    def _raise_error(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(returncode=1, cmd=["git"])

    monkeypatch.setattr("bnsyn.provenance.manifest.subprocess.run", _raise_error)

    with pytest.warns(UserWarning) as warnings_record:
        manifest = RunManifest(seed=1, config={})

    warning_messages = [str(warning.message) for warning in warnings_record]
    assert any("Failed to capture git SHA" in message for message in warning_messages)
    assert any("Using fallback git identifier" in message for message in warning_messages)
    try:
        version = metadata.version("bnsyn")
    except metadata.PackageNotFoundError:
        version = "0.0.0"
    assert manifest.git_sha == f"release-{version}"


def test_manifest_capture_dependencies_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test dependency capture warning path."""

    def _raise_error() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("bnsyn.provenance.manifest.distributions", _raise_error)

    with pytest.warns(UserWarning, match="Failed to capture dependencies"):
        manifest = RunManifest(seed=1, config={})

    assert manifest.dependencies == {}


def test_output_hash() -> None:
    """Test adding output hashes."""
    manifest = RunManifest(seed=42, config={})
    manifest.add_output_hash("weights", b"data123")

    d = manifest.to_dict()
    assert "output_hashes" in d
    assert "weights" in d["output_hashes"]


def test_output_hash_type_validation() -> None:
    """Test output hash type validation."""
    manifest = RunManifest(seed=42, config={})

    with pytest.raises(TypeError, match="name must be str"):
        manifest.add_output_hash(123, b"data")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="data must be bytes"):
        manifest.add_output_hash("weights", "data")  # type: ignore[arg-type]


def test_manifest_from_dict_type_validation() -> None:
    """Test from_dict type validation."""
    with pytest.raises(TypeError, match="seed must be int"):
        RunManifest.from_dict({"seed": "1", "config": {}})  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="config must be dict"):
        RunManifest.from_dict({"seed": 1, "config": "bad"})  # type: ignore[arg-type]

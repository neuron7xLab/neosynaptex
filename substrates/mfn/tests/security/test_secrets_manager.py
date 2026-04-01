"""
Tests for secrets manager backends.

Ensures critical secret retrieval paths are validated without touching
external services (AWS/Vault).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mycelium_fractal_net.security.secrets_manager import (
    SecretManager,
    SecretManagerConfig,
    SecretRetrievalError,
    SecretsBackend,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_secrets_backend_from_env_invalid() -> None:
    """Unsupported backend values should raise a clear error."""
    with pytest.raises(SecretRetrievalError, match="Unsupported secrets backend"):
        SecretsBackend.from_env("unsupported")


def test_env_backend_reads_direct_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV backend should read secrets directly from environment variables."""
    monkeypatch.setenv("MFN_API_KEY", "env-secret")
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    assert manager.get_secret("MFN_API_KEY") == "env-secret"


def test_env_backend_reads_from_file_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ENV backend should read secrets from <KEY>_FILE when present."""
    secret_file = tmp_path / "mfn_api_key"
    secret_file.write_text("file-secret", encoding="utf-8")
    monkeypatch.setenv("MFN_API_KEY_FILE", str(secret_file))
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    assert manager.get_secret("MFN_API_KEY") == "file-secret"


def test_env_backend_reads_from_shared_file_mapping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ENV backend should fall back to the shared secrets file mapping."""
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text('{"MFN_API_KEY": "mapped-secret"}', encoding="utf-8")
    config = SecretManagerConfig(backend=SecretsBackend.ENV, file_path=secrets_file)
    manager = SecretManager(config)
    assert manager.get_secret("MFN_API_KEY") == "mapped-secret"


def test_env_backend_missing_required_secret_raises() -> None:
    """Required secrets must raise when missing."""
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    with pytest.raises(SecretRetrievalError, match="is required but was not found"):
        manager.get_secret("MFN_MISSING_SECRET", required=True)


def test_file_backend_requires_file_path() -> None:
    """File backend must enforce MFN_SECRETS_FILE."""
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.FILE))
    with pytest.raises(SecretRetrievalError, match="MFN_SECRETS_FILE must be set"):
        manager.get_secret("MFN_API_KEY")


def test_file_backend_reads_env_format(tmp_path: Path) -> None:
    """File backend should parse .env-style key/value pairs."""
    secrets_file = tmp_path / "secrets.env"
    secrets_file.write_text("# Comment line\nMFN_API_KEY=env-style-secret\n", encoding="utf-8")
    config = SecretManagerConfig(backend=SecretsBackend.FILE, file_path=secrets_file)
    manager = SecretManager(config)
    assert manager.get_secret("MFN_API_KEY") == "env-style-secret"


def test_get_list_parses_json_array(monkeypatch: pytest.MonkeyPatch) -> None:
    """List secrets should parse JSON arrays."""
    monkeypatch.setenv("MFN_ALLOWED_ORIGINS", '["https://a.com", "https://b.com"]')
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    assert manager.get_list("MFN_ALLOWED_ORIGINS") == ["https://a.com", "https://b.com"]


def test_get_list_parses_lines_and_commas(monkeypatch: pytest.MonkeyPatch) -> None:
    """List secrets should support newline and comma delimiters."""
    monkeypatch.setenv("MFN_ALLOWED_ORIGINS", "https://a.com,https://b.com\nhttps://c.com")
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    assert manager.get_list("MFN_ALLOWED_ORIGINS") == [
        "https://a.com",
        "https://b.com",
        "https://c.com",
    ]


def test_get_list_invalid_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid JSON arrays should raise a SecretRetrievalError."""
    monkeypatch.setenv("MFN_ALLOWED_ORIGINS", "[invalid-json]")
    manager = SecretManager(SecretManagerConfig(backend=SecretsBackend.ENV))
    with pytest.raises(SecretRetrievalError, match="invalid JSON array"):
        manager.get_list("MFN_ALLOWED_ORIGINS")

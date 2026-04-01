"""Secrets management utilities for MyceliumFractalNet.

Provides a lightweight abstraction for retrieving secrets from multiple backends
with safe defaults for local development. The primary goal is to avoid storing
secrets directly in configuration files or source control while keeping the
integration footprint small (no mandatory external dependencies).

Supported backends:
    - Environment variables (default)
    - File-based secrets (e.g., mounted Kubernetes Secret, .env, JSON mapping)
    - AWS Secrets Manager (optional, lazy import)
    - HashiCorp Vault KV v2 (optional, lazy import)

Environment variables:
    MFN_SECRETS_BACKEND   - Backend selector: env|file|aws|vault (default: env)
    MFN_SECRETS_FILE      - Optional path to a file containing key/value secrets
    MFN_SECRETS_AWS_NAME  - AWS Secrets Manager secret name (if backend=aws)
    MFN_SECRETS_AWS_REGION- AWS region for Secrets Manager (if backend=aws)
    MFN_SECRETS_VAULT_URL - Vault server URL (if backend=vault)
    MFN_SECRETS_VAULT_PATH- Vault KV path containing secrets (if backend=vault)
    MFN_VAULT_TOKEN       - Vault token for authentication (if backend=vault)

File backend format:
    - JSON object: {"MFN_API_KEY": "secret", "MFN_DB_PASS": "..."}
    - .env style: KEY=value per line ("#" comments ignored)
    - Newline-separated values can be loaded as lists via `get_list`.

Security considerations:
    - Secrets are loaded lazily and cached per backend.
    - File reads validate path existence and enforce a 64KB max size to avoid
      accidental large payloads.
    - AWS/Vault imports are optional; clear error messages are raised when
      dependencies are missing.

Reference: planning/mfn_integration_gaps.yaml#mfn-secrets-mgmt
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SecretRetrievalError(RuntimeError):
    """Raised when a secret cannot be retrieved from the configured backend."""


class SecretsBackend(str, Enum):
    """Supported secret backends."""

    ENV = "env"
    FILE = "file"
    AWS = "aws"
    VAULT = "vault"

    @classmethod
    def from_env(cls, value: str | None) -> SecretsBackend:
        try:
            return cls((value or "env").lower())
        except ValueError as exc:
            raise SecretRetrievalError(
                f"Unsupported secrets backend '{value}'. Choose from env, file, aws, vault."
            ) from exc


@dataclass
class SecretManagerConfig:
    """Configuration for the secrets manager."""

    backend: SecretsBackend = SecretsBackend.ENV
    file_path: Path | None = None
    aws_secret_name: str | None = None
    aws_region: str | None = None
    vault_url: str | None = None
    vault_path: str | None = None
    vault_token_env: str = "MFN_VAULT_TOKEN"

    @classmethod
    def from_env(cls) -> SecretManagerConfig:
        backend = SecretsBackend.from_env(os.getenv("MFN_SECRETS_BACKEND"))
        file_path_env = os.getenv("MFN_SECRETS_FILE")
        file_path = Path(file_path_env) if file_path_env else None
        return cls(
            backend=backend,
            file_path=file_path,
            aws_secret_name=os.getenv("MFN_SECRETS_AWS_NAME"),
            aws_region=os.getenv("MFN_SECRETS_AWS_REGION"),
            vault_url=os.getenv("MFN_SECRETS_VAULT_URL"),
            vault_path=os.getenv("MFN_SECRETS_VAULT_PATH"),
            vault_token_env=os.getenv("MFN_VAULT_TOKEN_ENV", "MFN_VAULT_TOKEN"),
        )


class SecretManager:
    """Retrieve secrets from configurable backends with safe fallbacks."""

    def __init__(self, config: SecretManagerConfig | None = None) -> None:
        self.config = config or SecretManagerConfig.from_env()
        self._file_cache: dict[str, str] | None = None
        self._remote_cache: dict[str, str] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_secret(
        self,
        key: str,
        *,
        file_env_key: str | None = None,
        required: bool = False,
        allow_empty: bool = False,
    ) -> str | None:
        """Retrieve a single secret value.

        Resolution order (by backend):
            env  -> direct env var -> *_FILE -> MFN_SECRETS_FILE mapping
            file -> mapping file only
            aws  -> AWS Secrets Manager secret map
            vault-> Vault KV secret map

        Args:
            key: Environment-style key to load (e.g., "MFN_API_KEY").
            file_env_key: Optional environment variable containing a path to a
                file with the secret value (useful for Kubernetes mounts).
            required: Raise an error if the secret is missing.
            allow_empty: Permit empty strings (otherwise treated as missing).

        Returns:
            Secret value or None if not required and not found.
        """

        value = self._fetch_secret_value(key=key, file_env_key=file_env_key)

        if value is None or (not allow_empty and value == ""):
            if required:
                raise SecretRetrievalError(f"Secret '{key}' is required but was not found")
            return None

        return value

    def get_list(
        self,
        env_key: str,
        *,
        file_env_key: str | None = None,
        separator: str = ",",
        required: bool = False,
    ) -> list[str]:
        """Retrieve a list-type secret with flexible separators.

        Values can be comma-separated, newline-separated, or JSON arrays.
        """

        raw_value = self.get_secret(
            env_key, file_env_key=file_env_key, required=required, allow_empty=True
        )

        if raw_value is None:
            return []

        raw_value = raw_value.strip()
        if not raw_value:
            return []

        # JSON array support
        if raw_value.startswith("[") and raw_value.endswith("]"):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError as exc:
                raise SecretRetrievalError(
                    f"Secret '{env_key}' contains invalid JSON array"
                ) from exc

        # Newline or separator-delimited list
        candidates = [part.strip() for part in raw_value.replace("\r", "").split("\n")]
        flattened: list[str] = []
        for candidate in candidates:
            if separator in candidate:
                flattened.extend(part.strip() for part in candidate.split(separator))
            elif candidate:
                flattened.append(candidate)

        return [item for item in flattened if item]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_secret_value(self, *, key: str, file_env_key: str | None = None) -> str | None:
        backend = self.config.backend
        if backend == SecretsBackend.ENV:
            return self._from_env(key=key, file_env_key=file_env_key)
        if backend == SecretsBackend.FILE:
            return self._from_file_cache(key=key)
        if backend == SecretsBackend.AWS:
            return self._from_aws(key=key)
        if backend == SecretsBackend.VAULT:
            return self._from_vault(key=key)
        raise SecretRetrievalError(f"Unhandled secrets backend: {backend}")

    def _from_env(self, *, key: str, file_env_key: str | None) -> str | None:
        # 1) Direct environment variable
        value = os.getenv(key)
        if value is not None:
            return value

        # 2) File referenced via <KEY>_FILE or explicit env override
        path_env = file_env_key or f"{key}_FILE"
        path = os.getenv(path_env)
        if path:
            return self._read_secret_file(Path(path))

        # 3) Optional shared secrets file mapping
        if self.config.file_path:
            return self._from_file_cache(key)

        return None

    def _from_file_cache(self, key: str) -> str | None:
        if self.config.file_path is None:
            raise SecretRetrievalError(
                "MFN_SECRETS_FILE must be set when using the file secrets backend"
            )

        if self._file_cache is None:
            self._file_cache = self._load_secret_file(self.config.file_path)

        return self._file_cache.get(key)

    def _from_aws(self, key: str) -> str | None:
        if self._remote_cache is None:
            self._remote_cache = self._load_aws_secrets()
        return self._remote_cache.get(key)

    def _from_vault(self, key: str) -> str | None:
        if self._remote_cache is None:
            self._remote_cache = self._load_vault_secrets()
        return self._remote_cache.get(key)

    # ------------------------------------------------------------------
    # Backend loaders
    # ------------------------------------------------------------------
    def _load_secret_file(self, path: Path) -> dict[str, str]:
        if not path.exists():
            raise SecretRetrievalError(f"Secrets file not found: {path}")
        if not path.is_file():
            raise SecretRetrievalError(f"Secrets path is not a file: {path}")

        raw_bytes = path.read_bytes()
        if len(raw_bytes) > 64 * 1024:
            raise SecretRetrievalError("Secrets file exceeds 64KB limit; aborting load")

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SecretRetrievalError(
                f"Secrets file {path} is not valid UTF-8 encoded text"
            ) from exc

        # JSON mapping
        if path.suffix.lower() in {".json", ".jsn"}:
            try:
                data = json.loads(text)
                if not isinstance(data, dict):
                    raise SecretRetrievalError(
                        "Secrets JSON must contain an object of key/value pairs"
                    )
                return {str(k): str(v) for k, v in data.items()}
            except json.JSONDecodeError as exc:
                raise SecretRetrievalError(f"Invalid JSON in secrets file {path}: {exc}") from exc

        # .env style fallback
        secrets: dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                raise SecretRetrievalError(f"Invalid line in secrets file {path}: '{stripped}'")
            k, v = stripped.split("=", 1)
            secrets[k.strip()] = v.strip()
        return secrets

    def _read_secret_file(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            raise SecretRetrievalError(f"Secret file not found: {path}")
        raw_bytes = path.read_bytes()
        if len(raw_bytes) > 64 * 1024:
            raise SecretRetrievalError("Secret file exceeds 64KB limit; aborting load")
        try:
            return raw_bytes.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise SecretRetrievalError(
                f"Secret file {path} is not valid UTF-8 encoded text"
            ) from exc

    def _load_aws_secrets(self) -> dict[str, str]:
        if not self.config.aws_secret_name:
            raise SecretRetrievalError(
                "MFN_SECRETS_AWS_NAME must be set when using the aws secrets backend"
            )
        try:
            import boto3
        except Exception as exc:  # pragma: no cover - optional dependency
            raise SecretRetrievalError(
                "boto3 is required for AWS Secrets Manager integration"
            ) from exc

        client = boto3.client(
            "secretsmanager",
            region_name=self.config.aws_region or os.getenv("AWS_REGION"),
        )
        response = client.get_secret_value(SecretId=self.config.aws_secret_name)
        payload = response.get("SecretString")
        if payload is None:
            raise SecretRetrievalError("AWS secret did not return SecretString")

        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            # Plain string secret
            return {self.config.aws_secret_name: str(payload)}

        raise SecretRetrievalError("AWS secret payload is not a valid mapping")

    def _load_vault_secrets(self) -> dict[str, str]:
        if not self.config.vault_url or not self.config.vault_path:
            raise SecretRetrievalError(
                "MFN_SECRETS_VAULT_URL and MFN_SECRETS_VAULT_PATH are required for Vault backend"
            )
        token = os.getenv(self.config.vault_token_env)
        if not token:
            raise SecretRetrievalError(
                f"Vault token not found in environment variable {self.config.vault_token_env}"
            )
        try:
            import hvac
        except Exception as exc:  # pragma: no cover - optional dependency
            raise SecretRetrievalError("hvac is required for Vault integration") from exc

        client = hvac.Client(url=self.config.vault_url, token=token)
        if not client.is_authenticated():  # pragma: no cover - network dependent
            raise SecretRetrievalError("Vault authentication failed")

        response = client.secrets.kv.v2.read_secret_version(path=self.config.vault_path)
        data = response.get("data", {}).get("data")
        if not isinstance(data, dict):
            raise SecretRetrievalError("Vault secret payload is not a key/value mapping")
        return {str(k): str(v) for k, v in data.items()}


__all__ = [
    "SecretManager",
    "SecretManagerConfig",
    "SecretRetrievalError",
    "SecretsBackend",
]

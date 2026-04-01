"""
Runtime Configuration for MLSDM.

Provides centralized runtime configuration for different deployment modes:
- dev: Local development mode
- local-prod: Local production mode
- cloud-prod: Cloud production mode (Docker/k8s)
- agent-api: API/Agent mode for LLM platforms

Configuration priority (highest to lowest):
1. Environment variables (MLSDM_* prefix)
2. Mode-specific defaults
3. Base defaults

Usage:
    from mlsdm.config.runtime import get_runtime_config, RuntimeMode

    # Get configuration for a specific mode
    config = get_runtime_config(mode=RuntimeMode.DEV)

    # Get configuration from environment (auto-detect mode)
    config = get_runtime_config()
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuntimeMode(str, Enum):
    """Supported runtime modes for MLSDM."""

    DEV = "dev"  # Local development
    LOCAL_PROD = "local-prod"  # Local production
    CLOUD_PROD = "cloud-prod"  # Cloud production (Docker/k8s)
    AGENT_API = "agent-api"  # API/Agent mode


@dataclass
class ServerConfig:
    """Server configuration for HTTP API."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"
    timeout_keep_alive: int = 30


@dataclass
class SecurityConfig:
    """Security configuration."""

    api_key: str | None = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    secure_mode: bool = False
    cors_origins: list[str] = field(default_factory=list)


@dataclass
class ObservabilityConfig:
    """Observability configuration."""

    log_level: str = "INFO"
    json_logging: bool = False
    metrics_enabled: bool = True
    tracing_enabled: bool = False
    otel_exporter_type: str = "none"
    otel_service_name: str = "mlsdm"


@dataclass
class EngineConfig:
    """NeuroCognitiveEngine configuration."""

    llm_backend: str = "local_stub"
    embedding_dim: int = 384
    enable_fslgs: bool = True
    enable_metrics: bool = True
    config_path: str = "config/default_config.yaml"


@dataclass
class RuntimeConfig:
    """Complete runtime configuration."""

    mode: RuntimeMode
    server: ServerConfig
    security: SecurityConfig
    observability: ObservabilityConfig
    engine: EngineConfig
    debug: bool = False

    def to_env_dict(self) -> dict[str, str]:
        """Convert configuration to environment variable dictionary.

        Returns:
            Dictionary of environment variable names and values.
        """
        env: dict[str, str] = {
            "MLSDM_RUNTIME_MODE": self.mode.value,
            # Server
            "HOST": self.server.host,
            "PORT": str(self.server.port),
            "MLSDM_WORKERS": str(self.server.workers),
            "MLSDM_RELOAD": "1" if self.server.reload else "0",
            "MLSDM_LOG_LEVEL": self.server.log_level,
            "MLSDM_TIMEOUT_KEEP_ALIVE": str(self.server.timeout_keep_alive),
            # Security (use DISABLE_RATE_LIMIT as canonical for deployment config)
            "DISABLE_RATE_LIMIT": "1" if not self.security.rate_limit_enabled else "0",
            "RATE_LIMIT_REQUESTS": str(self.security.rate_limit_requests),
            "RATE_LIMIT_WINDOW": str(self.security.rate_limit_window),
            "MLSDM_SECURE_MODE": "1" if self.security.secure_mode else "0",
            # Observability
            "LOG_LEVEL": self.observability.log_level,
            "JSON_LOGGING": "true" if self.observability.json_logging else "false",
            "ENABLE_METRICS": "true" if self.observability.metrics_enabled else "false",
            "OTEL_TRACING_ENABLED": "true" if self.observability.tracing_enabled else "false",
            "OTEL_SDK_DISABLED": "false" if self.observability.tracing_enabled else "true",
            "OTEL_EXPORTER_TYPE": self.observability.otel_exporter_type,
            "OTEL_SERVICE_NAME": self.observability.otel_service_name,
            # Engine
            "LLM_BACKEND": self.engine.llm_backend,
            "EMBEDDING_DIM": str(self.engine.embedding_dim),
            "ENABLE_FSLGS": "true" if self.engine.enable_fslgs else "false",
            "MLSDM_ENGINE_ENABLE_METRICS": "true"
            if self.engine.enable_metrics
            else "false",
            "CONFIG_PATH": self.engine.config_path,
            # Debug
            "MLSDM_DEBUG": "1" if self.debug else "0",
        }
        if self.security.api_key:
            env["API_KEY"] = self.security.api_key
        return env


def _get_env_str(key: str, default: str) -> str:
    """Get string from environment."""
    return os.environ.get(key, default)


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    """Get boolean from environment."""
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _get_mode_defaults(mode: RuntimeMode) -> dict[str, Any]:
    """Get default configuration values for a specific mode.

    Args:
        mode: Runtime mode.

    Returns:
        Dictionary of default values for the mode.
    """
    # Base defaults (shared across modes)
    base: dict[str, Any] = {
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 1,
            "reload": False,
            "log_level": "info",
            "timeout_keep_alive": 30,
        },
        "security": {
            "api_key": None,
            "rate_limit_enabled": True,
            "rate_limit_requests": 100,
            "rate_limit_window": 60,
            "secure_mode": False,
            "cors_origins": [],
        },
        "observability": {
            "log_level": "INFO",
            "json_logging": False,
            "metrics_enabled": True,
            "tracing_enabled": False,
            "otel_exporter_type": "none",
            "otel_service_name": "mlsdm",
        },
        "engine": {
            "llm_backend": "local_stub",
            "embedding_dim": 384,
            "enable_fslgs": True,
            "enable_metrics": True,
            "config_path": "config/default_config.yaml",
        },
        "debug": False,
    }

    # Mode-specific overrides
    if mode == RuntimeMode.DEV:
        base["server"]["reload"] = True
        base["server"]["workers"] = 1
        base["server"]["log_level"] = "debug"
        base["security"]["rate_limit_enabled"] = False
        base["observability"]["log_level"] = "DEBUG"
        base["observability"]["json_logging"] = False
        base["debug"] = True
        base["engine"]["config_path"] = "config/default_config.yaml"

    elif mode == RuntimeMode.LOCAL_PROD:
        base["server"]["workers"] = 2
        base["server"]["log_level"] = "info"
        base["security"]["rate_limit_enabled"] = True
        base["security"]["secure_mode"] = True
        base["observability"]["log_level"] = "INFO"
        base["observability"]["json_logging"] = True
        base["observability"]["metrics_enabled"] = True
        base["engine"]["config_path"] = "config/production.yaml"

    elif mode == RuntimeMode.CLOUD_PROD:
        base["server"]["workers"] = 4
        base["server"]["log_level"] = "info"
        base["server"]["timeout_keep_alive"] = 60
        base["security"]["rate_limit_enabled"] = True
        base["security"]["secure_mode"] = True
        base["observability"]["log_level"] = "INFO"
        base["observability"]["json_logging"] = True
        base["observability"]["metrics_enabled"] = True
        base["observability"]["tracing_enabled"] = True
        base["observability"]["otel_exporter_type"] = "otlp"
        base["engine"]["config_path"] = "config/production.yaml"

    elif mode == RuntimeMode.AGENT_API:
        base["server"]["workers"] = 2
        base["server"]["log_level"] = "info"
        base["security"]["rate_limit_enabled"] = True
        base["security"]["secure_mode"] = True
        base["observability"]["log_level"] = "INFO"
        base["observability"]["json_logging"] = True
        base["observability"]["metrics_enabled"] = True
        base["engine"]["enable_fslgs"] = True
        base["engine"]["config_path"] = "config/production.yaml"

    return base


def get_runtime_mode() -> RuntimeMode:
    """Get the current runtime mode from environment.

    Uses MLSDM_RUNTIME_MODE environment variable.
    Defaults to DEV if not set or invalid.

    Returns:
        RuntimeMode enum value.
    """
    mode_str = os.environ.get("MLSDM_RUNTIME_MODE", "dev").lower()
    try:
        return RuntimeMode(mode_str)
    except ValueError:
        return RuntimeMode.DEV


def get_runtime_config(mode: RuntimeMode | None = None) -> RuntimeConfig:
    """Get runtime configuration for the specified mode.

    Args:
        mode: Runtime mode. If None, auto-detected from MLSDM_RUNTIME_MODE env var.

    Returns:
        RuntimeConfig instance with merged defaults and environment overrides.
    """
    if mode is None:
        mode = get_runtime_mode()

    defaults = _get_mode_defaults(mode)

    # Server config with env overrides
    server = ServerConfig(
        host=_get_env_str("HOST", defaults["server"]["host"]),
        port=_get_env_int("PORT", defaults["server"]["port"]),
        workers=_get_env_int("MLSDM_WORKERS", defaults["server"]["workers"]),
        reload=_get_env_bool("MLSDM_RELOAD", defaults["server"]["reload"]),
        log_level=_get_env_str("MLSDM_LOG_LEVEL", defaults["server"]["log_level"]),
        timeout_keep_alive=_get_env_int(
            "MLSDM_TIMEOUT_KEEP_ALIVE", defaults["server"]["timeout_keep_alive"]
        ),
    )

    # Security config with env overrides
    # Note: DISABLE_RATE_LIMIT is part of stable API (not legacy)
    # It's a convenience variable that inverts to rate_limit_enabled
    # This is separate from MLSDM_* prefix which is reserved for SystemConfig overrides

    # Determine rate_limit_enabled: prioritize DISABLE_RATE_LIMIT if set, otherwise use default
    if "DISABLE_RATE_LIMIT" in os.environ:
        rate_limit_enabled = not _get_env_bool("DISABLE_RATE_LIMIT", False)
    else:
        rate_limit_enabled = defaults["security"]["rate_limit_enabled"]

    security = SecurityConfig(
        api_key=os.environ.get("API_KEY", defaults["security"]["api_key"]),
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_requests=_get_env_int(
            "RATE_LIMIT_REQUESTS", defaults["security"]["rate_limit_requests"]
        ),
        rate_limit_window=_get_env_int(
            "RATE_LIMIT_WINDOW", defaults["security"]["rate_limit_window"]
        ),
        secure_mode=_get_env_bool("MLSDM_SECURE_MODE", defaults["security"]["secure_mode"]),
        cors_origins=defaults["security"]["cors_origins"],
    )

    # Observability config with env overrides
    otel_sdk_disabled = _get_env_bool(
        "OTEL_SDK_DISABLED", not defaults["observability"]["tracing_enabled"]
    )
    observability = ObservabilityConfig(
        log_level=_get_env_str("LOG_LEVEL", defaults["observability"]["log_level"]),
        json_logging=_get_env_bool("JSON_LOGGING", defaults["observability"]["json_logging"]),
        metrics_enabled=_get_env_bool(
            "ENABLE_METRICS", defaults["observability"]["metrics_enabled"]
        ),
        tracing_enabled=_get_env_bool(
            "OTEL_TRACING_ENABLED", defaults["observability"]["tracing_enabled"]
        )
        and not otel_sdk_disabled,
        otel_exporter_type=_get_env_str(
            "OTEL_EXPORTER_TYPE", defaults["observability"]["otel_exporter_type"]
        ),
        otel_service_name=_get_env_str(
            "OTEL_SERVICE_NAME", defaults["observability"]["otel_service_name"]
        ),
    )

    # Engine config with env overrides
    engine = EngineConfig(
        llm_backend=_get_env_str("LLM_BACKEND", defaults["engine"]["llm_backend"]),
        embedding_dim=_get_env_int("EMBEDDING_DIM", defaults["engine"]["embedding_dim"]),
        enable_fslgs=_get_env_bool("ENABLE_FSLGS", defaults["engine"]["enable_fslgs"]),
        enable_metrics=_get_env_bool(
            "MLSDM_ENGINE_ENABLE_METRICS", defaults["engine"]["enable_metrics"]
        ),
        config_path=_get_env_str("CONFIG_PATH", defaults["engine"]["config_path"]),
    )

    return RuntimeConfig(
        mode=mode,
        server=server,
        security=security,
        observability=observability,
        engine=engine,
        debug=_get_env_bool("MLSDM_DEBUG", defaults["debug"]),
    )


def apply_runtime_config(config: RuntimeConfig) -> None:
    """Apply runtime configuration to environment.

    Sets environment variables based on the configuration.
    Useful for ensuring consistent configuration across all components.

    Args:
        config: RuntimeConfig instance to apply.
    """
    for key, value in config.to_env_dict().items():
        os.environ[key] = value


def print_runtime_config(config: RuntimeConfig) -> None:
    """Print runtime configuration in a human-readable format.

    Args:
        config: RuntimeConfig instance to print.
    """
    print("=" * 60)
    print(f"MLSDM Runtime Configuration ({config.mode.value})")
    print("=" * 60)
    print()
    print("Server:")
    print(f"  Host: {config.server.host}")
    print(f"  Port: {config.server.port}")
    print(f"  Workers: {config.server.workers}")
    print(f"  Reload: {config.server.reload}")
    print(f"  Log Level: {config.server.log_level}")
    print()
    print("Security:")
    print(f"  API Key: {'<set>' if config.security.api_key else '<not set>'}")
    print(f"  Rate Limit Enabled: {config.security.rate_limit_enabled}")
    print(f"  Secure Mode: {config.security.secure_mode}")
    print()
    print("Observability:")
    print(f"  Log Level: {config.observability.log_level}")
    print(f"  JSON Logging: {config.observability.json_logging}")
    print(f"  Metrics Enabled: {config.observability.metrics_enabled}")
    print(f"  Tracing Enabled: {config.observability.tracing_enabled}")
    print()
    print("Engine:")
    print(f"  LLM Backend: {config.engine.llm_backend}")
    print(f"  Embedding Dim: {config.engine.embedding_dim}")
    print(f"  FSLGS Enabled: {config.engine.enable_fslgs}")
    print(f"  Config Path: {config.engine.config_path}")
    print("=" * 60)

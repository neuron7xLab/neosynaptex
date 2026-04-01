"""
API configuration for MyceliumFractalNet.

Provides configuration management for API authentication, rate limiting,
logging, and other production features. Configuration is sourced from
environment variables and optional config files.

Environment Variables:
    MFN_ENV                  - Environment name: dev, staging, prod (default: dev)
    MFN_API_KEY_REQUIRED     - Whether API key authentication is required (default: false in dev)
    MFN_API_KEY              - Primary API key for authentication
    MFN_API_KEY_FILE         - Path to a file containing the primary API key
    MFN_API_KEYS             - Comma-separated list of valid API keys
    MFN_API_KEYS_FILE        - Path to a file with newline/CSV/JSON list of keys
    MFN_RATE_LIMIT_REQUESTS  - Max requests per minute (default: 100)
    MFN_RATE_LIMIT_WINDOW    - Rate limit window in seconds (default: 60)
    MFN_LOG_LEVEL            - Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    MFN_LOG_FORMAT           - Log format: json or text (default: json in prod, text in dev)
    MFN_METRICS_ENDPOINT     - Metrics endpoint path (default: /metrics)

Reference: docs/MFN_BACKLOG.md#MFN-API-001, MFN-API-002, MFN-LOG-001
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from mycelium_fractal_net.security import SecretManager, SecretRetrievalError


class Environment(str, Enum):
    """Environment types for configuration."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


def _normalize_endpoint_path(value: str, default: str) -> str:
    """Normalize endpoint paths to ensure leading slash and no trailing slash."""
    raw = (value or "").strip()
    if not raw:
        raw = default

    if not raw.startswith("/"):
        raw = f"/{raw}"

    if raw != "/" and raw.endswith("/"):
        raw = raw.rstrip("/")

    return raw


def _parse_positive_int(env_var: str, default: int) -> int:
    """Parse a positive integer from an environment variable."""
    raw_value = os.getenv(env_var)
    if raw_value is None or raw_value == "":
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_var} must be an integer, got {raw_value!r}.") from exc
    if value <= 0:
        raise ValueError(f"{env_var} must be a positive integer, got {value}.")
    return value


@dataclass
class AuthConfig:
    """
    Authentication configuration.

    Attributes:
        api_key_required: Whether API key is required for protected endpoints.
        api_keys: List of valid API keys for authentication.
        public_endpoints: Endpoints that don't require authentication.
    """

    api_key_required: bool = False
    api_keys: list[str] = field(default_factory=list)
    public_endpoints: list[str] = field(
        default_factory=lambda: [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    )

    @classmethod
    def from_env(cls, env: Environment) -> AuthConfig:
        """
        Create AuthConfig from environment variables.

        Args:
            env: Current environment (dev/staging/prod).

        Returns:
            AuthConfig: Configured authentication settings.
        """
        secret_manager = SecretManager()

        # Determine if auth is required based on environment
        env_required = os.getenv("MFN_API_KEY_REQUIRED", "").lower()
        if env_required:
            api_key_required = env_required in ("true", "1", "yes")
        else:
            # Default: required in staging/prod, optional in dev
            api_key_required = env != Environment.DEV

        # Collect API keys from environment
        api_keys: list[str] = []

        # Single key via env or file-backed secret
        try:
            single_key = secret_manager.get_secret("MFN_API_KEY", file_env_key="MFN_API_KEY_FILE")
        except SecretRetrievalError as exc:
            raise ValueError(str(exc)) from exc
        if single_key:
            api_keys.append(single_key)

        # Multiple keys (comma-separated/newline/JSON) via env or file
        try:
            multi_keys = secret_manager.get_list("MFN_API_KEYS", file_env_key="MFN_API_KEYS_FILE")
        except SecretRetrievalError as exc:
            raise ValueError(str(exc)) from exc

        if multi_keys:
            api_keys.extend(multi_keys)

        # Guard against misconfiguration: authentication required but no keys provided
        if api_key_required and not api_keys:
            raise ValueError(
                "API key authentication is required but no API keys were provided. "
                "Set MFN_API_KEY or MFN_API_KEYS to configure valid credentials."
            )

        # In dev mode without explicit keys and when auth isn't enforced,
        # add a convenience key to simplify local testing.
        if env == Environment.DEV and not api_keys:
            api_keys.append("dev-key-for-testing")

        return cls(
            api_key_required=api_key_required,
            api_keys=api_keys,
        )


@dataclass
class RateLimitConfig:
    """
    Rate limiting configuration.

    Attributes:
        max_requests: Maximum requests per window.
        window_seconds: Time window for rate limit counting.
        enabled: Whether rate limiting is enabled.
        per_endpoint_limits: Optional per-endpoint rate limits.
    """

    max_requests: int = 100
    window_seconds: int = 60
    enabled: bool = True
    per_endpoint_limits: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Environment) -> RateLimitConfig:
        """
        Create RateLimitConfig from environment variables.

        Args:
            env: Current environment (dev/staging/prod).

        Returns:
            RateLimitConfig: Configured rate limiting settings.
        """
        max_requests = _parse_positive_int("MFN_RATE_LIMIT_REQUESTS", 100)
        window_seconds = _parse_positive_int("MFN_RATE_LIMIT_WINDOW", 60)

        # Disable rate limiting in dev by default unless explicitly enabled
        enabled_env = os.getenv("MFN_RATE_LIMIT_ENABLED", "").lower()
        if enabled_env:
            enabled = enabled_env in ("true", "1", "yes")
        else:
            enabled = env != Environment.DEV

        metrics_endpoint = _normalize_endpoint_path(
            os.getenv("MFN_METRICS_ENDPOINT", "/metrics"),
            "/metrics",
        )

        # Per-endpoint limits (can be extended via config files)
        per_endpoint_limits = {
            "/health": 1000,  # Health checks can be frequent
            metrics_endpoint: 1000,  # Metrics scraping can be frequent
            "/validate": 50,  # Validation is more expensive
            "/simulate": 50,  # Simulation is expensive
            "/nernst": 200,  # Nernst is lightweight
            "/federated/aggregate": 50,  # Federated is expensive
        }

        return cls(
            max_requests=max_requests,
            window_seconds=window_seconds,
            enabled=enabled,
            per_endpoint_limits=per_endpoint_limits,
        )


@dataclass
class LoggingConfig:
    """
    Logging configuration.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        format: Log format (json or text).
        include_request_body: Whether to log request bodies.
    """

    level: str = "INFO"
    format: str = "json"
    include_request_body: bool = False

    @classmethod
    def from_env(cls, env: Environment) -> LoggingConfig:
        """
        Create LoggingConfig from environment variables.

        Args:
            env: Current environment (dev/staging/prod).

        Returns:
            LoggingConfig: Configured logging settings.
        """
        level = os.getenv("MFN_LOG_LEVEL", "INFO").upper()

        # Default format based on environment
        default_format = "json" if env == Environment.PROD else "text"
        log_format = os.getenv("MFN_LOG_FORMAT", default_format).lower()

        # Include request body only in dev
        include_body = env == Environment.DEV

        return cls(
            level=level,
            format=log_format,
            include_request_body=include_body,
        )


@dataclass
class MetricsConfig:
    """
    Metrics configuration.

    Attributes:
        enabled: Whether metrics collection is enabled.
        endpoint: Metrics endpoint path.
        include_in_auth: Whether /metrics requires authentication.
    """

    enabled: bool = True
    endpoint: str = "/metrics"
    include_in_auth: bool = False

    @classmethod
    def from_env(cls, env: Environment) -> MetricsConfig:
        """
        Create MetricsConfig from environment variables.

        Args:
            env: Current environment (dev/staging/prod).

        Returns:
            MetricsConfig: Configured metrics settings.
        """
        enabled_env = os.getenv("MFN_METRICS_ENABLED", "true").lower()
        enabled = enabled_env in ("true", "1", "yes")

        include_in_auth_env = os.getenv("MFN_METRICS_INCLUDE_IN_AUTH", "false").lower()
        include_in_auth = include_in_auth_env in ("true", "1", "yes")

        endpoint_env = os.getenv("MFN_METRICS_ENDPOINT", cls.endpoint)
        endpoint = _normalize_endpoint_path(endpoint_env, cls.endpoint)

        return cls(
            enabled=enabled,
            include_in_auth=include_in_auth,
            endpoint=endpoint,
        )


@dataclass
class APIConfig:
    """
    Complete API configuration.

    Aggregates all API-related configuration including authentication,
    rate limiting, logging, and metrics.

    Attributes:
        env: Current environment.
        auth: Authentication configuration.
        rate_limit: Rate limiting configuration.
        logging: Logging configuration.
        metrics: Metrics configuration.
    """

    env: Environment = Environment.DEV
    auth: AuthConfig = field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)

    def __post_init__(self) -> None:
        """Align authentication config with metrics exposure settings."""
        metrics_path = _normalize_endpoint_path(self.metrics.endpoint, "/metrics")
        self.metrics.endpoint = metrics_path
        public_endpoints = [
            endpoint
            for endpoint in self.auth.public_endpoints
            if endpoint not in {metrics_path, "/metrics"}
        ]

        if self.metrics.include_in_auth:
            # Ensure metrics endpoint is protected
            self.auth.public_endpoints = [
                endpoint for endpoint in public_endpoints if endpoint != metrics_path
            ]
        else:
            # Maintain metrics as public when authentication is not required
            public_endpoints.append(metrics_path)
            deduped: list[str] = []
            for endpoint in public_endpoints:
                if endpoint not in deduped:
                    deduped.append(endpoint)
            self.auth.public_endpoints = deduped

    @classmethod
    def from_env(cls) -> APIConfig:
        """
        Create complete API configuration from environment.

        Returns:
            APIConfig: Fully configured API settings.
        """
        env_str = os.getenv("MFN_ENV", "dev").lower()
        try:
            env = Environment(env_str)
        except ValueError:
            env = Environment.DEV

        return cls(
            env=env,
            auth=AuthConfig.from_env(env),
            rate_limit=RateLimitConfig.from_env(env),
            logging=LoggingConfig.from_env(env),
            metrics=MetricsConfig.from_env(env),
        )


# Singleton instance for easy access
_config: APIConfig | None = None


def get_api_config() -> APIConfig:
    """
    Get the API configuration singleton.

    Returns:
        APIConfig: Current API configuration.
    """
    global _config
    if _config is None:
        _config = APIConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton (useful for testing)."""
    global _config
    _config = None


__all__ = [
    "APIConfig",
    "AuthConfig",
    "Environment",
    "LoggingConfig",
    "MetricsConfig",
    "RateLimitConfig",
    "get_api_config",
    "reset_config",
]

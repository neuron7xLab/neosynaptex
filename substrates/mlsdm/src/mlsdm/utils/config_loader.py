"""Configuration loading with validation for MLSDM Governed Cognitive Memory.

This module provides utilities for loading and validating configuration files
with comprehensive error messages and type safety.

Optimization: Includes configuration caching to avoid repeated file I/O
and validation for the same configuration files.
"""

import configparser
import hashlib
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from mlsdm.utils.config_schema import SystemConfig, validate_config_dict


@dataclass
class _CachedConfig:
    """Internal cached configuration entry."""

    config: dict[str, Any]
    mtime: float
    file_hash: str
    timestamp: float


class ConfigCache:
    """Thread-safe cache for loaded configurations.

    Caches configurations by file path with invalidation based on:
    - File modification time
    - File content hash (for reliability)
    - TTL expiration

    This reduces file I/O and validation overhead for repeated config loads.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_entries: int = 100,
        now: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the config cache.

        Args:
            ttl_seconds: Time-to-live for cached entries (default: 5 minutes)
            max_entries: Maximum number of cached configurations
            now: Optional clock function for deterministic testing
        """
        self._cache: dict[str, _CachedConfig] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0
        self._now = now or time.time

    def _compute_file_hash(self, path: str) -> str:
        """Compute SHA-256 hash of file contents."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def get(self, cache_key: str, file_path: str | None = None) -> dict[str, Any] | None:
        """Get cached configuration if valid.

        Args:
            cache_key: Cache key (may be path or composite key)
            file_path: Actual file path for mtime validation (optional)

        Returns:
            Cached configuration dict or None if not cached/expired
        """
        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[cache_key]
            current_time = self._now()

            # Check TTL expiration
            if current_time - entry.timestamp > self.ttl_seconds:
                del self._cache[cache_key]
                self._misses += 1
                return None

            # Check if file was modified (only if file_path provided)
            if file_path is not None:
                try:
                    current_mtime = os.path.getmtime(file_path)
                    if current_mtime != entry.mtime:
                        del self._cache[cache_key]
                        self._misses += 1
                        return None
                    current_hash = self._compute_file_hash(file_path)
                    if entry.file_hash and current_hash != entry.file_hash:
                        del self._cache[cache_key]
                        self._misses += 1
                        return None
                except OSError:
                    del self._cache[cache_key]
                    self._misses += 1
                    return None

            self._hits += 1
            # Return a copy to prevent external modification
            return entry.config.copy()

    def put(self, cache_key: str, config: dict[str, Any], file_path: str | None = None) -> None:
        """Store configuration in cache.

        Args:
            cache_key: Cache key (may be path or composite key)
            config: Configuration dictionary to cache
            file_path: Actual file path for mtime tracking (optional)
        """
        with self._lock:
            # Evict oldest entries if cache is full
            while len(self._cache) >= self.max_entries:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
                del self._cache[oldest_key]

            # Use file_path for mtime and hash, or cache_key if not provided
            path_for_metadata = file_path if file_path is not None else cache_key
            try:
                mtime = os.path.getmtime(path_for_metadata)
                file_hash = self._compute_file_hash(path_for_metadata)
            except OSError:
                # If we can't read file metadata, use defaults
                mtime = self._now()
                file_hash = ""

            self._cache[cache_key] = _CachedConfig(
                config=config.copy(),
                mtime=mtime,
                file_hash=file_hash,
                timestamp=self._now(),
            )

    def invalidate(self, path: str) -> bool:
        """Invalidate a specific cached configuration.

        Args:
            path: Path to configuration file

        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache if key == path or key.startswith(f"{path}:")
            ]

            for key in keys_to_remove:
                del self._cache[key]

            return bool(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached configurations."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "size": len(self._cache),
            }


# Global config cache instance
_config_cache: ConfigCache | None = None
_config_cache_lock = threading.Lock()


def get_config_cache() -> ConfigCache:
    """Get or create the global config cache."""
    global _config_cache
    if _config_cache is None:
        with _config_cache_lock:
            if _config_cache is None:
                _config_cache = ConfigCache()
    return _config_cache


class ConfigLoader:
    """Load and validate configuration files with schema validation.

    Optimization: Uses ConfigCache for repeated loads of the same file,
    reducing file I/O and validation overhead.
    """

    @staticmethod
    def load_config(
        path: str,
        validate: bool = True,
        env_override: bool = True,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Load configuration from file with optional validation.

        Args:
            path: Path to configuration file (YAML or INI)
            validate: If True, validate against schema
            env_override: If True, allow environment variable overrides
            use_cache: If True, use configuration cache (default: True)

        Returns:
            Configuration dictionary

        Raises:
            TypeError: If path is not a string
            ValueError: If file format is unsupported or validation fails
            FileNotFoundError: If configuration file does not exist
        """
        if not isinstance(path, str):
            raise TypeError("Path must be a string.")

        resource_config: dict[str, Any] | None = None
        resource_loaded = False

        if path == "config/default_config.yaml" and not Path(path).is_file():
            resource_config = ConfigLoader._load_yaml_resource(
                package="mlsdm.config", resource="default_config.yaml"
            )
            resource_loaded = True

        if not resource_loaded and not Path(path).is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        if not path.endswith((".yaml", ".yml", ".ini")):
            raise ValueError(
                "Unsupported configuration file format. "
                "Only YAML (.yaml, .yml) and INI (.ini) are supported."
            )

        # Optimization: Try cache first (only for validated configs without env override)
        cache_key = f"{path}:{validate}:{env_override}"
        if not resource_loaded and use_cache and validate and not env_override:
            cache = get_config_cache()
            cached = cache.get(cache_key, file_path=path)
            if cached is not None:
                return cached

        config: dict[str, Any] = {}

        # Load from file
        if resource_loaded and resource_config is not None:
            config = resource_config
        elif path.endswith((".yaml", ".yml")):
            config = ConfigLoader._load_yaml(path)
        else:
            config = ConfigLoader._load_ini(path)

        # Apply environment variable overrides if enabled
        if env_override:
            config = ConfigLoader._apply_env_overrides(config)

        # Validate against schema if enabled
        if validate:
            try:
                validated_config = validate_config_dict(config)
                # Convert back to dict for backward compatibility
                config = validated_config.model_dump()
            except ValueError as e:
                raise ValueError(
                    f"Configuration validation failed for '{path}':\n{str(e)}\n\n"
                    f"Please check your configuration file against the schema "
                    f"documentation in mlsdm.utils.config_schema.py"
                ) from e

        # Optimization: Cache the result (only for validated configs without env override)
        if not resource_loaded and use_cache and validate and not env_override:
            cache = get_config_cache()
            cache.put(cache_key, config, file_path=path)

        return config

    @staticmethod
    def _load_yaml_resource(package: str, resource: str) -> dict[str, Any]:
        """Load YAML configuration from a packaged resource."""
        try:
            text = resources.files(package).joinpath(resource).read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Resource '{resource}' not found in package '{package}'") from e
        except Exception as e:
            raise ValueError(
                f"Error reading resource '{resource}' from package '{package}': {str(e)}"
            ) from e

        try:
            config = yaml.safe_load(text) or {}
            return config
        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid YAML syntax in resource '{resource}' from package '{package}': {str(e)}"
            ) from e

    @staticmethod
    def _load_yaml(path: str) -> dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in '{path}': {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Error reading YAML file '{path}': {str(e)}") from e

    @staticmethod
    def _load_ini(path: str) -> dict[str, Any]:
        """Load INI configuration file."""
        try:
            config: dict[str, Any] = {}
            parser = configparser.ConfigParser()
            parser.read(path, encoding="utf-8")

            for section in parser.sections():
                for key, value in parser[section].items():
                    lower = value.lower()
                    if lower in ("true", "false"):
                        config[key] = lower == "true"
                    else:
                        try:
                            config[key] = int(value)
                        except ValueError:
                            try:
                                config[key] = float(value)
                            except ValueError:
                                config[key] = value

            return config
        except Exception as e:
            raise ValueError(f"Error reading INI file '{path}': {str(e)}") from e

    @staticmethod
    def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to configuration.

        Environment variables should be prefixed with MLSDM_ and use
        double underscores for nested keys. For example:
        - MLSDM_DIMENSION=768
        - MLSDM_MORAL_FILTER__THRESHOLD=0.7
        - MLSDM_COGNITIVE_RHYTHM__WAKE_DURATION=10
        """
        prefix = "MLSDM_"

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Remove prefix and convert to lowercase
            config_key = env_key[len(prefix) :].lower()

            # Filter out empty segments (e.g., trailing '__') to avoid creating empty keys
            parts = [p for p in config_key.split("__") if p]
            if not parts:
                continue

            target = config
            path_segments: list[str] = []

            # Traverse or create nested dictionaries except for the final key.
            # If an intermediate node is not a dict, raise a clear error to avoid clobbering.
            for part in parts[:-1]:
                path_segments.append(part)
                current_path = ".".join(path_segments)
                existing = target.get(part)
                if existing is None:
                    target[part] = {}
                    target = target[part]
                elif isinstance(existing, dict):
                    target = existing
                else:
                    raise ValueError(
                        "Environment override target is not a mapping; refusing to overwrite "
                        f"path '{current_path}' (existing type: {type(existing).__name__}). "
                        "Ensure intermediate keys are dictionaries before applying nested overrides."
                    )

            target[parts[-1]] = ConfigLoader._parse_env_value(env_value)

        return config

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable value to appropriate type."""
        # Try boolean
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False

        # Try integer
        # Conversion precedence: attempt integers first, then floats, else return raw string
        try:
            return int(value)
        except ValueError:
            # Try float next
            try:
                return float(value)
            except ValueError:
                return value

    @staticmethod
    def load_validated_config(path: str) -> SystemConfig:
        """Load and return validated configuration as SystemConfig object.

        Args:
            path: Path to configuration file

        Returns:
            Validated SystemConfig instance

        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If file does not exist
        """
        config_dict = ConfigLoader.load_config(path, validate=True)
        return validate_config_dict(config_dict)

    @staticmethod
    def get_aphasia_config_from_dict(config_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract aphasia configuration parameters for NeuroLangWrapper.

        This is a convenience method to extract aphasia configuration
        from a loaded config dict and return it in a format suitable
        for passing to NeuroLangWrapper constructor.

        Args:
            config_dict: Configuration dictionary (from load_config)

        Returns:
            Dictionary with keys matching NeuroLangWrapper aphasia parameters:
            - aphasia_detect_enabled: bool
            - aphasia_repair_enabled: bool
            - aphasia_severity_threshold: float

        Example:
            >>> config = ConfigLoader.load_config("config/production.yaml")
            >>> aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config)
            >>> wrapper = NeuroLangWrapper(
            ...     llm_generate_fn=my_llm,
            ...     embedding_fn=my_embed,
            ...     **aphasia_params
            ... )
        """
        aphasia_section = config_dict.get("aphasia", {})
        return {
            "aphasia_detect_enabled": aphasia_section.get("detect_enabled", True),
            "aphasia_repair_enabled": aphasia_section.get("repair_enabled", True),
            "aphasia_severity_threshold": aphasia_section.get("severity_threshold", 0.3),
        }

    @staticmethod
    def get_neurolang_config_from_dict(config_dict: dict[str, Any]) -> dict[str, Any]:
        """Extract NeuroLang configuration parameters for NeuroLangWrapper.

        This is a convenience method to extract NeuroLang configuration
        from a loaded config dict and return it in a format suitable
        for passing to NeuroLangWrapper constructor.

        Args:
            config_dict: Configuration dictionary (from load_config)

        Returns:
            Dictionary with keys matching NeuroLangWrapper neurolang parameters:
            - neurolang_mode: str
            - neurolang_checkpoint_path: str | None

        Example:
            >>> config = ConfigLoader.load_config("config/production.yaml")
            >>> neu_params = ConfigLoader.get_neurolang_config_from_dict(config)
            >>> aphasia_params = ConfigLoader.get_aphasia_config_from_dict(config)
            >>> wrapper = NeuroLangWrapper(
            ...     llm_generate_fn=my_llm,
            ...     embedding_fn=my_embed,
            ...     dim=384,
            ...     **aphasia_params,
            ...     **neu_params
            ... )
        """
        neurolang_section = config_dict.get("neurolang", {})
        return {
            "neurolang_mode": neurolang_section.get("mode", "eager_train"),
            "neurolang_checkpoint_path": neurolang_section.get("checkpoint_path"),
        }

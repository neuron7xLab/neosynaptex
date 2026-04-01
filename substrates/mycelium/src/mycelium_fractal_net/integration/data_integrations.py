"""
Data integrations module for MyceliumFractalNet iteration optimization.

Provides 77 data integration constants and utilities for optimizing
security iterations and cryptographic operations.

Integration Categories:
    1-10: Core iteration parameters
    11-20: Key derivation integrations
    21-30: Encryption optimization integrations
    31-40: Hash function integrations
    41-50: Salt generation integrations
    51-60: Memory optimization integrations
    61-70: Parallelization integrations
    71-77: Validation and audit integrations

Usage:
    >>> from mycelium_fractal_net.integration.data_integrations import (
    ...     DataIntegrationConfig,
    ...     get_integration,
    ...     INTEGRATION_COUNT,
    ... )
    >>> config = DataIntegrationConfig()
    >>> integration = get_integration(1)
    >>> # Returns core iteration parameter integration

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntegrationCategory(str, Enum):
    """Categories for data integrations."""

    CORE_ITERATION = "core_iteration"
    KEY_DERIVATION = "key_derivation"
    ENCRYPTION_OPTIMIZATION = "encryption_optimization"
    HASH_FUNCTION = "hash_function"
    SALT_GENERATION = "salt_generation"
    MEMORY_OPTIMIZATION = "memory_optimization"
    PARALLELIZATION = "parallelization"
    VALIDATION_AUDIT = "validation_audit"


# === Total Integration Count ===
INTEGRATION_COUNT: int = 77


# === Core Iteration Parameters (1-10) ===
CORE_ITERATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    1: {
        "name": "base_iteration_factor",
        "value": 1.0,
        "description": "Base iteration multiplier",
    },
    2: {
        "name": "iteration_scaling",
        "value": 1.5,
        "description": "Iteration scaling factor",
    },
    3: {"name": "iteration_warmup", "value": 100, "description": "Warmup iterations"},
    4: {
        "name": "iteration_cooldown",
        "value": 50,
        "description": "Cooldown iterations",
    },
    5: {
        "name": "iteration_batch_size",
        "value": 1000,
        "description": "Batch size for iterations",
    },
    6: {
        "name": "iteration_checkpoint",
        "value": 10000,
        "description": "Checkpoint interval",
    },
    7: {
        "name": "iteration_timeout_ms",
        "value": 5000,
        "description": "Timeout in milliseconds",
    },
    8: {
        "name": "iteration_retry_count",
        "value": 3,
        "description": "Retry count on failure",
    },
    9: {
        "name": "iteration_cache_size",
        "value": 1024,
        "description": "Cache size in KB",
    },
    10: {
        "name": "iteration_buffer_size",
        "value": 4096,
        "description": "Buffer size in bytes",
    },
}

# === Key Derivation Integrations (11-20) ===
KEY_DERIVATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    11: {
        "name": "kdf_algorithm",
        "value": "pbkdf2",
        "description": "Key derivation algorithm",
    },
    12: {"name": "kdf_hash", "value": "sha256", "description": "Hash function for KDF"},
    13: {"name": "kdf_salt_length", "value": 16, "description": "Salt length in bytes"},
    14: {
        "name": "kdf_key_length",
        "value": 32,
        "description": "Derived key length in bytes",
    },
    15: {
        "name": "kdf_memory_cost",
        "value": 65536,
        "description": "Memory cost for Argon2",
    },
    16: {"name": "kdf_time_cost", "value": 3, "description": "Time cost for Argon2"},
    17: {
        "name": "kdf_parallelism",
        "value": 4,
        "description": "Parallelism for Argon2",
    },
    18: {"name": "kdf_version", "value": "1.3", "description": "KDF version"},
    19: {
        "name": "kdf_context",
        "value": "encryption",
        "description": "Derivation context",
    },
    20: {"name": "kdf_info_length", "value": 32, "description": "Info length for HKDF"},
}

# === Encryption Optimization Integrations (21-30) ===
ENCRYPTION_OPTIMIZATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    21: {"name": "enc_block_size", "value": 16, "description": "Encryption block size"},
    22: {"name": "enc_iv_length", "value": 16, "description": "IV length in bytes"},
    23: {
        "name": "enc_tag_length",
        "value": 16,
        "description": "Authentication tag length",
    },
    # Security note: Key rotation of 86400s (24h) follows NIST SP 800-57 recommendations.
    # Shorter intervals (e.g., 3600s) may be used for higher security requirements.
    24: {
        "name": "enc_key_rotation",
        "value": 86400,
        "description": "Key rotation interval (seconds). Security-critical: 24h default.",
    },
    25: {
        "name": "enc_compression",
        "value": False,
        "description": "Enable compression",
    },
    26: {"name": "enc_padding", "value": "pkcs7", "description": "Padding scheme"},
    27: {"name": "enc_mode", "value": "cbc", "description": "Encryption mode"},
    28: {
        "name": "enc_chunk_size",
        "value": 65536,
        "description": "Chunk size for streaming",
    },
    29: {"name": "enc_header_size", "value": 32, "description": "Header size in bytes"},
    30: {"name": "enc_footer_size", "value": 32, "description": "Footer size in bytes"},
}

# === Hash Function Integrations (31-40) ===
HASH_FUNCTION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    31: {
        "name": "hash_algorithm",
        "value": "sha256",
        "description": "Primary hash algorithm",
    },
    32: {
        "name": "hash_output_length",
        "value": 32,
        "description": "Hash output length",
    },
    33: {"name": "hash_block_size", "value": 64, "description": "Hash block size"},
    34: {"name": "hmac_key_length", "value": 32, "description": "HMAC key length"},
    35: {
        "name": "hash_iterations",
        "value": 1,
        "description": "Hash iterations for strengthening",
    },
    36: {
        "name": "hash_personalization",
        "value": "",
        "description": "Personalization string",
    },
    37: {"name": "hash_salt_prefix", "value": "mfn_", "description": "Salt prefix"},
    38: {
        "name": "hash_domain_separator",
        "value": "|",
        "description": "Domain separator",
    },
    39: {
        "name": "hash_version_byte",
        "value": 1,
        "description": "Version byte for hashes",
    },
    40: {"name": "hash_checksum_length", "value": 4, "description": "Checksum length"},
}

# === Salt Generation Integrations (41-50) ===
SALT_GENERATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    41: {
        "name": "salt_entropy_bits",
        "value": 128,
        "description": "Entropy bits for salt",
    },
    42: {"name": "salt_source", "value": "os_urandom", "description": "Random source"},
    43: {
        "name": "salt_unique_per_op",
        "value": True,
        "description": "Unique salt per operation",
    },
    44: {
        "name": "salt_timestamp_mix",
        "value": False,
        "description": "Mix timestamp in salt",
    },
    45: {
        "name": "salt_counter_mix",
        "value": False,
        "description": "Mix counter in salt",
    },
    46: {"name": "salt_version", "value": 1, "description": "Salt generation version"},
    47: {
        "name": "salt_encoding",
        "value": "raw",
        "description": "Salt encoding format",
    },
    48: {
        "name": "salt_derivation",
        "value": False,
        "description": "Enable salt derivation",
    },
    49: {
        "name": "salt_cache_enabled",
        "value": False,
        "description": "Enable salt caching",
    },
    50: {
        "name": "salt_validation",
        "value": True,
        "description": "Enable salt validation",
    },
}

# === Memory Optimization Integrations (51-60) ===
MEMORY_OPTIMIZATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    51: {
        "name": "mem_pool_size",
        "value": 1048576,
        "description": "Memory pool size in bytes",
    },
    52: {"name": "mem_alignment", "value": 64, "description": "Memory alignment"},
    53: {
        "name": "mem_secure_alloc",
        "value": True,
        "description": "Use secure allocation",
    },
    54: {
        "name": "mem_zero_on_free",
        "value": True,
        "description": "Zero memory on free",
    },
    55: {"name": "mem_lock_pages", "value": False, "description": "Lock memory pages"},
    56: {"name": "mem_guard_pages", "value": True, "description": "Use guard pages"},
    57: {
        "name": "mem_canary_enabled",
        "value": True,
        "description": "Enable memory canaries",
    },
    58: {
        "name": "mem_max_alloc",
        "value": 16777216,
        "description": "Maximum allocation size",
    },
    59: {
        "name": "mem_prealloc_count",
        "value": 16,
        "description": "Preallocated buffers",
    },
    60: {
        "name": "mem_gc_threshold",
        "value": 0.8,
        "description": "GC threshold (0.0-1.0)",
    },
}

# === Parallelization Integrations (61-70) ===
PARALLELIZATION_INTEGRATIONS: dict[int, dict[str, Any]] = {
    61: {
        "name": "parallel_enabled",
        "value": True,
        "description": "Enable parallelization",
    },
    62: {"name": "parallel_threads", "value": 4, "description": "Number of threads"},
    63: {
        "name": "parallel_chunk_size",
        "value": 4096,
        "description": "Chunk size for parallel ops",
    },
    64: {"name": "parallel_queue_depth", "value": 8, "description": "Work queue depth"},
    65: {
        "name": "parallel_affinity",
        "value": False,
        "description": "Enable CPU affinity",
    },
    66: {
        "name": "parallel_priority",
        "value": "normal",
        "description": "Thread priority",
    },
    67: {
        "name": "parallel_timeout",
        "value": 30000,
        "description": "Parallel op timeout (ms)",
    },
    68: {
        "name": "parallel_retry",
        "value": 2,
        "description": "Retry count for failed ops",
    },
    69: {
        "name": "parallel_batch_mode",
        "value": True,
        "description": "Enable batch processing",
    },
    70: {
        "name": "parallel_load_balance",
        "value": True,
        "description": "Enable load balancing",
    },
}

# === Validation and Audit Integrations (71-77) ===
VALIDATION_AUDIT_INTEGRATIONS: dict[int, dict[str, Any]] = {
    71: {"name": "audit_enabled", "value": True, "description": "Enable audit logging"},
    72: {"name": "audit_level", "value": "info", "description": "Audit log level"},
    73: {
        "name": "validation_strict",
        "value": True,
        "description": "Enable strict validation",
    },
    74: {
        "name": "validation_timeout",
        "value": 5000,
        "description": "Validation timeout (ms)",
    },
    75: {"name": "compliance_mode", "value": "soc2", "description": "Compliance mode"},
    76: {
        "name": "integrity_check",
        "value": True,
        "description": "Enable integrity checks",
    },
    77: {
        "name": "checksum_algorithm",
        "value": "crc32",
        "description": "Checksum algorithm",
    },
}


@dataclass
class DataIntegration:
    """
    Represents a single data integration.

    Attributes:
        id: Integration identifier (1-77).
        name: Integration name.
        value: Integration value.
        description: Human-readable description.
        category: Integration category.
        enabled: Whether the integration is enabled.
    """

    id: int
    name: str
    value: Any
    description: str
    category: IntegrationCategory
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "category": self.category.value,
            "enabled": self.enabled,
        }


def _get_category_for_id(integration_id: int) -> IntegrationCategory:
    """Determine category based on integration ID."""
    if 1 <= integration_id <= 10:
        return IntegrationCategory.CORE_ITERATION
    elif 11 <= integration_id <= 20:
        return IntegrationCategory.KEY_DERIVATION
    elif 21 <= integration_id <= 30:
        return IntegrationCategory.ENCRYPTION_OPTIMIZATION
    elif 31 <= integration_id <= 40:
        return IntegrationCategory.HASH_FUNCTION
    elif 41 <= integration_id <= 50:
        return IntegrationCategory.SALT_GENERATION
    elif 51 <= integration_id <= 60:
        return IntegrationCategory.MEMORY_OPTIMIZATION
    elif 61 <= integration_id <= 70:
        return IntegrationCategory.PARALLELIZATION
    elif 71 <= integration_id <= 77:
        return IntegrationCategory.VALIDATION_AUDIT
    else:
        raise ValueError(f"Invalid integration ID: {integration_id}")


def _get_integration_data(integration_id: int) -> dict[str, Any]:
    """Get raw integration data by ID."""
    all_integrations = {
        **CORE_ITERATION_INTEGRATIONS,
        **KEY_DERIVATION_INTEGRATIONS,
        **ENCRYPTION_OPTIMIZATION_INTEGRATIONS,
        **HASH_FUNCTION_INTEGRATIONS,
        **SALT_GENERATION_INTEGRATIONS,
        **MEMORY_OPTIMIZATION_INTEGRATIONS,
        **PARALLELIZATION_INTEGRATIONS,
        **VALIDATION_AUDIT_INTEGRATIONS,
    }
    if integration_id not in all_integrations:
        raise ValueError(f"Integration {integration_id} not found")
    return all_integrations[integration_id]


@dataclass
class DataIntegrationConfig:
    """
    Configuration for all 77 data integrations.

    Manages the complete set of data integrations for iteration
    optimization with support for enabling/disabling and customization.

    Attributes:
        version: Configuration version.
        integrations: Dictionary of all integrations.
        _changes: List of configuration changes.

    Example:
        >>> config = DataIntegrationConfig()
        >>> config.get_integration(1)
        DataIntegration(id=1, name='base_iteration_factor', ...)
    """

    version: str = "1.0.0"
    _integrations: dict[int, DataIntegration] = field(default_factory=dict)
    _changes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize all 77 integrations."""
        self._load_all_integrations()

    def _load_all_integrations(self) -> None:
        """Load all 77 integrations from definitions."""
        for i in range(1, INTEGRATION_COUNT + 1):
            data = _get_integration_data(i)
            category = _get_category_for_id(i)
            self._integrations[i] = DataIntegration(
                id=i,
                name=data["name"],
                value=data["value"],
                description=data["description"],
                category=category,
            )

    def get_integration(self, integration_id: int) -> DataIntegration:
        """
        Get integration by ID.

        Args:
            integration_id: Integration ID (1-77).

        Returns:
            DataIntegration: The requested integration.

        Raises:
            ValueError: If integration ID is invalid.
        """
        if integration_id not in self._integrations:
            raise ValueError(f"Invalid integration ID: {integration_id}")
        return self._integrations[integration_id]

    def get_integrations_by_category(
        self,
        category: IntegrationCategory,
    ) -> list[DataIntegration]:
        """
        Get all integrations for a specific category.

        Args:
            category: Integration category.

        Returns:
            List of integrations in the category.
        """
        return [intg for intg in self._integrations.values() if intg.category == category]

    def get_enabled_integrations(self) -> list[DataIntegration]:
        """Get all enabled integrations."""
        return [intg for intg in self._integrations.values() if intg.enabled]

    def enable_integration(self, integration_id: int) -> None:
        """Enable a specific integration."""
        if integration_id in self._integrations:
            self._integrations[integration_id].enabled = True
            self._record_change(integration_id, "enabled", True)

    def disable_integration(self, integration_id: int) -> None:
        """Disable a specific integration."""
        if integration_id in self._integrations:
            self._integrations[integration_id].enabled = False
            self._record_change(integration_id, "enabled", False)

    def update_value(self, integration_id: int, value: Any) -> None:
        """
        Update the value of an integration.

        Args:
            integration_id: Integration ID to update.
            value: New value.
        """
        if integration_id in self._integrations:
            old_value = self._integrations[integration_id].value
            self._integrations[integration_id].value = value
            self._record_change(integration_id, "value", value, old_value)

    def _record_change(
        self,
        integration_id: int,
        field: str,
        new_value: Any,
        old_value: Any = None,
    ) -> None:
        """Record a configuration change."""
        self._changes.append(
            {
                "integration_id": integration_id,
                "field": field,
                "new_value": new_value,
                "old_value": old_value,
            }
        )

    def get_change_history(self) -> list[dict[str, Any]]:
        """Get history of configuration changes."""
        return list(self._changes)

    def count_enabled(self) -> int:
        """Count enabled integrations."""
        return len(self.get_enabled_integrations())

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "version": self.version,
            "total_integrations": INTEGRATION_COUNT,
            "enabled_count": self.count_enabled(),
            "integrations": {i: intg.to_dict() for i, intg in self._integrations.items()},
        }

    def get_optimization_summary(self) -> dict[str, Any]:
        """
        Get optimization summary for all integrations.

        Returns:
            Summary of integration optimization status.
        """
        categories: dict[str, int] = {}
        for intg in self._integrations.values():
            cat = intg.category.value
            if cat not in categories:
                categories[cat] = 0
            if intg.enabled:
                categories[cat] += 1

        return {
            "total": INTEGRATION_COUNT,
            "enabled": self.count_enabled(),
            "disabled": INTEGRATION_COUNT - self.count_enabled(),
            "by_category": categories,
        }


# Global configuration instance
_data_integration_config: DataIntegrationConfig | None = None


def get_data_integration_config() -> DataIntegrationConfig:
    """
    Get the global data integration configuration.

    Returns:
        DataIntegrationConfig: Global configuration instance.
    """
    global _data_integration_config
    if _data_integration_config is None:
        _data_integration_config = DataIntegrationConfig()
    return _data_integration_config


def reset_data_integration_config() -> None:
    """Reset the global data integration configuration."""
    global _data_integration_config
    _data_integration_config = None


def get_integration(integration_id: int) -> DataIntegration:
    """
    Get a specific data integration.

    Convenience function using the global configuration.

    Args:
        integration_id: Integration ID (1-77).

    Returns:
        DataIntegration: The requested integration.

    Example:
        >>> integration = get_integration(1)
        >>> integration.name
        'base_iteration_factor'
    """
    return get_data_integration_config().get_integration(integration_id)


def list_all_integrations() -> list[DataIntegration]:
    """
    List all 77 data integrations.

    Returns:
        List of all integrations.
    """
    config = get_data_integration_config()
    return [config.get_integration(i) for i in range(1, INTEGRATION_COUNT + 1)]


def get_integration_categories() -> list[tuple[IntegrationCategory, int, int]]:
    """
    Get all integration categories with their ID ranges.

    Returns:
        List of (category, start_id, end_id) tuples.
    """
    return [
        (IntegrationCategory.CORE_ITERATION, 1, 10),
        (IntegrationCategory.KEY_DERIVATION, 11, 20),
        (IntegrationCategory.ENCRYPTION_OPTIMIZATION, 21, 30),
        (IntegrationCategory.HASH_FUNCTION, 31, 40),
        (IntegrationCategory.SALT_GENERATION, 41, 50),
        (IntegrationCategory.MEMORY_OPTIMIZATION, 51, 60),
        (IntegrationCategory.PARALLELIZATION, 61, 70),
        (IntegrationCategory.VALIDATION_AUDIT, 71, 77),
    ]


__all__ = [
    "CORE_ITERATION_INTEGRATIONS",
    "ENCRYPTION_OPTIMIZATION_INTEGRATIONS",
    "HASH_FUNCTION_INTEGRATIONS",
    # Constants
    "INTEGRATION_COUNT",
    "KEY_DERIVATION_INTEGRATIONS",
    "MEMORY_OPTIMIZATION_INTEGRATIONS",
    "PARALLELIZATION_INTEGRATIONS",
    "SALT_GENERATION_INTEGRATIONS",
    "VALIDATION_AUDIT_INTEGRATIONS",
    # Classes
    "DataIntegration",
    "DataIntegrationConfig",
    # Enums
    "IntegrationCategory",
    # Functions
    "get_data_integration_config",
    "get_integration",
    "get_integration_categories",
    "list_all_integrations",
    "reset_data_integration_config",
]

"""
Security iterations module for MyceliumFractalNet.

Provides configurable security iteration parameters for key derivation
and encryption operations. Implements 6 security iterations for enhanced
cryptographic key strengthening.

Security Iterations:
    1. BASE_ITERATIONS: Base PBKDF2 iteration count (100,000)
    2. ENHANCED_ITERATIONS: Enhanced security for sensitive data (150,000)
    3. HIGH_SECURITY_ITERATIONS: High security for critical operations (200,000)
    4. MAXIMUM_ITERATIONS: Maximum security for highly sensitive data (250,000)
    5. ADAPTIVE_ITERATIONS: Dynamically scaled based on data sensitivity (100,000-300,000)
    6. QUANTUM_RESISTANT_ITERATIONS: Future-proof iteration count (350,000)

Usage:
    >>> from mycelium_fractal_net.security.iterations import (
    ...     SecurityIterationConfig,
    ...     get_iteration_count,
    ...     SecurityLevel,
    ... )
    >>> config = SecurityIterationConfig()
    >>> count = get_iteration_count(SecurityLevel.HIGH)
    >>> # count = 200000

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SecurityLevel(str, Enum):
    """Security levels for iteration configuration."""

    BASE = "base"
    ENHANCED = "enhanced"
    HIGH = "high"
    MAXIMUM = "maximum"
    ADAPTIVE = "adaptive"
    QUANTUM_RESISTANT = "quantum_resistant"


# === Security Iteration Constants ===
# These 6 iteration levels provide progressive security strengthening

# Iteration 1: Base security (standard PBKDF2)
BASE_ITERATIONS: int = 100_000

# Iteration 2: Enhanced security for sensitive data
ENHANCED_ITERATIONS: int = 150_000

# Iteration 3: High security for critical operations
HIGH_SECURITY_ITERATIONS: int = 200_000

# Iteration 4: Maximum security for highly sensitive data
MAXIMUM_ITERATIONS: int = 250_000

# Iteration 5: Adaptive range (dynamically calculated)
ADAPTIVE_MIN_ITERATIONS: int = 100_000
ADAPTIVE_MAX_ITERATIONS: int = 300_000

# Iteration 6: Quantum-resistant future-proof iterations
QUANTUM_RESISTANT_ITERATIONS: int = 350_000


@dataclass
class SecurityIterationConfig:
    """
    Configuration for security iterations.

    Manages iteration counts for different security levels and
    provides validation for custom iteration settings.

    Attributes:
        base: Base iteration count for standard operations.
        enhanced: Enhanced iteration count for sensitive data.
        high: High security iteration count.
        maximum: Maximum security iteration count.
        adaptive_min: Minimum for adaptive iterations.
        adaptive_max: Maximum for adaptive iterations.
        quantum_resistant: Quantum-resistant iteration count.
        version: Configuration version for tracking.

    Example:
        >>> config = SecurityIterationConfig()
        >>> config.get_iterations(SecurityLevel.HIGH)
        200000
    """

    base: int = BASE_ITERATIONS
    enhanced: int = ENHANCED_ITERATIONS
    high: int = HIGH_SECURITY_ITERATIONS
    maximum: int = MAXIMUM_ITERATIONS
    adaptive_min: int = ADAPTIVE_MIN_ITERATIONS
    adaptive_max: int = ADAPTIVE_MAX_ITERATIONS
    quantum_resistant: int = QUANTUM_RESISTANT_ITERATIONS
    version: str = "1.0.0"
    _iteration_history: list[dict[str, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()
        self._record_iteration_state()

    def _validate(self) -> None:
        """
        Validate iteration configuration.

        Raises:
            ValueError: If any iteration count is invalid.
        """
        if self.base < 10_000:
            raise ValueError(f"Base iterations must be >= 10000, got {self.base}")
        if self.enhanced < self.base:
            raise ValueError(f"Enhanced iterations ({self.enhanced}) must be >= base ({self.base})")
        if self.high < self.enhanced:
            raise ValueError(f"High iterations ({self.high}) must be >= enhanced ({self.enhanced})")
        if self.maximum < self.high:
            raise ValueError(f"Maximum iterations ({self.maximum}) must be >= high ({self.high})")
        if self.adaptive_min < self.base:
            raise ValueError(f"Adaptive min ({self.adaptive_min}) must be >= base ({self.base})")
        if self.adaptive_max < self.adaptive_min:
            raise ValueError(
                f"Adaptive max ({self.adaptive_max}) must be >= adaptive min ({self.adaptive_min})"
            )
        if self.quantum_resistant < self.maximum:
            raise ValueError(
                f"Quantum resistant ({self.quantum_resistant}) must be >= maximum ({self.maximum})"
            )

    def _record_iteration_state(self) -> None:
        """Record current iteration state for audit trail."""
        self._iteration_history.append(
            {
                "base": self.base,
                "enhanced": self.enhanced,
                "high": self.high,
                "maximum": self.maximum,
                "quantum_resistant": self.quantum_resistant,
            }
        )

    def get_iterations(
        self,
        level: SecurityLevel,
        *,
        sensitivity_score: float | None = None,
    ) -> int:
        """
        Get iteration count for specified security level.

        Args:
            level: Security level to get iterations for.
            sensitivity_score: Optional sensitivity score in [0.0, 1.0] used
                when ``level`` is ``SecurityLevel.ADAPTIVE``. If omitted, the
                default midpoint (0.5) is used.

        Returns:
            int: Iteration count for the specified level.

        Example:
            >>> config = SecurityIterationConfig()
            >>> config.get_iterations(SecurityLevel.ENHANCED)
            150000
        """
        level_map = {
            SecurityLevel.BASE: self.base,
            SecurityLevel.ENHANCED: self.enhanced,
            SecurityLevel.HIGH: self.high,
            SecurityLevel.MAXIMUM: self.maximum,
            SecurityLevel.ADAPTIVE: self._compute_adaptive(
                sensitivity_score if sensitivity_score is not None else 0.5
            ),
            SecurityLevel.QUANTUM_RESISTANT: self.quantum_resistant,
        }
        return level_map[level]

    def _compute_adaptive(self, sensitivity_score: float = 0.5) -> int:
        """
        Compute adaptive iteration count based on sensitivity score.

        Args:
            sensitivity_score: Score from 0.0 (low) to 1.0 (high).

        Returns:
            int: Computed iteration count.
        """
        score = max(0.0, min(1.0, sensitivity_score))
        range_size = self.adaptive_max - self.adaptive_min
        return self.adaptive_min + int(range_size * score)

    def get_iteration_history(self) -> list[dict[str, int]]:
        """
        Get history of iteration configuration changes.

        Returns:
            List of iteration state dictionaries.
        """
        return list(self._iteration_history)

    def update_iterations(
        self,
        level: SecurityLevel,
        new_count: int,
    ) -> None:
        """
        Update iteration count for a specific level.

        Args:
            level: Security level to update.
            new_count: New iteration count.

        Raises:
            ValueError: If new count violates constraints.
        """
        if level == SecurityLevel.BASE:
            self.base = new_count
        elif level == SecurityLevel.ENHANCED:
            self.enhanced = new_count
        elif level == SecurityLevel.HIGH:
            self.high = new_count
        elif level == SecurityLevel.MAXIMUM:
            self.maximum = new_count
        elif level == SecurityLevel.QUANTUM_RESISTANT:
            self.quantum_resistant = new_count
        else:
            raise ValueError("Cannot update adaptive level directly")

        self._validate()
        self._record_iteration_state()

    def to_dict(self) -> dict[str, int | str]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        return {
            "version": self.version,
            "base": self.base,
            "enhanced": self.enhanced,
            "high": self.high,
            "maximum": self.maximum,
            "adaptive_min": self.adaptive_min,
            "adaptive_max": self.adaptive_max,
            "quantum_resistant": self.quantum_resistant,
        }


# Global configuration instance
_security_iteration_config: SecurityIterationConfig | None = None


def get_security_iteration_config() -> SecurityIterationConfig:
    """
    Get the global security iteration configuration.

    Returns:
        SecurityIterationConfig: Global configuration instance.
    """
    global _security_iteration_config
    if _security_iteration_config is None:
        _security_iteration_config = SecurityIterationConfig()
    return _security_iteration_config


def reset_security_iteration_config() -> None:
    """Reset the global security iteration configuration."""
    global _security_iteration_config
    _security_iteration_config = None


def get_iteration_count(
    level: SecurityLevel = SecurityLevel.BASE,
    *,
    sensitivity_score: float | None = None,
) -> int:
    """
    Get iteration count for specified security level.

    Convenience function using the global configuration.

    Args:
        level: Security level to get iterations for.
        sensitivity_score: Optional sensitivity score for adaptive level.

    Returns:
        int: Iteration count for the specified level.

    Example:
        >>> get_iteration_count(SecurityLevel.HIGH)
        200000
    """
    return get_security_iteration_config().get_iterations(
        level, sensitivity_score=sensitivity_score
    )


def validate_iteration_count(count: int, min_count: int = 10_000) -> bool:
    """
    Validate that an iteration count meets security requirements.

    Args:
        count: Iteration count to validate.
        min_count: Minimum required iterations.

    Returns:
        bool: True if count is valid.

    Example:
        >>> validate_iteration_count(100000)
        True
        >>> validate_iteration_count(5000)
        False
    """
    return count >= min_count


__all__ = [
    "ADAPTIVE_MAX_ITERATIONS",
    "ADAPTIVE_MIN_ITERATIONS",
    # Constants
    "BASE_ITERATIONS",
    "ENHANCED_ITERATIONS",
    "HIGH_SECURITY_ITERATIONS",
    "MAXIMUM_ITERATIONS",
    "QUANTUM_RESISTANT_ITERATIONS",
    # Classes
    "SecurityIterationConfig",
    # Enums
    "SecurityLevel",
    "get_iteration_count",
    # Functions
    "get_security_iteration_config",
    "reset_security_iteration_config",
    "validate_iteration_count",
]

"""
Tests for security iterations module.

Verifies the 6 security iteration levels for key derivation
and encryption operations.

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.security.iterations import (
    ADAPTIVE_MAX_ITERATIONS,
    ADAPTIVE_MIN_ITERATIONS,
    BASE_ITERATIONS,
    ENHANCED_ITERATIONS,
    HIGH_SECURITY_ITERATIONS,
    MAXIMUM_ITERATIONS,
    QUANTUM_RESISTANT_ITERATIONS,
    SecurityIterationConfig,
    SecurityLevel,
    get_iteration_count,
    get_security_iteration_config,
    reset_security_iteration_config,
    validate_iteration_count,
)


class TestSecurityIterationConstants:
    """Tests for security iteration constants."""

    def test_base_iterations_value(self) -> None:
        """Base iterations should be 100,000."""
        assert BASE_ITERATIONS == 100_000

    def test_enhanced_iterations_value(self) -> None:
        """Enhanced iterations should be 150,000."""
        assert ENHANCED_ITERATIONS == 150_000

    def test_high_security_iterations_value(self) -> None:
        """High security iterations should be 200,000."""
        assert HIGH_SECURITY_ITERATIONS == 200_000

    def test_maximum_iterations_value(self) -> None:
        """Maximum iterations should be 250,000."""
        assert MAXIMUM_ITERATIONS == 250_000

    def test_quantum_resistant_iterations_value(self) -> None:
        """Quantum resistant iterations should be 350,000."""
        assert QUANTUM_RESISTANT_ITERATIONS == 350_000

    def test_adaptive_range(self) -> None:
        """Adaptive range should be 100,000 to 300,000."""
        assert ADAPTIVE_MIN_ITERATIONS == 100_000
        assert ADAPTIVE_MAX_ITERATIONS == 300_000

    def test_iteration_ordering(self) -> None:
        """Iterations should be in ascending order."""
        assert BASE_ITERATIONS < ENHANCED_ITERATIONS
        assert ENHANCED_ITERATIONS < HIGH_SECURITY_ITERATIONS
        assert HIGH_SECURITY_ITERATIONS < MAXIMUM_ITERATIONS
        assert MAXIMUM_ITERATIONS < QUANTUM_RESISTANT_ITERATIONS

    def test_six_iteration_levels(self) -> None:
        """There should be exactly 6 security levels."""
        assert len(SecurityLevel) == 6


class TestSecurityLevel:
    """Tests for SecurityLevel enum."""

    def test_all_levels_defined(self) -> None:
        """All 6 security levels should be defined."""
        expected_levels = {
            "BASE",
            "ENHANCED",
            "HIGH",
            "MAXIMUM",
            "ADAPTIVE",
            "QUANTUM_RESISTANT",
        }
        actual_levels = {level.name for level in SecurityLevel}
        assert actual_levels == expected_levels

    def test_level_values(self) -> None:
        """Security levels should have correct string values."""
        assert SecurityLevel.BASE.value == "base"
        assert SecurityLevel.ENHANCED.value == "enhanced"
        assert SecurityLevel.HIGH.value == "high"
        assert SecurityLevel.MAXIMUM.value == "maximum"
        assert SecurityLevel.ADAPTIVE.value == "adaptive"
        assert SecurityLevel.QUANTUM_RESISTANT.value == "quantum_resistant"


class TestSecurityIterationConfig:
    """Tests for SecurityIterationConfig class."""

    def test_default_config(self) -> None:
        """Default config should use standard values."""
        config = SecurityIterationConfig()
        assert config.base == BASE_ITERATIONS
        assert config.enhanced == ENHANCED_ITERATIONS
        assert config.high == HIGH_SECURITY_ITERATIONS
        assert config.maximum == MAXIMUM_ITERATIONS
        assert config.quantum_resistant == QUANTUM_RESISTANT_ITERATIONS

    def test_get_iterations_base(self) -> None:
        """Should return correct iterations for base level."""
        config = SecurityIterationConfig()
        assert config.get_iterations(SecurityLevel.BASE) == BASE_ITERATIONS

    def test_get_iterations_enhanced(self) -> None:
        """Should return correct iterations for enhanced level."""
        config = SecurityIterationConfig()
        assert config.get_iterations(SecurityLevel.ENHANCED) == ENHANCED_ITERATIONS

    def test_get_iterations_high(self) -> None:
        """Should return correct iterations for high level."""
        config = SecurityIterationConfig()
        assert config.get_iterations(SecurityLevel.HIGH) == HIGH_SECURITY_ITERATIONS

    def test_get_iterations_maximum(self) -> None:
        """Should return correct iterations for maximum level."""
        config = SecurityIterationConfig()
        assert config.get_iterations(SecurityLevel.MAXIMUM) == MAXIMUM_ITERATIONS

    def test_get_iterations_quantum_resistant(self) -> None:
        """Should return correct iterations for quantum resistant level."""
        config = SecurityIterationConfig()
        assert (
            config.get_iterations(SecurityLevel.QUANTUM_RESISTANT) == QUANTUM_RESISTANT_ITERATIONS
        )

    def test_get_iterations_adaptive(self) -> None:
        """Should return adaptive iterations in valid range."""
        config = SecurityIterationConfig()
        adaptive = config.get_iterations(SecurityLevel.ADAPTIVE)
        assert ADAPTIVE_MIN_ITERATIONS <= adaptive <= ADAPTIVE_MAX_ITERATIONS

    def test_custom_config(self) -> None:
        """Should accept custom iteration values with valid constraints.

        Note: adaptive_min must be >= base per SecurityIterationConfig validation.
        """
        config = SecurityIterationConfig(
            base=120_000,
            enhanced=180_000,
            high=240_000,
            maximum=300_000,
            adaptive_min=120_000,
            adaptive_max=400_000,
            quantum_resistant=400_000,
        )
        assert config.base == 120_000
        assert config.enhanced == 180_000

    def test_validation_base_too_low(self) -> None:
        """Should reject base iterations below 10,000."""
        with pytest.raises(ValueError, match="Base iterations must be >= 10000"):
            SecurityIterationConfig(base=5_000)

    def test_validation_enhanced_below_base(self) -> None:
        """Should reject enhanced iterations below base."""
        with pytest.raises(ValueError, match="Enhanced iterations.*must be >= base"):
            SecurityIterationConfig(base=100_000, enhanced=50_000)

    def test_validation_high_below_enhanced(self) -> None:
        """Should reject high iterations below enhanced."""
        with pytest.raises(ValueError, match="High iterations.*must be >= enhanced"):
            SecurityIterationConfig(enhanced=150_000, high=100_000)

    def test_to_dict(self) -> None:
        """Should convert config to dictionary."""
        config = SecurityIterationConfig()
        data = config.to_dict()
        assert data["base"] == BASE_ITERATIONS
        assert data["enhanced"] == ENHANCED_ITERATIONS
        assert data["version"] == "1.0.0"

    def test_iteration_history(self) -> None:
        """Should track iteration configuration history."""
        config = SecurityIterationConfig()
        history = config.get_iteration_history()
        assert len(history) >= 1

    def test_update_iterations(self) -> None:
        """Should allow updating iteration counts."""
        config = SecurityIterationConfig()
        # Update enhanced to a higher value (base stays at default)
        config.update_iterations(SecurityLevel.ENHANCED, 160_000)
        assert config.enhanced == 160_000
        # Update high as well
        config.update_iterations(SecurityLevel.HIGH, 220_000)
        assert config.high == 220_000

    def test_adaptive_iterations_respect_sensitivity(self) -> None:
        """Adaptive iterations should scale with the provided sensitivity score."""
        config = SecurityIterationConfig(adaptive_min=120_000, adaptive_max=220_000)

        low = config.get_iterations(SecurityLevel.ADAPTIVE, sensitivity_score=0.0)
        mid = config.get_iterations(SecurityLevel.ADAPTIVE, sensitivity_score=0.5)
        high = config.get_iterations(SecurityLevel.ADAPTIVE, sensitivity_score=1.0)

        assert low == config.adaptive_min
        assert high == config.adaptive_max
        assert mid > low
        assert mid < high


class TestGetIterationCount:
    """Tests for get_iteration_count function."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_security_iteration_config()

    def test_default_level(self) -> None:
        """Default level should be BASE."""
        count = get_iteration_count()
        assert count == BASE_ITERATIONS

    def test_specific_level(self) -> None:
        """Should return correct count for specific levels."""
        assert get_iteration_count(SecurityLevel.BASE) == BASE_ITERATIONS
        assert get_iteration_count(SecurityLevel.ENHANCED) == ENHANCED_ITERATIONS
        assert get_iteration_count(SecurityLevel.HIGH) == HIGH_SECURITY_ITERATIONS
        assert get_iteration_count(SecurityLevel.MAXIMUM) == MAXIMUM_ITERATIONS
        assert get_iteration_count(SecurityLevel.QUANTUM_RESISTANT) == QUANTUM_RESISTANT_ITERATIONS

    def test_adaptive_level_respects_sensitivity(self) -> None:
        """Global helper should forward sensitivity to adaptive calculations."""
        config = get_security_iteration_config()
        config.adaptive_min = 90_000
        config.adaptive_max = 150_000

        low = get_iteration_count(SecurityLevel.ADAPTIVE, sensitivity_score=0.0)
        high = get_iteration_count(SecurityLevel.ADAPTIVE, sensitivity_score=1.0)

        assert low == config.adaptive_min
        assert high == config.adaptive_max


class TestValidateIterationCount:
    """Tests for validate_iteration_count function."""

    def test_valid_count(self) -> None:
        """Should return True for valid counts."""
        assert validate_iteration_count(100_000) is True
        assert validate_iteration_count(200_000) is True

    def test_invalid_count(self) -> None:
        """Should return False for counts below minimum."""
        assert validate_iteration_count(5_000) is False
        assert validate_iteration_count(9_999) is False

    def test_custom_minimum(self) -> None:
        """Should respect custom minimum."""
        assert validate_iteration_count(50_000, min_count=10_000) is True
        assert validate_iteration_count(50_000, min_count=100_000) is False


class TestGlobalConfig:
    """Tests for global configuration management."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_security_iteration_config()

    def test_get_security_iteration_config_singleton(self) -> None:
        """Should return same config instance."""
        config1 = get_security_iteration_config()
        config2 = get_security_iteration_config()
        assert config1 is config2

    def test_reset_creates_new_instance(self) -> None:
        """Reset should create new instance on next access."""
        config1 = get_security_iteration_config()
        reset_security_iteration_config()
        config2 = get_security_iteration_config()
        assert config1 is not config2

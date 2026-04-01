"""
Tests for data integrations module.

Verifies the 77 data integrations for iteration optimization.

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.integration.data_integrations import (
    CORE_ITERATION_INTEGRATIONS,
    ENCRYPTION_OPTIMIZATION_INTEGRATIONS,
    HASH_FUNCTION_INTEGRATIONS,
    INTEGRATION_COUNT,
    KEY_DERIVATION_INTEGRATIONS,
    MEMORY_OPTIMIZATION_INTEGRATIONS,
    PARALLELIZATION_INTEGRATIONS,
    SALT_GENERATION_INTEGRATIONS,
    VALIDATION_AUDIT_INTEGRATIONS,
    DataIntegration,
    DataIntegrationConfig,
    IntegrationCategory,
    get_data_integration_config,
    get_integration,
    get_integration_categories,
    list_all_integrations,
    reset_data_integration_config,
)


class TestIntegrationCount:
    """Tests for integration count constant."""

    def test_total_count(self) -> None:
        """Total integration count should be 77."""
        assert INTEGRATION_COUNT == 77

    def test_category_counts(self) -> None:
        """Integration categories should sum to 77."""
        total = (
            len(CORE_ITERATION_INTEGRATIONS)
            + len(KEY_DERIVATION_INTEGRATIONS)
            + len(ENCRYPTION_OPTIMIZATION_INTEGRATIONS)
            + len(HASH_FUNCTION_INTEGRATIONS)
            + len(SALT_GENERATION_INTEGRATIONS)
            + len(MEMORY_OPTIMIZATION_INTEGRATIONS)
            + len(PARALLELIZATION_INTEGRATIONS)
            + len(VALIDATION_AUDIT_INTEGRATIONS)
        )
        assert total == INTEGRATION_COUNT


class TestIntegrationCategory:
    """Tests for IntegrationCategory enum."""

    def test_all_categories_defined(self) -> None:
        """All 8 integration categories should be defined."""
        expected = {
            "CORE_ITERATION",
            "KEY_DERIVATION",
            "ENCRYPTION_OPTIMIZATION",
            "HASH_FUNCTION",
            "SALT_GENERATION",
            "MEMORY_OPTIMIZATION",
            "PARALLELIZATION",
            "VALIDATION_AUDIT",
        }
        actual = {cat.name for cat in IntegrationCategory}
        assert actual == expected


class TestCoreIterationIntegrations:
    """Tests for core iteration integrations (1-10)."""

    def test_integration_count(self) -> None:
        """Should have 10 core iteration integrations."""
        assert len(CORE_ITERATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 1-10."""
        assert set(CORE_ITERATION_INTEGRATIONS.keys()) == set(range(1, 11))

    def test_base_iteration_factor(self) -> None:
        """Integration 1 should be base_iteration_factor."""
        intg = CORE_ITERATION_INTEGRATIONS[1]
        assert intg["name"] == "base_iteration_factor"
        assert intg["value"] == 1.0


class TestKeyDerivationIntegrations:
    """Tests for key derivation integrations (11-20)."""

    def test_integration_count(self) -> None:
        """Should have 10 key derivation integrations."""
        assert len(KEY_DERIVATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 11-20."""
        assert set(KEY_DERIVATION_INTEGRATIONS.keys()) == set(range(11, 21))

    def test_kdf_algorithm(self) -> None:
        """Integration 11 should be kdf_algorithm."""
        intg = KEY_DERIVATION_INTEGRATIONS[11]
        assert intg["name"] == "kdf_algorithm"
        assert intg["value"] == "pbkdf2"


class TestEncryptionOptimizationIntegrations:
    """Tests for encryption optimization integrations (21-30)."""

    def test_integration_count(self) -> None:
        """Should have 10 encryption optimization integrations."""
        assert len(ENCRYPTION_OPTIMIZATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 21-30."""
        assert set(ENCRYPTION_OPTIMIZATION_INTEGRATIONS.keys()) == set(range(21, 31))


class TestHashFunctionIntegrations:
    """Tests for hash function integrations (31-40)."""

    def test_integration_count(self) -> None:
        """Should have 10 hash function integrations."""
        assert len(HASH_FUNCTION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 31-40."""
        assert set(HASH_FUNCTION_INTEGRATIONS.keys()) == set(range(31, 41))


class TestSaltGenerationIntegrations:
    """Tests for salt generation integrations (41-50)."""

    def test_integration_count(self) -> None:
        """Should have 10 salt generation integrations."""
        assert len(SALT_GENERATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 41-50."""
        assert set(SALT_GENERATION_INTEGRATIONS.keys()) == set(range(41, 51))


class TestMemoryOptimizationIntegrations:
    """Tests for memory optimization integrations (51-60)."""

    def test_integration_count(self) -> None:
        """Should have 10 memory optimization integrations."""
        assert len(MEMORY_OPTIMIZATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 51-60."""
        assert set(MEMORY_OPTIMIZATION_INTEGRATIONS.keys()) == set(range(51, 61))


class TestParallelizationIntegrations:
    """Tests for parallelization integrations (61-70)."""

    def test_integration_count(self) -> None:
        """Should have 10 parallelization integrations."""
        assert len(PARALLELIZATION_INTEGRATIONS) == 10

    def test_integration_ids(self) -> None:
        """Integration IDs should be 61-70."""
        assert set(PARALLELIZATION_INTEGRATIONS.keys()) == set(range(61, 71))


class TestValidationAuditIntegrations:
    """Tests for validation and audit integrations (71-77)."""

    def test_integration_count(self) -> None:
        """Should have 7 validation/audit integrations."""
        assert len(VALIDATION_AUDIT_INTEGRATIONS) == 7

    def test_integration_ids(self) -> None:
        """Integration IDs should be 71-77."""
        assert set(VALIDATION_AUDIT_INTEGRATIONS.keys()) == set(range(71, 78))


class TestDataIntegration:
    """Tests for DataIntegration class."""

    def test_creation(self) -> None:
        """Should create integration with required fields."""
        intg = DataIntegration(
            id=1,
            name="test",
            value=42,
            description="Test integration",
            category=IntegrationCategory.CORE_ITERATION,
        )
        assert intg.id == 1
        assert intg.name == "test"
        assert intg.value == 42
        assert intg.enabled is True

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        intg = DataIntegration(
            id=1,
            name="test",
            value=42,
            description="Test",
            category=IntegrationCategory.CORE_ITERATION,
        )
        data = intg.to_dict()
        assert data["id"] == 1
        assert data["name"] == "test"
        assert data["category"] == "core_iteration"


class TestDataIntegrationConfig:
    """Tests for DataIntegrationConfig class."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_data_integration_config()

    def test_loads_all_integrations(self) -> None:
        """Should load all 77 integrations."""
        _config = DataIntegrationConfig()  # Initialize config to ensure loading
        assert len(list_all_integrations()) == INTEGRATION_COUNT

    def test_get_integration(self) -> None:
        """Should get integration by ID."""
        config = DataIntegrationConfig()
        intg = config.get_integration(1)
        assert intg.id == 1
        assert intg.name == "base_iteration_factor"

    def test_get_integration_invalid_id(self) -> None:
        """Should raise for invalid ID."""
        config = DataIntegrationConfig()
        with pytest.raises(ValueError, match="Invalid integration ID"):
            config.get_integration(100)

    def test_get_integrations_by_category(self) -> None:
        """Should filter integrations by category."""
        config = DataIntegrationConfig()
        core = config.get_integrations_by_category(IntegrationCategory.CORE_ITERATION)
        assert len(core) == 10
        assert all(i.category == IntegrationCategory.CORE_ITERATION for i in core)

    def test_get_enabled_integrations(self) -> None:
        """Should return all enabled integrations."""
        config = DataIntegrationConfig()
        enabled = config.get_enabled_integrations()
        assert len(enabled) == INTEGRATION_COUNT

    def test_disable_integration(self) -> None:
        """Should disable specific integration."""
        config = DataIntegrationConfig()
        config.disable_integration(1)
        assert config.get_integration(1).enabled is False
        assert config.count_enabled() == INTEGRATION_COUNT - 1

    def test_enable_integration(self) -> None:
        """Should enable specific integration."""
        config = DataIntegrationConfig()
        config.disable_integration(1)
        config.enable_integration(1)
        assert config.get_integration(1).enabled is True

    def test_update_value(self) -> None:
        """Should update integration value."""
        config = DataIntegrationConfig()
        config.update_value(1, 2.0)
        assert config.get_integration(1).value == 2.0

    def test_change_history(self) -> None:
        """Should track configuration changes."""
        config = DataIntegrationConfig()
        config.update_value(1, 2.0)
        history = config.get_change_history()
        assert len(history) >= 1
        assert history[-1]["integration_id"] == 1

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        config = DataIntegrationConfig()
        data = config.to_dict()
        assert data["total_integrations"] == INTEGRATION_COUNT
        assert data["enabled_count"] == INTEGRATION_COUNT

    def test_optimization_summary(self) -> None:
        """Should provide optimization summary."""
        config = DataIntegrationConfig()
        summary = config.get_optimization_summary()
        assert summary["total"] == INTEGRATION_COUNT
        assert summary["enabled"] == INTEGRATION_COUNT
        assert summary["disabled"] == 0


class TestGetIntegration:
    """Tests for get_integration function."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_data_integration_config()

    def test_get_first_integration(self) -> None:
        """Should get first integration."""
        intg = get_integration(1)
        assert intg.id == 1
        assert intg.name == "base_iteration_factor"

    def test_get_last_integration(self) -> None:
        """Should get last integration."""
        intg = get_integration(77)
        assert intg.id == 77
        assert intg.name == "checksum_algorithm"


class TestListAllIntegrations:
    """Tests for list_all_integrations function."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_data_integration_config()

    def test_returns_77_integrations(self) -> None:
        """Should return all 77 integrations."""
        all_integrations = list_all_integrations()
        assert len(all_integrations) == INTEGRATION_COUNT

    def test_integrations_ordered(self) -> None:
        """Integrations should be ordered by ID."""
        all_integrations = list_all_integrations()
        ids = [i.id for i in all_integrations]
        assert ids == list(range(1, INTEGRATION_COUNT + 1))


class TestGetIntegrationCategories:
    """Tests for get_integration_categories function."""

    def test_returns_8_categories(self) -> None:
        """Should return 8 categories."""
        categories = get_integration_categories()
        assert len(categories) == 8

    def test_category_ranges(self) -> None:
        """Categories should cover IDs 1-77."""
        categories = get_integration_categories()
        all_ids = set()
        for _, start, end in categories:
            all_ids.update(range(start, end + 1))
        assert all_ids == set(range(1, INTEGRATION_COUNT + 1))


class TestGlobalConfig:
    """Tests for global configuration management."""

    def setup_method(self) -> None:
        """Reset config before each test."""
        reset_data_integration_config()

    def test_singleton(self) -> None:
        """Should return same config instance."""
        config1 = get_data_integration_config()
        config2 = get_data_integration_config()
        assert config1 is config2

    def test_reset(self) -> None:
        """Reset should create new instance on next access."""
        config1 = get_data_integration_config()
        reset_data_integration_config()
        config2 = get_data_integration_config()
        assert config1 is not config2

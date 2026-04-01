"""
Tests for Configuration Management.

Tests configuration loading, validation, and serialization.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.config import (
    CoreConfig,
    ExperimentConfig,
    create_deterministic_config,
    get_default_config,
    load_config,
    merge_configs,
    save_config,
    validate_config,
)


class TestCoreConfig:
    """Test CoreConfig dataclass."""

    def test_default_values(self) -> None:
        """CoreConfig has sensible defaults."""
        config = CoreConfig()

        assert config.n_neurons == 100
        assert config.dt == 0.1
        assert config.seed == 42
        assert config.n_layers == 4
        assert config.debug_mode is True

    def test_to_simulation_config(self) -> None:
        """CoreConfig converts to SimulationConfig."""
        config = CoreConfig(n_neurons=50, seed=123)
        sim_config = config.to_simulation_config()

        assert sim_config.n_neurons == 50
        assert sim_config.seed == 123
        assert sim_config.dt == config.dt

    def test_to_dict_and_from_dict(self) -> None:
        """CoreConfig round-trips through dict."""
        original = CoreConfig(n_neurons=200, theta_frequency=6.0)
        as_dict = original.to_dict()
        restored = CoreConfig.from_dict(as_dict)

        assert restored.n_neurons == 200
        assert restored.theta_frequency == 6.0

    def test_from_dict_ignores_unknown_fields(self) -> None:
        """from_dict ignores unknown fields."""
        data = {"n_neurons": 50, "unknown_field": "ignored"}
        config = CoreConfig.from_dict(data)

        assert config.n_neurons == 50
        assert not hasattr(config, "unknown_field")


class TestExperimentConfig:
    """Test ExperimentConfig dataclass."""

    def test_default_values(self) -> None:
        """ExperimentConfig has sensible defaults."""
        config = ExperimentConfig()

        assert config.name == "default"
        assert config.version == "1.0.0"
        assert config.core is not None
        assert isinstance(config.core, CoreConfig)

    def test_to_dict_and_from_dict(self) -> None:
        """ExperimentConfig round-trips through dict."""
        original = ExperimentConfig(
            name="test_experiment",
            description="Test description",
            core=CoreConfig(n_neurons=150),
        )
        as_dict = original.to_dict()
        restored = ExperimentConfig.from_dict(as_dict)

        assert restored.name == "test_experiment"
        assert restored.description == "Test description"
        assert restored.core.n_neurons == 150


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config_passes(self) -> None:
        """Valid configuration passes validation."""
        config = get_default_config()
        errors = validate_config(config)

        assert errors == []

    def test_negative_neurons_fails(self) -> None:
        """Negative n_neurons fails validation."""
        config = ExperimentConfig(core=CoreConfig(n_neurons=-10))
        errors = validate_config(config)

        assert any("n_neurons" in e for e in errors)

    def test_invalid_connection_probability_fails(self) -> None:
        """Invalid connection_probability fails validation."""
        config = ExperimentConfig(core=CoreConfig(connection_probability=1.5))
        errors = validate_config(config)

        assert any("connection_probability" in e for e in errors)

    def test_invalid_spectral_radius_fails(self) -> None:
        """Invalid spectral_radius_target fails validation."""
        config = ExperimentConfig(core=CoreConfig(spectral_radius_target=1.5))
        errors = validate_config(config)

        assert any("spectral_radius_target" in e for e in errors)

    def test_inverted_weight_bounds_fails(self) -> None:
        """weight_min >= weight_max fails validation."""
        config = ExperimentConfig(core=CoreConfig(weight_min=5.0, weight_max=1.0))
        errors = validate_config(config)

        assert any("weight_min" in e and "weight_max" in e for e in errors)


class TestConfigIO:
    """Test configuration I/O."""

    def test_save_and_load_json(self) -> None:
        """Config saves and loads from JSON."""
        config = ExperimentConfig(
            name="json_test",
            core=CoreConfig(n_neurons=75),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            save_config(config, path)

            loaded = load_config(path)

            assert loaded.name == "json_test"
            assert loaded.core.n_neurons == 75

    def test_save_and_load_yaml(self) -> None:
        """Config saves and loads from YAML."""
        pytest.importorskip("yaml")

        config = ExperimentConfig(
            name="yaml_test",
            core=CoreConfig(n_neurons=80),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.yaml"
            save_config(config, path)

            loaded = load_config(path)

            assert loaded.name == "yaml_test"
            assert loaded.core.n_neurons == 80

    def test_load_nonexistent_file_raises(self) -> None:
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_unsupported_format_raises(self) -> None:
        """Loading unsupported format raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:
            with pytest.raises(ValueError, match="Unsupported"):
                load_config(f.name)

    def test_load_base_yaml_config(self) -> None:
        """Load the actual base.yaml config file."""
        pytest.importorskip("yaml")

        base_path = Path(__file__).parent.parent / "configs" / "base.yaml"

        if base_path.exists():
            config = load_config(base_path)

            assert config.name == "default"
            assert config.core.seed == 42
            assert config.core.n_layers == 4


class TestConfigFactories:
    """Test configuration factory functions."""

    def test_get_default_config(self) -> None:
        """get_default_config returns valid config."""
        config = get_default_config()

        assert config.name == "default"
        errors = validate_config(config)
        assert errors == []

    def test_create_deterministic_config(self) -> None:
        """create_deterministic_config creates reproducible config."""
        config1 = create_deterministic_config(seed=42)
        config2 = create_deterministic_config(seed=42)

        assert config1.core.seed == config2.core.seed
        assert config1.core.debug_mode is True
        assert config1.core.guards_enabled is True

    def test_create_deterministic_config_custom_params(self) -> None:
        """create_deterministic_config accepts custom parameters."""
        config = create_deterministic_config(
            seed=123,
            n_neurons=200,
            duration_ms=5000.0,
        )

        assert config.core.seed == 123
        assert config.core.n_neurons == 200
        assert config.core.duration_ms == 5000.0


class TestConfigMerging:
    """Test configuration merging."""

    def test_merge_simple_override(self) -> None:
        """Simple override merges correctly."""
        base = get_default_config()
        override = {"name": "overridden"}

        merged = merge_configs(base, override)

        assert merged.name == "overridden"
        assert merged.core.n_neurons == base.core.n_neurons

    def test_merge_nested_override(self) -> None:
        """Nested override merges correctly."""
        base = get_default_config()
        override = {"core": {"n_neurons": 500}}

        merged = merge_configs(base, override)

        assert merged.core.n_neurons == 500
        assert merged.core.dt == base.core.dt  # Other values preserved

    def test_merge_preserves_base(self) -> None:
        """Merging doesn't modify the base config."""
        base = get_default_config()
        original_neurons = base.core.n_neurons

        merge_configs(base, {"core": {"n_neurons": 999}})

        assert base.core.n_neurons == original_neurons

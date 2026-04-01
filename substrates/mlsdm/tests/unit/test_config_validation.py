"""Tests for configuration schema validation.

Tests cover:
- Schema validation for all configuration parameters
- Range constraints and type checking
- Hierarchical constraints (decay rates, thresholds)
- Cross-field validation
- Error message clarity
"""

import pytest
from pydantic import ValidationError

from mlsdm.utils.config_schema import (
    CognitiveRhythmConfig,
    MoralFilterConfig,
    MultiLevelMemoryConfig,
    OntologyMatcherConfig,
    PELMConfig,
    SynergyExperienceConfig,
    SystemConfig,
    get_default_config,
    validate_config_dict,
)


class TestSystemConfig:
    """Tests for SystemConfig validation."""

    def test_default_config_is_valid(self):
        """Default configuration should be valid."""
        config = get_default_config()
        assert config.dimension == 384
        assert config.strict_mode is False

    def test_valid_dimension_range(self):
        """Test valid dimension values."""
        config = SystemConfig(dimension=384)
        assert config.dimension == 384

        # When changing dimension, must provide matching ontology vectors
        config = SystemConfig(
            dimension=2,
            ontology_matcher=OntologyMatcherConfig(ontology_vectors=[[1.0, 0.0], [0.0, 1.0]]),
        )
        assert config.dimension == 2

        # Test maximum dimension with matching ontology vectors
        large_vec = [1.0] + [0.0] * 4095
        config = SystemConfig(
            dimension=4096,
            ontology_matcher=OntologyMatcherConfig(ontology_vectors=[large_vec, large_vec]),
        )
        assert config.dimension == 4096

    def test_invalid_dimension_too_small(self):
        """Dimension below minimum should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(dimension=1)
        assert "greater than or equal to 2" in str(exc_info.value)

    def test_invalid_dimension_too_large(self):
        """Dimension above maximum should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(dimension=5000)
        assert "less than or equal to 4096" in str(exc_info.value)

    def test_invalid_dimension_type(self):
        """Non-integer dimension should raise error."""
        # Pydantic v2 coerces strings to ints, so test with truly invalid type
        with pytest.raises(ValidationError):
            SystemConfig(dimension="not-a-number")

    def test_strict_mode_boolean(self):
        """Strict mode should accept boolean values."""
        config = SystemConfig(strict_mode=True)
        assert config.strict_mode is True

        config = SystemConfig(strict_mode=False)
        assert config.strict_mode is False

    def test_unknown_fields_rejected(self):
        """Unknown configuration fields should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(unknown_field="value")
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_drift_logging_silent_mode(self):
        """Test drift_logging accepts 'silent' mode."""
        config = SystemConfig(drift_logging="silent")
        assert config.drift_logging == "silent"

    def test_drift_logging_verbose_mode(self):
        """Test drift_logging accepts 'verbose' mode."""
        config = SystemConfig(drift_logging="verbose")
        assert config.drift_logging == "verbose"

    def test_drift_logging_none_allowed(self):
        """Test drift_logging accepts None (default)."""
        config = SystemConfig(drift_logging=None)
        assert config.drift_logging is None

    def test_drift_logging_default_is_none(self):
        """Test drift_logging defaults to None when not specified."""
        config = SystemConfig()
        assert config.drift_logging is None

    def test_drift_logging_invalid_value_rejected(self):
        """Test drift_logging rejects invalid values with clear message."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(drift_logging="loud")
        error_msg = str(exc_info.value)
        assert "silent" in error_msg and "verbose" in error_msg

    def test_drift_logging_dict_validation(self):
        """Test drift_logging validation via validate_config_dict."""
        # Valid values should pass
        config_dict = {"drift_logging": "silent"}
        config = validate_config_dict(config_dict)
        assert config.drift_logging == "silent"

        config_dict = {"drift_logging": "verbose"}
        config = validate_config_dict(config_dict)
        assert config.drift_logging == "verbose"

        # Invalid value should fail
        with pytest.raises(ValueError) as exc_info:
            validate_config_dict({"drift_logging": "invalid"})
        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()


class TestMultiLevelMemoryConfig:
    """Tests for MultiLevelMemoryConfig validation."""

    def test_valid_decay_hierarchy(self):
        """Valid decay rate hierarchy should pass."""
        config = MultiLevelMemoryConfig(lambda_l1=0.5, lambda_l2=0.1, lambda_l3=0.01)
        assert config.lambda_l1 == 0.5
        assert config.lambda_l2 == 0.1
        assert config.lambda_l3 == 0.01

    def test_invalid_decay_hierarchy_l3_gt_l2(self):
        """lambda_l3 > lambda_l2 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            MultiLevelMemoryConfig(
                lambda_l1=0.5,
                lambda_l2=0.1,
                lambda_l3=0.2,  # Invalid: > lambda_l2
            )
        assert "Decay rates must follow hierarchy" in str(exc_info.value)

    def test_invalid_decay_hierarchy_l2_gt_l1(self):
        """lambda_l2 > lambda_l1 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            MultiLevelMemoryConfig(
                lambda_l1=0.1,
                lambda_l2=0.5,  # Invalid: > lambda_l1
                lambda_l3=0.01,
            )
        assert "Decay rates must follow hierarchy" in str(exc_info.value)

    def test_decay_rates_equal_allowed(self):
        """Equal decay rates should be allowed."""
        config = MultiLevelMemoryConfig(lambda_l1=0.5, lambda_l2=0.5, lambda_l3=0.5)
        assert config.lambda_l1 == config.lambda_l2 == config.lambda_l3

    def test_decay_rates_range_valid(self):
        """Decay rates within [0.0, 1.0] should pass."""
        # Must maintain hierarchy: l3 <= l2 <= l1
        config = MultiLevelMemoryConfig(lambda_l1=0.0, lambda_l2=0.0, lambda_l3=0.0)
        assert config.lambda_l1 == 0.0

        config = MultiLevelMemoryConfig(lambda_l1=1.0, lambda_l2=0.5, lambda_l3=0.1)
        assert config.lambda_l1 == 1.0

    def test_decay_rates_range_invalid(self):
        """Decay rates outside [0.0, 1.0] should fail."""
        with pytest.raises(ValidationError):
            MultiLevelMemoryConfig(lambda_l1=-0.1)

        with pytest.raises(ValidationError):
            MultiLevelMemoryConfig(lambda_l1=1.1)

    def test_valid_threshold_hierarchy(self):
        """theta_l2 > theta_l1 should pass."""
        config = MultiLevelMemoryConfig(theta_l1=1.0, theta_l2=2.0)
        assert config.theta_l1 == 1.0
        assert config.theta_l2 == 2.0

    def test_invalid_threshold_hierarchy(self):
        """theta_l2 <= theta_l1 should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            MultiLevelMemoryConfig(
                theta_l1=2.0,
                theta_l2=1.0,  # Invalid: <= theta_l1
            )
        assert "threshold hierarchy violated" in str(exc_info.value)

    def test_gating_factors_range(self):
        """Gating factors should be in [0.0, 1.0]."""
        config = MultiLevelMemoryConfig(gating12=0.0, gating23=1.0)
        assert config.gating12 == 0.0
        assert config.gating23 == 1.0

        with pytest.raises(ValidationError):
            MultiLevelMemoryConfig(gating12=-0.1)

        with pytest.raises(ValidationError):
            MultiLevelMemoryConfig(gating23=1.1)


class TestMoralFilterConfig:
    """Tests for MoralFilterConfig validation."""

    def test_valid_threshold_bounds(self):
        """Valid threshold configuration should pass."""
        config = MoralFilterConfig(threshold=0.5, min_threshold=0.3, max_threshold=0.9)
        assert config.threshold == 0.5
        assert config.min_threshold == 0.3
        assert config.max_threshold == 0.9

    def test_invalid_min_greater_than_max(self):
        """min_threshold >= max_threshold should fail."""
        with pytest.raises(ValidationError) as exc_info:
            MoralFilterConfig(min_threshold=0.9, max_threshold=0.3)
        assert "must be <" in str(exc_info.value)

    def test_invalid_threshold_below_min(self):
        """threshold < min_threshold should fail."""
        with pytest.raises(ValidationError) as exc_info:
            MoralFilterConfig(threshold=0.2, min_threshold=0.3)
        assert "must be >=" in str(exc_info.value)

    def test_invalid_threshold_above_max(self):
        """threshold > max_threshold should fail."""
        with pytest.raises(ValidationError) as exc_info:
            MoralFilterConfig(threshold=0.95, max_threshold=0.9)
        # Pydantic v2 uses "less than or equal" in error messages
        assert "less than or equal" in str(exc_info.value).lower()

    def test_threshold_range_constraints(self):
        """Thresholds should be in valid ranges."""
        with pytest.raises(ValidationError):
            MoralFilterConfig(threshold=0.05)  # Below 0.1

        with pytest.raises(ValidationError):
            MoralFilterConfig(threshold=0.95)  # Above 0.9

    def test_adapt_rate_range(self):
        """Adapt rate should be in [0.0, 0.5]."""
        config = MoralFilterConfig(adapt_rate=0.0)
        assert config.adapt_rate == 0.0

        config = MoralFilterConfig(adapt_rate=0.5)
        assert config.adapt_rate == 0.5

        with pytest.raises(ValidationError):
            MoralFilterConfig(adapt_rate=-0.1)

        with pytest.raises(ValidationError):
            MoralFilterConfig(adapt_rate=0.6)


class TestOntologyMatcherConfig:
    """Tests for OntologyMatcherConfig validation."""

    def test_valid_vectors_and_labels(self):
        """Valid ontology configuration should pass."""
        config = OntologyMatcherConfig(
            ontology_vectors=[[1.0, 0.0], [0.0, 1.0]], ontology_labels=["cat1", "cat2"]
        )
        assert len(config.ontology_vectors) == 2
        assert len(config.ontology_labels) == 2

    def test_vectors_same_dimension(self):
        """All vectors should have same dimension."""
        with pytest.raises(ValidationError) as exc_info:
            OntologyMatcherConfig(ontology_vectors=[[1.0, 0.0], [1.0, 0.0, 0.0]])
        assert "same dimension" in str(exc_info.value)

    def test_empty_vectors_rejected(self):
        """Empty ontology_vectors should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OntologyMatcherConfig(ontology_vectors=[])
        assert "cannot be empty" in str(exc_info.value)

    def test_labels_mismatch_count(self):
        """Number of labels must match vectors."""
        with pytest.raises(ValidationError) as exc_info:
            OntologyMatcherConfig(
                ontology_vectors=[[1.0, 0.0], [0.0, 1.0]],
                ontology_labels=["cat1"],  # Only 1 label for 2 vectors
            )
        assert "must match" in str(exc_info.value)

    def test_labels_optional(self):
        """Labels should be optional."""
        config = OntologyMatcherConfig(
            ontology_vectors=[[1.0, 0.0], [0.0, 1.0]], ontology_labels=None
        )
        assert config.ontology_labels is None


class TestCognitiveRhythmConfig:
    """Tests for CognitiveRhythmConfig validation."""

    def test_valid_durations(self):
        """Valid wake/sleep durations should pass."""
        config = CognitiveRhythmConfig(wake_duration=8, sleep_duration=3)
        assert config.wake_duration == 8
        assert config.sleep_duration == 3

    def test_duration_range_constraints(self):
        """Durations should be in [1, 100]."""
        config = CognitiveRhythmConfig(wake_duration=1)
        assert config.wake_duration == 1

        config = CognitiveRhythmConfig(sleep_duration=100)
        assert config.sleep_duration == 100

        with pytest.raises(ValidationError):
            CognitiveRhythmConfig(wake_duration=0)

        with pytest.raises(ValidationError):
            CognitiveRhythmConfig(sleep_duration=101)

    def test_unusual_ratio_warning(self, caplog):
        """Unusual wake/sleep ratios should trigger warning."""
        import logging

        caplog.set_level(logging.WARNING)

        # Ratio < 1.0 should trigger warning
        config = CognitiveRhythmConfig(wake_duration=2, sleep_duration=5)
        assert config.wake_duration == 2
        assert config.sleep_duration == 5
        assert "Unusual wake/sleep ratio detected" in caplog.text

        # Clear log and test ratio > 10.0
        caplog.clear()
        config = CognitiveRhythmConfig(wake_duration=50, sleep_duration=4)
        assert config.wake_duration == 50
        assert config.sleep_duration == 4
        assert "Unusual wake/sleep ratio detected" in caplog.text

        # Normal ratio should not trigger warning
        caplog.clear()
        config = CognitiveRhythmConfig(wake_duration=8, sleep_duration=3)
        assert "Unusual wake/sleep ratio detected" not in caplog.text


class TestCrossFieldValidation:
    """Tests for cross-field validation in SystemConfig."""

    def test_ontology_dimension_mismatch(self):
        """Ontology vector dimension must match system dimension."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(
                dimension=10,
                ontology_matcher=OntologyMatcherConfig(
                    ontology_vectors=[[1.0, 0.0], [0.0, 1.0]]  # dim=2, not 10
                ),
            )
        assert "must match system dimension" in str(exc_info.value)

    def test_ontology_dimension_match(self):
        """Matching ontology and system dimensions should pass."""
        config = SystemConfig(
            dimension=2,
            ontology_matcher=OntologyMatcherConfig(ontology_vectors=[[1.0, 0.0], [0.0, 1.0]]),
        )
        assert config.dimension == 2


class TestConfigLoaderIntegration:
    """Tests for validate_config_dict function."""

    def test_valid_dict(self):
        """Valid configuration dictionary should pass."""
        config_dict = {"dimension": 384, "moral_filter": {"threshold": 0.5}, "strict_mode": False}
        config = validate_config_dict(config_dict)
        assert config.dimension == 384

    def test_invalid_dict(self):
        """Invalid configuration dictionary should raise ValueError."""
        config_dict = {
            "dimension": -1  # Invalid
        }
        with pytest.raises(ValueError) as exc_info:
            validate_config_dict(config_dict)
        assert "Configuration validation failed" in str(exc_info.value)

    def test_empty_dict_uses_defaults(self):
        """Empty dictionary should use all defaults."""
        config = validate_config_dict({})
        assert config.dimension == 384  # Default
        assert config.strict_mode is False  # Default


class TestConfigSerialization:
    """Tests for configuration serialization/deserialization."""

    def test_model_dump(self):
        """Config should serialize to dictionary."""
        # Use default dimension to avoid ontology mismatch
        config = SystemConfig(dimension=384)
        data = config.model_dump()
        assert isinstance(data, dict)
        assert data["dimension"] == 384

    def test_model_dump_json(self):
        """Config should serialize to JSON."""
        config = SystemConfig(dimension=384)
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)
        assert "384" in json_str

    def test_round_trip(self):
        """Config should round-trip through dict."""
        config1 = SystemConfig(dimension=384, moral_filter=MoralFilterConfig(threshold=0.7))
        data = config1.model_dump()
        config2 = SystemConfig(**data)
        assert config2.dimension == config1.dimension
        assert config2.moral_filter.threshold == config1.moral_filter.threshold


class TestPELMConfig:
    """Tests for PELMConfig validation."""

    def test_default_values(self):
        """Test default PELM configuration."""
        config = PELMConfig()
        assert config.capacity == 20000
        assert config.phase_tolerance == 0.15

    def test_valid_capacity_range(self):
        """Test valid capacity values."""
        config = PELMConfig(capacity=100)
        assert config.capacity == 100

        config = PELMConfig(capacity=1000000)
        assert config.capacity == 1000000

    def test_invalid_capacity_too_small(self):
        """Test capacity below minimum."""
        with pytest.raises(ValidationError):
            PELMConfig(capacity=50)

    def test_invalid_capacity_too_large(self):
        """Test capacity above maximum."""
        with pytest.raises(ValidationError):
            PELMConfig(capacity=2000000)

    def test_valid_phase_tolerance(self):
        """Test valid phase tolerance values."""
        config = PELMConfig(phase_tolerance=0.0)
        assert config.phase_tolerance == 0.0

        config = PELMConfig(phase_tolerance=1.0)
        assert config.phase_tolerance == 1.0

    def test_invalid_phase_tolerance(self):
        """Test invalid phase tolerance values."""
        with pytest.raises(ValidationError):
            PELMConfig(phase_tolerance=-0.1)

        with pytest.raises(ValidationError):
            PELMConfig(phase_tolerance=1.5)

    def test_large_capacity_warning(self, caplog):
        """Test that large capacity triggers warning."""
        import logging

        caplog.set_level(logging.WARNING)

        config = PELMConfig(capacity=200000)
        assert config.capacity == 200000
        assert "Large PELM capacity configured" in caplog.text


class TestSynergyExperienceConfig:
    """Tests for SynergyExperienceConfig validation."""

    def test_default_values(self):
        """Test default synergy experience configuration."""
        config = SynergyExperienceConfig()
        assert config.epsilon == 0.1
        assert config.neutral_tolerance == 0.01
        assert config.min_trials_for_confidence == 3
        assert config.ema_alpha == 0.2

    def test_valid_epsilon_range(self):
        """Test valid epsilon values."""
        config = SynergyExperienceConfig(epsilon=0.0)
        assert config.epsilon == 0.0

        config = SynergyExperienceConfig(epsilon=1.0)
        assert config.epsilon == 1.0

    def test_invalid_epsilon(self):
        """Test invalid epsilon values."""
        with pytest.raises(ValidationError):
            SynergyExperienceConfig(epsilon=-0.1)

        with pytest.raises(ValidationError):
            SynergyExperienceConfig(epsilon=1.5)

    def test_valid_neutral_tolerance(self):
        """Test valid neutral tolerance values."""
        config = SynergyExperienceConfig(neutral_tolerance=0.0)
        assert config.neutral_tolerance == 0.0

        config = SynergyExperienceConfig(neutral_tolerance=0.5)
        assert config.neutral_tolerance == 0.5

    def test_invalid_neutral_tolerance(self):
        """Test invalid neutral tolerance values."""
        with pytest.raises(ValidationError):
            SynergyExperienceConfig(neutral_tolerance=-0.1)

        with pytest.raises(ValidationError):
            SynergyExperienceConfig(neutral_tolerance=0.6)

    def test_valid_min_trials(self):
        """Test valid min_trials_for_confidence values."""
        config = SynergyExperienceConfig(min_trials_for_confidence=1)
        assert config.min_trials_for_confidence == 1

        config = SynergyExperienceConfig(min_trials_for_confidence=100)
        assert config.min_trials_for_confidence == 100

    def test_invalid_min_trials(self):
        """Test invalid min_trials_for_confidence values."""
        with pytest.raises(ValidationError):
            SynergyExperienceConfig(min_trials_for_confidence=0)

        with pytest.raises(ValidationError):
            SynergyExperienceConfig(min_trials_for_confidence=101)

    def test_high_epsilon_warning(self, caplog):
        """Test that high epsilon triggers warning."""
        import logging

        caplog.set_level(logging.WARNING)

        config = SynergyExperienceConfig(epsilon=0.7)
        assert config.epsilon == 0.7
        assert "High exploration rate" in caplog.text

    def test_high_ema_alpha_warning(self, caplog):
        """Test that high EMA alpha triggers warning."""
        import logging

        caplog.set_level(logging.WARNING)

        config = SynergyExperienceConfig(ema_alpha=0.8)
        assert config.ema_alpha == 0.8
        assert "High EMA alpha" in caplog.text


class TestSystemConfigWithNewSections:
    """Tests for SystemConfig with PELM and SynergyExperience sections."""

    def test_default_includes_new_sections(self):
        """Test that default SystemConfig includes PELM and SynergyExperience."""
        config = get_default_config()
        assert hasattr(config, "pelm")
        assert hasattr(config, "synergy_experience")
        assert config.pelm.capacity == 20000
        assert config.synergy_experience.epsilon == 0.1

    def test_custom_pelm_config(self):
        """Test SystemConfig with custom PELM configuration."""
        config = SystemConfig(pelm=PELMConfig(capacity=50000, phase_tolerance=0.2))
        assert config.pelm.capacity == 50000
        assert config.pelm.phase_tolerance == 0.2

    def test_custom_synergy_experience_config(self):
        """Test SystemConfig with custom SynergyExperience configuration."""
        config = SystemConfig(
            synergy_experience=SynergyExperienceConfig(
                epsilon=0.2, neutral_tolerance=0.05, min_trials_for_confidence=5
            )
        )
        assert config.synergy_experience.epsilon == 0.2
        assert config.synergy_experience.neutral_tolerance == 0.05
        assert config.synergy_experience.min_trials_for_confidence == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

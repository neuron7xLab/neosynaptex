"""
Configuration Validator

Validates configuration parameters for MLSDM components to ensure they meet
requirements and fail fast with clear error messages.

Author: neuron7x
License: MIT
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationError(Exception):
    """Configuration validation error with context."""

    parameter: str
    value: Any
    expected: str
    component: str

    def __str__(self) -> str:
        return (
            f"Invalid configuration for {self.component}.{self.parameter}: "
            f"got {self.value!r}, expected {self.expected}"
        )


class ConfigValidator:
    """Validates configuration parameters for MLSDM components."""

    @staticmethod
    def validate_dimension(dim: Any, component: str = "Component") -> int:
        """Validate embedding dimension parameter.

        Args:
            dim: Dimension value to validate
            component: Component name for error messages

        Returns:
            Validated dimension as integer

        Raises:
            ValidationError: If dimension is invalid
        """
        if not isinstance(dim, int):
            raise ValidationError(
                parameter="dim", value=dim, expected="positive integer", component=component
            )

        if dim <= 0:
            raise ValidationError(
                parameter="dim", value=dim, expected="positive integer (> 0)", component=component
            )

        if dim > 10000:
            raise ValidationError(
                parameter="dim",
                value=dim,
                expected="reasonable integer (<= 10000)",
                component=component,
            )

        return dim

    @staticmethod
    def validate_capacity(capacity: Any, component: str = "Component") -> int:
        """Validate memory capacity parameter.

        Args:
            capacity: Capacity value to validate
            component: Component name for error messages

        Returns:
            Validated capacity as integer

        Raises:
            ValidationError: If capacity is invalid
        """
        if not isinstance(capacity, int):
            raise ValidationError(
                parameter="capacity",
                value=capacity,
                expected="positive integer",
                component=component,
            )

        if capacity <= 0:
            raise ValidationError(
                parameter="capacity",
                value=capacity,
                expected="positive integer (> 0)",
                component=component,
            )

        if capacity > 1_000_000:
            raise ValidationError(
                parameter="capacity",
                value=capacity,
                expected="reasonable integer (<= 1,000,000)",
                component=component,
            )

        return capacity

    @staticmethod
    def validate_threshold(
        threshold: Any, min_val: float = 0.0, max_val: float = 1.0, component: str = "Component"
    ) -> float:
        """Validate threshold parameter.

        Args:
            threshold: Threshold value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            component: Component name for error messages

        Returns:
            Validated threshold as float

        Raises:
            ValidationError: If threshold is invalid
        """
        if not isinstance(threshold, (int, float)):
            raise ValidationError(
                parameter="threshold",
                value=threshold,
                expected=f"float in range [{min_val}, {max_val}]",
                component=component,
            )

        threshold_float: float = float(threshold)

        if not (min_val <= threshold_float <= max_val):
            raise ValidationError(
                parameter="threshold",
                value=threshold_float,
                expected=f"float in range [{min_val}, {max_val}]",
                component=component,
            )

        return threshold_float

    @staticmethod
    def validate_duration(
        duration: Any, parameter_name: str = "duration", component: str = "Component"
    ) -> int:
        """Validate duration parameter (wake/sleep).

        Args:
            duration: Duration value to validate
            parameter_name: Parameter name for error messages
            component: Component name for error messages

        Returns:
            Validated duration as integer

        Raises:
            ValidationError: If duration is invalid
        """
        if not isinstance(duration, int):
            raise ValidationError(
                parameter=parameter_name,
                value=duration,
                expected="positive integer",
                component=component,
            )

        if duration <= 0:
            raise ValidationError(
                parameter=parameter_name,
                value=duration,
                expected="positive integer (> 0)",
                component=component,
            )

        if duration > 1000:
            raise ValidationError(
                parameter=parameter_name,
                value=duration,
                expected="reasonable integer (<= 1000)",
                component=component,
            )

        return duration

    @staticmethod
    def validate_rate(
        rate: Any, parameter_name: str = "rate", component: str = "Component"
    ) -> float:
        """Validate rate parameter (learning rate, decay rate, etc.).

        Args:
            rate: Rate value to validate
            parameter_name: Parameter name for error messages
            component: Component name for error messages

        Returns:
            Validated rate as float

        Raises:
            ValidationError: If rate is invalid
        """
        if not isinstance(rate, (int, float)):
            raise ValidationError(
                parameter=parameter_name,
                value=rate,
                expected="float in range (0, 1]",
                component=component,
            )

        rate_float: float = float(rate)

        if not (0 < rate_float <= 1.0):
            raise ValidationError(
                parameter=parameter_name,
                value=rate_float,
                expected="float in range (0, 1]",
                component=component,
            )

        return rate_float

    @staticmethod
    def validate_positive_int(
        value: Any, parameter_name: str, component: str = "Component", max_val: int | None = None
    ) -> int:
        """Validate positive integer parameter.

        Args:
            value: Value to validate
            parameter_name: Parameter name for error messages
            component: Component name for error messages
            max_val: Optional maximum value

        Returns:
            Validated value as integer

        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, int):
            expected = "positive integer"
            if max_val is not None:
                expected += f" (<= {max_val})"
            raise ValidationError(
                parameter=parameter_name, value=value, expected=expected, component=component
            )

        if value <= 0:
            expected = "positive integer (> 0)"
            if max_val is not None:
                expected += f" (<= {max_val})"
            raise ValidationError(
                parameter=parameter_name, value=value, expected=expected, component=component
            )

        if max_val is not None and value > max_val:
            raise ValidationError(
                parameter=parameter_name,
                value=value,
                expected=f"positive integer (<= {max_val})",
                component=component,
            )

        return value

    @staticmethod
    def validate_float_range(
        value: Any,
        parameter_name: str,
        min_val: float,
        max_val: float,
        component: str = "Component",
    ) -> float:
        """Validate float in specific range.

        Args:
            value: Value to validate
            parameter_name: Parameter name for error messages
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            component: Component name for error messages

        Returns:
            Validated value as float

        Raises:
            ValidationError: If value is invalid
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                parameter=parameter_name,
                value=value,
                expected=f"float in range [{min_val}, {max_val}]",
                component=component,
            )

        value_float: float = float(value)

        if not (min_val <= value_float <= max_val):
            raise ValidationError(
                parameter=parameter_name,
                value=value_float,
                expected=f"float in range [{min_val}, {max_val}]",
                component=component,
            )

        return value_float

    @classmethod
    def validate_llm_wrapper_config(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Validate LLMWrapper configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Validated configuration

        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {}
        component = "LLMWrapper"

        # Required parameters
        if "llm_generate_fn" not in config:
            raise ValidationError(
                parameter="llm_generate_fn",
                value=None,
                expected="callable function",
                component=component,
            )
        if not callable(config["llm_generate_fn"]):
            raise ValidationError(
                parameter="llm_generate_fn",
                value=config["llm_generate_fn"],
                expected="callable function",
                component=component,
            )
        validated["llm_generate_fn"] = config["llm_generate_fn"]

        if "embedding_fn" not in config:
            raise ValidationError(
                parameter="embedding_fn",
                value=None,
                expected="callable function",
                component=component,
            )
        if not callable(config["embedding_fn"]):
            raise ValidationError(
                parameter="embedding_fn",
                value=config["embedding_fn"],
                expected="callable function",
                component=component,
            )
        validated["embedding_fn"] = config["embedding_fn"]

        # Optional parameters with defaults
        validated["dim"] = cls.validate_dimension(config.get("dim", 384), component)

        validated["capacity"] = cls.validate_capacity(config.get("capacity", 20000), component)

        validated["wake_duration"] = cls.validate_duration(
            config.get("wake_duration", 8), "wake_duration", component
        )

        validated["sleep_duration"] = cls.validate_duration(
            config.get("sleep_duration", 3), "sleep_duration", component
        )

        validated["initial_moral_threshold"] = cls.validate_threshold(
            config.get("initial_moral_threshold", 0.50),
            min_val=0.30,
            max_val=0.90,
            component=component,
        )

        return validated

    @classmethod
    def validate_moral_filter_config(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Validate MoralFilter configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Validated configuration

        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {}
        component = "MoralFilter"

        validated["initial_threshold"] = cls.validate_threshold(
            config.get("initial_threshold", 0.50), min_val=0.30, max_val=0.90, component=component
        )

        validated["adapt_rate"] = cls.validate_rate(
            config.get("adapt_rate", 0.05), "adapt_rate", component
        )

        validated["ema_alpha"] = cls.validate_rate(
            config.get("ema_alpha", 0.1), "ema_alpha", component
        )

        return validated

    @classmethod
    def validate_qilm_config(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Validate QILM configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Validated configuration

        Raises:
            ValidationError: If any parameter is invalid
        """
        validated = {}
        component = "QILM"

        validated["dim"] = cls.validate_dimension(config.get("dim", 384), component)

        validated["capacity"] = cls.validate_capacity(config.get("capacity", 20000), component)

        return validated


def validate_config(config: dict[str, Any], component_type: str) -> dict[str, Any]:
    """Validate configuration for a component.

    Args:
        config: Configuration dictionary
        component_type: Type of component ("llm_wrapper", "moral_filter", "qilm")

    Returns:
        Validated configuration

    Raises:
        ValidationError: If configuration is invalid
        ValueError: If component_type is unknown
    """
    validators = {
        "llm_wrapper": ConfigValidator.validate_llm_wrapper_config,
        "moral_filter": ConfigValidator.validate_moral_filter_config,
        "qilm": ConfigValidator.validate_qilm_config,
    }

    if component_type not in validators:
        raise ValueError(
            f"Unknown component type: {component_type}. " f"Valid types: {list(validators.keys())}"
        )

    return validators[component_type](config)

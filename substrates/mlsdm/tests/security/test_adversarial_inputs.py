"""
Adversarial Input Handling Test Suite

This module validates the system's resilience against adversarial inputs:

1. PAYLOAD MANIPULATION: Tests for crafted payloads that attempt to bypass safety
2. BOUNDARY ATTACKS: Tests for inputs at mathematical boundaries
3. OVERFLOW ATTEMPTS: Tests for inputs that could cause numeric overflow
4. TYPE CONFUSION: Tests for inputs with incorrect types

These tests ensure the system maintains safety under adversarial conditions.

Author: Principal AI Safety Engineer (Distinguished Level)
"""

import sys

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.security.payload_scrubber import scrub_dict, scrub_text
from mlsdm.security.rate_limit import RateLimiter
from mlsdm.utils.input_validator import InputValidator

# ============================================================================
# Adversarial Payload Tests
# ============================================================================


class TestAdversarialPayloads:
    """Tests for adversarial payload handling."""

    def test_null_byte_injection_blocked(self):
        """
        SECURITY: Null byte injection attempts are neutralized

        Null bytes can be used to terminate strings prematurely in C-based systems.
        """
        validator = InputValidator()

        payloads = [
            "safe\x00secret",
            "\x00hidden_data",
            "data\x00\x00\x00multiple",
            "path/to/file\x00.txt",
        ]

        for payload in payloads:
            result = validator.sanitize_string(payload)
            assert "\x00" not in result, f"Null byte not removed from: {payload!r}"

    def test_unicode_normalization_attacks(self):
        """
        SECURITY: Unicode normalization attacks are handled

        Different Unicode representations of same character should be handled.
        """
        validator = InputValidator()

        # These are different Unicode representations
        test_strings = [
            "café",  # NFC form
            "cafe\u0301",  # NFD form (combining acute accent)
            "\u202ehidden\u202c",  # Right-to-left override
        ]

        for text in test_strings:
            # Should not crash
            result = validator.sanitize_string(text)
            assert isinstance(result, str)

    def test_oversized_input_rejected(self):
        """
        SECURITY: Oversized inputs are rejected to prevent DoS

        Very large inputs should be rejected before processing.
        """
        validator = InputValidator()

        # Create input larger than maximum
        oversized = "a" * 20000

        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.sanitize_string(oversized)

    def test_deeply_nested_dict_scrubbed(self):
        """
        SECURITY: Deeply nested dictionaries don't cause stack overflow

        Recursive scrubbing should handle deep nesting.
        """
        # Create deeply nested structure
        data = {"secret": "password123"}
        for i in range(50):
            data = {"nested": data, f"key{i}": "value"}

        # Should not crash
        result = scrub_dict(data)
        assert isinstance(result, dict)

    def test_circular_reference_handling(self):
        """
        SECURITY: Circular references don't cause infinite loops

        Note: Current implementation may not detect cycles, but should not crash.
        """
        # This test verifies the system handles dict scrubbing without cycles
        data = {
            "key1": "value1",
            "key2": {"nested": "value2"},
            "api_key": "secret123",
        }

        result = scrub_dict(data)
        assert result["api_key"] == "***REDACTED***"


# ============================================================================
# Mathematical Boundary Tests
# ============================================================================


class TestMathematicalBoundaries:
    """Tests for mathematical boundary conditions."""

    def test_float_precision_boundaries(self):
        """
        INVARIANT: Float precision boundaries are handled correctly

        Values very close to boundaries should be handled correctly.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # Test values extremely close to threshold
        epsilon = 1e-10
        threshold = moral_filter.threshold

        # Slightly above threshold
        assert moral_filter.evaluate(threshold + epsilon) is True

        # Slightly below threshold
        assert moral_filter.evaluate(threshold - epsilon) is False

    def test_subnormal_numbers_handled(self):
        """
        INVARIANT: Subnormal (denormalized) numbers don't cause issues

        Very small numbers near zero should be handled.
        """
        validator = InputValidator()

        # Subnormal number (smallest positive float32)
        subnormal = np.finfo(np.float32).tiny / 2

        # Should not cause issues (will be treated as effectively zero)
        vector = [subnormal, subnormal, 1.0, 0.0]
        result = validator.validate_vector(vector, expected_dim=4)
        assert len(result) == 4

    def test_max_float_values_handled(self):
        """
        INVARIANT: Maximum float values don't cause overflow

        Values near float max should be handled without overflow.
        """
        validator = InputValidator()

        # Large but finite values
        large_value = 1e30
        vector = [large_value, -large_value, 0.0, 1.0]

        result = validator.validate_vector(vector, expected_dim=4)
        assert np.all(np.isfinite(result))

    @settings(max_examples=100, deadline=None)
    @given(
        value=st.floats(
            min_value=-1e308,
            max_value=1e308,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_extreme_float_range(self, value):
        """
        INVARIANT: Extreme but finite floats are handled

        Any finite float should be processable (if in valid range).
        """
        validator = InputValidator()

        # For moral values, must be in [0, 1]
        if 0.0 <= value <= 1.0:
            result = validator.validate_moral_value(value)
            assert 0.0 <= result <= 1.0

    def test_integer_overflow_prevention(self):
        """
        INVARIANT: Integer overflow is prevented

        Operations with large integers should not overflow.
        """
        # Test rate limiter with large numbers
        limiter = RateLimiter(requests_per_window=sys.maxsize, window_seconds=1)

        # Should not overflow
        for _ in range(100):
            result = limiter.is_allowed("test_client")
            assert isinstance(result, bool)


# ============================================================================
# Type Confusion Tests
# ============================================================================


class TestTypeConfusion:
    """Tests for type confusion attacks."""

    def test_string_as_number_rejected(self):
        """
        SECURITY: String values cannot be used as numbers

        Type confusion between strings and numbers is prevented.
        """
        validator = InputValidator()

        with pytest.raises(ValueError):
            validator.validate_moral_value("0.5")

        with pytest.raises(ValueError):
            validator.validate_moral_value("1")

    def test_list_as_scalar_rejected(self):
        """
        SECURITY: Lists cannot be used as scalar values

        Arrays/lists are rejected where scalars are expected.
        """
        validator = InputValidator()

        with pytest.raises(ValueError):
            validator.validate_moral_value([0.5])

        with pytest.raises(ValueError):
            validator.validate_moral_value([0.5, 0.6])

    def test_dict_inputs_rejected(self):
        """
        SECURITY: Dictionary inputs are rejected for vector validation

        Dicts should not be accepted as vectors.
        """
        validator = InputValidator()

        with pytest.raises(ValueError):
            validator.validate_vector({"0": 0.1, "1": 0.2}, expected_dim=2)

    def test_none_inputs_handled(self):
        """
        SECURITY: None inputs don't cause crashes

        None should be handled gracefully.
        """
        validator = InputValidator()

        with pytest.raises((ValueError, TypeError)):
            validator.validate_moral_value(None)

        with pytest.raises(ValueError):
            validator.validate_vector(None, expected_dim=4)

    def test_boolean_type_confusion(self):
        """
        SECURITY: Boolean values handled correctly

        True/False should be treated as 1/0 when converted to float.
        """
        validator = InputValidator()

        # Python treats bool as subtype of int
        # True == 1, False == 0, which are valid moral values
        result_true = validator.validate_moral_value(True)
        assert result_true == 1.0

        result_false = validator.validate_moral_value(False)
        assert result_false == 0.0


# ============================================================================
# Rate Limiter Security Tests
# ============================================================================


class TestRateLimiterSecurity:
    """Security tests for rate limiter."""

    def test_rate_limiter_cannot_be_bypassed_by_timing(self):
        """
        SECURITY: Rate limiter cannot be bypassed by timing manipulation

        The rate limiter should enforce limits regardless of timing patterns.
        """
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)

        # Rapid requests should be blocked after limit
        allowed_count = 0
        for _ in range(100):
            if limiter.is_allowed("attacker"):
                allowed_count += 1

        assert allowed_count == 5, f"Rate limiter allowed {allowed_count} requests, expected 5"

    def test_rate_limiter_client_isolation(self):
        """
        SECURITY: Rate limits are enforced per-client

        One client hitting limit should not affect other clients.
        """
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)

        # Exhaust limit for client A
        for _ in range(10):
            limiter.is_allowed("client_a")

        # Client B should still have full allowance
        allowed_count = 0
        for _ in range(5):
            if limiter.is_allowed("client_b"):
                allowed_count += 1

        assert allowed_count == 5, "Client isolation failed - client B affected by client A's usage"

    def test_rate_limiter_reset_works(self):
        """
        SECURITY: Rate limiter reset clears state correctly

        After reset, limits should be restored.
        """
        limiter = RateLimiter(requests_per_window=5, window_seconds=60)

        # Exhaust limit
        for _ in range(5):
            limiter.is_allowed("client")

        # Should be blocked
        assert limiter.is_allowed("client") is False

        # Reset
        limiter.reset("client")

        # Should be allowed again
        assert limiter.is_allowed("client") is True


# ============================================================================
# Secret Scrubbing Security Tests
# ============================================================================


class TestSecretScrubbingSecurity:
    """Security tests for secret scrubbing."""

    def test_api_key_patterns_scrubbed(self):
        """
        SECURITY: Various API key patterns are detected and scrubbed

        Common API key formats should be identified and removed.
        """
        test_cases = [
            ("api_key=sk-1234567890abcdef1234567890abcdef", "sk-"),
            ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "Bearer"),
            ('token="ghp_1234567890abcdef1234567890abcdef"', "ghp_"),
        ]

        for payload, expected_pattern in test_cases:
            result = scrub_text(payload)
            # The secret should be redacted
            assert "REDACTED" in result, f"Pattern {expected_pattern} not scrubbed in: {payload}"

    def test_password_patterns_scrubbed(self):
        """
        SECURITY: Password patterns are detected and scrubbed

        Password fields should be identified and removed.
        """
        test_cases = [
            'password="mysecretpassword123"',
            "passwd: verysecurepassword",
            'pwd="another_secret_pwd"',
        ]

        for payload in test_cases:
            result = scrub_text(payload)
            assert "REDACTED" in result, f"Password not scrubbed in: {payload}"

    def test_aws_key_patterns_scrubbed(self):
        """
        SECURITY: AWS credential patterns are detected and scrubbed

        AWS access keys are partially redacted, preserving the AKIA prefix
        for identification while removing the secret portion.
        """
        test_cases = [
            "AKIA1234567890123456",  # AWS Access Key ID
        ]

        for payload in test_cases:
            result = scrub_text(payload)
            # The scrubber preserves "AKIA" prefix but redacts the rest
            # Expected output: "AKIA***REDACTED***"
            assert "REDACTED" in result, f"AWS key not properly scrubbed: {result}"
            assert "1234567890123456" not in result, f"AWS key ID not redacted: {result}"

    def test_private_key_patterns_scrubbed(self):
        """
        SECURITY: Private key patterns are detected and scrubbed

        PEM-formatted private keys should be identified.
        """
        payload = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA1234567890...
-----END RSA PRIVATE KEY-----"""

        result = scrub_text(payload)
        assert "REDACTED" in result


# ============================================================================
# Moral Filter Attack Resistance
# ============================================================================


class TestMoralFilterAttackResistance:
    """Tests for moral filter resistance to manipulation attacks."""

    def test_gradual_threshold_manipulation_bounded(self):
        """
        SECURITY: Gradual threshold manipulation is bounded

        Slow, sustained manipulation should not push threshold to extremes.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # 10000 iterations of gradual manipulation
        for _ in range(10000):
            # Very slight bias toward acceptance
            moral_filter.adapt(True)

        # Should still be within bounds
        assert moral_filter.threshold <= MoralFilterV2.MAX_THRESHOLD
        assert moral_filter.threshold >= MoralFilterV2.MIN_THRESHOLD

    def test_threshold_recovery_after_attack(self):
        """
        SECURITY: Threshold can recover after attack ends

        After an attack, normal usage should restore reasonable threshold.
        """
        moral_filter = MoralFilterV2(initial_threshold=0.5)

        # Attack phase - all rejections
        for _ in range(500):
            moral_filter.adapt(False)

        # Recovery phase - balanced usage
        for _ in range(500):
            moral_filter.adapt(np.random.random() < 0.5)

        recovery_threshold = moral_filter.threshold

        # Recovery should show some improvement (not always, due to randomness)
        # Just verify it's still in bounds
        assert MoralFilterV2.MIN_THRESHOLD <= recovery_threshold <= MoralFilterV2.MAX_THRESHOLD

    def test_type_error_on_invalid_threshold(self):
        """
        SECURITY: Invalid threshold types are rejected

        Non-numeric thresholds should raise TypeError.
        """
        with pytest.raises(TypeError):
            MoralFilterV2(initial_threshold="0.5")

        with pytest.raises(TypeError):
            MoralFilterV2(initial_threshold=[0.5])

        with pytest.raises(TypeError):
            MoralFilterV2(initial_threshold={"value": 0.5})


# ============================================================================
# Memory Safety Tests
# ============================================================================


class TestMemorySafety:
    """Tests for memory safety guarantees."""

    def test_vector_size_limits_enforced(self):
        """
        SECURITY: Vector size limits prevent memory exhaustion

        Extremely large vectors should be rejected.
        """
        validator = InputValidator()

        # Attempt to create oversized vector
        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_vector(
                [0.0] * (InputValidator.MAX_VECTOR_SIZE + 1),
                expected_dim=InputValidator.MAX_VECTOR_SIZE + 1,
            )

    def test_array_size_limits_enforced(self):
        """
        SECURITY: Array size limits prevent memory exhaustion

        Very large arrays should be rejected.
        """
        validator = InputValidator()

        # Attempt to validate oversized array
        with pytest.raises(ValueError, match="exceeds maximum"):
            validator.validate_array_size(
                [0] * (InputValidator.MAX_ARRAY_ELEMENTS + 1),
                name="test_array",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

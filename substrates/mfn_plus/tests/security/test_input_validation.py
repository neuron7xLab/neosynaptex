"""
Tests for input validation and sanitization.

Verifies protection against:
    - SQL injection attacks
    - XSS attacks
    - Input overflow
    - Invalid data formats

Reference: docs/MFN_SECURITY.md
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.security.input_validation import (
    InputValidator,
    ValidationError,
    detect_sql_injection,
    detect_xss,
    sanitize_string,
    validate_api_key_format,
    validate_numeric_range,
)


class TestSQLInjectionDetection:
    """Tests for SQL injection detection."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "SELECT * FROM users",
            "1; DROP TABLE users--",
            "' OR '1'='1",
            "admin'--",
            "1 UNION SELECT password FROM users",
            "INSERT INTO users VALUES ('hacked')",
            "DELETE FROM accounts WHERE id=1",
            "1 OR 1=1",
            "1 AND 1=1",
            "@@version",
            "/* comment */",
        ],
    )
    def test_detect_sql_injection_malicious(self, malicious_input: str) -> None:
        """Should detect SQL injection patterns."""
        assert detect_sql_injection(malicious_input) is True

    @pytest.mark.parametrize(
        "safe_input",
        [
            "normal user input",
            "my password is secret",
            "grid_size: 64",
            "Hello, World!",
            "2024-01-01",
            "127.0.0.1",
            "temperature_k: 310.0",
        ],
    )
    def test_detect_sql_injection_safe(self, safe_input: str) -> None:
        """Should not flag safe input."""
        assert detect_sql_injection(safe_input) is False


class TestXSSDetection:
    """Tests for XSS detection."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "<script>alert('xss')</script>",
            "<SCRIPT>document.cookie</SCRIPT>",
            "javascript:alert(1)",
            "<img onerror=alert(1) src=x>",
            "<iframe src='evil.com'>",
            "<div onclick=evil()>click</div>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert(1) autofocus>",
        ],
    )
    def test_detect_xss_malicious(self, malicious_input: str) -> None:
        """Should detect XSS patterns."""
        assert detect_xss(malicious_input) is True

    @pytest.mark.parametrize(
        "safe_input",
        [
            "normal text",
            "Hello <name>",  # Not a script tag
            "price is $100",
            "2 + 2 = 4",
            "https://example.com",
            "email@example.com",
        ],
    )
    def test_detect_xss_safe(self, safe_input: str) -> None:
        """Should not flag safe input."""
        assert detect_xss(safe_input) is False


class TestSanitizeString:
    """Tests for string sanitization."""

    def test_sanitize_html_entities(self) -> None:
        """Should encode HTML special characters."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_sanitize_strip_whitespace(self) -> None:
        """Should strip leading/trailing whitespace by default."""
        result = sanitize_string("  test  ")
        assert result == "test"

    def test_sanitize_max_length(self) -> None:
        """Should truncate to max_length."""
        long_string = "a" * 2000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100

    def test_sanitize_preserve_whitespace(self) -> None:
        """Should preserve whitespace when strip_whitespace=False."""
        result = sanitize_string("  test  ", strip_whitespace=False)
        assert result == "  test  "

    def test_sanitize_allow_html(self) -> None:
        """Should not encode HTML when allow_html=True."""
        result = sanitize_string("<b>bold</b>", allow_html=True)
        assert result == "<b>bold</b>"


class TestValidateNumericRange:
    """Tests for numeric range validation."""

    def test_validate_within_range(self) -> None:
        """Should pass for values within range."""
        assert validate_numeric_range(5, min_value=1, max_value=10) == 5

    def test_validate_at_boundaries(self) -> None:
        """Should pass for values at boundaries."""
        assert validate_numeric_range(1, min_value=1, max_value=10) == 1
        assert validate_numeric_range(10, min_value=1, max_value=10) == 10

    def test_validate_below_minimum(self) -> None:
        """Should raise for values below minimum."""
        with pytest.raises(ValidationError, match="must be >= 1"):
            validate_numeric_range(0, min_value=1, max_value=10)

    def test_validate_above_maximum(self) -> None:
        """Should raise for values above maximum."""
        with pytest.raises(ValidationError, match="must be <= 10"):
            validate_numeric_range(11, min_value=1, max_value=10)

    def test_validate_no_minimum(self) -> None:
        """Should work without minimum."""
        assert validate_numeric_range(-100, max_value=10) == -100

    def test_validate_no_maximum(self) -> None:
        """Should work without maximum."""
        assert validate_numeric_range(1000, min_value=1) == 1000

    def test_validate_float(self) -> None:
        """Should work with float values."""
        assert validate_numeric_range(5.5, min_value=1.0, max_value=10.0) == 5.5


class TestValidateAPIKeyFormat:
    """Tests for API key format validation."""

    @pytest.mark.parametrize(
        "valid_key",
        [
            "abcdefghij1234567890",  # 20 chars, minimum
            "api-key-valid-format-123",
            "API_KEY_VALID_FORMAT_123",
            "a" * 64,  # 64 chars, maximum
            "test-api-key-12345678901234",
        ],
    )
    def test_validate_valid_keys(self, valid_key: str) -> None:
        """Should accept valid API key formats."""
        assert validate_api_key_format(valid_key) is True

    @pytest.mark.parametrize(
        "invalid_key",
        [
            "short",  # Too short
            "a" * 19,  # Just under minimum
            "a" * 65,  # Just over maximum
            "key with spaces",
            "key@special#chars",
            "",
            "key\nwith\nnewlines",
        ],
    )
    def test_validate_invalid_keys(self, invalid_key: str) -> None:
        """Should reject invalid API key formats."""
        assert validate_api_key_format(invalid_key) is False


class TestInputValidator:
    """Tests for InputValidator class."""

    def test_validate_string_basic(self) -> None:
        """Should validate basic string."""
        validator = InputValidator()
        result = validator.validate_string("test input")
        assert result == "test input"

    def test_validate_string_empty(self) -> None:
        """Should reject empty string by default."""
        validator = InputValidator()
        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate_string("")

    def test_validate_string_empty_allowed(self) -> None:
        """Should allow empty string when configured."""
        validator = InputValidator()
        result = validator.validate_string("", allow_empty=True)
        assert result == ""

    def test_validate_string_sql_injection(self) -> None:
        """Should reject SQL injection in strict mode."""
        validator = InputValidator(strict_mode=True)
        with pytest.raises(ValidationError, match="dangerous SQL patterns"):
            validator.validate_string("SELECT * FROM users")

    def test_validate_string_xss(self) -> None:
        """Should reject XSS in strict mode."""
        validator = InputValidator(strict_mode=True)
        with pytest.raises(ValidationError, match="dangerous script patterns"):
            validator.validate_string("<script>alert('xss')</script>")

    def test_validate_string_max_length(self) -> None:
        """Should reject strings exceeding max length in strict mode."""
        validator = InputValidator(strict_mode=True, max_string_length=10)
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validator.validate_string("this is too long")

    def test_validate_string_sanitizes(self) -> None:
        """Should sanitize HTML entities."""
        validator = InputValidator(check_sql_injection=False, check_xss=False)
        result = validator.validate_string("<b>test</b>")
        assert "&lt;b&gt;" in result

    def test_validate_integer(self) -> None:
        """Should validate integer values."""
        validator = InputValidator()
        result = validator.validate_integer(5, min_value=1, max_value=10)
        assert result == 5

    def test_validate_float(self) -> None:
        """Should validate float values."""
        validator = InputValidator()
        result = validator.validate_float(5.5, min_value=1.0, max_value=10.0)
        assert result == 5.5

    def test_validate_api_key(self) -> None:
        """Should validate API key format."""
        validator = InputValidator()
        result = validator.validate_api_key("valid-api-key-1234567890")
        assert result == "valid-api-key-1234567890"

    def test_validate_api_key_invalid(self) -> None:
        """Should reject invalid API key format."""
        validator = InputValidator()
        with pytest.raises(ValidationError, match="invalid format"):
            validator.validate_api_key("short")

    def test_validate_request_body(self) -> None:
        """Should validate request body against schema."""
        validator = InputValidator()
        schema = {
            "name": {"type": "string", "max_length": 100},
            "count": {"type": "integer", "min_value": 1, "max_value": 100},
        }
        body = {"name": "test", "count": 50}

        result = validator.validate_request_body(body, schema)

        assert result["name"] == "test"
        assert result["count"] == 50

    def test_validate_request_body_missing_required(self) -> None:
        """Should reject missing required fields."""
        validator = InputValidator()
        schema = {
            "name": {"type": "string", "required": True},
        }
        body = {}

        with pytest.raises(ValidationError, match="is required"):
            validator.validate_request_body(body, schema)


class TestSecurityCompliance:
    """Integration tests for security compliance."""

    def test_owasp_injection_prevention(self) -> None:
        """Verify OWASP injection prevention recommendations."""
        validator = InputValidator(strict_mode=True)

        # OWASP A1: Injection
        injection_payloads = [
            "'; DROP TABLE users--",
            "1 OR 1=1",
            "<script>document.location='evil.com'</script>",
        ]

        for payload in injection_payloads:
            with pytest.raises(ValidationError):
                validator.validate_string(payload)

    def test_input_length_limits(self) -> None:
        """Verify input length limits are enforced."""
        validator = InputValidator(strict_mode=True, max_string_length=1000)

        # Large payload should be rejected
        large_payload = "x" * 10001

        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validator.validate_string(large_payload)

    def test_sanitization_removes_dangerous_content(self) -> None:
        """Verify dangerous content is neutralized."""
        result = sanitize_string("<script>alert('xss')</script>")

        # Script tags should be encoded
        assert "<script>" not in result
        assert "</script>" not in result

        # Content should be preserved but safe
        assert "alert" in result

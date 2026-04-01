"""
Comprehensive tests for security/payload_scrubber.py.

Tests cover:
- scrub_text function with various secret patterns
- scrub_dict function with nested structures
- should_log_payload function
- All secret pattern types
"""

import os

import pytest

from mlsdm.security.payload_scrubber import (
    is_secure_mode,
    scrub_dict,
    scrub_log_record,
    scrub_request_payload,
    scrub_text,
    should_log_payload,
)


class TestScrubText:
    """Tests for scrub_text function."""

    def test_scrub_empty_text(self):
        """Test scrubbing empty text returns empty."""
        assert scrub_text("") == ""
        assert scrub_text(None) is None

    def test_scrub_no_secrets(self):
        """Test text without secrets is unchanged."""
        text = "Hello, this is a normal message without secrets."
        assert scrub_text(text) == text

    def test_scrub_api_key_basic(self):
        """Test scrubbing basic API key patterns."""
        text = 'api_key="sk-abc123def456ghi789jkl012mno345"'
        result = scrub_text(text)
        assert "***REDACTED***" in result
        assert "abc123" not in result

    def test_scrub_sk_pattern(self):
        """Test scrubbing sk- prefixed keys (OpenAI style)."""
        text = "Using key sk-abcdefghijklmnopqrstuvwxyz123456"
        result = scrub_text(text)
        assert "sk-***REDACTED***" in result
        assert "abcdefghijk" not in result

    def test_scrub_bearer_token(self):
        """Test scrubbing Bearer tokens."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = scrub_text(text)
        assert "***REDACTED***" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_scrub_password_patterns(self):
        """Test scrubbing password patterns."""
        texts = [
            'password="mysecretpassword123"',
            "passwd: mysecretpassword123",
            'pwd="secretvalue123"',
        ]
        for text in texts:
            result = scrub_text(text)
            assert "***REDACTED***" in result

    def test_scrub_token_patterns(self):
        """Test scrubbing various token patterns."""
        texts = [
            'token="abcdefghijklmnopqrstuvwxyz"',
            'access_token: "abc123def456ghi789jkl"',
            'refresh_token="abc123def456ghi789jkl"',
        ]
        for text in texts:
            result = scrub_text(text)
            assert "***REDACTED***" in result

    def test_scrub_aws_keys(self):
        """Test scrubbing AWS keys."""
        # AWS Access Key ID pattern
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        result = scrub_text(text)
        assert "AKIA***REDACTED***" in result
        assert "IOSFODNN7EXAMPLE" not in result

    def test_scrub_aws_secret(self):
        """Test scrubbing AWS secret access key."""
        text = 'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        result = scrub_text(text)
        assert "***REDACTED***" in result

    def test_scrub_private_key(self):
        """Test scrubbing private key content."""
        text = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAhp7+/S7MWN3BtDgGXD2Xy4xC...
-----END RSA PRIVATE KEY-----"""
        result = scrub_text(text)
        assert "***REDACTED***" in result
        assert "MIIEowIBAAKCAQEAhp7" not in result

    def test_scrub_credit_card(self):
        """Test scrubbing credit card numbers."""
        texts = [
            "Card: 4111-1111-1111-1111",
            "Card: 4111 1111 1111 1111",
            "Card: 4111111111111111",
        ]
        for text in texts:
            result = scrub_text(text)
            assert "****-****-****-****" in result

    def test_scrub_multiple_secrets(self):
        """Test scrubbing multiple secrets in one text."""
        text = 'api_key="sk-secret123456789012345" password="mypassword12"'
        result = scrub_text(text)
        # The api_key pattern matches first, so the sk- prefix may be included in the redacted value
        assert "***REDACTED***" in result
        assert "secret123456789012345" not in result
        assert "mypassword12" not in result

    def test_scrub_preserves_non_secret_text(self):
        """Test that non-secret text is preserved."""
        text = "Hello world! api_key=sk-12345678901234567890 goodbye"
        result = scrub_text(text)
        assert "Hello world!" in result
        assert "goodbye" in result


class TestScrubDict:
    """Tests for scrub_dict function."""

    def test_scrub_dict_empty(self):
        """Test scrubbing empty dict."""
        assert scrub_dict({}) == {}

    def test_scrub_dict_no_secrets(self):
        """Test dict without secrets is preserved."""
        data = {"name": "John", "age": 30}
        result = scrub_dict(data)
        assert result == {"name": "John", "age": 30}

    def test_scrub_dict_known_keys(self):
        """Test scrubbing known secret keys."""
        data = {
            "api_key": "my-secret-key",
            "password": "my-password",
            "username": "john",
        }
        result = scrub_dict(data)
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["username"] == "john"

    def test_scrub_dict_nested(self):
        """Test scrubbing nested dictionaries."""
        data = {
            "config": {
                "api_key": "secret",
                "timeout": 30,
            }
        }
        result = scrub_dict(data)
        assert result["config"]["api_key"] == "***REDACTED***"
        assert result["config"]["timeout"] == 30

    def test_scrub_dict_list_values(self):
        """Test scrubbing lists in dictionaries."""
        data = {
            "tokens": ["token123", "token456"],
            "numbers": [1, 2, 3],
        }
        result = scrub_dict(data)
        # Lists are recursively scrubbed
        assert isinstance(result["tokens"], list)
        assert result["numbers"] == [1, 2, 3]

    def test_scrub_dict_string_patterns(self):
        """Test string values with patterns are scrubbed."""
        data = {
            "message": "My API key is sk-abcdefghijklmnopqrstuvwxyz",
        }
        result = scrub_dict(data)
        assert "sk-***REDACTED***" in result["message"]

    def test_scrub_dict_non_string_values(self):
        """Test non-string values are preserved."""
        data = {
            "count": 42,
            "active": True,
            "ratio": 3.14,
            "empty": None,
        }
        result = scrub_dict(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["ratio"] == 3.14
        assert result["empty"] is None

    def test_scrub_dict_custom_keys(self):
        """Test scrubbing with custom keys to scrub."""
        data = {
            "custom_secret": "secret-value",
            "public": "public-value",
        }
        custom_keys = {"custom_secret"}
        result = scrub_dict(data, keys_to_scrub=custom_keys)
        assert result["custom_secret"] == "***REDACTED***"
        assert result["public"] == "public-value"

    def test_scrub_dict_case_insensitive(self):
        """Test key matching is case insensitive."""
        data = {
            "API_KEY": "secret",
            "Password": "secret",
            "TOKEN": "secret",
        }
        result = scrub_dict(data)
        assert result["API_KEY"] == "***REDACTED***"
        assert result["Password"] == "***REDACTED***"
        assert result["TOKEN"] == "***REDACTED***"

    def test_scrub_dict_deeply_nested(self):
        """Test scrubbing deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "api_key": "deep-secret",
                    }
                }
            }
        }
        result = scrub_dict(data)
        assert result["level1"]["level2"]["level3"]["api_key"] == "***REDACTED***"

    def test_scrub_dict_original_unmodified(self):
        """Test that original dict is not modified."""
        data = {"api_key": "secret"}
        original = data.copy()
        scrub_dict(data)
        assert data == original


class TestShouldLogPayload:
    """Tests for should_log_payload function."""

    def test_should_log_payload_default(self):
        """Test default behavior (no env var) returns False."""
        # Clear the environment variable if set
        if "LOG_PAYLOADS" in os.environ:
            del os.environ["LOG_PAYLOADS"]
        assert should_log_payload() is False

    def test_should_log_payload_true(self):
        """Test LOG_PAYLOADS=true returns True."""
        os.environ["LOG_PAYLOADS"] = "true"
        try:
            assert should_log_payload() is True
        finally:
            del os.environ["LOG_PAYLOADS"]

    def test_should_log_payload_false(self):
        """Test LOG_PAYLOADS=false returns False."""
        os.environ["LOG_PAYLOADS"] = "false"
        try:
            assert should_log_payload() is False
        finally:
            del os.environ["LOG_PAYLOADS"]

    def test_should_log_payload_case_insensitive(self):
        """Test LOG_PAYLOADS is case insensitive."""
        for value in ["TRUE", "True", "TrUe"]:
            os.environ["LOG_PAYLOADS"] = value
            try:
                assert should_log_payload() is True
            finally:
                del os.environ["LOG_PAYLOADS"]

    def test_should_log_payload_other_values(self):
        """Test other values return False."""
        for value in ["yes", "1", "enabled", ""]:
            os.environ["LOG_PAYLOADS"] = value
            try:
                assert should_log_payload() is False
            finally:
                del os.environ["LOG_PAYLOADS"]


class TestSecretPatterns:
    """Tests for specific secret pattern coverage."""

    def test_openai_api_key_pattern(self):
        """Test OpenAI API key pattern."""
        # When key is referenced by name like openai_api_key, the key pattern matches first
        text = "openai_api_key: sk-proj-abcdefghijklmnop"
        result = scrub_text(text)
        assert "***REDACTED***" in result
        assert "abcdefghijklmnop" not in result

    def test_mixed_case_api_key(self):
        """Test mixed case API key labels."""
        texts = [
            'API_KEY: "secret12345678901234567890"',
            'Api-Key = "secret12345678901234567890"',
            'apiKey: "secret12345678901234567890"',
        ]
        for text in texts:
            result = scrub_text(text)
            assert "***REDACTED***" in result

    def test_json_format_secrets(self):
        """Test JSON format secrets."""
        text = '{"api_key": "sk-secret123456789012345", "model": "gpt-4"}'
        result = scrub_text(text)
        # The api_key pattern matches first in this JSON context
        assert "***REDACTED***" in result
        assert '"model": "gpt-4"' in result
        assert "sk-secret123456789012345" not in result

    def test_query_string_secrets(self):
        """Test query string format."""
        text = "?api_key=secret123456789012345&format=json"
        result = scrub_text(text)
        # API key should be redacted if it matches pattern
        assert "***REDACTED***" in result or "secret12345" not in result


class TestSecureScrubbingEntrypoints:
    """Tests for high-level scrubbing functions and secure mode flags."""

    def test_scrub_request_payload_scrubs_forbidden_and_nested(self):
        """Ensure request payload scrubs forbidden fields, PII, and nested secrets."""
        payload = {
            "prompt": "Sensitive prompt",
            "user_id": "user-123",
            "metadata": {"email": "user@example.com"},
            "items": [{"token": "abc123"}],
        }
        result = scrub_request_payload(payload)

        # Forbidden keys are redacted
        assert result["prompt"] == "***REDACTED***"
        assert result["user_id"] == "***REDACTED***"
        # Nested dict/list values are redacted
        assert result["metadata"] == "***REDACTED***"
        assert result["items"][0]["token"] == "***REDACTED***"
        # Original payload is not mutated
        assert payload["prompt"] == "Sensitive prompt"

    def test_scrub_log_record_scrubs_sensitive_fields(self):
        """Ensure log record scrubbing redacts forbidden identifiers."""
        record = {"message": "ok", "session_id": "sess-1", "details": {"token": "secret"}}
        scrubbed = scrub_log_record(record)

        assert scrubbed["message"] == "ok"
        assert scrubbed["session_id"] == "***REDACTED***"
        assert scrubbed["details"]["token"] == "***REDACTED***"

    def test_is_secure_mode_respects_env(self, monkeypatch):
        """Verify secure mode flag reads MLSDM_SECURE_MODE."""
        if "MLSDM_SECURE_MODE" in os.environ:
            del os.environ["MLSDM_SECURE_MODE"]
        assert is_secure_mode() is False

        monkeypatch.setenv("MLSDM_SECURE_MODE", "1")
        assert is_secure_mode() is True

        monkeypatch.setenv("MLSDM_SECURE_MODE", "true")
        assert is_secure_mode() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

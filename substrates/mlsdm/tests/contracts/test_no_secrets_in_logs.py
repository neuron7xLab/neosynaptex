"""
Contract tests for "no secrets in logs" security invariant.

This test suite validates that secrets, PII, and sensitive data
are never logged by the application, ensuring compliance with
SECURITY_POLICY.md requirements.

Security Invariants Tested:
- SEC-INV-001: Secrets (API keys, tokens, passwords) are never logged
- SEC-INV-002: PII (emails, user IDs, IP addresses) are never logged
- SEC-INV-003: Raw prompts/responses are never logged in secure mode
"""

from __future__ import annotations

import io
import json
import logging
import os

import pytest

from mlsdm.security.payload_scrubber import (
    DEFAULT_SECRET_KEYS,
    scrub_dict,
    scrub_log_record,
    scrub_request_payload,
    scrub_text,
)
from mlsdm.utils.security_logger import SecurityEventType, SecurityLogger


class TestNoSecretsInLogs:
    """Contract tests ensuring secrets are never logged."""

    @pytest.fixture
    def secret_payloads(self) -> list[dict]:
        """Sample payloads containing secrets - keys that are in DEFAULT_SECRET_KEYS."""
        return [
            {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyz"},
            {"password": "super_secret_password_123"},
            {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.xyz"},
            {"authorization": "Bearer token123456789012345678901234"},
            {"secret": "my_secret_value_that_should_not_appear"},
            {"openai_api_key": "sk-proj-1234567890abcdefghijklmnop"},
        ]

    @pytest.fixture
    def pii_payloads_for_scrub_request(self) -> list[dict]:
        """Sample payloads containing PII - scrubbed by scrub_request_payload."""
        return [
            {"email": "user@example.com"},
            {"user_id": "user_12345"},
            {"ip_address": "192.168.1.100"},
            {"client_ip": "10.0.0.1"},
            {"phone": "555-123-4567"},
            {"ssn": "123-45-6789"},
        ]

    def test_scrub_dict_removes_default_secret_keys(
        self, secret_payloads: list[dict]
    ) -> None:
        """Verify scrub_dict removes all values for DEFAULT_SECRET_KEYS."""
        for payload in secret_payloads:
            key = list(payload.keys())[0]
            # Only check if key is in DEFAULT_SECRET_KEYS
            if key.lower() in DEFAULT_SECRET_KEYS:
                result = scrub_dict(payload)
                result_value = list(result.values())[0]
                assert result_value == "***REDACTED***", (
                    f"Secret not scrubbed for key in DEFAULT_SECRET_KEYS: {key}"
                )

    def test_scrub_request_payload_removes_pii(
        self, pii_payloads_for_scrub_request: list[dict]
    ) -> None:
        """Verify scrub_request_payload removes all PII (uses secure mode scrubbing)."""
        for payload in pii_payloads_for_scrub_request:
            key = list(payload.keys())[0]
            result = scrub_request_payload(payload)
            result_value = list(result.values())[0]
            assert result_value == "***REDACTED***", (
                f"PII not scrubbed by scrub_request_payload: {key}"
            )

    def test_scrub_request_payload_removes_forbidden_fields(self) -> None:
        """Verify scrub_request_payload removes all forbidden fields."""
        payload = {
            "user_id": "user123",
            "prompt": "What is the meaning of life?",
            "raw_input": "sensitive data",
            "ip_address": "192.168.1.1",
            "session_id": "sess_abc123",
            "metadata": {"user_info": "sensitive"},
            # Safe field that should be preserved
            "model": "gpt-4",
        }

        result = scrub_request_payload(payload)

        # All forbidden fields should be redacted
        assert result["user_id"] == "***REDACTED***"
        assert result["prompt"] == "***REDACTED***"
        assert result["raw_input"] == "***REDACTED***"
        assert result["ip_address"] == "***REDACTED***"
        assert result["session_id"] == "***REDACTED***"
        assert result["metadata"] == "***REDACTED***"

        # Safe field should be preserved
        assert result["model"] == "gpt-4"

    def test_scrub_log_record_removes_sensitive_data(self) -> None:
        """Verify scrub_log_record removes all sensitive data."""
        record = {
            "message": "Processing request",
            "user_id": "user123",
            "ip": "10.0.0.1",
            "prompt": "Hello world",
            "api_key": "sk-secret123456789012345678",
            "level": "INFO",
        }

        result = scrub_log_record(record)

        # Sensitive fields should be redacted
        assert result["user_id"] == "***REDACTED***"
        assert result["ip"] == "***REDACTED***"
        assert result["prompt"] == "***REDACTED***"
        assert result["api_key"] == "***REDACTED***"

        # Non-sensitive fields should be preserved
        assert result["message"] == "Processing request"
        assert result["level"] == "INFO"

    def test_scrub_text_removes_embedded_secrets(self) -> None:
        """Verify scrub_text removes secrets embedded in text."""
        texts = [
            ("api_key=sk-secret123456789012345678", "sk-secret123456789012345678"),
            ('password: "super_secret_password"', "super_secret_password"),
            ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
            ("AKIAIOSFODNN7EXAMPLE", "IOSFODNN7EXAMPLE"),
        ]

        for text, secret_part in texts:
            result = scrub_text(text)
            assert secret_part not in result, (
                f"Secret not scrubbed from text: {secret_part}"
            )
            assert "***REDACTED***" in result

    def test_nested_secrets_are_scrubbed(self) -> None:
        """Verify deeply nested secrets are scrubbed."""
        payload = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret_token_12345678901234",
                },
                "body": {
                    "config": {
                        "api_key": "sk-nested-secret-123456789012",
                    }
                }
            }
        }

        result = scrub_dict(payload)

        assert result["request"]["headers"]["authorization"] == "***REDACTED***"
        assert result["request"]["body"]["config"]["api_key"] == "***REDACTED***"

    def test_list_of_secrets_are_scrubbed(self) -> None:
        """Verify lists containing secrets are scrubbed."""
        payload = {
            "api_keys": [
                {"api_key": "key1_secret123456789012"},
                {"api_key": "key2_secret123456789012"},
            ]
        }

        result = scrub_dict(payload)

        for item in result["api_keys"]:
            assert item["api_key"] == "***REDACTED***"

    def test_security_logger_does_not_log_pii(self) -> None:
        """Verify SecurityLogger filters out PII from additional_data."""
        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        security_logger = SecurityLogger()
        security_logger.logger.addHandler(handler)
        security_logger.logger.setLevel(logging.INFO)

        try:
            # Log an event with PII in additional_data
            security_logger._log_event(
                SecurityEventType.AUTH_SUCCESS,
                logging.INFO,
                "Test event",
                additional_data={
                    "email": "user@example.com",  # Should be filtered
                    "username": "testuser",  # Should be filtered
                    "password": "secret123",  # Should be filtered
                    "token": "abc123",  # Should be filtered
                    "safe_field": "preserved",
                },
            )

            # Get log output
            log_output = log_stream.getvalue()

            # Parse the JSON log
            log_data = json.loads(log_output.strip())

            # PII fields should not be present
            data = log_data.get("data", {})
            assert "email" not in data
            assert "username" not in data
            assert "password" not in data
            assert "token" not in data

            # Safe field should be present
            assert data.get("safe_field") == "preserved"

        finally:
            security_logger.logger.removeHandler(handler)


class TestSecretPatternsCompleteness:
    """Tests to ensure secret patterns cover common secret formats."""

    def test_openai_legacy_key_format_covered(self) -> None:
        """Verify legacy OpenAI API key format (sk-xxx) is detected and scrubbed."""
        key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        result = scrub_text(f"key: {key}")
        assert "1234567890abcdefghijklmnopqrstuvwxyz" not in result

    def test_aws_key_formats_covered(self) -> None:
        """Verify AWS key formats are detected and scrubbed."""
        # AWS Access Key ID
        access_key = "AKIAIOSFODNN7EXAMPLE"
        result = scrub_text(f"AWS Key: {access_key}")
        assert "IOSFODNN7EXAMPLE" not in result

        # AWS Secret Access Key
        secret_key = 'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        result = scrub_text(secret_key)
        assert "wJalrXUtnFEMI" not in result

    def test_jwt_tokens_covered(self) -> None:
        """Verify JWT tokens are detected and scrubbed."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = scrub_text(f"Bearer {jwt}")
        assert jwt not in result

    def test_private_keys_covered(self) -> None:
        """Verify private keys are detected and scrubbed."""
        private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7
-----END PRIVATE KEY-----"""
        result = scrub_text(private_key)
        assert "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7" not in result

    def test_credit_card_numbers_covered(self) -> None:
        """Verify credit card numbers are detected and scrubbed."""
        cards = [
            "4111-1111-1111-1111",
            "4111 1111 1111 1111",
            "4111111111111111",
        ]
        for card in cards:
            result = scrub_text(f"Card: {card}")
            assert card not in result


class TestSecureModeEnforcement:
    """Tests for secure mode behavior."""

    def test_secure_mode_env_var_detection(self) -> None:
        """Verify MLSDM_SECURE_MODE environment variable is respected."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        # Save original value using get() to avoid modifying during lookup
        orig_value = os.environ.get("MLSDM_SECURE_MODE")
        try:
            # Clear the env var for testing
            if "MLSDM_SECURE_MODE" in os.environ:
                del os.environ["MLSDM_SECURE_MODE"]

            assert is_secure_mode() is False

            os.environ["MLSDM_SECURE_MODE"] = "1"
            assert is_secure_mode() is True

            os.environ["MLSDM_SECURE_MODE"] = "true"
            assert is_secure_mode() is True

            os.environ["MLSDM_SECURE_MODE"] = "0"
            assert is_secure_mode() is False

        finally:
            # Restore original value
            if orig_value is not None:
                os.environ["MLSDM_SECURE_MODE"] = orig_value
            elif "MLSDM_SECURE_MODE" in os.environ:
                del os.environ["MLSDM_SECURE_MODE"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

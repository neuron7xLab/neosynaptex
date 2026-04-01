"""
Targeted security tests for payload_scrubber.

Tests focus on:
- PII (Personally Identifiable Information) scrubbing
- Token and credential scrubbing
- Raw LLM payload scrubbing
- Large/malformed payload handling
- Edge cases and robustness
- New scrub_request_payload and scrub_log_record functions
- Forbidden fields for secure mode
"""

import os

import pytest

from mlsdm.security.payload_scrubber import (
    EMAIL_PATTERN,
    PII_FIELDS,
    SECRET_PATTERNS,
    scrub_dict,
    scrub_log_record,
    scrub_request_payload,
    scrub_text,
    should_log_payload,
)


class TestPIIScrubbing:
    """Tests for PII (Personally Identifiable Information) scrubbing."""

    def test_email_in_text_preserved_by_default(self):
        """Test that email addresses are preserved by default (configurable)."""
        text = "Contact john.doe@example.com for support"
        result = scrub_text(text)
        # By default, emails are NOT scrubbed
        assert "john.doe@example.com" in result

    def test_email_scrubbed_when_enabled(self):
        """Test that email addresses are scrubbed when scrub_emails=True."""
        text = "Contact john.doe@example.com for support"
        result = scrub_text(text, scrub_emails=True)
        assert "john.doe@example.com" not in result
        assert "***@***.***" in result

    def test_multiple_emails_scrubbed(self):
        """Test that multiple email addresses are scrubbed."""
        text = "From: alice@company.com, To: bob@example.org"
        result = scrub_text(text, scrub_emails=True)
        assert "alice@company.com" not in result
        assert "bob@example.org" not in result
        assert result.count("***@***.***") == 2

    def test_email_pattern_matches_valid_emails(self):
        """Test that EMAIL_PATTERN matches various valid email formats."""
        valid_emails = [
            "simple@example.com",
            "user.name@example.com",
            "user+tag@example.org",
            "user123@sub.domain.co.uk",
        ]
        for email in valid_emails:
            assert EMAIL_PATTERN.search(email), f"Should match: {email}"

    def test_pii_fields_contain_expected_keys(self):
        """Test that PII_FIELDS contains expected field names."""
        expected_keys = {"email", "phone", "ssn", "address"}
        assert expected_keys.issubset(PII_FIELDS)

    def test_credit_card_scrubbed(self):
        """Test that credit card numbers are scrubbed."""
        cards = [
            "4111-1111-1111-1111",  # Visa test card
            "5500 0000 0000 0004",  # Mastercard test
            "4111111111111111",  # No separators
        ]
        for card in cards:
            text = f"Card number: {card}"
            result = scrub_text(text)
            assert "****-****-****-****" in result
            # Original digits should not be present
            assert card not in result

    def test_ip_addresses_preserved(self):
        """Test that IP addresses are preserved (not PII in security context)."""
        text = "Client IP: 192.168.1.100"
        result = scrub_text(text)
        # IPs are not scrubbed by current implementation
        assert "192.168.1.100" in result

    def test_ssn_like_patterns_not_scrubbed(self):
        """Test SSN patterns - not currently scrubbed."""
        # Note: SSN scrubbing could be added if needed
        text = "SSN: 123-45-6789"
        result = scrub_text(text)
        # Current implementation does not scrub SSN patterns
        assert "123-45-6789" in result

    def test_scrub_dict_with_pii_flag(self):
        """Test that scrub_dict with scrub_pii=True scrubs PII fields."""
        payload = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
            "name": "John Doe",
        }
        result = scrub_dict(payload, scrub_pii=True)
        assert result["email"] == "***REDACTED***"
        assert result["phone"] == "***REDACTED***"
        assert result["ssn"] == "***REDACTED***"
        assert result["name"] == "John Doe"  # Name is preserved

    def test_scrub_dict_pii_nested(self):
        """Test that scrub_dict with scrub_pii=True works on nested structures."""
        payload = {
            "user": {
                "email": "nested@example.com",
                "profile": {
                    "phone": "555-987-6543",
                },
            }
        }
        result = scrub_dict(payload, scrub_pii=True)
        assert result["user"]["email"] == "***REDACTED***"
        assert result["user"]["profile"]["phone"] == "***REDACTED***"

    def test_scrub_dict_with_email_in_text_field(self):
        """Test scrub_dict with scrub_emails=True scrubs emails in text values."""
        payload = {
            "message": "Contact us at support@company.com",
            "subject": "Hello",
        }
        result = scrub_dict(payload, scrub_emails=True)
        assert "support@company.com" not in result["message"]
        assert "***@***.***" in result["message"]
        assert result["subject"] == "Hello"


class TestTokenScrubbing:
    """Tests for API token and credential scrubbing."""

    def test_openai_key_formats(self):
        """Test various OpenAI API key formats are scrubbed."""
        keys = [
            "sk-1234567890abcdefghijklmnopqrstuvwxyz",  # Legacy format - matches sk- pattern
        ]
        for key in keys:
            result = scrub_text(f"Key: {key}")
            assert "***REDACTED***" in result
            # The actual key content should be removed
            assert "1234567890abcdefghijklmnopqrstuv" not in result

    def test_openai_key_with_api_key_label(self):
        """Test OpenAI key with api_key= label gets redacted via key pattern."""
        text = 'api_key="sk-proj-1234567890abcdefghij"'
        result = scrub_text(text)
        # The api_key pattern matches first, so whole value is redacted
        assert "***REDACTED***" in result
        assert "1234567890" not in result

    def test_jwt_token_scrubbed(self):
        """Test that JWT tokens are scrubbed."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        text = f"Authorization: Bearer {jwt}"
        result = scrub_text(text)
        assert "***REDACTED***" in result
        # JWT header should not be visible
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_aws_access_key_scrubbed(self):
        """Test that AWS access keys are scrubbed."""
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        text = f"AWS Key: {aws_key}"
        result = scrub_text(text)
        assert "AKIA***REDACTED***" in result
        assert "IOSFODNN7EXAMPLE" not in result

    def test_aws_secret_key_scrubbed(self):
        """Test that AWS secret keys are scrubbed."""
        text = 'aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        result = scrub_text(text)
        assert "***REDACTED***" in result
        assert "wJalrXUtnFEMI" not in result

    def test_generic_token_patterns(self):
        """Test that generic token patterns are scrubbed."""
        tokens = [
            'token="abcdef123456789012345678"',
            'access_token: "xyz123456789012345678abc"',
            'refresh_token="refresh_12345678901234567"',
        ]
        for token in tokens:
            result = scrub_text(token)
            assert "***REDACTED***" in result


class TestRawLLMPayloadScrubbing:
    """Tests for scrubbing raw LLM request/response payloads."""

    def test_openai_request_payload_scrubbed(self):
        """Test that OpenAI request payloads are scrubbed."""
        payload = {
            "model": "gpt-4",
            "api_key": "sk-secret123456789012345678901234",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        result = scrub_dict(payload)
        assert result["api_key"] == "***REDACTED***"
        assert result["model"] == "gpt-4"
        assert result["messages"] == [{"role": "user", "content": "Hello"}]

    def test_anthropic_request_payload_scrubbed(self):
        """Test that Anthropic request payloads are scrubbed."""
        payload = {
            "model": "claude-3",
            "api_key": "sk-ant-123456789012345678901234567",
            "messages": [{"role": "user", "content": "Test"}],
        }
        result = scrub_dict(payload)
        assert result["api_key"] == "***REDACTED***"

    def test_response_with_embedded_secrets(self):
        """Test LLM response containing embedded secrets."""
        response = {
            "response": "Here is the code: api_key = 'sk-secret123456789012345678'",
            "status": "success",
        }
        result = scrub_dict(response)
        # The api_key pattern should catch this and redact
        assert "***REDACTED***" in result["response"]
        # The actual secret value should not be present
        assert "secret12345678901234" not in result["response"]

    def test_headers_dict_scrubbed(self):
        """Test that HTTP headers are scrubbed."""
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "Content-Type": "application/json",
            "api_key": "secret-api-key-value123",
        }
        result = scrub_dict(headers)
        # Authorization is a known key to scrub
        assert result["Authorization"] == "***REDACTED***"
        assert result["Content-Type"] == "application/json"
        # api_key should be scrubbed by key name
        assert result["api_key"] == "***REDACTED***"


class TestSafeFieldsPreserved:
    """Tests that safe fields remain unchanged."""

    def test_normal_text_preserved(self):
        """Test that normal text without secrets is preserved."""
        text = "Hello, world! This is a normal message."
        assert scrub_text(text) == text

    def test_numeric_values_preserved(self):
        """Test that numeric values are preserved."""
        payload = {
            "count": 42,
            "rate": 3.14,
            "enabled": True,
        }
        result = scrub_dict(payload)
        assert result["count"] == 42
        assert result["rate"] == 3.14
        assert result["enabled"] is True

    def test_short_strings_preserved(self):
        """Test that short strings (likely not secrets) are preserved."""
        payload = {
            "status": "ok",
            "phase": "wake",
            "model": "gpt-4",
        }
        result = scrub_dict(payload)
        assert result["status"] == "ok"
        assert result["phase"] == "wake"
        assert result["model"] == "gpt-4"

    def test_prompt_content_preserved(self):
        """Test that prompt content without secrets is preserved."""
        payload = {
            "prompt": "What is the meaning of life?",
            "max_tokens": 100,
        }
        result = scrub_dict(payload)
        assert result["prompt"] == "What is the meaning of life?"

    def test_response_text_preserved(self):
        """Test that response text without secrets is preserved."""
        text = "NEURO-RESPONSE: The meaning of life is 42."
        assert scrub_text(text) == text


class TestLargePayloadHandling:
    """Tests for handling large or unusual payloads."""

    def test_large_text_scrubbed(self):
        """Test that large text is handled without crashing."""
        # 1MB of text with embedded secret
        large_text = "a" * 500_000 + " api_key=sk-secret123456789012345678 " + "b" * 500_000
        result = scrub_text(large_text)
        # The api_key pattern should match and redact
        assert "***REDACTED***" in result
        assert "secret12345678901234" not in result

    def test_deeply_nested_dict_scrubbed(self):
        """Test that deeply nested dicts are handled."""
        payload = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "api_key": "secret-value",
                        }
                    }
                }
            }
        }
        result = scrub_dict(payload)
        assert result["level1"]["level2"]["level3"]["level4"]["api_key"] == "***REDACTED***"

    def test_list_with_many_items(self):
        """Test list with many items is handled."""
        payload = {
            "items": [{"api_key": f"key-{i}"} for i in range(100)],
        }
        result = scrub_dict(payload)
        # All api_key values should be redacted
        for item in result["items"]:
            assert item["api_key"] == "***REDACTED***"

    def test_mixed_types_in_list(self):
        """Test mixed types in lists are handled."""
        payload = {
            "mixed": [
                "string value",
                42,
                {"api_key": "secret"},
                ["nested", "list"],
                None,
                True,
            ]
        }
        result = scrub_dict(payload)
        assert result["mixed"][0] == "string value"
        assert result["mixed"][1] == 42
        assert result["mixed"][2]["api_key"] == "***REDACTED***"
        assert result["mixed"][4] is None

    def test_unicode_text_handled(self):
        """Test that unicode text is handled correctly."""
        text = "日本語のテキスト api_key=sk-secret123456789012345 более текста"
        result = scrub_text(text)
        assert "日本語のテキスト" in result
        # api_key pattern should catch this
        assert "***REDACTED***" in result
        assert "более текста" in result
        # The secret value should be gone
        assert "secret123456789012345" not in result

    def test_newlines_and_special_chars(self):
        """Test text with newlines and special characters."""
        text = "Line 1\napi_key=sk-secret123456789012345\nLine 3\t\ttabbed"
        result = scrub_text(text)
        # api_key pattern should match
        assert "***REDACTED***" in result
        assert "Line 1" in result
        assert "Line 3" in result
        # The secret should be gone
        assert "secret123456789012345" not in result


class TestMalformedInputHandling:
    """Tests for handling malformed inputs."""

    def test_none_input_to_scrub_text(self):
        """Test that None input returns None."""
        result = scrub_text(None)  # type: ignore
        assert result is None

    def test_empty_string(self):
        """Test that empty string returns empty string."""
        assert scrub_text("") == ""

    def test_empty_dict(self):
        """Test that empty dict returns empty dict."""
        assert scrub_dict({}) == {}

    def test_dict_with_none_values(self):
        """Test dict with None values."""
        payload = {
            "present": "value",
            "absent": None,
        }
        result = scrub_dict(payload)
        assert result["present"] == "value"
        assert result["absent"] is None


class TestScrubDictOriginalUnmodified:
    """Test that original dict is not modified by scrubbing."""

    def test_original_dict_unchanged(self):
        """Test that original dict is not mutated."""
        original = {"api_key": "secret123456789012345678"}
        original_copy = original.copy()

        scrub_dict(original)

        # Original should be unchanged
        assert original == original_copy
        assert original["api_key"] == "secret123456789012345678"

    def test_nested_original_unchanged(self):
        """Test that nested original dict is not mutated."""
        original = {"config": {"api_key": "secret"}}
        inner_original = original["config"]["api_key"]

        scrub_dict(original)

        assert original["config"]["api_key"] == inner_original


class TestSecretPatternCoverage:
    """Test that all defined secret patterns are covered."""

    def test_all_patterns_are_tuples(self):
        """Test that SECRET_PATTERNS are properly formatted."""
        for pattern, replacement in SECRET_PATTERNS:
            assert hasattr(pattern, "sub"), "Pattern should be a compiled regex"
            assert isinstance(replacement, str), "Replacement should be a string"

    def test_pattern_count(self):
        """Test that we have a reasonable number of patterns."""
        # Sanity check - should have at least 10 patterns
        assert len(SECRET_PATTERNS) >= 10


class TestEnvironmentVariableScrubbing:
    """Test LOG_PAYLOADS environment variable behavior."""

    def test_log_payloads_default_false(self):
        """Test that LOG_PAYLOADS defaults to false."""
        if "LOG_PAYLOADS" in os.environ:
            del os.environ["LOG_PAYLOADS"]
        assert should_log_payload() is False

    def test_log_payloads_true(self):
        """Test LOG_PAYLOADS=true enables logging."""
        os.environ["LOG_PAYLOADS"] = "true"
        try:
            assert should_log_payload() is True
        finally:
            del os.environ["LOG_PAYLOADS"]

    def test_log_payloads_case_insensitive(self):
        """Test LOG_PAYLOADS is case insensitive."""
        for value in ["TRUE", "True", "TrUe", "true"]:
            os.environ["LOG_PAYLOADS"] = value
            try:
                assert should_log_payload() is True
            finally:
                del os.environ["LOG_PAYLOADS"]

    def test_log_payloads_other_values_false(self):
        """Test that non-'true' values return false."""
        for value in ["yes", "1", "on", "enabled", ""]:
            os.environ["LOG_PAYLOADS"] = value
            try:
                assert should_log_payload() is False
            finally:
                del os.environ["LOG_PAYLOADS"]


class TestScrubRequestPayload:
    """Tests for scrub_request_payload function."""

    def test_scrubs_user_id(self):
        """Test that user_id is scrubbed."""
        payload = {"user_id": "user123", "message": "hello"}
        result = scrub_request_payload(payload)
        assert result["user_id"] == "***REDACTED***"
        assert result["message"] == "hello"

    def test_scrubs_prompt_field(self):
        """Test that prompt field is scrubbed."""
        payload = {"prompt": "What is the meaning of life?", "max_tokens": 100}
        result = scrub_request_payload(payload)
        assert result["prompt"] == "***REDACTED***"
        assert result["max_tokens"] == 100

    def test_scrubs_raw_input(self):
        """Test that raw_input is scrubbed."""
        payload = {"raw_input": "sensitive data", "model": "gpt-4"}
        result = scrub_request_payload(payload)
        assert result["raw_input"] == "***REDACTED***"
        assert result["model"] == "gpt-4"

    def test_scrubs_ip_address(self):
        """Test that ip_address is scrubbed."""
        payload = {"ip_address": "192.168.1.1", "request_id": "abc123"}
        result = scrub_request_payload(payload)
        assert result["ip_address"] == "***REDACTED***"
        assert result["request_id"] == "abc123"

    def test_scrubs_nested_forbidden_fields(self):
        """Test that nested forbidden fields are scrubbed."""
        payload = {
            "user": {"user_id": "user123", "email": "test@example.com"},
            "request": {"prompt": "sensitive prompt"},
        }
        result = scrub_request_payload(payload)
        assert result["user"]["user_id"] == "***REDACTED***"
        assert result["user"]["email"] == "***REDACTED***"
        assert result["request"]["prompt"] == "***REDACTED***"

    def test_scrubs_full_prompt_and_full_response(self):
        """Test that full_prompt and full_response are scrubbed."""
        payload = {"full_prompt": "What is AI?", "full_response": "AI is artificial intelligence."}
        result = scrub_request_payload(payload)
        assert result["full_prompt"] == "***REDACTED***"
        assert result["full_response"] == "***REDACTED***"

    def test_case_insensitive_scrubbing(self):
        """Test that scrubbing is case-insensitive."""
        payload = {"User_ID": "user123", "USER_ID": "user456", "IP_ADDRESS": "192.168.1.1"}
        result = scrub_request_payload(payload)
        assert result["User_ID"] == "***REDACTED***"
        assert result["USER_ID"] == "***REDACTED***"
        assert result["IP_ADDRESS"] == "***REDACTED***"

    def test_preserves_safe_fields(self):
        """Test that safe fields are preserved."""
        payload = {"model": "gpt-4", "max_tokens": 100, "temperature": 0.7, "status": "success"}
        result = scrub_request_payload(payload)
        assert result == payload

    def test_never_raises_exceptions(self):
        """Test that scrub_request_payload never raises exceptions."""
        # Test with malformed data - should return empty dict
        assert scrub_request_payload({}) == {}
        # None values in dict should be preserved
        assert scrub_request_payload({"key": None})["key"] is None


class TestScrubLogRecord:
    """Tests for scrub_log_record function."""

    def test_scrubs_user_id_in_log(self):
        """Test that user_id is scrubbed from log records."""
        record = {"message": "User logged in", "user_id": "user123"}
        result = scrub_log_record(record)
        assert result["user_id"] == "***REDACTED***"
        assert result["message"] == "User logged in"

    def test_scrubs_raw_text_in_log(self):
        """Test that raw_text is scrubbed from log records."""
        record = {"message": "Processing", "raw_text": "sensitive content"}
        result = scrub_log_record(record)
        assert result["raw_text"] == "***REDACTED***"

    def test_scrubs_ip_in_log(self):
        """Test that ip is scrubbed from log records."""
        record = {"message": "Request received", "ip": "10.0.0.1"}
        result = scrub_log_record(record)
        assert result["ip"] == "***REDACTED***"

    def test_scrubs_metadata_field(self):
        """Test that metadata field is scrubbed."""
        record = {"message": "Event logged", "metadata": {"user_info": "sensitive"}}
        result = scrub_log_record(record)
        assert result["metadata"] == "***REDACTED***"

    def test_scrubs_session_id(self):
        """Test that session_id is scrubbed."""
        record = {"action": "login", "session_id": "sess_abc123"}
        result = scrub_log_record(record)
        assert result["session_id"] == "***REDACTED***"

    def test_scrubs_nested_log_data(self):
        """Test that nested log data is scrubbed."""
        record = {"event": "api_call", "data": {"user_id": "user123", "prompt": "Hello"}}
        result = scrub_log_record(record)
        assert result["data"]["user_id"] == "***REDACTED***"
        assert result["data"]["prompt"] == "***REDACTED***"

    def test_scrubs_list_with_sensitive_data(self):
        """Test that lists with sensitive data are scrubbed."""
        record = {"events": [{"user_id": "user1"}, {"user_id": "user2"}]}
        result = scrub_log_record(record)
        assert result["events"][0]["user_id"] == "***REDACTED***"
        assert result["events"][1]["user_id"] == "***REDACTED***"

    def test_never_raises_exceptions(self):
        """Test that scrub_log_record never raises exceptions."""
        assert scrub_log_record({}) == {}
        assert scrub_log_record({"key": None})["key"] is None


class TestForbiddenFields:
    """Tests for FORBIDDEN_FIELDS coverage."""

    def test_forbidden_fields_contains_user_identifiers(self):
        """Test that user identifiers are in FORBIDDEN_FIELDS."""
        from mlsdm.security.payload_scrubber import FORBIDDEN_FIELDS

        user_ids = {"user_id", "userid", "username", "account_id", "session_id"}
        assert user_ids.issubset(FORBIDDEN_FIELDS)

    def test_forbidden_fields_contains_network_identifiers(self):
        """Test that network identifiers are in FORBIDDEN_FIELDS."""
        from mlsdm.security.payload_scrubber import FORBIDDEN_FIELDS

        network_ids = {"ip", "ip_address", "client_ip", "remote_addr"}
        assert network_ids.issubset(FORBIDDEN_FIELDS)

    def test_forbidden_fields_contains_raw_content(self):
        """Test that raw content fields are in FORBIDDEN_FIELDS."""
        from mlsdm.security.payload_scrubber import FORBIDDEN_FIELDS

        raw_fields = {"raw_input", "raw_text", "full_prompt", "full_response", "prompt"}
        assert raw_fields.issubset(FORBIDDEN_FIELDS)


class TestIsSecureMode:
    """Tests for is_secure_mode function."""

    def test_secure_mode_default_false(self):
        """Test that secure mode is disabled by default."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        if "MLSDM_SECURE_MODE" in os.environ:
            del os.environ["MLSDM_SECURE_MODE"]
        assert is_secure_mode() is False

    def test_secure_mode_enabled_with_1(self):
        """Test that secure mode is enabled with MLSDM_SECURE_MODE=1."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        os.environ["MLSDM_SECURE_MODE"] = "1"
        try:
            assert is_secure_mode() is True
        finally:
            del os.environ["MLSDM_SECURE_MODE"]

    def test_secure_mode_enabled_with_true(self):
        """Test that secure mode is enabled with MLSDM_SECURE_MODE=true."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        os.environ["MLSDM_SECURE_MODE"] = "true"
        try:
            assert is_secure_mode() is True
        finally:
            del os.environ["MLSDM_SECURE_MODE"]

    def test_secure_mode_enabled_with_TRUE(self):
        """Test that secure mode is enabled with MLSDM_SECURE_MODE=TRUE."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        os.environ["MLSDM_SECURE_MODE"] = "TRUE"
        try:
            assert is_secure_mode() is True
        finally:
            del os.environ["MLSDM_SECURE_MODE"]

    def test_secure_mode_disabled_with_0(self):
        """Test that secure mode is disabled with MLSDM_SECURE_MODE=0."""
        from mlsdm.security.payload_scrubber import is_secure_mode

        os.environ["MLSDM_SECURE_MODE"] = "0"
        try:
            assert is_secure_mode() is False
        finally:
            del os.environ["MLSDM_SECURE_MODE"]


class TestExceptionSafety:
    """Tests that scrubber functions never raise exceptions."""

    def test_scrub_text_with_malformed_input(self):
        """Test that scrub_text handles malformed input gracefully."""
        # Empty string should return empty string
        assert scrub_text("") == ""
        # None should be returned as-is (documented behavior for empty/null input)
        # The function checks 'if not text' which handles None
        result = scrub_text(None)  # type: ignore[arg-type]
        assert result is None

    def test_scrub_dict_with_malformed_input(self):
        """Test that scrub_dict handles malformed input."""
        # These should not raise
        assert scrub_dict({}) == {}
        assert scrub_dict({"key": None})["key"] is None

    def test_scrub_request_payload_robust(self):
        """Test that scrub_request_payload is robust."""
        # Empty dict
        assert scrub_request_payload({}) == {}
        # None values
        result = scrub_request_payload({"key": None})
        assert result["key"] is None
        # Complex nested structure
        complex_data = {
            "a": {"b": {"c": {"d": {"e": "value"}}}},
            "list": [1, 2, {"nested": "data"}],
        }
        result = scrub_request_payload(complex_data)
        assert "a" in result

    def test_scrub_log_record_robust(self):
        """Test that scrub_log_record is robust."""
        # Empty dict
        assert scrub_log_record({}) == {}
        # None values
        result = scrub_log_record({"key": None})
        assert result["key"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

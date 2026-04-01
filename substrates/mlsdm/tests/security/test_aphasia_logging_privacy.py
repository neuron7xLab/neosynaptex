"""
Security tests for aphasia logging privacy.

This test suite validates that aphasia logging does NOT leak sensitive information
such as prompts, responses, or user input text. Only metadata like decisions,
severity, and flags should be logged.
"""

import logging

import numpy as np
import pytest

from mlsdm.extensions.neuro_lang_extension import NeuroLangWrapper
from mlsdm.observability.aphasia_logging import LOGGER_NAME

# Unique secret tokens to test for leakage
SECRET_PROMPT_TOKEN = "SUPER_SECRET_PROMPT_12345"
SECRET_RESPONSE_TOKEN = "CONFIDENTIAL_RESPONSE_98765"
SECRET_TECHNICAL_TOKEN = "API_KEY_XYZ_INTERNAL"


def leaky_llm_with_secrets(prompt: str, max_tokens: int) -> str:
    """
    LLM that produces responses containing secret tokens.
    We'll verify these don't appear in logs.
    """
    # Return a response with the secret token embedded
    return f"This is a response containing {SECRET_RESPONSE_TOKEN} and other data."


def dummy_embedder(text: str):
    """Generate deterministic embeddings for testing."""
    vec = np.ones(384, dtype=np.float32)
    return vec / np.linalg.norm(vec)


@pytest.mark.security
def test_aphasia_logs_do_not_contain_prompt_text(caplog):
    """Test that aphasia logs do not contain the user's prompt text."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=leaky_llm_with_secrets,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=True,
        neurolang_mode="disabled",
    )

    # Generate with a prompt containing a secret token
    prompt_with_secret = f"Tell me about {SECRET_PROMPT_TOKEN} in detail."
    _ = wrapper.generate(prompt=prompt_with_secret, moral_value=0.7, max_tokens=50)

    # Verify the secret prompt token is NOT in any log messages
    assert SECRET_PROMPT_TOKEN not in caplog.text, "Prompt text leaked into aphasia logs!"


@pytest.mark.security
def test_aphasia_logs_do_not_contain_response_text(caplog):
    """Test that aphasia logs do not contain the LLM's response text."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=leaky_llm_with_secrets,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=True,
        neurolang_mode="disabled",
    )

    # Generate - the response will contain SECRET_RESPONSE_TOKEN
    _ = wrapper.generate(prompt="Tell me something", moral_value=0.7, max_tokens=50)

    # Verify the secret response token is NOT in any log messages
    assert SECRET_RESPONSE_TOKEN not in caplog.text, "Response text leaked into aphasia logs!"


@pytest.mark.security
def test_aphasia_logs_only_contain_metadata(caplog):
    """Test that aphasia logs only contain expected metadata fields."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=leaky_llm_with_secrets,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=True,
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(
        prompt=f"Question about {SECRET_PROMPT_TOKEN}", moral_value=0.7, max_tokens=50
    )

    # Get all aphasia log records
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) > 0, "Expected at least one aphasia log record"

    for record in records:
        message = record.getMessage()

        # Verify expected metadata fields are present
        assert "decision=" in message
        assert "is_aphasic=" in message
        assert "severity=" in message
        assert "flags=" in message
        assert "detect_enabled=" in message
        assert "repair_enabled=" in message
        assert "severity_threshold=" in message

        # Verify sensitive data is NOT present
        assert SECRET_PROMPT_TOKEN not in message
        assert SECRET_RESPONSE_TOKEN not in message


@pytest.mark.security
def test_aphasia_logs_with_repair_do_not_leak_content(caplog):
    """Test that even when repair is triggered, no content leaks into logs."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    def telegraphic_llm_with_secret(prompt: str, max_tokens: int) -> str:
        """LLM producing aphasic output with a secret token."""
        return f"Short. Bad. {SECRET_TECHNICAL_TOKEN}. No good."

    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm_with_secret,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=True,
        aphasia_severity_threshold=0.1,  # Low threshold to trigger repair
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt=f"Explain {SECRET_PROMPT_TOKEN}", moral_value=0.7, max_tokens=50)

    # Verify neither the prompt secret nor the response secret leaked
    assert SECRET_PROMPT_TOKEN not in caplog.text
    assert SECRET_TECHNICAL_TOKEN not in caplog.text


@pytest.mark.security
def test_aphasia_logs_do_not_leak_even_with_disabled_detection(caplog):
    """Test that no sensitive data appears in logs even when detection is disabled."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=leaky_llm_with_secrets,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=False,  # Detection disabled
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(
        prompt=f"Secret query: {SECRET_PROMPT_TOKEN}", moral_value=0.7, max_tokens=50
    )

    # When detection is disabled, there should be no aphasia logs at all
    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 0

    # But also verify the secret didn't leak anywhere in the entire log
    assert SECRET_PROMPT_TOKEN not in caplog.text
    assert SECRET_RESPONSE_TOKEN not in caplog.text


@pytest.mark.security
def test_multiple_generations_do_not_leak_any_secrets(caplog):
    """Test that across multiple generations, no secrets leak into logs."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=leaky_llm_with_secrets,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        aphasia_detect_enabled=True,
        neurolang_mode="disabled",
    )

    # Perform multiple generations with different secret tokens
    secrets = [
        "SECRET_TOKEN_A",
        "SECRET_TOKEN_B",
        "SECRET_TOKEN_C",
    ]

    for secret in secrets:
        _ = wrapper.generate(prompt=f"Query about {secret}", moral_value=0.7, max_tokens=50)

    # Verify none of the secrets leaked
    for secret in secrets:
        assert secret not in caplog.text, f"Secret {secret} leaked into logs!"

    # Also verify our test response secret didn't leak
    assert SECRET_RESPONSE_TOKEN not in caplog.text

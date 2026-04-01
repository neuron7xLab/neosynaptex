"""
Unit tests for PipelineSpeechGovernor.

Tests the composable pipeline implementation for speech governance,
including deterministic execution order and failure isolation.
"""

import logging

from mlsdm.speech.governance import (
    PipelineSpeechGovernor,
    SpeechGovernanceResult,
)


class AppendGovernor:
    def __init__(self, suffix: str) -> None:
        self._suffix = suffix

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        new_text = draft + self._suffix
        return SpeechGovernanceResult(
            final_text=new_text,
            raw_text=draft,
            metadata={"suffix": self._suffix},
        )


class FailingGovernor:
    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        raise RuntimeError("boom")


def test_pipeline_applies_governors_in_order():
    pipeline = PipelineSpeechGovernor(
        governors=[
            ("g1", AppendGovernor("A")),
            ("g2", AppendGovernor("B")),
        ]
    )
    result = pipeline(prompt="p", draft="X", max_tokens=32)

    assert result.raw_text == "X"
    assert result.final_text == "XAB"

    history = result.metadata["pipeline"]
    assert [step["name"] for step in history] == ["g1", "g2"]
    assert history[0]["raw_text"] == "X"
    assert history[0]["final_text"] == "XA"
    assert history[1]["raw_text"] == "XA"
    assert history[1]["final_text"] == "XAB"


def test_pipeline_isolates_failing_governor(caplog):
    pipeline = PipelineSpeechGovernor(
        governors=[
            ("ok", AppendGovernor("A")),
            ("fail", FailingGovernor()),
            ("ok2", AppendGovernor("B")),
        ]
    )

    caplog.set_level(logging.ERROR, logger="mlsdm.speech.pipeline")

    result = pipeline(prompt="p", draft="X", max_tokens=32)

    assert result.final_text == "XAB"

    history = result.metadata["pipeline"]
    assert [step["name"] for step in history] == ["ok", "fail", "ok2"]
    assert history[0]["status"] == "ok"
    assert history[1]["status"] == "error"
    assert history[2]["status"] == "ok"

    # Verify that error was logged
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "governor=fail failed" in messages


def test_pipeline_empty_governors_list():
    """Test pipeline with no governors returns original draft."""
    pipeline = PipelineSpeechGovernor(governors=[])
    result = pipeline(prompt="test", draft="original", max_tokens=32)

    assert result.final_text == "original"
    assert result.raw_text == "original"
    assert result.metadata["pipeline"] == []


def test_pipeline_single_governor():
    """Test pipeline with single governor works correctly."""
    pipeline = PipelineSpeechGovernor(
        governors=[("only", AppendGovernor("!"))],
    )
    result = pipeline(prompt="test", draft="Hello", max_tokens=32)

    assert result.final_text == "Hello!"
    assert result.raw_text == "Hello"
    assert len(result.metadata["pipeline"]) == 1
    assert result.metadata["pipeline"][0]["name"] == "only"


def test_pipeline_preserves_governor_metadata():
    """Test that governor-specific metadata is preserved in pipeline history."""
    pipeline = PipelineSpeechGovernor(
        governors=[
            ("append_x", AppendGovernor("X")),
            ("append_y", AppendGovernor("Y")),
        ]
    )
    result = pipeline(prompt="test", draft="Z", max_tokens=32)

    history = result.metadata["pipeline"]
    assert history[0]["metadata"]["suffix"] == "X"
    assert history[1]["metadata"]["suffix"] == "Y"


def test_pipeline_error_includes_exception_details():
    """Test that error entries include exception type and message."""
    pipeline = PipelineSpeechGovernor(governors=[("failer", FailingGovernor())])
    result = pipeline(prompt="test", draft="text", max_tokens=32)

    history = result.metadata["pipeline"]
    assert len(history) == 1
    assert history[0]["status"] == "error"
    assert history[0]["error_type"] == "RuntimeError"
    assert history[0]["error_message"] == "boom"


def test_pipeline_all_governors_fail():
    """Test pipeline where all governors fail still returns original draft."""
    pipeline = PipelineSpeechGovernor(
        governors=[
            ("fail1", FailingGovernor()),
            ("fail2", FailingGovernor()),
        ]
    )
    result = pipeline(prompt="test", draft="original", max_tokens=32)

    assert result.final_text == "original"  # No successful transformation
    assert result.raw_text == "original"
    assert all(step["status"] == "error" for step in result.metadata["pipeline"])


def test_pipeline_governor_receives_correct_prompt():
    """Test that all governors receive the original prompt."""
    received_prompts = []

    class PromptCapturingGovernor:
        def __init__(self, name: str):
            self.name = name

        def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
            received_prompts.append((self.name, prompt))
            return SpeechGovernanceResult(
                final_text=draft,
                raw_text=draft,
                metadata={},
            )

    pipeline = PipelineSpeechGovernor(
        governors=[
            ("g1", PromptCapturingGovernor("g1")),
            ("g2", PromptCapturingGovernor("g2")),
        ]
    )
    pipeline(prompt="original_prompt", draft="text", max_tokens=32)

    assert received_prompts == [("g1", "original_prompt"), ("g2", "original_prompt")]


def test_pipeline_governor_receives_correct_max_tokens():
    """Test that all governors receive the same max_tokens."""
    received_tokens = []

    class TokenCapturingGovernor:
        def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
            received_tokens.append(max_tokens)
            return SpeechGovernanceResult(
                final_text=draft,
                raw_text=draft,
                metadata={},
            )

    pipeline = PipelineSpeechGovernor(
        governors=[
            ("g1", TokenCapturingGovernor()),
            ("g2", TokenCapturingGovernor()),
        ]
    )
    pipeline(prompt="test", draft="text", max_tokens=128)

    assert received_tokens == [128, 128]

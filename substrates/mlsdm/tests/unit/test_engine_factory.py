"""
Comprehensive tests for engine/factory.py.

Tests cover:
- build_stub_embedding_fn
- build_neuro_engine_from_env with various configurations
"""

import os
from unittest.mock import patch

import numpy as np
import pytest

from mlsdm.engine.factory import (
    build_neuro_engine_from_env,
    build_stub_embedding_fn,
)
from mlsdm.engine.neuro_cognitive_engine import NeuroEngineConfig


class TestBuildStubEmbeddingFn:
    """Tests for build_stub_embedding_fn function."""

    def test_default_dimension(self):
        """Test embedding function with default dimension."""
        embed_fn = build_stub_embedding_fn()
        vec = embed_fn("test text")
        assert vec.shape == (384,)
        assert vec.dtype == np.float32

    def test_custom_dimension(self):
        """Test embedding function with custom dimension."""
        embed_fn = build_stub_embedding_fn(dim=128)
        vec = embed_fn("test text")
        assert vec.shape == (128,)

    def test_deterministic_output(self):
        """Test that same input produces same output."""
        embed_fn = build_stub_embedding_fn()
        vec1 = embed_fn("test text")
        vec2 = embed_fn("test text")
        assert np.allclose(vec1, vec2)

    def test_different_inputs_produce_different_outputs(self):
        """Test that different inputs produce different outputs."""
        embed_fn = build_stub_embedding_fn()
        vec1 = embed_fn("text one")
        vec2 = embed_fn("text two")
        assert not np.allclose(vec1, vec2)

    def test_normalized_output(self):
        """Test that output is normalized (unit length)."""
        embed_fn = build_stub_embedding_fn()
        vec = embed_fn("any text here")
        norm = np.linalg.norm(vec)
        assert norm == pytest.approx(1.0, rel=1e-6)


class TestBuildNeuroEngineFromEnvLocalStub:
    """Tests for build_neuro_engine_from_env with local_stub backend."""

    def test_default_local_stub(self):
        """Test building engine with default (local_stub) backend."""
        # Clear any existing LLM_BACKEND
        env = {"LLM_BACKEND": "local_stub"}
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env()
            assert engine is not None
            # Verify it can generate
            result = engine.generate("Hello")
            assert result is not None

    def test_explicit_local_stub(self):
        """Test building engine with explicit local_stub backend."""
        env = {"LLM_BACKEND": "local_stub"}
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env()
            assert engine is not None

    def test_with_custom_config(self):
        """Test building engine with custom config."""
        config = NeuroEngineConfig(
            dim=256,
            capacity=5000,
            initial_moral_threshold=0.6,
        )
        env = {"LLM_BACKEND": "local_stub"}
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env(config=config)
            assert engine is not None


class TestBuildNeuroEngineFromEnvInvalid:
    """Tests for build_neuro_engine_from_env with invalid configurations."""

    def test_invalid_backend(self):
        """Test that invalid backend raises ValueError."""
        env = {"LLM_BACKEND": "invalid_backend"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError) as exc_info:
                build_neuro_engine_from_env()
            assert "Invalid LLM_BACKEND" in str(exc_info.value)

    def test_invalid_router_mode(self):
        """Test that invalid router_mode raises ValueError."""
        config = NeuroEngineConfig(router_mode="invalid_mode")
        env = {"LLM_BACKEND": "local_stub"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError) as exc_info:
                build_neuro_engine_from_env(config=config)
            assert "Invalid router_mode" in str(exc_info.value)


class TestBuildNeuroEngineRouterModes:
    """Tests for different router modes."""

    def test_single_mode_default(self):
        """Test single router mode (default)."""
        config = NeuroEngineConfig(router_mode="single")
        env = {"LLM_BACKEND": "local_stub"}
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env(config=config)
            assert engine is not None

    def test_rule_based_mode(self):
        """Test rule_based router mode."""
        config = NeuroEngineConfig(
            router_mode="rule_based",
            rule_based_config={"default": "local_stub"},
        )
        env = {
            "LLM_BACKEND": "local_stub",
            "MULTI_LLM_BACKENDS": "local_stub",
        }
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env(config=config)
            assert engine is not None

    def test_ab_test_mode(self):
        """Test ab_test router mode."""
        config = NeuroEngineConfig(
            router_mode="ab_test",
            ab_test_config={
                "control": "default",
                "treatment": "default",
                "treatment_ratio": 0.5,
            },
        )
        env = {
            "LLM_BACKEND": "local_stub",
            "MULTI_LLM_BACKENDS": "local_stub",
        }
        with patch.dict(os.environ, env, clear=False):
            engine = build_neuro_engine_from_env(config=config)
            assert engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

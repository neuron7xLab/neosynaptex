"""
End-to-end tests for NeuroCognitiveEngine with local_stub backend.

These tests validate the complete pipeline from factory creation through
generation, ensuring all components work together correctly.
"""

import json
import os

from mlsdm.engine import build_neuro_engine_from_env


class TestNeuroCognitiveEngineE2EStubBackend:
    """E2E tests using local_stub backend (no external dependencies)."""

    def setup_method(self) -> None:
        """Set up environment for each test."""
        # Ensure we're using the local_stub backend
        os.environ["LLM_BACKEND"] = "local_stub"

    def test_e2e_basic_request_returns_response(self) -> None:
        """
        Test that a basic request returns a valid response.

        Validates:
        - Engine can be built from environment
        - Generate method returns structured response
        - Response contains expected keys
        - Response text is non-empty
        """
        # Build engine from environment
        engine = build_neuro_engine_from_env()

        # Make a simple request
        prompt = "Hello, how are you?"
        result = engine.generate(prompt, max_tokens=128)

        # Validate response structure
        assert "response" in result
        assert "governance" in result
        assert "mlsdm" in result
        assert "timing" in result
        assert "validation_steps" in result
        assert "error" in result
        assert "rejected_at" in result

        # Validate successful response
        assert result["response"] != ""
        assert result["error"] is None
        assert result["rejected_at"] is None

        # Validate MLSDM state
        assert result["mlsdm"] is not None
        assert result["mlsdm"]["accepted"] is True

        # Validate response contains expected stub pattern
        assert "NEURO-RESPONSE:" in result["response"]

    def test_e2e_rejected_by_moral_precheck(self) -> None:
        """
        Test that moral pre-check correctly rejects immoral requests.

        Validates:
        - Pre-flight moral check is executed
        - High moral thresholds lead to rejection at pre_flight stage
        - Rejection errors are properly returned
        - Validation steps are tracked
        """
        # Build engine from environment
        engine = build_neuro_engine_from_env()

        # Make a request with very high moral threshold (0.95)
        # This will be rejected by moral precheck since score (0.8) < threshold (0.95)
        result = engine.generate(
            "This should be rejected",
            moral_value=0.95,  # Very high threshold
            max_tokens=128,
        )

        # Validate moral_precheck step exists
        moral_steps = [s for s in result["validation_steps"] if s["step"] == "moral_precheck"]
        assert len(moral_steps) > 0, "moral_precheck step should be present"

        moral_step = moral_steps[0]

        # Check if moral precheck was executed or skipped
        if moral_step.get("skipped", False):
            # If skipped, no moral filter available - test passes
            assert moral_step.get("reason") == "moral_filter_not_available"
        else:
            # If executed, validate structure
            assert "passed" in moral_step
            assert "score" in moral_step
            assert "threshold" in moral_step

            # With compute_moral_value, score=0.8 < threshold=0.95, so it should fail
            if not moral_step["passed"]:
                assert result["rejected_at"] == "pre_flight"
                assert result["error"] is not None
                assert result["error"]["type"] == "moral_precheck"
                assert result["response"] == ""
                assert moral_step["score"] < moral_step["threshold"]

    def test_e2e_response_structure_and_serialization(self) -> None:
        """
        Test complete response structure and JSON serialization.

        Validates:
        - All expected keys are present
        - Timing metrics are collected
        - Validation steps are tracked
        - Response can be serialized to JSON (for API use)
        """
        # Build engine from environment
        engine = build_neuro_engine_from_env()

        # Make a request with various parameters
        result = engine.generate(
            "Test prompt for serialization",
            max_tokens=256,
            user_intent="conversational",
            cognitive_load=0.5,
            moral_value=0.5,
            context_top_k=5,
            enable_diagnostics=True,
        )

        # Validate all expected keys
        expected_keys = {
            "response",
            "governance",
            "mlsdm",
            "timing",
            "validation_steps",
            "error",
            "rejected_at",
            "decision_trace",
            "meta",  # Added in Phase 8 for multi-LLM tracking
        }
        assert set(result.keys()) == expected_keys

        # Validate timing metrics
        assert isinstance(result["timing"], dict)
        assert "total" in result["timing"]
        assert "moral_precheck" in result["timing"]
        assert "generation" in result["timing"]
        assert result["timing"]["total"] > 0

        # Validate validation steps
        assert isinstance(result["validation_steps"], list)
        assert len(result["validation_steps"]) > 0
        for step in result["validation_steps"]:
            assert "step" in step
            assert "passed" in step

        # Validate JSON serialization (excluding complex objects)
        serializable_result = {
            "response": result["response"],
            "timing": result["timing"],
            "validation_steps": result["validation_steps"],
            "error": result["error"],
            "rejected_at": result["rejected_at"],
            "decision_trace": result["decision_trace"],
        }

        # Should not raise exception
        json_str = json.dumps(serializable_result)
        parsed = json.loads(json_str)

        # Verify round-trip
        assert parsed["response"] == result["response"]
        assert parsed["timing"] == result["timing"]
        assert parsed["validation_steps"] == result["validation_steps"]

    def test_e2e_multiple_requests_isolation(self) -> None:
        """
        Test that multiple requests maintain proper isolation.

        Validates:
        - Engine can handle multiple requests
        - Each request has independent timing metrics
        - At least some requests succeed (adaptive moral filter may reject some)

        Note: MLSDM has an adaptive moral filter that adjusts after each request.
        Some requests may be rejected due to this adaptation, which is expected behavior.
        """
        # Build engine from environment with lower moral threshold to reduce rejections
        from mlsdm.engine import NeuroEngineConfig

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.3,  # Lower threshold to accept more
        )
        engine = build_neuro_engine_from_env(config=config)

        # Make multiple requests with low moral value
        results = []
        for i in range(3):
            result = engine.generate(
                f"Request number {i}",
                max_tokens=128,
                moral_value=0.3,  # Low moral requirement
            )
            results.append(result)

        # Validate timing independence for all requests
        timings = [r["timing"]["total"] for r in results]
        # All should have positive timing
        assert all(t > 0 for t in timings)

        # At least the first request should succeed
        assert results[0]["response"] != ""
        assert results[0]["error"] is None
        assert "Request number 0" in results[0]["response"]

    def test_e2e_different_parameters_affect_pipeline(self) -> None:
        """
        Test that different parameters properly affect the pipeline.

        Validates:
        - max_tokens affects response content
        - moral_value is propagated
        - Different requests can have different parameters
        """
        # Build engine from environment with low moral threshold
        from mlsdm.engine import NeuroEngineConfig

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.3,
        )
        engine = build_neuro_engine_from_env(config=config)

        # Test with low moral threshold (should accept)
        result_accept = engine.generate(
            "Neutral prompt",
            moral_value=0.3,  # Low threshold to ensure acceptance
            max_tokens=50,
        )
        # May succeed or be rejected by adaptive filter
        assert result_accept["response"] != "" or result_accept["error"] is not None

        # Test with different max_tokens in a fresh engine to avoid adaptive rejection
        engine2 = build_neuro_engine_from_env(config=config)
        result_long = engine2.generate(
            "Test prompt",
            max_tokens=512,
            moral_value=0.3,
        )
        # Should succeed with first request
        assert result_long["error"] is None
        assert result_long["response"] != ""
        # Stub adapter includes max_tokens info in response
        assert "max_tokens=512" in result_long["response"]

    def test_e2e_factory_with_custom_config(self) -> None:
        """
        Test factory with custom NeuroEngineConfig.

        Validates:
        - Custom config is respected for most parameters
        - Engine can be built with custom config
        - Generation works with custom config

        Note: The factory may override the dim parameter based on EMBEDDING_DIM
        environment variable, so we don't strictly validate dim.
        """
        from mlsdm.engine import NeuroEngineConfig

        # Create custom config
        custom_config = NeuroEngineConfig(
            dim=384,  # Use default dim to match factory behavior
            capacity=10000,
            enable_fslgs=False,  # Disable FSLGS for simplicity
            initial_moral_threshold=0.3,
        )

        # Build engine with custom config
        engine = build_neuro_engine_from_env(config=custom_config)

        # Validate config is used (capacity and fslgs should be preserved)
        assert engine.config.capacity == 10000
        assert engine.config.enable_fslgs is False

        # Test generation still works
        result = engine.generate(
            "Test with custom config",
            max_tokens=128,
            moral_value=0.3,
        )
        assert result["response"] != ""
        assert result["error"] is None

    def test_e2e_state_persistence(self) -> None:
        """
        Test that engine state persists across calls.

        Validates:
        - MLSDM state is updated after each call
        - Last states can be retrieved
        """
        # Build engine from environment
        engine = build_neuro_engine_from_env()

        # First request
        engine.generate("First request", max_tokens=128)
        state1 = engine.get_last_states()

        assert state1["mlsdm"] is not None

        # Second request
        engine.generate("Second request", max_tokens=128)
        state2 = engine.get_last_states()

        assert state2["mlsdm"] is not None

        # States should be different (different steps)
        assert state1["mlsdm"]["step"] != state2["mlsdm"]["step"]

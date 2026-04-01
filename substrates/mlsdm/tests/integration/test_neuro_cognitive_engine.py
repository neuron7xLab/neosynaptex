"""
Integration / architecture tests for NeuroCognitiveEngine.

Ціль:
- Валідувати ключові архітектурні рішення (single memory, pre-flight, error propagation).
- Перевірити базові SLA (латентність з моками).
- Переконатися, що результат можна серіалізувати та інтегрувати в прод.
"""

import concurrent.futures
import json
import time
from unittest.mock import Mock, patch

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import (
    NeuroCognitiveEngine,
    NeuroEngineConfig,
)

# Fixed seed for reproducible tests
_SEED = 42


@pytest.fixture(autouse=True)
def set_random_seed():
    """Set random seed before each test for reproducibility."""
    np.random.seed(_SEED)
    yield


class TestNeuroCognitiveEngineArchitecture:
    """Architectural validation: single memory, params, errors, observability."""

    def test_single_source_of_truth_memory_architecture(self):
        """FIX-001: FSLGS не має власної пам'яті, використовує MLSDM як єдине джерело."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=True,
            fslgs_memory_capacity=2048,  # має бути проігноровано
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        if engine._fslgs is None:
            pytest.skip("FSLGS not available in this environment")

        # FSLGS повинен працювати без власної пам'яті
        assert getattr(engine._fslgs, "memory_capacity", 0) == 0
        assert getattr(engine._fslgs, "fractal_levels", None) is None

    def test_runtime_parameter_propagation(self):
        """FIX-002: Параметри moral_value та context_top_k правильно передаються."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        # Перевіряємо, що runtime-параметри оновлюються
        engine.generate("Test", moral_value=0.8, context_top_k=10)

        assert engine._runtime_moral_value == 0.8
        assert engine._runtime_context_top_k == 10

    def test_explicit_error_handling(self):
        """FIX-003: Explicit exceptions замість silent failures."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        # Симулюємо MLSDM rejection
        with patch.object(engine._mlsdm, "generate") as mock_generate:
            mock_generate.return_value = {
                "accepted": False,
                "note": "moral rejection",
                "response": "",
            }

            result = engine.generate("Test")

            # Очікуємо structured error у відповіді
            assert result["error"] is not None
            assert result["error"]["type"] == "mlsdm_rejection"
            assert result["rejected_at"] == "generation"

    def test_preflight_validation_moral_check(self):
        """FIX-004: Pre-flight moral check блокує некоректні запити."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        # Mock moral filter для pre-flight rejection
        with patch.object(engine._mlsdm, "moral") as mock_moral:
            mock_moral.compute_moral_value = Mock(return_value=0.2)

            result = engine.generate("Bad prompt", moral_value=0.5)

            # LLM не повинен бути викликаний
            llm_mock.assert_not_called()

            # Перевіряємо швидку відмову
            assert result["rejected_at"] == "pre_flight"
            assert result["error"]["type"] == "moral_precheck"
            assert result["response"] == ""

    def test_timing_metrics_collection(self):
        """FIX-005: Timing metrics збираються для всіх етапів."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        result = engine.generate("Test prompt")

        # Перевіряємо наявність timing metrics
        assert "timing" in result
        assert "total" in result["timing"]
        assert "moral_precheck" in result["timing"]
        assert "generation" in result["timing"]

        # Timing має бути в мілісекундах
        assert result["timing"]["total"] > 0
        assert isinstance(result["timing"]["total"], (int, float))

    def test_validation_steps_tracking(self):
        """Validation steps відслідковуються та логуються."""
        llm_mock = Mock(return_value="Test response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        result = engine.generate("Test prompt")

        # Перевіряємо наявність validation_steps
        assert "validation_steps" in result
        assert isinstance(result["validation_steps"], list)

        # Має бути хоча б один крок валідації (moral_precheck)
        assert len(result["validation_steps"]) > 0

        # Кожен крок має мати поля step та passed
        for step in result["validation_steps"]:
            assert "step" in step
            assert "passed" in step


class TestNeuroCognitiveEnginePerformance:
    """Performance and SLA validation with mocks."""

    def test_latency_baseline_without_fslgs(self):
        """Baseline latency без FSLGS (тільки MLSDM)."""

        def fast_llm(prompt: str, max_tokens: int) -> str:
            time.sleep(0.01)  # 10ms mock
            return "Fast response"

        def fast_embedding(text: str) -> np.ndarray:
            return np.random.randn(384)

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=fast_llm,
            embedding_fn=fast_embedding,
            config=config,
        )

        result = engine.generate("Test")

        # Очікуємо латентність < 100ms з моками
        assert result["timing"]["total"] < 100.0

    def test_concurrent_requests_isolation(self):
        """Concurrent requests не перетинаються за state."""
        call_count = [0]

        def counting_llm(prompt: str, max_tokens: int) -> str:
            call_count[0] += 1
            return f"Response {call_count[0]}"

        def simple_embedding(text: str) -> np.ndarray:
            return np.random.randn(384)

        config = NeuroEngineConfig(
            enable_fslgs=False,
            initial_moral_threshold=0.0,  # Accept all requests
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=counting_llm,
            embedding_fn=simple_embedding,
            config=config,
        )

        # Mock the moral filter to always accept
        with (
            patch.object(engine._mlsdm.moral, "evaluate", return_value=True),
            concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor,
        ):
            futures = [
                executor.submit(engine.generate, f"Prompt {i}", moral_value=0.0) for i in range(3)
            ]
            results = [f.result() for f in futures]

        # Всі запити повинні успішно завершитися
        assert all(r["response"] for r in results)
        assert all("timing" in r for r in results)

        # Перевіряємо ізоляцію - кожен має унікальну відповідь
        responses = [r["response"] for r in results]
        assert len(set(responses)) == 3  # Всі відповіді унікальні


class TestNeuroCognitiveEngineIntegration:
    """End-to-end integration scenarios."""

    def test_response_serialization(self):
        """Результат можна серіалізувати для production use."""
        llm_mock = Mock(return_value="Serializable response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        result = engine.generate("Test")

        # Перевіряємо, що результат можна серіалізувати
        try:
            # Видаляємо numpy arrays для JSON serialization
            serializable_result = {
                k: v for k, v in result.items() if k not in ["mlsdm", "governance"]
            }
            json_str = json.dumps(serializable_result)
            parsed = json.loads(json_str)

            assert parsed["response"] == "Serializable response"
            assert "timing" in parsed
            assert "validation_steps" in parsed
        except (TypeError, ValueError) as e:
            pytest.fail(f"Result not serializable: {e}")

    def test_full_pipeline_success_path(self):
        """Повний успішний шлях через pipeline."""
        llm_mock = Mock(return_value="Full pipeline response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        result = engine.generate(
            "Valid prompt",
            moral_value=0.7,
            context_top_k=5,
            max_tokens=256,
        )

        # Перевіряємо успішний результат
        assert result["response"] == "Full pipeline response"
        assert result["error"] is None
        assert result["rejected_at"] is None
        assert result["mlsdm"] is not None
        assert result["mlsdm"]["accepted"] is True

    def test_full_pipeline_rejection_path(self):
        """Повний шлях з rejection."""
        llm_mock = Mock(return_value="Should not be called")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        # Mock moral filter для rejection
        with patch.object(engine._mlsdm, "moral") as mock_moral:
            mock_moral.compute_moral_value = Mock(return_value=0.1)

            result = engine.generate("Bad prompt", moral_value=0.5)

            # Перевіряємо rejection
            assert result["response"] == ""
            assert result["error"] is not None
            assert result["rejected_at"] == "pre_flight"
            llm_mock.assert_not_called()

    def test_state_persistence_across_calls(self):
        """State правильно зберігається між викликами."""
        llm_mock = Mock(return_value="Response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        # Перший виклик
        engine.generate("First prompt")
        state1 = engine.get_last_states()

        assert state1["mlsdm"] is not None

        # Другий виклик
        engine.generate("Second prompt")
        state2 = engine.get_last_states()

        # State оновлюється
        assert state2["mlsdm"] is not None
        assert state1["mlsdm"]["step"] != state2["mlsdm"]["step"]


class TestNeuroCognitiveEngineFSLGSIntegration:
    """FSLGS-specific integration tests."""

    @pytest.mark.skipif("fslgs" not in dir(), reason="FSLGS not available in this environment")
    def test_fslgs_grammar_precheck(self):
        """FSLGS grammar pre-check працює коректно."""
        llm_mock = Mock(return_value="Response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=True)

        with patch("mlsdm.engine.neuro_cognitive_engine.FSLGSWrapper") as mock_fslgs_cls:
            mock_fslgs_instance = Mock()
            mock_fslgs_instance.grammar = Mock()
            mock_fslgs_instance.grammar.validate_input_structure = Mock(return_value=False)
            mock_fslgs_cls.return_value = mock_fslgs_instance

            engine = NeuroCognitiveEngine(
                llm_generate_fn=llm_mock,
                embedding_fn=embedding_mock,
                config=config,
            )

            result = engine.generate("Invalid grammar prompt")

            # Grammar pre-check має відхилити
            assert result["rejected_at"] == "pre_flight"
            assert result["error"]["type"] == "grammar_precheck"
            llm_mock.assert_not_called()

    def test_fslgs_disabled_fallback(self):
        """Коректний fallback коли FSLGS вимкнений."""
        llm_mock = Mock(return_value="Fallback response")
        embedding_mock = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_mock,
            embedding_fn=embedding_mock,
            config=config,
        )

        assert engine._fslgs is None

        result = engine.generate("Test")

        # Має працювати через MLSDM fallback
        assert result["response"] == "Fallback response"
        assert result["governance"] is None

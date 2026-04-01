import numpy as np

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.core.llm_wrapper import LLMWrapper


def _dummy_llm(prompt: str, max_tokens: int) -> str:
    return prompt[:max_tokens]


def _dummy_embedder(text: str) -> np.ndarray:
    # Keep embedding dimension small for test speed but valid normalization
    return np.ones(8, dtype=np.float32)


def test_wrapper_moral_ro_blocks_adapt() -> None:
    wrapper = LLMWrapper(llm_generate_fn=_dummy_llm, embedding_fn=_dummy_embedder, dim=8)
    assert not hasattr(wrapper.moral, "adapt")


def test_wrapper_synaptic_ro_blocks_update_and_reset() -> None:
    wrapper = LLMWrapper(llm_generate_fn=_dummy_llm, embedding_fn=_dummy_embedder, dim=8)
    assert not hasattr(wrapper.synaptic, "update")
    assert not hasattr(wrapper.synaptic, "reset_all")


def test_wrapper_pelm_ro_blocks_entangle() -> None:
    wrapper = LLMWrapper(llm_generate_fn=_dummy_llm, embedding_fn=_dummy_embedder, dim=8)
    assert not hasattr(wrapper.pelm, "entangle")


def test_wrapper_rhythm_ro_blocks_step() -> None:
    wrapper = LLMWrapper(llm_generate_fn=_dummy_llm, embedding_fn=_dummy_embedder, dim=8)
    assert not hasattr(wrapper.rhythm, "step")


def test_wrapper_generate_smoke() -> None:
    wrapper = LLMWrapper(llm_generate_fn=_dummy_llm, embedding_fn=_dummy_embedder, dim=8)
    result = wrapper.generate(prompt="hello world", moral_value=0.8)
    assert result["accepted"] is True
    assert result["response"]


def test_cognitive_controller_process_event_smoke() -> None:
    controller = CognitiveController(dim=8)
    vector = np.ones(8, dtype=np.float32)
    result = controller.process_event(vector=vector, moral_value=0.8)
    assert result["accepted"] is True

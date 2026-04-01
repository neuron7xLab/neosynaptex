import numpy as np

from ai_integration.memory_module import CA1MemoryModule
from data.biophysical_parameters import AIIntegrationParams


def test_memory_store_and_retrieve_topk_deterministic():
    np.random.seed(0)
    params = AIIntegrationParams(
        d_model=4,
        d_CA1=4,
        memory_size=4,
        key_dim=4,
        value_dim=4,
        top_k=2,
        use_phase_key=False,
        temperature=0.1,
    )
    memory = CA1MemoryModule(params)
    # Make encoding/decoding deterministic and identity-like
    memory.W_encoder = np.eye(params.key_dim, params.d_model)
    memory.W_decoder = np.eye(params.d_model, params.value_dim)

    vectors = [
        np.array([1.0, 0.0, 0.0, 0.0]),
        np.array([0.9, 0.1, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0, 0.0]),
    ]
    for v in vectors:
        memory.store(h_t=v, v_t=v, novelty=1.0)

    query = np.array([1.0, 0.0, 0.0, 0.0])
    retrieved, indices = memory.retrieve(query, top_k=2)

    assert indices == [0, 1]
    assert retrieved.shape == (params.d_model,)
    # Highest weight on the first vector
    assert np.isclose(retrieved[0], retrieved.max())

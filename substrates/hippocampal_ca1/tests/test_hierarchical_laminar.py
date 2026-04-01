import numpy as np

from core.hierarchical_laminar import CellDataHier, HierarchicalLaminarModel


def test_em_outputs_normalized_and_finite():
    np.random.seed(0)
    cells = [
        CellDataHier(
            cell_id=i, animal_id=0, x=0.0, y=0.0, z=z, s=0.0, transcripts=np.array([5, 1, 0, 0])
        )
        for i, z in enumerate(np.linspace(0.1, 0.9, 4))
    ]
    model = HierarchicalLaminarModel(lambda_mrf=0.0)
    q = model.fit_em_vectorized(cells, max_iter=5, verbose=False)

    assert q.shape == (len(cells), model.n_layers)
    assert np.allclose(q.sum(axis=1), 1.0)
    assert not np.isnan(q).any()

    assignments = model.assign_layers(cells, q)
    assert assignments.shape == (len(cells),)
    # Ensure assignments remain stable over another short run
    q2 = model.fit_em_vectorized(cells, max_iter=5, verbose=False)
    assignments2 = model.assign_layers(cells, q2)
    assert np.array_equal(assignments, assignments2)

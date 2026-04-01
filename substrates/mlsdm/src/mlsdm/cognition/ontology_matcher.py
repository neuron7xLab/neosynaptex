from typing import Any

import numpy as np


class OntologyMatcher:
    def __init__(self, ontology_vectors: np.ndarray, labels: list[Any] | None = None) -> None:
        if not isinstance(ontology_vectors, np.ndarray) or ontology_vectors.ndim != 2:
            raise ValueError("ontology_vectors must be a 2D NumPy array.")
        if labels is not None and len(labels) != len(ontology_vectors):
            raise ValueError("Length of labels must match ontology size.")

        self.ontology = ontology_vectors
        self.labels = labels or list(range(len(ontology_vectors)))
        self.dimension = self.ontology.shape[1]

    def match(self, event_vector: np.ndarray, metric: str = "cosine") -> tuple[Any | None, float]:
        if not isinstance(event_vector, np.ndarray) or event_vector.shape[0] != self.dimension:
            raise ValueError(f"Event vector must be a NumPy array of dimension {self.dimension}.")
        if metric not in ("cosine", "euclidean"):
            raise ValueError("Metric must be 'cosine' or 'euclidean'.")

        if self.ontology.shape[0] == 0:
            return None, 0.0

        ev = event_vector
        if metric == "euclidean":
            diffs = self.ontology - ev
            dists = np.linalg.norm(diffs, axis=1)
            idx = int(np.argmin(dists))
            return self.labels[idx], float(-dists[idx])

        norms_onto = np.linalg.norm(self.ontology, axis=1)
        norm_ev = float(np.linalg.norm(ev))
        if norm_ev == 0 or np.all(norms_onto == 0):
            return None, 0.0
        sims = self.ontology.dot(ev) / (norms_onto * norm_ev)
        idx = int(np.argmax(sims))
        return self.labels[idx], float(sims[idx])

    def to_dict(self) -> dict[str, Any]:
        return {"ontology_vectors": self.ontology.tolist(), "labels": self.labels}

"""FractalPELMGPU: Experimental GPU/CPU backend for phase-aware retrieval.

EXPERIMENTAL STATUS:
    This module is experimental and intended for research/benchmarking purposes.
    It is not part of the stable MLSDM API and does not integrate with the core pipeline.
    Requires PyTorch (torch) which is an optional dependency.

Purpose:
    Provides a GPU-accelerated (or CPU fallback) implementation of phase-entangled
    memory with fractal-weighted scoring for retrieval.

Scoring formula:
    score = cos_sim(q, v) * exp(-|φ_q - φ_v|) * clamp(1 - fractal_weight * log1p(||q - v||), 0, 1)

    Where:
    - cos_sim(q, v) = (q · v) / (||q|| * ||v|| + ε)  -- cosine similarity
    - exp(-|φ_q - φ_v|) -- phase similarity term, peaks at 1.0 when phases match
    - log1p(||q - v||) -- distance term using log1p for numerical stability
    - fractal_weight -- engineering hyperparameter controlling distance influence [0, 1]
    - ε = 1e-12 -- small constant for numerical stability

    The final score is in [0, 1] due to the clamp operation.

Requirements:
    - torch>=2.0.0 (optional dependency, install with 'pip install mlsdm[neurolang]')
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

import numpy as np

# Check if torch is available without importing it
TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None

if TYPE_CHECKING:
    import torch

if not TORCH_AVAILABLE:
    _IMPORT_ERROR_MSG = (
        "FractalPELMGPU requires PyTorch. "
        "Install with 'pip install mlsdm[neurolang]' or 'pip install torch>=2.0.0'."
    )
else:
    _IMPORT_ERROR_MSG = ""

# Numerical stability constant
_EPS = 1e-12


class FractalPELMGPU:
    """Experimental GPU/CPU backend for phase-aware memory retrieval.

    This class provides batch operations for storing and retrieving vectors
    with associated phase values. It uses GPU acceleration when available
    and supports automatic mixed precision (AMP) for improved performance.

    This is a standalone experimental module, not integrated with the core
    MLSDM pipeline. Use for benchmarking and research purposes.

    Scoring formula:
        score = cos_sim * phase_sim * distance_factor
        where:
        - cos_sim = (q · v) / (||q|| * ||v|| + ε)
        - phase_sim = exp(-|φ_q - φ_v|)
        - distance_factor = clamp(1 - fractal_weight * log1p(||q - v||), 0, 1)

    Attributes:
        dimension: Embedding vector dimension.
        capacity: Maximum number of vectors that can be stored.
        size: Current number of stored vectors.
        fractal_weight: Engineering hyperparameter controlling distance influence.
            Higher values penalize distant vectors more strongly.
        use_amp: Whether automatic mixed precision is enabled.

    Example:
        >>> import numpy as np
        >>> from mlsdm.memory.experimental import FractalPELMGPU
        >>> memory = FractalPELMGPU(dimension=16, capacity=1000, device="cpu")
        >>> vectors = np.random.randn(50, 16).astype(np.float32)
        >>> phases = np.random.rand(50).astype(np.float32)
        >>> memory.batch_entangle(vectors, phases)
        >>> results = memory.retrieve(vectors[0], current_phase=phases[0], top_k=5)
        >>> # results: [(score, vector_np, metadata), ...]
    """

    def __init__(
        self,
        dimension: int = 384,
        capacity: int = 100_000,
        device: str | None = None,
        use_amp: bool = True,
        fractal_weight: float = 0.3,
    ) -> None:
        """Initialize FractalPELMGPU memory.

        Args:
            dimension: Embedding vector dimension. Must be positive.
            capacity: Maximum number of vectors to store. Must be positive.
            device: PyTorch device string ('cuda', 'cpu', or None for auto-detect).
                If None, uses CUDA if available, otherwise CPU.
            use_amp: Enable automatic mixed precision for GPU operations.
                Only effective on CUDA devices. Ignored on CPU.
            fractal_weight: Engineering hyperparameter controlling distance influence
                in scoring. Must be in [0.0, 1.0]. Default 0.3.

        Raises:
            RuntimeError: If PyTorch is not installed.
            ValueError: If dimension <= 0 or capacity <= 0.
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError(_IMPORT_ERROR_MSG)

        # Import torch at runtime when needed
        import torch as _torch

        # Validate inputs
        if dimension <= 0:
            raise ValueError(f"dimension must be positive, got {dimension}")
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")

        self.dimension = dimension
        self.capacity = capacity
        self.fractal_weight = float(fractal_weight)
        self.use_amp = use_amp

        # Determine device
        if device is None:
            self._device = _torch.device("cuda" if _torch.cuda.is_available() else "cpu")
        else:
            self._device = _torch.device(device)

        # AMP is only effective on CUDA
        self._amp_enabled = self.use_amp and self._device.type == "cuda"

        # Initialize storage tensors
        # Vectors stored in float16 for memory efficiency
        self._vectors = _torch.zeros(
            (capacity, dimension), dtype=_torch.float16, device=self._device
        )
        # Phases stored in float32 for precision
        self._phases = _torch.zeros(capacity, dtype=_torch.float32, device=self._device)
        # Norms stored separately in float32 for cosine similarity computation
        self._norms = _torch.zeros(capacity, dtype=_torch.float32, device=self._device)
        # Metadata list
        self._metadata: list[dict | None] = [None] * capacity

        # Current size (no ring buffer - strict capacity enforcement)
        self.size: int = 0

    @property
    def device(self) -> str:
        """Return the device string."""
        return str(self._device)

    def _to_tensor(
        self, data: np.ndarray | torch.Tensor, dtype: torch.dtype | None = None
    ) -> torch.Tensor:
        """Convert numpy array or tensor to device tensor with specified dtype."""
        import torch as _torch

        if dtype is None:
            dtype = _torch.float32

        if isinstance(data, np.ndarray):
            tensor = _torch.from_numpy(np.ascontiguousarray(data))
        else:
            tensor = data.clone()
        return tensor.to(device=self._device, dtype=dtype)

    def _score_single(
        self,
        query_vec: torch.Tensor,
        query_phase: float,
    ) -> torch.Tensor:
        """Compute retrieval scores for a single query against stored vectors.

        Scoring formula:
            score = cos_sim * phase_sim * distance_factor

        Where:
            - cos_sim = (q · v) / (||q|| * ||v|| + ε)
            - phase_sim = exp(-|φ_q - φ_v|)
            - distance_factor = clamp(1 - fractal_weight * log1p(||q - v||), 0, 1)

        Args:
            query_vec: Query vector tensor of shape (dimension,), float32.
            query_phase: Query phase value.

        Returns:
            Score tensor of shape (size,) with values in [0, 1].
        """
        import torch as _torch

        if self.size == 0:
            return _torch.tensor([], device=self._device, dtype=_torch.float32)

        # Get active portion of storage
        active_vectors = self._vectors[: self.size].float()  # (size, dim) -> float32
        active_phases = self._phases[: self.size]  # (size,)
        active_norms = self._norms[: self.size]  # (size,)

        # Query norm with numerical stability
        query_norm = _torch.clamp(_torch.norm(query_vec), min=_EPS)

        # Cosine similarity: (q · v) / (||q|| * ||v|| + ε)
        dot_products = _torch.mv(active_vectors, query_vec)  # (size,)
        cos_sim = dot_products / (query_norm * active_norms + _EPS)

        # Phase similarity: exp(-|φ_q - φ_v|)
        phase_diff = _torch.abs(active_phases - query_phase)
        phase_sim = _torch.exp(-phase_diff)

        # Distance term: log1p(||q - v||)
        # Compute L2 distances: ||q - v_i||
        diff = active_vectors - query_vec.unsqueeze(0)  # (size, dim)
        distances = _torch.norm(diff, dim=1)  # (size,)
        log_dist = _torch.log1p(distances)

        # Distance factor: clamp(1 - fractal_weight * log1p(dist), 0, 1)
        distance_factor = _torch.clamp(1.0 - self.fractal_weight * log_dist, min=0.0, max=1.0)

        # Combined score: cos_sim * phase_sim * distance_factor
        # Clamp final result to [0, 1]
        scores = _torch.clamp(cos_sim * phase_sim * distance_factor, min=0.0, max=1.0)

        return scores

    def batch_entangle(
        self,
        vectors: np.ndarray | torch.Tensor,
        phases: np.ndarray | torch.Tensor,
        metadatas: list[dict | None] | None = None,
    ) -> None:
        """Store a batch of vectors with associated phases in memory.

        Args:
            vectors: Batch of embedding vectors with shape (N, dimension).
                Can be numpy array or torch tensor.
            phases: Phase values for each vector with shape (N,).
                Values should be in [0.0, 1.0].
                Can be numpy array or torch tensor.
            metadatas: Optional list of metadata dicts for each vector.
                If provided, must have length N. None entries are allowed.

        Raises:
            ValueError: If shapes don't match or dimensions are incorrect.
            RuntimeError: If adding this batch would exceed capacity.
        """
        import torch as _torch

        vec_tensor = self._to_tensor(vectors, dtype=_torch.float32)
        phase_tensor = self._to_tensor(phases, dtype=_torch.float32)

        # Validate shapes
        if vec_tensor.dim() != 2:
            raise ValueError(f"vectors must be 2D, got shape {tuple(vec_tensor.shape)}")
        if vec_tensor.shape[1] != self.dimension:
            raise ValueError(
                f"vector dimension mismatch: expected {self.dimension}, "
                f"got {vec_tensor.shape[1]}"
            )
        if phase_tensor.dim() != 1:
            raise ValueError(f"phases must be 1D, got shape {tuple(phase_tensor.shape)}")
        if vec_tensor.shape[0] != phase_tensor.shape[0]:
            raise ValueError(
                f"vectors and phases batch size mismatch: "
                f"{vec_tensor.shape[0]} vs {phase_tensor.shape[0]}"
            )

        batch_size = vec_tensor.shape[0]

        # Check capacity - no ring buffer, strict enforcement
        if self.size + batch_size > self.capacity:
            raise RuntimeError(
                f"Cannot add {batch_size} vectors: would exceed capacity. "
                f"Current size: {self.size}, capacity: {self.capacity}. "
                f"Call reset() to clear memory or increase capacity."
            )

        if metadatas is not None and len(metadatas) != batch_size:
            raise ValueError(
                f"metadatas length mismatch: expected {batch_size}, got {len(metadatas)}"
            )

        # Compute norms for each vector
        norms = _torch.norm(vec_tensor, dim=1)  # (batch,)
        # Clamp norms to avoid division by zero
        norms = _torch.clamp(norms, min=_EPS)

        # Store vectors (converted to float16), phases, and norms
        start_idx = self.size
        end_idx = self.size + batch_size

        self._vectors[start_idx:end_idx] = vec_tensor.half()
        self._phases[start_idx:end_idx] = phase_tensor
        self._norms[start_idx:end_idx] = norms

        # Store metadata
        if metadatas is not None:
            for i, meta in enumerate(metadatas):
                self._metadata[start_idx + i] = meta
        else:
            for i in range(batch_size):
                self._metadata[start_idx + i] = None

        self.size = end_idx

    def retrieve(
        self,
        query_vector: np.ndarray | torch.Tensor,
        current_phase: float,
        top_k: int = 5,
    ) -> list[tuple[float, np.ndarray, dict | None]]:
        """Retrieve top-k vectors most similar to query with phase weighting.

        Args:
            query_vector: Query embedding vector with shape (dimension,) or (1, dimension).
            current_phase: Current phase value in [0.0, 1.0].
            top_k: Number of top results to return.

        Returns:
            List of (score, vector, metadata) tuples sorted by descending score.
            Score is in [0, 1]. Vector is returned as numpy array (float32).
            Metadata is the dict stored with the vector (or None).
            Returns empty list if memory is empty.

        Raises:
            ValueError: If query_vector shape is invalid.
        """
        import torch as _torch

        if self.size == 0:
            return []

        # Convert and validate query vector
        q_tensor = self._to_tensor(query_vector, dtype=_torch.float32)

        # Handle (1, dim) shape
        if q_tensor.dim() == 2 and q_tensor.shape[0] == 1:
            q_tensor = q_tensor.squeeze(0)

        # Validate shape
        if q_tensor.dim() != 1:
            raise ValueError(
                f"query_vector must have shape (dimension,) or (1, dimension), "
                f"got shape {tuple(query_vector.shape)}"
            )
        if q_tensor.shape[0] != self.dimension:
            raise ValueError(
                f"query dimension mismatch: expected {self.dimension}, " f"got {q_tensor.shape[0]}"
            )

        # Use AMP context if enabled
        with _torch.autocast(device_type=self._device.type, enabled=self._amp_enabled):
            scores = self._score_single(q_tensor, current_phase)

        # Get top-k
        effective_k = min(top_k, self.size)
        top_scores, top_indices = _torch.topk(scores, k=effective_k)

        # Convert to numpy and build results
        top_scores_np = top_scores.cpu().numpy()
        top_indices_np = top_indices.cpu().numpy()
        vectors_np = self._vectors[: self.size].float().cpu().numpy()

        results: list[tuple[float, np.ndarray, dict | None]] = []
        for i in range(effective_k):
            idx = int(top_indices_np[i])
            score = float(top_scores_np[i])
            vector = vectors_np[idx].astype(np.float32).copy()
            metadata = self._metadata[idx]
            results.append((score, vector, metadata))

        return results

    def batch_retrieve(
        self,
        query_vectors: np.ndarray | torch.Tensor,
        current_phases: np.ndarray | torch.Tensor,
        top_k: int = 5,
    ) -> list[list[tuple[float, np.ndarray, dict | None]]]:
        """Retrieve top-k vectors for a batch of queries.

        Args:
            query_vectors: Batch of query vectors with shape (B, dimension).
            current_phases: Phase values for each query with shape (B,).
            top_k: Number of top results per query.

        Returns:
            List of B lists, each containing up to top_k (score, vector, metadata)
            tuples sorted by descending score.
            Returns list of empty lists if memory is empty.

        Raises:
            ValueError: If shapes don't match or dimensions are incorrect.
        """
        import torch as _torch

        q_tensor = self._to_tensor(query_vectors, dtype=_torch.float32)
        phase_tensor = self._to_tensor(current_phases, dtype=_torch.float32)

        # Validate shapes
        if q_tensor.dim() != 2:
            raise ValueError(f"query_vectors must be 2D, got shape {tuple(q_tensor.shape)}")
        if q_tensor.shape[1] != self.dimension:
            raise ValueError(
                f"query dimension mismatch: expected {self.dimension}, " f"got {q_tensor.shape[1]}"
            )
        if phase_tensor.dim() != 1:
            raise ValueError(f"current_phases must be 1D, got shape {tuple(phase_tensor.shape)}")
        if q_tensor.shape[0] != phase_tensor.shape[0]:
            raise ValueError(
                f"query_vectors and current_phases batch mismatch: "
                f"{q_tensor.shape[0]} vs {phase_tensor.shape[0]}"
            )

        batch_size = q_tensor.shape[0]

        if self.size == 0:
            return [[] for _ in range(batch_size)]

        # Vectorized batch scoring for GPU parallelization
        with _torch.autocast(device_type=self._device.type, enabled=self._amp_enabled):
            scores = self._score_batch(q_tensor, phase_tensor)  # (batch, size)

        # Get top-k for each query
        effective_k = min(top_k, self.size)
        top_scores, top_indices = _torch.topk(scores, k=effective_k, dim=1)  # (batch, k)

        # Convert to numpy
        top_scores_np = top_scores.cpu().numpy()
        top_indices_np = top_indices.cpu().numpy()
        vectors_np = self._vectors[: self.size].float().cpu().numpy()

        # Build results
        all_results: list[list[tuple[float, np.ndarray, dict | None]]] = []
        for b in range(batch_size):
            query_results: list[tuple[float, np.ndarray, dict | None]] = []
            for k in range(effective_k):
                idx = int(top_indices_np[b, k])
                score = float(top_scores_np[b, k])
                vector = vectors_np[idx].astype(np.float32).copy()
                metadata = self._metadata[idx]
                query_results.append((score, vector, metadata))
            all_results.append(query_results)

        return all_results

    def _score_batch(
        self,
        query_vecs: torch.Tensor,
        query_phases: torch.Tensor,
    ) -> torch.Tensor:
        """Compute retrieval scores for a batch of queries against stored vectors.

        Vectorized implementation for GPU parallelization.

        Args:
            query_vecs: Query vectors tensor of shape (batch, dimension), float32.
            query_phases: Query phase values tensor of shape (batch,), float32.

        Returns:
            Score tensor of shape (batch, size) with values in [0, 1].
        """
        import torch as _torch

        batch_size = query_vecs.shape[0]

        if self.size == 0:
            return _torch.zeros((batch_size, 0), device=self._device, dtype=_torch.float32)

        # Get active portion of storage
        active_vectors = self._vectors[: self.size].float()  # (size, dim)
        active_phases = self._phases[: self.size]  # (size,)
        active_norms = self._norms[: self.size]  # (size,)

        # Query norms with numerical stability: (batch,)
        query_norms = _torch.clamp(_torch.norm(query_vecs, dim=1), min=_EPS)

        # Cosine similarity: (batch, dim) @ (dim, size) -> (batch, size)
        dot_products = _torch.mm(query_vecs, active_vectors.t())
        # Outer product of norms: (batch, 1) * (1, size) -> (batch, size)
        norm_products = query_norms.unsqueeze(1) * active_norms.unsqueeze(0) + _EPS
        cos_sim = dot_products / norm_products

        # Phase similarity: exp(-|φ_q - φ_v|)
        # (batch, 1) - (1, size) -> (batch, size)
        phase_diff = _torch.abs(query_phases.unsqueeze(1) - active_phases.unsqueeze(0))
        phase_sim = _torch.exp(-phase_diff)

        # Distance term: log1p(||q - v||) using cdist for efficiency
        # cdist computes pairwise distances: (batch, dim), (size, dim) -> (batch, size)
        distances = _torch.cdist(query_vecs, active_vectors, p=2.0)
        log_dist = _torch.log1p(distances)

        # Distance factor: clamp(1 - fractal_weight * log1p(dist), 0, 1)
        distance_factor = _torch.clamp(1.0 - self.fractal_weight * log_dist, min=0.0, max=1.0)

        # Combined score: cos_sim * phase_sim * distance_factor
        scores = _torch.clamp(cos_sim * phase_sim * distance_factor, min=0.0, max=1.0)

        return scores

    def reset(self) -> None:
        """Clear all stored vectors and reset memory state.

        Note: This does not reallocate tensors, just resets size to 0.
        Capacity remains unchanged.
        """
        # Just reset size - tensors are reused
        self.size = 0
        # Clear metadata references
        self._metadata = [None] * self.capacity

    def get_state_stats(self) -> dict[str, int | float | str | bool]:
        """Return statistics about current memory state.

        Returns:
            Dictionary with capacity, used count, device, and memory usage.
        """
        memory_bytes = (
            self._vectors.numel() * self._vectors.element_size()
            + self._phases.numel() * self._phases.element_size()
            + self._norms.numel() * self._norms.element_size()
        )
        return {
            "capacity": self.capacity,
            "used": self.size,
            "device": str(self._device),
            "memory_mb": round(memory_bytes / (1024 * 1024), 2),
            "amp_enabled": self._amp_enabled,
            "fractal_weight": self.fractal_weight,
        }

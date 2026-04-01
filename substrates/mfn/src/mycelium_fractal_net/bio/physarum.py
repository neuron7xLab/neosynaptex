"""Physarum polycephalum adaptive conductivity model.

Ref: Tero et al. (2007) J. Theor. Biol. 244:553-564
     Tero et al. (2010) Science 327:439-442

Core equations:
    Q_ij = D_ij * (p_i - p_j)                   [flux]
    sum_j D_ij * (p_i - p_j) = b_i              [Kirchhoff]
    dD_ij/dt = |Q_ij|^gamma - alpha * D_ij      [adaptation]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse.linalg import cg

__all__ = ["PhysarumConfig", "PhysarumEngine", "PhysarumState"]

DEFAULT_GAMMA = 1.0
DEFAULT_ALPHA = 0.01
DEFAULT_MU = 1.8
DEFAULT_I0 = 1.0


@dataclass(frozen=True)
class PhysarumConfig:
    """Physarum adaptive conductivity parameters (Tero et al. 2007)."""

    gamma: float = DEFAULT_GAMMA
    alpha: float = DEFAULT_ALPHA
    mu: float = DEFAULT_MU
    use_sigmoid: bool = False
    dt: float = 0.01
    pressure_solver: str = "exact"
    n_pressure_iters: int = 20


@dataclass
class PhysarumState:
    """Physarum network state: conductivity, pressure, and flux fields."""

    D_h: np.ndarray
    D_v: np.ndarray
    p: np.ndarray
    Q_h: np.ndarray
    Q_v: np.ndarray
    u_h: np.ndarray
    u_v: np.ndarray
    step_count: int = 0

    def conductivity_map(self) -> np.ndarray:
        """Conductivity map."""
        N = self.D_h.shape[0]
        c = np.zeros((N, N))
        c[:, :-1] += self.D_h
        c[:, 1:] += self.D_h
        c[:-1, :] += self.D_v
        c[1:, :] += self.D_v
        return c / 4.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "conductivity_mean": float(np.mean(self.D_h) + np.mean(self.D_v)) / 2,
            "conductivity_max": float(max(np.max(self.D_h), np.max(self.D_v))),
            "pressure_range": float(np.max(self.p) - np.min(self.p)),
            "flux_max": float(max(np.max(np.abs(self.Q_h)), np.max(np.abs(self.Q_v)))),
            "step_count": self.step_count,
        }


class PhysarumEngine:
    """Physarum polycephalum adaptive transport network solver."""

    def __init__(self, N: int, config: PhysarumConfig | None = None) -> None:
        self.N = N
        self.config = config or PhysarumConfig()
        # Precompute sparse Laplacian structure (indices never change, only data)
        self._rows, self._cols, self._edge_map = self._precompute_structure()

    def _precompute_structure(
        self,
    ) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int, int, int, str]]]:
        """Build row/col index arrays for the graph Laplacian once."""
        N = self.N
        rows_list: list[int] = []
        cols_list: list[int] = []
        # edge_map: (row_idx_in_data, node1, node2, grid_i, grid_j, direction)
        edge_map: list[tuple[int, int, int, int, str]] = []

        for i in range(N):
            for j in range(N):
                node = i * N + j
                if j < N - 1:
                    nb = i * N + j + 1
                    # 4 entries per horizontal edge: diag+, off-, diag+, off-
                    rows_list.extend([node, node, nb, nb])
                    cols_list.extend([node, nb, nb, node])
                    edge_map.append((i, j, node, nb, "h"))
                if i < N - 1:
                    nb = (i + 1) * N + j
                    rows_list.extend([node, node, nb, nb])
                    cols_list.extend([node, nb, nb, node])
                    edge_map.append((i, j, node, nb, "v"))

        return np.array(rows_list, dtype=np.int32), np.array(cols_list, dtype=np.int32), edge_map

    def initialize(
        self,
        source_mask: np.ndarray,
        sink_mask: np.ndarray,
        rng: np.random.Generator | None = None,
    ) -> PhysarumState:
        """Initialize state from input field."""
        N = self.N
        D_h = np.ones((N, N - 1), dtype=np.float64)
        D_v = np.ones((N - 1, N), dtype=np.float64)
        p = np.zeros((N, N), dtype=np.float64)
        Q_h = np.zeros((N, N - 1), dtype=np.float64)
        Q_v = np.zeros((N - 1, N), dtype=np.float64)
        state = PhysarumState(
            D_h=D_h,
            D_v=D_v,
            p=p,
            Q_h=Q_h,
            Q_v=Q_v,
            u_h=Q_h.copy(),
            u_v=Q_v.copy(),
        )
        b = self._build_source_vector(source_mask, sink_mask)
        state = self._solve_pressure(state, b)
        state = self._compute_flux(state)
        return state

    def step(
        self,
        state: PhysarumState,
        source_mask: np.ndarray,
        sink_mask: np.ndarray,
    ) -> PhysarumState:
        """Advance one timestep."""
        b = self._build_source_vector(source_mask, sink_mask)
        cfg = self.config
        if cfg.use_sigmoid:
            f_h = np.abs(state.Q_h) ** cfg.mu / (1.0 + np.abs(state.Q_h) ** cfg.mu)
            f_v = np.abs(state.Q_v) ** cfg.mu / (1.0 + np.abs(state.Q_v) ** cfg.mu)
        else:
            f_h = np.abs(state.Q_h) ** cfg.gamma
            f_v = np.abs(state.Q_v) ** cfg.gamma
        D_h_new = np.clip(state.D_h + cfg.dt * (f_h - cfg.alpha * state.D_h), 1e-8, None)
        D_v_new = np.clip(state.D_v + cfg.dt * (f_v - cfg.alpha * state.D_v), 1e-8, None)
        new_state = PhysarumState(
            D_h=D_h_new,
            D_v=D_v_new,
            p=state.p.copy(),
            Q_h=state.Q_h.copy(),
            Q_v=state.Q_v.copy(),
            u_h=state.u_h.copy(),
            u_v=state.u_v.copy(),
            step_count=state.step_count + 1,
        )
        new_state = self._solve_pressure(new_state, b)
        new_state = self._compute_flux(new_state)
        return new_state

    def _build_source_vector(
        self,
        source_mask: np.ndarray,
        sink_mask: np.ndarray,
    ) -> np.ndarray:
        N = self.N
        b = np.zeros(N * N, dtype=np.float64)
        src_idx = np.where(source_mask.ravel())[0]
        snk_idx = np.where(sink_mask.ravel())[0]
        if len(src_idx) > 0:
            b[src_idx] = DEFAULT_I0 / max(len(src_idx), 1)
        if len(snk_idx) > 0:
            b[snk_idx] = -DEFAULT_I0 / max(len(snk_idx), 1)
        b -= b.mean()
        return b

    def _solve_pressure(self, state: PhysarumState, b: np.ndarray) -> PhysarumState:
        if self.config.pressure_solver == "jacobi":
            return self._solve_pressure_jacobi(state, b)
        return self._solve_pressure_exact(state, b)

    def _solve_pressure_jacobi(self, state: PhysarumState, b: np.ndarray) -> PhysarumState:
        """Jacobi iterative pressure solver — finite propagation speed.

        Real Physarum polycephalum doesn't solve a global linear system.
        Shuttle streaming propagates pressure at finite speed via local
        peristaltic contractions. Jacobi iteration with limited steps
        approximates this: pressure information travels ~n_iters cells
        per timestep.
        """
        N = self.N
        b_2d = b.reshape(N, N)
        p = state.p.copy()
        D_h, D_v = state.D_h, state.D_v  # (N, N-1) and (N-1, N)

        for _ in range(self.config.n_pressure_iters):
            num = np.zeros((N, N), dtype=np.float64)
            denom = np.zeros((N, N), dtype=np.float64)

            # Right neighbor: (i,j+1) with conductivity D_h[i,j]
            num[:, :-1] += D_h * p[:, 1:]
            denom[:, :-1] += D_h
            # Left neighbor: (i,j-1) with conductivity D_h[i,j-1]
            num[:, 1:] += D_h * p[:, :-1]
            denom[:, 1:] += D_h
            # Down neighbor: (i+1,j) with conductivity D_v[i,j]
            num[:-1, :] += D_v * p[1:, :]
            denom[:-1, :] += D_v
            # Up neighbor: (i-1,j) with conductivity D_v[i-1,j]
            num[1:, :] += D_v * p[:-1, :]
            denom[1:, :] += D_v

            num += b_2d
            safe_denom = np.maximum(denom, 1e-12)
            p = num / safe_denom
            p[0, 0] = 0.0  # Reference pressure

        state.p = p
        return state

    def _solve_pressure_exact(self, state: PhysarumState, b: np.ndarray) -> PhysarumState:
        """Exact pressure solver via LU decomposition or CG."""
        from scipy.sparse import csr_matrix

        N = self.N
        n_nodes = N * N

        data = np.zeros(len(self._rows), dtype=np.float64)
        for idx, (i, j, _node, _nb, direction) in enumerate(self._edge_map):
            d = state.D_h[i, j] if direction == "h" else state.D_v[i, j]
            base = idx * 4
            data[base] = d
            data[base + 1] = -d
            data[base + 2] = d
            data[base + 3] = -d

        L = csr_matrix((data, (self._rows, self._cols)), shape=(n_nodes, n_nodes))
        L = L.tolil()
        L[0, :] = 0
        L[0, 0] = 1.0
        L_csr = L.tocsr()

        b_fixed = b.copy()
        b_fixed[0] = 0.0

        if N <= 32:
            from scipy.sparse.linalg import splu

            try:
                lu = splu(L_csr.tocsc())
                p_flat = lu.solve(b_fixed)
            except Exception:
                p_flat, _ = cg(L_csr, b_fixed, x0=state.p.ravel(), atol=1e-8, maxiter=500)
        else:
            p_flat, _ = cg(L_csr, b_fixed, x0=state.p.ravel(), atol=1e-8, maxiter=500)

        state.p = p_flat.reshape(N, N)
        return state

    def _compute_flux(self, state: PhysarumState) -> PhysarumState:
        p = state.p
        state.Q_h = state.D_h * (p[:, :-1] - p[:, 1:])
        state.Q_v = state.D_v * (p[:-1, :] - p[1:, :])
        state.u_h = state.Q_h / np.clip(state.D_h, 1e-12, None)
        state.u_v = state.Q_v / np.clip(state.D_v, 1e-12, None)
        return state

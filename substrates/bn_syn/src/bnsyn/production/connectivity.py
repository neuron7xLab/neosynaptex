"""Deterministic connectivity builders for BN-Syn experiments.

Parameters
----------
None

Returns
-------
None

Notes
-----
Determinism is controlled by explicit NumPy generators.

References
----------
docs/SPEC.md#P2-11
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True, slots=True)
class ConnectivityConfig:
    """Connectivity configuration for production helpers.

    Parameters
    ----------
    n_pre : int
        Number of presynaptic neurons.
    n_post : int
        Number of postsynaptic neurons.
    p_connect : float
        Connection probability.
    allow_self : bool, optional
        Whether self-connections are permitted.

    Notes
    -----
    Configuration is immutable to preserve deterministic connectivity.
    """

    n_pre: int
    n_post: int
    p_connect: float
    allow_self: bool = False


def build_connectivity(
    cfg: ConnectivityConfig,
    *,
    rng: np.random.Generator,
) -> np.ndarray:
    """Build a boolean adjacency matrix with Bernoulli(p_connect).

    Parameters
    ----------
    cfg : ConnectivityConfig
        Connectivity configuration.
    rng : np.random.Generator
        NumPy Generator for deterministic sampling.

    Returns
    -------
    np.ndarray
        Boolean adjacency matrix (shape: [n_post, n_pre]).

    Raises
    ------
    ValueError
        If configuration values are invalid.

    Notes
    -----
    Pass a managed NumPy Generator to preserve deterministic reproducibility.

    References
    ----------
    docs/SPEC.md#P2-11
    """
    if cfg.n_pre <= 0 or cfg.n_post <= 0:
        raise ValueError("n_pre and n_post must be > 0")
    if not (0.0 <= cfg.p_connect <= 1.0):
        raise ValueError("p_connect must be in [0, 1]")
    adj = rng.random((cfg.n_post, cfg.n_pre)) < cfg.p_connect
    if not cfg.allow_self and cfg.n_pre == cfg.n_post:
        np.fill_diagonal(adj, False)
    return adj

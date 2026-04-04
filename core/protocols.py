"""NFI Protocols — shared type contracts for the entire monorepo.

DomainAdapter is the canonical interface every substrate must implement.
Used by Neosynaptex engine, AdapterRegistry, and CoherenceBridge.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DomainAdapter(Protocol):
    """Interface each NFI subsystem implements.

    Contract:
        - domain:     unique ASCII identifier (max 32 chars)
        - state_keys: list of state variable names (max 4)
        - state():    current state as {key: float} dict
        - topo():     topological complexity measure (> 0)
        - thermo_cost(): thermodynamic cost measure (> 0)

    Power-law invariant: cost ~ topo^(-gamma), gamma derived only.
    """

    @property
    def domain(self) -> str: ...

    @property
    def state_keys(self) -> list[str]: ...

    def state(self) -> dict[str, float]: ...

    def topo(self) -> float: ...

    def thermo_cost(self) -> float: ...


__all__ = ["DomainAdapter"]

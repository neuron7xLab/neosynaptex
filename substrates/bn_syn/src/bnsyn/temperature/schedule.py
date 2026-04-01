"""Temperature scheduling and plasticity gating utilities.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements SPEC P1-5 temperature schedule and gate function.

References
----------
docs/SPEC.md#P1-5
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bnsyn.config import TemperatureParams


def gate_sigmoid(T: float, Tc: float, tau: float) -> float:
    """Compute the plasticity gate sigmoid value.

    Parameters
    ----------
    T : float
        Current temperature (dimensionless).
    Tc : float
        Gate center temperature.
    tau : float
        Gate slope parameter.

    Returns
    -------
    float
        Gate value in [0, 1].

    Notes
    -----
    G(T) = 1 / (1 + exp(-(T - Tc) / tau)).

    References
    ----------
    docs/SPEC.md#P1-5
    docs/SSOT.md
    """
    return float(1.0 / (1.0 + np.exp(-(float(T) - float(Tc)) / float(tau))))


@dataclass
class TemperatureSchedule:
    """Track geometric temperature schedule and plasticity gate.

    Parameters
    ----------
    params : TemperatureParams
        Temperature schedule parameters.
    T : float | None, optional
        Optional initial temperature (defaults to params.T0).

    Notes
    -----
    Temperature state is mutated deterministically across steps.

    References
    ----------
    docs/SPEC.md#P1-5
    docs/SSOT.md
    """

    params: TemperatureParams
    T: float | None = None

    def __post_init__(self) -> None:
        if self.T is None:
            self.T = float(self.params.T0)

    def step_geometric(self) -> float:
        """Advance the temperature by one geometric decay step.

        Returns
        -------
        float
            Updated temperature value.

        Notes
        -----
        Applies a multiplicative decay with floor ``Tmin``.
        """
        p = self.params
        temperature = self.T if self.T is not None else float(p.T0)
        self.T = max(float(p.Tmin), float(temperature) * float(p.alpha))
        return float(self.T)

    def plasticity_gate(self) -> float:
        """Compute the plasticity gate value from the current temperature.

        Returns
        -------
        float
            Gate value in [0, 1].

        Notes
        -----
        Uses the logistic gate defined in SPEC P1-5.
        """
        p = self.params
        temperature = self.T if self.T is not None else float(p.T0)
        return gate_sigmoid(float(temperature), float(p.Tc), float(p.gate_tau))

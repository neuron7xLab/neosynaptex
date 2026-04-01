"""Helper to convert a TEResult into a proof-artifact-friendly dict."""

from __future__ import annotations

from .transfer_entropy import TEResult


def te_to_flow_graph(result: TEResult) -> dict[str, object]:
    """Produce a flat dict representation of transfer entropy results.

    Parameters
    ----------
    result : TEResult
        Output from ``TransferEntropyEngine.compute()``.

    Returns
    -------
    dict
        Keys: E_to_I, I_to_E, net_flow, E_to_I_significant, I_to_E_significant.
    """
    return {
        "E_to_I": result.te_e_to_i,
        "I_to_E": result.te_i_to_e,
        "net_flow": result.te_net,
        "E_to_I_significant": result.p_value_e_to_i < 0.05,
        "I_to_E_significant": result.p_value_i_to_e < 0.05,
    }

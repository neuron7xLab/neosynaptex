"""Tests for the info_flow_graph helper."""

from __future__ import annotations

from bnsyn.causality.info_flow_graph import te_to_flow_graph
from bnsyn.causality.transfer_entropy import TEResult


class TestInfoFlowGraph:
    """Verify te_to_flow_graph produces correct keys and values."""

    def test_correct_keys_and_values(self) -> None:
        result = TEResult(
            te_e_to_i=0.15,
            te_i_to_e=0.03,
            te_net=0.12,
            p_value_e_to_i=0.01,
            p_value_i_to_e=0.30,
            timestamp_step=500,
        )
        graph = te_to_flow_graph(result)

        assert set(graph.keys()) == {
            "E_to_I",
            "I_to_E",
            "net_flow",
            "E_to_I_significant",
            "I_to_E_significant",
        }
        assert graph["E_to_I"] == 0.15
        assert graph["I_to_E"] == 0.03
        assert graph["net_flow"] == 0.12
        assert graph["E_to_I_significant"] is True
        assert graph["I_to_E_significant"] is False

    def test_borderline_significance(self) -> None:
        """p-value exactly at 0.05 should NOT be significant (strict <)."""
        result = TEResult(
            te_e_to_i=0.10,
            te_i_to_e=0.10,
            te_net=0.0,
            p_value_e_to_i=0.05,
            p_value_i_to_e=0.049,
            timestamp_step=100,
        )
        graph = te_to_flow_graph(result)
        assert graph["E_to_I_significant"] is False
        assert graph["I_to_E_significant"] is True

    def test_zero_te(self) -> None:
        result = TEResult(
            te_e_to_i=0.0,
            te_i_to_e=0.0,
            te_net=0.0,
            p_value_e_to_i=1.0,
            p_value_i_to_e=1.0,
            timestamp_step=0,
        )
        graph = te_to_flow_graph(result)
        assert graph["E_to_I"] == 0.0
        assert graph["I_to_E"] == 0.0
        assert graph["net_flow"] == 0.0
        assert graph["E_to_I_significant"] is False
        assert graph["I_to_E_significant"] is False

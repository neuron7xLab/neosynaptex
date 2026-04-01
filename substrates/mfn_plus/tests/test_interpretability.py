"""Integration tests for MFN Interpretability Engine.

Tests the full pipeline: simulation -> features -> attribution -> diagnostics -> report.
"""

from __future__ import annotations

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.interpretability import (
    AttributionGraph,
    AttributionGraphBuilder,
    CausalTracer,
    FeatureVector,
    GammaDiagnosticReport,
    GammaDiagnostics,
    LinearStateProbe,
    MFNFeatureExtractor,
    MFNInterpretabilityReport,
)


def _make_sequences(n: int = 10, seed_base: int = 42) -> list[mfn.FieldSequence]:
    return [
        mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=seed_base + i))
        for i in range(n)
    ]


def _make_gamma_values(sequences: list[mfn.FieldSequence]) -> list[float]:
    """Synthetic gamma values correlated with field variance."""
    return [
        float(1.0 + 0.5 * np.std(seq.field))
        for seq in sequences
    ]


class TestFeatureExtractor:
    def test_extract_topological(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ex = MFNFeatureExtractor()
        topo = ex.extract_topological_features(seq)
        assert "betti_0" in topo
        assert "persistence_entropy" in topo
        assert all(np.isfinite(v) for v in topo.values())

    def test_extract_fractal(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ex = MFNFeatureExtractor()
        fractal = ex.extract_fractal_features(seq)
        assert "d_box" in fractal
        assert "active_fraction" in fractal
        assert 0.0 <= fractal["active_fraction"] <= 1.0

    def test_extract_causal(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        desc = mfn.extract(seq)
        causal = validate_causal_consistency(seq, descriptor=desc)
        ex = MFNFeatureExtractor()
        features = ex.extract_causal_features(causal)
        assert "total_rules" in features
        assert "causal_ok" in features
        assert features["total_rules"] > 0

    def test_extract_all(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ex = MFNFeatureExtractor()
        fv = ex.extract_all(seq)
        assert isinstance(fv, FeatureVector)
        arr = fv.to_array()
        assert arr.ndim == 1
        assert len(arr) > 0
        assert all(np.isfinite(arr))

    def test_feature_names_match_array(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ex = MFNFeatureExtractor()
        fv = ex.extract_all(seq)
        assert len(fv.feature_names()) == len(fv.to_array())


class TestAttributionGraph:
    def test_build_graph(self) -> None:
        sequences = _make_sequences(8)
        gammas = _make_gamma_values(sequences)

        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq, step=i) for i, seq in enumerate(sequences)]

        builder = AttributionGraphBuilder()
        graph = builder.build(fvs, gammas)

        assert isinstance(graph, AttributionGraph)
        assert graph.gamma_value > 0
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0
        assert len(graph.gamma_attribution) > 0

    def test_top_contributors(self) -> None:
        sequences = _make_sequences(8)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]

        graph = AttributionGraphBuilder().build(fvs, gammas)
        top = graph.top_contributors(3)
        assert len(top) <= 3
        for name, weight in top:
            assert isinstance(name, str)
            assert np.isfinite(weight)

    def test_temporal_graphs(self) -> None:
        sequences = _make_sequences(15)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]

        graphs = AttributionGraphBuilder().build_temporal(fvs, gammas, window=8)
        assert len(graphs) >= 1

    def test_graph_to_dict(self) -> None:
        sequences = _make_sequences(8)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]
        graph = AttributionGraphBuilder().build(fvs, gammas)
        d = graph.to_dict()
        assert "gamma_value" in d
        assert "gamma_attribution" in d
        assert "n_nodes" in d
        assert "n_edges" in d

    def test_causal_path(self) -> None:
        sequences = _make_sequences(8)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]
        graph = AttributionGraphBuilder().build(fvs, gammas)
        if len(graph.nodes) >= 2:
            path = graph.causal_path(graph.nodes[0].node_id, graph.nodes[-1].node_id)
            assert isinstance(path, list)


class TestCausalTracer:
    def test_trace_rules(self) -> None:
        sequences = _make_sequences(5)
        results = [
            validate_causal_consistency(seq, descriptor=mfn.extract(seq))
            for seq in sequences
        ]

        tracer = CausalTracer()
        traces = tracer.trace_rules(results)
        assert len(traces) > 0
        for trace in traces.values():
            assert len(trace.activations) == 5

    def test_find_critical_rules(self) -> None:
        sequences = _make_sequences(8)
        results = [
            validate_causal_consistency(seq, descriptor=mfn.extract(seq))
            for seq in sequences
        ]
        gammas = [1.0 + 0.5 * np.std(seq.field) for seq in sequences]

        tracer = CausalTracer()
        traces = tracer.trace_rules(results)
        critical = tracer.find_critical_rules(traces, gammas, threshold=0.01)
        assert isinstance(critical, list)
        for rule_id in critical:
            assert isinstance(rule_id, str)

    def test_stage_transitions(self) -> None:
        sequences = _make_sequences(5)
        results = [
            validate_causal_consistency(seq, descriptor=mfn.extract(seq))
            for seq in sequences
        ]

        tracer = CausalTracer()
        st = tracer.trace_stage_transitions(results)
        assert len(st.stage_pass_rates) == 5
        assert st.bottleneck_stage != ""
        assert len(st.entropy_profile) == 5

    def test_null_model(self) -> None:
        sequences = _make_sequences(5)
        results = [
            validate_causal_consistency(seq, descriptor=mfn.extract(seq))
            for seq in sequences
        ]

        tracer = CausalTracer()
        traces = tracer.trace_rules(results)
        p_values = tracer.null_model_comparison(traces, n_null=50)
        assert len(p_values) > 0
        for p in p_values.values():
            assert 0.0 <= p <= 1.0


class TestGammaDiagnostics:
    def test_diagnose_healthy(self) -> None:
        sequences = _make_sequences(8)
        gammas = [1.0 + 0.1 * i / 8 for i in range(8)]  # ~ +1.0

        diag = GammaDiagnostics()
        report = diag.diagnose(sequences, gammas)

        assert isinstance(report, GammaDiagnosticReport)
        assert report.gamma_status == "healthy"
        assert report.mechanistic_description != ""

    def test_diagnose_pathological(self) -> None:
        sequences = _make_sequences(8)
        gammas = [-0.5 + 0.1 * i for i in range(8)]  # negative

        diag = GammaDiagnostics()
        report = diag.diagnose(sequences, gammas)

        assert report.gamma_status in ("pathological_low", "critical")
        assert report.deviation_origin != ""

    def test_report_to_dict(self) -> None:
        sequences = _make_sequences(5)
        gammas = [1.1] * 5

        report = GammaDiagnostics().diagnose(sequences, gammas)
        d = report.to_dict()
        assert "gamma_value" in d
        assert "gamma_status" in d
        assert "description" in d


class TestStateProbe:
    def test_probe_single_group(self) -> None:
        sequences = _make_sequences(20, seed_base=0)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]
        labels = [0 if i < 10 else 1 for i in range(20)]

        probe = LinearStateProbe()
        result = probe.fit(fvs, labels, "fractal")
        assert "accuracy" in result
        assert "roc_auc" in result
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_probe_all_groups(self) -> None:
        sequences = _make_sequences(20, seed_base=0)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]
        labels = [0 if i < 10 else 1 for i in range(20)]

        probe = LinearStateProbe()
        results = probe.probe_all_groups(fvs, labels)
        assert "fractal" in results
        assert "all" in results
        assert len(results) == 5


class TestReport:
    def test_generate_report(self) -> None:
        sequences = _make_sequences(8)
        gammas = [1.1] * 8

        diag = GammaDiagnostics()
        report = diag.diagnose(sequences, gammas)

        gen = MFNInterpretabilityReport()
        md = gen.generate(report)
        assert "Executive Summary" in md
        assert "Attribution Analysis" in md
        assert "Mechanistic Hypothesis" in md

    def test_export_for_paper(self) -> None:
        sequences = _make_sequences(5)
        gammas = [1.1] * 5

        report = GammaDiagnostics().diagnose(sequences, gammas)
        gen = MFNInterpretabilityReport()
        data = gen.export_for_paper(report)
        assert "gamma_summary" in data
        assert "top_features" in data

    def test_generate_with_graph_and_traces(self) -> None:
        sequences = _make_sequences(8)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq, step=i) for i, seq in enumerate(sequences)]
        graph = AttributionGraphBuilder().build(fvs, gammas)
        report = GammaDiagnostics().diagnose(sequences, gammas)

        # With causal traces
        results = [
            validate_causal_consistency(seq, descriptor=mfn.extract(seq))
            for seq in sequences
        ]
        tracer = CausalTracer()
        traces = tracer.trace_rules(results)

        # With probe results
        labels = [0 if g < 1.1 else 1 for g in gammas]
        probe_results: dict[str, dict[str, float]] | None = None
        if len(set(labels)) == 2:
            probe_results = LinearStateProbe().probe_all_groups(fvs, labels)

        gen = MFNInterpretabilityReport()
        md = gen.generate(report, graph, traces, probe_results)
        assert len(md) > 200
        assert "Attribution Analysis" in md

    def test_export_with_probes(self) -> None:
        sequences = _make_sequences(20, seed_base=0)
        gammas = _make_gamma_values(sequences)
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq) for seq in sequences]
        labels = [0 if i < 10 else 1 for i in range(20)]
        probe_results = LinearStateProbe().probe_all_groups(fvs, labels)

        report = GammaDiagnostics().diagnose(sequences, gammas)
        gen = MFNInterpretabilityReport()
        data = gen.export_for_paper(report, probe_results)
        assert "gamma_summary" in data
        assert "top_features" in data


class TestFullPipeline:
    def test_full_interpretability_pipeline(self) -> None:
        """Full cycle: simulate -> extract -> attribute -> diagnose -> report."""
        sequences = _make_sequences(10)
        gammas = _make_gamma_values(sequences)

        # Feature extraction
        ex = MFNFeatureExtractor()
        fvs = [ex.extract_all(seq, step=i) for i, seq in enumerate(sequences)]
        assert all(len(fv.to_array()) > 0 for fv in fvs)

        # Attribution graph
        graph = AttributionGraphBuilder().build(fvs, gammas)
        assert len(graph.gamma_attribution) > 0

        # Gamma diagnostics
        report = GammaDiagnostics().diagnose(sequences, gammas)
        assert report.mechanistic_description != ""

        # State probes
        labels = [0 if g < 1.1 else 1 for g in gammas]
        if len(set(labels)) == 2:
            probe_results = LinearStateProbe().probe_all_groups(fvs, labels)
            assert len(probe_results) == 5

        # Report generation
        md = MFNInterpretabilityReport().generate(report, graph)
        assert len(md) > 100

"""Tests for formal.substrate_diversity — universality evidence."""

from __future__ import annotations

from formal.substrate_diversity import DiversityReport, analyze_diversity


class TestSubstrateDiversity:
    def test_report_loads(self) -> None:
        report = analyze_diversity()
        assert isinstance(report, DiversityReport)
        assert report.total_entries >= 8

    def test_validated_count(self) -> None:
        report = analyze_diversity()
        assert report.validated_entries >= 6

    def test_broad_categories_at_least_two(self) -> None:
        report = analyze_diversity()
        assert report.n_broad_categories >= 2

    def test_universality_holds(self) -> None:
        """Core claim: γ ≈ 1.0 across 3+ independent broad categories."""
        report = analyze_diversity()
        assert report.universality_holds is True

    def test_mean_gamma_near_unity(self) -> None:
        report = analyze_diversity()
        assert abs(report.mean_gamma_validated - 1.0) < 0.15

    def test_metastable_fraction_majority(self) -> None:
        """Majority of validated substrates in metastable zone."""
        report = analyze_diversity()
        assert report.metastable_fraction >= 0.5

    def test_no_mock_in_broad_categories(self) -> None:
        report = analyze_diversity()
        assert "MOCK" not in report.broad_categories

    def test_domains_non_empty(self) -> None:
        report = analyze_diversity()
        assert len(report.domains_represented) >= 3

    def test_all_substrates_have_gamma(self) -> None:
        report = analyze_diversity()
        for s in report.all_substrates:
            assert isinstance(s.gamma, (int, float))

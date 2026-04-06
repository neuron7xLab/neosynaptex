"""Tests for core.evidence_hardening — evidence quality audit."""

from __future__ import annotations

from core.evidence_hardening import AuditReport, EntryGrade, audit_ledger


class TestAuditLedger:
    def test_returns_report(self) -> None:
        report = audit_ledger()
        assert isinstance(report, AuditReport)

    def test_has_validated_entries(self) -> None:
        report = audit_ledger()
        assert report.validated_entries >= 6

    def test_all_entries_graded(self) -> None:
        report = audit_ledger()
        assert len(report.grades) == report.total_entries
        for g in report.grades:
            assert isinstance(g, EntryGrade)
            assert g.grade in ("A", "B", "C", "D", "F")

    def test_ess_in_range(self) -> None:
        report = audit_ledger()
        for g in report.grades:
            assert 0.0 <= g.ess <= 1.0

    def test_claim_strength_valid(self) -> None:
        report = audit_ledger()
        assert report.claim_strength in ("STRONG", "MODERATE", "WEAK", "INSUFFICIENT")

    def test_weakest_and_strongest_exist(self) -> None:
        report = audit_ledger()
        assert report.weakest_entry != ""
        assert report.strongest_entry != ""

    def test_recommendations_non_empty(self) -> None:
        """There SHOULD be recommendations — the ledger has known gaps."""
        report = audit_ledger()
        assert len(report.recommendations) > 0

    def test_honest_about_missing_pvalues(self) -> None:
        """Audit should flag missing p-values."""
        report = audit_ledger()
        p_recs = [r for r in report.recommendations if "p-value" in r]
        assert len(p_recs) > 0, "expected recommendations about missing p-values"

    def test_honest_about_missing_hashes(self) -> None:
        """Audit should flag missing SHA-256 hashes."""
        report = audit_ledger()
        hash_recs = [r for r in report.recommendations if "SHA-256" in r or "hash" in r]
        assert len(hash_recs) > 0

    def test_reliable_count_plus_unreliable_equals_validated(self) -> None:
        report = audit_ledger()
        assert report.n_reliable + report.n_unreliable == report.validated_entries

    def test_grade_issues_are_specific(self) -> None:
        """Each issue should name what's missing, not be generic."""
        report = audit_ledger()
        for g in report.grades:
            for issue in g.issues:
                assert len(issue) > 5  # not just "bad"

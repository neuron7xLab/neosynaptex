"""
Tests for CI Performance & Resilience Gate.

This module provides comprehensive tests for the CI gate that determines
merge safety based on PR changes and CI job results.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from ci_perf_resilience_gate import (  # noqa: E402
    ChangeClass,
    CIInspector,
    CIPerfResilienceGate,
    FileChange,
    JobResult,
    JobStatus,
    MergeVerdictor,
    PRAnalyzer,
    RiskClassifier,
    RiskMode,
    parse_pr_url,
)


class TestPRAnalyzer:
    """Test PR analyzer functionality.

    Tests file classification and change analysis logic.
    """

    analyzer: PRAnalyzer

    def setup_method(self) -> None:
        """Set up test fixtures.

        Initializes the PRAnalyzer instance for each test.
        """
        self.analyzer = PRAnalyzer()

    def test_classify_documentation_file(self) -> None:
        """Test classification of documentation files.

        Verifies README.md and docs/ files are classified as DOC_ONLY.
        """
        change = self.analyzer.classify_file("README.md", "")
        assert change.change_class == ChangeClass.DOC_ONLY
        assert "Documentation" in change.reason

        change = self.analyzer.classify_file("docs/guide.md", "")
        assert change.change_class == ChangeClass.DOC_ONLY

    def test_classify_core_critical_path(self) -> None:
        """Test classification of core critical paths.

        Verifies neuro_engine/ and config/ paths are CORE_CRITICAL.
        """
        change = self.analyzer.classify_file("src/mlsdm/neuro_engine/core.py", "")
        assert change.change_class == ChangeClass.CORE_CRITICAL
        assert "critical path" in change.reason.lower()

        change = self.analyzer.classify_file("config/settings.yaml", "")
        assert change.change_class == ChangeClass.CORE_CRITICAL

    def test_classify_core_critical_content(self) -> None:
        """Test classification based on patch content.

        Verifies patches containing async/timeout/circuit_breaker patterns
        are classified as CORE_CRITICAL.
        """
        patch = """
        async def process_request(timeout=5):
            await asyncio.sleep(1)
            return circuit_breaker.call()
        """
        change = self.analyzer.classify_file("src/utils.py", patch)
        assert change.change_class == ChangeClass.CORE_CRITICAL
        assert "critical patterns" in change.reason.lower()

    def test_classify_non_core_code(self) -> None:
        """Test classification of non-core code.

        Verifies utility files are classified as NON_CORE_CODE.
        """
        change = self.analyzer.classify_file("src/mlsdm/utils/helpers.py", "")
        assert change.change_class == ChangeClass.NON_CORE_CODE
        assert "non-critical" in change.reason.lower()

    def test_analyze_changes(self) -> None:
        """Test analyzing multiple file changes.

        Verifies analyze_changes correctly classifies multiple files.
        """
        files = [
            {"filename": "README.md", "patch": ""},
            {"filename": "src/mlsdm/neuro_engine/main.py", "patch": ""},
            {"filename": "src/utils.py", "patch": ""},
        ]
        changes = self.analyzer.analyze_changes(files)
        assert len(changes) == 3
        assert changes[0].change_class == ChangeClass.DOC_ONLY
        assert changes[1].change_class == ChangeClass.CORE_CRITICAL

    def test_classify_scripts_directory(self) -> None:
        """Test classification of scripts directory as critical.

        Verifies scripts/ files are classified as CORE_CRITICAL.
        """
        change = self.analyzer.classify_file("scripts/run_effectiveness_suite.py", "")
        assert change.change_class == ChangeClass.CORE_CRITICAL
        assert "critical path" in change.reason.lower()

    def test_classify_benchmarks_directory(self) -> None:
        """Test classification of benchmarks directory as critical.

        Verifies benchmarks/ files are classified as CORE_CRITICAL.
        """
        change = self.analyzer.classify_file("benchmarks/test_neuro_engine_performance.py", "")
        assert change.change_class == ChangeClass.CORE_CRITICAL
        assert "critical path" in change.reason.lower()


class TestCIInspector:
    """Test CI inspector functionality.

    Tests job status mapping and key fact extraction.
    """

    inspector: CIInspector

    def setup_method(self) -> None:
        """Set up test fixtures.

        Initializes the CIInspector instance for each test.
        """
        self.inspector = CIInspector()

    def test_map_job_status_success(self) -> None:
        """Test mapping successful job status.

        Verifies 'success' conclusion maps to JobStatus.SUCCESS.
        """
        status = self.inspector.map_job_status("success", "completed")
        assert status == JobStatus.SUCCESS

    def test_map_job_status_failure(self) -> None:
        """Test mapping failed job status.

        Verifies 'failure' conclusion maps to JobStatus.FAILURE.
        """
        status = self.inspector.map_job_status("failure", "completed")
        assert status == JobStatus.FAILURE

    def test_map_job_status_skipped(self) -> None:
        """Test mapping skipped job status.

        Verifies 'skipped' conclusion or status maps to JobStatus.SKIPPED.
        """
        status = self.inspector.map_job_status("skipped", "completed")
        assert status == JobStatus.SKIPPED

        status = self.inspector.map_job_status(None, "skipped")
        assert status == JobStatus.SKIPPED

    def test_map_job_status_pending(self) -> None:
        """Test mapping pending job status.

        Verifies 'in_progress' status maps to JobStatus.PENDING.
        """
        status = self.inspector.map_job_status(None, "in_progress")
        assert status == JobStatus.PENDING

    def test_extract_key_facts_success(self) -> None:
        """Test extracting key facts from successful job.

        Verifies duration and pass status are extracted.
        """
        job: dict[str, Any] = {
            "name": "Test Job",
            "conclusion": "success",
            "status": "completed",
            "started_at": "2025-01-01T00:00:00Z",
            "completed_at": "2025-01-01T00:05:00Z",
        }
        facts = self.inspector._extract_key_facts(job, JobStatus.SUCCESS)
        assert "Passed" in facts
        assert "5m0s" in facts

    def test_extract_key_facts_failure(self) -> None:
        """Test extracting key facts from failed job.

        Verifies failed step is identified in key facts.
        """
        job: dict[str, Any] = {
            "name": "Test Job",
            "conclusion": "failure",
            "status": "completed",
            "steps": [
                {"name": "Setup", "conclusion": "success"},
                {"name": "Test", "conclusion": "failure"},
            ],
        }
        facts = self.inspector._extract_key_facts(job, JobStatus.FAILURE)
        assert "Failed" in facts
        assert "Test" in facts


class TestRiskClassifier:
    """Test risk classifier functionality.

    Tests risk mode classification based on changes and labels.
    """

    classifier: RiskClassifier

    def setup_method(self) -> None:
        """Set up test fixtures.

        Initializes the RiskClassifier instance for each test.
        """
        self.classifier = RiskClassifier()

    def test_classify_green_light_doc_only(self) -> None:
        """Test green light classification for doc-only changes.

        Verifies documentation-only PRs get GREEN_LIGHT mode.
        """
        changes = [
            FileChange("README.md", ChangeClass.DOC_ONLY, "Doc file"),
            FileChange("docs/guide.md", ChangeClass.DOC_ONLY, "Doc file"),
        ]
        mode, reasons = self.classifier.classify(changes, [], [])
        assert mode == RiskMode.GREEN_LIGHT
        assert any("documentation-only" in r.lower() for r in reasons)

    def test_classify_green_light_non_core(self) -> None:
        """Test green light classification for non-core changes.

        Verifies non-critical code changes get GREEN_LIGHT mode.
        """
        changes = [
            FileChange("src/utils.py", ChangeClass.NON_CORE_CODE, "Utility"),
            FileChange("tests/test_util.py", ChangeClass.NON_CORE_CODE, "Test"),
        ]
        mode, reasons = self.classifier.classify(changes, [], [])
        assert mode == RiskMode.GREEN_LIGHT
        assert any("no core critical" in r.lower() for r in reasons)

    def test_classify_yellow_moderate_critical(self) -> None:
        """Test yellow classification for moderate critical changes.

        Verifies moderate number of critical changes get YELLOW mode.
        """
        changes = [
            FileChange("src/mlsdm/neuro_engine/core.py", ChangeClass.CORE_CRITICAL, "Critical"),
            FileChange("src/utils.py", ChangeClass.NON_CORE_CODE, "Utility"),
        ]
        mode, reasons = self.classifier.classify(changes, [], [])
        assert mode == RiskMode.YELLOW_CRITICAL_PATH
        assert any("moderate" in r.lower() for r in reasons)

    def test_classify_red_many_critical(self) -> None:
        """Test red classification for many critical changes.

        Verifies high number of critical changes get RED mode.
        """
        changes = [
            FileChange(f"src/core{i}.py", ChangeClass.CORE_CRITICAL, "Critical") for i in range(15)
        ]
        mode, reasons = self.classifier.classify(changes, [], [])
        assert mode == RiskMode.RED_HIGH_RISK_OR_RELEASE
        assert any("high number" in r.lower() for r in reasons)

    def test_classify_red_release_label(self) -> None:
        """Test red classification for release label.

        Verifies PRs with 'release' label get RED mode.
        """
        changes = [
            FileChange("src/core.py", ChangeClass.CORE_CRITICAL, "Critical"),
        ]
        mode, reasons = self.classifier.classify(changes, [], ["release"])
        assert mode == RiskMode.RED_HIGH_RISK_OR_RELEASE
        assert any("release" in r.lower() for r in reasons)


class TestMergeVerdictor:
    """Test merge verdictor functionality.

    Tests merge verdict determination based on risk mode and job results.
    """

    verdictor: MergeVerdictor

    def setup_method(self) -> None:
        """Set up test fixtures.

        Initializes the MergeVerdictor instance for each test.
        """
        self.verdictor = MergeVerdictor()

    def test_verdict_green_light_safe(self) -> None:
        """Test safe verdict for green light mode.

        Verifies all-passing jobs in GREEN_LIGHT mode allow merge.
        """
        job_results = [
            JobResult("CI / Lint", JobStatus.SUCCESS, "Passed"),
            JobResult("CI / Tests", JobStatus.SUCCESS, "Passed"),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.GREEN_LIGHT, job_results
        )
        assert verdict == "SAFE_TO_MERGE_NOW"
        assert len(actions) == 0
        assert any("low-risk" in r.lower() for r in reasons)

    def test_verdict_green_light_base_failure(self) -> None:
        """Test do not merge for green light with base job failure.

        Verifies base CI failures block merge even in GREEN_LIGHT mode.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.FAILURE, "Failed"),
            JobResult("CI / Tests", JobStatus.SUCCESS, "Passed"),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.GREEN_LIGHT, job_results
        )
        assert verdict == "DO_NOT_MERGE_YET"
        assert len(actions) > 0
        assert any("base ci jobs failed" in r.lower() for r in reasons)

    def test_verdict_yellow_tests_passed(self) -> None:
        """Test safe verdict for yellow mode with tests passed.

        Verifies passing perf/resilience tests allow merge in YELLOW mode.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed"),
            JobResult(
                "Performance & Resilience Validation / Fast Resilience Tests",
                JobStatus.SUCCESS,
                "Passed",
            ),
            JobResult(
                "Performance & Resilience Validation / Performance & SLO Validation",
                JobStatus.SUCCESS,
                "Passed",
            ),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.YELLOW_CRITICAL_PATH, job_results
        )
        assert verdict == "SAFE_TO_MERGE_NOW"
        assert len(actions) == 0
        assert any("passed" in r.lower() for r in reasons)

    def test_verdict_yellow_tests_skipped(self) -> None:
        """Test do not merge for yellow mode with tests skipped.

        Verifies skipped perf/resilience tests block merge in YELLOW mode.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed"),
            JobResult(
                "Performance & Resilience Validation / Fast Resilience Tests",
                JobStatus.SKIPPED,
                "Skipped",
            ),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.YELLOW_CRITICAL_PATH, job_results
        )
        assert verdict == "DO_NOT_MERGE_YET"
        assert len(actions) > 0
        assert any("label" in action.lower() for action in actions)

    def test_verdict_red_all_passed(self) -> None:
        """Test safe verdict for red mode with all tests passed.

        Verifies all-passing jobs in RED mode allow merge.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed"),
            JobResult(
                "Performance & Resilience Validation / Fast Resilience Tests",
                JobStatus.SUCCESS,
                "Passed",
            ),
            JobResult(
                "Performance & Resilience Validation / Performance & SLO Validation",
                JobStatus.SUCCESS,
                "Passed",
            ),
            JobResult(
                "Performance & Resilience Validation / Comprehensive Resilience Tests",
                JobStatus.SUCCESS,
                "Passed",
            ),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.RED_HIGH_RISK_OR_RELEASE, job_results
        )
        assert verdict == "SAFE_TO_MERGE_NOW"
        assert len(actions) == 0
        assert any("all" in r.lower() and "passed" in r.lower() for r in reasons)

    def test_verdict_red_missing_comprehensive(self) -> None:
        """Test do not merge for red mode missing comprehensive tests.

        Verifies missing comprehensive tests block merge in RED mode.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed"),
            JobResult(
                "Performance & Resilience Validation / Fast Resilience Tests",
                JobStatus.SUCCESS,
                "Passed",
            ),
            JobResult(
                "Performance & Resilience Validation / Performance & SLO Validation",
                JobStatus.SUCCESS,
                "Passed",
            ),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.RED_HIGH_RISK_OR_RELEASE, job_results
        )
        assert verdict == "DO_NOT_MERGE_YET"
        assert len(actions) > 0
        assert any("comprehensive" in r.lower() for r in reasons)

    def test_verdict_red_perf_failure(self) -> None:
        """Test do not merge for red mode with perf/resilience failures.

        Verifies perf/resilience failures block merge in RED mode.
        """
        job_results = [
            JobResult("Lint and Type Check", JobStatus.SUCCESS, "Passed"),
            JobResult(
                "Performance & Resilience Validation / Fast Resilience Tests",
                JobStatus.FAILURE,
                "Failed | Test timeout exceeded",
            ),
            JobResult(
                "Performance & Resilience Validation / Performance & SLO Validation",
                JobStatus.SUCCESS,
                "Passed",
            ),
            JobResult(
                "Performance & Resilience Validation / Comprehensive Resilience Tests",
                JobStatus.FAILURE,
                "Failed | Memory leak detected",
            ),
        ]
        verdict, actions, reasons = self.verdictor.determine_verdict(
            RiskMode.RED_HIGH_RISK_OR_RELEASE, job_results
        )
        assert verdict == "DO_NOT_MERGE_YET"
        assert len(actions) >= 2
        assert any("Fast Resilience" in action for action in actions)
        assert any("Comprehensive" in action for action in actions)
        assert any("failed" in r.lower() for r in reasons)


class TestCIPerfResilienceGate:
    """Test main gate functionality.

    Tests SLO improvement generation and output formatting.
    """

    gate: CIPerfResilienceGate

    def setup_method(self) -> None:
        """Set up test fixtures.

        Initializes the CIPerfResilienceGate instance for each test.
        """
        self.gate = CIPerfResilienceGate()

    def test_generate_slo_improvements(self) -> None:
        """Test generating SLO improvement suggestions.

        Verifies suggestions are generated for skipped jobs.
        """
        analysis: dict[str, Any] = {
            "job_results": [
                JobResult(
                    "Performance & Resilience Validation / Fast Resilience Tests",
                    JobStatus.SKIPPED,
                    "Skipped",
                ),
            ],
            "mode": RiskMode.YELLOW_CRITICAL_PATH,
        }
        suggestions = self.gate.generate_slo_improvements(analysis)
        assert len(suggestions) <= 3
        assert len(suggestions) > 0

    def test_format_output_structure(self) -> None:
        """Test output formatting structure.

        Verifies all required sections are present in output.
        """
        analysis: dict[str, Any] = {
            "pr_number": 123,
            "pr_title": "Test PR",
            "pr_labels": ["test"],
            "changes": [
                FileChange("README.md", ChangeClass.DOC_ONLY, "Doc file"),
            ],
            "job_results": [
                JobResult("Test Job", JobStatus.SUCCESS, "Passed"),
            ],
            "mode": RiskMode.GREEN_LIGHT,
            "mode_reasons": ["Test reason"],
            "verdict": "SAFE_TO_MERGE_NOW",
            "required_actions": [],
            "verdict_reasons": ["All tests passed"],
        }
        output = self.gate.format_output(analysis)

        # Check for required sections
        assert "Section 1: MODE_CLASSIFICATION" in output
        assert "Section 2: CI_STATUS_TABLE" in output
        assert "Section 3: REQUIRED_ACTIONS_BEFORE_MERGE" in output
        assert "Section 4: MERGE_VERDICT" in output
        assert "Section 5: SLO/CI_IMPROVEMENT_IDEAS" in output
        assert "Appendix: Change Classification Details" in output


class TestParsePRUrl:
    """Test PR URL parsing.

    Tests valid and invalid URL parsing scenarios.
    """

    def test_parse_valid_url(self) -> None:
        """Test parsing valid PR URL.

        Verifies owner, repo, and PR number are extracted correctly.
        """
        url = "https://github.com/neuron7xLab/mlsdm/pull/231"
        owner, repo, pr_number = parse_pr_url(url)
        assert owner == "neuron7x"
        assert repo == "mlsdm"
        assert pr_number == 231

    def test_parse_http_url(self) -> None:
        """Test parsing HTTP (non-HTTPS) URL.

        Verifies HTTP URLs are parsed correctly.
        """
        url = "http://github.com/owner/repo/pull/42"
        owner, repo, pr_number = parse_pr_url(url)
        assert owner == "owner"
        assert repo == "repo"
        assert pr_number == 42

    def test_parse_invalid_url(self) -> None:
        """Test parsing invalid URL raises error.

        Verifies ValueError is raised for malformed URLs.
        """
        with pytest.raises(ValueError):
            parse_pr_url("https://github.com/owner/repo")

        with pytest.raises(ValueError):
            parse_pr_url("not a url")


class TestIntegration:
    """Integration tests for the gate.

    Tests full PR analysis with mocked API responses.
    """

    @patch("ci_perf_resilience_gate.requests.get")
    def test_analyze_pr_integration(self, mock_get: Mock) -> None:
        """Test full PR analysis integration.

        Verifies PR analysis works with mocked GitHub API responses.
        """
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Mock PR data, files, and workflow runs
        mock_response.json.side_effect = [
            # PR data (first call)
            {
                "title": "Test PR",
                "labels": [{"name": "test"}],
                "head": {"sha": "abc123"},
            },
            # Files data (second call)
            [
                {"filename": "README.md", "patch": ""},
                {"filename": "src/mlsdm/neuro_engine/core.py", "patch": ""},
            ],
        ]

        mock_get.return_value = mock_response

        gate = CIPerfResilienceGate()
        # Mock the CI inspector methods to avoid additional API calls
        with patch.object(gate.ci_inspector, "inspect_ci_jobs", return_value=[]):
            analysis = gate.analyze_pr("owner", "repo", 123)

        assert analysis["pr_number"] == 123
        assert analysis["pr_title"] == "Test PR"
        assert len(analysis["changes"]) == 2
        assert isinstance(analysis["mode"], RiskMode)
        assert analysis["verdict"] in [
            "SAFE_TO_MERGE_NOW",
            "DO_NOT_MERGE_YET",
            "MERGE_ONLY_IF_YOU_CONSCIOUSLY_ACCEPT_RISK",
        ]

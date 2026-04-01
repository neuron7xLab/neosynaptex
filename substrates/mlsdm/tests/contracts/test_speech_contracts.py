"""
Speech Governance Contract Tests for MLSDM.

These tests validate the speech governance output contracts as defined by the
AphasiaReport, PipelineStepResult, PipelineMetadata, and AphasiaMetadata models.

CONTRACT STABILITY:
These tests protect the speech governance contract.
If a test fails after code changes, it indicates a potential breaking change.

Test Coverage:
- AphasiaReport model validation
- PipelineStepResult structure
- PipelineMetadata aggregation
- AphasiaMetadata API response format
- Factory methods and conversions
"""

import pytest

from mlsdm.contracts import (
    AphasiaMetadata,
    AphasiaReport,
    PipelineMetadata,
    PipelineStepResult,
)


class TestAphasiaReport:
    """Test AphasiaReport model contract."""

    def test_report_defaults(self) -> None:
        """AphasiaReport has sensible defaults."""
        report = AphasiaReport()
        assert report.is_aphasic is False
        assert report.severity == 0.0
        assert report.patterns_detected == []
        assert report.repaired is False
        assert report.repair_notes is None

    def test_report_detected(self) -> None:
        """AphasiaReport captures detection results."""
        report = AphasiaReport(
            is_aphasic=True,
            severity=0.7,
            patterns_detected=["missing_articles", "omitted_function_words"],
            repaired=True,
            repair_notes="Fixed 3 patterns",
        )
        assert report.is_aphasic is True
        assert report.severity == 0.7
        assert len(report.patterns_detected) == 2
        assert report.repaired is True
        assert report.repair_notes == "Fixed 3 patterns"

    def test_report_severity_range(self) -> None:
        """AphasiaReport severity must be in [0.0, 1.0]."""
        # Valid severities
        AphasiaReport(severity=0.0)
        AphasiaReport(severity=0.5)
        AphasiaReport(severity=1.0)

        # Invalid severities
        with pytest.raises(ValueError):
            AphasiaReport(severity=-0.1)
        with pytest.raises(ValueError):
            AphasiaReport(severity=1.1)

    def test_report_none_detected_factory(self) -> None:
        """AphasiaReport.none_detected() creates empty report."""
        report = AphasiaReport.none_detected()
        assert report.is_aphasic is False
        assert report.severity == 0.0
        assert report.patterns_detected == []

    def test_report_serialization(self) -> None:
        """AphasiaReport serializes correctly."""
        report = AphasiaReport(
            is_aphasic=True,
            severity=0.5,
            patterns_detected=["test_pattern"],
            repaired=True,
        )
        dumped = report.model_dump()
        assert dumped == {
            "is_aphasic": True,
            "severity": 0.5,
            "patterns_detected": ["test_pattern"],
            "repaired": True,
            "repair_notes": None,
        }


class TestPipelineStepResult:
    """Test PipelineStepResult model contract."""

    def test_step_success(self) -> None:
        """PipelineStepResult captures successful step."""
        step = PipelineStepResult(
            name="aphasia_repair",
            status="ok",
            raw_text="input text",
            final_text="output text",
            metadata={"patterns_fixed": 2},
        )
        assert step.name == "aphasia_repair"
        assert step.status == "ok"
        assert step.raw_text == "input text"
        assert step.final_text == "output text"
        assert step.metadata == {"patterns_fixed": 2}
        assert step.is_success is True
        assert step.is_error is False

    def test_step_error(self) -> None:
        """PipelineStepResult captures failed step."""
        step = PipelineStepResult(
            name="faulty_governor",
            status="error",
            error_type="RuntimeError",
            error_message="something went wrong",
        )
        assert step.name == "faulty_governor"
        assert step.status == "error"
        assert step.error_type == "RuntimeError"
        assert step.error_message == "something went wrong"
        assert step.is_success is False
        assert step.is_error is True

    def test_step_required_fields(self) -> None:
        """PipelineStepResult requires name and status."""
        # Valid minimal
        PipelineStepResult(name="test", status="ok")

        # Missing name
        with pytest.raises(ValueError):
            PipelineStepResult(status="ok")  # type: ignore[call-arg]

        # Missing status
        with pytest.raises(ValueError):
            PipelineStepResult(name="test")  # type: ignore[call-arg]

    def test_step_status_enum(self) -> None:
        """PipelineStepResult status must be 'ok' or 'error'."""
        PipelineStepResult(name="test", status="ok")
        PipelineStepResult(name="test", status="error")

        with pytest.raises(ValueError):
            PipelineStepResult(name="test", status="invalid")  # type: ignore[arg-type]


class TestPipelineMetadata:
    """Test PipelineMetadata model contract."""

    def test_metadata_defaults(self) -> None:
        """PipelineMetadata has sensible defaults."""
        meta = PipelineMetadata()
        assert meta.pipeline == []
        assert meta.aphasia_report is None
        assert meta.total_steps == 0
        assert meta.successful_steps == 0
        assert meta.failed_steps == 0

    def test_metadata_with_steps(self) -> None:
        """PipelineMetadata aggregates step results."""
        steps = [
            PipelineStepResult(name="step1", status="ok", raw_text="a", final_text="b"),
            PipelineStepResult(name="step2", status="ok", raw_text="b", final_text="c"),
        ]
        meta = PipelineMetadata(
            pipeline=steps,
            total_steps=2,
            successful_steps=2,
            failed_steps=0,
        )
        assert len(meta.pipeline) == 2
        assert meta.total_steps == 2
        assert meta.successful_steps == 2
        assert meta.failed_steps == 0

    def test_metadata_from_history_success(self) -> None:
        """PipelineMetadata.from_history converts success steps."""
        history = [
            {
                "name": "gov1",
                "status": "ok",
                "raw_text": "input",
                "final_text": "output",
                "metadata": {"key": "value"},
            }
        ]
        meta = PipelineMetadata.from_history(history)

        assert meta.total_steps == 1
        assert meta.successful_steps == 1
        assert meta.failed_steps == 0
        assert meta.pipeline[0].name == "gov1"
        assert meta.pipeline[0].status == "ok"
        assert meta.pipeline[0].raw_text == "input"
        assert meta.pipeline[0].final_text == "output"

    def test_metadata_from_history_error(self) -> None:
        """PipelineMetadata.from_history converts error steps."""
        history = [
            {
                "name": "failing_gov",
                "status": "error",
                "error_type": "ValueError",
                "error_message": "boom",
            }
        ]
        meta = PipelineMetadata.from_history(history)

        assert meta.total_steps == 1
        assert meta.successful_steps == 0
        assert meta.failed_steps == 1
        assert meta.pipeline[0].name == "failing_gov"
        assert meta.pipeline[0].status == "error"
        assert meta.pipeline[0].error_type == "ValueError"
        assert meta.pipeline[0].error_message == "boom"

    def test_metadata_from_history_mixed(self) -> None:
        """PipelineMetadata.from_history handles mixed success/error."""
        history = [
            {"name": "ok1", "status": "ok", "raw_text": "a", "final_text": "b", "metadata": {}},
            {"name": "fail", "status": "error", "error_type": "E", "error_message": "msg"},
            {"name": "ok2", "status": "ok", "raw_text": "b", "final_text": "c", "metadata": {}},
        ]
        meta = PipelineMetadata.from_history(history)

        assert meta.total_steps == 3
        assert meta.successful_steps == 2
        assert meta.failed_steps == 1
        assert [s.name for s in meta.pipeline] == ["ok1", "fail", "ok2"]

    def test_metadata_with_aphasia_report(self) -> None:
        """PipelineMetadata can include aphasia report."""
        report = AphasiaReport(is_aphasic=True, severity=0.5)
        meta = PipelineMetadata.from_history([], aphasia_report=report)

        assert meta.aphasia_report is not None
        assert meta.aphasia_report.is_aphasic is True
        assert meta.aphasia_report.severity == 0.5

    def test_metadata_from_history_missing_status(self) -> None:
        """PipelineMetadata.from_history treats missing status as error."""
        history = [
            {"name": "missing_status_step"},  # No status field
        ]
        meta = PipelineMetadata.from_history(history)

        assert meta.total_steps == 1
        assert meta.successful_steps == 0
        assert meta.failed_steps == 1
        assert meta.pipeline[0].name == "missing_status_step"
        assert meta.pipeline[0].status == "error"
        assert meta.pipeline[0].error_message == "missing status field"


class TestAphasiaMetadata:
    """Test AphasiaMetadata model contract (API response format)."""

    def test_metadata_enabled(self) -> None:
        """AphasiaMetadata captures enabled state."""
        meta = AphasiaMetadata(
            enabled=True,
            detected=True,
            severity=0.6,
            repaired=True,
        )
        assert meta.enabled is True
        assert meta.detected is True
        assert meta.severity == 0.6
        assert meta.repaired is True
        assert meta.note is None

    def test_metadata_disabled_factory(self) -> None:
        """AphasiaMetadata.disabled() creates disabled metadata."""
        meta = AphasiaMetadata.disabled()
        assert meta.enabled is False
        assert meta.detected is False
        assert meta.severity == 0.0
        assert meta.repaired is False

    def test_metadata_from_report(self) -> None:
        """AphasiaMetadata.from_report converts AphasiaReport."""
        report = AphasiaReport(
            is_aphasic=True,
            severity=0.7,
            repaired=True,
        )
        meta = AphasiaMetadata.from_report(report, enabled=True, note="test note")

        assert meta.enabled is True
        assert meta.detected is True
        assert meta.severity == 0.7
        assert meta.repaired is True
        assert meta.note == "test note"

    def test_metadata_from_none_report(self) -> None:
        """AphasiaMetadata.from_report handles None report."""
        meta = AphasiaMetadata.from_report(None, enabled=True)

        assert meta.enabled is True
        assert meta.detected is False
        assert meta.severity == 0.0
        assert meta.repaired is False

    def test_metadata_severity_range(self) -> None:
        """AphasiaMetadata severity must be in [0.0, 1.0]."""
        # Valid
        AphasiaMetadata(enabled=True, severity=0.0)
        AphasiaMetadata(enabled=True, severity=1.0)

        # Invalid
        with pytest.raises(ValueError):
            AphasiaMetadata(enabled=True, severity=-0.1)
        with pytest.raises(ValueError):
            AphasiaMetadata(enabled=True, severity=1.1)

    def test_metadata_serialization(self) -> None:
        """AphasiaMetadata serializes correctly for API response."""
        meta = AphasiaMetadata(
            enabled=True,
            detected=True,
            severity=0.5,
            repaired=False,
            note="aphasia_mode enabled but no speech governor configured",
        )
        dumped = meta.model_dump()
        assert dumped == {
            "enabled": True,
            "detected": True,
            "severity": 0.5,
            "repaired": False,
            "note": "aphasia_mode enabled but no speech governor configured",
        }


class TestContractCompatibility:
    """Test that contract models are compatible with existing code."""

    def test_aphasia_metadata_matches_api_response_format(self) -> None:
        """AphasiaMetadata matches the format used in /infer endpoint."""
        # Simulated output from /infer endpoint
        api_response_format = {
            "enabled": True,
            "detected": False,
            "severity": 0.0,
            "repaired": False,
            "note": "aphasia_mode enabled but no speech governor configured",
        }

        # Create model from dict
        meta = AphasiaMetadata(**api_response_format)

        # Verify round-trip
        assert meta.model_dump() == api_response_format

    def test_pipeline_metadata_matches_speech_governance_format(self) -> None:
        """PipelineMetadata matches the format from PipelineSpeechGovernor."""
        # Simulated output from PipelineSpeechGovernor
        pipeline_history = [
            {
                "name": "gov1",
                "status": "ok",
                "raw_text": "input",
                "final_text": "output",
                "metadata": {"suffix": "A"},
            },
            {
                "name": "gov2",
                "status": "error",
                "error_type": "RuntimeError",
                "error_message": "boom",
            },
        ]

        # Convert to PipelineMetadata
        meta = PipelineMetadata.from_history(pipeline_history)

        # Verify structure
        assert meta.total_steps == 2
        assert meta.successful_steps == 1
        assert meta.failed_steps == 1
        assert meta.pipeline[0].name == "gov1"
        assert meta.pipeline[0].is_success
        assert meta.pipeline[1].name == "gov2"
        assert meta.pipeline[1].is_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

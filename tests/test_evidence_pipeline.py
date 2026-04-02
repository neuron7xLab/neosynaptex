"""10 tests for EvidencePipeline — collect, validate, register, query."""

import time

import pytest

from core.evidence_pipeline import EvidencePipeline
from core.evidence_schema import EvidenceRecord, validate_record


@pytest.fixture()
def pipeline(tmp_path):
    return EvidencePipeline(evidence_dir=tmp_path)


def test_collect_creates_raw(pipeline):
    raw = pipeline.collect(
        "test_source",
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="theilslopes",
    )
    assert raw.substrate == "bn_syn"
    assert raw.value == 0.95


def test_validate_valid_evidence(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="theilslopes",
    )
    result = pipeline.validate(raw)
    assert len(result.validation_errors) == 0
    assert result.record.substrate == "bn_syn"


def test_validate_invalid_ci(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=1.1,
        ci95_hi=0.9,
        method="theilslopes",
    )
    result = pipeline.validate(raw)
    assert len(result.validation_errors) > 0
    assert any("ci95_lo" in e for e in result.validation_errors)


def test_validate_nan_value(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="bn_syn",
        metric="gamma",
        value=float("nan"),
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="theilslopes",
    )
    result = pipeline.validate(raw)
    assert len(result.validation_errors) > 0


def test_register_appends(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="theilslopes",
    )
    validated = pipeline.validate(raw)
    assert pipeline.register(validated)

    # Register another
    raw2 = pipeline.collect(
        "test",
        substrate="morpho",
        metric="gamma",
        value=1.0,
        ci95_lo=0.95,
        ci95_hi=1.05,
        method="theilslopes",
    )
    validated2 = pipeline.validate(raw2)
    assert pipeline.register(validated2)

    records = pipeline.query()
    assert len(records) == 2


def test_register_rejects_invalid(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="",
        metric="",
        value=float("nan"),
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="",
    )
    validated = pipeline.validate(raw)
    assert not pipeline.register(validated)


def test_query_by_substrate(pipeline):
    for sub in ["bn_syn", "morpho", "bn_syn"]:
        raw = pipeline.collect(
            "test", substrate=sub, metric="gamma", value=1.0, ci95_lo=0.9, ci95_hi=1.1, method="ts"
        )
        pipeline.register(pipeline.validate(raw))

    results = pipeline.query(substrate="bn_syn")
    assert len(results) == 2


def test_query_by_metric(pipeline):
    for metric in ["gamma", "sr", "gamma"]:
        raw = pipeline.collect(
            "test",
            substrate="bn_syn",
            metric=metric,
            value=1.0,
            ci95_lo=0.9,
            ci95_hi=1.1,
            method="ts",
        )
        pipeline.register(pipeline.validate(raw))

    results = pipeline.query(metric="sr")
    assert len(results) == 1


def test_manifest_creates_file(pipeline):
    raw = pipeline.collect(
        "test",
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="ts",
    )
    pipeline.register(pipeline.validate(raw))
    manifest = pipeline.manifest("session_001")
    assert manifest["session_id"] == "session_001"
    assert manifest["n_records"] == 1


def test_evidence_record_schema():
    record = EvidenceRecord(
        substrate="bn_syn",
        metric="gamma",
        value=0.95,
        ci95_lo=0.9,
        ci95_hi=1.0,
        method="theilslopes",
        timestamp=time.time(),
        git_sha="abc1234",
    )
    valid, errors = validate_record(record)
    assert valid
    assert len(errors) == 0

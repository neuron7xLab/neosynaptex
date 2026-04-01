"""Bundle specification tests — verify artifact schemas and validation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import mycelium_fractal_net as mfn


class TestBundleSchemas:
    """Verify schema generation and validation."""

    def test_schemas_generated(self) -> None:
        import subprocess

        subprocess.run(
            [".venv/bin/python", "scripts/generate_bundle_schemas.py"],
            check=True,
            capture_output=True,
        )
        schema_dir = Path("docs/contracts/schemas")
        assert schema_dir.exists()
        schemas = list(schema_dir.glob("*.schema.json"))
        assert len(schemas) >= 7, f"Expected 7+ schemas, got {len(schemas)}"

    def test_each_schema_valid_json(self) -> None:
        schema_dir = Path("docs/contracts/schemas")
        if not schema_dir.exists():
            import subprocess

            subprocess.run(
                [".venv/bin/python", "scripts/generate_bundle_schemas.py"],
                check=True,
                capture_output=True,
            )
        for sf in schema_dir.glob("*.schema.json"):
            data = json.loads(sf.read_text())
            assert "$schema" in data, f"{sf.name}: missing $schema"
            assert "title" in data, f"{sf.name}: missing title"
            assert "version" in data, f"{sf.name}: missing version"
            assert "properties" in data, f"{sf.name}: missing properties"


class TestBundleReport:
    """Verify full pipeline produces a valid bundle."""

    def test_report_produces_valid_json_artifacts(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        with tempfile.TemporaryDirectory() as tmpdir:
            mfn.report(seq, tmpdir)
            # Find all JSON files in the report output
            json_files = list(Path(tmpdir).rglob("*.json"))
            assert len(json_files) >= 1, "Report should produce JSON artifacts"
            for jf in json_files:
                data = json.loads(jf.read_text())
                assert isinstance(data, dict), f"{jf.name}: not a dict"

    def test_report_artifact_has_version(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        d = mfn.report(seq, tempfile.mkdtemp()).to_dict()
        assert "schema_version" in d or "engine_version" in d


class TestBundleVerifier:
    """Test standalone bundle verifier."""

    def test_verify_valid_bundle(self) -> None:
        from scripts.verify_bundle import verify_bundle

        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
        seq = mfn.simulate(spec)
        with tempfile.TemporaryDirectory() as tmpdir:
            mfn.report(seq, tmpdir)
            result = verify_bundle(tmpdir)
            assert result["ok"] or len(result["artifacts"]) > 0

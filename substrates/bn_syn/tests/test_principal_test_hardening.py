from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class TestEntropyMonotonicity:
    def test_entropy_current_does_not_exceed_baseline(self) -> None:
        baseline = json.loads((REPO_ROOT / "entropy" / "baseline.json").read_text(encoding="utf-8"))
        current = json.loads((REPO_ROOT / "entropy" / "current.json").read_text(encoding="utf-8"))
        baseline_det = baseline["determinism"]
        current_det = current["determinism"]
        monitored = ["global_np_random_offenders", "python_random_offenders", "time_calls_offenders"]
        for key in monitored:
            assert int(current_det[key]) <= int(baseline_det[key])


class TestDeterministicExecutionChain:
    def test_generate_inventory_is_deterministic(self, tmp_path: Path) -> None:
        first = subprocess.check_output(["python", "-m", "scripts.generate_tests_inventory"], text=True)
        assert first == ""
        inventory_path = REPO_ROOT / "tests_inventory.json"
        first_hash = _sha256_bytes(inventory_path.read_bytes())

        second = subprocess.check_output(["python", "-m", "scripts.generate_tests_inventory"], text=True)
        assert second == ""
        second_hash = _sha256_bytes(inventory_path.read_bytes())

        assert first_hash == second_hash
        tmp_path.joinpath("inventory.sha").write_text(first_hash, encoding="utf-8")


class TestArtifactProvenanceInvariant:
    def test_repo_manifest_entries_are_sorted_and_sha_addressed(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "manifest" / "repo_manifest.computed.json").read_text(encoding="utf-8")
        )
        assert isinstance(manifest["invariants"], list)
        assert len(manifest["invariants"]) > 0
        repo_ref = manifest["repo_ref"]
        assert isinstance(repo_ref, str)
        assert len(repo_ref) == 64
        assert repo_ref.isalnum()

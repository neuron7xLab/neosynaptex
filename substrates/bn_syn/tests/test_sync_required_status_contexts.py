from __future__ import annotations

from pathlib import Path
import pytest

from scripts.sync_required_status_contexts import build_payload, sync_required_status_contexts
from scripts.validate_required_status_contexts import (
    RequiredStatusContextsParseError,
    expected_required_status_contexts,
)


def test_build_payload_matches_contract() -> None:
    payload = build_payload(Path(".github/PR_GATES.yml"), Path(".github/workflows"))

    assert payload["version"] == "1"
    contexts = payload["required_status_contexts"]
    assert isinstance(contexts, list)
    assert contexts
    assert "ci-pr-atomic / gate-profile" in contexts


def test_sync_required_status_contexts_check_and_update(tmp_path: Path) -> None:
    contexts_path = tmp_path / "REQUIRED_STATUS_CONTEXTS.yml"
    contexts_path.write_text("version: '1'\nrequired_status_contexts: []\n", encoding="utf-8")

    check_exit = sync_required_status_contexts(
        contexts_path=contexts_path,
        pr_gates_path=Path(".github/PR_GATES.yml"),
        workflows_dir=Path(".github/workflows"),
        check=True,
    )
    assert check_exit == 2

    update_exit = sync_required_status_contexts(
        contexts_path=contexts_path,
        pr_gates_path=Path(".github/PR_GATES.yml"),
        workflows_dir=Path(".github/workflows"),
        check=False,
    )
    assert update_exit == 0

    saved = contexts_path.read_text(encoding="utf-8")
    assert "required_status_contexts:" in saved
    assert "ci-pr-atomic / gate-profile" in saved


def test_expected_required_status_contexts_rejects_pr_gates_unknown_keys(tmp_path: Path) -> None:
    pr_gates = tmp_path / "PR_GATES.yml"
    pr_gates.write_text(
        "version: '1'\nrequired_pr_gates: []\nextra: true\n",
        encoding="utf-8",
    )
    workflows = tmp_path / "workflows"
    workflows.mkdir()

    with pytest.raises(RequiredStatusContextsParseError, match="Unknown keys"):
        expected_required_status_contexts(pr_gates, workflows)


def test_expected_required_status_contexts_rejects_duplicate_required_job_ids(
    tmp_path: Path,
) -> None:
    pr_gates = tmp_path / "PR_GATES.yml"
    pr_gates.write_text(
        "\n".join(
            [
                "version: '1'",
                "required_pr_gates:",
                "  - workflow_file: ci-pr-atomic.yml",
                "    workflow_name: ci-pr-atomic",
                "    required_job_ids:",
                "      - gate-profile",
                "      - gate-profile",
                "",
            ]
        ),
        encoding="utf-8",
    )
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "ci-pr-atomic.yml").write_text(
        "name: ci-pr-atomic\non:\n  pull_request:\njobs:\n  gate-profile:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    with pytest.raises(RequiredStatusContextsParseError, match="contains duplicates"):
        expected_required_status_contexts(pr_gates, workflows)

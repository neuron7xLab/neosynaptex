from __future__ import annotations

from typing import Any


def render_markdown(computed: dict[str, Any]) -> str:
    metrics = computed["metrics"]
    invariants = computed["invariants"]
    required = computed["required_pr_gates"]

    invariant_rows = "\n".join(
        f"| {item['id']} | {item['statement']} | `{item['enforcement']}` | {item['evidence_kind']} |"
        for item in sorted(invariants, key=lambda entry: entry["id"])
    )

    return (
        "# Repository Manifest (Generated)\n\n"
        f"- Manifest version: `{computed['manifest_version']}`\n"
        f"- Generated marker: `{computed['generated_at']}`\n"
        f"- Repository fingerprint: `{computed['repo_ref']}`\n"
        f"- Required PR gates source: `{required['source']}`\n"
        f"- Required PR gates SHA-256: `{required['sha256']}`\n\n"
        "## Metrics\n\n"
        f"- Workflow files (`.github/workflows/*.yml`): **{metrics['workflow_total']}**\n"
        f"- Reusable workflow files (`_reusable_*.yml`): **{metrics['workflow_reusable_total']}**\n"
        f"- Workflows declaring `workflow_call`: **{metrics['workflow_call_total']}**\n"
        f"- Required PR gates (`.github/PR_GATES.yml`): **{metrics['required_pr_gate_total']}**\n"
        f"- Coverage minimum percent (`quality/coverage_gate.json`): **{metrics['coverage_minimum_percent']}**\n"
        f"- Coverage baseline percent (`quality/coverage_gate.json`): **{metrics['coverage_baseline_percent']}**\n"
        f"- Mutation baseline score (`quality/mutation_baseline.json`): **{metrics['mutation_baseline_score']}**\n"
        f"- Mutation total mutants (`quality/mutation_baseline.json`): **{metrics['mutation_total_mutants']}**\n"
        f"- `ci_manifest.json` exists: **{metrics['ci_manifest_exists']}**\n"
        f"- `ci_manifest.json` references in scoped scan: **{metrics['ci_manifest_reference_count']}**\n"
        + "- `ci_manifest.json` scan scope:\n"
        + "\n".join(f"  - `{item}`" for item in metrics["ci_manifest_reference_scope"])
        + "\n\n"
        "## Invariants\n\n"
        "| ID | Statement | Enforcement | Evidence kind |\n"
        "|---|---|---|---|\n"
        f"{invariant_rows}\n\n"
        "## Evidence Rules\n\n"
        "Accepted pointer formats:\n"
        + "\n".join(
            f"- `{item}`" for item in computed["evidence_rules"]["accepted_pointer_formats"]
        )
        + "\n"
    )

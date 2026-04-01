"""Export ZebrafishValidationReport to various formats."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .gamma_validator import ZebrafishValidationReport

__all__ = ["ZebrafishReportExporter"]


class ZebrafishReportExporter:

    def to_json(
        self, report: ZebrafishValidationReport, path: Path | None = None
    ) -> str:
        """Serialize report to JSON."""
        data = {
            "wild_type": asdict(report.wild_type),
            "mutant": asdict(report.mutant),
            "transition": asdict(report.transition) if report.transition else None,
            "hypothesis_supported": report.hypothesis_supported,
            "falsification_verdict": report.falsification_verdict,
            "organoid_gamma": report.organoid_gamma,
            "wt_in_organoid_ci": report.wt_in_organoid_ci,
            "label_real": report.label_real,
            "timestamp": report.timestamp,
        }
        js = json.dumps(data, indent=2, default=str)
        if path:
            path.write_text(js)
        return js

    def to_markdown(
        self, report: ZebrafishValidationReport, path: Path | None = None
    ) -> str:
        """Generate Markdown report for manuscript."""
        wt = report.wild_type
        mut = report.mutant

        evidence_label = (
            "SYNTHETIC PROXY" if not report.label_real else "REAL DATA"
        )

        lines = [
            "# Zebrafish gamma-Scaling Validation Report",
            "",
            f"**Evidence type**: {evidence_label}",
            f"**Timestamp**: {report.timestamp}",
            "",
            "## Results",
            "",
            "| Phenotype | gamma | R2 | p-value | CI95 | gamma~1.0? | Verdict |",
            "|-----------|-------|----|---------|------|------------|---------|",
            f"| Wild-type | {wt.gamma:.3f} | {wt.r_squared:.3f} | {wt.p_value:.4f} "
            f"| [{wt.ci95_lo:.3f}, {wt.ci95_hi:.3f}] "
            f"| {'YES' if wt.hypothesis_1_0 else 'NO'} "
            f"| {'VALID' if wt.valid else 'INVALID'} |",
            f"| Mutant    | {mut.gamma:.3f} | {mut.r_squared:.3f} | {mut.p_value:.4f} "
            f"| [{mut.ci95_lo:.3f}, {mut.ci95_hi:.3f}] "
            f"| {'YES' if mut.hypothesis_1_0 else 'NO'} "
            f"| {'VALID' if mut.valid else 'INVALID'} |",
        ]
        if report.transition:
            tr = report.transition
            lines.append(
                f"| Transition | {tr.gamma:.3f} | {tr.r_squared:.3f} | {tr.p_value:.4f} "
                f"| [{tr.ci95_lo:.3f}, {tr.ci95_hi:.3f}] "
                f"| {'YES' if tr.hypothesis_1_0 else 'NO'} "
                f"| {'VALID' if tr.valid else 'INVALID'} |"
            )

        lines += [
            "",
            "## Organoid Reference",
            "",
            f"gamma_organoid (Vasylenko 2026, Zenodo 10301912) = "
            f"**{report.organoid_gamma} +/- 0.208**",
            f"Wild-type gamma in organoid CI "
            f"[{report.organoid_ci_lo:.3f}, {report.organoid_ci_hi:.3f}]: "
            f"**{report.wt_in_organoid_ci}**",
            "",
            "## Falsification Verdict",
            "",
            f"**{report.falsification_verdict}**",
            "",
            "> Hypothesis (Vasylenko-Levin-Tononi): Wild-type gamma ~ +1.0, "
            "Mutant gamma != 1.0.",
            "",
            "## Notes",
            "",
        ]

        for note in wt.notes + mut.notes:
            if note.strip():
                lines.append(f"- {note}")

        lines += [
            "",
            "## References",
            "",
            "- McGuirl et al. (2020) PNAS 117(10):5217-5224. "
            "DOI: 10.1073/pnas.1917038117",
            "- Vasylenko (2026) gamma-scaling on brain organoids. Zenodo 10301912",
            "- Theil (1950), Sen (1968): robust slope estimator",
        ]

        md = "\n".join(lines)
        if path:
            path.write_text(md)
        return md

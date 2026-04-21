#!/usr/bin/env python3
"""
Canon-closure master check.

Implements the 10 checks mandated by the canon closure protocol
v1.0 (patch v1.2) Phase 7:

  1. docs/CLAIM_BOUNDARY.md exists and contains claims C-001..C-004.
  2. docs/REVIEWER_ATTACK_SURFACE.md exists with >= 7 attack rows.
  3. docs/CONTRIBUTION_STATEMENT.md exists and contains all three
     pillars (grep for "Operational reframing", "Rigorous anchor",
     "Empirical cross-substrate").
  4. manuscript/arxiv_submission.tex §2 ("Analytical result for
     Kuramoto") exists with subsections 2.1 through 2.6.
  5. manuscript references evidence/lemma_1_numerical.json.
  6. scripts/validate_claims.py exits 0 when run.
  7. README.md contains no forbidden phrases (same forbidden list
     as validate_claims.py).
  8. Manuscript contains the defensive sentence verbatim.
  9. Abstract contains the anchor number γ̂ = 0.9923 (or the value
     stored in evidence/lemma_1_numerical.json#primary_fit.
     anchor_value_for_abstract, whichever the evidence file states).
  9b. Abstract contains the descriptive sentence verbatim.

Exit code 0 iff all 10 checks pass; else 1, with reason strings
naming each failed check.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEFENSIVE_SENTENCE = (
    "Analytical proof is currently available only for the Kuramoto "
    "dense-graph case; universality across other substrates remains "
    "an empirical conjecture."
)
DESCRIPTIVE_SENTENCE = (
    "We prove $\\gamma = 1$ for the Kuramoto model on dense symmetric "
    "graphs and test the broader cross-substrate conjecture empirically."
)

FORBIDDEN = [
    re.compile(r"proves\s+universality", re.IGNORECASE),
    re.compile(r"universal\s+law", re.IGNORECASE),
    re.compile(r"universal\s+exponent", re.IGNORECASE),
    re.compile(r"universal\s+scaling\s+(exponent|law|invariant|signature)", re.IGNORECASE),
    re.compile(r"substrate[-\s]independent\s+law", re.IGNORECASE),
    re.compile(r"global\s+theorem", re.IGNORECASE),
    re.compile(r"γ\s*=\s*1\s+everywhere", re.IGNORECASE),
    re.compile(r"gamma\s*=\s*1\s+everywhere", re.IGNORECASE),
]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# -- individual checks ------------------------------------------------


def check_1_claim_boundary() -> tuple[bool, str]:
    p = REPO / "docs" / "CLAIM_BOUNDARY.md"
    if not p.exists():
        return False, "docs/CLAIM_BOUNDARY.md missing"
    text = _read(p)
    missing = [cid for cid in ("C-001", "C-002", "C-003", "C-004") if cid not in text]
    if missing:
        return False, f"CLAIM_BOUNDARY.md missing rows: {missing}"
    return True, "OK"


def check_2_reviewer_shield() -> tuple[bool, str]:
    p = REPO / "docs" / "REVIEWER_ATTACK_SURFACE.md"
    if not p.exists():
        return False, "docs/REVIEWER_ATTACK_SURFACE.md missing"
    text = _read(p)
    # Count attack rows: lines starting with "| <digit> |" in the table body.
    rows = re.findall(r"^\|\s*\d+\s*\|", text, re.MULTILINE)
    n = len(rows)
    if n < 7:
        return False, f"REVIEWER_ATTACK_SURFACE.md has only {n} attack rows (< 7)"
    return True, f"OK ({n} rows)"


def check_3_contribution_pillars() -> tuple[bool, str]:
    p = REPO / "docs" / "CONTRIBUTION_STATEMENT.md"
    if not p.exists():
        return False, "docs/CONTRIBUTION_STATEMENT.md missing"
    text = _read(p)
    required = ("Operational reframing", "Rigorous anchor", "Empirical cross-substrate")
    missing = [r for r in required if r not in text]
    if missing:
        return False, f"CONTRIBUTION_STATEMENT.md missing pillars: {missing}"
    return True, "OK"


def check_4_manuscript_section_2() -> tuple[bool, str]:
    p = REPO / "manuscript" / "arxiv_submission.tex"
    if not p.exists():
        return False, "manuscript/arxiv_submission.tex missing"
    text = _read(p)
    if r"\section{Analytical result for Kuramoto}" not in text:
        return False, "manuscript §2 header not set to 'Analytical result for Kuramoto'"
    required = (
        r"\subsection{Model and assumptions}",
        r"\subsection{Lemma 1}",
        r"\subsection{Proof}",
        r"\subsection{Special case",
        r"\subsection{Numerical verification}",
        r"\subsection{Remark on normalization conventions}",
    )
    missing = [s for s in required if s not in text]
    if missing:
        return False, f"manuscript §2 missing subsections: {missing}"
    return True, "OK"


def check_5_evidence_reference() -> tuple[bool, str]:
    p = REPO / "manuscript" / "arxiv_submission.tex"
    text = _read(p)
    # Accept either raw path or LaTeX-escaped underscore form.
    if (
        "evidence/lemma_1_numerical.json" not in text
        and r"evidence/lemma\_1\_numerical.json" not in text
    ):
        return False, "manuscript does not reference evidence/lemma_1_numerical.json"
    return True, "OK"


def check_6_validate_claims() -> tuple[bool, str]:
    script = REPO / "scripts" / "validate_claims.py"
    if not script.exists():
        return False, "scripts/validate_claims.py missing"
    try:
        res = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, "validate_claims.py timed out (>120 s)"
    if res.returncode != 0:
        return False, f"validate_claims.py exited {res.returncode}: {res.stdout.strip().splitlines()[-1:]}"
    return True, "OK"


def check_7_readme_forbidden() -> tuple[bool, str]:
    p = REPO / "README.md"
    if not p.exists():
        return False, "README.md missing"
    text = _read(p)
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for pat in FORBIDDEN:
            if pat.search(line):
                hits.append((i, line.strip()[:120]))
                break
    if hits:
        samples = "; ".join(f"L{i}:{s[:40]}" for i, s in hits[:3])
        return False, f"README.md contains {len(hits)} forbidden-phrase hit(s): {samples}"
    return True, "OK"


def check_8_defensive_sentence() -> tuple[bool, str]:
    p = REPO / "manuscript" / "arxiv_submission.tex"
    text = _norm_ws(_read(p))
    target = _norm_ws(DEFENSIVE_SENTENCE)
    if target not in text:
        return False, "manuscript missing defensive sentence verbatim"
    return True, "OK"


def check_9_anchor_number() -> tuple[bool, str]:
    p = REPO / "manuscript" / "arxiv_submission.tex"
    ev = REPO / "evidence" / "lemma_1_numerical.json"
    if not ev.exists():
        return False, "evidence/lemma_1_numerical.json missing"
    data = json.loads(_read(ev))
    primary = data.get("primary_fit", {})
    anchor = primary.get("anchor_value_for_abstract") or primary.get("gamma_hat")
    if anchor is None:
        return False, "evidence primary_fit lacks anchor value"
    text = _read(p)
    # Extract abstract block only for anchor check.
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
    if not m:
        return False, "manuscript abstract block not found"
    abstract = m.group(1)
    anchor_str = f"{anchor:.4f}".rstrip("0").rstrip(".")
    if anchor_str not in abstract and f"{anchor}" not in abstract:
        return False, f"abstract missing anchor number {anchor_str} from evidence primary_fit"
    return True, f"OK (anchor={anchor_str})"


def check_9b_descriptive_sentence() -> tuple[bool, str]:
    p = REPO / "manuscript" / "arxiv_submission.tex"
    text = _read(p)
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
    if not m:
        return False, "manuscript abstract block not found"
    abstract = _norm_ws(m.group(1))
    target = _norm_ws(DESCRIPTIVE_SENTENCE)
    if target not in abstract:
        return False, "abstract missing descriptive sentence verbatim"
    return True, "OK"


CHECKS = [
    ("1  CLAIM_BOUNDARY C-001..C-004", check_1_claim_boundary),
    ("2  REVIEWER_ATTACK_SURFACE >=7 rows", check_2_reviewer_shield),
    ("3  CONTRIBUTION_STATEMENT pillars", check_3_contribution_pillars),
    ("4  manuscript §2 with 2.1-2.6", check_4_manuscript_section_2),
    ("5  manuscript -> evidence/lemma_1_numerical.json", check_5_evidence_reference),
    ("6  scripts/validate_claims.py exits 0", check_6_validate_claims),
    ("7  README.md forbidden-phrase free", check_7_readme_forbidden),
    ("8  manuscript defensive sentence verbatim", check_8_defensive_sentence),
    ("9  abstract anchor number from evidence", check_9_anchor_number),
    ("9b abstract descriptive sentence verbatim", check_9b_descriptive_sentence),
]


def main() -> int:
    failed: list[tuple[str, str]] = []
    passed: list[tuple[str, str]] = []
    for name, fn in CHECKS:
        ok, detail = fn()
        (passed if ok else failed).append((name, detail))
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name} — {detail}")
    print()
    if failed:
        print(f"canon_closure_check: FAIL ({len(failed)} of {len(CHECKS)} checks failed).")
        for name, detail in failed:
            print(f"  FAIL  {name}  {detail}")
        return 1
    print(f"canon_closure_check: PASS (all {len(CHECKS)} checks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

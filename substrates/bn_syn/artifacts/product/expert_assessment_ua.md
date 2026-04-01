# 100% VOLUME & EVIDENCE REPORT (BN-SYN · 28-DAY WINDOW)
**Execution Date:** 2026-02-20
**Global Readiness:** 75.00%
**Status:** BLOCKED
**Contradictions Detected:** 0

## 1. GITHUB TOOLING EVIDENCE (DOMAIN A · HOTFIX)
| Metric | Extracted Data | Status | Anchor / Ref |
|--------|----------------|--------|--------------|
| Token Presence (`GITHUB_TOKEN`) | Not present (`GITHUB_TOKEN_PRESENT=0`) | FAIL | `proof_bundle/logs/hotfix_github_token_presence.log` |
| Token Presence (`GH_TOKEN`) | Not present (`GH_TOKEN_PRESENT=0`) | FAIL | `proof_bundle/logs/hotfix_gh_token_presence.log` |
| `gh auth status` | Not logged in to `github.com` (`EXIT_CODE:1`) | FAIL | `proof_bundle/logs/hotfix_gh_auth_status.log` |
| CodeQL/SAST Alerts | API extraction blocked by missing auth (`EXIT_CODE:4`) | FAIL | `proof_bundle/logs/hotfix_gh_code_scanning_alerts.log`, `artifacts/security/security_scan_final.json` |
| Dependabot Alerts | API extraction blocked by missing auth (`EXIT_CODE:4`) | FAIL | `proof_bundle/logs/hotfix_gh_dependabot_alerts.log`, `artifacts/security/security_scan_final.json` |
| CI Pipeline (Last 10) | `gh run list` blocked by missing auth (`EXIT_CODE:4`) | FAIL | `proof_bundle/logs/hotfix_gh_run_list.log`, `artifacts/security/security_scan_final.json` |
| Branch Protection (main) | API extraction blocked by missing auth (`EXIT_CODE:4`) | FAIL | `proof_bundle/logs/hotfix_gh_branch_protection.log`, `artifacts/security/security_scan_final.json` |

## 2. TEST & CODEBASE EVIDENCE (DOMAIN B)
| Metric | Extracted Data | Status | Anchor / Ref |
|--------|----------------|--------|--------------|
| Total Tests Run | 1025 | INFO | `proof_bundle/logs/pytest_not_validation_property.log` |
| Tests Passed/Failed | Passed: 1019, Failed: 0, Skipped: 6 | PASS | `proof_bundle/logs/pytest_not_validation_property.log` |
| Mypy Strict Errors | 0 (`--strict`) | PASS | `proof_bundle/logs/113_mypy_strict_final4.log` |
| Ruff Violations | 0 | PASS | `proof_bundle/logs/119_ruff_required_final.log` |

## 3. FORMAL & META-PROTOCOL EVIDENCE (DOMAIN C)
| Protocol / Spec | File / Path | Status | sha256 Signature |
|-----------------|-------------|--------|------------------|
| GHTPO-2026.02 | `GHTPO-2026.02.md` | VERIFIED | `manifest/repo_manifest.json` |
| ELPEG-2026.04 | `ELPEG-2026.04.md` | VERIFIED | `manifest/repo_manifest.json` |
| BIO-DIGITAL-S12 | `BIO-DIGITAL-S12.yaml` | VERIFIED | `manifest/repo_manifest.json` |
| TLA+ / Coq Proofs| `specs/tla/BNsyn.tla`, `specs/coq/BNsyn_Sigma.v` | VERIFIED | `manifest/repo_manifest.json` |

## 4. PRODUCT UX & BLOCKERS (DOMAIN D)
| Metric | Extracted Data | Status | Anchor / Ref |
|--------|----------------|--------|--------------|
| CLI Error Path | Invalid input returns deterministic error path (no traceback) | PASS | `proof_bundle/logs/94_cli_invalid_gate.log` |
| Evidence Bundle Integrity | Consolidated security JSON updated and hash-anchored | PASS | `artifacts/security/security_scan_final.json`, `manifest/repo_manifest.json` |

## 5. EXECUTIVE VOLUME SUMMARY (28 DAYS)
- **Total Commits Analyzed:** 911
- **Total Synthetic Objects Integrated:** 1456
- **Lines of Code / Tests Written:** Added 402008, Deleted 50811, Total Changed 452819
- **P0 BLOCKERS:**
  1. Domain A telemetry gates cannot pass without authenticated `gh` session (`gh auth status` must be `EXIT_CODE:0`).

**END OF REPORT.**

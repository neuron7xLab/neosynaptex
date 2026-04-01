# Hygiene: Remove Proven Digital Noise

## Title
Hygiene: Remove Proven Digital Noise

## Scope
Deletions-only hygiene audit for 100% provable digital trash with evidence artifacts.

## Summary
- Candidates discovered: 0
- Approved for delete: 0
- Deleted: 0
- Kept: 0 candidates (none discovered)

No deletion was executed in this run because no candidate satisfied the strict T1–T4 rubric at confidence=1.0.

## Evidence
- Manifest: `noise_cleanup_manifest.json`
- Report: `noise_cleanup_report.md`
- Baseline/candidate/dry-run/gate logs: `proof_bundle/logs/093_baseline_git_status.log` … `proof_bundle/logs/114_final_status.log`
- Proof index: `proof_bundle/index.json`
- Proof hashes: `proof_bundle/hashes/sha256sums.txt`

## Reproduction Commands
```bash
git status --porcelain=v1
git ls-files -o -i --exclude-standard
find . -maxdepth 6 -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" \)
find . -maxdepth 6 -type f \( -name "*.pyc" -o -name ".DS_Store" -o -name "Thumbs.db" -o -name "*.swp" -o -name "*.swo" -o -name "*~" \)
git clean -ndX
git clean -nd
python -m pytest -m "not validation" -q
ruff check .
pylint src/bnsyn
mypy src --strict --config-file pyproject.toml
python -m build
```

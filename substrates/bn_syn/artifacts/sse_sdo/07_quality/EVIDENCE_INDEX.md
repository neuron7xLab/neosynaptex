# EVIDENCE_INDEX

## G0 CONTRADICTIONS_ZERO
- §REF:cmd:python - <<'PY'
import json
from pathlib import Path
p=Path('artifacts/sse_sdo/07_quality/CONTRADICTIONS.json')
obj=json.loads(p.read_text())
raise SystemExit(0 if len(obj.get('contradictions', []))==0 else 1)
PY -> log:artifacts/sse_sdo/logs/g0_20260219T083353Z.log#e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

## G1 POLICY_SCHEMA_STRICT
- §REF:cmd:scripts/sse_policy_load .github/sse_sdo_fhe.yml -> log:artifacts/sse_sdo/logs/g1_20260219T083354Z.log#a12b7cb43c9d9134b5bb1b35e9096b66775d9e92e7611d1cc92b02edd6782a87

## G2 LAW_POLICE_PRESENT
- §REF:cmd:python -m pytest -q tests/test_policy_to_execution_contract.py -> log:artifacts/sse_sdo/logs/g2_20260219T083354Z.log#99db33d5c94c6f7da021687c7391181685cc33299c5435b1c861e2db3be3ec87

## G3 SSOT_ALIGNMENT
- §REF:cmd:python -m pytest -q tests/test_ssot_alignment_contract.py -> log:artifacts/sse_sdo/logs/g3_20260219T083355Z.log#423b1d0e014eb1eab96f4420f7b344c2615be505dd574b756ac884826ca74f2d

## G4 WORKFLOW_INTEGRITY
- §REF:cmd:python -m pytest -q tests/test_workflow_integrity_contract.py -> log:artifacts/sse_sdo/logs/g4_20260219T083356Z.log#423b1d0e014eb1eab96f4420f7b344c2615be505dd574b756ac884826ca74f2d

## G11 SECURITY_SECRETS_DEPS
- §REF:cmd:scripts/sse_safety_gate -> log:artifacts/sse_sdo/logs/g11_20260219T083357Z.log#a12b7cb43c9d9134b5bb1b35e9096b66775d9e92e7611d1cc92b02edd6782a87

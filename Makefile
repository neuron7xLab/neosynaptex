.PHONY: all clean init validate_contracts test_dynamic verify verify_pr verify_full audit_internal governance_brake test lint format install typecheck reproduce report demo

all: clean init governance_brake validate_contracts audit_internal test_dynamic

clean:
	@echo "Purging non-deterministic artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info dist build .coverage htmlcov .tox .nox

init:
	@echo "Bootstrapping hermetic environment via uv..."
	uv sync --locked --extra test --extra dev

validate_contracts:
	@echo "Parsing invariants.yaml and enforcing traceability..."
	uv run python3 scripts/validate_invariants.py
	uv run ruff check neosynaptex.py core/ contracts/ evl/ tests/


governance_brake:
	@echo "Checking PR-body claim_status contract..."
	uv run python -m tools.audit.pr_body_check pr_body.md

test_dynamic:
	@echo "Executing property-based test matrix..."
	uv run pytest --hypothesis-show-statistics --cov=core --cov-fail-under=95 tests/

install:
	uv sync --locked --extra test --extra dev

test: install
	uv run python3 -m pytest tests/ -v --tb=short --timeout=300

lint:
	uv run ruff check neosynaptex.py core/ contracts/ evl/ tests/
	uv run ruff format --check neosynaptex.py core/ contracts/ evl/ tests/

format:
	uv run ruff format neosynaptex.py core/ contracts/ evl/ tests/

typecheck:
	uv run mypy core/ contracts/ --ignore-missing-imports

verify_pr: install lint test
	uv run python3 -c "from core.axioms import SUBSTRATE_GAMMA, verify_axiom_consistency; gammas=[v[0] for v in SUBSTRATE_GAMMA.values() if v[0] is not None]; subs=[k for k,v in SUBSTRATE_GAMMA.items() if v[0] is not None]; state={'gamma':sum(gammas)/len(gammas),'substrates':subs,'convergence_slope':-0.0016}; assert verify_axiom_consistency(state); print('AXIOM_0: CONSISTENT')"

reproduce: install
	uv run python3 scripts/reproduce.py

demo:
	uv run python3 demo_multi.py

report:
	uv run python3 run_calibration_diagnostic.py
verify_full: install lint test
	uv run python3 -c "from core.axioms import SUBSTRATE_GAMMA, verify_axiom_consistency; gammas=[v[0] for v in SUBSTRATE_GAMMA.values() if v[0] is not None]; subs=[k for k,v in SUBSTRATE_GAMMA.items() if v[0] is not None]; state={'gamma':sum(gammas)/len(gammas),'substrates':subs,'convergence_slope':-0.0016}; assert verify_axiom_consistency(state); print('AXIOM_0: CONSISTENT')"

verify: verify_full

audit_internal: verify_full demo report
	@echo "Internal audit surfaces executed (verify + demo + report)."

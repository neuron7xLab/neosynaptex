.PHONY: all clean init validate_contracts test_dynamic verify audit_internal test lint format install typecheck reproduce report demo

all: clean init audit_internal validate_contracts test_dynamic

clean:
	@echo "Purging non-deterministic artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache *.egg-info dist build .coverage htmlcov .tox .nox

init:
	@echo "Bootstrapping hermetic environment via uv..."
	uv sync --extra test --extra dev

validate_contracts:
	@echo "Parsing invariants.yaml and enforcing traceability..."
	python3 scripts/validate_invariants.py
	ruff check neosynaptex.py core/ contracts/ evl/ tests/


test_dynamic:
	@echo "Executing property-based test matrix..."
	pytest --hypothesis-show-statistics --cov=core --cov-fail-under=95 tests/

install:
	pip install -e ".[dev,test]" --quiet

test: install
	python3 -m pytest tests/ -v --tb=short --timeout=300

lint:
	ruff check neosynaptex.py core/ contracts/ evl/ tests/
	ruff format --check neosynaptex.py core/ contracts/ evl/ tests/

format:
	ruff format neosynaptex.py core/ contracts/ evl/ tests/

typecheck:
	mypy core/ contracts/ --ignore-missing-imports

verify: install lint test
	python3 -c "from core.axioms import SUBSTRATE_GAMMA, verify_axiom_consistency; gammas=[v[0] for v in SUBSTRATE_GAMMA.values() if v[0] is not None]; subs=[k for k,v in SUBSTRATE_GAMMA.items() if v[0] is not None]; state={'gamma':sum(gammas)/len(gammas),'substrates':subs,'convergence_slope':-0.0016}; assert verify_axiom_consistency(state); print('AXIOM_0: CONSISTENT')"

reproduce: install
	python3 scripts/reproduce.py

demo:
	python3 demo_multi.py

report:
	python3 run_calibration_diagnostic.py
audit_internal: verify demo report
	@echo "Internal audit surfaces executed (verify + demo + report)."

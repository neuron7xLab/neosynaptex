.PHONY: verify demo report clean install

install:
	pip install -e ".[dev]" --quiet

verify: install
	python3 -m pytest tests/ -v --tb=short
	python3 core/axioms.py

demo:
	python3 -c "\
from core.axioms import SUBSTRATE_GAMMA, classify_regime; \
print('NFI — Cross-Substrate γ Validation'); \
print('='*50); \
[print(f'{name:20s} γ={gamma:.4f}  |γ-1|={abs(gamma-1.0):.4f}  {classify_regime(gamma)}') for name, (gamma, note) in SUBSTRATE_GAMMA.items()]; \
gammas = [v[0] for v in SUBSTRATE_GAMMA.values()]; \
mean_g = sum(gammas)/len(gammas); \
std_g = (sum((g-mean_g)**2 for g in gammas)/len(gammas))**0.5; \
print(f'\nMean: {mean_g:.4f} ± {std_g:.4f}'); \
print('AXIOM_0: Intelligence = regime, not substrate.')"

report:
	python3 -c "\
from core.axioms import SUBSTRATE_GAMMA, verify_axiom_consistency; \
gammas = [v[0] for v in SUBSTRATE_GAMMA.values()]; \
state = {'gamma': sum(gammas)/len(gammas), 'substrates': list(SUBSTRATE_GAMMA.keys()), 'convergence_slope': -0.0016}; \
result = verify_axiom_consistency(state); \
print(f'NFI STATE: {\"VALID\" if result else \"INVALID\"}'); \
print(f'γ = {state[\"gamma\"]:.4f}'); \
print(f'Substrates: {len(state[\"substrates\"])} independent witnesses'); \
print(f'Motion: slope={state[\"convergence_slope\"]}')"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

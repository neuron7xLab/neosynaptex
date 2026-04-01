# Contributing to neuron7x-agents

## Development setup

```bash
git clone https://github.com/neuron7xLab/neuron7x-agents.git
cd neuron7x-agents
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

All contributions must pass:

```bash
# Tests (99+ tests, <1s)
pytest -v

# Lint (zero errors required)
ruff check src/ tests/

# Type check (strict mode, zero errors)
mypy src/

# Coverage (80% minimum)
pytest --cov=neuron7x_agents --cov-fail-under=80
```

## Architecture

```
primitives/      Shared building blocks (column, confidence, evidence)
cognitive/       NCE: reasoning strategies + engine
regulation/      SERO: hormonal regulation + immune system
verification/    Kriterion: epistemic gates + anti-gaming
agents/          Composed agent blueprints
```

**Design rules:**

1. Every control-theoretic mechanism maps to a numbered equation
2. Every claim about system behavior has a deterministic test
3. Fail-closed: missing evidence = constraint, not gap
4. No metaphors without math behind them

## Commit messages

Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`

## Pull requests

- One logical change per PR
- All quality gates must pass
- New cognitive functions need: implementation + tests + docstrings

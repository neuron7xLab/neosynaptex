# Entrypoints and CUJ

## Critical User Journey (CUJ)
Primary value flow: Discover (`README quickstart`) → Onboard (`pip install -e .[dev]`) → First Value (`bnsyn demo ...`) → Repeat Value (iterate `bnsyn demo` / experiment YAML runs).

## Reproducible local commands
```bash
python -m venv .venv_lpro
source .venv_lpro/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -m "not validation" -q
bnsyn demo --steps 20 --dt-ms 0.1 --seed 123 --N 16
```

Evidence logs are captured in `proof_bundle/logs/phase1_install.log`, `proof_bundle/logs/phase1_pytest.log`, and `proof_bundle/logs/phase1_cuj_demo.log`.

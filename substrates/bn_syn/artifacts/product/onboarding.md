# Onboarding

## New user checklist
1. Install package in fresh environment.
2. Run `bnsyn --help`.
3. Run `bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32`.
4. Confirm JSON output contains `demo`.
5. Run `python -m pytest -m "not validation" -q`.

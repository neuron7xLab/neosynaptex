.PHONY: bn-syn-regime-gate check coherent-induction-v2-gate pfc-coherent-induction-v2-gate
bn-syn-regime-gate:
	python scripts/check_regime_release_gate.py

check:
	python -m pytest -q
	python scripts/check_regime_release_gate.py

coherent-induction-v2-gate:
	PYTHONPATH=src python -m pytest tests/coherent_induction -q

pfc-coherent-induction-v2-gate:
	PYTHONPATH=src python -m pytest tests/test_pfc_coherent_induction.py -q

coherent-induction-v2-automation:
	PYTHONPATH=src python scripts/automate_coherent_induction_v2.py

# BN-Syn Conference Runbook (Release-Ready Demo)

This runbook provides deterministic, offline steps for preparing and presenting the BN-Syn demo.
All commands are designed for reproducibility and auditability.

## Preconditions

- Python 3.11+
- Virtual environment activated
- Repository at a clean commit

## 1) Install Dependencies

```bash
pip install -e ".[dev,viz]"
```

## 2) Release Readiness Report (Blocking)

```bash
python -m scripts.release_readiness
```

**Expected output:**
- `artifacts/release_readiness.json`
- `artifacts/release_readiness.md`
- Terminal message: `Release readiness: READY`

If the report is `BLOCKED`, resolve missing files before proceeding.

## 3) Deterministic Demo Run (Primary)

```bash
bnsyn sleep-stack --seed 123 --steps-wake 240 --steps-sleep 180 --out results/demo_rc
```

**Expected outputs**
- `results/demo_rc/manifest.json`
- `results/demo_rc/metrics.json`
- `results/demo_rc/summary.json`
- `figures/demo_rc/summary.png` (if `matplotlib` installed)

## 4) Fast Sanity Demo (Backup)

```bash
bnsyn sleep-stack --seed 7 --steps-wake 60 --steps-sleep 40 --out results/demo_smoke
```

**Expected outputs**
- `results/demo_smoke/manifest.json`
- `results/demo_smoke/metrics.json`
- `results/demo_smoke/summary.json`

## 5) Determinism Spot-Check (Optional)

Re-run the primary demo with the same seed and confirm that metrics match:

```bash
bnsyn sleep-stack --seed 123 --steps-wake 240 --steps-sleep 180 --out results/demo_rc_repeat
```

Compare `results/demo_rc/metrics.json` and `results/demo_rc_repeat/metrics.json`.

## 6) Conference Presentation Notes

- Use the deterministic seed (`123`) for repeatable visuals.
- Avoid network access during the demo; all artifacts are generated locally.
- If visual output is unavailable (missing `matplotlib`), present the JSON metrics and manifest files.

## 7) Post-Demo Cleanup (Optional)

```bash
rm -rf results/demo_rc results/demo_rc_repeat results/demo_smoke figures/demo_rc
```

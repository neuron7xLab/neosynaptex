# Data Provenance — BN-Syn

## artifacts/math_audit/manifest.json
- Generator: `python scripts/generate_math_data.py`
- Seed: N/A (deterministic filesystem walk)
- Dependencies: repository tracked files in `results/`, `benchmarks/`, `docs/`, `src/`, root config files
- Reproduction: `python scripts/generate_math_data.py`
- Checksum (SHA256): `c0b7c1825238dbba95e2bd1eb4c247fa64bef115da10d9ab798c79dbe3fda7af`

## artifacts/math_audit/validator_report.json
- Generator: `python scripts/math_validate.py`
- Seed: N/A (deterministic contract execution)
- Dependencies: `artifacts/math_audit/manifest.json`, contract set in `src/contracts/math_contracts.py`
- Reproduction: `python scripts/math_validate.py`
- Checksum (SHA256): `e446191a8ea00380312ebcb8ea6bc3375c43074e4de437806da41599518e5db7`

## artifacts/math_audit/validator_report.md
- Generator: `python scripts/math_validate.py`
- Seed: N/A
- Dependencies: validator execution results
- Reproduction: `python scripts/math_validate.py`
- Checksum (SHA256): `c0a9eaaf814cc40181ffadc17719653950d017ea596ed8ac619d27ccc770b1ae`

## artifacts/math_audit/baseline_env.txt
- Generator: phase-0 environment baseline command block
- Seed: N/A
- Dependencies: local Python/pip/runtime platform and installed packages
- Reproduction:
  - `python --version`
  - `python -m pip --version`
  - `python -c "import platform; print(platform.platform())"`
  - `python -m pip freeze`
- Checksum (SHA256): `a719e4b5d759d2017c565db33a99cb2113b228cd3f5efbc9259f0e468ed55105`

## artifacts/math_audit/phase_a_audit.txt
- Generator: Phase A audit command bundle
- Seed: N/A
- Dependencies: repository file inventory and command outputs
- Reproduction: rerun Phase A command block from task specification
- Checksum (SHA256): `cd78d067b710b45ddbc6d0c15d2c15ac8a4538f504c2b95acf3602eea980d46d`

## artifacts/math_audit/hardened_run.log
- Generator: `python scripts/math_validate.py 2>&1 | tee artifacts/math_audit/hardened_run.log`
- Seed: N/A
- Dependencies: validator runtime output stream
- Reproduction: command above
- Checksum (SHA256): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

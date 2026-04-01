# EVIDENCE INDEX

- G00: §REF:cmd:python -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in sorted(pathlib.Path('.github/workflows').glob('*.yml'))]" -> log:artifacts/ghtpo/logs/G00.log#sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- G11: §REF:cmd:python -m pytest -m "not (validation or property)" -q -> log:artifacts/ghtpo/logs/G11.log#sha256:819bcade02556461f3c2f6458dad02c273ee55b9e200eaaf29bca79b639d2897
- G12: §REF:cmd:ruff check . -> log:artifacts/ghtpo/logs/G12.log#sha256:82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18
- G12B: §REF:cmd:pylint src/bnsyn -> log:artifacts/ghtpo/logs/G12B.log#sha256:8fda5322955f2f888fc8b5c784bc7736930700db56fb1dad3d417b9033d96535
- G14: §REF:cmd:mypy src --strict --config-file pyproject.toml -> log:artifacts/ghtpo/logs/G14.log#sha256:25499469eab292b707aaafb426bb37ffc20ebb6f29a73f5d9ab147221e899cc4
- G15: §REF:cmd:python -m build -> log:artifacts/ghtpo/logs/G15.log#sha256:b930f283c0a4af1ca915dcc06cd86bee7a220b7fe84c037a65c252208974d63f
- G17: §REF:cmd:python -m pytest -q tests/test_ci_policy_contract.py -> log:artifacts/ghtpo/logs/G17.log#sha256:cf426ab35f3b06fccef8290fde5325d90af130a79da1d1752031518df77c4236

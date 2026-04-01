# Production Readiness Runbook

## Canonical Commands
- `make install`
- `make build`
- `make test`
- `make lint`
- `make mypy`
- `make security`
- `make sbom`
- `make release`
- `make cleanroom`

## Clean-room sequence
1. `make install`
2. `make build`
3. `make test`
4. `bnsyn demo --steps 50 --dt-ms 0.1 --seed 123 --N 16`
5. `make security`
6. `make sbom`
7. `make release`

All command transcripts are in `artifacts/prod_ready/logs/` and mirrored to `proof_bundle/logs/`.

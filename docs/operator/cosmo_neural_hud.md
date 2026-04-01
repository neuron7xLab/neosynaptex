# NEOSYNAPTEX COSMO-NEURAL HUD

Repo-native cockpit for shell + tmux.

## Enable / Disable

- Enable: `bash tools/hud/install.sh && source ~/.bashrc`
- Disable (rollback): `bash tools/hud/uninstall.sh && source ~/.bashrc`

The installer writes a bounded marker block into `~/.bashrc` and `~/.tmux.conf`; no full-file overwrite.

## Signals rendered in prompt

- repo identity (`NEO`)
- branch
- dirty/clean status
- cwd subsystem layer (`root_integration`, `agents`, `bn_syn`, `hippocampal_ca1`, `mlsdm`, `mfn_plus`, `kuramoto`, `docs`, `manuscript`, `tools_scripts`)
- cognitive risk state (`STABLE`, `DIRTY`, `DRIFT`, `UNVERIFIED`, `BLOCKED`, `DETACHED`, `CONFLICT`)
- last meaningful action (`verify`, `bench`, `commit`, `push`, `sync`, `install`)
- wall clock time

## Fast commands

- `neo` – dashboard snapshot
- `nv` / `nt` – verify current layer / targeted test run
- `ncd <layer>` – jump to major subsystem
- `neo-map` – show repository subsystem map
- `neo-evidence` – recent git/action evidence
- `neo-refresh` – force prompt recompute
- `neo-enable` / `neo-disable` – toggle in current shell
- `neo-help` – command summary

## Palette

- void `#050505`
- field `#111111`
- field-2 `#1C1C1C`
- signal `#00F0FF`
- anomaly `#FF006E`
- stable `#00FF9C`
- warning `#FFB000`
- danger `#FF3B3B`
- foreground `#EAEAEA`

## Operational notes

- Action and verify evidence is stored under `~/.cache/neosynaptex-hud/`.
- Verify freshness defaults to 30 minutes (`NEO_HUD_VERIFY_STALE_SECONDS` in `tools/hud/hud.conf`).

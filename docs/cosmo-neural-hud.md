# NEOSYNAPTEX COSMO-NEURAL HUD

AI Engineering Cockpit — cognitive-state-aware terminal system for neosynaptex development.

## What it is

A shell + tmux integration layer that transforms the terminal into a repo-aware engineering cockpit with:
- **Cognitive state signaling** — computed from git state, last command exit, verify freshness
- **Layer detection** — knows which subsystem you're working in (bn_syn, hca1, mlsdm, mfn+, kuramoto, etc.)
- **Last action trace** — tracks meaningful engineering actions (test, commit, push, lint, build)
- **Disciplined palette** — void black, signal cyan, event magenta, stability green, danger red, warning amber
- **Fast commands** — single-letter aliases for high-frequency repo operations

## Enable

```bash
bash tools/hud/install.sh
source ~/.bashrc
```

## Disable / Rollback

```bash
bash tools/hud/uninstall.sh
```

Backups of `.bashrc` and `.tmux.conf` are stored in `~/.local/share/neo-hud-backup/`.

## Cognitive States

| State        | Color   | Meaning                                           |
|-------------|---------|---------------------------------------------------|
| `STABLE`    | green   | Clean working tree, no errors                     |
| `DIRTY`     | amber   | Uncommitted changes, recently verified            |
| `DRIFT`     | magenta | Uncommitted changes, no recent verify             |
| `UNVERIFIED`| amber   | Changes present, last verify older than 5 minutes |
| `ERROR`     | red     | Last command exited non-zero                      |
| `BLOCKED`   | red     | Merge conflict detected                           |
| `DETACHED`  | red     | HEAD is detached                                  |

## Layer Detection

The HUD detects which subsystem you're in based on your current working directory:

| Directory pattern     | Label     | Color          |
|----------------------|-----------|----------------|
| `neosynaptex`        | `core`    | cyan           |
| `bn_syn`, `bnsyn`   | `bn_syn`  | magenta        |
| `hippocampal`, `hca1`| `hca1`    | violet         |
| `mlsdm`             | `mlsdm`   | teal           |
| `mfn_plus`, `mfn+`  | `mfn+`    | orange         |
| `kuramoto`          | `kuramoto` | light blue    |
| `agent`             | `agents`  | gold           |
| `doc`, `manuscript` | `docs`    | dim            |
| `test`              | `tests`   | green          |
| `tools`, `script`   | `tools`   | dim            |
| repo root           | `root`    | cyan           |
| outside repo        | `ext`     | neutral        |

## Commands

| Command    | Action                              |
|-----------|-------------------------------------|
| `neo`     | Full status dashboard               |
| `nv`      | Verify — run tests                  |
| `nt`      | Targeted tests (pass args)          |
| `nl`      | Recent evidence (git log graph)     |
| `nm`      | Repo file map                       |
| `ncd`     | Jump to repo root or subsystem      |
| `nd`      | Show dirty files                    |
| `neo-help`| Show all commands and states        |

## Prompt Format

```
┌ [NEO] layer :: branch ∴ STATE ⟡ action
└ ❯
```

## tmux Status Line

```
 ⟡ NEO │ session │ windows │ branch │ HH:MM
```

## Palette

| Name     | Hex       | Usage                |
|----------|-----------|----------------------|
| void     | `#050505` | background           |
| field    | `#0A0A0F` | tmux status bg       |
| cyan     | `#00F0FF` | primary signal       |
| magenta  | `#FF006E` | anomaly / event      |
| green    | `#00FF9C` | stability / pass     |
| red      | `#FF3B3B` | danger / error       |
| amber    | `#FFB000` | warning / dirty      |
| dim      | `#505570` | structural / borders |
| fg       | `#C8C8D2` | text                 |

## Customization

Edit `tools/hud/hud.sh` to modify:
- Colors: `_C_CYAN`, `_C_MAG`, etc. (true-color escape sequences)
- Layer patterns: `_neo_layer()` function
- State logic: `_neo_state()` function
- Verify timeout: currently 300 seconds (5 minutes)

Edit `tools/hud/tmux-hud.conf` for tmux appearance.

## Architecture

```
tools/hud/
├── hud.sh           # Shell library (sourced by bashrc)
├── tmux-hud.conf    # tmux configuration
├── install.sh       # Enable locally
└── uninstall.sh     # Disable / rollback
```

Local integration:
- `.bashrc`: source block injected between markers `# >>> neosynaptex-hud >>>` / `# <<< neosynaptex-hud <<<`
- `.tmux.conf`: replaced (backup preserved)
- Temp files: `/tmp/.neo_last_action`, `/tmp/.neo_last_verify_ts`

## Requirements

- bash 4+
- git
- tmux 3+ (optional, for status bar)
- Terminal with true color support (gnome-terminal, kitty, alacritty, wezterm)

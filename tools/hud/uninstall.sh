#!/usr/bin/env bash
set -euo pipefail

HUD_DIR="$(cd "$(dirname "$0")" && pwd)"
BASHRC="${HOME}/.bashrc"
TMUX_CONF="${HOME}/.tmux.conf"
MARK_START="# >>> neosynaptex-cosmo-neural-hud >>>"
MARK_END="# <<< neosynaptex-cosmo-neural-hud <<<"

[[ -f "$BASHRC" ]] && sed -i "/$MARK_START/,/$MARK_END/d" "$BASHRC"
[[ -f "$TMUX_CONF" ]] && sed -i "/$MARK_START/,/$MARK_END/d" "$TMUX_CONF"

rm -f "${HOME}/.cache/neosynaptex-hud/last_action.tsv" "${HOME}/.cache/neosynaptex-hud/state.tsv"

echo "HUD disabled. Run: source ~/.bashrc"
echo "Manual current-shell disable: neo-disable"

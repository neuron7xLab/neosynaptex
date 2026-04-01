#!/usr/bin/env bash
set -euo pipefail

HUD_DIR="$(cd "$(dirname "$0")" && pwd)"
BASHRC="${HOME}/.bashrc"
TMUX_CONF="${HOME}/.tmux.conf"
MARK_START="# >>> neosynaptex-cosmo-neural-hud >>>"
MARK_END="# <<< neosynaptex-cosmo-neural-hud <<<"

mkdir -p "${HOME}/.cache/neosynaptex-hud"
touch "$BASHRC"
tail -c1 "$BASHRC" | read -r _ || printf '\n' >>"$BASHRC"

if grep -q "$MARK_START" "$BASHRC"; then
  sed -i "/$MARK_START/,/$MARK_END/d" "$BASHRC"
fi
printf '\n' >>"$BASHRC"
cat >>"$BASHRC" <<EOF2
$MARK_START
# repo-local integration for NEOSYNAPTEX COSMO-NEURAL HUD
if [[ -f "$HUD_DIR/hud.sh" ]]; then
  source "$HUD_DIR/hud.sh"
fi
$MARK_END
EOF2

if [[ -f "$TMUX_CONF" ]] && grep -q "$MARK_START" "$TMUX_CONF"; then
  sed -i "/$MARK_START/,/$MARK_END/d" "$TMUX_CONF"
fi
touch "$TMUX_CONF"
tail -c1 "$TMUX_CONF" | read -r _ || printf '\n' >>"$TMUX_CONF"
printf '\n' >>"$TMUX_CONF"
cat >>"$TMUX_CONF" <<EOF2
$MARK_START
if-shell '[ -f "$HUD_DIR/tmux-hud.conf" ]' 'source-file "$HUD_DIR/tmux-hud.conf"'
$MARK_END
EOF2

if command -v tmux >/dev/null 2>&1 && tmux list-sessions >/dev/null 2>&1; then
  tmux source-file "$TMUX_CONF" || true
fi

echo "HUD enabled. Run: source ~/.bashrc"
echo "Rollback: ${HUD_DIR}/uninstall.sh"

#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════╗
# ║  NEOSYNAPTEX COSMO-NEURAL HUD — Installer                        ║
# ║  Enables the HUD locally. Reversible via uninstall.sh             ║
# ╚═══════════════════════════════════════════════════════════════════╝
set -euo pipefail

HUD_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HUD_DIR/../.." && pwd)"

BASHRC="$HOME/.bashrc"
TMUX_CONF="$HOME/.tmux.conf"
BACKUP_DIR="$HOME/.local/share/neo-hud-backup"

C=$'\033[38;2;0;240;255m'
M=$'\033[38;2;255;0;110m'
D=$'\033[38;2;80;85;110m'
R=$'\033[0m'
B=$'\033[1m'

echo -e "${C}${B}  NEOSYNAPTEX COSMO-NEURAL HUD${R}"
echo -e "${D}  ═══════════════════════════════${R}"
echo

# ── Backup ───────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

if [[ -f "$BASHRC" ]]; then
    cp "$BASHRC" "$BACKUP_DIR/bashrc.bak.$(date +%s)"
    echo -e "  ${D}→ backed up${R} ${C}.bashrc${R}"
fi

if [[ -f "$TMUX_CONF" ]]; then
    cp "$TMUX_CONF" "$BACKUP_DIR/tmux.conf.bak.$(date +%s)"
    echo -e "  ${D}→ backed up${R} ${C}.tmux.conf${R}"
fi

# ── Bashrc integration ──────────────────────────────────────────────
MARKER_START="# >>> neosynaptex-hud >>>"
MARKER_END="# <<< neosynaptex-hud <<<"

# Remove old block if present
if grep -q "$MARKER_START" "$BASHRC" 2>/dev/null; then
    sed -i "/$MARKER_START/,/$MARKER_END/d" "$BASHRC"
fi

cat >> "$BASHRC" << EOF

$MARKER_START
# NEOSYNAPTEX COSMO-NEURAL HUD — auto-sourced
# To disable: run $HUD_DIR/uninstall.sh
if [[ -f "$HUD_DIR/hud.sh" ]]; then
    source "$HUD_DIR/hud.sh"
fi
$MARKER_END
EOF

echo -e "  ${D}→ injected${R} ${C}hud.sh${R} ${D}into .bashrc${R}"

# ── tmux integration ────────────────────────────────────────────────
# Replace tmux.conf with HUD config (backup already taken)
cp "$HUD_DIR/tmux-hud.conf" "$TMUX_CONF"
echo -e "  ${D}→ installed${R} ${C}tmux-hud.conf${R} ${D}→ .tmux.conf${R}"

# Reload tmux if running
if tmux list-sessions &>/dev/null; then
    tmux source-file "$TMUX_CONF" 2>/dev/null && \
        echo -e "  ${D}→ reloaded${R} ${C}tmux${R}" || true
fi

# ── FZF theme integration ───────────────────────────────────────────
# Update FZF colors to match palette (already in bashrc via marker block)
# FZF picks up FZF_DEFAULT_OPTS from bashrc

echo
echo -e "  ${C}${B}∴ HUD ENABLED${R}"
echo -e "  ${D}Open a new terminal or run:${R} ${C}source ~/.bashrc${R}"
echo -e "  ${D}For tmux:${R} ${C}tmux${R} ${D}or${R} ${C}tmux source ~/.tmux.conf${R}"
echo -e "  ${D}Rollback:${R} ${M}$HUD_DIR/uninstall.sh${R}"
echo -e "  ${D}Backups:${R} ${D}$BACKUP_DIR/${R}"
echo

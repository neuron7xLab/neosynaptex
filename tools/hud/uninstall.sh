#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════╗
# ║  NEOSYNAPTEX COSMO-NEURAL HUD — Uninstaller / Rollback           ║
# ║  Removes HUD integration and restores backups.                    ║
# ╚═══════════════════════════════════════════════════════════════════╝
set -euo pipefail

BASHRC="$HOME/.bashrc"
TMUX_CONF="$HOME/.tmux.conf"
BACKUP_DIR="$HOME/.local/share/neo-hud-backup"

C=$'\033[38;2;0;240;255m'
M=$'\033[38;2;255;0;110m'
D=$'\033[38;2;80;85;110m'
R=$'\033[0m'
B=$'\033[1m'

echo -e "${C}${B}  NEOSYNAPTEX HUD — Rollback${R}"
echo -e "${D}  ═══════════════════════════════${R}"
echo

# ── Remove bashrc block ─────────────────────────────────────────────
MARKER_START="# >>> neosynaptex-hud >>>"
MARKER_END="# <<< neosynaptex-hud <<<"

if grep -q "$MARKER_START" "$BASHRC" 2>/dev/null; then
    sed -i "/$MARKER_START/,/$MARKER_END/d" "$BASHRC"
    echo -e "  ${D}→ removed${R} ${C}HUD block${R} ${D}from .bashrc${R}"
else
    echo -e "  ${D}→ no HUD block found in .bashrc${R}"
fi

# ── Restore tmux.conf from backup ───────────────────────────────────
if [[ -d "$BACKUP_DIR" ]]; then
    LATEST_TMUX=$(ls -t "$BACKUP_DIR"/tmux.conf.bak.* 2>/dev/null | head -1)
    if [[ -n "$LATEST_TMUX" ]]; then
        cp "$LATEST_TMUX" "$TMUX_CONF"
        echo -e "  ${D}→ restored${R} ${C}.tmux.conf${R} ${D}from backup${R}"
    else
        echo -e "  ${D}→ no tmux backup found${R}"
    fi
else
    echo -e "  ${D}→ no backup directory found${R}"
fi

# ── Clean up temp files ──────────────────────────────────────────────
rm -f /tmp/.neo_last_action /tmp/.neo_last_verify_ts
echo -e "  ${D}→ cleaned temp files${R}"

# ── Unset env var ────────────────────────────────────────────────────
unset _NEO_HUD_ACTIVE 2>/dev/null || true

echo
echo -e "  ${M}${B}∴ HUD DISABLED${R}"
echo -e "  ${D}Open a new terminal to apply changes.${R}"
echo -e "  ${D}Backups remain in:${R} ${D}$BACKUP_DIR/${R}"
echo

#!/usr/bin/env bash
# shellcheck shell=bash
# NEOSYNAPTEX COSMO-NEURAL HUD

[[ -n "${_NEO_HUD_ACTIVE:-}" ]] && return 0
export _NEO_HUD_ACTIVE=1

_NEO_HUD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NEO_REPO_ROOT="$(cd "${_NEO_HUD_DIR}/../.." && pwd)"
# shellcheck disable=SC1091
source "${_NEO_HUD_DIR}/hud.conf"
mkdir -p "$(dirname "${NEO_HUD_TRACK_FILE}")"

_neo_hex_to_rgb() {
  local hex="${1#\#}"
  printf '%d;%d;%d' "0x${hex:0:2}" "0x${hex:2:2}" "0x${hex:4:2}"
}

_neo_c() { printf '\033[38;2;%sm' "$( _neo_hex_to_rgb "$1" )"; }
_neo_cp() { printf '\[\033[38;2;%sm\]' "$( _neo_hex_to_rgb "$1" )"; }

_C_SIGNAL="$(_neo_c "$NEO_HUD_COLOR_SIGNAL")"
_C_ANOM="$(_neo_c "$NEO_HUD_COLOR_ANOMALY")"
_C_STABLE="$(_neo_c "$NEO_HUD_COLOR_STABLE")"
_C_WARN="$(_neo_c "$NEO_HUD_COLOR_WARNING")"
_C_DANGER="$(_neo_c "$NEO_HUD_COLOR_DANGER")"
_C_DIM="$(_neo_c "$NEO_HUD_COLOR_DIM")"
_C_FG="$(_neo_c "$NEO_HUD_COLOR_FOREGROUND")"
_C_B=$'\033[1m'
_C_R=$'\033[0m'

_P_SIGNAL="$(_neo_cp "$NEO_HUD_COLOR_SIGNAL")"
_P_ANOM="$(_neo_cp "$NEO_HUD_COLOR_ANOMALY")"
_P_STABLE="$(_neo_cp "$NEO_HUD_COLOR_STABLE")"
_P_WARN="$(_neo_cp "$NEO_HUD_COLOR_WARNING")"
_P_DANGER="$(_neo_cp "$NEO_HUD_COLOR_DANGER")"
_P_DIM="$(_neo_cp "$NEO_HUD_COLOR_DIM")"
_P_FG="$(_neo_cp "$NEO_HUD_COLOR_FOREGROUND")"
_P_B='\[\033[1m\]'
_P_R='\[\033[0m\]'

_neo_layer() {
  local rel
  case "$PWD" in
    "${_NEO_REPO_ROOT}"/*|"${_NEO_REPO_ROOT}") ;;
    *) echo external; return ;;
  esac

  rel="${PWD#"${_NEO_REPO_ROOT}"}"; rel="${rel#/}"
  [[ -z "$rel" ]] && { echo root_integration; return; }

  case "$rel" in
    agents|agents/*|*/agents/*) echo agents ;;
    bn_syn|bn_syn/*|substrates/bn_syn|substrates/bn_syn/*|*/bn_syn/*) echo bn_syn ;;
    substrates/hippocampal_ca1|substrates/hippocampal_ca1/*|hippocampal_ca1|hippocampal_ca1/*) echo hippocampal_ca1 ;;
    substrates/mlsdm|substrates/mlsdm/*|mlsdm|mlsdm/*) echo mlsdm ;;
    substrates/mfn_plus|substrates/mfn_plus/*|mfn_plus|mfn_plus/*) echo mfn_plus ;;
    substrates/kuramoto|substrates/kuramoto/*|kuramoto|kuramoto/*) echo kuramoto ;;
    docs|docs/*) echo docs ;;
    manuscript|manuscript/*) echo manuscript ;;
    tools|tools/*|scripts|scripts/*|*/scripts/*) echo tools_scripts ;;
    *) echo root_integration ;;
  esac
}

_neo_layer_color() {
  case "$1" in
    root_integration) echo "$_P_SIGNAL" ;;
    agents) echo "$_P_WARN" ;;
    bn_syn) echo "$_P_ANOM" ;;
    hippocampal_ca1) echo '\[\033[38;2;168;140;255m\]' ;;
    mlsdm) echo '\[\033[38;2;0;210;190m\]' ;;
    mfn_plus) echo '\[\033[38;2;255;132;56m\]' ;;
    kuramoto) echo '\[\033[38;2;120;190;255m\]' ;;
    docs|manuscript|tools_scripts) echo "$_P_DIM" ;;
    *) echo "$_P_FG" ;;
  esac
}

_neo_git_snapshot() {
  local branch dirty detached conflict
  branch="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
  if [[ -z "$branch" ]]; then
    detached=1
    branch="$(git rev-parse --short HEAD 2>/dev/null || echo '∅')"
  else
    detached=0
  fi

  dirty=0
  git diff --quiet --ignore-submodules HEAD -- 2>/dev/null || dirty=1
  git diff --cached --quiet --ignore-submodules HEAD -- 2>/dev/null || dirty=1
  [[ -n "$(git ls-files --others --exclude-standard 2>/dev/null | head -n 1)" ]] && dirty=1

  conflict=0
  local gd
  gd="$(git rev-parse --git-dir 2>/dev/null || true)"
  if [[ -n "$gd" ]] && { [[ -f "$gd/MERGE_HEAD" ]] || [[ -d "$gd/rebase-merge" ]] || [[ -d "$gd/rebase-apply" ]]; }; then
    conflict=1
  fi
  printf '%s\t%s\t%s\t%s\n' "$branch" "$dirty" "$detached" "$conflict"
}

_neo_last_verify_status() {
  [[ -f "$NEO_HUD_STATE_FILE" ]] || { echo none; return; }
  awk -F '\t' '$1=="verify"{print $2"\t"$3; exit}' "$NEO_HUD_STATE_FILE" 2>/dev/null || echo none
}

_neo_risk_state() {
  local dirty="$1" detached="$2" conflict="$3" last_rc="$4"
  if [[ "$conflict" -eq 1 ]]; then echo CONFLICT; return; fi
  if [[ "$detached" -eq 1 ]]; then echo DETACHED; return; fi
  if [[ "$last_rc" -ne 0 ]]; then echo BLOCKED; return; fi

  local verify ts now
  verify="$(_neo_last_verify_status)"
  if [[ "$dirty" -eq 1 ]]; then
    if [[ "$verify" == none ]]; then echo DRIFT; return; fi
    ts="${verify%%$'\t'*}"
    now="$(date +%s)"
    if (( now - ts > NEO_HUD_VERIFY_STALE_SECONDS )); then
      echo UNVERIFIED
    else
      echo DIRTY
    fi
    return
  fi

  if [[ "$verify" != none ]] && [[ "${verify#*$'\t'}" != "0" ]]; then
    echo BLOCKED
  else
    echo STABLE
  fi
}

_neo_state_color() {
  case "$1" in
    STABLE) echo "$_P_STABLE" ;;
    DIRTY|UNVERIFIED) echo "$_P_WARN" ;;
    DRIFT) echo "$_P_ANOM" ;;
    CONFLICT|DETACHED|BLOCKED) echo "$_P_DANGER" ;;
    *) echo "$_P_DIM" ;;
  esac
}

_neo_trace_action() {
  local raw="$1" rc="$2" kind="cmd"
  [[ -z "$raw" ]] && return
  case "$raw" in
    *pytest*|*" -m pytest"*|make\ test*|make\ verify*|tox*) kind=verify ;;
    *benchmark*|*hyperfine*|*asv\ run*) kind=bench ;;
    git\ commit*|git\ ci*) kind=commit ;;
    git\ push*) kind=push ;;
    git\ pull*|git\ fetch*|git\ submodule\ update*) kind=sync ;;
    pip\ install*|uv\ sync*|poetry\ install*) kind=install ;;
  esac
  printf '%s\t%s\t%s\t%s\n' "$(date +%s)" "$kind" "$rc" "$raw" >"$NEO_HUD_TRACK_FILE"
  if [[ "$kind" == verify ]]; then
    printf 'verify\t%s\t%s\n' "$(date +%s)" "$rc" >"$NEO_HUD_STATE_FILE"
  fi
}

_neo_last_action() {
  [[ -f "$NEO_HUD_TRACK_FILE" ]] || { echo none; return; }
  awk -F '\t' '{print $2"("$3")"}' "$NEO_HUD_TRACK_FILE" 2>/dev/null
}

_neo_prompt() {
  local last_rc=$?
  history -a
  local cmd
  cmd=$(HISTTIMEFORMAT='' history 1 | sed 's/^[ ]*[0-9]\+[ ]*//')
  _neo_trace_action "$cmd" "$last_rc"

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    PS1="${_P_DIM}[${_P_SIGNAL}NEO${_P_DIM}] ${_P_FG}\\W${_P_R}\n${_P_SIGNAL}❯${_P_R} "
    return
  fi

  local branch dirty detached conflict
  IFS=$'\t' read -r branch dirty detached conflict < <(_neo_git_snapshot)
  local layer state lcol scol action
  layer="$(_neo_layer)"
  state="$(_neo_risk_state "$dirty" "$detached" "$conflict" "$last_rc")"
  lcol="$(_neo_layer_color "$layer")"
  scol="$(_neo_state_color "$state")"
  action="$(_neo_last_action)"

  PS1="${_P_DIM}┌[${_P_SIGNAL}${_P_B}NEO${_P_R}${_P_DIM}] ${lcol}${layer}${_P_DIM} • ${_P_ANOM}${branch}${_P_DIM} • ${scol}${_P_B}${state}${_P_R}${_P_DIM} • ${_P_FG}${action}${_P_DIM} • ${_P_FG}\\A${_P_R}"
  PS1+="\n${_P_DIM}└${scol}❯${_P_R} "
}

PROMPT_COMMAND="_neo_prompt"

neo-refresh() { _neo_prompt; printf '%b\n' "${_C_SIGNAL}HUD refreshed${_C_R}"; }
neo-enable() { source "${_NEO_HUD_DIR}/hud.sh"; }
neo-disable() { unset PROMPT_COMMAND; export PS1='\u@\h:\w\\$ '; }
neo-map() { find "$_NEO_REPO_ROOT" -maxdepth 2 -type d | sed "s#^${_NEO_REPO_ROOT}#.#" | sort; }
neo-evidence() { git -C "$_NEO_REPO_ROOT" log --oneline --decorate -n 12; [[ -f "$NEO_HUD_TRACK_FILE" ]] && tail -n 5 "$NEO_HUD_TRACK_FILE"; }
neo-layer() { _neo_layer; }

nv() {
  local layer
  layer="$(_neo_layer)"
  case "$layer" in
    bn_syn)
      (cd "$_NEO_REPO_ROOT/substrates/bn_syn" && python -m pytest -m "not (validation or property)" -q "$@") ;;
    agents)
      (cd "$_NEO_REPO_ROOT/agents" && python -m pytest -q "$@") ;;
    *)
      (cd "$_NEO_REPO_ROOT" && python -m pytest -q "$@") ;;
  esac
}

nt() { nv "$@"; }
ncd() {
  local target="$1"
  case "$target" in
    ''|root) cd "$_NEO_REPO_ROOT" ;;
    agents) cd "$_NEO_REPO_ROOT/agents" ;;
    bn|bn_syn) cd "$_NEO_REPO_ROOT/substrates/bn_syn" ;;
    hca1) cd "$_NEO_REPO_ROOT/substrates/hippocampal_ca1" ;;
    mlsdm) cd "$_NEO_REPO_ROOT/substrates/mlsdm" ;;
    mfn|mfn_plus) cd "$_NEO_REPO_ROOT/substrates/mfn_plus" ;;
    kura|kuramoto) cd "$_NEO_REPO_ROOT/substrates/kuramoto" ;;
    docs) cd "$_NEO_REPO_ROOT/docs" ;;
    manuscript) cd "$_NEO_REPO_ROOT/manuscript" ;;
    tools|scripts) cd "$_NEO_REPO_ROOT/tools" ;;
    *) printf '%b\n' "${_C_WARN}Unknown layer: ${target}${_C_R}"; return 1 ;;
  esac
}

neo() {
  local branch dirty detached conflict
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%b\n' "${_C_WARN}Outside git repo${_C_R}"; return 1
  fi
  IFS=$'\t' read -r branch dirty detached conflict < <(_neo_git_snapshot)
  local layer state verify action
  layer="$(_neo_layer)"
  state="$(_neo_risk_state "$dirty" "$detached" "$conflict" 0)"
  verify="$(_neo_last_verify_status)"
  action="$(_neo_last_action)"
  printf '%b\n' "${_C_SIGNAL}${_C_B}NEOSYNAPTEX COSMO-NEURAL HUD${_C_R}"
  printf ' layer      %s\n branch     %s\n dirty      %s\n risk       %s\n last       %s\n verify     %s\n time       %s\n' \
    "$layer" "$branch" "$dirty" "$state" "$action" "$verify" "$(date '+%Y-%m-%d %H:%M:%S')"
}

neo-help() {
  cat <<'TXT'
NEOSYNAPTEX HUD commands
  neo            dashboard snapshot
  nv / nt        verify current layer / targeted tests
  ncd <layer>    jump layer (root|agents|bn_syn|hca1|mlsdm|mfn_plus|kuramoto|docs|manuscript|tools)
  neo-map        subsystem map
  neo-evidence   recent git+action evidence
  neo-refresh    recompute prompt state
  neo-enable     source HUD in current shell
  neo-disable    disable prompt HUD for current shell
TXT
}

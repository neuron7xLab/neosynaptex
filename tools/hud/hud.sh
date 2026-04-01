#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════╗
# ║  NEOSYNAPTEX COSMO-NEURAL HUD                                    ║
# ║  AI Engineering Cockpit — Shell Layer                             ║
# ║  Source this file to activate.                                    ║
# ╚═══════════════════════════════════════════════════════════════════╝

# Guard: don't double-source
[[ -n "$_NEO_HUD_ACTIVE" ]] && return 0
export _NEO_HUD_ACTIVE=1

# ── Resolve HUD root ────────────────────────────────────────────────
_NEO_HUD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NEO_REPO_ROOT="$(cd "$_NEO_HUD_DIR/../.." && pwd)"

# ── Palette (true color) ────────────────────────────────────────────
_C_CYAN=$'\033[38;2;0;240;255m'
_C_MAG=$'\033[38;2;255;0;110m'
_C_GRN=$'\033[38;2;0;255;156m'
_C_RED=$'\033[38;2;255;59;59m'
_C_AMB=$'\033[38;2;255;176;0m'
_C_DIM=$'\033[38;2;80;85;110m'
_C_FG=$'\033[38;2;200;200;210m'
_C_B=$'\033[1m'
_C_R=$'\033[0m'

# PS1 palette (with \[ \] escapes for readline)
_P_CYAN='\[\033[38;2;0;240;255m\]'
_P_MAG='\[\033[38;2;255;0;110m\]'
_P_GRN='\[\033[38;2;0;255;156m\]'
_P_RED='\[\033[38;2;255;59;59m\]'
_P_AMB='\[\033[38;2;255;176;0m\]'
_P_DIM='\[\033[38;2;80;85;110m\]'
_P_FG='\[\033[38;2;200;200;210m\]'
_P_B='\[\033[1m\]'
_P_R='\[\033[0m\]'

# ── Layer detection ──────────────────────────────────────────────────
_neo_layer() {
    local cwd="$PWD" rel
    # Fast: are we inside the neosynaptex repo at all?
    case "$cwd" in
        "$_NEO_REPO_ROOT"*) ;;
        *) echo "ext"; return ;;
    esac
    rel="${cwd#"$_NEO_REPO_ROOT"}"
    rel="${rel#/}"
    [[ -z "$rel" ]] && { echo "root"; return; }

    # Match known subsystem paths
    case "$rel" in
        *bn_syn*|*bnsyn*)          echo "bn_syn" ;;
        *hippocampal*|*hca1*)      echo "hca1" ;;
        *mlsdm*)                   echo "mlsdm" ;;
        *mfn_plus*|*mfn+*)        echo "mfn+" ;;
        *kuramoto*)                echo "kuramoto" ;;
        *agent*)                   echo "agents" ;;
        *doc*|*manuscript*)        echo "docs" ;;
        *test*)                    echo "tests" ;;
        *bench*)                   echo "bench" ;;
        *tools*|*script*)          echo "tools" ;;
        *neosynaptex*)             echo "core" ;;
        *)
            # First directory component
            local first="${rel%%/*}"
            echo "${first:0:12}"
            ;;
    esac
}

# Layer → color
_neo_layer_color() {
    case "$1" in
        core)    echo "$_P_CYAN" ;;
        bn_syn)  echo "$_P_MAG" ;;
        hca1)    echo '\[\033[38;2;180;120;255m\]' ;;
        mlsdm)   echo '\[\033[38;2;0;200;180m\]' ;;
        mfn+)    echo '\[\033[38;2;255;150;50m\]' ;;
        kuramoto) echo '\[\033[38;2;120;200;255m\]' ;;
        agents)  echo '\[\033[38;2;255;200;0m\]' ;;
        docs)    echo "$_P_DIM" ;;
        tests)   echo "$_P_GRN" ;;
        tools)   echo "$_P_DIM" ;;
        root)    echo "$_P_CYAN" ;;
        *)       echo "$_P_FG" ;;
    esac
}

# ── Git state (fast) ────────────────────────────────────────────────
_neo_git() {
    # Output: branch dirty detached conflict
    local branch
    branch=$(git symbolic-ref --short HEAD 2>/dev/null)
    if [[ -z "$branch" ]]; then
        branch=$(git rev-parse --short HEAD 2>/dev/null || echo "∅")
        local detached=1
    else
        local detached=0
    fi

    local dirty=0
    if ! git diff --quiet HEAD -- 2>/dev/null || ! git diff --cached --quiet HEAD -- 2>/dev/null; then
        dirty=1
    fi
    # Untracked files count as dirty too
    if [[ $dirty -eq 0 ]] && [[ -n "$(git ls-files --others --exclude-standard 2>/dev/null | head -1)" ]]; then
        dirty=1
    fi

    local conflict=0
    [[ -f "$(git rev-parse --git-dir 2>/dev/null)/MERGE_HEAD" ]] && conflict=1

    echo "$branch $dirty $detached $conflict"
}

# ── Cognitive state ──────────────────────────────────────────────────
_neo_state() {
    local branch="$1" dirty="$2" detached="$3" conflict="$4" last_rc="$5"

    [[ $conflict -eq 1 ]] && { echo "BLOCKED"; return; }
    [[ $detached -eq 1 ]] && { echo "DETACHED"; return; }
    [[ $last_rc -ne 0 ]]  && { echo "ERROR"; return; }

    if [[ $dirty -eq 1 ]]; then
        # Check recency of last verify
        if [[ -f /tmp/.neo_last_verify_ts ]]; then
            local now vts age
            now=$(date +%s)
            vts=$(cat /tmp/.neo_last_verify_ts 2>/dev/null || echo 0)
            age=$(( now - vts ))
            if [[ $age -gt 300 ]]; then
                echo "UNVERIFIED"; return
            fi
            echo "DIRTY"; return
        fi
        echo "DRIFT"; return
    fi

    echo "STABLE"
}

# State → prompt color
_neo_state_pcolor() {
    case "$1" in
        STABLE)     echo "$_P_GRN" ;;
        DIRTY)      echo "$_P_AMB" ;;
        DRIFT)      echo "$_P_MAG" ;;
        UNVERIFIED) echo "$_P_AMB" ;;
        ERROR)      echo "$_P_RED" ;;
        BLOCKED)    echo "$_P_RED" ;;
        DETACHED)   echo "$_P_RED" ;;
        *)          echo "$_P_DIM" ;;
    esac
}

# State → raw color (for echo)
_neo_state_color() {
    case "$1" in
        STABLE)     echo "$_C_GRN" ;;
        DIRTY)      echo "$_C_AMB" ;;
        DRIFT)      echo "$_C_MAG" ;;
        UNVERIFIED) echo "$_C_AMB" ;;
        ERROR)      echo "$_C_RED" ;;
        BLOCKED)    echo "$_C_RED" ;;
        DETACHED)   echo "$_C_RED" ;;
        *)          echo "$_C_DIM" ;;
    esac
}

# ── Last action tracking ────────────────────────────────────────────
_NEO_ACTION_FILE="/tmp/.neo_last_action"

_neo_track() {
    local cmd
    cmd=$(HISTTIMEFORMAT='' history 1 | sed 's/^[ ]*[0-9]*[ ]*//')
    [[ -z "$cmd" ]] && return

    case "$cmd" in
        pytest*|python*test*|*-m\ pytest*|make*test*)
            echo "test" > "$_NEO_ACTION_FILE"
            [[ $_NEO_LAST_RC -eq 0 ]] && date +%s > /tmp/.neo_last_verify_ts
            ;;
        git\ commit*|git\ ci*)   echo "commit" > "$_NEO_ACTION_FILE" ;;
        git\ push*)              echo "push" > "$_NEO_ACTION_FILE" ;;
        git\ pull*|git\ fetch*)  echo "sync" > "$_NEO_ACTION_FILE" ;;
        pip\ install*|pip3\ install*) echo "install" > "$_NEO_ACTION_FILE" ;;
        ruff*|mypy*|flake8*)     echo "lint" > "$_NEO_ACTION_FILE" ;;
        git\ merge*)             echo "merge" > "$_NEO_ACTION_FILE" ;;
        git\ rebase*)            echo "rebase" > "$_NEO_ACTION_FILE" ;;
        make*|cargo*|npm\ run*)  echo "build" > "$_NEO_ACTION_FILE" ;;
    esac
}

_neo_last_action() {
    [[ -f "$_NEO_ACTION_FILE" ]] && cat "$_NEO_ACTION_FILE" || echo ""
}

# ── PROMPT_COMMAND ───────────────────────────────────────────────────
_neo_prompt() {
    _NEO_LAST_RC=$?

    # Preserve history flush
    history -a

    _neo_track

    # Check if inside a git repo
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        PS1="${_P_DIM}[${_P_CYAN}${_P_B}NEO${_P_DIM}] ${_P_FG}\W${_P_R}\n${_P_CYAN}❯${_P_R} "
        return
    fi

    local git_info branch dirty detached conflict
    git_info=$(_neo_git)
    read -r branch dirty detached conflict <<< "$git_info"

    local state
    state=$(_neo_state "$branch" "$dirty" "$detached" "$conflict" "$_NEO_LAST_RC")

    local layer
    layer=$(_neo_layer)
    local lcolor
    lcolor=$(_neo_layer_color "$layer")

    local scolor
    scolor=$(_neo_state_pcolor "$state")

    local action
    action=$(_neo_last_action)

    # Build prompt
    # ┌ [NEO] layer :: branch ∴ STATE ⟡ action
    # └ ❯
    local p=""
    p+="${_P_DIM}┌ [${_P_CYAN}${_P_B}NEO${_P_R}${_P_DIM}] "
    p+="${lcolor}${_P_B}${layer}${_P_R}${_P_DIM} :: "
    p+="${_P_MAG}${branch}${_P_R}${_P_DIM} ∴ "
    p+="${scolor}${_P_B}${state}${_P_R}"

    if [[ -n "$action" ]]; then
        p+="${_P_DIM} ⟡ ${_P_FG}${action}${_P_R}"
    fi

    p+="\n${_P_DIM}└ ${scolor}❯${_P_R} "

    PS1="$p"
}

PROMPT_COMMAND="_neo_prompt"

# ── Fast commands ────────────────────────────────────────────────────

# neo — full status dashboard
neo() {
    echo -e "${_C_CYAN}${_C_B}  NEOSYNAPTEX COSMO-NEURAL HUD${_C_R}"
    echo -e "${_C_DIM}  ═══════════════════════════════${_C_R}"

    local git_info branch dirty detached conflict
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        git_info=$(_neo_git)
        read -r branch dirty detached conflict <<< "$git_info"
        local state=$(_neo_state "$branch" "$dirty" "$detached" "$conflict" 0)
        local layer=$(_neo_layer)
        local sc=$(_neo_state_color "$state")

        echo -e "  ${_C_DIM}LAYER   ${_C_CYAN}${layer}${_C_R}"
        echo -e "  ${_C_DIM}BRANCH  ${_C_MAG}${branch}${_C_R}"
        echo -e "  ${_C_DIM}STATE   ${sc}${state}${_C_R}"
        echo -e "  ${_C_DIM}DIRTY   ${_C_FG}$([ $dirty -eq 1 ] && echo 'yes' || echo 'no')${_C_R}"
        local action=$(_neo_last_action)
        [[ -n "$action" ]] && echo -e "  ${_C_DIM}ACTION  ${_C_FG}${action}${_C_R}"
        echo -e "  ${_C_DIM}REPO    ${_C_FG}${_NEO_REPO_ROOT}${_C_R}"
    else
        echo -e "  ${_C_DIM}Not inside a git repository${_C_R}"
    fi
    echo
}

# nv — verify (run tests)
nv() {
    echo -e "${_C_CYAN}∴ verify${_C_R}"
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ -n "$root" ]]; then
        if [[ -f "$root/test_neosynaptex.py" ]]; then
            (cd "$root" && python3 -m pytest test_neosynaptex.py -q "$@")
        elif [[ -f "$root/neosynaptex/test_neosynaptex.py" ]]; then
            (cd "$root/neosynaptex" && python3 -m pytest test_neosynaptex.py -q "$@")
        elif [[ -f "$root/pyproject.toml" ]] || [[ -f "$root/pytest.ini" ]]; then
            (cd "$root" && python3 -m pytest -q "$@")
        else
            echo -e "${_C_DIM}No test target found${_C_R}"
            return 1
        fi
    fi
}

# nt — targeted tests (pass path or pattern)
nt() { nv "$@"; }

# nl — recent evidence (git log)
nl() {
    echo -e "${_C_CYAN}∴ recent evidence${_C_R}"
    git log --oneline --graph --decorate -15 2>/dev/null || echo "Not in a git repo"
}

# nm — repo map
nm() {
    echo -e "${_C_CYAN}∴ repo map${_C_R}"
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null) || return 1
    find "$root" -maxdepth 3 -type f \( -name '*.py' -o -name '*.toml' -o -name '*.md' \) \
        -not -path '*__pycache__*' -not -path '*.git*' -not -path '*node_modules*' \
        | sort | sed "s|$root/||" | head -50
}

# ncd — jump to repo root or named subsystem
ncd() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null) || return 1
    if [[ -z "$1" ]]; then
        cd "$root"
    elif [[ -d "$root/$1" ]]; then
        cd "$root/$1"
    elif [[ -d "$root/neosynaptex/$1" ]]; then
        cd "$root/neosynaptex/$1"
    else
        # Fuzzy find
        local match
        match=$(find "$root" -maxdepth 3 -type d -name "*$1*" 2>/dev/null | head -1)
        if [[ -n "$match" ]]; then
            cd "$match"
        else
            echo -e "${_C_DIM}No match for: $1${_C_R}"
        fi
    fi
}

# nd — show dirty files
nd() {
    echo -e "${_C_CYAN}∴ dirty files${_C_R}"
    git status --short 2>/dev/null || echo "Not in a git repo"
}

# ── Help ─────────────────────────────────────────────────────────────
neo-help() {
    echo -e "${_C_CYAN}${_C_B}  NEOSYNAPTEX HUD — Commands${_C_R}"
    echo -e "${_C_DIM}  ═══════════════════════════════${_C_R}"
    echo -e "  ${_C_CYAN}neo${_C_R}       Full status dashboard"
    echo -e "  ${_C_CYAN}nv${_C_R}        Verify (run tests)"
    echo -e "  ${_C_CYAN}nt${_C_R}        Targeted tests (pass args)"
    echo -e "  ${_C_CYAN}nl${_C_R}        Recent evidence (git log)"
    echo -e "  ${_C_CYAN}nm${_C_R}        Repo map (files)"
    echo -e "  ${_C_CYAN}ncd${_C_R}       Jump to repo root or subsystem"
    echo -e "  ${_C_CYAN}nd${_C_R}        Show dirty files"
    echo -e "  ${_C_CYAN}neo-help${_C_R}  This help"
    echo
    echo -e "  ${_C_DIM}States: ${_C_GRN}STABLE${_C_R} ${_C_AMB}DIRTY${_C_R} ${_C_MAG}DRIFT${_C_R} ${_C_AMB}UNVERIFIED${_C_R} ${_C_RED}ERROR${_C_R} ${_C_RED}BLOCKED${_C_R} ${_C_RED}DETACHED${_C_R}"
    echo
}

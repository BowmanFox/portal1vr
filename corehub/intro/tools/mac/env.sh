# Shared settings for the Corehub Mac pipeline. Sourced by every handler.
emulate -R zsh
setopt null_glob extended_glob
R=${COREHUB_ROOT:-${0:A:h:h}}
R10=$R/r10
GAME=$R/runtime/game              # Niko's Corehub build (hl2.exe lives here)
MOD=$GAME/corehub_intro           # the intro mod folder
OUTPUTS=$R/outputs/Corehub-Intro  # published package
CXROOT=/Applications/CrossOver.app/Contents/SharedSupport/CrossOver
CXBIN=$CXROOT/bin
export CX_BOTTLE=${CX_BOTTLE:-Corehub}
BOTTLE_DIR="$HOME/Library/Application Support/CrossOver/Bottles/$CX_BOTTLE"
WINE=$CXBIN/wine
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
# Windows path (Z: drive) for a native path
winpath() { print -r -- "Z:${1//\//\\}" }
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ }

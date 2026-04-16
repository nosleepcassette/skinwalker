#!/usr/bin/env zsh
# maps · cassette.help · MIT
# install.zsh — installs skinwalker to PATH via uv tool
# usage: zsh install.zsh [--patch-hermes]

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PATCH_HERMES=0

for arg in "$@"; do
  [[ "$arg" == "--patch-hermes" ]] && PATCH_HERMES=1
done

# ── check uv ──────────────────────────────────────────────────────────────────

if ! command -v uv &>/dev/null; then
  print -P "%F{red}error:%f uv is not installed."
  print "install it with:  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# ── install skinwalker ─────────────────────────────────────────────────────────

print -P "%F{cyan}installing skinwalker…%f"
uv tool install --reinstall "$SCRIPT_DIR"

# confirm it landed on PATH
if command -v skinwalker &>/dev/null; then
  print -P "%F{green}✓%f skinwalker installed at $(command -v skinwalker)"
else
  print -P "%F{yellow}skinwalker installed but not found on PATH.%f"
  print "add this to your ~/.zshrc:"
  print '  export PATH="$HOME/.local/bin:$PATH"'
fi

# ── optionally patch hermes ───────────────────────────────────────────────────

if (( PATCH_HERMES )); then
  zsh "$SCRIPT_DIR/patch-hermes.zsh"
fi

print ""
print -P "%F{cyan}done.%f  run: skinwalker"

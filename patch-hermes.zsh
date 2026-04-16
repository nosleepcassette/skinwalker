#!/usr/bin/env zsh
# maps · cassette.help · MIT
# patch-hermes.zsh — patches local hermes-agent so skin spinner faces/verbs
#                    are read from the active skin at runtime.
#
# this is a local workaround for NousResearch/hermes-agent#10668 while the
# upstream PR is under review. safe to re-run — idempotent.
#
# usage:
#   zsh patch-hermes.zsh
#   zsh patch-hermes.zsh --hermes-root /path/to/hermes-agent
#   HERMES_AGENT_ROOT=/path/to/hermes-agent zsh patch-hermes.zsh

set -euo pipefail

# ── resolve hermes-agent root ─────────────────────────────────────────────────

HERMES_ROOT=""

for arg in "$@"; do
  if [[ "$arg" == --hermes-root=* ]]; then
    HERMES_ROOT="${arg#--hermes-root=}"
  fi
done

# also accept --hermes-root <value> (two-arg form)
set -- "$@"
local i=1
while (( i <= $# )); do
  if [[ "${argv[$i]}" == "--hermes-root" ]] && (( i < $# )); then
    HERMES_ROOT="${argv[$((i+1))]}"
  fi
  (( i++ )) || true
done

if [[ -z "$HERMES_ROOT" ]]; then
  HERMES_ROOT="${HERMES_AGENT_ROOT:-$HOME/.hermes/hermes-agent}"
fi

HERMES_ROOT="${HERMES_ROOT/#\~/$HOME}"

if [[ ! -d "$HERMES_ROOT" ]]; then
  print -P "%F{red}error:%f hermes-agent not found at: $HERMES_ROOT"
  print "pass a path with --hermes-root or set HERMES_AGENT_ROOT"
  exit 1
fi

DISPLAY_PY="$HERMES_ROOT/agent/display.py"
RUN_AGENT_PY="$HERMES_ROOT/run_agent.py"

for f in "$DISPLAY_PY" "$RUN_AGENT_PY"; do
  if [[ ! -f "$f" ]]; then
    print -P "%F{red}error:%f expected file not found: $f"
    print "is $HERMES_ROOT the correct hermes-agent root?"
    exit 1
  fi
done

print -P "%F{cyan}patching hermes-agent at:%f $HERMES_ROOT"

# ── idempotency check ─────────────────────────────────────────────────────────

if grep -q "get_waiting_faces" "$DISPLAY_PY" 2>/dev/null; then
  print -P "%F{green}✓%f display.py already patched — skipping"
  DISPLAY_ALREADY=1
else
  DISPLAY_ALREADY=0
fi

if grep -q "get_waiting_faces" "$RUN_AGENT_PY" 2>/dev/null; then
  print -P "%F{green}✓%f run_agent.py already patched — skipping"
  RUN_ALREADY=1
else
  RUN_ALREADY=0
fi

if (( DISPLAY_ALREADY && RUN_ALREADY )); then
  print -P "%F{green}already fully patched.%f"
  exit 0
fi

# ── backup ────────────────────────────────────────────────────────────────────

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if (( ! DISPLAY_ALREADY )); then
  cp "$DISPLAY_PY" "${DISPLAY_PY}.bak.${TIMESTAMP}"
  print "  backed up display.py → display.py.bak.${TIMESTAMP}"
fi

if (( ! RUN_ALREADY )); then
  cp "$RUN_AGENT_PY" "${RUN_AGENT_PY}.bak.${TIMESTAMP}"
  print "  backed up run_agent.py → run_agent.py.bak.${TIMESTAMP}"
fi

# ── patch display.py ──────────────────────────────────────────────────────────
# inserts three class methods on KawaiiSpinner after THINKING_VERBS

if (( ! DISPLAY_ALREADY )); then
  python3 - "$DISPLAY_PY" <<'PYEOF'
import sys, re

path = sys.argv[1]
src = open(path).read()

# find the end of THINKING_VERBS list and insert methods after it
marker = '        "analyzing", "computing", "synthesizing", "formulating", "brainstorming",\n    ]\n'
insert = '''        "analyzing", "computing", "synthesizing", "formulating", "brainstorming",
    ]

    @classmethod
    def get_waiting_faces(cls) -> list:
        """Return waiting faces from the active skin, falling back to KAWAII_WAITING."""
        try:
            skin = _get_skin()
            if skin:
                faces = skin.spinner.get("waiting_faces", [])
                if faces:
                    return faces
        except Exception:
            pass
        return cls.KAWAII_WAITING

    @classmethod
    def get_thinking_faces(cls) -> list:
        """Return thinking faces from the active skin, falling back to KAWAII_THINKING."""
        try:
            skin = _get_skin()
            if skin:
                faces = skin.spinner.get("thinking_faces", [])
                if faces:
                    return faces
        except Exception:
            pass
        return cls.KAWAII_THINKING

    @classmethod
    def get_thinking_verbs(cls) -> list:
        """Return thinking verbs from the active skin, falling back to THINKING_VERBS."""
        try:
            skin = _get_skin()
            if skin:
                verbs = skin.spinner.get("thinking_verbs", [])
                if verbs:
                    return verbs
        except Exception:
            pass
        return cls.THINKING_VERBS

'''

if marker not in src:
    print("error: could not find insertion point in display.py — may already be patched or upstream changed")
    sys.exit(1)

patched = src.replace(marker, insert, 1)
open(path, 'w').write(patched)
print("  patched display.py")
PYEOF
fi

# ── patch run_agent.py ────────────────────────────────────────────────────────
# replaces the 7 hardcoded KawaiiSpinner class constant references

if (( ! RUN_ALREADY )); then
  python3 - "$RUN_AGENT_PY" <<'PYEOF'
import sys, re

path = sys.argv[1]
src = open(path).read()

replacements = [
    ("random.choice(KawaiiSpinner.KAWAII_WAITING)",  "random.choice(KawaiiSpinner.get_waiting_faces())"),
    ("random.choice(KawaiiSpinner.KAWAII_THINKING)", "random.choice(KawaiiSpinner.get_thinking_faces())"),
    ("random.choice(KawaiiSpinner.THINKING_VERBS)",  "random.choice(KawaiiSpinner.get_thinking_verbs())"),
]

total = 0
for old, new in replacements:
    count = src.count(old)
    if count == 0:
        print(f"warning: '{old}' not found — upstream may have changed")
    src = src.replace(old, new)
    total += count

open(path, 'w').write(src)
print(f"  patched run_agent.py ({total} sites updated)")
PYEOF
fi

# ── done ──────────────────────────────────────────────────────────────────────

print ""
print -P "%F{green}✓ patch applied.%f"
print "  your skin's waiting_faces, thinking_faces, and thinking_verbs will now"
print "  be used at runtime. restart hermes to pick up the changes."
print ""
print "  to revert: restore the .bak files in $HERMES_ROOT/agent/"
print "  upstream fix: https://github.com/NousResearch/hermes-agent/pull/10668"

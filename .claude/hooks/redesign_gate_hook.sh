#!/usr/bin/env sh
# Portable launcher for the redesign hard-gates hook.
# Wired from .claude/settings.json (SessionStart / Stop / PreToolUse).
# Picks an interpreter in this order so a fresh clone / other OS still works:
#   1. project venv  (.venv/Scripts/python.exe  |  .venv/bin/python)
#   2. python3 / python / py on PATH
# The gate scripts are standard-library only, so any Python 3 is fine.
# Exits 0 when no Python is found — a missing interpreter must not wedge the
# session; the gates just don't run until Python is available.

set -u

root="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$root" ]; then
  root=$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)
fi
script="$root/tools/redesign_gate_hook.py"

for cand in \
  "$root/.venv/Scripts/python.exe" \
  "$root/.venv/bin/python" \
  python3 python py
do
  case "$cand" in
    /*|*/*)
      [ -x "$cand" ] && exec "$cand" "$script"
      ;;
    *)
      command -v "$cand" >/dev/null 2>&1 && exec "$cand" "$script"
      ;;
  esac
done

echo "redesign_gate_hook: no Python 3 interpreter found — gates not run" >&2
exit 0

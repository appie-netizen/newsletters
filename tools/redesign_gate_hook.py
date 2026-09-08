#!/usr/bin/env python
"""Claude Code hook helper for redesign_website hard gates.

Reads hook JSON from stdin. Events:
  SessionStart — inject reminder about verify_redesign_gates.py
  Stop         — if .claude/active_redesign_slug set, verify; exit 2 on fail
  PreToolUse   — if Bash publishes the site (git push OR a Vercel prod deploy)
                 AND active slug set, verify first; exit 2 blocks it

Designed for .claude/settings.json hooks invoking:
  .venv\\Scripts\\python.exe tools/redesign_gate_hook.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Resolve project root: CLAUDE_PROJECT_DIR > cwd > tools parent
def _project_root() -> Path:
    import os

    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    if (cwd / "tools" / "verify_redesign_gates.py").is_file():
        return cwd
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _project_root()
ACTIVE_SLUG_PATH = PROJECT_ROOT / ".claude" / "active_redesign_slug"
VERIFY_SCRIPT = PROJECT_ROOT / "tools" / "verify_redesign_gates.py"


def _read_stdin_json() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _active_slug() -> str | None:
    if not ACTIVE_SLUG_PATH.is_file():
        return None
    try:
        text = ACTIVE_SLUG_PATH.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return None
    if not text:
        return None
    # first line only
    slug = text.splitlines()[0].strip()
    if not slug or re.search(r"[\\/]", slug):
        return None
    return slug


def _venv_python() -> Path:
    win = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    unix = PROJECT_ROOT / ".venv" / "bin" / "python"
    if win.is_file():
        return win
    if unix.is_file():
        return unix
    return Path(sys.executable)


def _run_verify(slug: str) -> tuple[int, dict, str]:
    """Return (exit_code, summary_dict, stderr_text)."""
    py = _venv_python()
    try:
        proc = subprocess.run(
            [str(py), str(VERIFY_SCRIPT), "--slug", slug],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 2, {}, f"verify_redesign_gates.py failed to run: {e}"
    summary: dict = {}
    out = (proc.stdout or "").strip()
    if out:
        try:
            # last JSON object if mixed
            summary = json.loads(out)
        except json.JSONDecodeError:
            # try find first { ... }
            start = out.find("{")
            end = out.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    summary = json.loads(out[start : end + 1])
                except json.JSONDecodeError:
                    summary = {}
    err = (proc.stderr or "").strip()
    return proc.returncode, summary if isinstance(summary, dict) else {}, err


def _format_fail_reason(slug: str, summary: dict, err: str) -> str:
    fails = summary.get("failed") or []
    if fails:
        lines = [f"Redesign gates failed for slug={slug}:"]
        for item in fails:
            if isinstance(item, dict):
                lines.append(f"  - {item.get('id')}: {item.get('reason')}")
            else:
                lines.append(f"  - {item}")
        lines.append(
            f"Fix missing gates, then re-run: "
            f"python tools/verify_redesign_gates.py --slug {slug}"
        )
        return "\n".join(lines)
    if err:
        return f"Redesign gates failed for slug={slug}:\n{err}"
    return (
        f"Redesign gates failed for slug={slug}. "
        f"Run: python tools/verify_redesign_gates.py --slug {slug}"
    )


def handle_session_start(_payload: dict) -> int:
    msg = (
        "HARD GATES (redesign_website): Before declaring a redesign done or "
        "pushing the nested site repo, run "
        "`python tools/verify_redesign_gates.py --slug <slug>` and ensure exit 0. "
        "See workflows/redesign_website/GATES.md. At job start set "
        "`.claude/active_redesign_slug` to the client slug; remove it only when "
        "all gates G0-G7 pass. The Stop hook blocks early exit while that file "
        "is present and gates fail."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": msg,
        }
    }
    print(json.dumps(out))
    return 0


def handle_stop(payload: dict) -> int:
    # Avoid infinite stop-hook loops: still verify, but if no active slug, allow.
    slug = _active_slug()
    if not slug:
        return 0
    if not VERIFY_SCRIPT.is_file():
        sys.stderr.write(
            "active_redesign_slug is set but tools/verify_redesign_gates.py is missing\n"
        )
        return 2
    code, summary, err = _run_verify(slug)
    if code == 0 and summary.get("ok", True):
        return 0
    reason = _format_fail_reason(slug, summary, err)
    sys.stderr.write(reason + "\n")
    return 2


def _command_looks_like_push(command: str) -> bool:
    """True when the command would publish the site: a git push, or a Vercel
    production deploy/promote (so `/deploy prod` can't bypass the gates when a
    redesign is active). Preview deploys (`vercel`, `vercel deploy`) don't gate.
    """
    if re.search(r"(^|[;&|]\s*)git(\.exe)?\s+push\b", command, re.I):
        return True
    if re.search(r"(^|[;&|]\s*)(npx\s+|npm\s+exec\s+)?vercel(\.cmd)?\b", command, re.I) and (
        re.search(r"--prod\b", command, re.I)
        or re.search(r"--target[=\s]+prod(uction)?\b", command, re.I)
        or re.search(r"\bvercel(\.cmd)?\s+(deploy\s+)?--prod\b", command, re.I)
        or re.search(r"\bvercel(\.cmd)?\s+promote\b", command, re.I)
    ):
        return True
    return False


def handle_pre_tool_use(payload: dict) -> int:
    tool = payload.get("tool_name") or ""
    if tool not in ("Bash", "PowerShell"):
        return 0
    tool_input = payload.get("tool_input") or {}
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    if not _command_looks_like_push(command):
        return 0
    slug = _active_slug()
    if not slug:
        return 0  # allow publish when no active redesign
    code, summary, err = _run_verify(slug)
    if code == 0 and summary.get("ok", True):
        return 0
    reason = _format_fail_reason(slug, summary, err)
    sys.stderr.write(
        "Blocked: redesign gates not satisfied (git push / Vercel prod deploy).\n"
        + reason + "\n"
    )
    return 2


def main() -> int:
    payload = _read_stdin_json()
    event = (
        payload.get("hook_event_name")
        or payload.get("hookEventName")
        or ""
    )
    if event == "SessionStart":
        return handle_session_start(payload)
    if event == "Stop":
        return handle_stop(payload)
    if event == "PreToolUse":
        return handle_pre_tool_use(payload)
    # Unknown / empty — no-op
    return 0


if __name__ == "__main__":
    sys.exit(main())

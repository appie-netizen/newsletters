#!/usr/bin/env python
"""Publish an issue: flip it to published, rebuild docs/, commit and push.

Usage:
    python tools/publish_site.py --slug home-batteries
    python tools/publish_site.py --slug home-batteries --dry-run

Pushing to `origin` triggers the GitHub Pages redeploy (~1 minute). This is the
only step that touches the network; re-running it is safe.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urljoin

from _common import ISSUES_DIR, PROJECT_ROOT, load_config, read_json, write_json

import build_site


def _git_exe() -> str:
    exe = shutil.which("git")
    if exe:
        return exe
    for cand in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
    ):
        if os.path.exists(cand):
            return cand
    sys.stderr.write(
        "git not found. Install Git for Windows (winget install --id Git.Git) "
        "and reopen the terminal.\n"
    )
    raise SystemExit(1)


def git(*args: str, capture: bool = False) -> str:
    exe = _git_exe()
    result = subprocess.run(
        [exe, *args], cwd=PROJECT_ROOT, text=True,
        capture_output=True,
    )
    if result.returncode != 0 and not capture:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"git {' '.join(args)} failed ({result.returncode})")
    return (result.stdout or "").strip()


def has_origin() -> bool:
    return "origin" in git("remote", capture=True).split()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-m", "--message", help="override the commit message")
    args = ap.parse_args()

    cfg = load_config()
    issue_path = ISSUES_DIR / f"{args.slug}.json"
    if not issue_path.exists():
        sys.stderr.write(f"issue file not found: {issue_path}\n")
        return 1
    issue = read_json(issue_path)
    msg = args.message or f"Issue {issue.get('number')}: {issue.get('title')}"
    live_url = urljoin(cfg.get("base_url", ""), f"issues/{args.slug}.html")

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "would_set_status": "published",
            "current_status": issue.get("status"),
            "commit_message": msg,
            "commands": ["git add issues docs", f'git commit -m "{msg}"', "git push"],
            "git_status": git("status", "--short", capture=True).splitlines(),
            "live_url": live_url,
            "has_origin": has_origin(),
        }, indent=2))
        return 0

    issue["status"] = "published"
    write_json(issue_path, issue)
    result = build_site.build(include_drafts=False)
    sys.stderr.write(f"[publish] rebuilt: {result['issues_rendered']}\n")

    if not has_origin():
        sys.stderr.write(
            "\nIssue marked published and docs/ rebuilt, but there is no 'origin' remote.\n"
            "Create a GitHub repo, then:\n"
            "  git remote add origin https://github.com/<you>/<repo>.git\n"
            "  git push -u origin main\n"
            "and enable Pages (Settings -> Pages -> Deploy from a branch -> main / /docs).\n"
        )
        return 1

    git("add", "issues", "docs", "newsletter.config.yaml")
    if not git("status", "--porcelain", capture=True):
        sys.stderr.write("[publish] nothing to commit (already up to date)\n")
    else:
        git("commit", "-m", msg)
    branch = git("rev-parse", "--abbrev-ref", "HEAD", capture=True) or "main"
    git("push", "-u", "origin", branch)

    print(json.dumps({"published": args.slug, "branch": branch, "live_url": live_url}))
    print(f"\nLive in ~1 minute: {live_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

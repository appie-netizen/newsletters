#!/usr/bin/env python
"""Build the static newsletter site into docs/ from issues/*.json.

Usage:
    python tools/build_site.py            # published issues only
    python tools/build_site.py --drafts   # also render drafts (for local preview)

Writes:
    docs/index.html
    docs/issues/<slug>.html
    docs/feed.xml            (published issues only, always)
    docs/assets/style.css
    docs/.nojekyll

Exits non-zero if an included issue fails validation (missing alt text, or an
illustration file that isn't on disk).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from email.utils import format_datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from _common import DOCS_DIR, ISSUES_DIR, PROJECT_ROOT, load_config, read_json

TEMPLATES = PROJECT_ROOT / "tools" / "templates"


def _nicedate(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        return value or ""
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def _rfc822(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        dt = datetime.now(timezone.utc)
    return format_datetime(dt)


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["nicedate"] = _nicedate
    env.filters["rfc822"] = _rfc822
    return env


def load_issues() -> list[dict]:
    if not ISSUES_DIR.exists():
        return []
    issues = []
    for f in sorted(ISSUES_DIR.glob("*.json")):
        issues.append(read_json(f))
    return issues


def validate(issue: dict) -> list[str]:
    errs = []
    for i, s in enumerate(issue.get("sections", [])):
        needs_alt = s.get("image_brief") or s.get("image")
        if needs_alt and not (s.get("image_alt") or "").strip():
            errs.append(f"section {i} has an illustration but no image_alt")
        if s.get("image"):
            p = DOCS_DIR / s["image"]
            if not p.exists():
                errs.append(f"section {i} image file missing: {s['image']}")
    return errs


def build(include_drafts: bool = False) -> dict:
    cfg = load_config()
    env = _env()
    all_issues = load_issues()

    published = [i for i in all_issues if i.get("status") == "published"]
    rendered = [
        i for i in all_issues
        if i.get("status") == "published" or (include_drafts and i.get("status") == "draft")
    ]

    problems = {}
    for issue in rendered:
        errs = validate(issue)
        if errs:
            problems[issue.get("slug", "?")] = errs
    if problems:
        sys.stderr.write("[build] validation failed:\n")
        for slug, errs in problems.items():
            for e in errs:
                sys.stderr.write(f"  {slug}: {e}\n")
        raise SystemExit(1)

    rendered.sort(key=lambda i: i.get("number", 0))          # ascending for prev/next
    display = list(reversed(rendered))                        # newest first for index
    feed_issues = sorted(published, key=lambda i: i.get("number", 0), reverse=True)

    (DOCS_DIR / "issues").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    # stylesheet
    css = env.get_template("style.css.j2").render(config=cfg)
    (DOCS_DIR / "assets" / "style.css").write_text(css, encoding="utf-8")

    # index
    index_html = env.get_template("index.html.j2").render(config=cfg, issues=display, rel="")
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # feed (published only)
    feed_xml = env.get_template("feed.xml.j2").render(config=cfg, issues=feed_issues)
    (DOCS_DIR / "feed.xml").write_text(feed_xml, encoding="utf-8")

    # issue pages
    issue_tpl = env.get_template("issue.html.j2")
    written = []
    for idx, issue in enumerate(rendered):
        prev_issue = rendered[idx - 1] if idx > 0 else None
        next_issue = rendered[idx + 1] if idx < len(rendered) - 1 else None
        html = issue_tpl.render(
            config=cfg, issue=issue, prev=prev_issue, next=next_issue, rel="../"
        )
        (DOCS_DIR / "issues" / f"{issue['slug']}.html").write_text(html, encoding="utf-8")
        written.append(issue["slug"])

    return {
        "issues_rendered": written,
        "published": [i["slug"] for i in published],
        "drafts_included": include_drafts,
        "out": str(DOCS_DIR),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drafts", action="store_true", help="also render draft issues")
    args = ap.parse_args()
    result = build(include_drafts=args.drafts)
    import json
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

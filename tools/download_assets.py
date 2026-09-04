#!/usr/bin/env python
"""Download generated illustrations into the site and attach them to the issue.

The agent generates images (generate_image MCP) from the briefs printed by
draft_newsletter.py, then passes the resulting URLs here IN THE SAME ORDER as
the briefs. Local file paths are also accepted (they are copied).

Usage:
    python tools/download_assets.py --slug home-batteries \\
        --urls https://cdn.../a.png https://cdn.../b.png

Effect:
    writes docs/assets/<slug>/illustration-N.<ext>
    sets sections[...]["image"] on issues/<slug>.json for each section that has
    an image_brief, in order
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

from _common import DOCS_DIR, ISSUES_DIR, read_json, write_json

EXT_BY_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def _guess_ext(url: str, content_type: str | None) -> str:
    if content_type:
        base = content_type.split(";")[0].strip().lower()
        if base in EXT_BY_TYPE:
            return EXT_BY_TYPE[base]
        guessed = mimetypes.guess_extension(base)
        if guessed:
            return ".jpg" if guessed == ".jpe" else guessed
    ext = Path(urlparse(url).path).suffix.lower()
    return ext if ext in EXT_BY_TYPE else ".png"


def fetch(src: str, dest_no_ext: Path) -> Path:
    if "://" not in src or src.startswith("file://"):
        local = Path(src[7:] if src.startswith("file://") else src)
        if not local.exists():
            raise FileNotFoundError(f"local image not found: {local}")
        dest = dest_no_ext.with_suffix(local.suffix or ".png")
        shutil.copyfile(local, dest)
        return dest
    r = requests.get(src, timeout=60)
    r.raise_for_status()
    dest = dest_no_ext.with_suffix(_guess_ext(src, r.headers.get("content-type")))
    dest.write_bytes(r.content)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--urls", nargs="+", required=True, help="image URLs or local paths, in brief order")
    args = ap.parse_args()

    issue_path = ISSUES_DIR / f"{args.slug}.json"
    if not issue_path.exists():
        sys.stderr.write(f"issue file not found: {issue_path}\n")
        return 1
    issue = read_json(issue_path)

    brief_idxs = [i for i, s in enumerate(issue["sections"]) if s.get("image_brief")]
    if not brief_idxs:
        sys.stderr.write("this issue has no sections with an image_brief; nothing to attach\n")
        return 1
    if len(args.urls) != len(brief_idxs):
        sys.stderr.write(
            f"warning: {len(args.urls)} images for {len(brief_idxs)} briefs; "
            f"attaching the first {min(len(args.urls), len(brief_idxs))}\n"
        )

    asset_dir = DOCS_DIR / "assets" / args.slug
    asset_dir.mkdir(parents=True, exist_ok=True)

    attached = []
    for n, (idx, src) in enumerate(zip(brief_idxs, args.urls), start=1):
        dest = fetch(src, asset_dir / f"illustration-{n}")
        rel = dest.relative_to(DOCS_DIR).as_posix()  # e.g. assets/<slug>/illustration-1.png
        issue["sections"][idx]["image"] = rel
        attached.append({"section_index": idx, "path": rel})

    write_json(issue_path, issue)
    print(json.dumps({"slug": args.slug, "attached": attached}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""Attach images to an issue: copy/download them into the site and wire them
into issues/<slug>.json.

Sources can be URLs or local file paths (PNG / JPG / WEBP / SVG). Use this for
hand-made infographics (SVG), Canva exports, or images from an MCP/tool.

Usage:
    # attach to the sections that already carry an image_brief, in order
    python tools/download_assets.py --slug home-batteries --urls a.png b.png

    # attach to explicit sections (e.g. SVGs on a --no-images draft), with alt text
    python tools/download_assets.py --slug home-batteries \\
        --urls chart.svg map.svg --sections 1 3 \\
        --alt "Bar chart of adoption by country" "Map of grid regions"

Effect:
    writes docs/assets/<slug>/illustration-N.<ext>
    sets sections[...]["image"] (and image_alt if --alt) on issues/<slug>.json
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
    ap.add_argument("--urls", nargs="+", required=True, help="image URLs or local paths (PNG/JPG/SVG)")
    ap.add_argument("--sections", nargs="+", type=int, metavar="IDX",
                    help="section indices to attach to, paired with --urls in order "
                         "(default: sections that have an image_brief)")
    ap.add_argument("--alt", nargs="+", metavar="TEXT",
                    help="alt text per image (sets image_alt); needed when the "
                         "target section has no image_brief/image_alt yet")
    args = ap.parse_args()

    issue_path = ISSUES_DIR / f"{args.slug}.json"
    if not issue_path.exists():
        sys.stderr.write(f"issue file not found: {issue_path}\n")
        return 1
    issue = read_json(issue_path)

    if args.sections:
        target_idxs = args.sections
        n_sections = len(issue["sections"])
        bad = [i for i in target_idxs if not 0 <= i < n_sections]
        if bad:
            sys.stderr.write(f"section index out of range (0..{n_sections - 1}): {bad}\n")
            return 1
    else:
        target_idxs = [i for i, s in enumerate(issue["sections"]) if s.get("image_brief")]
        if not target_idxs:
            sys.stderr.write(
                "no sections have an image_brief; pass --sections IDX [IDX ...] "
                "(and --alt) to say where images go\n"
            )
            return 1
    if len(args.urls) != len(target_idxs):
        sys.stderr.write(
            f"warning: {len(args.urls)} images for {len(target_idxs)} target sections; "
            f"attaching the first {min(len(args.urls), len(target_idxs))}\n"
        )
    if args.alt and len(args.alt) != len(args.urls):
        sys.stderr.write(f"--alt count ({len(args.alt)}) must match --urls count ({len(args.urls)})\n")
        return 1

    asset_dir = DOCS_DIR / "assets" / args.slug
    asset_dir.mkdir(parents=True, exist_ok=True)

    attached = []
    for n, (idx, src) in enumerate(zip(target_idxs, args.urls), start=1):
        dest = fetch(src, asset_dir / f"illustration-{n}")
        rel = dest.relative_to(DOCS_DIR).as_posix()  # e.g. assets/<slug>/illustration-1.png
        issue["sections"][idx]["image"] = rel
        if args.alt:
            issue["sections"][idx]["image_alt"] = args.alt[n - 1]
        attached.append({"section_index": idx, "path": rel})

    write_json(issue_path, issue)
    print(json.dumps({"slug": args.slug, "attached": attached}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

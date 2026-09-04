#!/usr/bin/env python
"""Generate this issue's illustrations with Gemini and attach them to the issue.

Reads the image briefs from issues/<slug>.json, sends each (plus the config's
illustration_style) to a Gemini image model, saves PNGs into docs/assets/<slug>/,
and sets sections[...]["image"] on the issue file.

Usage:
    python tools/generate_illustrations.py --slug home-batteries
    python tools/generate_illustrations.py --slug x --model gemini-2.5-flash-image

Free Gemini key: https://aistudio.google.com  ->  GEMINI_API_KEY in .env
For hand-made art instead, use download_assets.py with local PNG paths.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys

from _common import (
    DEFAULT_GEMINI_IMAGE_MODEL,
    DOCS_DIR,
    ISSUES_DIR,
    env,
    gemini_client,
    load_config,
    read_json,
    write_json,
)

EXT_BY_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _image_from_response(resp):
    """Return (bytes, ext) for the first inline image part, or raise."""
    cands = getattr(resp, "candidates", None) or []
    for cand in cands:
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, str):
                    data = base64.b64decode(data)
                ext = EXT_BY_MIME.get(getattr(inline, "mime_type", ""), ".png")
                return data, ext
    reason = getattr(cands[0], "finish_reason", "?") if cands else "no candidates"
    raise RuntimeError(f"Gemini returned no image (finish_reason={reason})")


def generate_one(client, model: str, prompt: str) -> tuple[bytes, str]:
    from google.genai import types

    try:
        resp = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
    except Exception as e:  # noqa: BLE001 - some model builds reject response_modalities
        if "response_modalities" in str(e) or "modalit" in str(e).lower():
            resp = client.models.generate_content(model=model, contents=prompt)
        else:
            raise
    return _image_from_response(resp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--model", help=f"image model (default: {DEFAULT_GEMINI_IMAGE_MODEL})")
    args = ap.parse_args()

    cfg = load_config()
    model = args.model or env("GEMINI_IMAGE_MODEL") or DEFAULT_GEMINI_IMAGE_MODEL
    style = (cfg.get("illustration_style") or "").strip()

    issue_path = ISSUES_DIR / f"{args.slug}.json"
    if not issue_path.exists():
        sys.stderr.write(f"issue file not found: {issue_path}\n")
        return 1
    issue = read_json(issue_path)

    targets = [(i, s) for i, s in enumerate(issue["sections"]) if s.get("image_brief")]
    if not targets:
        sys.stderr.write("no sections with an image_brief; nothing to generate\n")
        return 1

    client = gemini_client()
    asset_dir = DOCS_DIR / "assets" / args.slug
    asset_dir.mkdir(parents=True, exist_ok=True)

    attached, failed = [], []
    for n, (idx, section) in enumerate(targets, start=1):
        prompt = section["image_brief"]
        if style:
            prompt = f"{prompt}\n\nStyle: {style}"
        sys.stderr.write(f"[illustrations] {n}/{len(targets)} section {idx}: {section['image_brief'][:60]}...\n")
        try:
            data, ext = generate_one(client, model, prompt)
        except Exception as e:  # noqa: BLE001 - report and keep going
            sys.stderr.write(f"[illustrations] section {idx} failed: {e}\n")
            failed.append(idx)
            continue
        dest = asset_dir / f"illustration-{n}{ext}"
        dest.write_bytes(data)
        rel = dest.relative_to(DOCS_DIR).as_posix()
        issue["sections"][idx]["image"] = rel
        attached.append({"section_index": idx, "path": rel})

    write_json(issue_path, issue)
    print(json.dumps({"slug": args.slug, "model": model, "attached": attached, "failed": failed}))
    if failed and not attached:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

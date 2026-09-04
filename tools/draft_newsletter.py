#!/usr/bin/env python
"""Turn research JSON into a structured newsletter issue.

Usage:
    python tools/draft_newsletter.py --research .tmp/research_home-batteries.json
    python tools/draft_newsletter.py --research .tmp/research_x.json --no-images

Output:
    issues/<slug>.json  -- the canonical issue file (status: "draft")
    stdout: JSON listing the image briefs the agent should now generate
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from _common import (
    ISSUES_DIR,
    extract_json,
    generate,
    load_config,
    model_id,
    read_json,
    resolve_provider,
    slugify,
    write_json,
)

ALLOWED_TAGS = "p, h3, strong, em, a, ul, ol, li, blockquote"

PROMPT = """You are the writer for "{publication}" - {tagline}

Write issue {number} from the research below. Audience: smart non-specialists. \
Tone: clear, concrete, no hype, no filler. Target ~6 minutes reading time \
(roughly 900-1300 words across all sections).

RESEARCH JSON:
{research}

Return ONLY a JSON object in a ```json fenced block:

{{
  "title": "specific, inviting issue title (<= 70 characters)",
  "dek": "one-sentence standfirst that says what the reader will learn (<= 160 characters)",
  "sections": [
    {{
      "heading": "short section heading",
      "body_html": "1-4 paragraphs. Only these tags: {allowed}. Link factual claims inline with <a href=\\"...\\">. No headings inside body_html.",
      "image_brief": "{image_rule}",
      "image_alt": "{image_alt_rule}"
    }}
  ],
  "sources": [{{"title": "...", "url": "https://..."}}]
}}

Rules:
- 4 to 6 sections. The first section is the lede (no image_brief).
- {image_count_rule}
- image_brief (when present) is a standalone illustration prompt: describe a \
single clear conceptual scene, no text in the image.
- image_alt (when present) plainly describes that illustration for screen readers.
- Do NOT include a "Sources" section in body_html; list sources in the JSON \
"sources" array (dedupe, keep the most useful 5-10)."""


def draft(research: dict, cfg: dict, number: int, provider: str, model: str, with_images: bool) -> dict:
    if with_images:
        image_rule = "illustration prompt for 2-3 of the sections, else null"
        image_alt_rule = "screen-reader description when image_brief is set, else null"
        image_count_rule = "Exactly 2 or 3 sections (not the lede) have a non-null image_brief AND image_alt; the rest use null for both."
    else:
        image_rule = "always null"
        image_alt_rule = "always null"
        image_count_rule = "Every section uses null for image_brief and image_alt."

    prompt = PROMPT.format(
        publication=cfg.get("publication", "the newsletter"),
        tagline=cfg.get("tagline", ""),
        number=number,
        research=json.dumps(research, ensure_ascii=False, indent=2),
        allowed=ALLOWED_TAGS,
        image_rule=image_rule,
        image_alt_rule=image_alt_rule,
        image_count_rule=image_count_rule,
    )
    text = generate(provider, model, prompt, grounded=False, max_tokens=16000)
    return extract_json(text)


def next_issue_number() -> int:
    n = 0
    if ISSUES_DIR.exists():
        for f in ISSUES_DIR.glob("*.json"):
            try:
                n = max(n, int(read_json(f).get("number", 0)))
            except Exception:  # noqa: BLE001 - skip unreadable files
                pass
    return n + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--research", required=True, help="path to .tmp/research_<slug>.json")
    ap.add_argument("--slug", help="override the issue slug")
    ap.add_argument("--no-images", action="store_true", help="text-only issue; skip illustrations")
    ap.add_argument("--provider", choices=["anthropic", "gemini"], help="force an LLM backend")
    ap.add_argument("--model", help="override the model id")
    args = ap.parse_args()

    cfg = load_config()
    research = read_json(args.research)
    topic = research.get("topic") or "untitled"
    slug = args.slug or slugify(topic)
    provider = resolve_provider(args.provider, cfg)
    model = model_id(provider, cfg, args.model)
    number = next_issue_number()

    sys.stderr.write(f"[draft] issue {number} slug={slug} provider={provider} model={model} images={not args.no_images}\n")
    content = draft(research, cfg, number, provider, model, with_images=not args.no_images)

    sections = []
    briefs = []
    for i, s in enumerate(content.get("sections", [])):
        brief = s.get("image_brief") or None
        alt = s.get("image_alt") or None
        if args.no_images:
            brief = alt = None
        sections.append({
            "heading": s.get("heading", ""),
            "body_html": s.get("body_html", ""),
            "image_brief": brief,
            "image_alt": alt,
            "image": None,
        })
        if brief:
            briefs.append({"section_index": i, "brief": brief, "alt": alt})

    sources = content.get("sources") or [
        {"title": x.get("title", x.get("url", "")), "url": x.get("url", "")}
        for x in research.get("sources", [])
    ]
    sources = [s for s in sources if s.get("url")][:10]

    issue = {
        "number": number,
        "slug": slug,
        "title": content.get("title", topic),
        "dek": content.get("dek", ""),
        "date": date.today().isoformat(),
        "topic": topic,
        "status": "draft",
        "sections": sections,
        "sources": sources,
    }
    out = ISSUES_DIR / f"{slug}.json"
    write_json(out, issue)

    print(json.dumps({
        "slug": slug,
        "issue_file": str(out),
        "number": number,
        "sections": len(sections),
        "image_briefs": briefs,
        "illustration_style": cfg.get("illustration_style", "").strip(),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

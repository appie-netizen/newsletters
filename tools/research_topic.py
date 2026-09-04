#!/usr/bin/env python
"""Research a newsletter topic with an LLM + web search.

Backend is auto-selected (Gemini if only GEMINI_API_KEY is set, else Anthropic);
force it with --provider or $NEWSLETTER_PROVIDER.

Usage:
    python tools/research_topic.py --topic "state of home batteries 2026"
    python tools/research_topic.py --topic "..." --slug home-batteries --provider gemini

Output:
    .tmp/research_<slug>.json  -- structured findings with a sources list
    (also prints a one-line summary to stdout)

Exits non-zero if the topic yields no usable material.
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import (
    extract_json,
    generate,
    load_config,
    model_id,
    resolve_provider,
    slugify,
    tmp_path,
    write_json,
)

PROMPT = """You are a research assistant for a newsletter. Research this topic \
using web search and return findings as JSON.

TOPIC: {topic}

Prefer sources published within the last {recency} months; note in the summary \
if the topic is largely older. Every key point and statistic must be traceable \
to one of the sources you list.

Return ONLY a JSON object in a ```json fenced block, shaped exactly like this:

{{
  "topic": "{topic}",
  "summary": "2-4 sentence plain-language overview of where things stand",
  "key_points": ["specific, factual statement", "..."],
  "stats": ["<number> - what it measures - (source name, date)", "..."],
  "quotes": [{{"text": "...", "speaker": "name, role", "source_url": "https://..."}}],
  "sources": [{{"title": "...", "url": "https://...", "published": "YYYY-MM-DD or ''"}}]
}}

Aim for 6-9 key_points, 3-6 stats, 0-3 quotes, 5-12 sources. If you genuinely \
cannot find enough material, still return valid JSON with what you have and say \
so in the summary."""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, help="what the newsletter issue is about")
    ap.add_argument("--slug", help="override the derived slug")
    ap.add_argument("--recency-months", type=int, help="override config research.recency_months")
    ap.add_argument("--provider", choices=["anthropic", "gemini"], help="force an LLM backend")
    ap.add_argument("--model", help="override the model id")
    args = ap.parse_args()

    cfg = load_config()
    slug = args.slug or slugify(args.topic)
    recency = args.recency_months or int((cfg.get("research") or {}).get("recency_months", 6))
    provider = resolve_provider(args.provider, cfg)
    model = model_id(provider, cfg, args.model)

    sys.stderr.write(f"[research] topic={args.topic!r} slug={slug} provider={provider} model={model}\n")
    prompt = PROMPT.format(topic=args.topic, recency=recency)
    text = generate(provider, model, prompt, grounded=True, max_tokens=16000)

    data = extract_json(text)
    data.setdefault("topic", args.topic)
    for key in ("key_points", "stats", "quotes", "sources"):
        data.setdefault(key, [])

    if not data.get("summary") or (not data["key_points"] and not data["sources"]):
        sys.stderr.write(
            "[research] no usable material found for this topic. "
            "Try a broader or differently worded topic.\n"
        )
        return 1

    out = tmp_path(f"research_{slug}.json")
    write_json(out, data)
    print(json.dumps({
        "slug": slug,
        "research_file": str(out),
        "provider": provider,
        "key_points": len(data["key_points"]),
        "stats": len(data["stats"]),
        "sources": len(data["sources"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

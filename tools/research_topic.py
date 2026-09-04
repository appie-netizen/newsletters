#!/usr/bin/env python
"""Research a newsletter topic with Claude + web search.

Usage:
    python tools/research_topic.py --topic "state of home batteries 2026"
    python tools/research_topic.py --topic "..." --slug home-batteries --recency-months 12

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
    anthropic_client,
    env,
    extract_json,
    load_config,
    model_id,
    run_messages,
    slugify,
    tmp_path,
    write_json,
)

# Dynamic-filtering web search (Opus 4.6+/Sonnet 4.6+). Falls back to the basic
# variant automatically on a 400.
WEB_SEARCH_PRIMARY = env("WEB_SEARCH_TOOL_TYPE") or "web_search_20260209"
WEB_SEARCH_FALLBACK = "web_search_20250305"

PROMPT = """You are a research assistant for a newsletter. Research this topic \
and return findings as JSON.

TOPIC: {topic}

Use web search. Prefer sources published within the last {recency} months; note \
in the summary if the topic is largely older. Every key point and statistic must \
be traceable to one of the sources you list.

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


def research(topic: str, recency: int, model: str) -> dict:
    client = anthropic_client()
    prompt = PROMPT.format(topic=topic, recency=recency)

    def call(tool_type: str) -> str:
        tools = [{"type": tool_type, "name": "web_search", "max_uses": 8}]
        return run_messages(client, model=model, prompt=prompt, tools=tools, max_tokens=16000)

    try:
        text = call(WEB_SEARCH_PRIMARY)
    except Exception as e:  # noqa: BLE001 - retry once with the basic tool variant
        msg = str(e).lower()
        if "web_search" in msg or "tool" in msg or "400" in msg:
            sys.stderr.write(
                f"web search tool '{WEB_SEARCH_PRIMARY}' rejected ({e}); "
                f"retrying with '{WEB_SEARCH_FALLBACK}'\n"
            )
            text = call(WEB_SEARCH_FALLBACK)
        else:
            raise

    data = extract_json(text)
    data.setdefault("topic", topic)
    for key in ("key_points", "stats", "quotes", "sources"):
        data.setdefault(key, [])
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, help="what the newsletter issue is about")
    ap.add_argument("--slug", help="override the derived slug")
    ap.add_argument("--recency-months", type=int, help="override config research.recency_months")
    ap.add_argument("--model", help="override the Claude model id")
    args = ap.parse_args()

    cfg = load_config()
    slug = args.slug or slugify(args.topic)
    recency = args.recency_months or int((cfg.get("research") or {}).get("recency_months", 6))
    model = args.model or model_id(cfg)

    sys.stderr.write(f"[research] topic={args.topic!r} slug={slug} model={model}\n")
    data = research(args.topic, recency, model)

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
        "key_points": len(data["key_points"]),
        "stats": len(data["stats"]),
        "sources": len(data["sources"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

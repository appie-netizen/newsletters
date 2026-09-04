# Newsletter Automation

## Objective

Given a topic, produce a researched, illustrated newsletter issue and publish it
as a page on the static site (GitHub Pages). Distribution is the published URL —
there is no email step. Run this whenever the user asks for "a newsletter about X".

## Inputs

- `topic` (required) — what the issue is about, e.g. "the state of home batteries in 2026".
- `--no-images` (optional) — text-only issue; skips illustration generation and its credit cost.
- `slug` (optional) — defaults to a slugified topic; only override to avoid a clash.

## LLM backend

`draft_newsletter.py` auto-picks a backend: **Gemini** (`gemini-flash-latest`) if
only `GEMINI_API_KEY` is set, **Anthropic** if `ANTHROPIC_API_KEY` is set. Force
with `--provider` / `NEWSLETTER_PROVIDER`.

**Free-tier reality (Gemini key without a billing account):** text drafting works;
Google Search grounding and image generation return `429`. So on the free path:
- **Research is done by the agent in-session** (its own web search), which then
  writes `.tmp/research_<slug>.json` in the shape `research_topic.py` would.
  `research_topic.py` is only for keys/backends that have grounded search.
- **Infographics are SVGs authored by the agent** (see step 3).

## Tools Used

- `tools/research_topic.py --topic "..."` — LLM + web search → `.tmp/research_<slug>.json`.
- `tools/draft_newsletter.py --research .tmp/research_<slug>.json [--no-images]` —
  drafts structured content → `issues/<slug>.json` (status `draft`); prints image briefs.
- `tools/generate_illustrations.py --slug <slug>` — Gemini image model, one image
  per brief (style appended from config), attaches them to the issue JSON.
- `tools/download_assets.py --slug <slug> --urls <p1> <p2> ...` — alternative to the
  above: import images you made in Canva / elsewhere (URLs or local file paths).
- `tools/build_site.py --drafts` — renders `docs/` (index, issue pages, `feed.xml`, CSS).
- `tools/preview_site.py --slug <slug>` — serves `docs/` on localhost for review.
- `tools/publish_site.py --slug <slug>` — flips status to `published`, rebuilds,
  commits, pushes. `--dry-run` to see what it would do.

## Steps

1. Derive `slug` from the topic. Gather research:
   - Free path: the agent web-searches the topic, then writes
     `.tmp/research_<slug>.json` (keys: topic, summary, key_points[], stats[],
     quotes[], sources[{title,url,published}]).
   - Grounded backend available: `python tools/research_topic.py --topic "..."`.
   If little material exists, ask the user to reword or broaden the topic.
2. Run `draft_newsletter.py --research .tmp/research_<slug>.json` (add `--no-images`
   for a text-only issue, or to hand-place SVGs in step 3).
3. Infographics (skip for `--no-images` / text-only issues):
   - **Free path (no billing): SVG.** Draft with `--no-images`, then the agent
     authors 2-3 SVG infographics from the research data (stat callouts, simple
     bar/line charts, concept diagrams) in the config's theme colors, and attaches
     them: `python tools/download_assets.py --slug <slug> --urls a.svg b.svg
     --sections 1 3 --alt "..." "..."`.
   - Gemini images (needs Google billing): `python tools/generate_illustrations.py --slug <slug>`.
   - Canva/other: export PNGs, then `download_assets.py ... --urls file1.png ...`.
4. Run `build_site.py --drafts`.
5. Run `preview_site.py --slug <slug>` (background it, then open / show the user
   `http://127.0.0.1:8000/issues/<slug>.html`). **Present the title + dek and wait
   for the user's approval.** To revise: edit `issues/<slug>.json` directly and
   re-run steps 4–5 — no API cost.
6. On approval: run `publish_site.py --slug <slug>`.
7. Give the user the live URL and note that Pages takes about a minute to update.

## Outputs

- `issues/<slug>.json` — canonical issue content (committed; source of truth).
- `docs/` — the built site (committed; regenerable with `build_site.py`).
- Live page: `<base_url>issues/<slug>.html`, listed on the index and in `feed.xml`.

## Edge Cases & Failure Handling

- **`research_topic.py` exits 1** → no usable sources. Reword/broaden the topic.
- **No LLM credentials** → set `GEMINI_API_KEY` (free: aistudio.google.com) or
  `ANTHROPIC_API_KEY` in `.env`.
- **Anthropic web search tool rejected (400)** → auto-retries with the basic
  `web_search_20250305` variant; if that also fails, set `WEB_SEARCH_TOOL_TYPE`.
- **Gemini model 404 / bad model name** → override `GEMINI_MODEL` /
  `GEMINI_IMAGE_MODEL` in `.env` with a current id.
- **Gemini image quota exhausted / `generate_illustrations.py` fails** → make the
  art by hand and import it with `download_assets.py`, or null the section's
  `image_brief`/`image_alt` and rebuild.
- **`build_site.py` exits 1: "missing image_alt"** → an illustrated section has no
  alt text. Add `image_alt` in `issues/<slug>.json` and rebuild.
- **`build_site.py` exits 1: "image file missing"** → the illustration step didn't
  run or produced fewer images than briefs. Re-run it, or null that section's
  `image`/`image_brief`/`image_alt` in the JSON.
- **`publish_site.py`: "no 'origin' remote"** → the issue is marked published and
  docs rebuilt, but nothing was pushed. Add the GitHub remote and re-run, or
  `git push` manually.
## Notes / Learnings

- Research is cached at `.tmp/research_<slug>.json`. Re-drafting, restyling, and
  rebuilding cost nothing — only steps 1–3 call an LLM.
- With Gemini's free tier (aistudio.google.com), the whole pipeline runs at zero
  cost within daily quotas (~500 requests/day, plenty for a newsletter). Free-tier
  inputs may be used by Google for training — fine for public topics.
- GitHub Pages redeploys ~1 minute after a push. The build itself is instant.
- Run `build_site.py` after ANY manual edit to an issue JSON, or the site won't
  reflect it.
- Drafts never appear on the public index or in the feed unless `--drafts` is
  passed to `build_site.py` (which `publish_site.py` never does).
- Model defaults: `gemini-2.5-flash` (Gemini) / `claude-opus-5` (Anthropic).
  Override with `GEMINI_MODEL` / `NEWSLETTER_MODEL` / `--model`.

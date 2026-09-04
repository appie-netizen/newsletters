# Newsletter Automation

## Objective

Given a topic, produce a researched, illustrated newsletter issue and publish it
as a page on the static site (GitHub Pages). Distribution is the published URL —
there is no email step. Run this whenever the user asks for "a newsletter about X".

## Inputs

- `topic` (required) — what the issue is about, e.g. "the state of home batteries in 2026".
- `--no-images` (optional) — text-only issue; skips illustration generation and its credit cost.
- `slug` (optional) — defaults to a slugified topic; only override to avoid a clash.

## Tools Used

- `tools/research_topic.py --topic "..."` — Claude + web search → `.tmp/research_<slug>.json`.
- `tools/draft_newsletter.py --research .tmp/research_<slug>.json [--no-images]` —
  Claude drafts structured content → `issues/<slug>.json` (status `draft`); prints
  the image briefs to generate.
- `generate_image` (MCP, agent-run) — one image per brief, appending the config's
  `illustration_style` to each brief.
- `tools/download_assets.py --slug <slug> --urls <u1> <u2> ...` — downloads images
  into `docs/assets/<slug>/` and attaches them to the issue JSON (in brief order).
- `tools/build_site.py --drafts` — renders `docs/` (index, issue pages, `feed.xml`, CSS).
- `tools/preview_site.py --slug <slug>` — serves `docs/` on localhost for review.
- `tools/publish_site.py --slug <slug>` — flips status to `published`, rebuilds,
  commits, pushes. `--dry-run` to see what it would do.

## Steps

1. Derive `slug` from the topic. Run `research_topic.py`. If it exits non-zero,
   the topic was too narrow/obscure — ask the user to reword or broaden it.
2. Run `draft_newsletter.py` (add `--no-images` if the user asked for no images
   or wants zero credit cost). Read the printed `image_briefs` and `illustration_style`.
3. For each brief: call `generate_image` with `"<brief>. <illustration_style>"`.
   Collect the result image URLs in the same order as the briefs.
4. Run `download_assets.py` with those URLs. (Skip 3–4 entirely for `--no-images`.)
5. Run `build_site.py --drafts`.
6. Run `preview_site.py --slug <slug>` (background it, then open / show the user
   `http://127.0.0.1:8000/issues/<slug>.html`). **Present the title + dek and wait
   for the user's approval.** To revise: edit `issues/<slug>.json` directly and
   re-run steps 5–6 — no API cost.
7. On approval: run `publish_site.py --slug <slug>`.
8. Give the user the live URL and note that Pages takes about a minute to update.

## Outputs

- `issues/<slug>.json` — canonical issue content (committed; source of truth).
- `docs/` — the built site (committed; regenerable with `build_site.py`).
- Live page: `<base_url>issues/<slug>.html`, listed on the index and in `feed.xml`.

## Edge Cases & Failure Handling

- **`research_topic.py` exits 1** → no usable sources. Reword/broaden the topic.
- **Web search tool rejected (400)** → the tool auto-retries with the basic
  `web_search_20250305` variant; if that also fails, set `WEB_SEARCH_TOOL_TYPE` in `.env`.
- **`build_site.py` exits 1: "missing image_alt"** → the draft has an illustrated
  section without alt text. Add `image_alt` in `issues/<slug>.json` and rebuild.
- **`build_site.py` exits 1: "image file missing"** → `download_assets.py` wasn't
  run, or fewer images than briefs. Re-generate/re-download, or null out that
  section's `image_brief`/`image_alt` in the JSON.
- **`publish_site.py`: "no 'origin' remote"** → the issue is marked published and
  docs rebuilt, but nothing was pushed. Add the GitHub remote and re-run, or
  `git push` manually.
- **`generate_image` unavailable / out of credits** → rerun the workflow with
  `--no-images`, or manually null the image fields and rebuild.

## Notes / Learnings

- Research is cached at `.tmp/research_<slug>.json`. Re-drafting, restyling, and
  rebuilding cost no API spend — only steps 1–3 hit paid APIs.
- GitHub Pages redeploys ~1 minute after a push. The build itself is instant.
- Run `build_site.py` after ANY manual edit to an issue JSON, or the site won't
  reflect it.
- Drafts never appear on the public index or in the feed unless `--drafts` is
  passed to `build_site.py` (which `publish_site.py` never does).
- Model defaults to `claude-opus-5`; override with `NEWSLETTER_MODEL` or `--model`.

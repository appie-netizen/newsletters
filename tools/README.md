# Tools

Deterministic Python scripts. Each does one job: API calls, transforms, file/db ops.

## Conventions

- **Runnable standalone**: `python tools/<name>.py --help` should explain usage.
- **Args via CLI flags** (argparse), not interactive prompts.
- **Secrets from `.env`** via `python-dotenv` — never hardcode keys.
- **Output**: print JSON to stdout or write to `.tmp/`; exit non-zero on failure.
- **Errors**: fail loud with a clear message and stack trace. The agent reads these.
- **Idempotent** where possible.

## Shared helpers

- `tools/_common.py` — load env, `.tmp/` path helpers, JSON I/O.

## Inventory

| Script | Purpose | Used by workflow |
|--------|---------|------------------|
| _common.py | shared helpers: env, config, slugify, LLM dispatch (Gemini/Claude), JSON extraction | (all) |
| research_topic.py | LLM + web search → `.tmp/research_<slug>.json` | newsletter_automation |
| draft_newsletter.py | research JSON → `issues/<slug>.json` + image briefs | newsletter_automation |
| generate_illustrations.py | Gemini image model → `docs/assets/`, attach to issue | newsletter_automation |
| download_assets.py | import hand-made / MCP images from URLs or local paths, attach to issue | newsletter_automation |
| build_site.py | render `docs/` (index, issue pages, feed.xml, CSS) from `issues/*.json` | newsletter_automation |
| preview_site.py | serve `docs/` on localhost for review | newsletter_automation |
| publish_site.py | mark issue published, rebuild, git commit + push | newsletter_automation |

Templates for the site build live in `tools/templates/` (`*.j2`).

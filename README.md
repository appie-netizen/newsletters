# Newsletters Demo

A [WAT framework](CLAUDE.md) project (Workflows, Agents, Tools) for producing newsletters.

## Layout

```
workflows/   Markdown SOPs — what to do and how
tools/       Python scripts — deterministic execution
.tmp/        Disposable intermediates (gitignored)
.env         Secrets (gitignored) — copy from .env.example
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env                              # then add ANTHROPIC_API_KEY
Copy-Item newsletter.config.example.yaml newsletter.config.yaml   # then edit
```

Publishing needs a GitHub repo with Pages set to **Deploy from a branch → `main` / `/docs`**,
and `base_url` in `newsletter.config.yaml` pointed at the resulting URL.

## How it works

The agent reads a workflow in `workflows/`, figures out the inputs it needs,
runs the matching `tools/*.py` scripts in order, handles failures, and writes
deliverables to cloud services. See [CLAUDE.md](CLAUDE.md) for the full model.

## Workflows

- [newsletter_automation](workflows/newsletter_automation.md) — topic in →
  researched, illustrated issue published to the static site (GitHub Pages).

# Redesign kickoff — `<CLIENT NAME>`

Run `workflows/redesign_website.md` end-to-end for:

- **URL:** https://example.com
- **Slug:** `client-slug`
- **Business:** one-line what they do + location
- **Contact:** phone / email if known
- **Persona:** who uses the site and primary job-to-be-done
- **Business context:** scope, budget band if any, primary conversion action
- **Brand continuity:** NEW IDENTITY OK / LIKE-FOR-LIKE (keep colours, logo, photos) — pick one and say why
- **Why pick:** short note from scout / intake

## Hard gates (mandatory)

1. At start, set the active slug file (Stop hook + push guard):
   write `client-slug` into `.claude/active_redesign_slug`

2. After each phase, update `sites/<slug>/gates.json` (or run verify with `--write-status`).

3. Before any nested-repo remote push, and before declaring done:

```
python tools/verify_redesign_gates.py --slug client-slug
```

Must exit **0**. See `workflows/redesign_website/GATES.md` (G0–G7).

4. When all gates pass, remove `.claude/active_redesign_slug`.

## Deliverables expected

Create `sites/<slug>/`, capture → Audits A/B/C → brief → mockup → Next.js nested
`<slug>-website/` (or de-jonge root pattern), private GitHub under **appie-netizen**,
Vercel-ready publish. Send Alfred the GitHub + Vercel/preview link when verify passes.

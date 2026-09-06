# Redesign Website

## Objective

Take an existing business's website and produce (a) three independent design
audits, each grounded in a distinct published framework, (b) a synthesised
redesign brief, and (c) a concrete redesign — first as a visual canvas mockup,
then as production code.

Run this when someone gives you a URL and asks for a redesign, a design
critique, or "what's wrong with this site".

The three audits are deliberately different lenses. Run all three; do not
collapse them:

| Audit | Framework | Finds |
|-------|-----------|-------|
| **A — Brand & Anti-Slop** | Impeccable (`impeccable.style`) | generic / AI-cheap / off-brand visual choices; design-system drift |
| **B — UI Design Principles** | design-audit skill (`agentskill.sh/@vitalikpestov/design-audit`) | weak hierarchy, spacing, alignment, consistency, responsiveness |
| **C — UX / Usability** | ux-audit skill (`github.com/jezweb/claude-skills`) | what breaks or creates friction when a real person uses the live site |

Rubrics live in `workflows/redesign_website/`:
`audit_a_brand_slop.md`, `audit_b_ui_principles.md`, `audit_c_ux_usability.md`,
`redesign_brief_template.md`.

## Inputs

- `url` (required) — the site to audit, e.g. `https://acme-plumbing.com`
- `persona` (optional) — who uses the site and what they're trying to do. If
  not given, ask once before Audit C (it's persona-locked).
- `business_context` (optional) — what the business does, the goal of the
  redesign, the primary conversion action, hard constraints (CMS, brand
  assets that must stay, timeline). Ask if the site alone doesn't make it clear.
- `pages` (optional) — specific paths to audit. Default: crawl up to 6
  same-site pages from the start URL.
- `reference_designs` (optional) — e.g. the user's magicpath / grokbot board
  <https://www.magicpath.ai/files/446346949956878336>. Treat as inspiration
  for direction, not as a spec.

## Tools Used

- `tools/capture_site.py` — Playwright capture of the live site. Screenshots at
  375 / 768 / 1440, rendered HTML, headings/landmark outline, the colour + type
  tokens actually in use, console errors/warnings, 4xx/5xx + failed requests,
  pragmatic vitals (LCP/CLS/nav timing), and an axe-core run.
  `python tools/capture_site.py --url <url> [--slug <slug>] [--pages / /about ...] [--max-pages N] [--no-axe]`
  → writes `.tmp/audit_<slug>/` (`capture.json` + `screens/`, `html/`, `outline/`).
  First run needs the browser binary once: `python -m playwright install chromium`.
- **Artifact** (default delivery) — publish each finished report as its own
  Artifact web page: renders the screenshots, severity tables and before/after,
  and gives the user a shareable link. No setup.
- `tools/export_gdoc.py` — *optional* alternative: push a finished Markdown
  report to Google Docs.
  `python tools/export_gdoc.py --md <file.md> --title "<title>" [--folder-id <id>]`
  → prints `{"doc_id", "url"}`. Needs one-time Google OAuth setup (see the
  script's docstring); use only if the user asks for Docs specifically.
- **Claude design canvas** (the `design` skill) — build the redesign mockup as
  editable artboards.
- **v0.dev** (external, user's account) — turn the chosen mockup into
  React/Tailwind/shadcn code. The agent writes the v0 prompt; the user runs it.

## Steps

### 0. Set up the site folder
Every redesign engagement gets its own folder: `sites/<client-slug>/` (see
`sites/README.md` for the convention). Create it now with a `README.md`
(status, links, brand-direction call, decisions log — copy the shape from an
existing client folder). Everything that follows — capture data stays in
`.tmp/audit_<slug>/` as usual, but the actual code project (once you reach
step 7) lives inside this client folder, and the client folder's `README.md`
is where you record artifact links, the GitHub repo, and the deploy URL as
you go. Don't let client-uploaded files (logos, zips, screenshots) sit loose
in the repo root — move them into `sites/<slug>/client-uploads/`.

### 1. Frame the job
Confirm `url`. Get or infer `business_context` and the primary conversion
action. Ask for the `persona` now if it isn't obvious — Audit C needs it. Pick
a `slug` (default: the domain, matching the `sites/<slug>/` folder from step 0).

**Brand-continuity check (ask if not obvious):** does this business want a new
identity (palette/type/imagery reinvented — audit A's findings drive a fresh
system) or a like-for-like redesign (keep their existing colours, logo, and
content/images; only fix structure, hierarchy, and UX)? This changes what
Audit A's "direction" section recommends and what the brief's design-system
section locks — state the answer at the top of the brief.

### 2. Capture the site
```
python tools/capture_site.py --url <url> --slug <slug>
```
Add `--pages` if the user named specific pages, or `--max-pages 8` for a bigger
site. Use `--no-axe` only if offline. Read the printed `summary` block and skim
`capture.json` + the screenshots before auditing anything. If the start URL
fails to load, stop and report — everything downstream depends on this.

### 2b. Benchmark 2–3 competitors (do this before designing, and revisit before sign-off)
Ask the client for the sites they measure themselves against (or find the
obvious sector leaders). Capture each with `capture_site.py --slug comp-<name>
--max-pages 4 --no-axe` and read the desktop home screenshot + the `tokens`
block. You are calibrating the *level*: typeface ambition, hero treatment
(full-bleed photo vs boxed), section rhythm, use of depth/shadow, how bold the
accent gets. A conservative "fix the broken template" redesign will clear the
audit gates but still look a tier below a bureau-built competitor — name the
gap explicitly in the brief and decide with the client how far to push
(targeted polish vs full art-direction pass). Re-open these screenshots when
the build is done and compare side-by-side before you call it finished.

### 3. Run the three audits (independent passes)
Best run as three separate sub-agents so each stays in its own lens, then you
synthesise. Each produces one Markdown file in `.tmp/audit_<slug>/`.

- **Audit A** → follow `workflows/redesign_website/audit_a_brand_slop.md`
  → `.tmp/audit_<slug>/audit_a.md`
- **Audit B** → follow `workflows/redesign_website/audit_b_ui_principles.md`
  → `.tmp/audit_<slug>/audit_b.md`
- **Audit C** → follow `workflows/redesign_website/audit_c_ux_usability.md`.
  This one is **interaction-first**: drive the live site with Playwright (type,
  click, submit, resize, watch console/network). A pass with no Interaction
  Manifest is verdict **Incomplete**. → `.tmp/audit_<slug>/audit_c.md`

Each audit references screenshots by their `.tmp/audit_<slug>/screens/...` path
so the reader can follow along.

### 4. Synthesise the redesign brief
Copy `workflows/redesign_website/redesign_brief_template.md` to
`.tmp/audit_<slug>/redesign_brief.md` and fill it in:
- Dedupe findings across the three audits; a bug found by both B and C is one
  entry with two sources.
- Rank combined priorities by impact × ease.
- Every Audit C hard-gate failure and every Audit B Phase-1 finding becomes a
  **Must-fix** with an observable acceptance criterion.
- Lock the design system values (ramp, type scale, spacing, radius, buttons).
- Write the page & section plan, each change citing the finding that drove it.

### 5. Deliver the audits
Publish each of the four documents (three audits + brief) as its own
**Artifact** — this is the default, no setup needed. One combined, well-designed
Artifact (scorecard + all three audits + the brief as sections) reads better
than four separate links; either is fine. Record the URL(s) in the client's
`sites/<slug>/README.md`. Only use `tools/export_gdoc.py` if the user
specifically asks for Google Docs (needs one-time OAuth — see the script).

### 6. Design — mockup
Prefer the `design` skill (Claude Design canvas) — seed it from the redesign
brief; build home (desktop + mobile), the primary conversion page, and one
interior page; publish for hands-on editing. **It needs `node` or `bun` on
this machine** (its `seed-canvas.mjs` helper won't run without one); if
neither is installed and the user doesn't want to install one yet, fall back
to a hand-built static Artifact instead: author each page as its own
`.dc.html`-style fragment (plain HTML/CSS, no runtime), scope each fragment's
CSS with a unique class prefix (rewrite bare selectors like `body{}`/`h1{}` to
`.mN{}`/`.mN h1{}`), inline any photos as base64 `data:` URIs, and assemble
them into one page with labelled sections. Either way: load `artifact-design`
first, do the one-look-then-publish pass, and if the mockup uses a font tied
to real content (a client-supplied logo font), check whether it's a Google
Font before assuming it can be live text — see the design-system section below.

### 7. Design — production code
Two ways to get there — ask which the user wants, or default to the second once
a project has proven the local toolchain works:

**(a) v0.dev first.** Write a v0.dev prompt: the design system, page/section
plan, Must-fix acceptance criteria, and (if new-identity) the "slop tells to
avoid" list. The user runs it in v0 and iterates until they hit their v0 usage
limit or are happy with the structure. Then take the codebase over directly:
- User exports the v0 project (Download ZIP or push to GitHub) into
  `sites/<slug>/<slug>-website/`.

**(b) Build it directly, no v0.** Once Node is installed and a prior project's
skeleton exists in `sites/`, it's faster to write the Next.js/Tailwind project
by hand than to round-trip through v0's chat: copy the proven skeleton
(`package.json`, `next.config.mjs`, `tsconfig.json`, `postcss.config.mjs`,
`app/globals.css`'s `@theme` token pattern) from an existing `sites/*/`
project, swap in the new design tokens and content, author
`components/`+`app/` from the mockup and brief directly. **Pin dependency
versions deliberately** — after `npm install`, read the output for
vulnerability warnings before moving on; don't guess a version number, copy
one already proven in another `sites/*/` project when you can. Pull every
contact/address/KvK-BTW/etc. fact from the audit's `capture.json`/HTML rather
than inventing or leaving it bracketed, when the live site actually has it.

Either way, from here on every change follows the same loop:
- If `node`/`npm` aren't installed on this machine, install Node LTS
  (`winget install OpenJS.NodeJS.LTS` on Windows) — once. New shells pick up
  PATH automatically; a shell that was already open needs the PATH exported
  by hand for the rest of its session (e.g. `export PATH="$PATH:/c/Program
  Files/nodejs"` in Bash).
- Give the project its own GitHub repo (`gh repo create <slug>-website
  --private --source=. --remote=origin --push`) if it doesn't have one, so
  Vercel can deploy it independently of this outer repo. Add
  `sites/*/*-website/` to this repo's `.gitignore` so the nested repo's files
  aren't also tracked here.
- From here, every change is: edit → `npm run build` (catches real errors) →
  free the dev port if a previous server is still holding it
  (`netstat -ano | grep :<port>` then `taskkill //PID <pid> //F` — stopping
  the background task alone does not reliably kill the underlying `node.exe`
  on Windows) → `npm start -- -p <port>` in the background → confirm with
  `curl` → Playwright screenshots → **dispatch a fresh subagent to review the
  screenshots** (this session's own image-read budget runs out fast in a long
  conversation — a clean subagent context reads images fine and doubles as an
  independent QA pass) → fix anything real → only commit + push once verified.
  Never push unverified.
- The user just watches the Vercel deployment (auto-rebuilds on every push) —
  no more v0 credits needed for iteration.

### 8. Verify
Run `tools/capture_site.py` against the deployed/preview URL and re-check
Audit C's hard gates and the brief's Must-fix boxes. Nothing is "done" until
every Must-fix has an observable pass.

## Outputs

- `sites/<slug>/README.md` — the client's status + every link below, kept current.
- `.tmp/audit_<slug>/` — capture artifacts + the four Markdown reports
  (regenerable; disposable).
- **Artifacts** (deliverables): three audits + the redesign brief, and the mockup.
- **`sites/<slug>/<slug>-website/`** — the v0-exported, then hand-maintained,
  codebase; own GitHub repo + Vercel deployment, owned by the user.

## Edge Cases & Failure Handling

- **`playwright` not installed / no browser binary** → `pip install -r
  requirements.txt` then `python -m playwright install chromium` (one-time,
  ~150 MB, free). Re-run step 2.
- **Start URL won't load** (DNS, timeout, hard block) → stop. Try `https://`
  vs `http://`, try `www.`; if it's bot-blocked (Cloudflare challenge), tell
  the user — an audit of a page you can't load is worthless.
- **JS-heavy / SPA site** → `capture_site.py` already waits for `networkidle` +
  1.2s. If content is still missing, pass explicit `--pages` and bump
  `--settle-ms`.
- **`axe.run` fails** (CDN blocked / offline) → re-run with `--no-axe`; note in
  Audit C that automated a11y was skipped and do a manual keyboard + contrast pass.
- **Auth-gated pages** → capture only what's public; note the gap. Don't
  attempt logins.
- **Audit C can't interact** (forms hard-blocked, captcha on submit) → don't
  fake it. Record what was reachable, mark the flow **Incomplete**, and audit
  the rest.
- **Google OAuth not set up** → `export_gdoc.py` exits 2 with setup steps.
  Deliver the `.md` files directly; circle back once `credentials.json` exists.
- **Google Docs Markdown import mangles a table** → keep tables simple (no
  merged cells); if it still breaks, the Doc is editable — fix in place.
- **Site is already good** → say so. A short "keep / minor polish" audit is a
  valid outcome; don't invent findings to fill a template.
- **Paid API calls** (LLM calls inside sub-agent audits use Claude/Gemini) →
  the capture and export tools cost nothing. If an audit pass needs to be
  re-run repeatedly, check with the user first per project policy.

## Notes / Learnings

- The three frameworks overlap least on purpose: A is taste, B is structure, C
  is behaviour. Findings that show up in two audits are the highest-confidence
  ones — surface them first in the brief.
- Audit C's own rule: no Interaction Manifest ⇒ verdict `Incomplete`, and "it
  looked fine" never upgrades to `Pass`. Honour that even under time pressure.
- `capture.json.tokens` is the fastest read on design-system drift — if there
  are 12 text colours and 5 greys, Audit A's "Absent" verdict writes itself.
- Keep the redesign brief as the single source of truth. The canvas and v0 both
  read from it; when they drift, pull them back to it rather than editing three
  places.
- magicpath.ai is fine for loose exploration; this workflow otherwise prefers
  the Claude canvas → v0.dev → local-code path because it ends in a real,
  owned, deployable codebase.
- **Reading many images in one long session eventually hard-fails** ("many-image
  request" size-limit error, even on a tiny image) — this is a cumulative
  session budget, not a per-image size problem. Fix: dispatch a fresh
  general-purpose subagent to `Read` and describe/QA images; a clean context
  reads them fine. Works reliably both for "describe this reference design"
  and "QA these screenshots for bugs" — use it for both.
- **Recolouring a client's Canva-exported "traced" SVG** (looks like flat art
  but is actually a raster image piped through `feColorMatrix` luminance-mask
  filters): find the `</mask></defs>` marker and replace the *first*
  `<image .../>` tag after it with a solid `<rect fill="#yourhex"/>` — reuses
  their derived alpha silhouette regardless of the original ink colour, and
  shrinks the file a lot (drops a duplicate base64 blob). Verify by rendering
  and sampling pixels with Pillow, not by eye.
- **Rendering a client-supplied raw `.svg` file to PNG via Playwright hangs
  indefinitely** ("waiting for fonts to load" never resolves) if you
  `page.goto()` it directly as a document. Wrap it in a tiny HTML shell
  (`<img src="file://...">`) and screenshot *that* instead — reliable, and lets
  you set an explicit background (or `omit_background=True` for real
  transparency; a plain screenshot bakes the page background in as opaque).
- **A client's logo font is often a paid font** (e.g. Recoleta Alt / Latinotype)
  available inside Canva but not licensed for embedding as live web text. Fine
  baked into an exported logo image/SVG (it becomes shapes, not a font
  reference); for site-wide headings, check fonts.google.com for the same
  name first, else use a free lookalike (Fraunces is a reasonable stand-in for
  soft/rounded serif branding) until/unless they buy a web licence.
- **Don't assume a v0/Canva export's assets are all wired up correctly** —
  after adding a new logo/asset, grep the *whole* codebase for the *literal
  old filename*, not just for the component that's supposed to render it. A
  stale `<Image src="/brand/old-file.png">` sitting in an unrelated component
  (e.g. the hero, not the header) is exactly the kind of thing a
  component-name search misses.
- **A redesign can pass every audit gate and still read a tier below the
  client's benchmark competitor.** The audits catch broken/absent/inaccessible;
  they don't catch "tasteful but timid". Signs you've built timid: display type
  is a friendly rounded sans (Quicksand etc.) instead of something with a
  point of view; the hero photo is boxed in a column instead of full-bleed;
  every section sits on the same white plane; one flat radius + no shadow
  everywhere; the accent only ever appears as thin chips. Fix = a deliberate
  art-direction pass (see step 2b): pick a display face with character, go
  full-bleed on the hero, give each section its own ground for rhythm, add
  real elevation tokens, and let the accent own a whole band.
- **`next/font/google` variable fonts with a width axis**: `Archivo({ subsets:
  ['latin'], axes: ['wdth'], variable: '--font-archivo' })` builds fine under
  Next 16 — but you must NOT also pass `weight` (static weights and an `axes`
  request are mutually exclusive). Then `font-weight` and
  `font-variation-settings: 'wdth' <62–125>` both work in CSS. If the axis ever
  fails to load, the `wdth` setting is silently ignored (font stays normal
  width) — safe degradation, but screenshot to confirm you actually got the
  expanded stance.
- (Add rate limits, SPA quirks, per-site gotchas here as you hit them.)

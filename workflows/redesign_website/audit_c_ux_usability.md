# Audit C — UX / Usability

**Source:** the *ux-audit* skill by jezweb — <https://github.com/jezweb/claude-skills> (`plugins/dev-tools/skills/ux-audit`)
**Question it answers:** what actually *breaks or creates friction* when a real person uses this site?
**Run against:** the **live site** (Playwright, driven interactively) + `.tmp/audit_<slug>/capture.json`.

Audit C is **interaction-first**. A static look at screenshots and HTML cannot
produce a verdict — you must type, click, submit, scroll, resize, and watch
what happens. A sweep that didn't interact ends in verdict **Incomplete**.

---

## Verdict states (pick exactly one)

- **Pass** — 0 Critical, 0 High, all hard gates green, Interaction Manifest complete.
- **Conditional Pass** — 0 Critical, 0 High, gates green, but Medium/Low present.
- **Fail** — ≥1 Critical or High, OR any hard gate red.
- **Incomplete** — manifest missing required entries, a phase skipped, or the
  interaction was implausibly fast. Cannot be upgraded to Pass because "it
  looked fine".

---

## Hard gates (auto-fail — cannot be downgraded)

Most come straight from `capture.json.summary`; confirm the rest live.

| Gate | Threshold | Severity |
|------|-----------|----------|
| Console errors during walkthrough | > 0 | Critical |
| Console warnings during walkthrough | > 0 | High |
| Network 5xx | > 0 | Critical |
| Network 403 / 404 on real pages | > 0 | High |
| Layout collapse at any tested viewport | > 0 | High |
| axe-core **critical** on any page | > 0 | Critical |
| axe-core **serious** on any page | > 0 | High |
| LCP on the main route | > 4.0 s | High |
| CLS on the main route | > 0.25 | High |
| INP on the main route | > 500 ms | High |

---

## Phase 1 — Pre-flight

1. **Persona lock.** Ask the user once if unknown: *"Who uses this site and
   what are they trying to get done?"* Capture role, tech comfort, time
   pressure, emotional state, device. Write it at the top of the report.
   Every finding must be defensible *from this persona's view* — if you catch
   yourself thinking "a developer would know…", stop.
2. **Also always run the first-time-user lens** (below) regardless of persona.
3. **Target = the live site.** Real auth, real latency, real CDN.
4. **Viewports:** 375 / 768 / 1024 / 1280 / 1440. Don't exceed ~1920.

---

## Phase 2 — Discovery

- **Sitemap:** one line per page with its purpose (`/pricing — plans, compare,
  checkout entry`). Use `capture.json.pages` + nav crawl.
- **Key tasks (3–5):** the spine of the audit. The real jobs someone comes to
  this site to do — *get a quote, book a call, buy X, find the phone number,
  compare plans*. Ask the user or infer from nav.
- **Element inventory per page:** every interactive element. Drives the
  coverage ratio (`tested 24 of 27 elements on /`).

---

## Phase 3 — Walkthrough (the audit itself)

### Interaction Manifest — MANDATORY

Log every action with a timestamp and the selector. Required per page:

- ≥ 1 input **typed into** (real text, not just focused)
- ≥ 1 primary action triggered (Submit / Send / Buy / Book / Search)
- ≥ 1 modal or detail view opened
- ≥ 1 console read *after* the primary action
- ≥ 1 screenshot **before and after** the primary action
- verification of the expected result (form cleared, toast shown, URL changed,
  list updated)

```
INTERACTION MANIFEST — /contact
  Persona: small-business owner, in a hurry, low patience for forms
  [x] 14:02:11  typed "Test Co" into #company
  [x] 14:02:14  typed "not-an-email" into #email  (testing validation)
  [x] 14:02:16  clicked Send  (button[type=submit])
  [x] 14:02:17  observed: inline error "enter a valid email" — good
  [x] 14:02:20  fixed email, clicked Send
  [x] 14:02:23  observed: success state? -> NONE. page just scrolled to top.  <-- finding
  [x] console read: 0 errors / 1 warning (favicon 404)
  [x] screenshots: contact-before.png, contact-after.png
```

### Task traversal
For each key task: start from the site entry point (not mid-flow). Walk it
**as the persona** — if they'd skim, skim; if they'd misread a label, note it.
Screenshot every state change (default → hover → active → after click → loaded
→ confirmation). Track the cost: click count, decision points, dead ends. Try
an interrupt (close tab mid-task, reopen — did anything survive?). At the end,
answer as the persona: *Did it end clearly? Would I come back? One thing to
make this twice as easy?*

### First-time-user lens (mandatory, every multi-step flow)
Adopt *someone here for the very first time, no prior context*. Per screen:

| Question | Catches |
|----------|---------|
| Could I complete the task without help or guessing? | hidden knowledge baked into the flow |
| Are labels plain language, not internal jargon? | `SKU`, `MOQ`, internal product codes in the UI |
| Do options explain what they do, not just name themselves? | opaque dropdown values |
| Are defaults good enough to accept and move on? | required fields with no default |
| Is it obvious what the primary action is on this screen? | 3 buttons competing |
| Would I bounce because I don't understand a step? | that's a UX bug — log it |

### Live interaction smoke — every interactive control
1. Click it. 2. Watch the network tab — did a request fire, to the right URL?
3. Watch the DOM — did something visibly change? 4. If nothing changed in 2 or
3, that's a bug (a button that looks alive but does nothing).

### Responsive / multi-pane sweep
At each viewport: scroll the longest page, screenshot, check for overflow,
clipped text, invisible text, vertical-stacked text, broken nav, off-screen
CTAs, tap targets < 44px.

---

## Phase 4 — Polish checks

- **Component states:** buttons, inputs, cards, dropdowns, toasts — default /
  hover / focus / active / disabled / loading / error. Missing states are findings.
- **Forms:** persistent labels (not placeholder-only), inline validation,
  specific error copy, sensible defaults, input types correct on mobile.
- **Navigation:** "where am I?" always answerable; active state on current
  page; logo links home; footer complete; search works if present.
- **Feedback:** every destructive/committing action (submit, delete, pay,
  send) has a clear confirmation and a clear result.

---

## Phase 5 — Scenario battery (run all that apply)

1. **First contact** — figure the site out cold; write a 2-min plain guide to each key task.
2. **Interrupted workflow** — abandon mid-form, refresh, come back. State survive?
3. **Wrong-turn recovery** — click the wrong thing on purpose. Clicks to recover?
4. **Returning user** — repeat a task. Faster? Anything remembered?
5. **Keyboard only** — every task with no mouse. Focus visible, tab order sane, Esc closes.
6. **Heavy content** — long product names, long lists, big text blocks — layout holds?
7. **Destructive confidence** — is consent clear before submit/pay/delete? Undo?
8. **Restricted context** — slow 3G throttle; does it stay usable? loading states?
9. **Reduced motion** — `prefers-reduced-motion: reduce` respected?
10. **Round-trip** — go A → B, act on B, return to A — does A reflect the change?
11. **Real-flavour data** — apostrophes, accents, very long strings, emoji in
    form fields — silently stripped or truncated?

---

## Findings format — every finding

**ID** (`C-1`, `H-2`, `M-3`, `L-4`) · **Layer** (Architecture / Interaction /
Visual / Feedback / Delight) · **Severity** · **Surface** (route + viewport) ·
**Persona** · **Reproduce** (numbered steps) · **Observed** · **Expected** ·
**Evidence** (screenshot paths, console/network lines) · **Suspected location**
(if the site's source is available) · **Smallest possible patch** (concrete and
committable — never "consider…", "improve…", "make better").

---

## Phase 6 — Verdict block (top of the report)

```
============================================================
VERDICT: <Pass / Conditional Pass / Fail / Incomplete>

Persona: <locked persona>
Pages audited: <N> / <M>
Interaction Manifest: complete / incomplete (<x> of <y> required entries)

Hard gates: console err <n> · warn <n> · 5xx <n> · 403/404 <n> ·
            layout-collapse <n> · axe-critical <n> · axe-serious <n>   (all must be 0)
Performance (on /<route>): LCP <n>s / CLS <n> / INP <n>ms   (budget 4.0s / 0.25 / 500ms)

Findings:  Critical <n>   High <n>   Medium <n>   Low <n>
Coverage:  <tested>/<inventoried> interactive elements

TOP 5 (impact × ease):
  1–5. <ID> <title> — one line on why this beats the rest
============================================================
```

Then: findings by severity, a **Perfection roadmap** (Quick wins 24–48h /
Structural 1–2 wk / Advanced polish), and a one-paragraph *"if this site were a
physical object, would I want to hold it?"* close.

## Output — `audit_c_ux_usability` (Google Doc)

The verdict block, the manifest(s), findings, roadmap, and closing paragraph.
Feeds the redesign brief's **Flows & interaction** and **Must-fix** sections.

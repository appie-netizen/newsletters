# Redesign Brief — <Business>

Single source of truth for the redesign. Synthesised from Audits A, B and C.
Everything the canvas mockup and the v0 build read from here. Delivered as a
Google Doc alongside the three audits.

---

## 1. Context

- **Business:** <what they do, who for>
- **Current site:** <url>  ·  captured <date>  ·  <N> pages audited
- **Primary audience & their job:** <who lands here and what they need to do>
- **Functional mode** (from Audit A): <Persuade / Operate / Read / Experience>
- **Business goal of the redesign:** <e.g. more qualified quote requests>
- **Primary conversion action:** <the one thing a visitor should do>
- **Constraints:** <CMS, tech stack, brand assets that must stay, timeline, budget>

---

## 2. Audit verdicts at a glance

| Audit | Verdict / score | The one thing it says |
|-------|-----------------|-----------------------|
| A — Brand & Anti-Slop | system: <Systemic/Drifting/Absent> · <N> slop tells | <one line> |
| B — UI Principles | <n> Critical / <n> Refinement / <n> Polish | <one line> |
| C — UX / Usability | <Pass/Conditional/Fail/Incomplete> · <n>C <n>H <n>M <n>L | <one line> |

**Combined top priorities** (deduped across all three, ranked by impact × ease):

1. …
2. …
3. …
4. …
5. …

---

## 3. Must-fix (non-negotiable in the redesign)

From Audit C hard-gate failures and Audit B Phase-1, plus any Audit A finding
that destroys brand credibility. Each is a pass/fail acceptance criterion.

- [ ] <fix> — *was:* <state> · *acceptance:* <observable condition>
- [ ] …

---

## 4. Keep (do not lose in the redesign)

The things that already work — content, flows, proof, personality. The
redesign is not a reset.

- …

---

## 5. Design system (define before designing)

From Audit B. These become tokens in the canvas and in v0.

- **Neutral ramp:** <0 / 50 / 100 / 200 / 300 / 400 / 500 / 600 / 700 / 800 / 900>
- **Brand + accent:** <hex, and where each is allowed to appear>
- **Type:** display `<family>` · text `<family>` · scale `<12 / 14 / 16 / 20 / 25 / 31 / 39 / 49>`
- **Line-height:** body `<1.5>` · headings `<1.15>` · prose measure `<66ch>`
- **Spacing scale:** `<4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96>`
- **Radius:** controls `<6px>` · cards `<12px>` · never nest equal radii
- **Elevation:** <one shadow ramp, 2–3 steps>
- **Container:** max-width `<1200px>` · gutter `<24px>` · grid `<12-col>`
- **Buttons:** primary / secondary / ghost — <fill, text, border, hover for each>
- **Motion:** duration `<180ms>` · easing `<cubic-bezier(...)>` · honour `prefers-reduced-motion`

---

## 6. Brand & visual language

From Audit A. The posture, not just the palette.

- **Voice / posture:** <e.g. plain-spoken, specific, no hype>
- **Palette move:** <away from AI-beige/indigo → toward …>
- **Type move:** <e.g. one confident grotesk, no italic serif>
- **Imagery:** <real photography of the work / product · no stock gradients>
- **What "designed by a team" looks like here:** <2–3 sentences>
- **Slop tells to specifically avoid:** <list the ones flagged in Audit A>

---

## 7. Page & section plan

Per page: purpose, sections top-to-bottom, the one primary action, what
changed vs today and why (cite the audit finding).

### <Home / route>
- **Purpose:** <…>  ·  **Primary action:** <…>
- **Sections:**
  1. <section> — <content> — *change:* <…> (ref B-C1 / C-H2 / A-slop-3)
  2. …

### <Next page>
- …

---

## 8. Flows & interaction

From Audit C. The A→B→A journeys and their fixes.

- **<Task name>:** <steps> — *fix:* <what changes> — *acceptance:* <observable>
- Form rules: <labels, validation, error copy, success state>
- Empty / loading / error states required: <list>

---

## 9. Accessibility & performance targets

- Contrast ≥ 4.5:1 body / 3:1 large · visible focus on every interactive element
- axe-core: 0 critical, 0 serious
- Tap targets ≥ 44px · no horizontal scroll 320–1920px
- LCP < 2.5s · CLS < 0.1 · INP < 200ms (stricter than the audit gate — this is a rebuild)

---

## 10. Deliverables & handoff

- **Canvas mockup:** <artifact link> — artboards: <list, e.g. Home desktop/mobile, Contact, one interior>
- **v0 project:** <link> — stack: <React / Tailwind / shadcn>
- **Definition of done:** every Must-fix box checked, verified with a fresh
  `tools/capture_site.py` run against the built preview and a re-run of Audit C's
  hard gates.

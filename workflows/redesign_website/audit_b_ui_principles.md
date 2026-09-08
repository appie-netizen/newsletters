# Audit B — UI Design Principles

**Source:** the *design-audit* skill by vitalikpestov — <https://agentskill.sh/@vitalikpestov/design-audit>
**Question it answers:** is the interface *structurally sound* — hierarchy, spacing, consistency, alignment?
**Run against:** `.tmp/audit_<slug>/` screenshots at all three viewports + `capture.json`.

Audit B is the rigor pass. Adopt the skill's stance:

> *You are a UI/UX architect. You do not write features or touch functionality.
> You make the site feel inevitable — like no other design was ever possible.*

Every finding must tie back to **hierarchy reasoning**. No cosmetic-only notes.

---

## The 6 principles (the lens for every finding)

1. **Simplicity is architecture** — every element must justify its existence.
   The best interface is the one the user never notices. *Remove until it
   breaks, then add back the last thing.*
2. **Hierarchy drives everything** — visual weight must match functional
   importance. **One primary action per screen.**
3. **Consistency is non-negotiable** — the same component looks and behaves
   identically everywhere. Every value references a token. No hardcoded
   one-off colours, spacing, or sizes. Ever.
4. **Alignment is precision** — elements sit on a grid. A 1–2px misalignment
   is a violation, not a rounding error.
5. **Whitespace is a feature** — space creates structure. Crowded interfaces
   feel cheap.
6. **Responsive is the real design** — mobile-first. Every screen must feel
   intentional at every viewport, not merely "not broken".

---

## The Reduction Filter (apply to every element)

Before proposing *any* addition, and to justify every *removal*:

1. **Can it be removed** without losing meaning? → remove it.
2. **Would a user need instruction** to understand it? → redesign it.
3. **Does it feel inevitable** in place, or arbitrary? → if arbitrary, it's a finding.

---

## The 14 dimensions — score each

Walk all screenshots. For each dimension: **state** (Solid / Weak / Broken),
the specific evidence, and the token-anchored fix.

| # | Dimension | What "Solid" looks like |
|---|-----------|--------------------------|
| 1 | **Visual hierarchy** | eye lands on the one most important thing first; H1 > H2 > body is unmistakable by size *and* weight *and* space |
| 2 | **Spacing & rhythm** | consistent scale (4/8/12/16/24/32/48); related things close, unrelated things apart; section padding consistent |
| 3 | **Typography** | ≤2 families; a real modular scale; line-length 45–75ch for prose; line-height ~1.5 body / ~1.2 headings; no orphaned single words in headings |
| 4 | **Colour usage** | one neutral ramp + limited brand/accent; colour carries meaning consistently; text contrast ≥ 4.5:1 (≥3:1 large) |
| 5 | **Alignment & grid** | shared max-width; columns and edges line up across sections; optical alignment where mechanical looks off |
| 6 | **Components** | buttons/inputs/cards identical everywhere; one button hierarchy (primary / secondary / ghost), used correctly |
| 7 | **Iconography** | one icon set, one weight, one size rhythm; icons align to text baseline; every icon earns its place |
| 8 | **Motion** | purposeful, fast (150–250ms), eased; respects `prefers-reduced-motion`; nothing loops without reason |
| 9 | **Empty / loading / error states** | designed, not default; skeletons match final layout; errors say what to do next |
| 10 | **Dark mode** (if present) | true re-mapping of tokens, not inverted colours; contrast holds; no pure-black/pure-white |
| 11 | **Density** | matches the functional mode; nothing cramped, nothing floating in a void |
| 12 | **Responsiveness** | reflows intentionally at 375 / 768 / 1440; tap targets ≥ 44px; no horizontal scroll; nav collapses sensibly |
| 13 | **Accessibility (visual)** | focus states visible; contrast passes; text resizes; hit areas adequate; not colour-alone signalling |
| 14 | **Content fit** | real-length content doesn't break layout; long headings, long names, empty sections all hold |

---

## Finding format — every finding, no exceptions

> **What's wrong → what it should be → why it matters**

- **What's wrong:** specific and located. *"Primary and secondary CTAs in the
  hero are the same size and weight; the eye can't choose."*
- **What it should be:** concrete and token-anchored. *"Secondary CTA →
  `button/ghost` (transparent bg, `text/secondary`, no fill). Primary stays
  `button/primary`."* Never *"make it stand out more"*.
- **Why it matters:** the hierarchy consequence. *"Two equal CTAs split
  attention and measurably lower click-through on the intended action."*

Anti-patterns that get a finding rejected: "make it softer", "improve
spacing", "consider a different colour", "modernise this". If it isn't a
committable instruction with a value, it isn't done.

---

## Phased output

- **Phase 1 — Critical:** actively harms usability or comprehension now
  (broken hierarchy, contrast failures, unreadable line-length, layout
  collapse, inconsistent primary components).
- **Phase 2 — Refinement:** brings it to professional standard (spacing scale,
  alignment, type scale, component unification, state design).
- **Phase 3 — Polish:** premium detail (optical alignment, micro-motion,
  hover calibration, empty-state personality).

---

## Output — `audit_b_ui_principles` (Google Doc)

```
# <Business> — UI Design Principles Audit
Source: design-audit skill (agentskill.sh/@vitalikpestov/design-audit)  |  Captured: <date>

## Overall assessment
<1–2 sentences on the current state of the design's structure>

## Dimension scorecard
| Dimension | State | Note |
|-----------|-------|------|
| Visual hierarchy | Weak | hero has 2 co-equal CTAs; H1/H2 differ by size only |
| Spacing & rhythm | Broken | section padding 40/64/48/72 — no scale |
| … (all 14) | | |

## Phase 1 — Critical
### B-C1 · <title>
What's wrong: …
What it should be: … (token: …)
Why it matters: …
Evidence: screens/<file>.png

## Phase 2 — Refinement
### B-R1 · …

## Phase 3 — Polish
### B-P1 · …

## Design-system values the redesign needs to define first
- Neutral ramp: <e.g. 0/50/100/…/900>
- Type scale: <e.g. 12 / 14 / 16 / 20 / 25 / 31 / 39>
- Spacing scale: <4 / 8 / 12 / 16 / 24 / 32 / 48 / 64>
- Button hierarchy: primary / secondary / ghost — <defined>
- Radius: <e.g. 6px controls, 12px cards>  ·  Container max-width: <e.g. 1200px>

## Notes for the build agent
<exact, unambiguous: "CardComponent border-radius 8px → 12px per token radius/lg">
```

Feeds the redesign brief's **Design system** and **Layout & hierarchy** sections.

# Audit A — Brand & Anti-Slop

**Source:** the *Impeccable* design framework — <https://impeccable.style/>
**Question it answers:** does this site look *considered and branded*, or *generic and AI-cheap*?
**Run against:** `.tmp/audit_<slug>/` (screenshots + `capture.json` tokens block).

Audit A is about taste and brand fidelity. It does not care whether a button
works (that's Audit C) or whether the grid is 4px-aligned (that's Audit B). It
cares whether a stranger would believe a real design team made deliberate
choices here.

---

## Step 1 — Name the functional mode

Impeccable's first move: every surface is built for one job. Score the site
against the mode it *should* be in, not a generic ideal.

| Mode | The surface exists to… | Gets it right when… |
|------|------------------------|---------------------|
| **Persuade** | win attention and belief (marketing / landing / pricing) | one clear claim, strong hierarchy, proof, a single obvious next action |
| **Operate** | let someone complete a task (app, dashboard, booking, checkout) | dense where it needs to be, quiet chrome, state always legible |
| **Read** | build understanding (docs, articles, guides) | measure ~65–75ch, generous leading, calm palette, minimal chrome |
| **Experience** | let the work lead (portfolio, product film, gallery) | imagery dominates, UI recedes, motion has intent |

Write one sentence: *"This is a **Persuade** surface for [business] whose job is
to get [audience] to [action]."* Every later finding is judged against that.

---

## Step 2 — Design-system coherence

A real design system *is inherited*, not reinvented per section. Check:

- **Colour** — count the distinct text + background colours in `capture.json`
  `tokens`. More than ~6–8 meaningful values (excluding true black/white and
  transparent) = no system, just accumulation. Are there 3 slightly different
  "greys"? 2 near-identical blues? That's drift.
- **Type** — how many font families? (2 is a system, 4 is a mess.) How many
  font sizes? Is there a visible scale (e.g. 14/16/20/28/40) or 15 arbitrary
  px values? Is weight used consistently (one bold weight, not 500/600/700
  scattered)?
- **Radius** — one or two corner radii used everywhere, or every card
  different? Nested elements over-rounded (a 16px radius inside another 16px
  radius)?
- **Spacing** — do gaps land on a rhythm (8/16/24/32) or random (13px, 27px)?
- **Shadows** — one elevation system, or a different shadow per component?

Verdict: **Systemic / Drifting / Absent.**

---

## Step 3 — The 61-point slop sweep

Impeccable ships a detector for the tells of AI-generated / template design.
Walk every screenshot and flag each that appears. Group and count.

### Typography tells
- [ ] Italic serif display headline used for "elegance" with no brand reason
- [ ] Centre-aligned body paragraphs wider than ~60ch
- [ ] Clipped / truncated labels, or text set in ALL CAPS with default tracking
- [ ] More than 2 type families; decorative font used for UI
- [ ] Headline and body the same size / weight — no hierarchy

### Colour & surface tells
- [ ] "AI beige" / muddy taupe palette, or the generic indigo-violet gradient
- [ ] Purple-to-blue hero gradient with white text (the default LLM look)
- [ ] Cards nested inside cards inside cards
- [ ] Ghost cards — bordered boxes containing almost nothing
- [ ] Over-rounding — pill everything, 24px radius on large panels
- [ ] Every section a different background colour for no reason
- [ ] Low-contrast grey-on-grey body text

### Layout tells
- [ ] Side-tab borders (a coloured 4px left border on every callout)
- [ ] Status-chip soup — rows of tiny coloured pills carrying no real signal
- [ ] Perfectly symmetrical 3-column "feature grid" with icon + heading + one line, ×3
- [ ] Equal visual weight on every section — no page rhythm, no climax
- [ ] Full-width everything; no considered max-width or margin logic

### Motion & detail tells
- [ ] Pulsing dots / "live" indicators that indicate nothing
- [ ] Everything fades-and-rises on scroll (the default AOS animation)
- [ ] Hover states that only change opacity
- [ ] Decorative floating blobs / grain / noise with no brand connection

### Copy tells
- [ ] Vague headline ("Empowering your business", "The future of X")
- [ ] Generic CTA ("Get Started", "Learn More" with no object)
- [ ] Feature names that describe the UI, not the benefit
- [ ] Placeholder-grade testimonials ("Great product!" — J. Smith)

For each flagged item: screenshot reference, where it appears, and the
one-line fix (what a designer would do instead).

---

## Step 4 — The "would I believe a team made this?" test

Three yes/no calls, defended in one sentence each:

1. **Intentional** — does every major section look chosen, or assembled?
2. **Branded** — swap the logo for a competitor's: would anything feel wrong?
   If not, there's no brand here.
3. **Confident** — does the page commit to a point of view, or hedge with
   generic reassurance everywhere?

---

## Output — `audit_a_brand_slop` (Google Doc)

```
# <Business> — Brand & Anti-Slop Audit
Source framework: Impeccable (impeccable.style)   |   Captured: <date>

## Verdict
<one paragraph: functional mode, system coherence verdict, slop density,
and the believe-a-team-made-this call>

Slop score: <N> tells flagged  (Typography <n> · Colour/Surface <n> · Layout <n> · Motion <n> · Copy <n>)
Design system: Systemic / Drifting / Absent

## Functional mode
This is a <mode> surface. Its job: <sentence>. It <does / does not> design for that job because <…>.

## Design-system findings
| Area | What's there now | What a system would do |
|------|------------------|------------------------|
| Colour | 11 near-duplicate values, 3 greys | one 5-step neutral ramp + 1 brand + 1 accent |
| … | | |

## Slop tells (ranked by how much they cheapen the page)
1. **<tell>** — <where> — screenshot `screens/home__desktop.png`. Fix: <what instead>.
2. …

## Keep
<the 2–4 things that are actually working and the redesign must not lose>

## Direction for the redesign
<3–5 sentences: the brand posture, palette move, type move, and the one
structural change that would make this look designed>
```

Feeds the redesign brief's **Brand & visual language** section.

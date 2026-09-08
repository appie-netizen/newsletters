# Redesign Website — Hard Gates (G0–G7)

These gates are **mandatory** for every `workflows/redesign_website.md` job.
Claude Code hooks call `tools/verify_redesign_gates.py`; Alfred/Claude must not
declare the job done or push the nested site repo until verify exits **0**.

## Active slug file

At **step 0** (site folder setup), write the client slug into
`.claude/active_redesign_slug` (plain text, one line).

While this file exists, the **Stop** hook blocks early exit if any gate fails,
and **PreToolUse (Bash)** blocks a remote push until verify passes.

Remove the file only when all gates pass.

## Verify command

```
python tools/verify_redesign_gates.py --slug <slug>
python tools/verify_redesign_gates.py --slug <slug> --write-status
```

`--write-status` updates `sites/<slug>/gates.json` with per-gate pass/fail.

Exit codes: `0` all pass · `2` one or more fail · `1` usage error.

## Gate list

| ID | Requirement |
|----|-------------|
| **G0** | `sites/<slug>/KICKOFF.md` and `sites/<slug>/README.md` exist |
| **G1** | `.tmp/audit_<slug>/capture.json` exists |
| **G2** | `.tmp/audit_<slug>/audit_a.md` (or `audit_a_*.md`), `audit_b*`, `audit_c*` each exist and **> 500 bytes** |
| **G3** | `.tmp/audit_<slug>/redesign_brief.md` exists and **> 500 bytes** |
| **G4** | Mockup or combined audit HTML under `sites/<slug>/` (`mockup/*.html` or `audit/*.html`) |
| **G5** | Nested Next.js project: `sites/<slug>/<slug>-website/package.json` **or** `sites/<slug>/*/package.json` with a `next` dependency **or** de-jonge pattern `sites/<slug>/package.json` with `next` |
| **G6** | Build succeeded: `.next/BUILD_ID` present under the Next.js project (and/or `gates.json` field `build_ok: true` *with* BUILD_ID) |
| **G7** | Nested origin points at `github.com/appie-netizen/` **and** HEAD resolves to a commit; optional stamp `gates.json` → `github_pushed` |

## When to stamp `sites/<slug>/gates.json`

After each phase, update progress (manually or via `--write-status`):

| After phase | Suggested stamps / notes |
|-------------|--------------------------|
| Step 0 folder + KICKOFF/README | G0 |
| Capture complete | G1 |
| Audits A/B/C written | G2 |
| Redesign brief filled | G3 |
| Mockup / combined HTML published into `sites/<slug>/` | G4 |
| Next.js project scaffolded | G5 |
| Production build succeeded | set `"build_ok": true` and ensure `.next/BUILD_ID` → G6 |
| Repo under appie-netizen + published | optional `"github_pushed": true` → G7 |

## Hook behaviour

- **SessionStart** — reminds the agent to use verify + this doc
- **Stop** — if `.claude/active_redesign_slug` is set, runs verify; exit 2 blocks stop and lists missing gates on stderr
- **PreToolUse / Bash** — if the command looks like a remote push and an active slug is set, runs verify first; exit 2 denies the push

## Done criteria

1. `python tools/verify_redesign_gates.py --slug <slug>` exits 0
2. Clear `.claude/active_redesign_slug`
3. Only then tell Alfred/the user the job is finished

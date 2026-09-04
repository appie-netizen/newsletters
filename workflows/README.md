# Workflows

Markdown SOPs. One file per workflow. The agent reads these to decide what to do.

## Template

```markdown
# <Workflow Name>

## Objective
What this workflow accomplishes and when to run it.

## Inputs
- `input_name` (required/optional) — description, format, where it comes from

## Tools Used
- `tools/<script>.py` — what it does, how to call it

## Steps
1. ...
2. ...

## Outputs
- Where results land (cloud service link, .tmp/ file, etc.) and their format

## Edge Cases & Failure Handling
- Known error → what to do

## Notes / Learnings
- Rate limits, timing quirks, discovered constraints (update as you learn)
```

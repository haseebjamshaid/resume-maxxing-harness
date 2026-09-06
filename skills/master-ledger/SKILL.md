---
name: master-ledger
description: Validates master_resume/master.json and reports the fact whitelists derived from it. Use after hand-editing the master resume, or when a tailoring run reports that a guardrail is disabled. Directory name is legacy; this checks the JSON master.
argument-hint: "[path to master.json, defaults to master_resume/master.json]"
---

# Check the master resume

The master is hand-edited JSON, so it is worth checking before relying on it.
There is no parsing or indexing step: deriving the whitelists is one call.

```bash
python3 scripts/lint_resume.py facts \
  --master master_resume/master.json \
  --out master_resume/.facts.json
```

## Read the counts

They are the guardrails' foundation, and two of them can be silently zero:

| Symptom | Meaning |
|---|---|
| `titles: 0` | The seniority ceiling is **disabled**. Add `personal.title_variants`. |
| `certifications: 0` | The no-drop check protects **nothing**. Populate `certifications`. |
| `numbers` far below what the resume contains | The master is thin, and tailoring will be blocked from using real figures. |
| `ids indexed` far below the bullet count | Bullets are missing ids, so their provenance cannot be verified. |

Warnings printed to stderr name any duplicate id, which would make provenance
ambiguous, and any missing top-level section.

Report the counts to the user, and say plainly if the master looks thin rather
than letting a tailoring run proceed on a weak foundation.

## What is deliberately excluded

Anything under `needs_review` is kept out of every whitelist. Those are claims
the user flagged as disputed or superseded, so they stay unusable until
resolved and written into a real bullet. Flagging a claim as shaky must not be
the thing that licenses its use.

If the master's counts look wrong because a figure sits in `needs_review`, say
so and let the user resolve it. Never work around the exclusion.

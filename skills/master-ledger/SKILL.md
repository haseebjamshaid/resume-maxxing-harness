---
name: master-ledger
description: Builds the indexed truth ledger and fact whitelists from the master resume PDF in master_resume/. Use before tailoring a resume, when the master resume has changed, or when master_resume/.ledger.md is missing or stale. Runs once per master, then is cached.
argument-hint: "[path to master resume, defaults to master_resume/]"
---

# Master ledger

Turns the master resume into two artefacts every later stage depends on:

| Artefact | Purpose |
|---|---|
| `master_resume/.ledger.md` | Human-readable, every claim carrying a stable id |
| `master_resume/.facts.json` | Closed whitelists the deterministic guardrails enforce |

Both are gitignored. Do not commit either, and do not paste ledger content
into a message that leaves this machine.

## 1. Check the cache first

```bash
ls -la master_resume/
shasum -a 256 master_resume/*.pdf 2>/dev/null
```

If `.ledger.md` exists and its recorded hash matches the PDF, **stop**. The
ledger is current and rebuilding it wastes a model pass. Report that it was
reused and move on.

If `master_resume/` holds no PDF, say so and point the user at
`master_resume/TEMPLATE.md`. Do not invent a ledger from an older output.

## 2. Extract the text deterministically

```bash
pdftotext -layout master_resume/<file>.pdf - > /tmp/master.txt
wc -w /tmp/master.txt
```

`pdftotext` is exact and free. Never retype or paraphrase the PDF by hand.

If it yields almost no text the PDF is a scan; tell the user rather than
guessing at the content.

## 3. Index it into the ledger

Rewrite the extracted text into `master_resume/.ledger.md` in this shape.
**Copy claims verbatim.** This is an indexing pass, not a writing pass: no
rephrasing, no tightening, no improving.

```markdown
<!-- source: abdul_haseeb_master.pdf  sha256: <hash>  indexed: YYYY-MM-DD -->

# FULL NAME
<title line> · <phone> · <location>
<email> · <linkedin> · <github>

## SUMMARY
[sum.1] The summary paragraph, copied verbatim.

## SKILLS
[skills.languages] Python, TypeScript / Node.js, SQL, Golang
[skills.data-eng] ClickHouse, DLT, ETL / ELT, Prefect

## EXPERIENCE
### Carbonteq | Senior Software Engineer | June 2022 - Present
[exp.carbonteq.scope] Role scope line, copied verbatim.

#### Healthcare Analytics ELT Platform *(Data Engineer, 2025 - present)*
- [exp.carbonteq.p1.b1] Owned the analytics transformation layer across 15+ healthcare data domains.
- [exp.carbonteq.p1.b2] Implemented CDC / merge-based incremental loading from MySQL into ClickHouse using DLT.

## PERSONAL PROJECTS
### Throughline: Local-First AI Second Brain *(Full-Stack, Python / FastAPI + React 19)*
- [proj.throughline.b1] Built a FastAPI backend over a hybrid sqlite-vec and FTS5 index.

## EDUCATION
### Institution | Degree | 2018 - 2022
[edu.1] Location and any detail, copied verbatim.

## CERTIFICATIONS
- IELTS 8.5
```

Id rules, since everything downstream cites them:

- Lowercase, dot-separated, stable across rebuilds.
- `exp.<employer>.p<N>.b<M>` for employer project bullets.
- `proj.<name>.b<M>` for personal projects.
- `skills.<category>`, `sum.N`, `edu.N`.
- Ids must never be reused for different content. Renumbering silently
  invalidates every provenance record that cites the old id.

Two structural requirements the guardrails depend on:

- **Client work and personal projects stay separate.** Anything not done for
  an employer belongs under `## PERSONAL PROJECTS`.
- **Certifications are `- ` bullets under `## CERTIFICATIONS`.** The
  no-drop check reads exactly that.

## 4. Build the fact whitelists

```bash
python3 scripts/lint_resume.py facts \
  --ledger master_resume/.ledger.md \
  --out master_resume/.facts.json
```

This is deterministic and takes no model pass. It is deliberately the same
code that later scans the tailored resume, so the whitelist cannot drift from
what it polices: anything the scanner can find in the output was, if genuinely
present, found in the ledger too.

## 5. Sanity-check the counts

The command prints how many of each fact it found. Read them:

- `titles: 0` means the seniority ceiling is **disabled**. Fix the
  `### Company | Title | dates` lines.
- `certifications: 0` means the no-drop check has nothing to protect. Fix the
  `## CERTIFICATIONS` bullets.
- A `numbers` or `technologies` count far below what the resume contains means
  the ledger is malformed. Every real figure must be in there, or tailoring
  will be blocked from using it.

Report the counts to the user, and say plainly if the ledger looks thin rather
than proceeding on a weak foundation.

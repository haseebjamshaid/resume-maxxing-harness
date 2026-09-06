# Output format

`output/<slug>/resume.md` must follow this shape exactly. The section set and
order are checked by `lint_resume.py`.

```markdown
# FULL NAME
<title line> · <phone> · <location>
<email> · <linkedin> · <github>

## SUMMARY
One paragraph. No bullet points.

## SKILLS
**Languages** Python, TypeScript / Node.js, SQL
**Backend & APIs** FastAPI, aiohttp / asyncio, REST, WebSocket
**Data Engineering** ClickHouse, dbt, ETL / ELT, CDC
...

## EXPERIENCE
### COMPANY NAME | Job Title | June 2022 - Present
One-line scope statement for the role.

#### Project Name *(Role, 2025 - ongoing)*
- **Bold lead-in claim** then plain continuation naming the specific tech.
- **Second claim** with the concrete figure copied from the master.

## PERSONAL PROJECTS
### Project Name *(Stack summary)*
- **Bold lead-in claim** then plain continuation.

## EDUCATION
### Institution Name | Degree | 2018 - 2022
Location.

## CERTIFICATIONS
- Credential, issuer, year.
```

## Section rules

| Section | Rule |
|---|---|
| Header | Copied from the master except the title line. Never invent contact details. |
| SUMMARY | Prose, no bullets. |
| SKILLS | `**Category**` then a comma list. Reorder categories and items by relevance. |
| EXPERIENCE | Employer, then projects nested beneath. **Client work only.** |
| PERSONAL PROJECTS | Own top-level section. Droppable when space is tight. |
| EDUCATION | Copied verbatim. |
| CERTIFICATIONS | **Always emitted.** Never drop an entry. |

`PERSONAL PROJECTS` is the only optional section. Every other heading must be
present, and all of them must appear in the order above.

## Why personal projects are separated

Nesting a personal project under an employer reads to a recruiter as paid work
for that employer. Keeping the employer block to client work only means
nothing in it can be misread, and the projects still get their own section.

## The title line is the main tailoring lever

The line under the name is a positioning statement and should be retargeted per
application, drawn from what the master supports. Reordering the SKILLS
categories is the second lever. Both are free: they change emphasis without
touching a single claim.

## Bullet convention

Open with a short bolded claim, then continue in plain text with the specific
technologies and figures. The bold half is what a six-second scan reads, so it
must carry the achievement rather than the tooling.

```
- **Owned the analytics transformation layer across 15+ data domains** built on
  a Hexagonal / Ports-&-Adapters design with reusable filesystem, DataFrame and
  SQL adapters.
```

## Length budget

Calibrated to a two-page resume. `lint_resume.py` enforces the total and the
per-bullet cap.

| Scope | Cap |
|---|---|
| Total | 1,250 words |
| SUMMARY | 90 words |
| SKILLS | 10 category rows |
| Experience projects | 4 |
| Bullets per project | 5 |
| Words per bullet | 32 |
| Personal projects | 3, at 3 bullets each |

When it does not fit, cut in this order: personal projects, then the
lowest-relevance experience project, then the weakest bullet in each remaining
project. Never cut certifications, and never compress a date range.

## Provenance sidecar

Every bullet under EXPERIENCE and PERSONAL PROJECTS needs a record in
`output/<slug>/provenance.json`:

```json
{
  "emitted": [
    {
      "path": "EXPERIENCE.acme.projects[0].bullets[1]",
      "source_id": "exp.acme.p1.b2",
      "original": "the master's text at that id, character for character",
      "value": "the emitted bullet text",
      "reason": "why this earns space against this job description"
    }
  ]
}
```

`source_id` is an id from `master_resume/master.json`. Both fields are
checked: the id must exist, and `original` must match the master's text at that
id exactly. A wrong id fails even when the quoted text appears elsewhere in the
master, so inventing a plausible-looking source does not work.

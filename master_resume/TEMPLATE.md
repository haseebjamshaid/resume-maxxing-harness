# Master resume: what to put in it

Your master resume is a single structured JSON file at
`master_resume/master.json`. Copy `master.example.json` and fill it in.

This folder is gitignored, so nothing you put here is committed even though
the repository is public. Only this file and the example are tracked.

Validate at any time:

```bash
python3 scripts/lint_resume.py facts --master master_resume/master.json
```

It prints the fact counts it derived and warns about anything that would
silently disable a guardrail.

## The one rule that makes tailoring work

**The master must be a superset, materially longer than any resume you would
send.** Aim for roughly twice your target length.

If the master and the target are the same size, there is nothing to select
from, and every stage collapses into rephrasing. Selection is where the value
is: deciding that this job wants the pipeline work and not the frontend work
beats any amount of rewording.

## The second rule, which surprises people

**Every number and technology you ever want to use must appear in the master.**

The guardrails treat it as a closed whitelist. A figure that is not in it is
rejected as fabricated *even when it is true*, because the checker has no way
to tell the difference. If you shipped something with a real, quotable number,
put the number in.

Numbers are compared as written, so `15+` and `15` are different claims.
Record them in the form you want to use.

## Structure

| Key | Holds |
|---|---|
| `personal` | Name and contact. `title_variants` are positioning lines the tailorer picks between. |
| `summary_variants` | Two or three summaries aimed at different role types. |
| `skills` | Rows of `{id, category, items}`. Include everything. |
| `experience` | Employers, each with `projects`, each with `bullets`. **Client work only.** |
| `personal_projects` | Side projects. Their own section, never nested under an employer. |
| `education` | Institution, degree, exact dates. |
| `certifications` | One entry each. Protected by the no-drop check. |
| `needs_review` | Disputed or unresolved claims. **Excluded from the whitelists.** |

Two structural points the guardrails depend on:

- **Keep personal projects out of `experience`.** A side project nested under
  an employer reads to a recruiter as paid work for that employer.
- **`certifications` must be populated.** The no-drop check protects whatever
  is listed there, and protects nothing if the list is empty.

## Ids

Every summary, skills row, scope, project and bullet carries an `id`, and
provenance cites it. Two rules:

- **Ids must be unique.** A duplicate makes provenance ambiguous, and
  validation reports it.
- **Ids must be stable.** Renumbering silently invalidates every provenance
  record that cited the old id. Add new ids rather than reshuffling.

Convention: `exp.<employer>.p<N>.b<M>`, `proj.<name>.b<M>`,
`skills.<category>`, `sum.<variant>`, `edu.<name>`, `cert.<name>`.

## needs_review

Use it for anything you are not sure you can defend, or where two old resumes
disagree. Its contents are deliberately kept out of the fact whitelists, so a
claim parked here **cannot** be used until you resolve it and write it into a
real bullet.

That is the point: flagging a claim as shaky must not be the thing that
licenses its use.

## Checklist

- [ ] Every employer, with exact date ranges including months
- [ ] Every project, under the right section
- [ ] Every real metric, written the way you want it to appear
- [ ] Every technology, including ones you use rarely
- [ ] Every certification, language and test score
- [ ] Both spellings where you use them (`TypeScript` and `Typescript`)
- [ ] Unique, stable ids throughout
- [ ] Roughly twice your target length

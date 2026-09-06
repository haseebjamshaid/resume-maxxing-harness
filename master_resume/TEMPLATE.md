# Master resume: what to put in it

Drop your master resume in this folder as a PDF. This folder is gitignored;
nothing you put here is committed, even though the repository is public.

## The one rule that makes tailoring work

**The master must be a superset, materially longer than any resume you would
send.** Aim for roughly twice the length of your target document.

If the master and the target are the same length, there is nothing to select
from, and every stage degrades into rephrasing the same content. Selection is
where the value is: deciding that this job wants the data-pipeline work and
not the frontend work is a bigger win than any rewording.

## The second rule, which surprises people

**Every number and technology you ever want to use must appear in the master.**

The guardrails treat the master as a closed whitelist. A figure that is not in
it is rejected as fabricated even when it is true, because the checker has no
way to tell the difference. If you shipped something with a real, quotable
number, put the number in the master.

Numbers are compared as written, so `15+` and `15` are different claims.
Record them in the form you want to use.

## Structure

Mirror the section set the harness emits, so the ledger indexes cleanly:

```
NAME
Title line · phone · location
email · linkedin · github

SUMMARY          One paragraph.
SKILLS           Category labels, each with a comma list. Include everything.
EXPERIENCE       Employer, title, exact dates. Projects nested beneath.
                 Client work only.
PERSONAL PROJECTS  Side projects, with their stack.
EDUCATION        Institution, degree, exact dates.
CERTIFICATIONS   One per line, with issuer and year.
```

Two structural points the guardrails depend on:

- **Keep personal projects out of the employer section.** A side project
  nested under an employer reads as paid work for that employer.
- **Certifications need their own section.** The no-drop check protects
  whatever is listed there, and protects nothing if the section is missing.

## Checklist

- [ ] Every employer, with exact date ranges including months
- [ ] Every project, under the right section
- [ ] Every real metric, written the way you want it to appear
- [ ] Every technology, including ones you use rarely
- [ ] Every certification, language and test score
- [ ] Both spellings where you use them (`TypeScript` and `Typescript`)
- [ ] Roughly twice your target length

## After you add it

Run the `master-ledger` skill. It indexes the PDF and prints how many facts it
found. Check those counts: `titles: 0` means the seniority check is disabled,
and `certifications: 0` means the no-drop check has nothing to protect. Both
point to a structure problem in the PDF rather than a bug.

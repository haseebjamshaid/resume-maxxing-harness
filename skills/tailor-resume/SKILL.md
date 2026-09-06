---
name: tailor-resume
description: Tailors the master resume to a job description and writes a verified markdown resume to output/. Accepts the job description as pasted text, a URL, or a file path (txt, md, pdf, docx). Use when the user wants a resume tailored, targeted or rewritten for a specific role or posting.
argument-hint: "[job description text | url | file path]"
---

# Tailor resume

Selects from the master resume, rewrites for one job description, and refuses
to ship anything it cannot trace back to the master.

Read these before writing a single line:

- `references/truthfulness-rules.md` - the nine rules, verbatim
- `references/output-format.md` - sections, budget, provenance shape
- `references/ai-phrase-blacklist.md` - what never to write
- `references/jd-analysis.md` - the two job-description passes

**The one rule behind all of it:** if a number, technology, date, credential
or outcome is not in the ledger, it does not go in the resume. Not reworded,
not softened, not "reasonably inferred". A claim you cannot source is a claim
the user has to defend in an interview.

## Stage 0 - Normalise the input

`$ARGUMENTS` arrives in whatever form the user had it. Detect which:

| Input | Test | Action |
|---|---|---|
| File | path exists | `./scripts/ingest_jd.sh <path>` |
| URL | starts `http://` or `https://` | `WebFetch`, asking for the full posting text |
| Text | anything else non-empty | use directly |
| Empty | no argument | ask the user to paste the posting |

Job boards block automated fetches routinely. If a URL returns a login wall,
a consent page or near-empty text, **say so and ask for a paste.** Do not
proceed on a fragment: a truncated posting produces confidently mistargeted
tailoring, which is worse than an error.

Then, per `references/jd-analysis.md`, derive the slug and write the posting to
`output/<slug>/jd.md`. Under ~200 characters, stop and ask for the full text.

## Stage 1 - Ledger

Ensure `master_resume/.ledger.md` and `.facts.json` exist and are current by
invoking the `master-ledger` skill. It self-caches, so this is cheap on a
rerun. Everything downstream is meaningless without it.

## Stage 2 - Analyse the posting

Both passes in `references/jd-analysis.md`, in order:

1. `output/<slug>/jd-keywords.json` - requirements and keywords
2. `output/<slug>/skill-targets.json` - the skills the ledger genuinely supports

Pass 2 is a **closed whitelist.** A skill the job wants that the ledger cannot
support does not get written, however good the match would look. That single
constraint is what separates keyword alignment from invention.

## Stage 3 - Select, then write

Selection first, and it is the part that matters. With a superset master, most
of the work is deciding what earns space.

1. Score each ledger project against `jd-keywords.json`.
2. Keep the top 4 employer projects and up to 3 personal projects, inside the
   `references/output-format.md` budget.
3. Retarget the title line, and reorder the SKILLS categories by relevance.
   Both change emphasis without touching a claim, so spend them freely.
4. Rewrite the surviving bullets in the job's terminology **only where the
   ledger already supports the substance**. Reframing `built automated data
   pipelines` as `built ETL pipelines` is right when the ledger shows that
   work. Reframing it as `owned the ETL platform` is not.

Cutting order when it will not fit: personal projects, then the
lowest-relevance employer project, then the weakest bullet in each remaining
project. Never cut a certification. Never compress a date.

Write `output/<slug>/resume.DRAFT.md`, and `output/<slug>/provenance.json`
with a record for every EXPERIENCE and PERSONAL PROJECTS bullet. Copy each
`original` from the ledger character for character; it is checked back against
the ledger, so an invented source fails exactly like an invented claim.

## Stage 4 - Deterministic guardrails

```bash
python3 scripts/lint_resume.py check output/<slug>/resume.DRAFT.md \
  --facts master_resume/.facts.json \
  --provenance output/<slug>/provenance.json \
  --ledger master_resume/.ledger.md \
  --jd-keywords output/<slug>/jd-keywords.json
```

Exit 0 is required to continue. These checks are code and are not negotiable:
argue with a finding only by fixing the draft.

Two findings have a specific meaning worth knowing:

- `fabricated_number` on a **reformatted** figure. The master says `15+` and
  the draft says `15`. That is intended: restating a real figure loosely is
  how a true number becomes a false one. Copy it exactly.
- `note: skill not carried into this version`. Informational, never a failure.
  Selecting from a superset master necessarily leaves skills out.

## Stage 5 - Independent audit

Launch the `resume-verifier` agent. It runs in fresh context and never sees
this reasoning, which is the point: it cannot inherit a rationalisation you
formed while writing. It catches what regex cannot, claim inflation and
invented scope and unsupported causation, and writes
`output/<slug>/verification.md`.

## Stage 6 - Ship, or do not

**Only on `PASS` from both layers**, rename the draft:

```bash
mv output/<slug>/resume.DRAFT.md output/<slug>/resume.md
```

On failure: repair and re-verify, at most **twice**. If violations survive,
leave the file as `resume.DRAFT.md` and tell the user exactly what is still
wrong and which ledger ids are implicated. A draft that cannot be verified is
a real outcome; do not present it as a clean one, and do not quietly relax a
check to get a pass.

Then report: the output path, the ATS score, what you cut and why, the title
line you chose, and any warnings the verifier raised.

Offer the `cover-letter` skill rather than writing one unasked.

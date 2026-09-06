# resume-maxxing-harness

A Claude Code plugin that tailors a resume to a job description and **refuses
to ship anything it cannot trace back to your master resume.**

Your master resume is one structured JSON file. Hand the harness a job
posting in whatever form you have it, and it selects from that master,
rewrites for the role, and gates the result behind five layers of
anti-fabrication checks. If a number, technology or date is not in your
master, it does not reach the output.

The prompts are ported from [Resume-Matcher](https://github.com/srbhr/Resume-Matcher).
The stack is not: that project runs FastAPI, Next.js, SQLite and LiteLLM to
call a model and template a PDF. Claude Code is already the model and already
has file tools, so all of that is redundant here.

## Install

```
/plugin marketplace add haseebjamshaid/resume-maxxing-harness
/plugin install resume-maxxing@resume-maxxing-harness
```

Requires Python 3.10+, plus `pdftotext` (`brew install poppler`) only if you
want to feed it job descriptions as PDFs.

## Use

Create `master_resume/master.json` (copy `master_resume/master.example.json`
and see [`TEMPLATE.md`](master_resume/TEMPLATE.md)), then:

```
/resume-maxxing:tailor-resume https://example.com/careers/senior-data-engineer
/resume-maxxing:tailor-resume ~/Downloads/posting.pdf
/resume-maxxing:tailor-resume <paste the posting text>
```

Any of those work; the skill detects which it got. Results land in
`output/<company>-<role>-<date>/`:

| File | Contents |
|---|---|
| `resume.md` | The tailored resume. Only written on a full pass. |
| `resume.DRAFT.md` | Written instead when verification fails. |
| `verification.md` | Verdict, with a master source id per finding. |
| `provenance.json` | Every bullet's `source_id` in the master. |
| `jd.md`, `jd-keywords.json`, `skill-targets.json` | The parsed posting. |

Then `/resume-maxxing:cover-letter` for a 100-150 word letter under the same
guardrails.

## How the guarantee works

Five layers. Layers 1, 2 and 4 are model-side; **layer 3 is code and cannot be
argued with**; layer 5 decides what ships.

1. **Prevention.** The nine truthfulness rules, verbatim, plus a closed
   whitelist of skills your master actually supports.
2. **Provenance.** Every bullet cites a `source_id` from the master and
   quotes that entry's text. A bullet without a record is invalid by
   construction, and both fields are checked: the id must exist, and the
   quoted text must match what the master holds there. A wrong id fails even
   when the quoted text appears elsewhere, so inventing a plausible-looking
   source fails exactly like inventing the claim.
3. **Deterministic checks.** `scripts/lint_resume.py` compares the output
   against closed whitelists built from your master: every number, technology,
   date range and job title, plus banned phrases and the length budget.
   Anything you park under the master's `needs_review` key is excluded, so a
   claim you flagged as shaky cannot be used until you resolve it.
4. **Independent audit.** A fresh-context subagent that never sees the
   tailoring reasoning, so it cannot inherit the rationalisation behind a bad
   claim. It catches what regex cannot: claim inflation, invented scope,
   unsupported causation.
5. **Fail closed.** Any violation and the output stays a draft. Two repair
   attempts, then it reports what is still wrong rather than shipping.

The whitelists in layer 3 are built by the same code that later enforces them,
so they cannot drift from what they police.

## Your master resume must be a superset

This is the one thing to get right. **Make the master materially longer than
anything you would send**, roughly double.

Same length means nothing to select from, and every stage collapses into
rephrasing. And because layer 3 treats the master as closed, a figure that is
not in it is rejected as fabricated *even when it is true*. If you shipped
something with a real, quotable number, put the number in the master.

See [`master_resume/TEMPLATE.md`](master_resume/TEMPLATE.md).

## Privacy

This repository is public and a resume is not. `master_resume/` and `output/`
are gitignored, along with `*.pdf` and `*.docx` repo-wide as a backstop. The
derived `.facts.json` is ignored too, since it contains verbatim resume
content. Only `TEMPLATE.md` and `master.example.json` are tracked.

Nothing personal is committed. Verify before your first push:

```bash
git status --porcelain -uall
```

## Development

```bash
python3 -m pytest scripts/tests/ -v      # 58 tests over the guardrails
claude plugin validate .claude-plugin/plugin.json
python3 scripts/lint_resume.py facts --master master_resume/master.example.json
```

The deterministic layer is the only real code here and carries the tests. The
suite that matters most is adversarial: inject a fake metric, a technology you
have never used, a stretched date, an inflated title, a stripped provenance
record, a faked source id, and a claim lifted out of `needs_review`, then
confirm each is caught. **A gate that never fails is not a gate.**

## Layout

```
master_resume/master.json  your master resume (gitignored; you author it)
skills/tailor-resume/      entry point, six stages, ported prompts in references/
skills/cover-letter/       100-150 words, same guardrails
agents/resume-verifier.md  fresh-context semantic audit
scripts/lint_resume.py     the deterministic layer
scripts/resume_facts.py    extractors, shared by whitelist and enforcement
scripts/ai_phrases.py      blacklist, ported verbatim
scripts/ingest_jd.sh       job description -> plain text
```

There is no parsing or indexing step: the master is already structured, so
deriving the whitelists is one deterministic script call.

## Credits

Prompts and the ATS scoring formula from
[srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) (Apache 2.0).
This harness is MIT.

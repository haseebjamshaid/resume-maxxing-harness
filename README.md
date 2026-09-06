# resume-maxxing-harness

A Claude Code plugin that tailors a resume to a job description and **refuses
to ship anything it cannot trace back to your master resume.**

Hand it a job posting in whatever form you have it. It selects from your
master, rewrites for the role, and gates the result behind five layers of
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

Requires `pdftotext` (`brew install poppler`) and Python 3.10+.

## Use

Put your master resume PDF in `master_resume/`, then:

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
| `verification.md` | Verdict, with a ledger id per finding. |
| `provenance.json` | Every bullet's source in the master. |
| `jd.md`, `jd-keywords.json`, `skill-targets.json` | The parsed posting. |

Then `/resume-maxxing:cover-letter` for a 100-150 word letter under the same
guardrails.

## How the guarantee works

Five layers. Layers 1, 2 and 4 are model-side; **layer 3 is code and cannot be
argued with**; layer 5 decides what ships.

1. **Prevention.** The nine truthfulness rules, verbatim, plus a closed
   whitelist of skills your master actually supports.
2. **Provenance.** Every bullet carries its source text, copied from the
   ledger. A bullet without one is invalid by construction. The quoted source
   is checked back against the ledger, so inventing a plausible-looking source
   fails exactly like inventing the claim.
3. **Deterministic checks.** `scripts/lint_resume.py` compares the output
   against closed whitelists built from your master: every number, technology,
   date range and job title, plus banned phrases and the length budget.
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
derived `.ledger.md` and `.facts.json` are ignored too, since they contain
verbatim resume content.

Nothing personal is committed. Verify before your first push:

```bash
git status --porcelain -uall
```

## Development

```bash
python3 -m pytest scripts/tests/ -v      # 51 tests over the guardrails
claude plugin validate .claude-plugin/plugin.json
```

The deterministic layer is the only real code here and carries the tests. The
suite that matters most is adversarial: inject a fake metric, a technology you
have never used, a stretched date, an inflated title, a stripped provenance
record, and confirm each is caught. **A gate that never fails is not a gate.**

## Layout

```
skills/tailor-resume/      entry point, six stages, ported prompts in references/
skills/master-ledger/      master PDF -> indexed ledger + fact whitelists (cached)
skills/cover-letter/       100-150 words, same guardrails
agents/resume-verifier.md  fresh-context semantic audit
scripts/lint_resume.py     the deterministic layer
scripts/resume_facts.py    extractors, shared by whitelist and enforcement
scripts/ai_phrases.py      blacklist, ported verbatim
```

## Credits

Prompts and the ATS scoring formula from
[srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) (Apache 2.0).
This harness is MIT.

---
name: cover-letter
description: Writes a short, verified cover letter for a tailored resume in output/. Use when the user asks for a cover letter, an application letter, or a note to accompany a resume. Requires a tailored resume and job description to already exist.
argument-hint: "[output slug, defaults to the most recent]"
---

# Cover letter

Ported from Resume-Matcher's `COVER_LETTER_PROMPT`, under the same guardrails
as the resume. Reads `output/<slug>/resume.md`, `jd.md` and
`master_resume/master.json`.

If no tailored resume exists for the slug, run `tailor-resume` first. Writing a
letter against an unverified resume defeats the point of verifying it.

## The prompt

```
Write a brief cover letter for this job application.

Requirements:
- 100-150 words maximum
- 3-4 short paragraphs
- Opening: Reference ONE specific thing from the job description (product, tech
  stack, or problem they're solving) - not generic excitement about "the role"
- Middle: Pick 1-2 qualifications from resume that DIRECTLY match stated
  requirements, and reframe them in the job's language/terminology where the
  candidate's proven experience supports it (e.g., if the resume shows "built
  automated data pipelines" and the job says "ETL," describe that real work as
  ETL) - prioritize relevance over impressiveness
- Closing: Simple availability to discuss, no desperate enthusiasm
- If resume shows career transition, frame the pivot as intentional and relevant
- Extract company name from job description - do not use placeholders
- Do NOT invent information not in the resume
- Tone: Confident peer, not eager applicant
- Do NOT use em dash ("—") anywhere in the writing/output, even if it exists,
  remove it

Output plain text only. No JSON, no markdown formatting.
```

## What the tone rule actually rules out

*Confident peer, not eager applicant* is the hardest constraint here and the
one most worth getting right. It rules out:

- "I am excited about", "I am passionate about", "I would love the
  opportunity" - all of it
- Thanking them for reading
- Explaining why you want the job instead of what you would do in it
- Superlatives about the company

A peer writes because the problem is interesting and they have done the work
before. Every sentence should survive being read by someone who is busy.

## Guardrails

The 100-150 word cap is a hard limit, not a target. Everything in
`references/../tailor-resume/references/truthfulness-rules.md` applies: no
number, technology, credential or outcome that is not in the master.

A cover letter is the easiest place to fabricate, because prose invites
narrative and there is no bullet structure holding you to a source. Watch
specifically for a claim built from two unrelated master facts, and for
enthusiasm that quietly asserts experience.

Write `output/<slug>/cover-letter.md`, then run the `resume-verifier` agent
against it. It applies the same semantic audit. On `FAIL`, repair and
re-verify at most twice, then report what is still unresolved.

## Related

`OUTREACH_MESSAGE_PROMPT` upstream covers the shorter cold-outreach variant:
70-100 words, opens on a specific detail, one qualification with a concrete
figure, and closes with a low-friction ask ("Worth a quick chat?"). Same
guardrails. Offer it if the user wants a LinkedIn or email approach rather
than a formal letter.

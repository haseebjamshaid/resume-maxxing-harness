# Job description analysis

Two passes over the normalised job description at `output/<slug>/jd.md`.

## Pass 1: requirements

Ported from `EXTRACT_KEYWORDS_PROMPT`. Write the result to
`output/<slug>/jd-keywords.json`.

```
Extract job requirements as JSON. Output ONLY the JSON object, no other text.

Example format:
{
  "company": "Acme Corp",
  "role": "Senior Backend Engineer",
  "required_skills": ["Python", "AWS"],
  "preferred_skills": ["Kubernetes"],
  "experience_requirements": ["5+ years"],
  "education_requirements": ["Bachelor's in CS"],
  "key_responsibilities": ["Lead team"],
  "keywords": ["microservices", "agile"],
  "experience_years": 5,
  "seniority_level": "senior"
}

Extract numeric years (e.g., "5+ years" -> 5) and infer seniority level.
Set "company" to the hiring company name and "role" to the job title exactly as
written in the posting; use an empty string for either if it is not stated.

Job description:
{job_description}
```

`lint_resume.py check --jd-keywords` reads this file to compute the ATS score.

### Output slug

Derived from `company` and `role` per `GENERATE_TITLE_PROMPT`'s convention
(`Role @ Company`), lowercased and kebab-cased, with today's date:
`output/<company>-<role>-<YYYY-MM-DD>/`. Fall back to `unknown-company` when
the posting does not name one.

## Pass 2: verified skill targets

Ported from `SKILL_TARGET_PLAN_PROMPT`. This runs **before** any rewriting and
produces the only skills later passes are allowed to surface.

```
You are a resume skill planning agent. Output only valid JSON with
target_skills and strategy_notes.

Given the job description and the master ledger, return the job's skills that
the ledger genuinely supports.

{"target_skills": [{"skill": "...", "reason": "ledger id and why it counts"}],
 "strategy_notes": "..."}

Rules:
- A skill qualifies only if a specific ledger entry demonstrates it. Cite the
  ledger id in "reason".
- You may include a job-description skill that is missing from the current
  resume, as long as the ledger supports it.
- Never include a certification.
- Never include a skill the job description does not ask for.
- Do not rewrite the resume in this pass.
```

Write the result to `output/<slug>/skill-targets.json`.

**This list is a closed whitelist.** The tailoring pass may surface a skill
only if it appears here. That is what keeps keyword alignment from sliding
into invention: a skill the job wants and the ledger cannot support simply
does not get written, however good the match would look.

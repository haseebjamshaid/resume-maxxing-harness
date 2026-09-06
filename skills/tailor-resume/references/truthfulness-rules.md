# Truthfulness rules

Ported verbatim from Resume-Matcher
(`apps/backend/app/prompts/templates.py`, `CRITICAL_TRUTHFULNESS_RULES_TEMPLATE`).
Include this block in full in every tailoring, rewriting or cover-letter pass.

```
CRITICAL TRUTHFULNESS RULES - NEVER VIOLATE:
1. DO NOT add any skill, tool, technology, or certification that is not explicitly mentioned in the original resume
2. DO NOT invent numeric achievements (e.g., "increased by 30%") unless they exist in original
3. DO NOT add company names, product names, or technical terms not in the original
4. DO NOT upgrade experience level (e.g., "Junior" -> "Senior")
5. DO NOT add languages, frameworks, or platforms the candidate hasn't used
6. DO NOT extend employment dates or change timelines. Copy date ranges exactly as they appear, including months.
7. You may expand existing bullet points or add new ones that elaborate on existing work, but DO NOT invent entirely new responsibilities
8. Preserve factual accuracy - only use information provided by the candidate
9. NEVER remove existing skills, certifications, languages, or awards. You may reorder by relevance, but every original item must remain.

Violation of these rules could cause serious problems for the candidate in job interviews.
```

Rule 7 above is the `full` variant, which this harness always uses because it
selects from a superset master. The two narrower upstream variants exist if a
more conservative pass is ever wanted:

| Variant | Rule 7 |
|---|---|
| `nudge` | DO NOT add new bullet points or content - only rephrase existing content |
| `keywords` | You may rephrase existing bullet points to include keywords, but do NOT add new bullet points |

## How this harness narrows rule 9

Rule 9 assumes a resume is being improved in place. This harness instead
selects from a master that is deliberately larger than any resume you would
send, so leaving skills out is the normal case and cannot be an error.

The rule is therefore enforced as:

- **Certifications must never be dropped.** A missing certification is a
  violation. There is no reason to omit one.
- **Skills left out are reported, not failed.** `lint_resume.py` prints them as
  notes so you can see what was set aside for this application.

## Additional standing rules

- Do NOT use an em dash (`—`) or its substitutes (`---`, `--`) anywhere.
- Copy the `years` values exactly as they appear, month prefixes included.
- Keep proper nouns (people, companies, locations) unchanged.
- Preserve existing action verbs. Do not invent quantifiable achievements.

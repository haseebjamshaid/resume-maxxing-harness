"""Layer 3: deterministic anti-fabrication guardrails.

Compares a tailored resume against the closed whitelists in `.facts.json`,
which `resume_facts.facts_from_text` derives from the master ledger using the
same extractors. No model is involved, so these checks cannot be argued with.

What this layer does NOT do: judge meaning. Claim inflation, implied scope and
unsupported causal claims are Layer 4's job (see agents/resume-verifier.md).

Usage:
    lint_resume.py facts  --ledger PATH [--out PATH]
    lint_resume.py check  RESUME.md --facts PATH [--provenance PATH]
                          [--ledger PATH] [--jd-keywords PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_phrases import (  # noqa: E402
    AI_PHRASE_BLACKLIST,
    AI_PHRASE_REPLACEMENTS,
    WEAK_PHRASES,
)
from resume_facts import (  # noqa: E402
    CANONICAL_HEADINGS,
    Facts,
    NUMBER_RE,
    OPTIONAL_HEADINGS,
    PROVENANCE_SECTIONS,
    DATE_RE,
    extract_bullets,
    extract_headings,
    extract_role_strings,
    extract_section,
    extract_proper_phrases,
    extract_tech_tokens,
    facts_from_dict,
    facts_from_text,
    facts_to_dict,
    load_facts,
    normalise_date,
    normalise_number,
    normalise_text,
    strip_dates,
    _body_after_header,
    _ranks_in,
)

ATS_WEIGHT_KEYWORDS = 0.55
ATS_WEIGHT_SKILLS = 0.25
ATS_WEIGHT_SECTIONS = 0.20

_ATS_SECTIONS: Mapping[str, str] = {
    "summary": r"summary|objective|profile|about",
    "experience": r"experience|work history|employment",
    "education": r"education|academic|degree",
    "skills": r"skills|technologies|competencies|technical",
}

_PUNCTUATION_PHRASES = ("—", "---", "--")


@dataclass(frozen=True)
class Violation:
    kind: str
    location: str
    detail: str
    ledger_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "location": self.location,
            "detail": self.detail,
            "ledger_id": self.ledger_id,
        }


@dataclass(frozen=True)
class Budget:
    total_words: int = 1250
    summary_words: int = 90
    skill_rows: int = 10
    experience_projects: int = 4
    project_bullets: int = 5
    bullet_words: int = 32
    personal_projects: int = 3
    personal_project_bullets: int = 3


@dataclass(frozen=True)
class Report:
    ok: bool
    words: int
    violations: tuple[Violation, ...]
    notes: tuple[str, ...]
    ats: Mapping[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "words": self.words,
            "violations": [v.as_dict() for v in self.violations],
            "notes": list(self.notes),
            "ats": dict(self.ats),
        }


def _whole_word(term: str, text: str) -> bool:
    if not term.strip():
        return False
    return re.search(
        rf"(?<!\w){re.escape(term.strip())}(?!\w)", text, re.IGNORECASE
    ) is not None


def _flexible_phrase(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(p) for p in phrase.split()]
    return re.compile(rf"(?<!\w){r'\s+'.join(parts)}(?!\w)", re.IGNORECASE)


# --------------------------------------------------------------------------
# Individual guardrails
# --------------------------------------------------------------------------

def check_numbers(resume: str, facts: Facts) -> tuple[Violation, ...]:
    """Every numeric claim must appear verbatim in the master."""
    body = strip_dates(_body_after_header(resume))
    seen: set[str] = set()
    out: list[Violation] = []
    for match in NUMBER_RE.finditer(body):
        raw = match.group().strip()
        if not raw:
            continue
        key = normalise_number(raw)
        if key in seen or key in facts.numbers:
            continue
        seen.add(key)
        out.append(
            Violation(
                "fabricated_number",
                "resume body",
                f"{raw!r} does not appear in the master resume",
            )
        )
    return tuple(out)


def check_technologies(resume: str, facts: Facts) -> tuple[Violation, ...]:
    """Every technology and proper noun must be mentioned in the master.

    Multi-word proper nouns are verified as one phrase, and their component
    words are then suppressed so a five-word product name yields one finding.
    """
    phrases = tuple(p for p in extract_proper_phrases(resume)
                    if not facts.mentions(p))
    covered = {w.lower() for p in phrases for w in p.split()}

    out = [
        Violation("fabricated_technology", "resume body", phrase)
        for phrase in phrases
    ]
    out.extend(
        Violation("fabricated_technology", "resume body", token)
        for token in extract_tech_tokens(resume)
        if not facts.mentions(token) and token.lower() not in covered
    )
    return tuple(out)


def check_dates(resume: str, facts: Facts) -> tuple[Violation, ...]:
    """Dates are copied exactly, months included (truthfulness rule 6)."""
    seen: set[str] = set()
    out: list[Violation] = []
    for match in DATE_RE.finditer(resume):
        key = normalise_date(match.group())
        if key in seen or key in facts.date_ranges:
            continue
        seen.add(key)
        out.append(
            Violation(
                "altered_date",
                "resume body",
                f"{match.group().strip()!r} does not match any master date",
            )
        )
    return tuple(out)


def check_seniority(resume: str, facts: Facts) -> tuple[Violation, ...]:
    """No title may outrank the master (truthfulness rule 4)."""
    ceiling = facts.max_seniority
    if ceiling is None:
        return ()
    out: list[Violation] = []
    for role in extract_role_strings(resume):
        ranks = _ranks_in(role)
        if ranks and max(ranks) > ceiling:
            out.append(
                Violation(
                    "seniority_inflation",
                    "title",
                    f"{role!r} outranks the master resume",
                )
            )
    return tuple(out)


def check_provenance(
    resume: str, provenance: Mapping[str, Any], ledger: str
) -> tuple[Violation, ...]:
    """Bullets need a source, and that source must exist in the ledger."""
    records: Sequence[Mapping[str, Any]] = provenance.get("emitted") or ()
    values = {normalise_text(str(r.get("value", ""))) for r in records}
    ledger_norm = normalise_text(ledger)
    out: list[Violation] = []

    for location, text in extract_bullets(resume, PROVENANCE_SECTIONS):
        if normalise_text(text) not in values:
            out.append(
                Violation(
                    "missing_provenance",
                    location,
                    f"no provenance record for {text[:60]!r}",
                )
            )

    for record in records:
        original = normalise_text(str(record.get("original", "")))
        if not original or original not in ledger_norm:
            out.append(
                Violation(
                    "unverifiable_source",
                    str(record.get("path", "unknown")),
                    "provenance 'original' is not present in the master ledger",
                    ledger_id=record.get("ledger_id"),
                )
            )
    return tuple(out)


def check_no_drop(
    resume: str, facts: Facts
) -> tuple[tuple[Violation, ...], tuple[str, ...]]:
    """Certifications must survive; dropped skills are reported, not failed.

    Selecting from a superset master necessarily leaves skills out, so a hard
    no-drop rule on skills would fail every run. Certifications are different:
    there is never a reason to omit one.
    """
    resume_norm = normalise_text(resume)
    violations = tuple(
        Violation("dropped_certification", "CERTIFICATIONS", cert)
        for cert in sorted(facts.certifications)
        if normalise_text(cert) not in resume_norm
    )
    notes = tuple(
        f"skill not carried into this version: {skill}"
        for skill in sorted(facts.skills)
        if not _whole_word(skill, resume)
    )
    return violations, notes


def check_phrases(resume: str) -> tuple[Violation, ...]:
    """AI tells, em dashes, and vague openers."""
    out: list[Violation] = []
    for phrase in sorted(AI_PHRASE_BLACKLIST):
        if phrase in _PUNCTUATION_PHRASES:
            if phrase not in resume:
                continue
        elif not _flexible_phrase(phrase).search(resume):
            continue
        replacement = AI_PHRASE_REPLACEMENTS.get(phrase)
        suggestion = (
            f"use {replacement!r} instead" if replacement
            else "remove it"
        )
        out.append(
            Violation("ai_phrase", "resume body", f"{phrase!r}: {suggestion}")
        )
    for phrase in sorted(WEAK_PHRASES):
        if _flexible_phrase(phrase).search(resume):
            out.append(
                Violation(
                    "weak_phrase",
                    "resume body",
                    f"{phrase!r} is vague; state what you did and its result",
                )
            )
    return tuple(out)


def check_budget(resume: str, budget: Budget) -> tuple[Violation, ...]:
    out: list[Violation] = []
    words = len(resume.split())
    if words > budget.total_words:
        out.append(
            Violation(
                "over_budget",
                "document",
                f"{words} words exceeds the {budget.total_words}-word budget",
            )
        )

    summary_words = len(extract_section(resume, "SUMMARY").split())
    if summary_words > budget.summary_words:
        out.append(
            Violation(
                "over_budget",
                "SUMMARY",
                f"{summary_words} words exceeds {budget.summary_words}",
            )
        )

    for location, text in extract_bullets(resume):
        count = len(text.split())
        if count > budget.bullet_words:
            out.append(
                Violation(
                    "bullet_too_long",
                    location,
                    f"{count} words exceeds {budget.bullet_words}",
                )
            )
    return tuple(out)


def check_headings(resume: str) -> tuple[Violation, ...]:
    found = [h for h in extract_headings(resume) if h in CANONICAL_HEADINGS]
    missing = [
        h for h in CANONICAL_HEADINGS
        if h not in OPTIONAL_HEADINGS and h not in found
    ]
    if missing:
        return (
            Violation(
                "missing_heading",
                "document",
                "missing sections: " + ", ".join(missing),
            ),
        )
    order = [CANONICAL_HEADINGS.index(h) for h in found]
    if order != sorted(order):
        return (
            Violation(
                "heading_order",
                "document",
                "sections are out of order; expected "
                + " then ".join(CANONICAL_HEADINGS),
            ),
        )
    return ()


def compute_ats_score(
    resume: str, jd_keywords: Mapping[str, Any]
) -> dict[str, float]:
    """Ported from Resume-Matcher's compute_ats_score. Reported, not gating."""
    required = [
        *jd_keywords.get("required_skills", ()),
        *jd_keywords.get("preferred_skills", ()),
    ]
    keywords = [*required, *jd_keywords.get("keywords", ())]

    def coverage(terms: Iterable[str]) -> float:
        unique = {t.strip() for t in terms if t and t.strip()}
        if not unique:
            return 0.0
        hits = sum(1 for t in unique if _whole_word(t, resume))
        return hits / len(unique) * 100.0

    keyword_match = coverage(keywords)
    skills_coverage = coverage(required)
    present = sum(
        1
        for pattern in _ATS_SECTIONS.values()
        if re.search(rf"(?<!\w)(?:{pattern})(?!\w)", resume, re.IGNORECASE)
    )
    section_completeness = present / len(_ATS_SECTIONS) * 100.0

    return {
        "keyword_match": keyword_match,
        "skills_coverage": skills_coverage,
        "section_completeness": section_completeness,
        "score": (
            keyword_match * ATS_WEIGHT_KEYWORDS
            + skills_coverage * ATS_WEIGHT_SKILLS
            + section_completeness * ATS_WEIGHT_SECTIONS
        ),
    }


def lint(
    resume: str,
    facts: Facts,
    provenance: Mapping[str, Any],
    ledger: str,
    jd_keywords: Mapping[str, Any],
    budget: Budget,
) -> Report:
    no_drop_violations, notes = check_no_drop(resume, facts)
    violations = (
        check_numbers(resume, facts)
        + check_technologies(resume, facts)
        + check_dates(resume, facts)
        + check_seniority(resume, facts)
        + check_provenance(resume, provenance, ledger)
        + no_drop_violations
        + check_phrases(resume)
        + check_budget(resume, budget)
        + check_headings(resume)
    )
    return Report(
        ok=not violations,
        words=len(resume.split()),
        violations=violations,
        notes=notes,
        ats=compute_ats_score(resume, jd_keywords),
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _read(path: str | Path | None, label: str) -> str:
    if path is None:
        return ""
    target = Path(path)
    if not target.is_file():
        raise SystemExit(f"error: {label} not found: {target}")
    return target.read_text(encoding="utf-8")


def _read_json(path: str | Path | None, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    text = _read(path, label)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {label} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"error: {label} must contain a JSON object")
    return payload


def _render(report: Report) -> str:
    lines: list[str] = []
    status = "PASS" if report.ok else "FAIL"
    lines.append(f"{status}  ({report.words} words)")
    ats = report.ats
    lines.append(
        "ATS  score={score:.1f}  keywords={keyword_match:.1f}"
        "  skills={skills_coverage:.1f}"
        "  sections={section_completeness:.1f}".format(**ats)
    )
    if report.violations:
        lines.append("")
        lines.append(f"{len(report.violations)} violation(s):")
        for v in report.violations:
            suffix = f"  [{v.ledger_id}]" if v.ledger_id else ""
            lines.append(f"  - {v.kind} @ {v.location}: {v.detail}{suffix}")
    for note in report.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


def _cmd_facts(args: argparse.Namespace) -> int:
    facts = facts_from_text(_read(args.ledger, "ledger"))
    payload = json.dumps(facts_to_dict(facts), indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        counts = {k: len(v) for k, v in facts_to_dict(facts).items()}
        print(f"wrote {args.out}: {counts}")
    else:
        print(payload)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    budget = Budget()
    if args.total_words:
        budget = replace(budget, total_words=args.total_words)
    report = lint(
        resume=_read(args.resume, "resume"),
        facts=load_facts(args.facts),
        provenance=_read_json(args.provenance, "provenance"),
        ledger=_read(args.ledger, "ledger"),
        jd_keywords=_read_json(args.jd_keywords, "jd keywords"),
        budget=budget,
    )
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(_render(report))
    return 0 if report.ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    facts_cmd = sub.add_parser("facts", help="build .facts.json from a ledger")
    facts_cmd.add_argument("--ledger", required=True)
    facts_cmd.add_argument("--out")
    facts_cmd.set_defaults(func=_cmd_facts)

    check = sub.add_parser("check", help="run the guardrails on a resume")
    check.add_argument("resume")
    check.add_argument("--facts", required=True)
    check.add_argument("--provenance")
    check.add_argument("--ledger")
    check.add_argument("--jd-keywords", dest="jd_keywords")
    check.add_argument("--total-words", type=int)
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

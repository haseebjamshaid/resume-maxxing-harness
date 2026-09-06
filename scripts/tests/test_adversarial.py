"""Adversarial tests: the guardrails must actually fire.

A gate that never fails is not a gate. Each case injects one realistic
fabrication into an otherwise clean resume and asserts the matching guardrail
catches it and that the report fails closed.

Fixtures are synthetic. No real resume content appears here.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lint_resume as lr  # noqa: E402
from resume_facts import facts_from_text  # noqa: E402

LEDGER = """\
# ACME CANDIDATE
Senior Data Engineer · +00 000 0000000 · Test City
candidate@example.com · linkedin.com/in/example · github.com/example

## SUMMARY
[sum.1] Data engineer with 4 years building pipelines.

## SKILLS
[skills.data] ClickHouse, MySQL, DLT, Prefect

## EXPERIENCE
### Acme Corp | Senior Data Engineer | June 2022 - Present
[exp.acme.scope] Own the data platform end to end.

#### Analytics ELT Platform *(Data Engineer, 2025 - present)*
- [exp.acme.p1.b1] Owned the transformation layer across 15+ data domains on ClickHouse.
- [exp.acme.p1.b2] Implemented CDC merge loading from MySQL using DLT, covered by 19 pytest suites.

## EDUCATION
### Test University | BSc Engineering | 2018 - 2022
[edu.1] Test City.

## CERTIFICATIONS
- IELTS 8.5
"""

CLEAN_RESUME = """\
# ACME CANDIDATE
Senior Data Engineer · +00 000 0000000 · Test City
candidate@example.com · linkedin.com/in/example · github.com/example

## SUMMARY
Data engineer with 4 years building pipelines.

## SKILLS
**Data** ClickHouse, MySQL, DLT, Prefect

## EXPERIENCE
### Acme Corp | Senior Data Engineer | June 2022 - Present
Own the data platform end to end.

#### Analytics ELT Platform *(Data Engineer, 2025 - present)*
- **Owned the transformation layer across 15+ data domains** on ClickHouse.
- **Implemented CDC merge loading from MySQL using DLT** covered by 19 pytest suites.

## EDUCATION
### Test University | BSc Engineering | 2018 - 2022
Test City.

## CERTIFICATIONS
- IELTS 8.5
"""

CLEAN_PROVENANCE = {
    "emitted": [
        {
            "path": "EXPERIENCE.acme.p1.b1",
            "ledger_id": "exp.acme.p1.b1",
            "original": "Owned the transformation layer across 15+ data "
                        "domains on ClickHouse.",
            "value": "**Owned the transformation layer across 15+ data "
                     "domains** on ClickHouse.",
            "reason": "job description names the transformation layer",
        },
        {
            "path": "EXPERIENCE.acme.p1.b2",
            "ledger_id": "exp.acme.p1.b2",
            "original": "Implemented CDC merge loading from MySQL using DLT, "
                        "covered by 19 pytest suites.",
            "value": "**Implemented CDC merge loading from MySQL using DLT** "
                     "covered by 19 pytest suites.",
            "reason": "job description names CDC",
        },
    ]
}


@pytest.fixture
def facts():
    return facts_from_text(LEDGER)


def _lint(resume: str, facts, provenance=None) -> lr.Report:
    return lr.lint(
        resume=resume,
        facts=facts,
        provenance=CLEAN_PROVENANCE if provenance is None else provenance,
        ledger=LEDGER,
        jd_keywords={},
        budget=lr.Budget(),
    )


def test_baseline_clean_resume_passes(facts) -> None:
    """Without a clean baseline the injections below prove nothing."""
    report = _lint(CLEAN_RESUME, facts)
    assert report.violations == (), [v.as_dict() for v in report.violations]
    assert report.ok is True


# --------------------------------------------------------------------------
# One injection per guardrail
# --------------------------------------------------------------------------

def test_catches_fabricated_metric(facts) -> None:
    resume = CLEAN_RESUME.replace(
        "on ClickHouse.", "on ClickHouse, cutting query latency by 45%."
    )
    report = _lint(resume, facts)
    assert "fabricated_number" in {v.kind for v in report.violations}
    assert any("45%" in v.detail for v in report.violations)
    assert report.ok is False


def test_catches_technology_never_used(facts) -> None:
    resume = CLEAN_RESUME.replace(
        "covered by 19 pytest suites.",
        "covered by 19 pytest suites, rewritten in Rust.",
    )
    report = _lint(resume, facts)
    assert "fabricated_technology" in {v.kind for v in report.violations}
    assert any("Rust" in v.detail for v in report.violations)
    assert report.ok is False


def test_catches_stretched_employment_date(facts) -> None:
    resume = CLEAN_RESUME.replace("June 2022 - Present", "June 2021 - Present")
    report = _lint(resume, facts)
    assert "altered_date" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_dropped_month_from_date(facts) -> None:
    resume = CLEAN_RESUME.replace("June 2022 - Present", "2022 - Present")
    report = _lint(resume, facts)
    assert "altered_date" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_title_inflation(facts) -> None:
    resume = CLEAN_RESUME.replace(
        "Senior Data Engineer · +00", "Lead Data Engineer · +00"
    )
    report = _lint(resume, facts)
    assert "seniority_inflation" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_bullet_with_provenance_stripped(facts) -> None:
    report = _lint(CLEAN_RESUME, facts, provenance={"emitted": []})
    kinds = [v.kind for v in report.violations]
    assert kinds.count("missing_provenance") == 2
    assert report.ok is False


def test_catches_invented_provenance_source(facts) -> None:
    """A fabricated bullet cannot be laundered with a plausible source."""
    provenance = copy.deepcopy(CLEAN_PROVENANCE)
    provenance["emitted"][0]["original"] = (
        "Rearchitected the platform, cutting cost by 30%."
    )
    report = _lint(CLEAN_RESUME, facts, provenance=provenance)
    assert "unverifiable_source" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_dropped_certification(facts) -> None:
    resume = CLEAN_RESUME.replace("- IELTS 8.5", "")
    report = _lint(resume, facts)
    assert "dropped_certification" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_ai_phrase(facts) -> None:
    resume = CLEAN_RESUME.replace("**Owned the", "**Spearheaded the")
    report = _lint(resume, facts)
    assert "ai_phrase" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_em_dash(facts) -> None:
    resume = CLEAN_RESUME.replace("on ClickHouse.", "on ClickHouse — quickly.")
    report = _lint(resume, facts)
    assert any(
        v.kind == "ai_phrase" and "—" in v.detail for v in report.violations
    )
    assert report.ok is False


def test_catches_removed_section(facts) -> None:
    resume = CLEAN_RESUME.replace("## CERTIFICATIONS", "## EXTRAS")
    report = _lint(resume, facts)
    assert "missing_heading" in {v.kind for v in report.violations}
    assert report.ok is False


def test_reformatted_figure_is_not_silently_accepted(facts) -> None:
    """The master says '15+'. Restating it as '15' is a different claim."""
    resume = CLEAN_RESUME.replace("15+ data domains", "15 data domains")
    report = _lint(resume, facts)
    assert "fabricated_number" in {v.kind for v in report.violations}
    assert report.ok is False


def test_ledger_yields_usable_whitelists(facts) -> None:
    """A ledger that indexes to empty whitelists disables the guardrails."""
    assert facts.titles, "no titles: the seniority ceiling would be disabled"
    assert facts.certifications, "no certifications: no-drop protects nothing"
    assert {"ClickHouse", "MySQL", "DLT"} <= facts.technologies
    assert {"15+", "19", "8.5"} <= facts.numbers
    assert "june 2022-present" in facts.date_ranges

"""Tests for the deterministic guardrail layer (Layer 3).

Each test targets one guardrail and must fail if that guardrail breaks.
Structure: Arrange - Act - Assert.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lint_resume as lr  # noqa: E402

# --------------------------------------------------------------------------
# Fixtures: a tiny synthetic master. No real resume content.
# --------------------------------------------------------------------------

LEDGER = """
# ACME CANDIDATE
Senior Data Engineer

## EXPERIENCE
### Acme Corp | Senior Data Engineer | June 2022 - Present
- exp.acme.p1.b1 :: Owned the transformation layer across 15+ data domains on ClickHouse.
- exp.acme.p1.b2 :: Implemented CDC merge loading from MySQL using DLT, covered by 19 pytest suites.

## EDUCATION
### Test University | 2018 - 2022

## CERTIFICATIONS
- IELTS 8.5
"""

FACTS = {
    "numbers": ["15+", "19", "8.5", "~16 GB"],
    "technologies": ["ClickHouse", "MySQL", "DLT", "CDC", "pytest", "IELTS"],
    "date_ranges": ["June 2022 - Present", "2018 - 2022"],
    "titles": ["Senior Data Engineer"],
    "skills": ["ClickHouse", "MySQL", "DLT"],
    "certifications": ["IELTS 8.5"],
}


@pytest.fixture
def facts() -> lr.Facts:
    return lr.facts_from_dict(FACTS)


def _provenance(*pairs: tuple[str, str, str]) -> dict:
    return {
        "emitted": [
            {"path": path, "ledger_id": lid, "original": original, "value": value}
            for path, lid, original, value in
            [(p, l, o, v) for p, l, o, v in pairs]
        ]
    }


# --------------------------------------------------------------------------
# Number whitelist
# --------------------------------------------------------------------------

def test_flags_number_absent_from_master(facts: lr.Facts) -> None:
    # Arrange: 45% appears nowhere in the master
    resume = "- Cut query latency by 45% on ClickHouse."

    # Act
    violations = lr.check_numbers(resume, facts)

    # Assert
    assert [v.kind for v in violations] == ["fabricated_number"]
    assert "45%" in violations[0].detail


def test_accepts_number_present_in_master(facts: lr.Facts) -> None:
    resume = "- Owned transformation across 15+ data domains."
    assert lr.check_numbers(resume, facts) == ()


def test_reformatted_number_is_rejected(facts: lr.Facts) -> None:
    """Master says '15+'. Restating it as bare '15' is a different claim."""
    resume = "- Owned transformation across 15 data domains."
    violations = lr.check_numbers(resume, facts)
    assert [v.kind for v in violations] == ["fabricated_number"]


def test_whitespace_in_number_is_tolerated(facts: lr.Facts) -> None:
    """'~16 GB' and '~16GB' are the same claim, only formatted differently."""
    resume = "- Kept the model resident within a ~16GB budget."
    assert lr.check_numbers(resume, facts) == ()


def test_dates_do_not_leak_into_the_number_scan(facts: lr.Facts) -> None:
    """Year digits belong to the date check, not the number check."""
    resume = "### Acme Corp | Senior Data Engineer | June 2022 - Present"
    assert lr.check_numbers(resume, facts) == ()


# --------------------------------------------------------------------------
# Technology whitelist
# --------------------------------------------------------------------------

def test_flags_technology_absent_from_master(facts: lr.Facts) -> None:
    resume = "- Rebuilt the ingest path in Rust with Terraform provisioning."
    violations = lr.check_technologies(resume, facts)
    flagged = {v.detail for v in violations}
    assert "Rust" in flagged and "Terraform" in flagged


def test_accepts_technology_present_in_master(facts: lr.Facts) -> None:
    resume = "- Implemented CDC merge loading from MySQL using DLT on ClickHouse."
    assert lr.check_technologies(resume, facts) == ()


def test_ordinary_capitalised_words_are_not_technologies(facts: lr.Facts) -> None:
    """Sentence-case verbs must not be mistaken for tech tokens."""
    resume = "- Owned and Implemented the layer. Built it. Delivered on time."
    assert lr.check_technologies(resume, facts) == ()


def test_section_headings_are_not_technologies(facts: lr.Facts) -> None:
    resume = "## SUMMARY\n## SKILLS\n## EXPERIENCE\n## EDUCATION\n## CERTIFICATIONS"
    assert lr.check_technologies(resume, facts) == ()


# --------------------------------------------------------------------------
# Date exactness
# --------------------------------------------------------------------------

def test_flags_stretched_employment_date(facts: lr.Facts) -> None:
    resume = "### Acme Corp | Senior Data Engineer | June 2021 - Present"
    violations = lr.check_dates(resume, facts)
    assert [v.kind for v in violations] == ["altered_date"]


def test_accepts_exact_date_range(facts: lr.Facts) -> None:
    resume = "### Acme Corp | June 2022 - Present\n### Test University | 2018 - 2022"
    assert lr.check_dates(resume, facts) == ()


def test_flags_dropped_month(facts: lr.Facts) -> None:
    """Rule 6: months must survive. '2022 - Present' is not 'June 2022 - Present'."""
    resume = "### Acme Corp | 2022 - Present"
    assert [v.kind for v in lr.check_dates(resume, facts)] == ["altered_date"]


# --------------------------------------------------------------------------
# Seniority ceiling
# --------------------------------------------------------------------------

def test_flags_title_inflation(facts: lr.Facts) -> None:
    resume = "# ACME CANDIDATE\nLead Data Engineer\n"
    violations = lr.check_seniority(resume, facts)
    assert [v.kind for v in violations] == ["seniority_inflation"]


def test_accepts_title_at_master_level(facts: lr.Facts) -> None:
    resume = "# ACME CANDIDATE\nSenior Data Engineer\n"
    assert lr.check_seniority(resume, facts) == ()


def test_verb_lead_in_prose_is_not_title_inflation(facts: lr.Facts) -> None:
    """'lead technical hiring' in a bullet is a verb, not a job title."""
    resume = "# ACME CANDIDATE\nSenior Data Engineer\n\n- Mentor engineers and lead technical hiring."
    assert lr.check_seniority(resume, facts) == ()


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

def test_flags_bullet_with_no_provenance_record() -> None:
    resume = "- Owned the transformation layer across 15+ data domains on ClickHouse."
    violations = lr.check_provenance(resume, {"emitted": []}, LEDGER)
    assert [v.kind for v in violations] == ["missing_provenance"]


def test_flags_provenance_whose_original_is_absent_from_ledger() -> None:
    """A fabricated bullet cannot be laundered by inventing a plausible source."""
    resume = "- Cut cloud spend by 30% through rightsizing."
    provenance = _provenance(
        (
            "EXPERIENCE.acme.p1.b9",
            "exp.acme.p1.b9",
            "Reduced infrastructure cost via rightsizing.",  # not in LEDGER
            "Cut cloud spend by 30% through rightsizing.",
        )
    )
    violations = lr.check_provenance(resume, provenance, LEDGER)
    assert [v.kind for v in violations] == ["unverifiable_source"]


def test_accepts_bullet_with_verifiable_provenance() -> None:
    resume = "- Owned the transformation layer across 15+ data domains."
    provenance = _provenance(
        (
            "EXPERIENCE.acme.p1.b1",
            "exp.acme.p1.b1",
            "Owned the transformation layer across 15+ data domains on ClickHouse.",
            "Owned the transformation layer across 15+ data domains.",
        )
    )
    assert lr.check_provenance(resume, provenance, LEDGER) == ()


# --------------------------------------------------------------------------
# Certifications must not be dropped
# --------------------------------------------------------------------------

def test_flags_dropped_certification(facts: lr.Facts) -> None:
    resume = "## CERTIFICATIONS\n(none)"
    violations, _ = lr.check_no_drop(resume, facts)
    assert [v.kind for v in violations] == ["dropped_certification"]


def test_dropped_skill_is_a_note_not_a_violation(facts: lr.Facts) -> None:
    """Selecting from a superset master must drop skills; that is not an error."""
    resume = "## SKILLS\n**Data** ClickHouse\n## CERTIFICATIONS\n- IELTS 8.5"
    violations, notes = lr.check_no_drop(resume, facts)
    assert violations == ()
    assert any("MySQL" in n for n in notes)


# --------------------------------------------------------------------------
# AI phrases and punctuation
# --------------------------------------------------------------------------

def test_flags_blacklisted_phrase_with_replacement() -> None:
    resume = "- Spearheaded the migration."
    violations = lr.check_phrases(resume)
    assert [v.kind for v in violations] == ["ai_phrase"]
    assert "led" in violations[0].detail


def test_flags_em_dash_and_double_hyphen() -> None:
    resume = "- Built the thing — quickly -- and well."
    kinds = {v.kind for v in lr.check_phrases(resume)}
    assert kinds == {"ai_phrase"}
    assert len(lr.check_phrases(resume)) >= 2


def test_flags_weak_opener() -> None:
    resume = "- Responsible for the data platform."
    assert [v.kind for v in lr.check_phrases(resume)] == ["weak_phrase"]


def test_blacklisted_phrase_without_replacement_does_not_crash() -> None:
    """'disruptor' is blacklisted but has no upstream replacement."""
    violations = lr.check_phrases("- Became a disruptor.")
    assert [v.kind for v in violations] == ["ai_phrase"]


def test_clean_text_produces_no_phrase_violations() -> None:
    assert lr.check_phrases("- Led the migration and used DLT.") == ()


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------

def test_flags_word_budget_overflow() -> None:
    resume = " ".join(["word"] * 1300)
    budget = lr.Budget(total_words=1250)
    assert [v.kind for v in lr.check_budget(resume, budget)] == ["over_budget"]


def test_accepts_resume_within_budget() -> None:
    assert lr.check_budget(" ".join(["word"] * 100), lr.Budget()) == ()


def test_flags_overlong_bullet() -> None:
    resume = "- " + " ".join(["word"] * 40)
    kinds = [v.kind for v in lr.check_budget(resume, lr.Budget(bullet_words=32))]
    assert "bullet_too_long" in kinds


# --------------------------------------------------------------------------
# Headings
# --------------------------------------------------------------------------

def test_flags_missing_heading() -> None:
    resume = "## SUMMARY\n## SKILLS\n## EXPERIENCE\n## EDUCATION"
    violations = lr.check_headings(resume)
    assert [v.kind for v in violations] == ["missing_heading"]
    assert "CERTIFICATIONS" in violations[0].detail


def test_flags_out_of_order_headings() -> None:
    resume = ("## SKILLS\n## SUMMARY\n## EXPERIENCE\n"
              "## PERSONAL PROJECTS\n## EDUCATION\n## CERTIFICATIONS")
    assert [v.kind for v in lr.check_headings(resume)] == ["heading_order"]


def test_accepts_canonical_headings() -> None:
    resume = ("## SUMMARY\n## SKILLS\n## EXPERIENCE\n"
              "## PERSONAL PROJECTS\n## EDUCATION\n## CERTIFICATIONS")
    assert lr.check_headings(resume) == ()


def test_personal_projects_is_optional() -> None:
    """The section is droppable when space is tight."""
    resume = "## SUMMARY\n## SKILLS\n## EXPERIENCE\n## EDUCATION\n## CERTIFICATIONS"
    assert lr.check_headings(resume) == ()


# --------------------------------------------------------------------------
# ATS score
# --------------------------------------------------------------------------

def test_ats_whole_word_matching_does_not_match_substrings() -> None:
    """'Go' must not be satisfied by 'Golang'."""
    ats = lr.compute_ats_score("We use Golang here.", {"required_skills": ["Go"]})
    assert ats["skills_coverage"] == 0.0


def test_ats_weights_sum_as_upstream() -> None:
    """keyword_match*0.55 + skills_coverage*0.25 + section_completeness*0.20"""
    resume = ("## SUMMARY\ns\n## EXPERIENCE\ne\n## EDUCATION\nd\n"
              "## SKILLS\nClickHouse, MySQL\n")
    ats = lr.compute_ats_score(resume, {"required_skills": ["ClickHouse", "MySQL"]})
    expected = (ats["keyword_match"] * 0.55
                + ats["skills_coverage"] * 0.25
                + ats["section_completeness"] * 0.20)
    assert ats["score"] == pytest.approx(expected)
    assert ats["skills_coverage"] == pytest.approx(100.0)
    assert ats["section_completeness"] == pytest.approx(100.0)


def test_ats_empty_keywords_scores_zero_not_full() -> None:
    """Upstream deliberately returns 0.0, not 100, when the JD yields nothing."""
    ats = lr.compute_ats_score("anything", {})
    assert ats["keyword_match"] == 0.0


# --------------------------------------------------------------------------
# End-to-end report
# --------------------------------------------------------------------------

def test_lint_fails_closed_on_any_violation(facts: lr.Facts) -> None:
    resume = "- Cut latency by 45% using Rust."
    report = lr.lint(resume, facts, {"emitted": []}, LEDGER, {}, lr.Budget())
    assert report.ok is False
    assert len(report.violations) > 0


def test_lint_passes_a_clean_resume(facts: lr.Facts) -> None:
    resume = (
        "# ACME CANDIDATE\nSenior Data Engineer\n\n"
        "## SUMMARY\nData engineer.\n\n"
        "## SKILLS\n**Data** ClickHouse, MySQL, DLT\n\n"
        "## EXPERIENCE\n### Acme Corp | June 2022 - Present\n"
        "- Owned the transformation layer across 15+ data domains.\n\n"
        "## EDUCATION\n### Test University | 2018 - 2022\n\n"
        "## CERTIFICATIONS\n- IELTS 8.5\n"
    )
    provenance = _provenance(
        (
            "EXPERIENCE.acme.p1.b1",
            "exp.acme.p1.b1",
            "Owned the transformation layer across 15+ data domains on ClickHouse.",
            "Owned the transformation layer across 15+ data domains.",
        )
    )
    report = lr.lint(resume, facts, provenance, LEDGER, {}, lr.Budget())
    assert report.violations == ()
    assert report.ok is True

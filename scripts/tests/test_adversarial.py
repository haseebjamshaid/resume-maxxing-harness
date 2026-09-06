"""Adversarial tests: the guardrails must actually fire.

A gate that never fails is not a gate. Each case injects one realistic
fabrication into an otherwise clean resume and asserts the matching guardrail
catches it and that the report fails closed.

Fixtures come from conftest.py and are synthetic.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lint_resume as lr  # noqa: E402
from conftest import CLEAN_PROVENANCE, CLEAN_RESUME, MASTER  # noqa: E402
from resume_facts import validate_master  # noqa: E402


def _lint(resume, facts, master_index, provenance=None) -> lr.Report:
    return lr.lint(
        resume=resume,
        facts=facts,
        provenance=CLEAN_PROVENANCE if provenance is None else provenance,
        master_index=master_index,
        jd_keywords={},
        budget=lr.Budget(),
    )


def test_baseline_clean_resume_passes(facts, master_index) -> None:
    """Without a clean baseline the injections below prove nothing."""
    report = _lint(CLEAN_RESUME, facts, master_index)
    assert report.violations == (), [v.as_dict() for v in report.violations]
    assert report.ok is True


# --------------------------------------------------------------------------
# Fabricated content
# --------------------------------------------------------------------------

def test_catches_fabricated_metric(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace(
        "on ClickHouse.", "on ClickHouse, cutting query latency by 45%."
    )
    report = _lint(resume, facts, master_index)
    assert "fabricated_number" in {v.kind for v in report.violations}
    assert any("45%" in v.detail for v in report.violations)
    assert report.ok is False


def test_catches_technology_never_used(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace(
        "covered by 19 pytest suites.",
        "covered by 19 pytest suites, rewritten in Rust.",
    )
    report = _lint(resume, facts, master_index)
    assert "fabricated_technology" in {v.kind for v in report.violations}
    assert any("Rust" in v.detail for v in report.violations)
    assert report.ok is False


def test_reformatted_figure_is_not_silently_accepted(facts, master_index) -> None:
    """The master says '15+'. Restating it as '15' is a different claim."""
    resume = CLEAN_RESUME.replace("15+ data domains", "15 data domains")
    report = _lint(resume, facts, master_index)
    assert "fabricated_number" in {v.kind for v in report.violations}
    assert report.ok is False


# --------------------------------------------------------------------------
# Dates, titles, sections
# --------------------------------------------------------------------------

def test_catches_stretched_employment_date(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("June 2022 - Present", "June 2021 - Present")
    report = _lint(resume, facts, master_index)
    assert "altered_date" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_dropped_month_from_date(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("June 2022 - Present", "2022 - Present")
    report = _lint(resume, facts, master_index)
    assert "altered_date" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_title_inflation(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace(
        "Senior Data Engineer · +00", "Lead Data Engineer · +00"
    )
    report = _lint(resume, facts, master_index)
    assert "seniority_inflation" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_dropped_certification(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("- IELTS 8.5", "")
    report = _lint(resume, facts, master_index)
    assert "dropped_certification" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_removed_section(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("## CERTIFICATIONS", "## EXTRAS")
    report = _lint(resume, facts, master_index)
    assert "missing_heading" in {v.kind for v in report.violations}
    assert report.ok is False


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------

def test_catches_bullet_with_provenance_stripped(facts, master_index) -> None:
    report = _lint(CLEAN_RESUME, facts, master_index, provenance={"emitted": []})
    kinds = [v.kind for v in report.violations]
    assert kinds.count("missing_provenance") == 2
    assert report.ok is False


def test_catches_invented_source_id(facts, master_index) -> None:
    provenance = copy.deepcopy(CLEAN_PROVENANCE)
    provenance["emitted"][0]["source_id"] = "exp.acme.p9.b9"
    report = _lint(CLEAN_RESUME, facts, master_index, provenance=provenance)
    assert "unverifiable_source" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_source_text_that_does_not_match_the_master(
    facts, master_index
) -> None:
    """A real id paired with invented source text still fails."""
    provenance = copy.deepcopy(CLEAN_PROVENANCE)
    provenance["emitted"][0]["original"] = (
        "Rearchitected the platform, cutting cost by 30%."
    )
    report = _lint(CLEAN_RESUME, facts, master_index, provenance=provenance)
    assert any(
        v.kind == "unverifiable_source" and "does not match" in v.detail
        for v in report.violations
    )
    assert report.ok is False


# --------------------------------------------------------------------------
# Quarantine: disputed claims must stay unusable
# --------------------------------------------------------------------------

def test_needs_review_claims_are_not_whitelisted(facts) -> None:
    """`needs_review` holds disputed claims. Its text must not become usable.

    Otherwise flagging a claim as disputed would be the very thing that
    licenses the tailorer to use it.
    """
    assert "30%" not in facts.numbers
    assert "9" not in facts.numbers
    assert "Terraform" not in facts.technologies
    assert "terraform" not in facts.corpus


def test_a_disputed_claim_is_caught_when_used(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace(
        "on ClickHouse.",
        "on ClickHouse, cutting cost by 30% across 9 regions using Terraform.",
    )
    report = _lint(resume, facts, master_index)
    kinds = {v.kind for v in report.violations}
    assert "fabricated_number" in kinds
    assert "fabricated_technology" in kinds
    assert report.ok is False


# --------------------------------------------------------------------------
# Phrases
# --------------------------------------------------------------------------

def test_catches_ai_phrase(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("**Owned the", "**Spearheaded the")
    report = _lint(resume, facts, master_index)
    assert "ai_phrase" in {v.kind for v in report.violations}
    assert report.ok is False


def test_catches_em_dash(facts, master_index) -> None:
    resume = CLEAN_RESUME.replace("on ClickHouse.", "on ClickHouse — quickly.")
    report = _lint(resume, facts, master_index)
    assert any(
        v.kind == "ai_phrase" and "—" in v.detail for v in report.violations
    )
    assert report.ok is False


# --------------------------------------------------------------------------
# The master itself
# --------------------------------------------------------------------------

def test_master_yields_usable_whitelists(facts) -> None:
    """A master that indexes to empty whitelists disables the guardrails."""
    assert facts.titles, "no titles: the seniority ceiling would be disabled"
    assert facts.certifications, "no certifications: no-drop protects nothing"
    assert {"ClickHouse", "MySQL", "DLT"} <= facts.technologies
    assert {"15+", "19"} <= facts.numbers
    assert "june 2022-present" in facts.date_ranges


def test_validate_master_accepts_a_well_formed_master(master) -> None:
    assert validate_master(master) == ()


def test_validate_master_flags_a_disabled_guardrail() -> None:
    broken = copy.deepcopy(MASTER)
    broken["certifications"] = []
    problems = validate_master(broken)
    assert any("no-drop" in p for p in problems)


def test_validate_master_flags_duplicate_ids() -> None:
    """Duplicate ids make provenance ambiguous."""
    broken = copy.deepcopy(MASTER)
    bullets = broken["experience"][0]["projects"][0]["bullets"]
    bullets[1]["id"] = bullets[0]["id"]
    problems = validate_master(broken)
    assert any("duplicate id" in p for p in problems)

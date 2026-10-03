"""Years of experience are derived from dates, never stored as a figure.

A stored "4+ years" goes stale every June and invites two sources to disagree.
The master instead says `{years_experience}`, and the tooling fills it in from
the earliest employer start date before any whitelist is built.
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lint_resume as lr  # noqa: E402
import resume_facts as rf  # noqa: E402

from conftest import MASTER  # noqa: E402

TODAY = date(2026, 9, 19)


def _master_with(summary: str, *employer_dates: str) -> dict:
    base = copy.deepcopy(MASTER)
    template = base["experience"][0]
    employers = [
        {**copy.deepcopy(template), "id": f"exp.e{n}", "dates": dates}
        for n, dates in enumerate(employer_dates or (template["dates"],))
    ]
    return {
        **base,
        "summary_variants": [{"id": "sum.1", "text": summary}],
        "experience": employers,
    }


# --------------------------------------------------------------------------
# Derivation
# --------------------------------------------------------------------------

def test_counts_whole_years_from_the_start_month() -> None:
    master = _master_with("x", "June 2022 - Present")
    assert rf.derive_years_experience(master, TODAY) == 4


def test_does_not_round_up_before_the_anniversary_month() -> None:
    master = _master_with("x", "June 2022 - Present")
    assert rf.derive_years_experience(master, date(2026, 5, 31)) == 3


def test_counts_the_anniversary_month_as_a_full_year() -> None:
    master = _master_with("x", "June 2022 - Present")
    assert rf.derive_years_experience(master, date(2026, 6, 1)) == 4


def test_year_only_start_is_read_as_december_so_it_never_overstates() -> None:
    master = _master_with("x", "2020 - Present")
    assert rf.derive_years_experience(master, TODAY) == 5


def test_uses_the_earliest_employer() -> None:
    master = _master_with("x", "June 2022 - Present", "March 2019 - May 2022")
    assert rf.derive_years_experience(master, TODAY) == 7


def test_no_parseable_start_date_derives_nothing() -> None:
    master = _master_with("x", "")
    assert rf.derive_years_experience(master, TODAY) is None


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------

def test_resolve_fills_the_placeholder_and_whitelists_the_figure() -> None:
    # Arrange
    master = _master_with("Engineer with {years_experience}+ years.")
    before = copy.deepcopy(master)

    # Act
    resolved = rf.resolve_master(master, TODAY)
    facts = rf.facts_from_master_json(resolved)

    # Assert
    assert resolved["summary_variants"][0]["text"] == "Engineer with 4+ years."
    assert "4+" in facts.numbers
    assert master == before, "resolve_master must not mutate its input"


def test_resolved_figure_passes_the_number_check() -> None:
    master = rf.resolve_master(
        _master_with("Engineer with {years_experience}+ years."), TODAY
    )
    facts = rf.facts_from_master_json(master)
    assert lr.check_numbers("## SUMMARY\nEngineer with 4+ years.", facts) == ()


def test_a_stale_figure_fails_the_number_check() -> None:
    master = rf.resolve_master(
        _master_with("Engineer with {years_experience}+ years."), TODAY
    )
    facts = rf.facts_from_master_json(master)
    violations = lr.check_numbers("## SUMMARY\nEngineer with 3+ years.", facts)
    assert [v.kind for v in violations] == ["fabricated_number"]


def test_resolve_fails_fast_when_the_placeholder_cannot_be_derived() -> None:
    master = _master_with("Engineer with {years_experience}+ years.", "")
    with pytest.raises(ValueError, match="years_experience"):
        rf.resolve_master(master, TODAY)


def test_resolve_leaves_a_master_without_placeholders_equal() -> None:
    master = _master_with("Engineer with 4 years.", "")
    assert rf.resolve_master(master, TODAY) == master


def test_load_master_returns_the_resolved_master(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "master.json"
    path.write_text(
        json.dumps(_master_with("Engineer with {years_experience}+ years.")),
        encoding="utf-8",
    )

    # Act
    master = rf.load_master(path, today=TODAY)

    # Assert
    assert master["summary_variants"][0]["text"] == "Engineer with 4+ years."


# --------------------------------------------------------------------------
# Linter
# --------------------------------------------------------------------------

def test_flags_a_placeholder_copied_into_the_resume() -> None:
    violations = lr.check_placeholders(
        "## SUMMARY\nEngineer with {years_experience}+ years."
    )
    assert [v.kind for v in violations] == ["unresolved_placeholder"]


def test_resume_without_placeholders_passes() -> None:
    assert lr.check_placeholders("## SUMMARY\nEngineer with 4+ years.") == ()

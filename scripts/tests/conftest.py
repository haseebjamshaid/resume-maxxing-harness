"""Shared synthetic fixtures. No real resume content appears here."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resume_facts import (  # noqa: E402
    facts_from_master_json,
    index_master_by_id,
)

MASTER: dict = {
    "schema_version": 1,
    "personal": {
        "name": "Acme Candidate",
        "title_variants": ["Senior Data Engineer"],
        "phone": "+00 000 0000000",
        "email": "candidate@example.com",
        "location": "Test City",
        "linkedin": "linkedin.com/in/example",
        "github": "github.com/example",
    },
    "summary_variants": [
        {"id": "sum.1", "text": "Data engineer with 4 years building pipelines."}
    ],
    "skills": [
        {
            "id": "skills.data",
            "category": "Data",
            "items": ["ClickHouse", "MySQL", "DLT", "Prefect"],
        }
    ],
    "experience": [
        {
            "id": "exp.acme",
            "company": "Acme Corp",
            "location": "Test City",
            "title": "Senior Data Engineer",
            "dates": "June 2022 - Present",
            "scope_variants": [
                {"id": "exp.acme.scope", "text": "Own the data platform end to end."}
            ],
            "projects": [
                {
                    "id": "exp.acme.p1",
                    "name": "Analytics ELT Platform",
                    "name_variants": [],
                    "role": "Data Engineer",
                    "dates": "2025 - present",
                    "bullets": [
                        {
                            "id": "exp.acme.p1.b1",
                            "text": "Owned the transformation layer across 15+ "
                                    "data domains on ClickHouse.",
                        },
                        {
                            "id": "exp.acme.p1.b2",
                            "text": "Implemented CDC merge loading from MySQL "
                                    "using DLT, covered by 19 pytest suites.",
                        },
                        {
                            # Present in the master but not selected into the
                            # clean resume: proves selection is not a failure.
                            "id": "exp.acme.p1.b3",
                            "text": "Kept a single heavy model resident "
                                    "within a fixed ~16 GB RAM budget.",
                        },
                    ],
                }
            ],
        }
    ],
    "personal_projects": [],
    "education": [
        {
            "id": "edu.test",
            "institution": "Test University",
            "degree": "BSc Engineering",
            "location": "Test City",
            "dates": "2018 - 2022",
        }
    ],
    "certifications": [{"id": "cert.ielts", "text": "IELTS 8.5"}],
    "needs_review": [
        {
            "id": "review.1",
            "issue": "Disputed claim held out of the whitelist.",
            "detail": "Rearchitected the platform, cutting cost by 30% across "
                      "9 regions using Terraform.",
            "affects": ["exp.acme.p1.b1"],
        }
    ],
}

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

CLEAN_PROVENANCE: dict = {
    "emitted": [
        {
            "path": "EXPERIENCE.acme.p1.b1",
            "source_id": "exp.acme.p1.b1",
            "original": "Owned the transformation layer across 15+ data "
                        "domains on ClickHouse.",
            "value": "**Owned the transformation layer across 15+ data "
                     "domains** on ClickHouse.",
            "reason": "job description names the transformation layer",
        },
        {
            "path": "EXPERIENCE.acme.p1.b2",
            "source_id": "exp.acme.p1.b2",
            "original": "Implemented CDC merge loading from MySQL using DLT, "
                        "covered by 19 pytest suites.",
            "value": "**Implemented CDC merge loading from MySQL using DLT** "
                     "covered by 19 pytest suites.",
            "reason": "job description names CDC",
        },
    ]
}


@pytest.fixture
def master() -> dict:
    return MASTER


@pytest.fixture
def facts():
    return facts_from_master_json(MASTER)


@pytest.fixture
def master_index() -> dict[str, str]:
    return index_master_by_id(MASTER)

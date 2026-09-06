"""Deterministic extractors and the Facts whitelist.

The same extractors build `.facts.json` from the master ledger AND scan the
tailored resume. That symmetry is the point: anything the scanner can find in
the output was, if genuinely present, also found in the ledger. No LLM is
involved, so the whitelist cannot drift from what it is meant to police.

All functions are pure and return new tuples; nothing here mutates its input.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# --------------------------------------------------------------------------
# Patterns
# --------------------------------------------------------------------------

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?"
_DASH = r"\s*(?:-{1,3}|–|—|to)\s*"
_RANGE_END = (
    rf"(?:{_MONTH}\s+\d{{4}}|\d{{4}}|Present|present|Ongoing|ongoing"
    r"|Current|current|Now|now)"
)

# Ranges are listed before the bare-year alternative so finditer consumes a
# full range as one match instead of leaving a stray year behind.
DATE_RE = re.compile(
    rf"(?:{_MONTH}\s+\d{{4}}|\b(?:19|20)\d{{2}})(?:{_DASH}{_RANGE_END})?"
)

# A numeric claim. The lookbehind stops digits embedded in identifiers
# (Neo4j, FTS5, React19) from being read as standalone figures.
NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9.])~?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|\+|GB|MB|TB|KB)?",
    re.IGNORECASE,
)

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./_-]*")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?:;])\s+")
_PHRASE_BREAK_RE = re.compile(r"[,;:()\[\]/|&+]+|\s-\s")
_MARKDOWN_LEAD_RE = re.compile(r"^[\s>#*\-•➜➔|]+")
_EMPHASIS_RE = re.compile(r"[*_`]+")
_CONTACT_LINE_RE = re.compile(
    r"^.*(?:@|linkedin\.com|github\.com|\+\d[\d\s()\-]{7,}).*$",
    re.MULTILINE,
)

# Seniority ladder. Only rank markers, so an ordinary word like "engineer"
# cannot be mistaken for a level.
SENIORITY_RANK: Mapping[str, int] = {
    "intern": 0, "trainee": 0,
    "junior": 1, "associate": 1, "graduate": 1,
    "mid": 2, "intermediate": 2,
    "senior": 3, "snr": 3, "sr": 3,
    "staff": 4, "lead": 4,
    "principal": 5,
    "head": 6, "manager": 6,
    "director": 7,
    "vp": 8, "vice": 8,
    "chief": 9, "cto": 9, "ceo": 9,
}

# Capitalised words that are ordinary English, resume boilerplate, or company
# and institution suffixes. A real technology sharing one of these names is
# only ever a missed detection, which Layer 4 still covers.
COMMON_CAPITALISED: frozenset[str] = frozenset(
    w.lower()
    for w in (
        # section headings and format words
        "Summary", "Skills", "Experience", "Education", "Certifications",
        "Personal", "Projects", "Project", "Profile", "Objective", "Awards",
        "Languages", "Interests", "Publications", "Volunteer", "Contact",
        # resume verbs, past and present
        "Owned", "Own", "Built", "Build", "Led", "Lead", "Designed", "Design",
        "Created", "Developed", "Develop", "Managed", "Manage", "Maintained",
        "Maintain", "Integrated", "Integrate", "Enforced", "Enforce",
        "Authored", "Applied", "Modeled", "Modelled", "Ran", "Run",
        "Guaranteed", "Hardened", "Engineered", "Established", "Improved",
        "Increased", "Reduced", "Migrated", "Refactored", "Shipped",
        "Launched", "Coordinated", "Mentored", "Supervised", "Conducted",
        "Supported", "Automated", "Optimized", "Optimised", "Scaled",
        "Deployed", "Monitored", "Tested", "Documented", "Reviewed",
        "Analyzed", "Analysed", "Researched", "Planned", "Drove", "Delivered",
        "Implemented", "Implement", "Rebuilt", "Wrote", "Added", "Removed",
        "Replaced", "Extended", "Exposed", "Parsed", "Cut", "Reworked",
        "Introduced", "Standardized", "Standardised", "Consolidated",
        "Instrumented", "Benchmarked", "Profiled", "Debugged", "Fixed",
        "Trained", "Onboarded", "Interviewed", "Presented", "Negotiated",
        # articles, prepositions, conjunctions
        "The", "A", "An", "And", "Or", "But", "For", "With", "From", "Into",
        "Over", "Under", "Across", "Through", "Using", "By", "To", "In", "On",
        "At", "Of", "As", "This", "That", "These", "Those", "It", "Its",
        "Per", "Via", "Both", "Each", "Every", "All", "Between", "During",
        "While", "When", "Where", "Which", "After", "Before", "Within",
        # dates and tenure
        "January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December",
        "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Sept",
        "Oct", "Nov", "Dec", "Present", "Ongoing", "Current", "Now",
        # organisation and institution words
        "Corp", "Corporation", "Inc", "Ltd", "Limited", "LLC", "PLC",
        "GmbH", "Company", "Group", "Holdings", "Technologies", "Labs",
        "University", "College", "School", "Institute", "Academy", "Faculty",
        "Bachelor", "Bachelors", "Master", "Masters", "Doctorate", "PhD",
        "Science", "Sciences", "Arts", "Engineering", "Technology",
        # role words that are not seniority markers
        "Engineer", "Developer", "Analyst", "Scientist", "Architect",
        "Consultant", "Specialist", "Administrator", "Data", "Software",
        "Full", "Stack", "Backend", "Frontend", "Senior", "Junior", "Staff",
        "Principal", "Lead", "Head", "Director", "Manager", "Intern",
        "Remote", "Onsite", "Hybrid", "Team", "Teams", "Client", "Clients",
        "Web", "Mobile", "Desktop", "Platform", "Platforms", "Service",
        "Services", "System", "Systems", "Pipeline", "Pipelines",
        "Application", "Applications", "Server", "Servers", "Layer",
        "Tool", "Tools", "Suite", "Module", "Modules", "Feature",
        "Features", "Product", "Products", "Report", "Reports",
    )
)

CANONICAL_HEADINGS: tuple[str, ...] = (
    "SUMMARY", "SKILLS", "EXPERIENCE", "PERSONAL PROJECTS",
    "EDUCATION", "CERTIFICATIONS",
)
OPTIONAL_HEADINGS: frozenset[str] = frozenset({"PERSONAL PROJECTS"})
PROVENANCE_SECTIONS: tuple[str, ...] = ("EXPERIENCE", "PERSONAL PROJECTS")


# --------------------------------------------------------------------------
# Facts
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Facts:
    """Closed whitelists derived from the master ledger."""

    numbers: frozenset[str]
    technologies: frozenset[str]
    date_ranges: frozenset[str]
    titles: tuple[str, ...]
    skills: frozenset[str]
    certifications: frozenset[str]
    corpus: str = ""

    @property
    def technologies_lower(self) -> frozenset[str]:
        return frozenset(t.lower() for t in self.technologies)

    def mentions(self, term: str) -> bool:
        """True when the master mentions this term, case-insensitively."""
        key = term.strip().lower()
        if not key:
            return False
        if key in self.technologies_lower:
            return True
        if not self.corpus:
            return False
        return re.search(
            rf"(?<!\w){re.escape(key)}(?!\w)", self.corpus
        ) is not None

    @property
    def max_seniority(self) -> int | None:
        ranks = [r for t in self.titles for r in _ranks_in(t)]
        return max(ranks) if ranks else None


def _norm_space(text: str) -> str:
    return " ".join(text.split())


def normalise_number(raw: str) -> str:
    """Formatting-insensitive, content-exact. '~16 GB' and '~16GB' agree."""
    return re.sub(r"[\s,]", "", raw).lower()


def normalise_date(raw: str) -> str:
    """Collapse dash and space variants but keep every meaningful token."""
    text = _norm_space(raw).lower().replace("–", "-").replace("—", "-")
    text = re.sub(r"\bto\b", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return re.sub(r"\s*-\s*", "-", text)


def normalise_text(raw: str) -> str:
    return _norm_space(_EMPHASIS_RE.sub("", raw)).lower()


def _ranks_in(text: str) -> tuple[int, ...]:
    words = re.findall(r"[a-z]+", text.lower())
    return tuple(SENIORITY_RANK[w] for w in words if w in SENIORITY_RANK)


# --------------------------------------------------------------------------
# Extractors
# --------------------------------------------------------------------------

def extract_date_ranges(text: str) -> tuple[str, ...]:
    seen = {normalise_date(m.group()) for m in DATE_RE.finditer(text)}
    return tuple(sorted(seen))


def strip_dates(text: str) -> str:
    """Remove dates so their digits and month names do not reach other scans."""
    return DATE_RE.sub(" ", text)


def extract_numbers(text: str) -> tuple[str, ...]:
    body = strip_dates(_body_after_header(text))
    seen = {
        normalise_number(m.group())
        for m in NUMBER_RE.finditer(body)
        if m.group().strip()
    }
    return tuple(sorted(seen))


def _is_technical_shape(token: str) -> bool:
    if len(token) < 2:
        return False
    has_alpha = any(c.isalpha() for c in token)
    if not has_alpha:
        return False
    if any(c.isdigit() for c in token):
        return True
    if re.search(r"[a-z][A-Z]", token):
        return True
    if token.isupper() and 2 <= len(token) <= 5:
        return True
    if "." in token and re.search(r"[A-Za-z]\.[A-Za-z]", token):
        return True
    if "+" in token or "#" in token:
        return True
    if "-" in token and any(c.isupper() for c in token):
        return True
    return False


def _body_after_header(text: str) -> str:
    """Drop the name and contact block, which is copied verbatim.

    Falls back to the whole text when the document has no `## ` heading, so
    that a bare fragment is still scanned in full.
    """
    match = re.search(r"^##\s", text, re.MULTILINE)
    body = text[match.start():] if match else text
    return _CONTACT_LINE_RE.sub(" ", body)


def _candidate_tokens(sentence: str) -> tuple[str, ...]:
    """Tokens from one sentence, minus the sentence-initial one.

    Slash-joined compounds are split, so `TypeScript/Node.js` is checked as
    its two real names rather than as one unknown string.
    """
    out: list[str] = []
    for token in TOKEN_RE.findall(sentence)[1:]:  # index 0 is sentence-initial
        for part in token.split("/"):
            bare = part.strip(".,;:!?()[]-")
            if bare:
                out.append(bare)
    return tuple(out)


def _is_candidate(token: str) -> bool:
    if not token or token.lower() in COMMON_CAPITALISED:
        return False
    return _is_technical_shape(token) or token[0].isupper()


def _scannable_sentences(
    text: str, *, skip_headings: bool = False
) -> tuple[str, ...]:
    """Sentences worth scanning, with the header, contact lines, dates and
    markdown markers already removed.

    `skip_headings` drops `#` lines. Section and project headings are a
    legitimate tailoring lever (a project may be reframed for the role), and
    they are held to account by their provenance record instead.
    """
    body = strip_dates(_body_after_header(text))
    out: list[str] = []
    for line in body.splitlines():
        if skip_headings and line.lstrip().startswith("#"):
            continue
        stripped = _EMPHASIS_RE.sub("", _MARKDOWN_LEAD_RE.sub("", line))
        out.extend(s for s in _SENTENCE_SPLIT_RE.split(stripped) if s.strip())
    return tuple(out)


def extract_tech_tokens(text: str) -> tuple[str, ...]:
    """Technology-shaped or non-generic capitalised tokens.

    Tokens that open a line or a sentence are skipped: sentence case there
    carries no signal, so `Rebuilt the path` must not read as a product name.
    """
    found = [
        token
        for sentence in _scannable_sentences(text)
        for token in _candidate_tokens(sentence)
        if _is_candidate(token)
    ]
    return tuple(sorted(set(found)))


def extract_proper_phrases(text: str) -> tuple[str, ...]:
    """Runs of two or more consecutive capitalised, non-generic tokens.

    A project name like `Acme Assembly Management Platform` is one claim,
    not four, so it is verified and reported as a single phrase. Runs never
    cross a comma, semicolon, bracket or slash, so a comma-separated skills
    list is not mistaken for a single multi-word product name.
    """
    phrases: list[str] = []
    for sentence in _scannable_sentences(text, skip_headings=True):
        initial = TOKEN_RE.search(sentence)
        rest = sentence[initial.end():] if initial else ""
        for segment in _PHRASE_BREAK_RE.split(rest):
            run: list[str] = []
            for token in TOKEN_RE.findall(segment):
                bare = token.strip(".,;:!?()[]-")
                if bare and _is_candidate(bare) and bare[0].isupper():
                    run.append(bare)
                    continue
                if len(run) >= 2:
                    phrases.append(" ".join(run))
                run = []
            if len(run) >= 2:
                phrases.append(" ".join(run))
    return tuple(sorted(set(phrases)))


def extract_role_strings(text: str) -> tuple[str, ...]:
    """Strings that can carry a job title: the header title line, `###`
    headings, and `*(Role, dates)*` parentheticals. Prose is excluded so a
    verb like `lead technical hiring` is never read as a level."""
    roles: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            for candidate in lines[index + 1:]:
                if candidate.strip():
                    roles.append(_EMPHASIS_RE.sub("", candidate).strip())
                    break
        elif line.startswith("### "):
            roles.append(_EMPHASIS_RE.sub("", line[4:]).strip())
    roles.extend(m.group(1) for m in re.finditer(r"\*\(([^)]*)\)\*", text))
    return tuple(r for r in roles if r)


def extract_bullets(
    text: str, sections: tuple[str, ...] | None = None
) -> tuple[tuple[str, str], ...]:
    """Bullet lines as (location, text).

    When `sections` is given, only bullets under those `## ` headings are
    returned; a document with no headings is treated as entirely in scope.
    """
    has_headings = re.search(r"^##\s", text, re.MULTILINE) is not None
    scoped = sections is not None and has_headings
    current = ""
    out: list[tuple[str, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            current = _norm_space(heading.group(1)).upper()
            continue
        if not re.match(r"^\s*(?:[-*•]|➜|➔)\s+\S", line):
            continue
        if scoped and current not in (sections or ()):
            continue
        body = re.sub(r"^\s*(?:[-*•]|➜|➔)\s+", "", line)
        out.append((f"line {number}", body.rstrip()))
    return tuple(out)


def extract_headings(text: str) -> tuple[str, ...]:
    return tuple(
        _norm_space(m.group(1)).upper()
        for m in re.finditer(r"^##\s+(.*)$", text, re.MULTILINE)
    )


def extract_section(text: str, heading: str) -> str:
    """Body of one `## ` section, empty when absent."""
    pattern = rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


# --------------------------------------------------------------------------
# Building and loading Facts
# --------------------------------------------------------------------------

def facts_from_text(ledger: str) -> Facts:
    """Build the whitelist from the master ledger using the same extractors
    that later police the output."""
    skills_body = extract_section(ledger, "SKILLS") or ledger
    certs_body = extract_section(ledger, "CERTIFICATIONS")
    return Facts(
        numbers=frozenset(extract_numbers(ledger)),
        technologies=frozenset(extract_tech_tokens(ledger)),
        date_ranges=frozenset(extract_date_ranges(ledger)),
        titles=extract_role_strings(ledger),
        skills=frozenset(extract_tech_tokens(skills_body)),
        certifications=frozenset(
            _norm_space(line.lstrip("-*• ").strip())
            for line in certs_body.splitlines()
            if line.strip().startswith(("-", "*", "•"))
        ),
        corpus=normalise_text(ledger),
    )


def facts_from_dict(payload: Mapping[str, Any]) -> Facts:
    return Facts(
        numbers=frozenset(
            normalise_number(n) for n in payload.get("numbers", ())
        ),
        technologies=frozenset(payload.get("technologies", ())),
        date_ranges=frozenset(
            normalise_date(d) for d in payload.get("date_ranges", ())
        ),
        titles=tuple(payload.get("titles", ())),
        skills=frozenset(payload.get("skills", ())),
        certifications=frozenset(payload.get("certifications", ())),
        corpus=str(payload.get("corpus", "")),
    )


def facts_to_dict(facts: Facts) -> dict[str, Any]:
    return {
        "numbers": sorted(facts.numbers),
        "technologies": sorted(facts.technologies),
        "date_ranges": sorted(facts.date_ranges),
        "titles": list(facts.titles),
        "skills": sorted(facts.skills),
        "certifications": sorted(facts.certifications),
        "corpus": facts.corpus,
    }


def load_facts(path: str | Path) -> Facts:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"facts file not found: {target}")
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{target} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{target} must contain a JSON object")
    return facts_from_dict(payload)

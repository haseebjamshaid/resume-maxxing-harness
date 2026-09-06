"""Deterministic extractors and the Facts whitelist.

The same extractors build the whitelist from `master_resume/master.json` AND
scan the tailored resume. That symmetry is the point: anything the scanner can
find in the output was, if genuinely present, also found in the master. No LLM
is involved, so the whitelist cannot drift from what it is meant to police.

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
    """Closed whitelists derived from the master resume JSON."""

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


def extract_numbers(text: str, *, strip_header: bool = True) -> tuple[str, ...]:
    body = strip_dates(_body_after_header(text) if strip_header else text)
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


def _candidate_tokens(
    sentence: str, *, skip_initial: bool = True
) -> tuple[str, ...]:
    """Tokens from one sentence, optionally minus the sentence-initial one.

    Slash-joined compounds are split, so `TypeScript/Node.js` is checked as
    its two real names rather than as one unknown string.
    """
    out: list[str] = []
    found = TOKEN_RE.findall(sentence)
    for token in (found[1:] if skip_initial else found):
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


def extract_tech_tokens(
    text: str, *, skip_initial: bool = True
) -> tuple[str, ...]:
    """Technology-shaped or non-generic capitalised tokens.

    When scanning a resume, tokens that open a line or a sentence are skipped:
    sentence case there carries no signal, so `Rebuilt the path` must not read
    as a product name. When building the whitelist from the master the
    opposite is wanted, since a skills entry like `Python` sits alone on its
    line and must still be whitelisted, so pass `skip_initial=False`.
    """
    found = [
        token
        for sentence in _scannable_sentences(text)
        for token in _candidate_tokens(sentence, skip_initial=skip_initial)
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


# --------------------------------------------------------------------------
# Master resume JSON
# --------------------------------------------------------------------------

# `needs_review` is deliberately excluded from every function below. It holds
# disputed or superseded claims, and letting its text reach the whitelist or
# the id index would make exactly the claims you flagged usable again.
MASTER_REVIEW_KEY = "needs_review"


def _texts_from_master(master: Mapping[str, Any]) -> tuple[str, ...]:
    """Every claim-bearing string in the master. Contact details are omitted:
    a phone number is not a claim, and the resume header is not scanned."""
    out: list[str] = []
    personal = master.get("personal", {}) or {}
    out.extend(str(v) for v in personal.get("title_variants", ()) or ())
    out.extend(str(v) for v in personal.get("tagline_variants", ()) or ())
    out.append(str(personal.get("location", "")))

    for entry in master.get("summary_variants", ()) or ():
        out.append(str(entry.get("text", "")))

    for row in master.get("skills", ()) or ():
        out.append(str(row.get("category", "")))
        out.extend(str(i) for i in row.get("items", ()) or ())

    for employer in master.get("experience", ()) or ():
        out.extend(
            str(employer.get(k, ""))
            for k in ("company", "title", "location")
        )
        for scope in employer.get("scope_variants", ()) or ():
            out.append(str(scope.get("text", "")))
        for project in employer.get("projects", ()) or ():
            out.append(str(project.get("name", "")))
            out.extend(str(n) for n in project.get("name_variants", ()) or ())
            out.append(str(project.get("role", "")))
            for bullet in project.get("bullets", ()) or ():
                out.append(str(bullet.get("text", "")))

    for project in master.get("personal_projects", ()) or ():
        out.append(str(project.get("name", "")))
        out.append(str(project.get("stack", "")))
        for bullet in project.get("bullets", ()) or ():
            out.append(str(bullet.get("text", "")))

    for school in master.get("education", ()) or ():
        out.extend(
            str(school.get(k, ""))
            for k in ("institution", "degree", "location")
        )
        out.extend(str(d) for d in school.get("degree_variants", ()) or ())

    for cert in master.get("certifications", ()) or ():
        out.append(str(cert.get("text", "")))

    return tuple(t for t in out if t.strip())


def _declared_dates(master: Mapping[str, Any]) -> tuple[str, ...]:
    out: list[str] = []
    for employer in master.get("experience", ()) or ():
        out.append(str(employer.get("dates", "")))
        for project in employer.get("projects", ()) or ():
            out.append(str(project.get("dates", "")))
    for project in master.get("personal_projects", ()) or ():
        out.append(str(project.get("dates", "")))
    for school in master.get("education", ()) or ():
        out.append(str(school.get("dates", "")))
    return tuple(d for d in out if d.strip())


def _declared_titles(master: Mapping[str, Any]) -> tuple[str, ...]:
    personal = master.get("personal", {}) or {}
    out = [str(t) for t in personal.get("title_variants", ()) or ()]
    for employer in master.get("experience", ()) or ():
        out.append(str(employer.get("title", "")))
        for project in employer.get("projects", ()) or ():
            out.append(str(project.get("role", "")))
    return tuple(t for t in out if t.strip())


def _declared_skills(master: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(item)
        for row in master.get("skills", ()) or ()
        for item in row.get("items", ()) or ()
        if str(item).strip()
    )


def index_master_by_id(master: Mapping[str, Any]) -> dict[str, str]:
    """Map every id in the master to its exact text.

    Provenance is checked against this, so a source id either resolves to text
    that matches character for character or the bullet is unverifiable. That
    is stricter than searching a blob: a wrong id fails even when the quoted
    text happens to appear somewhere else in the master.
    """
    index: dict[str, str] = {}

    def put(key: Any, value: Any) -> None:
        if key and str(value).strip():
            index[str(key)] = str(value)

    for entry in master.get("summary_variants", ()) or ():
        put(entry.get("id"), entry.get("text"))
    for row in master.get("skills", ()) or ():
        put(row.get("id"), ", ".join(str(i) for i in row.get("items", ()) or ()))
    for employer in master.get("experience", ()) or ():
        put(employer.get("id"), employer.get("company"))
        for scope in employer.get("scope_variants", ()) or ():
            put(scope.get("id"), scope.get("text"))
        for project in employer.get("projects", ()) or ():
            put(project.get("id"), project.get("name"))
            for bullet in project.get("bullets", ()) or ():
                put(bullet.get("id"), bullet.get("text"))
    for project in master.get("personal_projects", ()) or ():
        put(project.get("id"), project.get("name"))
        for bullet in project.get("bullets", ()) or ():
            put(bullet.get("id"), bullet.get("text"))
    for school in master.get("education", ()) or ():
        put(school.get("id"), school.get("degree"))
    for cert in master.get("certifications", ()) or ():
        put(cert.get("id"), cert.get("text"))
    return index


def facts_from_master_json(master: Mapping[str, Any]) -> Facts:
    """Build the closed whitelists from the master resume JSON."""
    texts = _texts_from_master(master)
    blob = "\n".join(texts)
    skills = _declared_skills(master)

    declared = {normalise_date(d) for d in _declared_dates(master)}
    inline = set(extract_date_ranges(blob))

    technologies = set(extract_tech_tokens(blob, skip_initial=False))
    # Skills entries are technologies by declaration, so whitelist each entry
    # whole as well as its tokens ("SQLite / sqlite-vec" as written).
    technologies.update(s for s in skills if s)

    return Facts(
        numbers=frozenset(extract_numbers(blob, strip_header=False)),
        technologies=frozenset(technologies),
        date_ranges=frozenset(declared | inline),
        titles=_declared_titles(master),
        skills=frozenset(skills),
        certifications=frozenset(
            str(c.get("text", ""))
            for c in master.get("certifications", ()) or ()
            if str(c.get("text", "")).strip()
        ),
        corpus=normalise_text(blob),
    )


def load_master(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(
            f"master resume not found: {target}\n"
            "Create it from master_resume/TEMPLATE.md."
        )
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{target} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{target} must contain a JSON object")
    return payload


def validate_master(master: Mapping[str, Any]) -> tuple[str, ...]:
    """Structural problems that would silently disable a guardrail."""
    problems: list[str] = []
    if not master.get("certifications"):
        problems.append(
            "no 'certifications': the no-drop check protects nothing"
        )
    if not (master.get("personal", {}) or {}).get("title_variants"):
        problems.append(
            "no 'personal.title_variants': the seniority ceiling is disabled"
        )
    if not master.get("experience"):
        problems.append("no 'experience' entries")
    if not master.get("skills"):
        problems.append("no 'skills' rows")

    index = index_master_by_id(master)
    seen: set[str] = set()
    duplicates: set[str] = set()
    for employer in master.get("experience", ()) or ():
        for project in employer.get("projects", ()) or ():
            for bullet in project.get("bullets", ()) or ():
                bid = str(bullet.get("id", ""))
                if not bid:
                    problems.append(
                        f"bullet with no id in {project.get('name', '?')!r}"
                    )
                elif bid in seen:
                    duplicates.add(bid)
                seen.add(bid)
    for dup in sorted(duplicates):
        problems.append(f"duplicate id {dup!r}: provenance would be ambiguous")
    if not index:
        problems.append("no ids found: provenance cannot be verified")
    return tuple(problems)

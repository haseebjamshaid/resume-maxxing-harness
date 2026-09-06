"""AI-tell phrase data, ported verbatim from Resume-Matcher.

Source: apps/backend/app/prompts/refinement.py (AI_PHRASE_BLACKLIST,
AI_PHRASE_REPLACEMENTS) and apps/backend/app/prompts/enrichment.py
(the weak-description indicators inside ANALYZE_RESUME_PROMPT).

Data only. No logic lives here so the tables stay diffable against upstream.
"""

from __future__ import annotations

# Phrases that read as machine-written. Grouped as upstream groups them.
AI_PHRASE_BLACKLIST: frozenset[str] = frozenset(
    {
        # Action verbs (overused in AI resume writing)
        "spearheaded", "orchestrated", "championed", "synergized", "leveraged",
        "revolutionized", "pioneered", "catalyzed", "operationalized",
        "architected", "envisioned", "effectuated", "endeavored",
        "facilitated", "utilized",
        # Corporate buzzwords
        "synergy", "synergies", "paradigm", "paradigm shift", "best-in-class",
        "world-class", "cutting-edge", "bleeding-edge", "game-changer",
        "game-changing", "disruptive", "disruptor", "holistic", "robust",
        "scalable", "actionable", "impactful", "proactive", "proactively",
        "stakeholder", "deliverables", "bandwidth", "circle back", "deep dive",
        "move the needle", "low-hanging fruit", "touch base", "value-add",
        # Filler phrases
        "in order to", "for the purpose of", "with a view to",
        "at the end of the day", "moving forward", "going forward",
        "on a daily basis", "on a regular basis", "in a timely manner",
        "at this point in time", "due to the fact that", "in the event that",
        "in light of the fact that",
        # Punctuation patterns
        "—", "---", "--",
    }
)

# Plain-English replacement for each blacklisted phrase.
AI_PHRASE_REPLACEMENTS: dict[str, str] = {
    "spearheaded": "led",
    "orchestrated": "coordinated",
    "championed": "advocated for",
    "synergized": "collaborated",
    "leveraged": "used",
    "revolutionized": "transformed",
    "pioneered": "introduced",
    "catalyzed": "initiated",
    "operationalized": "implemented",
    "architected": "designed",
    "envisioned": "planned",
    "effectuated": "completed",
    "endeavored": "worked",
    "facilitated": "helped",
    "utilized": "used",
    "synergy": "collaboration",
    "synergies": "collaborations",
    "paradigm": "approach",
    "paradigm shift": "change",
    "best-in-class": "top-performing",
    "world-class": "high-quality",
    "cutting-edge": "modern",
    "bleeding-edge": "modern",
    "game-changer": "innovation",
    "game-changing": "innovative",
    "disruptive": "innovative",
    "holistic": "comprehensive",
    "robust": "strong",
    "scalable": "expandable",
    "actionable": "practical",
    "impactful": "effective",
    "proactive": "active",
    "proactively": "actively",
    "stakeholder": "team member",
    "deliverables": "outputs",
    "bandwidth": "capacity",
    "circle back": "follow up",
    "deep dive": "analysis",
    "move the needle": "make progress",
    "low-hanging fruit": "quick wins",
    "touch base": "connect",
    "value-add": "benefit",
    "in order to": "to",
    "for the purpose of": "to",
    "with a view to": "to",
    "at the end of the day": "",
    "moving forward": "",
    "going forward": "",
    "on a daily basis": "daily",
    "on a regular basis": "regularly",
    "in a timely manner": "promptly",
    "at this point in time": "now",
    "due to the fact that": "because",
    "in the event that": "if",
    "in light of the fact that": "since",
    "—": ", ",
    "---": ", ",
    "--": ", ",
}

# Vague openers that signal an unquantified bullet.
WEAK_PHRASES: frozenset[str] = frozenset(
    {
        "responsible for", "worked on", "helped with", "assisted in",
        "involved in",
    }
)

"""Title rule (owner, 2026-11-21): salvage and non-road titles are excluded.

Excluded when the title text contains any of these words (case-insensitive):
SALVAGE (covers "Salvage Vehicle Title" and "Cert of Title-Salvage"), NON-REPAIRABLE,
JUNK, DESTRUCTION. Gemini analysis: these cannot be registered for road use in Portugal.
Blank title is handled separately (no title = excluded).
"""

from __future__ import annotations

EXCLUDED_TITLE_WORDS = ("SALVAGE", "NON-REPAIRABLE", "NON REPAIRABLE", "JUNK", "DESTRUCTION")


def title_exclusion(title: str | None) -> str | None:
    """Return the exclusion reason, or None if the title is allowed."""
    text = (title or "").upper()
    for word in EXCLUDED_TITLE_WORDS:
        if word in text:
            return f"{word.lower()} title: excluded (owner rule)"
    return None

"""Project glossary: a per-project term -> translation table.

The glossary is stored in the project file and injected into the LLM
translation request as extra context, so character names and recurring
terms stay consistent across the whole volume without touching the base
prompt.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from controller import ComicTranslate

# Headers injected between the glossary and the rest of the extra context.
GLOSSARY_HEADER = "Project glossary — keep these translations exact:"
GLOSSARY_FOOTER = "End of project glossary."


def format_glossary_for_prompt(glossary: dict) -> str:
    """Render the term table as the text block sent to the translator."""
    if not glossary:
        return ""
    lines = [
        GLOSSARY_HEADER,
        "Each line is: term = translation",
    ]
    for term, translation in glossary.items():
        lines.append(f"{term} = {translation}")
    lines.append(GLOSSARY_FOOTER)
    return "\n".join(lines)


def merge_extra_context(extra_context: str, glossary: dict) -> str:
    """Append the glossary block to an existing extra context string."""
    glossary_text = format_glossary_for_prompt(glossary)
    if not glossary_text:
        return extra_context or ""
    if extra_context and extra_context.strip():
        return f"{extra_context.strip()}\n\n{glossary_text}"
    return glossary_text


class GlossaryStore:
    """Owns the current project's glossary and its persistence helpers.

    Kept on the controller so the dialog, the pipeline (through
    ``resolve_extra_context``) and the project serializer all read the same
    instance.
    """

    def __init__(self, main: "ComicTranslate"):
        self.main = main
        self._terms: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Plain dict access
    # ------------------------------------------------------------------
    def get_terms(self) -> dict[str, str]:
        """Copy of the current term table (safe to serialize)."""
        return dict(self._terms)

    def set_terms(self, terms: dict) -> None:
        cleaned: dict[str, str] = {}
        if isinstance(terms, dict):
            for term, translation in terms.items():
                if isinstance(term, str) and term.strip() and isinstance(translation, str):
                    cleaned[term.strip()] = translation
        self._terms = cleaned

    def set_term(self, term: str, translation: str) -> None:
        term = (term or "").strip()
        if not term:
            return
        if translation is None:
            translation = ""
        self._terms[term] = str(translation)

    def remove_term(self, term: str) -> None:
        self._terms.pop(term, None)

    def clear(self) -> None:
        self._terms.clear()

    # ------------------------------------------------------------------
    # Serialization (called by the project serializer)
    # ------------------------------------------------------------------
    def to_json_blob(self) -> str:
        return json.dumps(self._terms, ensure_ascii=False, indent=1) if self._terms else ""

    def from_json_blob(self, raw) -> None:
        """Load a stored blob, tolerating older/corrupt values."""
        if not raw or not isinstance(raw, str):
            self._terms = {}
            return
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            self._terms = {}
            return
        if isinstance(data, dict):
            self.set_terms(data)
        else:
            self._terms = {}

    # ------------------------------------------------------------------
    # Merged context used by the pipeline
    # ------------------------------------------------------------------
    def merged_extra_context(self, extra_context: str) -> str:
        return merge_extra_context(extra_context, self._terms)

    def __iter__(self) -> Iterator[str]:
        return iter(self._terms)

    def __len__(self) -> int:
        return len(self._terms)

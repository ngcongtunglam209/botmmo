"""Collision-safe matching helpers for store brands and platform aliases."""

from __future__ import annotations

import re


def contains_search_term(text: object, term: object) -> bool:
    """Return whether *term* occurs as one or more complete search tokens.

    Plain substring checks are unsafe for short brand aliases: ``x`` occurs in
    ``20x``/``Express`` and ``ig`` occurs in ``Digital``.  This matcher accepts
    punctuation and whitespace around a term while rejecting letters, numbers,
    and underscores directly attached to it.
    """

    normalized_text = str(text or "").casefold()
    normalized_term = " ".join(str(term or "").casefold().split())
    if not normalized_text or not normalized_term:
        return False

    term_pattern = r"\s+".join(re.escape(part) for part in normalized_term.split(" "))
    return re.search(rf"(?<!\w){term_pattern}(?!\w)", normalized_text, flags=re.UNICODE) is not None


def contains_any_search_term(text: object, terms: object) -> bool:
    """Return whether any value in *terms* safely matches *text*."""

    return any(contains_search_term(text, term) for term in (terms or ()))

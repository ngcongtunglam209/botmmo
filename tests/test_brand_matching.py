"""Regression tests for collision-safe store brand and platform matching."""

from __future__ import annotations

import pytest

from app.services.brand_matching import contains_any_search_term, contains_search_term


@pytest.mark.parametrize(
    ("text", "term"),
    [
        ("X Premium", "x"),
        ("Premium (X)", "x"),
        ("x.com followers", "x.com"),
        ("IG Followers", "ig"),
        ("Facebook/FB Likes", "fb"),
        ("Tik   Tok views", "tik tok"),
    ],
)
def test_platform_alias_matches_complete_tokens(text: str, term: str):
    assert contains_search_term(text, term)


@pytest.mark.parametrize(
    ("text", "term"),
    [
        ("Claude 20x KBH", "x"),
        ("Express VPN", "x"),
        ("Max package", "x"),
        ("Digital product", "ig"),
        ("Original account", "ig"),
        ("softbank account", "bank"),
        ("telegrambot", "telegram"),
    ],
)
def test_platform_alias_does_not_match_inside_another_token(text: str, term: str):
    assert not contains_search_term(text, term)


def test_contains_any_search_term_uses_same_safe_boundaries():
    assert contains_any_search_term("Instagram | IG Followers", ("instagram", "ig"))
    assert not contains_any_search_term("Digital Express 20x", ("instagram", "ig", "x"))

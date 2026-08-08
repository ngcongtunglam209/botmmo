"""Kiểm tra chặn form post xuyên site của web admin (app/web/security.py)."""

import pytest
from fastapi import HTTPException

from app.web import deps, security, settings


@pytest.fixture(autouse=True)
def _public_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_API_URL", "https://lamtung.dev")
    settings.get_settings.cache_clear()
    yield
    settings.get_settings.cache_clear()


class _FakeURL:
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return self._value


class _FakeRequest:
    def __init__(self, origin, base_url):
        self.headers = {"origin": origin} if origin else {}
        self.base_url = _FakeURL(base_url)


def test_https_origin_is_accepted_when_the_proxy_hides_the_scheme():
    # Caddy kết thúc TLS nên trình duyệt gửi Origin https trong khi app vẫn dựng
    # base_url http. Cùng host thì không phải request xuyên site.
    assert security.origin_allowed("https://lamtung.dev", "http://lamtung.dev/")


def test_matching_origin_is_accepted():
    assert security.origin_allowed("https://lamtung.dev", "https://lamtung.dev/")


def test_missing_origin_header_is_accepted():
    assert security.origin_allowed("", "https://lamtung.dev/")


@pytest.mark.parametrize(
    "origin", ["https://evil.com", "https://lamtung.dev.evil.com", "null"]
)
def test_foreign_origin_is_rejected(origin):
    assert not security.origin_allowed(origin, "https://lamtung.dev/")


@pytest.mark.parametrize(
    "origin", ["https://evil.com", "https://lamtung.dev.evil.com", "null"]
)
def test_dependency_raises_403_for_foreign_origin(origin):
    with pytest.raises(HTTPException) as error:
        deps.require_same_origin(_FakeRequest(origin, "https://lamtung.dev/"))

    assert error.value.status_code == 403


def test_dependency_allows_same_origin():
    deps.require_same_origin(_FakeRequest("https://lamtung.dev", "https://lamtung.dev/"))

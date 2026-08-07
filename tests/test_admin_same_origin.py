import pytest
from fastapi import HTTPException

from app.core.runtime_loader import load_modules


class _FakeURL:
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return self._value


class _FakeRequest:
    def __init__(self, origin, base_url):
        self.headers = {"origin": origin} if origin else {}
        self.base_url = _FakeURL(base_url)


def _require_same_origin():
    modules = load_modules()
    return modules["app.api.admin_web"]._admin_web_require_same_origin


def test_https_origin_is_accepted_when_the_proxy_hides_the_scheme():
    # Caddy terminates TLS, so the browser sends an https Origin while the app
    # may still build an http base_url. Same host, so this is not cross-site.
    _require_same_origin()(_FakeRequest("https://lamtung.dev", "http://lamtung.dev/"))


def test_matching_origin_is_accepted():
    _require_same_origin()(_FakeRequest("https://lamtung.dev", "https://lamtung.dev/"))


def test_missing_origin_header_is_accepted():
    _require_same_origin()(_FakeRequest("", "https://lamtung.dev/"))


@pytest.mark.parametrize("origin", ["https://evil.com", "https://lamtung.dev.evil.com", "null"])
def test_foreign_origin_is_rejected(origin):
    with pytest.raises(HTTPException) as error:
        _require_same_origin()(_FakeRequest(origin, "https://lamtung.dev/"))

    assert error.value.status_code == 403

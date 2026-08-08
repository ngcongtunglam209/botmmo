from fastapi.testclient import TestClient

from app.core.runtime_loader import load_modules


def test_developer_docs_and_reference_are_available():
    modules = load_modules()
    app = modules["app.models.api_models"].app
    client = TestClient(app)

    docs = client.get("/docs")
    css = client.get("/docs/assets/api-docs.css")
    javascript = client.get("/docs/assets/api-docs.js")
    reference = client.get("/reference")

    assert docs.status_code == 200
    assert docs.headers["content-type"].startswith("text/html")
    assert "Tích hợp bán hàng".encode() in docs.content
    assert b'href="/reference"' in docs.content

    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert b"--accent" in css.content
    assert b".callout>div{min-width:0}" in css.content
    assert b".ambient{display:none}" in css.content

    assert javascript.status_code == 200
    assert javascript.headers["content-type"].startswith("application/javascript")
    assert b"navigator.clipboard" in javascript.content

    assert reference.status_code == 200
    assert b"SwaggerUIBundle" in reference.content


def test_admin_login_uses_the_admin_ui_skin():
    """Trang login phải do app/web phục vụ, chỉ có một đường đăng nhập Telegram."""
    modules = load_modules()
    app = modules["app.models.api_models"].app
    client = TestClient(app)

    login = client.get("/admin/login")

    assert login.status_code == 200
    assert "Mọi hoạt động.".encode() in login.content
    assert b"login-shell" in login.content
    assert b"login-points" in login.content
    assert b"/admin/static/app.css" in login.content
    # Không còn form mật khẩu: đăng nhập chỉ qua Telegram OIDC.
    assert b'name="username"' not in login.content
    assert b'name="password"' not in login.content


def test_admin_stylesheet_is_served():
    modules = load_modules()
    client = TestClient(modules["app.models.api_models"].app)

    stylesheet = client.get("/admin/static/app.css")

    assert stylesheet.status_code == 200
    assert b"--accent" in stylesheet.content

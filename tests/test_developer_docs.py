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
    # Callout chứa JSON dài; phải chặn tràn ngang thay vì để đẩy vỡ layout.
    assert b"overflow-x: auto" in css.content
    assert b"max-width: 100%" in css.content

    # Trang công khai không được gọi CDN ngoài: font đã self-host trong repo.
    assert b"fonts.googleapis.com" not in docs.content
    assert b"fonts.gstatic.com" not in docs.content
    assert b"/docs/assets/fonts.css" in css.content

    assert javascript.status_code == 200
    assert javascript.headers["content-type"].startswith("application/javascript")
    assert b"navigator.clipboard" in javascript.content

    assert reference.status_code == 200
    assert b"SwaggerUIBundle" in reference.content


def test_docs_serves_self_hosted_fonts_and_rejects_path_traversal():
    """Font dùng chung với admin nhưng qua đường công khai của /docs.

    Đây là trang không cần đăng nhập nên tên file phải nằm trong allowlist,
    không được ghép thẳng vào đường dẫn.
    """
    modules = load_modules()
    client = TestClient(modules["app.models.api_models"].app)

    fonts_css = client.get("/docs/assets/fonts.css")
    assert fonts_css.status_code == 200
    assert fonts_css.headers["content-type"].startswith("text/css")
    # Đã đổi tiền tố sang đường công khai, không còn trỏ vào /admin.
    assert b"/docs/assets/fonts/" in fonts_css.content
    assert b"/admin/static/fonts/" not in fonts_css.content

    name = fonts_css.text.split("/docs/assets/fonts/")[1].split("'")[0]
    font = client.get(f"/docs/assets/fonts/{name}")
    assert font.status_code == 200
    assert font.content[:4] == b"wOF2"

    # "../x" bị chính httpx gộp đường dẫn trước khi gửi nên không chạm handler;
    # dạng mã hóa mới thật sự tới nơi và phải bị allowlist chặn.
    for attack in ("%2e%2e%2fapi-docs.css", "khong-co.woff2", "fonts.css"):
        assert client.get(f"/docs/assets/fonts/{attack}").status_code == 404, attack


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

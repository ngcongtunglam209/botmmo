"""Dependency dùng chung cho router admin."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from . import security
from .settings import get_settings

LOGIN_PATH = "/admin/login"


class LoginRequired(HTTPException):
    """Bắt ở exception handler và đổi thành redirect 303 sang trang login."""

    def __init__(self) -> None:
        super().__init__(status_code=401, detail="login required")


def session_token(request: Request) -> str:
    return str(request.cookies.get(get_settings().session_cookie) or "").strip()


def is_authenticated(request: Request) -> bool:
    return security.session_active(session_token(request))


def require_admin(request: Request) -> str:
    """Dependency: chặn request chưa đăng nhập."""
    token = session_token(request)
    if not security.session_active(token):
        raise LoginRequired()
    return token


def csrf_token(request: Request) -> str:
    return security.csrf_token_for(session_token(request))


def require_same_origin(request: Request) -> None:
    origin = str(request.headers.get("origin") or "").strip()
    if not security.origin_allowed(origin, str(request.base_url)):
        raise HTTPException(status_code=403, detail="Invalid request origin")


def require_csrf(request: Request, form: Any) -> None:
    supplied = str(form.get("csrf_token") or "")
    if not security.csrf_valid(session_token(request), supplied):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def client_ip(request: Request) -> str:
    """IP dùng cho giới hạn số lần đăng nhập.

    Lấy phần tử CUỐI của `X-Forwarded-For`, không phải phần tử đầu. Caddy *nối
    thêm* vào header chứ không ghi đè, nên giá trị client tự gửi vẫn nằm ở đầu:
    đọc phần tử đầu là để client tự chọn khóa đếm, đổi một cái là reset bộ đếm
    và `login_max_attempts` thành vô nghĩa. Phần tử cuối là cái proxy tin cậy
    ngay trước mình vừa ghi.
    """
    forwarded = str(request.headers.get("x-forwarded-for") or "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    if hops:
        return hops[-1]
    return request.client.host if request.client else ""


def login_redirect(path: str = LOGIN_PATH) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def set_session_cookie(response: Any, request: Request, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie,
        token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure or request.url.scheme == "https",
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Any) -> None:
    response.delete_cookie(get_settings().session_cookie, path="/")

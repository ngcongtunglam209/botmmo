"""Đăng nhập / đăng xuất admin."""

from __future__ import annotations

import logging
import secrets

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .. import deps, security
from ..repo import sessions
from ..settings import get_settings
from ..templating import render

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])

ERROR_MESSAGES = {
    "config": "Đăng nhập Telegram chưa được cấu hình đầy đủ.",
    "denied": "Bạn đã hủy hoặc từ chối đăng nhập Telegram.",
    "state": "Phiên xác thực Telegram không hợp lệ hoặc đã hết hạn.",
    "token": "Không thể xác minh phản hồi từ Telegram.",
    "identity": "ID Token Telegram không hợp lệ.",
    "forbidden": "Tài khoản Telegram này không có quyền quản trị.",
    "ratelimit": "Bạn thử đăng nhập quá nhiều lần. Đợi vài phút rồi thử lại.",
}


def _error_redirect(code: str) -> RedirectResponse:
    response = RedirectResponse(f"/admin/login?error={code}", status_code=303)
    response.delete_cookie(security.OIDC_COOKIE, path=security.OIDC_COOKIE_PATH)
    return response


def _start_session(request: Request, redirect_path: str = "/admin") -> RedirectResponse:
    token, expires_at = security.new_session_token()
    sessions.create(token, expires_at)
    response = RedirectResponse(redirect_path, status_code=303)
    deps.set_session_cookie(response, request, token)
    return response


@router.get("/admin/login", include_in_schema=False)
async def login_page(request: Request):
    if deps.is_authenticated(request):
        return RedirectResponse("/admin", status_code=303)
    settings = get_settings()
    error_code = str(request.query_params.get("error") or "")
    return render(
        request,
        "login.html",
        {
            "telegram_enabled": settings.telegram_login_enabled,
            "error": ERROR_MESSAGES.get(error_code, "" if not error_code else
                                        "Đăng nhập Telegram không thành công."),
        },
    )


@router.get("/admin/login/telegram", include_in_schema=False)
async def telegram_start(request: Request):
    if deps.is_authenticated(request):
        return RedirectResponse("/admin", status_code=303)
    settings = get_settings()
    if not settings.telegram_login_enabled:
        return _error_redirect("config")

    ip = deps.client_ip(request)
    if sessions.attempts_within(ip, settings.login_window_seconds) >= settings.login_max_attempts:
        return _error_redirect("ratelimit")
    sessions.record_attempt(ip)

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    redirect_uri = settings.telegram_redirect_uri or str(
        request.url_for("telegram_callback")
    )

    response = RedirectResponse(
        security.build_authorization_url(state, nonce, verifier, redirect_uri),
        status_code=303,
    )
    response.set_cookie(
        security.OIDC_COOKIE,
        security.oidc_cookie_encode(
            {
                "state": state,
                "nonce": nonce,
                "verifier": verifier,
                "redirect_uri": redirect_uri,
                "issued_at": int(__import__("time").time()),
            }
        ),
        max_age=settings.oidc_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure or request.url.scheme == "https",
        samesite="lax",
        path=security.OIDC_COOKIE_PATH,
    )
    return response


@router.get("/admin/login/telegram/callback", include_in_schema=False, name="telegram_callback")
async def telegram_callback(request: Request):
    import hmac

    if request.query_params.get("error"):
        return _error_redirect("denied")

    code = str(request.query_params.get("code") or "").strip()
    state = str(request.query_params.get("state") or "").strip()
    stored = security.oidc_cookie_decode(request.cookies.get(security.OIDC_COOKIE))
    if not code or not state or not stored:
        return _error_redirect("state")
    if not hmac.compare_digest(state, str(stored.get("state") or "")):
        return _error_redirect("state")

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                security.TELEGRAM_TOKEN_URL,
                auth=(settings.telegram_client_id, settings.telegram_client_secret),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": str(stored.get("redirect_uri") or ""),
                    "client_id": settings.telegram_client_id,
                    "code_verifier": str(stored.get("verifier") or ""),
                },
                headers={"Accept": "application/json"},
            )
            if token_response.status_code != 200:
                logger.warning(
                    "Telegram OIDC token exchange failed: %s", token_response.status_code
                )
                return _error_redirect("token")
            jwks_response = await client.get(
                security.TELEGRAM_JWKS_URL, headers={"Accept": "application/json"}
            )
            if jwks_response.status_code != 200:
                logger.warning("Telegram JWKS fetch failed: %s", jwks_response.status_code)
                return _error_redirect("identity")
            claims = security.verify_id_token(
                str(token_response.json().get("id_token") or ""),
                jwks_response.json(),
                str(stored.get("nonce") or ""),
            )
    except (httpx.HTTPError, ValueError, TypeError):
        logger.exception("Đăng nhập Telegram OIDC thất bại")
        return _error_redirect("token")

    if not claims:
        return _error_redirect("identity")
    if not security.claims_are_admin(claims):
        logger.warning("Từ chối đăng nhập admin cho telegram id không khớp")
        return _error_redirect("forbidden")

    sessions.clear_attempts(deps.client_ip(request))
    response = _start_session(request)
    response.delete_cookie(security.OIDC_COOKIE, path=security.OIDC_COOKIE_PATH)
    return response


@router.post("/admin/login", include_in_schema=False)
async def login_post():
    """Web cũ có form mật khẩu; giờ chỉ còn một đường đăng nhập là Telegram."""
    return RedirectResponse("/admin/login/telegram", status_code=303)


@router.post("/admin/logout", include_in_schema=False)
async def logout(request: Request):
    deps.require_admin(request)
    deps.require_same_origin(request)
    form = await request.form()
    deps.require_csrf(request, form)
    sessions.revoke(deps.session_token(request))
    response = RedirectResponse("/admin/login", status_code=303)
    deps.clear_session_cookie(response)
    return response

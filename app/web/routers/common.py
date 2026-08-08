"""Khung xử lý POST dùng chung cho mọi router admin."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse

from .. import actions, deps

logger = logging.getLogger(__name__)

ActionFn = Callable[[Any], actions.Result]


def redirect_with_message(path: str, result: actions.Result) -> RedirectResponse:
    """Chuyển hướng kèm thông báo hiển thị dạng toast ở trang đích."""
    query = urlencode({"msg": result.message, "err": "" if result.ok else "1"})
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{separator}{query}", status_code=303)


def flash_from(request: Request) -> dict[str, Any] | None:
    message = str(request.query_params.get("msg") or "").strip()
    if not message:
        return None
    return {"message": message, "error": bool(request.query_params.get("err"))}


async def handle_action(
    request: Request,
    action_name: str,
    handler: ActionFn,
    redirect_to: str,
    target_field: str = "",
) -> RedirectResponse:
    """Đọc form, kiểm tra CSRF/same-origin, chạy action, ghi audit, redirect."""
    deps.require_same_origin(request)
    form = await request.form()
    deps.require_csrf(request, form)

    try:
        result = handler(form)
    except Exception as exc:
        logger.exception("Action %s thất bại", action_name)
        result = actions.fail(f"Lỗi {type(exc).__name__}: {exc}")

    await actions.record_and_notify(
        action_name,
        result,
        target=str(form.get(target_field) or "") if target_field else "",
        details={key: value for key, value in form.items() if isinstance(value, str)},
        client_ip=deps.client_ip(request),
    )
    return redirect_with_message(redirect_to, result)


async def run_async_action(
    request: Request,
    action_name: str,
    handler: Callable[[Any], Awaitable[actions.Result]],
    redirect_to: str,
    target_field: str = "",
) -> RedirectResponse:
    """Như handle_action nhưng cho handler bất đồng bộ (upload ảnh)."""
    deps.require_same_origin(request)
    form = await request.form()
    deps.require_csrf(request, form)

    try:
        result = await handler(form)
    except Exception as exc:
        logger.exception("Action %s thất bại", action_name)
        result = actions.fail(f"Lỗi {type(exc).__name__}: {exc}")

    await actions.record_and_notify(
        action_name,
        result,
        target=str(form.get(target_field) or "") if target_field else "",
        client_ip=deps.client_ip(request),
    )
    return redirect_with_message(redirect_to, result)

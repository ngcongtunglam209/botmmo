"""Môi trường Jinja2 và các filter hiển thị."""

from __future__ import annotations

import time
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from . import domain
from .settings import WEB_ROOT

templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))


def money(value: Any) -> str:
    return f"{domain.coerce_amount(value):,} VND"


def number(value: Any) -> str:
    return f"{domain.coerce_amount(value):,}"


def timestamp(value: Any) -> str:
    try:
        seconds = float(value or 0)
    except (TypeError, ValueError):
        return "—"
    if seconds <= 0:
        return "—"
    try:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(seconds))
    except (OSError, OverflowError, ValueError):
        return "—"


def shorten(value: Any, limit: int = 80) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)]}…"


def duration(seconds: Any) -> str:
    total = int(domain.coerce_amount(seconds))
    days, rest = divmod(max(0, total), 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def onoff(value: Any) -> str:
    return "bật" if value else "tắt"


templates.env.filters.update(
    {
        "money": money,
        "number": number,
        "timestamp": timestamp,
        "shorten": shorten,
        "duration": duration,
        "onoff": onoff,
        "plain": domain.plain_text,
    }
)
templates.env.globals["now"] = time.time


def render(request: Request, template: str, context: dict[str, Any] | None = None, **kwargs):
    """Render template với context chuẩn (csrf, đường dẫn, cờ trạng thái sidebar)."""
    from . import bridge
    from .deps import csrf_token

    payload: dict[str, Any] = {
        "request": request,
        "csrf_token": csrf_token(request),
        "current_path": request.url.path,
        # Thanh bên hiện cờ vận hành ở mọi trang, không riêng dashboard/ops.
        "maintenance": bridge.read_flag("maintenance_mode", False),
        "ai_auto_reply": bridge.read_flag("ai_auto_reply", True),
    }
    payload.update(context or {})
    return templates.TemplateResponse(request, template, payload, **kwargs)

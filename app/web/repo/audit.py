"""Nhật ký thao tác admin trên web."""

from __future__ import annotations

import time
from typing import Any

from ..settings import get_settings
from . import collections

#: Trường form không bao giờ được ghi nguyên văn vào audit log.
SENSITIVE_FIELDS = {"csrf_token", "password", "api_key", "target", "secret"}

ACTION_LABELS = {
    "user_balance": "Cập nhật ví user",
    "user_ban": "Ban/unban user",
    "user_profile": "Sửa hồ sơ user",
    "product_create": "Tạo sản phẩm",
    "product_update": "Sửa sản phẩm",
    "product_stock": "Xóa stock local",
    "product_delete": "Xóa sản phẩm",
    "product_image_delete": "Xóa ảnh sản phẩm",
    "product_image_upload": "Tải ảnh sản phẩm",
    "api_partner": "Thao tác API partner",
    "order_tools": "Cập nhật đơn hàng",
    "coupon": "Thao tác coupon",
    "system_toggle": "Đổi trạng thái hệ thống",
    "pending_manual": "Dọn pending manual",
    "support_update": "Cập nhật ticket hỗ trợ",
    "category_create": "Tạo danh mục",
    "category_update": "Sửa danh mục",
    "category_visibility": "Ẩn/hiện danh mục",
    "category_delete": "Xóa danh mục",
    "category_image_delete": "Xóa ảnh danh mục",
    "category_image_upload": "Tải ảnh danh mục",
    "login": "Đăng nhập admin",
}


def label_for(action: str) -> str:
    return ACTION_LABELS.get(action, action or "unknown")


def record(
    action: str,
    ok: bool,
    message: str,
    target: str = "",
    details: dict[str, Any] | None = None,
    actor: str = "admin_web",
    client_ip: str = "",
) -> dict:
    """Ghi một dòng audit, cắt bớt log cũ theo giới hạn cấu hình."""
    event = {
        "timestamp": int(time.time()),
        "action": action,
        "label": label_for(action),
        "ok": bool(ok),
        "message": str(message or "")[:500],
        "target": str(target or "")[:200],
        "details": _safe_details(details),
        "actor": actor,
        "ip": client_ip,
    }
    limit = get_settings().audit_limit
    with collections.admin_action_log.mutate() as log:
        log.append(event)
        if len(log) > limit:
            del log[: len(log) - limit]
    return event


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(details, dict):
        return {}
    clean: dict[str, Any] = {}
    for key, value in details.items():
        if key in SENSITIVE_FIELDS:
            continue
        clean[key] = str(value)[:200]
    return clean


def recent(limit: int = 120) -> list[dict]:
    entries = [item for item in collections.admin_action_log.read() if isinstance(item, dict)]
    return entries[-limit:][::-1]

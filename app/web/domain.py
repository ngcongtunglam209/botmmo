"""Quy tắc nghiệp vụ thuần, không chạm database.

Copy nguyên hành vi từ bot cũ để web hiển thị giống hệt, nhưng ở dạng hàm thuần
để test được mà không cần khởi động bot.
"""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Any

FALLBACK_CATEGORY = "Sản Phẩm Khác"

_CATEGORY_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("capcut",), "CapCut & Edit Video"),
    (("netflix",), "Netflix"),
    (("drive", "google"), "Google Drive & One"),
    (("youtube",), "YouTube Premium"),
    (("spotify",), "Spotify & Music"),
    (("kling",), "Kling"),
    (("perplexity",), "Perplexity"),
    (("tiktok", "tik tok"), "TikTok"),
    (("proxy",), "Proxy"),
    (
        ("gpt", "chatgpt", "openai", "copilot", "cursor", "claude", "gemini"),
        "AI Tools (GPT, Copilot...)",
    ),
    (("adobe",), "Adobe Creative Cloud"),
    (("elxa", "duolingo", "douligo", "doulingo"), "Học Tập"),
)


def infer_category(name: Any) -> str:
    """Đoán danh mục từ tên sản phẩm — giống store_menu.get_product_category."""
    lowered = str(name or "").lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
        if category.startswith("AI Tools") and re.search(r"\bai\b", lowered):
            return category
    return FALLBACK_CATEGORY


def product_category(product: Any) -> str:
    """Danh mục hiệu lực: admin đặt tay ưu tiên, không có thì đoán theo tên."""
    if not isinstance(product, dict):
        return ""
    explicit = str(product.get("store_category") or "").strip()
    if explicit:
        return explicit
    return infer_category(product.get("name"))


def category_slug(name: Any) -> str:
    """Slug ASCII dùng làm tên file ảnh danh mục."""
    ascii_name = (
        unicodedata.normalize("NFKD", str(name or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name).strip("_").lower()
    return slug or "uncategorized"


def product_type(product: Any) -> str:
    if not isinstance(product, dict):
        return "unknown"
    return "manual" if product.get("requires_gmail") else "local"


def stock_count(product: Any) -> int | str:
    """Số lượng tồn. Sản phẩm manual trả 'manual' như dashboard cũ."""
    if not isinstance(product, dict):
        return 0
    if product.get("requires_gmail"):
        return "manual"
    stock = product.get("stock")
    return len(stock) if isinstance(stock, list) else 0


def status_text(value: Any) -> str:
    """Ép status về chuỗi; dữ liệu cũ có chỗ lưu dict/list."""
    if isinstance(value, dict):
        return str(value.get("status") or "")
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return str(value or "")


def is_api_order(order: Any) -> bool:
    if not isinstance(order, dict):
        return False
    return bool(
        order.get("api_partner_ref")
        or order.get("api_partner_ref_key")
        or order.get("api_partner_key_hash")
        or str(order.get("source") or "").lower().startswith("api")
    )


def is_completed_order(order: Any) -> bool:
    """Đơn tính vào doanh thu — copy logic games_withdrawals_db.is_completed_order."""
    if not isinstance(order, dict):
        return False
    normalized = status_text(order.get("status")).strip().lower()
    if not normalized:
        return False
    if "hoàn thành" in normalized or "hoan thanh" in normalized:
        return True
    if normalized == "completed":
        return True
    return is_api_order(order) and "api sold" in normalized


def order_code(order: Any) -> str:
    if not isinstance(order, dict):
        return ""
    return str(
        order.get("order_code") or order.get("code") or order.get("id") or ""
    ).strip()


def order_timestamp(order: Any) -> float:
    if not isinstance(order, dict):
        return 0.0
    for field in ("timestamp", "created_at", "time", "order_time"):
        value = order.get(field)
        if value:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return 0.0


def coerce_amount(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    try:
        text = str(value or "").replace(",", "").replace(".", "").strip()
        return int(text) if text else default
    except (TypeError, ValueError):
        return default


def coupon_expiry_text(days: int, now: float | None = None) -> str:
    """Định dạng ngày hết hạn coupon giống bot: dd-mm-YYYY."""
    base = time.time() if now is None else now
    return time.strftime("%d-%m-%Y", time.localtime(base + days * 86400))


def strip_telegram_emoji(text: Any) -> str:
    """Bỏ thẻ <tg-emoji> mà bot chèn, chỉ giữ ký tự emoji bên trong."""
    value = str(text or "")
    return re.sub(
        r"<tg-emoji\b[^>]*>(.*?)</tg-emoji>", r"\1", value, flags=re.IGNORECASE | re.DOTALL
    )


def plain_text(value: Any) -> str:
    """Bỏ toàn bộ thẻ HTML để hiển thị an toàn trong bảng."""
    text = strip_telegram_emoji(value).strip()
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()

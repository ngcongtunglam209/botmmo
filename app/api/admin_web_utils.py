from __future__ import annotations

import json
import re
import time
from html import escape, unescape


def _admin_web_bool_text(value) -> str:
    return "bat" if bool(value) else "tat"


def _admin_web_int(value, default=0):
    try:
        return int(str(value or "").replace(",", "").replace(".", "").strip())
    except (TypeError, ValueError):
        return default


def _admin_web_money(value) -> str:
    return f"{_admin_web_int(value, 0):,} VND"


def _admin_web_text(value, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _admin_web_short(value, limit: int = 80) -> str:
    text = _admin_web_text(value)
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)]}..."


def _admin_web_strip_telegram_emoji_markup(text: str, decode_entities: bool = False) -> str:
    if decode_entities and ("&lt;" in text or "&gt;" in text or "&amp;" in text):
        text = unescape(text)
    text = re.sub(r"<tg-emoji\b[^>]*>(.*?)</tg-emoji>", r"\1", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"&lt;tg-emoji\b.*?&gt;(.*?)&lt;/tg-emoji&gt;", r"\1", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def _admin_web_plain_display(value) -> str:
    text = _admin_web_text(value)
    if not text:
        return ""
    text = _admin_web_strip_telegram_emoji_markup(text, decode_entities=True)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _admin_web_json_block(data) -> str:
    try:
        payload = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        payload = str(data)
    payload = _admin_web_strip_telegram_emoji_markup(payload)
    return f'<pre class="json-block">{escape(payload)}</pre>'


def _admin_web_mapping_get(mapping, key):
    if not isinstance(mapping, dict):
        return None
    if key in mapping:
        return mapping.get(key)
    text_key = str(key)
    if text_key in mapping:
        return mapping.get(text_key)
    if text_key.isdigit():
        int_key = int(text_key)
        if int_key in mapping:
            return mapping.get(int_key)
    return None


def _admin_web_row_search(*values) -> str:
    return escape(" ".join(str(value or "") for value in values).casefold(), quote=True)


def _admin_web_product_type(product_data) -> str:
    if not isinstance(product_data, dict):
        return "unknown"
    if product_data.get("is_social_source_service"):
        return "ctt"
    if product_data.get("is_supplier_source_resell"):
        return "supplier_source"
    if product_data.get("requires_gmail"):
        return "manual"
    return "local"


def _admin_web_order_code(order_data) -> str:
    if not isinstance(order_data, dict):
        return ""
    return str(order_data.get("order_code") or order_data.get("code") or order_data.get("id") or "").strip()


def _admin_web_order_time(order_data) -> str:
    if not isinstance(order_data, dict):
        return "N/A"
    for field in ("timestamp", "created_at", "time", "order_time"):
        value = order_data.get(field)
        if value:
            return _admin_web_format_timestamp(value)
    return "N/A"


def _admin_web_format_timestamp(timestamp) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp or 0)))
    except (TypeError, ValueError, OSError, OverflowError):
        return "N/A"


def _admin_web_active_count(data) -> int:
    if not isinstance(data, dict):
        return 0
    return sum(1 for item in data.values() if isinstance(item, dict) and item.get("status") == "active")


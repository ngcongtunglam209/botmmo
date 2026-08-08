"""Seam duy nhất giữa web mới và runtime cũ của bot.

Bot giữ toàn bộ dữ liệu trong dict/list RAM và `save_data()` ghi đè kv_store từ
RAM đó. Nếu web chỉ ghi SQLite, lần save_data kế tiếp của bot sẽ xóa thay đổi.

Vì vậy mọi ghi của web đi theo thứ tự: commit SQLite trước (nguồn sự thật), rồi
gọi `publish()` để cập nhật *tại chỗ* collection tương ứng trong app_state. Cập
nhật tại chỗ (clear + update) chứ không gán lại, để mọi alias mà legacy module
đang giữ đều thấy dữ liệu mới.

Nếu web chạy riêng process (không có bot), publish() là no-op an toàn.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: kv_store key -> tên field trong app.state.AppState
KV_TO_STATE: dict[str, str] = {
    "data_products.json": "products",
    "data_order_history.json": "order_history",
    "data_users.json": "user_data_db",
    "data_banned_users.json": "banned_users",
    "data_coupons.json": "coupons",
    "data_api_keys.json": "api_keys",
    "data_pending_orders.json": "pending_orders",
    "data_pending_manual_orders.json": "pending_manual_orders",
    "data_store_categories.json": "store_categories",
    "data_custom_store_icons.json": "custom_store_icons",
    "data_warranty_claims.json": "warranty_claims",
    "data_live_chats.json": "live_chats",
    "data_withdrawals.json": "withdrawal_requests",
    "data_admin_action_log.json": "admin_action_log",
    "data_transaction_history.json": "transaction_history",
    "data_flash_sales.json": "flash_sales",
    "data_combo_deals.json": "combo_deals",
    "data_giveaways.json": "active_giveaways",
    "data_promo_budget.json": "daily_promo_tracker",
    "data_pending_user_topups.json": "pending_user_topups",
    "data_product_ratings.json": "product_ratings",
    "data_referral_data.json": "referral_data",
    "data_stock_waitlist.json": "stock_waitlist",
    "data_dice_game.json": "dice_game_data",
    "data_wheel_data.json": "wheel_data",
    "data_processed_ids.json": "processed_transaction_ids",
    "data_bot_settings.json": "bot_settings",
}


def _app_state() -> Any:
    """Trả app_state nếu bot đang chạy chung process, ngược lại None."""
    import sys

    module = sys.modules.get("app.state")
    if module is None:
        return None
    return getattr(module, "app_state", None)


def _replace_in_place(current: Any, value: Any) -> bool:
    """Ghi đè nội dung `current` bằng `value` mà không đổi object identity."""
    if isinstance(current, dict) and isinstance(value, dict):
        current.clear()
        current.update(value)
        return True
    if isinstance(current, list) and isinstance(value, list):
        current[:] = value
        return True
    if isinstance(current, set) and isinstance(value, (list, set, tuple)):
        current.clear()
        current.update(value)
        return True
    return False


def publish(kv_key: str, value: Any) -> bool:
    """Đẩy giá trị vừa ghi vào SQLite sang runtime bot đang chạy.

    Trả True nếu đã đồng bộ được, False nếu không có bot trong process này
    (trường hợp bình thường khi chạy web độc lập hoặc chạy test).
    """
    field = KV_TO_STATE.get(kv_key)
    if field is None:
        return False
    state = _app_state()
    if state is None:
        return False
    current = getattr(state, field, None)
    if current is None:
        return False
    try:
        replaced = _replace_in_place(current, value)
    except Exception:
        logger.exception("Bridge publish failed for %s", kv_key)
        return False
    if replaced and field == "order_history":
        _rebuild_order_indexes()
    return replaced


def _rebuild_order_indexes() -> None:
    """Dựng lại index đơn hàng của bot.

    order_index/user_order_index/api_partner_ref_index giữ *tham chiếu* tới từng
    dict đơn hàng. Sau khi thay nội dung order_history bằng bản mới đọc từ
    SQLite, các tham chiếu cũ trỏ vào object đã lỗi thời, nên bot sẽ tra ra dữ
    liệu cũ nếu không dựng lại index.
    """
    import sys

    module = sys.modules.get("app.services.games_withdrawals_db")
    rebuild = getattr(module, "_rebuild_order_indexes", None) if module else None
    if not callable(rebuild):
        return
    try:
        rebuild()
    except Exception:
        logger.exception("Bridge could not rebuild order indexes")


def read_flag(name: str, default: bool) -> bool:
    """Đọc cờ runtime (maintenance_mode, ai_auto_reply) từ bot nếu có."""
    state = _app_state()
    if state is None:
        return default
    return bool(getattr(state, name, default))


def set_flag(name: str, value: bool) -> None:
    """Đổi cờ runtime trong bot và đồng bộ ngược vào namespace legacy."""
    state = _app_state()
    if state is not None:
        setattr(state, name, value)
    _sync_legacy_global(name.upper(), value)


def _sync_legacy_global(name: str, value: Any) -> None:
    """Đẩy cờ sang các module đã được runtime_loader exec (nếu có)."""
    import sys

    loader = sys.modules.get("app.core.runtime_loader")
    if loader is None:
        return
    try:
        loader.sync_runtime_bindings({name: value}, [name])
    except Exception:
        logger.warning("Bridge could not sync legacy global %s", name)


def bot_start_time(default: float) -> float:
    state = _app_state()
    if state is None:
        return default
    return float(getattr(state, "bot_start_time", default) or default)


class _BotContext:
    """Vỏ mỏng để dùng lại các hàm notify của bot vốn nhận `context`."""

    def __init__(self, bot: Any) -> None:
        self.bot = bot


async def notify_stock_channel(
    product_name: str,
    added_count: int,
    total_count: int,
    price: int = 0,
) -> bool:
    """Đăng thông báo nhập kho từ web admin, dùng lại logic kênh của bot."""
    import sys

    state = _app_state()
    bot = getattr(state, "bot_instance", None) if state is not None else None
    if bot is None:
        return False
    module = sys.modules.get("app.services.notifications_async")
    notify = getattr(module, "notify_stock_added", None) if module else None
    if not callable(notify):
        return False
    try:
        await notify(_BotContext(bot), product_name, added_count, total_count, price)
        return True
    except Exception:
        logger.warning("Bridge stock notification failed", exc_info=True)
        return False


async def notify_admin(text: str) -> bool:
    """Gửi thông báo Telegram qua bot đang chạy. Bỏ qua nếu không có bot."""
    state = _app_state()
    bot = getattr(state, "bot_instance", None) if state is not None else None
    if bot is None:
        return False
    import os

    admin_id = str(os.getenv("ADMIN_USER_ID", "") or "").strip()
    if not admin_id:
        return False
    try:
        await bot.send_message(chat_id=int(admin_id), text=text, parse_mode="HTML")
        return True
    except Exception:
        logger.warning("Bridge admin notification failed", exc_info=True)
        return False

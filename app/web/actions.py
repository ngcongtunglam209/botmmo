"""Mọi thao tác ghi của web admin.

Router chỉ đọc form rồi gọi một hàm ở đây; hàm trả `Result` để router quyết định
hiển thị. Toàn bộ validation nằm trong module này nên test được mà không cần HTTP.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import bridge, domain
from .repo import audit, catalog, collections, orders, partners, promo, support, users
from .repo.base import as_int
from .settings import get_settings

FALLBACK_CATEGORY = domain.FALLBACK_CATEGORY


@dataclass(frozen=True)
class Result:
    ok: bool
    message: str

    def __bool__(self) -> bool:
        return self.ok


def ok(message: str) -> Result:
    return Result(True, message)


def fail(message: str) -> Result:
    return Result(False, message)


def _text(form: Any, name: str) -> str:
    return str(form.get(name) or "").strip()


def _lines(form: Any, name: str) -> list[str]:
    return [line.strip() for line in _text(form, name).splitlines() if line.strip()]


# --- User & ví --------------------------------------------------------------

def update_user_balance(form: Any) -> Result:
    user_id = _text(form, "user_id")
    if not user_id.isdigit():
        return fail("User ID phải là số.")
    amount = as_int(_text(form, "amount"), -1)
    if amount < 0:
        return fail("Số tiền không hợp lệ.")
    mode = _text(form, "mode") or "add"
    reason = _text(form, "reason") or "Admin web"

    current = users.balance_of(user_id)
    if mode == "add":
        new_balance = current + amount
    elif mode == "sub":
        new_balance = max(0, current - amount)
    elif mode == "set":
        new_balance = amount
    else:
        return fail("Kiểu cập nhật ví không hợp lệ.")

    users.set_balance(user_id, new_balance, f"{reason} ({mode})")
    return ok(f"Ví user {user_id}: {current:,} → {new_balance:,} VND.")


def set_user_ban(form: Any) -> Result:
    user_id = _text(form, "user_id")
    if not user_id.isdigit():
        return fail("User ID phải là số.")
    mode = _text(form, "mode") or "ban"
    if mode not in {"ban", "unban"}:
        return fail("Thao tác ban/unban không hợp lệ.")
    users.set_banned(user_id, mode == "ban")
    return ok(f"Đã {'ban' if mode == 'ban' else 'unban'} user {user_id}.")


def update_user_profile(form: Any) -> Result:
    user_id = _text(form, "user_id")
    if not user_id.isdigit():
        return fail("User ID phải là số.")
    changes = {
        field: _text(form, field)
        for field in ("full_name", "username", "email", "admin_note")
        if _text(form, field)
    }
    if not changes:
        return fail("Chưa có thay đổi nào để lưu.")
    users.upsert_profile(user_id, changes)
    return ok(f"Đã cập nhật user {user_id}: {', '.join(changes)}.")


# --- Sản phẩm ---------------------------------------------------------------

def create_product(form: Any) -> Result:
    product_id = _text(form, "product_id") or f"web_{int(time.time())}_{secrets.token_hex(3)}"
    if catalog.product_exists(product_id):
        return fail("Product ID đã tồn tại.")
    name = _text(form, "name")
    if not name:
        return fail("Tên sản phẩm không được rỗng.")
    price = as_int(_text(form, "price"), -1)
    if price < 0:
        return fail("Giá bán không hợp lệ.")
    cost_price = as_int(_text(form, "cost_price"), -1)
    if cost_price < 0:
        return fail("Giá vốn không hợp lệ (bắt buộc để tính lãi).")

    requires_gmail = _text(form, "requires_gmail") in {"1", "true", "yes", "on"}
    record: dict[str, Any] = {
        "name": name,
        "price": price,
        "cost_price": cost_price,
        "description": _text(form, "description"),
        "duration": _text(form, "duration"),
        "warranty": _text(form, "warranty") or "Không",
        "requires_gmail": requires_gmail,
        "stock": [] if requires_gmail else _lines(form, "stock_items"),
        "created_by": "admin_web",
        "created_at": int(time.time()),
    }
    store_category = _text(form, "store_category")
    if store_category:
        record["store_category"] = store_category
    if requires_gmail:
        record["max_pending_orders"] = 10

    with collections.products.mutate() as data:
        data[product_id] = record
    return ok(f"Đã tạo sản phẩm {product_id}.")


def update_product(form: Any) -> Result:
    product_id = _text(form, "product_id")
    product = catalog.get_product(product_id)
    if product is None:
        return fail("Không tìm thấy product_id.")

    changes: list[str] = []
    updates: dict[str, Any] = {}
    drop_category_cache = False

    store_category = _text(form, "store_category")
    if store_category and store_category != domain.product_category(product):
        updates["store_category"] = store_category
        drop_category_cache = True
        changes.append("danh mục")

    for field, label in (("name", "tên"), ("description", "mô tả"),
                         ("duration", "thời hạn"), ("warranty", "bảo hành")):
        value = _text(form, field)
        if value:
            updates[field] = value
            changes.append(label)

    for field, label in (("price", "giá bán"), ("cost_price", "giá vốn")):
        raw = _text(form, field)
        if not raw:
            continue
        value = as_int(raw, -1)
        if value < 0:
            return fail(f"{label.capitalize()} không hợp lệ.")
        updates[field] = value
        changes.append(label)

    max_pending_raw = _text(form, "max_pending_orders")
    if max_pending_raw:
        max_pending = as_int(max_pending_raw, 0)
        if max_pending < 1:
            return fail("Giới hạn manual phải >= 1.")
        updates["max_pending_orders"] = max_pending
        changes.append("giới hạn manual")

    new_stock = _lines(form, "stock_items")
    if new_stock:
        if product.get("requires_gmail"):
            return fail("Chỉ thêm stock local cho sản phẩm local stock.")
        current = product.get("stock")
        updates["stock"] = (current if isinstance(current, list) else []) + new_stock
        changes.append(f"stock +{len(new_stock)}")

    if not changes:
        return fail("Chưa có thay đổi nào để lưu.")

    with collections.products.mutate() as data:
        record = data.get(product_id)
        if not isinstance(record, dict):
            return fail("Không tìm thấy product_id.")
        record.update(updates)
        if drop_category_cache:
            record.pop("category_image_file_id", None)
    return ok(f"Đã cập nhật {product_id}: {', '.join(changes)}.")


def clear_product_stock(form: Any) -> Result:
    product_id = _text(form, "product_id")
    product = catalog.get_product(product_id)
    if product is None:
        return fail("Không tìm thấy product_id.")
    if product.get("requires_gmail"):
        return fail("Chỉ xóa stock cho sản phẩm local stock.")
    count = len(product.get("stock") or [])
    with collections.products.mutate() as data:
        data[product_id]["stock"] = []
    return ok(f"Đã xóa {count} stock local của {product_id}.")


def delete_product(form: Any) -> Result:
    product_id = _text(form, "product_id")
    product = catalog.get_product(product_id)
    if product is None:
        return fail("Không tìm thấy product_id.")
    name = str(product.get("name") or product_id)
    with collections.products.mutate() as data:
        data.pop(product_id, None)
    catalog.clear_images(get_settings().product_image_dir, product_id)
    return ok(f"Đã xóa sản phẩm {product_id}: {name}.")


def delete_product_image(form: Any) -> Result:
    product_id = _text(form, "product_id")
    if not catalog.product_exists(product_id):
        return fail("Không tìm thấy product_id.")
    removed = catalog.clear_images(get_settings().product_image_dir, product_id)
    if not removed:
        return fail("Sản phẩm chưa có ảnh.")
    with collections.products.mutate() as data:
        data[product_id].pop("image_file_id", None)
    return ok(f"Đã xóa ảnh của {product_id}.")


# --- Danh mục ---------------------------------------------------------------

def _category_config(form: Any, current: dict | None = None) -> dict:
    config = dict(current or {})
    sort_raw = _text(form, "sort_order")
    if sort_raw:
        config["sort_order"] = max(0, as_int(sort_raw, 0))
    elif "sort_order" not in config:
        config["sort_order"] = len(catalog.all_categories()) + 1
    config["emoji_id"] = _text(form, "emoji_id")[:40]
    config["icon_url"] = _text(form, "icon_url")[:500]
    config["hidden"] = _text(form, "hidden") in {"1", "true", "yes", "on"}
    return catalog.touch_config(config)


def create_category(form: Any) -> Result:
    name = _text(form, "category_name")
    if not name:
        return fail("Tên danh mục không được rỗng.")
    if len(name) > 100:
        return fail("Tên danh mục quá dài (tối đa 100 ký tự).")
    if catalog.category_exists(name):
        return fail("Danh mục đã tồn tại.")
    with collections.store_categories.mutate() as data:
        data[name] = _category_config(form)
    return ok(f"Đã thêm danh mục {name}.")


def update_category(form: Any) -> Result:
    old_name = _text(form, "category_name")
    new_name = _text(form, "new_name") or old_name
    if not old_name or not catalog.category_exists(old_name):
        return fail("Không tìm thấy danh mục.")
    if len(new_name) > 100:
        return fail("Tên danh mục quá dài (tối đa 100 ký tự).")
    if new_name != old_name and catalog.category_exists(new_name):
        return fail("Tên danh mục mới đã tồn tại.")

    config = _category_config(form, catalog.category_config(old_name))
    moved = 0
    if new_name != old_name:
        moved = _move_products(old_name, new_name)
        _rename_category_image(old_name, new_name)

    with collections.store_categories.mutate() as data:
        if new_name != old_name:
            data.pop(old_name, None)
        data[new_name] = config
    suffix = f" ({moved} sản phẩm được chuyển)" if moved else ""
    return ok(f"Đã cập nhật danh mục {new_name}{suffix}.")


def set_category_visibility(form: Any) -> Result:
    name = _text(form, "category_name")
    if not catalog.category_exists(name):
        return fail("Không tìm thấy danh mục.")
    mode = _text(form, "mode")
    if mode not in {"hide", "show"}:
        return fail("Trạng thái danh mục không hợp lệ.")
    config = dict(catalog.category_config(name))
    config["hidden"] = mode == "hide"
    config.setdefault("sort_order", len(catalog.all_categories()) + 1)
    with collections.store_categories.mutate() as data:
        data[name] = catalog.touch_config(config)
    return ok(f"Đã {'ẩn' if mode == 'hide' else 'hiện'} danh mục {name}.")


def delete_category(form: Any) -> Result:
    name = _text(form, "category_name")
    if not catalog.category_exists(name):
        return fail("Không tìm thấy danh mục.")
    if name == FALLBACK_CATEGORY:
        return fail("Không thể xóa danh mục mặc định.")
    moved = _move_products(name, FALLBACK_CATEGORY)
    with collections.store_categories.mutate() as data:
        data.pop(name, None)
    catalog.clear_images(get_settings().category_image_dir, domain.category_slug(name))
    return ok(f"Đã xóa danh mục {name}; chuyển {moved} sản phẩm sang {FALLBACK_CATEGORY}.")


def delete_category_image(form: Any) -> Result:
    name = _text(form, "category_name")
    if not catalog.category_exists(name):
        return fail("Không tìm thấy danh mục.")
    removed = catalog.clear_images(
        get_settings().category_image_dir, domain.category_slug(name)
    )
    if not removed:
        return fail("Danh mục chưa có ảnh.")
    _clear_category_image_cache(name)
    return ok(f"Đã xóa ảnh danh mục {name}.")


def _move_products(old_name: str, new_name: str) -> int:
    moved = 0
    with collections.products.mutate() as data:
        for product in data.values():
            if isinstance(product, dict) and domain.product_category(product) == old_name:
                product["store_category"] = new_name
                product.pop("category_image_file_id", None)
                moved += 1
    return moved


def _clear_category_image_cache(name: str) -> None:
    with collections.products.mutate() as data:
        for product in data.values():
            if isinstance(product, dict) and domain.product_category(product) == name:
                product.pop("category_image_file_id", None)


def _rename_category_image(old_name: str, new_name: str) -> None:
    old_path = catalog.category_image_path(old_name)
    if old_path is None:
        return
    target = Path(get_settings().category_image_dir) / (
        f"{domain.category_slug(new_name)}{old_path.suffix.lower()}"
    )
    if not target.exists():
        old_path.rename(target)


# --- API partner ------------------------------------------------------------

def manage_partner(form: Any) -> Result:
    mode = _text(form, "mode") or "topup"
    target = _text(form, "target")
    amount = as_int(_text(form, "amount"), 0)

    if mode == "create":
        name = target or f"Partner{len(partners.all_keys()) + 1}"
        api_key, _record = partners.create_key(name, amount)
        return ok(f"Đã tạo partner {name}. Key mới (chỉ hiện lần này): {api_key}")

    api_key = partners.find_key(target)
    if api_key is None:
        return fail("Không tìm thấy API key/partner.")
    record = partners.get_key(api_key) or {}
    name = str(record.get("name") or api_key)

    if mode in {"topup", "subtract", "set_balance"}:
        return _partner_balance(api_key, name, mode, amount)

    if mode == "configure":
        return _partner_configure(api_key, name, form)

    if mode in {"disable", "revoke"}:
        partners.update_key(api_key, {"enabled": False, "revoked_at": int(time.time())})
        return ok(f"Đã thu hồi API key của {name}.")

    if mode == "enable":
        if record.get("rotated_to"):
            return fail("Key cũ đã regenerate, không bật lại được. Dùng key mới.")
        updated = partners.update_key(api_key, {"enabled": True})
        if updated is not None:
            updated.pop("revoked_at", None)
            partners.update_key(api_key, updated)
        return ok(f"Đã bật API key của {name}.")

    if mode == "regenerate":
        rotated = partners.rotate_key(api_key)
        if rotated is None:
            return fail("Không regenerate được API key.")
        new_key, new_record = rotated
        label = new_record.get("name") or name
        return ok(f"Đã regenerate {label}. Key mới (chỉ hiện lần này): {new_key}")

    return fail("Thao tác API partner không hợp lệ.")


def _partner_balance(api_key: str, name: str, mode: str, amount: int) -> Result:
    if mode == "set_balance":
        if amount < 0:
            return fail("Số dư không được âm.")
        done, balance = partners.set_balance(api_key, amount, f"Admin web set {name}")
    else:
        if amount <= 0:
            return fail("Số tiền phải lớn hơn 0.")
        delta = amount if mode == "topup" else -amount
        done, balance = partners.adjust_balance(
            api_key,
            delta,
            f"Admin web {mode} {name}",
            "deposit" if mode == "topup" else "adjustment",
        )
        if not done:
            return fail("Số dư không đủ để trừ.")
    if not done:
        return fail("Không cập nhật được số dư partner.")
    return ok(f"Đã cập nhật {name}: số dư mới {balance:,} VND.")


def _partner_configure(api_key: str, name: str, form: Any) -> Result:
    changes = {
        "allowed_ips": partners.normalize_allowed_ips(_text(form, "allowed_ips")),
        "rate_limit_per_minute": max(1, min(10000, as_int(_text(form, "rate_limit"), 60))),
        "low_balance_threshold": max(
            0, as_int(_text(form, "low_balance_threshold"), partners.DEFAULT_LOW_BALANCE)
        ),
        "low_balance_alert_enabled": bool(_text(form, "alert_enabled")),
        "admin_note": _text(form, "admin_note")[:500],
        "updated_at": int(time.time()),
    }
    partners.update_key(api_key, changes)
    return ok(f"Đã lưu bảo mật và quota cho {name}.")


# --- Đơn hàng ---------------------------------------------------------------

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def update_order(form: Any) -> Result:
    order_code = _text(form, "order_code").upper()
    if not order_code:
        return fail("Mã đơn không được rỗng.")
    if orders.find(order_code) is None:
        return fail("Không tìm thấy mã đơn.")
    mode = _text(form, "mode") or "set_email"
    value = _text(form, "value")
    if not value:
        return fail("Giá trị cập nhật không được rỗng.")

    if mode == "set_email":
        import re

        if not re.match(EMAIL_PATTERN, value):
            return fail("Email không hợp lệ.")
        changes = {"email": value, "customer_email": value, "delivery_email": value}
        label = "email"
    elif mode == "admin_note":
        changes = {"admin_note": value[:1000]}
        label = "ghi chú"
    else:
        return fail("Thao tác đơn hàng không hợp lệ.")

    touched = orders.update_records(order_code, changes)
    if not touched:
        return fail("Không cập nhật được bản ghi nào.")
    return ok(f"Đã cập nhật {label} cho {order_code} ({touched} bản ghi).")


def clear_pending_manual(form: Any) -> Result:
    mode = _text(form, "mode") or "clear_one"
    if mode == "clear_all":
        count = len(orders.pending_manual())
        collections.pending_manual_orders.write({})
        return ok(f"Đã xóa {count} đơn manual pending.")
    if mode != "clear_one":
        return fail("Thao tác pending manual không hợp lệ.")
    order_code = _text(form, "order_code").upper()
    if not order_code:
        return fail("Cần mã đơn để xóa một pending manual.")
    with collections.pending_manual_orders.mutate() as data:
        if order_code not in data:
            return fail("Không tìm thấy đơn pending manual.")
        data.pop(order_code, None)
    return ok(f"Đã xóa pending manual {order_code}.")


# --- Coupon -----------------------------------------------------------------

def manage_coupon(form: Any) -> Result:
    mode = _text(form, "mode") or "add"
    code = _text(form, "code").upper()
    if not code:
        return fail("Mã coupon không được rỗng.")

    if mode == "delete":
        if not promo.delete_coupon(code):
            return fail("Không tìm thấy coupon.")
        return ok(f"Đã xóa coupon {code}.")
    if mode != "add":
        return fail("Thao tác coupon không hợp lệ.")

    quantity = as_int(_text(form, "quantity"), 0)
    discount = as_int(_text(form, "discount"), 0)
    days = as_int(_text(form, "days"), 30)
    if quantity < 0 or discount < 0 or days < 0:
        return fail("Số lượng, giảm giá và số ngày phải >= 0.")

    existing = promo.get_coupon(code) or {}
    expires = domain.coupon_expiry_text(days)
    promo.save_coupon(
        code,
        {
            "discount": discount,
            "quantity": quantity,
            "expires": expires,
            "used": as_int(existing.get("used"), 0),
        },
    )
    return ok(f"Đã lưu coupon {code}: giảm {discount:,} VND, SL {quantity}, hết hạn {expires}.")


# --- Hỗ trợ -----------------------------------------------------------------

def update_support(form: Any) -> Result:
    entity = _text(form, "entity")
    if not support.entity_valid(entity):
        return fail("Loại ticket không hợp lệ.")
    item_id = _text(form, "item_id")
    if not item_id:
        return fail("Thiếu ID ticket.")
    changes: dict[str, Any] = {"status": _text(form, "status") or "pending"}
    note = _text(form, "admin_note")
    if note:
        changes["admin_note"] = note[:1000]
    if not support.update_item(entity, item_id, changes):
        return fail("Không tìm thấy ticket hỗ trợ.")
    return ok(f"Đã cập nhật {support.LABELS[entity]} {item_id}: {changes['status']}.")


# --- Hệ thống ---------------------------------------------------------------

SYSTEM_TOGGLES = {
    "maintenance_on": ("maintenance_mode", True, "Đã bật chế độ bảo trì."),
    "maintenance_off": ("maintenance_mode", False, "Đã tắt chế độ bảo trì."),
    "ai_on": ("ai_auto_reply", True, "Đã bật AI auto reply."),
    "ai_off": ("ai_auto_reply", False, "Đã tắt AI auto reply."),
}

ENV_TOGGLES = {
    "mbbank_on": ("ENABLE_PAYMENT_MBBANK", True, "Đã bật MBBank."),
    "mbbank_off": ("ENABLE_PAYMENT_MBBANK", False, "Đã tắt MBBank."),
    "binance_on": ("ENABLE_PAYMENT_BINANCE_SPOT", True, "Đã bật Binance Spot."),
    "binance_off": ("ENABLE_PAYMENT_BINANCE_SPOT", False, "Đã tắt Binance Spot."),
}


def toggle_system(form: Any) -> Result:
    mode = _text(form, "mode")
    if mode in SYSTEM_TOGGLES:
        flag, value, message = SYSTEM_TOGGLES[mode]
        bridge.set_flag(flag, value)
        return ok(message)
    if mode in ENV_TOGGLES:
        key, value, message = ENV_TOGGLES[mode]
        _write_env(key, "true" if value else "false")
        bridge._sync_legacy_global(key, value)
        return ok(f"{message} Cần restart bot để áp dụng hoàn toàn.")
    return fail("Thao tác hệ thống không hợp lệ.")


def _write_env(key: str, value: str) -> None:
    """Ghi biến vào .env để cấu hình sống sót sau restart."""
    import re

    from .settings import PROJECT_ROOT

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    content = env_path.read_text("utf-8")
    if re.search(rf"^{re.escape(key)}=", content, flags=re.MULTILINE):
        content = re.sub(
            rf"^{re.escape(key)}=.*$", f"{key}={value}", content, flags=re.MULTILINE
        )
    else:
        content = content.rstrip("\n") + f"\n{key}={value}\n"
    env_path.write_text(content, "utf-8")


# --- Audit ------------------------------------------------------------------

async def record_and_notify(
    action: str,
    result: Result,
    target: str = "",
    details: dict[str, Any] | None = None,
    client_ip: str = "",
) -> None:
    """Ghi audit rồi báo Telegram. Lỗi ở đây không được làm hỏng action."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        event = audit.record(
            action,
            result.ok,
            result.message,
            target=target,
            details=details,
            client_ip=client_ip,
        )
    except Exception:
        logger.exception("Không ghi được audit log cho %s", action)
        return
    if not get_settings().notify_admin:
        return
    status = "✅" if result.ok else "❌"
    text = (
        f"{status} <b>{audit.label_for(action)}</b>\n"
        f"{result.message}\n"
        f"<code>{event.get('target') or '—'}</code>"
    )
    await bridge.notify_admin(text)

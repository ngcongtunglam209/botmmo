"""Seam giữa Partner API mới và pipeline đơn hàng của bot.

Phần HTTP (routing, auth, schema, response) đã chuyển sang package này. Phần
nghiệp vụ nặng — tạo đơn, trừ kho, trừ ví partner, giao hàng, hoàn tiền — vẫn
nằm ở `app/api/routes_core.py` và `app/api/helpers.py` do runtime_loader nạp.

Cố ý không viết lại phần đó: nó khóa kho, ghi sổ ví và gửi hàng cho đối tác
đang chạy thật; viết lại là đổi hành vi tính tiền. Module này gom mọi lời gọi
sang runtime cũ vào một chỗ, thay vì để rải trong từng handler như trước.
"""

from __future__ import annotations

import sys
from typing import Any

HELPERS_MODULE = "app.api.helpers"
ORDERS_MODULE = "app.api.order_pipeline"
STOCK_MODULE = "app.services.local_stock_guard"
ORDER_DB_MODULE = "app.services.games_withdrawals_db"
REFERRAL_MODULE = "app.services.referrals_stats"
CONFIG_MODULE = "app.core.config_env"


class EngineUnavailable(RuntimeError):
    """Runtime bot chưa được nạp — Partner API không phục vụ được."""


def _module(name: str):
    module = sys.modules.get(name)
    if module is None:
        raise EngineUnavailable(f"Module {name} chưa được nạp")
    return module


def call(module_name: str, function_name: str, *args, **kwargs) -> Any:
    """Gọi một hàm trong runtime cũ, báo lỗi rõ ràng nếu thiếu."""
    function = getattr(_module(module_name), function_name, None)
    if not callable(function):
        raise EngineUnavailable(f"{module_name}.{function_name} không khả dụng")
    return function(*args, **kwargs)


def value(module_name: str, name: str, default: Any = None) -> Any:
    """Đọc một biến trong runtime cũ; trả default nếu chưa nạp."""
    module = sys.modules.get(module_name)
    if module is None:
        return default
    return getattr(module, name, default)


def available() -> bool:
    return sys.modules.get(HELPERS_MODULE) is not None


# --- Xác thực partner -------------------------------------------------------

def require_actor(
    x_api_key: str | None = None,
    x_api_token: str | None = None,
    authorization: str | None = None,
    allow_admin: bool = True,
) -> dict:
    return call(
        HELPERS_MODULE,
        "_api_require_actor",
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
        allow_admin=allow_admin,
    )


def remaining_balance(actor: dict) -> Any:
    return call(HELPERS_MODULE, "_api_get_remaining_balance", actor)


def actor_owner_user_id(actor: dict) -> Any:
    return call(HELPERS_MODULE, "_api_get_actor_owner_user_id", actor)


def actor_contact_email(actor: dict) -> Any:
    return call(HELPERS_MODULE, "_api_get_actor_contact_email", actor)


def order_belongs_to_actor(order_data: dict, actor: dict) -> bool:
    return bool(call(HELPERS_MODULE, "_api_order_belongs_to_actor", order_data, actor))


# --- Đọc dữ liệu ------------------------------------------------------------

def status_payload(actor: dict) -> dict:
    return call(HELPERS_MODULE, "_api_status_payload", actor)


def catalog_payload(actor: dict, **kwargs) -> tuple:
    return call(HELPERS_MODULE, "_api_catalog_payload", actor, **kwargs)


def order_payload(order_data: dict, **kwargs) -> dict:
    return call(HELPERS_MODULE, "_api_order_payload", order_data, **kwargs)


def orders_for_actor(actor: dict, **kwargs) -> tuple:
    return call(HELPERS_MODULE, "_api_get_orders_for_actor", actor, **kwargs)


def find_order_by_ref(actor: dict, partner_ref: str) -> Any:
    return call(HELPERS_MODULE, "_api_find_order_by_partner_ref", actor, partner_ref)


def find_order_by_code(order_code: str) -> Any:
    return call(ORDER_DB_MODULE, "find_order_by_code_or_supplier_id", order_code)


def order_by_index(order_code: str) -> Any:
    index = value(ORDER_DB_MODULE, "order_index", {})
    return index.get(order_code) if isinstance(index, dict) else None


def product(product_id: str) -> Any:
    products = value(HELPERS_MODULE, "products", {})
    return products.get(product_id) if isinstance(products, dict) else None


def user_rank(user_id: Any) -> Any:
    return call(REFERRAL_MODULE, "get_user_rank", user_id)


def maintenance_mode() -> bool:
    from .. import bridge

    return bridge.read_flag("maintenance_mode", bool(value(CONFIG_MODULE, "MAINTENANCE_MODE", False)))


# --- Sản phẩm dạng v1 -------------------------------------------------------

def v1_product_payload(product_id: str, product_data: dict, actor: dict) -> dict:
    return call(HELPERS_MODULE, "_api_build_v1_product_payload", product_id, product_data, actor=actor)


def v1_order_summary(order_data: dict) -> dict:
    return call(HELPERS_MODULE, "_api_build_v1_order_summary_payload", order_data)


def v1_order_detail(order_data: dict) -> dict:
    return call(HELPERS_MODULE, "_api_build_v1_order_detail_payload", order_data)


def humanize_error(detail: Any) -> str:
    return call(HELPERS_MODULE, "_api_v1_humanize_error", detail)


def synthetic_variant_id(product_id: str) -> str:
    return call(HELPERS_MODULE, "_api_make_synthetic_variant_id", product_id)


def product_from_variant(variant_id: str) -> tuple:
    return call(HELPERS_MODULE, "_api_get_product_from_synthetic_variant", variant_id)


# --- Ghi: tạo đơn -----------------------------------------------------------

async def create_order(**kwargs) -> tuple:
    """Tạo đơn qua đúng pipeline mà bot và web admin đang dùng."""
    return await call(ORDERS_MODULE, "_api_create_order", **kwargs)


# --- Kho local --------------------------------------------------------------

def last_stock_integrity_report() -> Any:
    return call(STOCK_MODULE, "get_last_local_stock_integrity_report")


async def audit_stock_integrity(source: str) -> Any:
    return await call(STOCK_MODULE, "audit_local_stock_integrity", source=source)

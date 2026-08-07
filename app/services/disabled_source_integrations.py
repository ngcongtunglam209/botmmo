# --- SOCIALSOURCE (CTT) + SUPPLIERSOURCE: TINH NANG DA BI VO HIEU HOA ---
#
# Nguoi ban source da xoa toan bo phan tich hop that voi 2 nha cung cap
# (SocialSource - dich vu tang tuong tac SMM, SupplierSource - dropship
# resell) truoc khi ban lai, nhung con sot lai ~120 cho goi toi ham/hang so
# da bi xoa, gay NameError crash khap noi (menu cua hang, thanh toan, lenh
# admin resell/ctt).
#
# SOCIAL_SOURCE_API_KEY / SUPPLIER_SOURCE_API_KEY / SUPPLIER_CATALOG_API_KEY
# deu hardcode rong vinh vien trong config_env.py (khong doc tu .env), nen
# 2 tinh nang nay KHONG THE nao duoc cau hinh lai trong ban source nay - moi
# ham duoi day chi can dam bao khong crash va tra ve trang thai "khong co
# dich vu/nha cung cap nao" mot cach nhat quan, khong bia them logic nghiep
# vu (gia ca, quy tac) ma minh khong biet.


def _ctt_is_service_product(product) -> bool:
    """San pham co phai dich vu SocialSource (SMM) khong. Luon False tren
    thuc te vi khong con duong nao tao ra san pham loai nay nua, nhung van
    doc dung flag goc de nhat quan neu co du lieu cu."""
    if not isinstance(product, dict):
        return False
    return bool(product.get("is_social_source_service") or product.get("ctt_service_type"))


def _ctt_is_catalog_visible(product) -> bool:
    """Gate hien thi chung cho MOI san pham (khong chi rieng CTT) - xem
    store_menu.py:_is_product_visible_in_store. San pham thuong luon visible;
    san pham SocialSource (khong con duong nao tao ra) bi an vinh vien."""
    if not isinstance(product, dict):
        return False
    if _ctt_is_service_product(product):
        return False
    return True


def _ctt_get_source_category_label(product) -> str:
    return str((product or {}).get("ctt_source_category") or (product or {}).get("store_category") or "")


def _ctt_get_base_unit_price_decimal(product):
    from decimal import Decimal
    try:
        return Decimal(str((product or {}).get("price", 0) or 0))
    except (ArithmeticError, ValueError, TypeError):
        return Decimal(0)


def _ctt_format_vnd_decimal(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _ctt_calculate_total_price(product, qty, discount_percent: int = 0) -> int:
    try:
        unit_price = int((product or {}).get("price", 0) or 0)
        total = unit_price * max(1, int(qty or 1))
    except (TypeError, ValueError):
        return 0
    try:
        discount_percent = max(0, min(100, int(discount_percent or 0)))
    except (TypeError, ValueError):
        discount_percent = 0
    if discount_percent:
        total -= total * discount_percent // 100
    return max(0, total)


def _ctt_get_package_quantity(product) -> int:
    try:
        return max(1, int((product or {}).get("min_quantity") or (product or {}).get("quantity") or 1))
    except (TypeError, ValueError):
        return 1


def _ctt_get_max_package_purchase(product) -> int:
    try:
        return max(1, int((product or {}).get("max_quantity") or 1))
    except (TypeError, ValueError):
        return 1


def _ctt_get_quick_quantity_options(product) -> list:
    return []


def _ctt_get_total_supplier_quantity(product, qty) -> int:
    return 0


def _ctt_validate_purchase_quantity(product, qty) -> str:
    """Tra chuoi loi neu so luong khong hop le, chuoi rong neu hop le
    (dung contract cua cac noi goi: `if _ctt_validate_purchase_quantity(...): show_alert(...)`)."""
    try:
        qty_int = int(qty)
    except (TypeError, ValueError):
        return "So luong khong hop le."
    if qty_int <= 0:
        return "So luong phai lon hon 0."
    return ""


def _ctt_required_input_fields(product) -> list:
    return ["link"]


def _ctt_validate_field_value(field_name: str, value):
    """Tra (gia_tri_da_lam_sach, loi_hoac_None) - xem cach dung tai
    routes_core.py: `val, err = _ctt_validate_field_value("link", ...)`."""
    cleaned = str(value or "").strip()
    if not cleaned:
        return cleaned, f"Thieu du lieu cho truong '{field_name}'."
    return cleaned, None


def _ctt_build_checkout_prompt(product, qty, field_name: str) -> str:
    return f"Vui long nhap '{field_name}' cho don hang (so luong: {qty})."


def _ctt_build_pending_payment_data(product, qty, collected_inputs) -> dict:
    return {}


def _ctt_customer_order_code(payment_reference_code, supplier_result) -> str:
    return str(payment_reference_code or "")


def ctt_build_local_order_status(raw_status) -> str:
    return str(raw_status or "Pending")


def ctt_is_completed_order_status(raw_status) -> bool:
    return str(raw_status or "").strip().casefold() in {"completed", "success", "done"}


def ctt_build_supplier_progress_text(order_data) -> str:
    return ""


def _ctt_build_payment_note(product, qty, ctt_inputs) -> str:
    return ""


def ctt_get_supplier_progress_counts(order_data) -> dict:
    return {}


async def refresh_ctt_order_status(order_data) -> None:
    """No-op: khong con nguon SocialSource nao de doi soat trang thai don."""
    return None


async def ctt_submit_local_service_order(product, qty, collected_inputs) -> dict:
    return {"success": False, "error": "social_source_not_configured", "status_code": 0}


async def ctt_sync_catalog(force_refresh: bool = False, log_error: bool = True) -> dict:
    return {"success": False, "error": "social_source_not_configured", "synced": 0}


async def supplier_create_order(product, qty) -> dict:
    return {"success": False, "error": "supplier_source_not_configured", "status_code": 0}


async def supplier_get_order_details(product, dm_id) -> dict:
    return {"success": False, "error": "supplier_source_not_configured", "status_code": 0}


async def supplier_get_variant_info(product) -> dict:
    return {"success": False, "error": "supplier_source_not_configured", "status_code": 0, "data": {}}


async def supplier_catalog_get_products(log_error: bool = True) -> dict:
    return {"success": False, "error": "supplier_catalog_not_configured", "products": []}


def _supplier_catalog_product_to_supplier_source_variant(item) -> dict:
    return {"success": False, "error": "supplier_catalog_not_configured", "status_code": 0}


def _supplier_source_is_purchase_unavailable_error(error_text: str, status_code: int) -> bool:
    return False


def _supplier_source_update_purchase_block_state(**kwargs) -> bool:
    return False


async def list_resell_command(update, context):
    await update.message.reply_text("Tinh nang SupplierSource resell da bi vo hieu hoa tren source nay.")


async def sync_resell_command(update, context):
    await update.message.reply_text("Tinh nang SupplierSource resell da bi vo hieu hoa tren source nay.")


async def list_ctt_command(update, context):
    await update.message.reply_text("Tinh nang SocialSource (SMM) da bi vo hieu hoa tren source nay.")


async def sync_ctt_command(update, context):
    await update.message.reply_text("Tinh nang SocialSource (SMM) da bi vo hieu hoa tren source nay.")


async def ctt_balance_command(update, context):
    await update.message.reply_text("Tinh nang SocialSource (SMM) da bi vo hieu hoa tren source nay.")

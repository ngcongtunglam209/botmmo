LOCAL_STOCK_DUPLICATE_QUARANTINE_ENABLED = False

_local_stock_integrity_state = {
    "last_report": None,
    "last_cleanup_report": None,
}
_local_stock_history_cache = {
    "signature": None,
    "index": {},
}


def _normalize_local_stock_item(item) -> str:
    return str(item or "").strip()


def _is_local_stock_product(product_data: dict | None) -> bool:
    return bool(
        isinstance(product_data, dict)
        and not product_data.get("requires_gmail")
    )


def _local_stock_history_signature():
    if not isinstance(order_history, list) or not order_history:
        return (0, "", 0)

    last_order = order_history[-1]
    items = last_order.get("items")
    last_items_count = len(items) if isinstance(items, list) else 0
    return (
        len(order_history),
        str(last_order.get("order_code") or ""),
        last_items_count,
    )


def _build_local_stock_item_history_index(use_cache: bool = True):
    signature = _local_stock_history_signature()
    if use_cache and _local_stock_history_cache.get("signature") == signature:
        return _local_stock_history_cache.get("index", {})

    item_index = {}
    for order in order_history:
        order_code = str(order.get("order_code") or "").strip()
        raw_status = str(order.get("status") or "").strip()
        try:
            refunded_at = float(order.get("refunded_at") or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            refunded_at = 0.0

        raw_items = order.get("items")
        if not isinstance(raw_items, list):
            continue

        for item in raw_items:
            normalized_item = _normalize_local_stock_item(item)
            if not normalized_item:
                continue

            item_index.setdefault(
                normalized_item,
                [],
            ).append(
                {
                    "order_code": order_code,
                    "status": raw_status,
                    "refunded_at": refunded_at,
                }
            )

    if use_cache:
        _local_stock_history_cache["signature"] = signature
        _local_stock_history_cache["index"] = item_index
    return item_index


def _split_clean_and_duplicate_stock(stock_items, item_history_index):
    clean_items = []
    duplicate_records = []

    for stock_index, item in enumerate(stock_items):
        normalized_item = _normalize_local_stock_item(item)
        if not normalized_item:
            continue

        matched_orders = item_history_index.get(normalized_item, [])
        if not matched_orders:
            clean_items.append(str(item))
            continue

        first_match = matched_orders[0]
        duplicate_records.append(
            {
                "item": str(item),
                "normalized_item": normalized_item,
                "stock_index": stock_index,
                "matched_order_code": first_match.get("order_code", ""),
                "matched_status": first_match.get("status", ""),
                "matched_refunded_at": first_match.get("refunded_at", 0),
                "matched_orders": [dict(match) for match in matched_orders[:5]],
            }
        )

    return clean_items, duplicate_records


def _get_order_stock_customer_key(order_data: dict | None):
    if not isinstance(order_data, dict):
        return ""
    api_customer_id = str(order_data.get("api_customer_id") or "").strip()
    if api_customer_id:
        return f"api_id:{api_customer_id.casefold()}"
    api_customer_email = str(order_data.get("api_customer_email") or "").strip()
    if api_customer_email:
        return f"api_email:{api_customer_email.casefold()}"
    email = str(order_data.get("email") or "").strip()
    user_id = str(order_data.get("user_id") or "").strip()
    if user_id and not user_id.startswith("PARTNER_"):
        return f"user:{user_id}"
    if email and email not in {"N/A", "api_partner@ref"}:
        return f"email:{email.casefold()}"
    return ""


def _get_local_stock_items_previously_delivered_to_customer(prod_id: str, order_state: dict | None):
    customer_key = _get_order_stock_customer_key(order_state)
    if not customer_key:
        return set()
    delivered_items = set()
    target_product_id = str(prod_id or "")
    for order in order_history:
        if str(order.get("product_id") or "") != target_product_id:
            continue
        if _get_order_stock_customer_key(order) != customer_key:
            continue
        raw_items = order.get("items")
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            normalized_item = _normalize_local_stock_item(item)
            if normalized_item:
                delivered_items.add(normalized_item)
    return delivered_items


def _reserve_customer_safe_stock_batch(stock_items, qty: int, previously_delivered: set):
    selected_indexes = []
    selected_normalized = set()
    duplicate_skipped_indexes = []
    if previously_delivered:
        for stock_index, item in enumerate(stock_items):
            normalized = _normalize_local_stock_item(item)
            if not normalized:
                continue
            if normalized in previously_delivered:
                continue
            if normalized in selected_normalized:
                duplicate_skipped_indexes.append(stock_index)
                continue
            selected_normalized.add(normalized)
            selected_indexes.append(stock_index)
            if len(selected_indexes) >= qty:
                break
    else:
        for stock_index, item in enumerate(stock_items):
            normalized = _normalize_local_stock_item(item)
            if not normalized:
                continue
            if normalized in selected_normalized:
                duplicate_skipped_indexes.append(stock_index)
                continue
            selected_normalized.add(normalized)
            selected_indexes.append(stock_index)
            if len(selected_indexes) >= qty:
                break
    selected_index_set = set(selected_indexes)
    reserved_batch = [str(stock_items[index]) for index in selected_indexes]
    remaining_stock = [
        item
        for stock_index, item in enumerate(stock_items)
        if stock_index not in selected_index_set
    ]
    skipped_count = len(duplicate_skipped_indexes)
    return reserved_batch, remaining_stock, skipped_count


def get_local_stock_available_count(product_data: dict | None, item_history_index: dict | None = None):
    if not _is_local_stock_product(product_data):
        return None

    stock_items = product_data.get("stock", [])
    if not isinstance(stock_items, list):
        return 0

    if not LOCAL_STOCK_DUPLICATE_QUARANTINE_ENABLED:
        return len(stock_items)

    history_index = item_history_index if isinstance(item_history_index, dict) else _build_local_stock_item_history_index()
    clean_items, _duplicate_records = _split_clean_and_duplicate_stock(stock_items, history_index)
    return len(clean_items)


def get_last_local_stock_integrity_report():
    report = _local_stock_integrity_state.get("last_report")
    return dict(report) if isinstance(report, dict) else None


def _build_local_stock_integrity_report(product_id: str | None = None):
    target_product_id = str(product_id or "").strip()
    report = {
        "generated_at": time.time(),
        "product_filter": target_product_id,
        "feature_enabled": False,
        "products_scanned": len(
            [
                pid
                for pid, pdata in products.items()
                if (not target_product_id or pid == target_product_id) and _is_local_stock_product(pdata)
            ]
        ),
        "products_with_duplicates": 0,
        "duplicate_item_count": 0,
        "products": [],
        "duplicate_items": [],
    }
    _local_stock_integrity_state["last_report"] = dict(report)
    return report


async def audit_local_stock_integrity(
    product_id: str | None = None,
    apply_fixes: bool = False,
    backup: bool = False,
    notify_bot=None,
    source: str = "runtime",
):
    report = _build_local_stock_integrity_report(product_id=product_id)
    report["applied_fixes"] = False
    report["quarantined_count"] = 0
    report["feature_disabled_reason"] = "duplicate_quarantine_disabled"
    _local_stock_integrity_state["last_cleanup_report"] = dict(report)
    return report


async def consume_local_stock_items(
    prod_id: str,
    qty: int,
    *,
    order_code: str = "",
    order_state: dict | None = None,
    persist_tables=None,
    notify_bot=None,
    source: str = "runtime",
):
    try:
        requested_qty = int(qty or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        requested_qty = 0

    if requested_qty <= 0:
        return {
            "items": [],
            "available": 0,
            "quarantined": [],
            "reused": False,
        }

    if isinstance(order_state, dict):
        reserved_items = order_state.get("reserved_items")
        reserved_product_id = str(order_state.get("reserved_product_id") or "")
        if (
            isinstance(reserved_items, list)
            and len(reserved_items) == requested_qty
            and reserved_product_id == str(prod_id or "")
        ):
            return {
                "items": [str(item) for item in reserved_items],
                "available": requested_qty,
                "quarantined": [],
                "reused": True,
            }

    product_lock = await get_product_lock(prod_id)
    save_targets = tuple(persist_tables or (PRODUCTS_FILE,))
    async with product_lock:
        product_data = products.get(prod_id)
        if not _is_local_stock_product(product_data):
            return {
                "items": None,
                "available": 0,
                "quarantined": [],
                "reused": False,
            }

        current_stock = product_data.get("stock", [])
        if not isinstance(current_stock, list):
            current_stock = []

        clean_stock = list(current_stock)
        duplicate_records = []
        stock_changed = False

        available_clean_stock = list(product_data.get("stock", [])) if stock_changed else list(clean_stock)
        available_count = len(available_clean_stock)
        if available_count < requested_qty:
            reserved_batch = None
            actual_delivered = 0
            refunded_qty = 0
        else:
            previously_delivered = _get_local_stock_items_previously_delivered_to_customer(prod_id, order_state)
            reserved_batch, remaining_stock, skipped_in_stock = _reserve_customer_safe_stock_batch(
                available_clean_stock,
                requested_qty,
                previously_delivered,
            )
            actual_delivered = len(reserved_batch)
            refunded_qty = requested_qty - actual_delivered
            if not reserved_batch:
                # Du `available_count` dat nhung khong chon duoc dong nao (tat ca
                # deu la hang da giao cho chinh khach nay, hoac dong rong/trung).
                # Phai bao "khong con hang" chu KHONG duoc tra list rong: moi
                # caller chi kiem tra `items is None`, nen mot list rong se lot
                # qua nhanh hoan tien va khach bi tru du tien de nhan 0 san pham.
                # Khong dong nao bi lay ra nen kho giu nguyen.
                reserved_batch = None
                actual_delivered = 0
            else:
                product_data["stock"] = list(remaining_stock)
                stock_changed = True
                if isinstance(order_state, dict):
                    order_state["reserved_items"] = list(reserved_batch)
                    order_state["reserved_product_id"] = str(prod_id or "")
                    order_state["reserved_qty"] = actual_delivered
                    order_state["refunded_qty"] = refunded_qty

        remaining_count = len(product_data.get("stock", [])) if stock_changed else available_count

        if stock_changed:
            await save_critical_tables(*save_targets)

    return {
        "items": reserved_batch,
        "available": remaining_count if reserved_batch else available_count,
        "quarantined": duplicate_records,
        "reused": False,
        "requested_qty": requested_qty,
        # Khong con `if reserved_batch else 0`: khi giao thieu hang, so luong
        # thieu phai bao dung de caller hoan tien, khong duoc lam tron ve 0.
        "actual_delivered": actual_delivered,
        "refunded_qty": refunded_qty if reserved_batch else 0,
    }


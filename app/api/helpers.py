def _api_sanitize_partner_ref(partner_ref: str) -> str:
    text = str(partner_ref or "").strip()
    text = re.sub(r"[^A-Za-z0-9._:-]", "-", text)[:API_V2_MAX_PARTNER_REF_LEN]
    text = text.strip("-_.:")
    return text

def _api_clean_text(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]

def _api_normalize_partner_key(api_key: str):
    key_data = api_keys.get(api_key)
    if key_data is None:
        return None
    if isinstance(key_data, str):
        key_data = {"name": key_data, "balance": 0}
        api_keys[api_key] = key_data
    if not isinstance(key_data, dict):
        return None
    try:
        key_data["balance"] = int(key_data.get("balance", 0))
    except (ValueError, TypeError, KeyError, IndexError):
        key_data["balance"] = 0
    return key_data

def _api_get_partner_display_balance(api_key: str | None = None, key_data: dict | None = None):
    effective_balance = _api_get_partner_effective_balance(api_key=api_key, key_data=key_data)
    if effective_balance is None:
        return 0
    try:
        return int(effective_balance or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        return 0

def _api_get_actor_owner_user_id(actor: dict | None):
    if not isinstance(actor, dict) or actor.get("is_admin"):
        return None
    try:
        direct_uid = int(actor.get("owner_user_id", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        direct_uid = 0
    if direct_uid > 0:
        return direct_uid

    key_data = actor.get("key_data")
    if not isinstance(key_data, dict):
        key_data = _api_normalize_partner_key(actor.get("api_key"))
    try:
        owner_uid = int((key_data or {}).get("user_id", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        owner_uid = 0
    return owner_uid if owner_uid > 0 else None

def _api_resolve_owner_user_id(order_data: dict):
    if not isinstance(order_data, dict):
        return None

    for field in ("api_owner_user_id", "owner_user_id", "rank_user_id"):
        try:
            owner_uid = int(order_data.get(field, 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            owner_uid = 0
        if owner_uid > 0:
            return owner_uid

    if not _api_is_order_record(order_data):
        try:
            regular_uid = int(order_data.get("user_id", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            regular_uid = 0
        return regular_uid if regular_uid > 0 else None

    key_hash = str(order_data.get("api_partner_key_hash") or "").strip()
    user_id_text = str(order_data.get("user_id") or "").strip()
    partner_name = ""
    if user_id_text.startswith("PARTNER_"):
        partner_name = user_id_text.replace("PARTNER_", "", 1).strip()
    if not partner_name:
        partner_name = str(order_data.get("full_name") or "").replace("Partner: ", "").strip()

    fallback_uid = None
    for api_key, api_data in api_keys.items():
        if not isinstance(api_data, dict):
            continue
        if api_data.get("enabled") is False:
            continue
        try:
            current_uid = int(api_data.get("user_id", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            current_uid = 0
        if current_uid <= 0:
            continue
        if key_hash and _api_key_fingerprint(api_key) == key_hash:
            return current_uid
        if not key_hash and partner_name and str(api_data.get("name") or "").strip() == partner_name:
            fallback_uid = current_uid
    return fallback_uid

def _api_get_effective_order_user_id(order_data: dict):
    owner_uid = _api_resolve_owner_user_id(order_data)
    if owner_uid:
        return owner_uid
    try:
        regular_uid = int(order_data.get("user_id", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        regular_uid = 0
    return regular_uid if regular_uid > 0 else None

API_PARTNER_TIERS = (
    {"id": "standard", "name": "Standard", "min_monthly_volume": 0, "discount_percent": 0},
    {"id": "vip", "name": "VIP", "min_monthly_volume": 5_000_000, "discount_percent": 3},
    {"id": "enterprise", "name": "Enterprise", "min_monthly_volume": 20_000_000, "discount_percent": 7},
)


def _api_partner_month_window(reference_ts: float | None = None) -> tuple[float, float]:
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.fromtimestamp(reference_ts, tz) if reference_ts else datetime.now(tz)
    start = datetime(now.year, now.month, 1, tzinfo=tz)
    end = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=tz)
    return start.timestamp(), end.timestamp()


def _api_partner_monthly_volume(api_key: str, reference_ts: float | None = None) -> int:
    start, end = _api_partner_month_window(reference_ts)
    fingerprints = _api_partner_key_fingerprints(api_key)
    total = 0
    for order in order_history:
        if str(order.get("api_partner_key_hash") or "") not in fingerprints:
            continue
        try:
            timestamp = float(order.get("timestamp", 0) or 0)
            if start <= timestamp < end and is_completed_order(order):
                total += max(0, int(order.get("amount", 0) or 0))
        except (TypeError, ValueError):
            continue
    return total


def _api_partner_tier(api_key: str, key_data: dict | None = None, reference_ts: float | None = None) -> dict:
    data = key_data if isinstance(key_data, dict) else api_keys.get(api_key, {})
    volume = _api_partner_monthly_volume(api_key, reference_ts)
    selected = API_PARTNER_TIERS[0]
    if str(data.get("tier_mode") or "auto").lower() == "manual":
        override = str(data.get("tier_override") or "standard").lower()
        selected = next((tier for tier in API_PARTNER_TIERS if tier["id"] == override), selected)
    else:
        for tier in API_PARTNER_TIERS:
            if volume >= tier["min_monthly_volume"]:
                selected = tier
    tier_index = API_PARTNER_TIERS.index(selected)
    next_tier = API_PARTNER_TIERS[tier_index + 1] if tier_index + 1 < len(API_PARTNER_TIERS) else None
    return {
        **selected,
        "monthly_volume": volume,
        "next_tier": next_tier,
        "remaining_to_next": max(0, next_tier["min_monthly_volume"] - volume) if next_tier else 0,
        "mode": str(data.get("tier_mode") or "auto").lower(),
    }


def _api_get_effective_product_price(actor: dict | None, product_id: str, product_data: dict):
    try:
        base_price = int(product_data.get("price", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        base_price = 0

    owner_user_id = _api_get_actor_owner_user_id(actor)
    best_price, discount_type, discount_info = base_price, None, None
    if base_price > 0 and owner_user_id and not (actor or {}).get("is_admin"):
        candidate, candidate_type, candidate_info = get_best_discount(owner_user_id, product_id, base_price)
        try:
            candidate = int(candidate or base_price)
        except (ValueError, TypeError):
            candidate = base_price
        if 0 < candidate < best_price:
            best_price, discount_type, discount_info = candidate, candidate_type, candidate_info

    api_key = str((actor or {}).get("api_key") or "")
    if base_price > 0 and api_key and not (actor or {}).get("is_admin"):
        tier = _api_partner_tier(api_key, (actor or {}).get("key_data"))
        tier_price = max(1, base_price * (100 - int(tier["discount_percent"])) // 100)
        if tier_price < best_price:
            best_price, discount_type = tier_price, "partner_tier"
            discount_info = {"discount_percent": tier["discount_percent"], "tier": tier["id"], "tier_name": tier["name"], "monthly_volume": tier["monthly_volume"]}

    return best_price, base_price, discount_type, discount_info, owner_user_id

def _api_extract_bearer_token(authorization: str | None):
    raw_value = _api_extract_token_value(authorization)
    if not raw_value:
        return ""

    parts = raw_value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return str(parts[1] or "").strip()
    return ""

def _api_extract_token_value(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore").strip()
        except (ValueError, TypeError, KeyError, IndexError):
            return ""
    if not isinstance(value, (str, int, float)):
        return ""
    return str(value).strip()

def _api_extract_token(
    x_api_key: str | None = None,
    x_api_token: str | None = None,
    authorization: str | None = None,
):
    for candidate in (x_api_token, _api_extract_bearer_token(authorization), x_api_key):
        token = _api_extract_token_value(candidate)
        if token:
            return token
    return ""

def _api_get_actor_contact_email(actor: dict | None):
    owner_user_id = _api_get_actor_owner_user_id(actor)
    if not owner_user_id:
        return ""

    profile = user_data_db.get(str(owner_user_id), {})
    if not isinstance(profile, dict):
        return ""

    for field_name in ("email", "gmail"):
        value = str(profile.get(field_name) or "").strip()
        if value:
            return value
    return ""

def _api_make_synthetic_variant_id(product_id: str) -> str:
    return f"var_{str(product_id or '').strip()}"

def _api_get_product_from_synthetic_variant(variant_id: str):
    normalized_variant_id = str(variant_id or "").strip()
    if not normalized_variant_id.startswith("var_"):
        return None, None

    product_id = normalized_variant_id[4:]
    product_data = products.get(product_id)
    if not isinstance(product_data, dict):
        return None, None
    return product_id, product_data

def _api_get_manual_product_available_slots(product_id: str, product_data: dict):
    try:
        max_pending = int(product_data.get("max_pending_orders", 10) or 10)
    except (ValueError, TypeError, KeyError, IndexError):
        max_pending = 10

    pending_count = 0
    for pending_order in pending_manual_orders.values():
        if str(pending_order.get("product_id") or "") == str(product_id or ""):
            pending_count += 1
    return max(0, max_pending - pending_count)

def _api_get_product_completed_sales_count(product_id: str):
    target_product_id = str(product_id or "").strip()
    if not target_product_id:
        return 0

    sold_count = 0
    for order in order_history:
        if str(order.get("product_id") or "").strip() != target_product_id:
            continue
        try:
            refunded_at = int(order.get("refunded_at", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            refunded_at = 0
        if refunded_at > 0 or not is_completed_order(order):
            continue
        try:
            sold_count += max(1, int(order.get("quantity", 1) or 1))
        except (ValueError, TypeError, KeyError, IndexError):
            sold_count += 1
    return sold_count

def _api_get_v1_product_stock_count(product_id: str, product_data: dict):
    if product_data.get("is_social_source_service"):
        return None
    if product_data.get("requires_gmail"):
        return _api_get_manual_product_available_slots(product_id, product_data)
    if product_data.get("is_supplier_source_resell"):
        try:
            return max(0, int(product_data.get("supplier_source_stock", 0) or 0))
        except (ValueError, TypeError, KeyError, IndexError):
            return 0
    return int(get_local_stock_available_count(product_data) or 0)

def _api_build_v1_variant_payload(product_id: str, product_data: dict, actor: dict | None = None):
    unit_price, _base_price, _discount_type, _discount_info, _owner_user_id = _api_get_effective_product_price(
        actor,
        product_id,
        product_data,
    )
    variant_name = str(product_data.get("duration") or product_data.get("name") or product_id).strip()
    return {
        "id": _api_make_synthetic_variant_id(product_id),
        "productId": str(product_id or ""),
        "name": variant_name or str(product_id or ""),
        "productTitle": str(product_data.get("name") or product_id),
        "price": int(unit_price or 0),
        "stock": _api_get_v1_product_stock_count(product_id, product_data),
    }

def _api_build_v1_product_payload(product_id: str, product_data: dict, actor: dict | None = None):
    unit_price, _base_price, _discount_type, _discount_info, _owner_user_id = _api_get_effective_product_price(
        actor,
        product_id,
        product_data,
    )
    return {
        "id": str(product_id or ""),
        "sellerId": "lam_shop",
        "title": str(product_data.get("name") or product_id),
        "shortDescription": str(product_data.get("description") or product_data.get("duration") or ""),
        "type": "SERVICE" if product_data.get("requires_gmail") or product_data.get("is_social_source_service") else "ACCOUNT",
        "price": str(int(unit_price or 0)),
        "stock": _api_get_v1_product_stock_count(product_id, product_data),
        "sold": _api_get_product_completed_sales_count(product_id),
        "imageUrl": "",
        "tags": [],
        "variants": [_api_build_v1_variant_payload(product_id, product_data, actor=actor)],
    }

def _api_v1_normalize_order_status(order_data: dict):
    try:
        refunded_at = int(order_data.get("refunded_at", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        refunded_at = 0
    if refunded_at > 0:
        return "REFUNDED"

    if order_data.get("is_social_source_service"):
        supplier_status = str(order_data.get("ctt_supplier_status") or "").strip()
        if supplier_status:
            normalized_supplier_status = supplier_status.casefold()
            if normalized_supplier_status in {"canceled", "cancelled"}:
                return "FAILED"
            if ctt_is_completed_order_status(supplier_status):
                return "COMPLETED"
            return "PENDING"

    raw_status = status_text(order_data.get("status")).strip().lower()
    delivery_method = str(order_data.get("delivery_method") or "").strip().lower()
    delivered_items = order_data.get("items")
    has_items = isinstance(delivered_items, list) and bool(delivered_items)

    if is_completed_order(order_data):
        return "COMPLETED"
    if delivery_method in {"manual_pending", "pending_source", "pending"}:
        return "PENDING"
    if "cho" in raw_status or "pending" in raw_status:
        return "PENDING"
    if "fail" in raw_status or "loi" in raw_status:
        return "FAILED"
    return "COMPLETED" if has_items else "PENDING"

def _api_v1_normalize_delivered_content(delivered_items):
    if not isinstance(delivered_items, list):
        return {}

    cleaned_items = [str(item).strip() for item in delivered_items if str(item).strip()]
    if not cleaned_items:
        return {}

    if all(item.count("|") == 1 for item in cleaned_items):
        content = {}
        for item in cleaned_items:
            left, right = item.split("|", 1)
            content[left.strip()] = right.strip()
        return content

    return {
        f"item_{index}": item
        for index, item in enumerate(cleaned_items, 1)
    }

def _api_get_v1_order_unit_price(order_data: dict):
    try:
        stored_unit_price = int(order_data.get("unit_price", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        stored_unit_price = 0
    if stored_unit_price > 0:
        return stored_unit_price

    try:
        quantity = max(1, int(order_data.get("quantity", 1) or 1))
    except (ValueError, TypeError, KeyError, IndexError):
        quantity = 1
    try:
        total_amount = int(order_data.get("amount", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        total_amount = 0
    return int(total_amount / quantity) if quantity > 0 else total_amount

def _api_build_v1_order_summary_payload(order_data: dict):
    return {
        "id": str(order_data.get("order_code") or ""),
        "status": _api_v1_normalize_order_status(order_data),
        "deliveredContent": _api_v1_normalize_delivered_content(order_data.get("items")),
    }

def _api_build_v1_order_detail_payload(order_data: dict):
    try:
        quantity = max(1, int(order_data.get("quantity", 1) or 1))
    except (ValueError, TypeError, KeyError, IndexError):
        quantity = 1

    return {
        "id": str(order_data.get("order_code") or ""),
        "status": _api_v1_normalize_order_status(order_data),
        "price": _api_get_v1_order_unit_price(order_data),
        "quantity": quantity,
        "deliveredContent": _api_v1_normalize_delivered_content(order_data.get("items")),
    }

def _api_stringify_error_detail(detail) -> str:
    if isinstance(detail, dict):
        for key_name in ("message", "detail", "error"):
            value = str(detail.get(key_name) or "").strip()
            if value:
                return value
        return json.dumps(detail, ensure_ascii=False)
    return str(detail or "").strip()

def _api_v1_humanize_error(detail) -> str:
    detail_text = _api_stringify_error_detail(detail)
    normalized = detail_text.lower()
    if not detail_text:
        return "Request failed"
    if detail_text == "product_not_found":
        return "Product not found"
    if detail_text == "dino_out_of_stock":
        return "Out of stock"
    if detail_text == "invalid_product_price":
        return "Invalid product price"
    if detail_text == "target_link is required for social_service":
        return "target_link is required for this social service"
    if detail_text == "comments is required for this social_service":
        return "comments is required for this social service"
    if detail_text == "supplier_source_product_id_missing":
        return "Supplier product configuration is missing"
    if normalized.startswith("supplier_error:"):
        return detail_text.split(":", 1)[1].strip() or "Supplier error"
    return detail_text

def _api_json_response(status_code: int, content: dict):
    try:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=status_code, content=content)
    except ImportError:
        fallback = dict(content)
        fallback["_status_code"] = int(status_code)
        return fallback

def _api_v1_error_response(message: str, status_code: int = 400):
    return _api_json_response(
        status_code,
        {
            "success": False,
            "message": str(message or "Request failed"),
        },
    )

def _api_normalize_allowed_ips(value) -> list[str]:
    raw_values = value if isinstance(value, (list, tuple, set)) else re.split(r"[,\s;]+", str(value or ""))
    normalized = []
    for raw in raw_values:
        item = str(raw or "").strip()
        if not item:
            continue
        try:
            network = ipaddress.ip_network(item, strict=False)
        except ValueError as exc:
            raise ValueError(f"IP/CIDR không hợp lệ: {item}") from exc
        canonical = str(network.network_address) if network.num_addresses == 1 else str(network)
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized


def _api_partner_ip_allowed(key_data: dict, client_ip: str) -> bool:
    allowed = _api_normalize_allowed_ips(key_data.get("allowed_ips") or [])
    if not allowed:
        return True
    try:
        address = ipaddress.ip_address(str(client_ip or "").strip())
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(rule, strict=False) for rule in allowed)


def _api_partner_rate_limit(key_data: dict) -> int:
    try:
        return max(1, min(10000, int(key_data.get("rate_limit_per_minute", 60) or 60)))
    except (TypeError, ValueError):
        return 60


def _api_generate_partner_key() -> str:
    new_key = f"sk_live_{secrets.token_hex(16)}"
    while new_key in api_keys:
        new_key = f"sk_live_{secrets.token_hex(16)}"
    return new_key


async def _api_rotate_partner_key(api_key: str):
    old_key = str(api_key or "").strip()
    partner_data = _api_normalize_partner_key(old_key)
    if not old_key or not isinstance(partner_data, dict):
        return None
    lock = await get_api_key_lock(old_key)
    async with lock:
        current_balance = _api_get_partner_display_balance(old_key, partner_data)
        new_key = _api_generate_partner_key()
        rotation_ts = int(time.time())
        new_data = dict(partner_data)
        new_data.update({"balance": current_balance, "enabled": True, "rotated_from": old_key, "rotated_at": rotation_ts})
        new_data.pop("rotated_to", None)
        partner_data.update({"balance": current_balance, "enabled": False, "rotated_to": new_key, "rotated_at": rotation_ts})
        api_keys[new_key] = new_data
        for pending in pending_api_deposits.values():
            if isinstance(pending, dict) and str(pending.get("api_key") or "") == old_key:
                pending["api_key"] = new_key
                pending["partner_name"] = new_data.get("name") or "Partner"
        await save_data(force=True, tables=[API_KEYS_FILE, "data_pending_api_deposits.json"])
    return new_key, new_data


# NOTE: run_api_server() đã được định nghĩa bên dưới (gần cuối file) — duy nhất 1 bản.

def _api_require_actor(
    x_api_key: str | None = None,
    x_api_token: str | None = None,
    authorization: str | None = None,
    allow_admin: bool = True,
):
    if not API_SECRET_KEY:
        raise HTTPException(status_code=503, detail="API secret not configured")
    resolved_api_key = _api_extract_token(
        x_api_key=x_api_key,
        x_api_token=x_api_token,
        authorization=authorization,
    )
    if not resolved_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")

    if hmac.compare_digest(resolved_api_key, API_SECRET_KEY):
        if not allow_admin:
            raise HTTPException(status_code=403, detail="Admin API key is not allowed for this route")
        return {
            "api_key": resolved_api_key,
            "is_admin": True,
            "partner_name": "Master Admin",
            "key_data": None,
            "balance": "unlimited",
            "key_fingerprint": "admin-master",
            "owner_user_id": None,
        }

    key_data = _api_normalize_partner_key(resolved_api_key)
    if key_data is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if key_data.get("enabled") is False:
        rotated_to = str(key_data.get("rotated_to") or "").strip()
        if rotated_to:
            raise HTTPException(
                status_code=403,
                detail="API Key is disabled. Please use the latest rotated key from Telegram.",
            )
        raise HTTPException(status_code=403, detail="API Key is disabled")

    partner_name = str(key_data.get("name") or "Unknown")
    try:
        owner_user_id = int(key_data.get("user_id", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        owner_user_id = 0
    return {
        "api_key": resolved_api_key,
        "is_admin": False,
        "partner_name": partner_name,
        "key_data": key_data,
        "balance": _api_get_partner_display_balance(resolved_api_key, key_data),
        "key_fingerprint": _api_key_fingerprint(resolved_api_key),
        "owner_user_id": owner_user_id or None,
    }

def _api_partner_key_fingerprints(api_key: str, key_data: dict | None = None) -> set[str]:
    fingerprints = {_api_key_fingerprint(api_key)}
    cursor = key_data if isinstance(key_data, dict) else _api_normalize_partner_key(api_key)
    seen = {str(api_key or "")}
    for _ in range(20):
        previous = str((cursor or {}).get("rotated_from") or "").strip()
        if not previous or previous in seen:
            break
        seen.add(previous)
        fingerprints.add(_api_key_fingerprint(previous))
        cursor = _api_normalize_partner_key(previous)
    return fingerprints


def _api_order_belongs_to_actor(order_data: dict, actor: dict) -> bool:
    if actor.get("is_admin"):
        return True
    key_hash = str(order_data.get("api_partner_key_hash") or "")
    return bool(key_hash and key_hash in _api_partner_key_fingerprints(actor.get("api_key"), actor.get("key_data")))

def _api_is_order_record(order_data: dict) -> bool:
    if not isinstance(order_data, dict):
        return False
    user_id = str(order_data.get("user_id") or "")
    if user_id.startswith("PARTNER_"):
        return True
    if str(order_data.get("source") or "").strip() == "developer_api_v2":
        return True
    if str(order_data.get("api_partner_ref") or "").strip():
        return True
    if str(order_data.get("api_partner_key_hash") or "").strip():
        return True
    if str(order_data.get("coupon_used") or "").startswith("API-"):
        return True
    return False

def _api_build_actor_for_partner(api_key: str, key_data: dict | None = None):
    normalized = key_data if isinstance(key_data, dict) else _api_normalize_partner_key(api_key)
    if not isinstance(normalized, dict):
        return None
    balance_value = _api_get_partner_display_balance(api_key, normalized)
    partner_name = str(normalized.get("name") or "Unknown")
    try:
        owner_user_id = int(normalized.get("user_id", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        owner_user_id = 0
    return {
        "api_key": api_key,
        "is_admin": False,
        "partner_name": partner_name,
        "key_data": normalized,
        "balance": balance_value,
        "key_fingerprint": _api_key_fingerprint(api_key),
        "owner_user_id": owner_user_id or None,
    }

def _api_get_orders_for_actor(
    actor: dict,
    limit: int | None = None,
    offset: int = 0,
    status_filter: str | None = None,
    search: str | None = None,
    social_only: bool | None = None,
):
    safe_offset = max(0, int(offset or 0))
    normalized_status = str(status_filter or "").strip().lower()
    normalized_search = str(search or "").strip().lower()
    matched_orders = []

    for order in reversed(order_history):
        if not _api_is_order_record(order):
            continue
        if not _api_order_belongs_to_actor(order, actor):
            continue
        is_social_order = bool(order.get("is_social_source_service"))
        if social_only is not None and is_social_order != social_only:
            continue

        raw_status = str(order.get("status") or "").strip().lower()
        pretty_status = status_text(order.get("status")).lower()
        if normalized_status and normalized_status not in raw_status and normalized_status not in pretty_status:
            continue

        if normalized_search:
            searchable_fields = (
                order.get("order_code"),
                order.get("api_partner_ref"),
                order.get("product_id"),
                order.get("product_name"),
                order.get("api_customer_email") or order.get("email"),
                order.get("api_customer_id"),
                order.get("api_note"),
                order.get("link"),
            )
            if not any(normalized_search in str(field or "").lower() for field in searchable_fields):
                continue

        matched_orders.append(order)

    total_count = len(matched_orders)
    if limit is None:
        return matched_orders[safe_offset:], total_count

    safe_limit = max(1, min(API_V2_MAX_HISTORY_LIMIT, int(limit or 1)))
    return matched_orders[safe_offset:safe_offset + safe_limit], total_count

def _api_get_orders_for_user(user_id: int):
    partner_key, partner_data = get_partner_api_entry_by_user(user_id)
    if not partner_key or not isinstance(partner_data, dict):
        return []
    actor = _api_build_actor_for_partner(partner_key, partner_data)
    if not actor:
        return []
    orders, _ = _api_get_orders_for_actor(actor, limit=None)
    return orders

def _api_user_can_access_order(user_id: int, order_data: dict) -> bool:
    if user_id == ADMIN_USER_ID:
        return True
    if str(order_data.get("user_id")) == str(user_id):
        return True
    effective_uid = _api_get_effective_order_user_id(order_data)
    if effective_uid and str(effective_uid) == str(user_id):
        return True
    if not _api_is_order_record(order_data):
        return False
    partner_key, partner_data = get_partner_api_entry_by_user(user_id)
    if not partner_key or not isinstance(partner_data, dict):
        return False
    actor = _api_build_actor_for_partner(partner_key, partner_data)
    return bool(actor and _api_order_belongs_to_actor(order_data, actor))

def _api_get_remaining_balance(actor: dict):
    if actor.get("is_admin"):
        return "unlimited"
    latest_key = _api_normalize_partner_key(actor.get("api_key"))
    if latest_key is None:
        try:
            return int(actor.get("balance", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            return 0
    return _api_get_partner_display_balance(actor.get("api_key"), latest_key)

def _api_find_order_by_partner_ref(actor: dict, partner_ref: str):
    target_ref = _api_sanitize_partner_ref(partner_ref).upper()
    if not target_ref:
        return None
    orders = api_partner_ref_index.get(target_ref, [])
    for order in reversed(orders):
        if _api_order_belongs_to_actor(order, actor):
            return order
    return None

def _api_get_product_stock_count(product_data: dict):
    if product_data.get("is_social_source_service") or product_data.get("requires_gmail"):
        return None
    if product_data.get("is_supplier_source_resell"):
        try:
            raw_stock = int(product_data.get("supplier_source_stock", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            raw_stock = 0
        return max(0, raw_stock)
    return int(get_local_stock_available_count(product_data) or 0)

def _api_is_product_available_for_catalog(product_data: dict):
    if product_data.get("is_social_source_service"):
        try:
            minimum_quantity = int(product_data.get("ctt_min_quantity", product_data.get("ctt_package_quantity", 1)) or 1)
        except (ValueError, TypeError, KeyError, IndexError):
            minimum_quantity = 1
        return bool(SOCIAL_SOURCE_API_KEY) and not _ctt_validate_purchase_quantity(product_data, minimum_quantity)
    if product_data.get("requires_gmail"):
        return True
    if product_data.get("is_supplier_source_resell"):
        if product_data.get("supplier_source_purchase_blocked"):
            return False
        try:
            return int(product_data.get("supplier_source_stock", 0) or 0) > 0
        except (ValueError, TypeError, KeyError, IndexError):
            return False
    return int(get_local_stock_available_count(product_data) or 0) > 0

def _api_get_product_stock_status(product_data: dict):
    return "in_stock" if _api_is_product_available_for_catalog(product_data) else "out_of_stock"

def _api_store_product_payload(product_id: str, product_data: dict, actor: dict | None = None):
    unit_price, base_price, discount_type, discount_info, owner_user_id = _api_get_effective_product_price(actor, product_id, product_data)
    stock_count = _api_get_product_stock_count(product_data)
    available = _api_is_product_available_for_catalog(product_data)
    payload = {
        "product_id": product_id,
        "name": str(product_data.get("name") or product_id),
        "price": unit_price,
        "currency": "VND",
        "description": str(product_data.get("description") or ""),
        "duration": str(product_data.get("duration") or ""),
        "warranty": str(product_data.get("warranty") or ""),
        "delivery_mode": (
            "social_service"
            if product_data.get("is_social_source_service")
            else (
                "manual_fulfillment"
                if product_data.get("requires_gmail")
                else ("resell_source_api" if product_data.get("is_supplier_source_resell") else "instant_items")
            )
        ),
        "stock_status": "in_stock" if available else "out_of_stock",
        "stock_count": stock_count,
        "stock": stock_count,
        "available": available,
        "requires_gmail": bool(product_data.get("requires_gmail", False)),
        "is_supplier_source_resell": bool(product_data.get("is_supplier_source_resell", False)),
        "is_social_source_service": bool(product_data.get("is_social_source_service", False)),
    }
    if product_data.get("is_social_source_service"):
        payload["warranty_supported"] = bool(product_data.get("ctt_refill"))
        payload["warranty_time"] = str(product_data.get("ctt_warranty_time") or "")
        minimum_quantity = int(product_data.get("ctt_min_quantity", product_data.get("ctt_package_quantity", 1)) or 1)
        payload["service_package_quantity"] = minimum_quantity
        payload["service_units_per_package"] = 1
        payload["minimum_order_quantity"] = minimum_quantity
        payload["maximum_order_quantity"] = int(product_data.get("ctt_max_quantity", 0) or 0)
        payload["pricing_model"] = str(product_data.get("ctt_pricing_model") or "per_unit")
        payload["social_input_fields"] = list(product_data.get("ctt_input_fields") or [])
        payload["supplier_service_id"] = str(product_data.get("ctt_service_id") or "")
    if base_price > unit_price:
        payload["list_price"] = base_price
        payload["discount_type"] = str(discount_type or "")
        if isinstance(discount_info, dict):
            try:
                payload["discount_percent"] = int(discount_info.get("discount_percent", 0) or 0)
            except (ValueError, TypeError, KeyError, IndexError):
                pass
        if owner_user_id:
            rank_info = get_user_rank(owner_user_id)
            payload["rank_name"] = re.sub(r"<[^>]+>", "", str(rank_info.get("rank", {}).get("name", "") or "")).strip()
    return payload


def _api_is_catalog_visible_product(product_data: dict | None):
    return bool(isinstance(product_data, dict) and _ctt_is_catalog_visible(product_data))

_API_CATALOG_CACHE = {}
_API_CATALOG_CACHE_TTL_SECONDS = 120

def _api_get_cached_catalog_payload(actor: dict | None = None, social_only: bool | None = None):
    # Stock is mutable; rebuild every request so partners never receive a stale count.
    items = []
    for pid, pdata in products.items():
        if not _api_is_catalog_visible_product(pdata):
            continue
        is_social_product = bool(pdata.get("is_social_source_service"))
        if social_only is not None and is_social_product != social_only:
            continue
        items.append(_api_store_product_payload(pid, pdata, actor=actor))
    return items

def _api_catalog_payload(
    actor: dict | None = None,
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    available_only: bool = False,
    social_only: bool | None = None,
):
    items = _api_get_cached_catalog_payload(actor, social_only=social_only)

    filtered_items = items
    search_text = str(search or "").strip().casefold()
    if search_text:
        filtered_items = [
            item for item in filtered_items
            if search_text in str(item.get("product_id") or "").casefold()
            or search_text in str(item.get("name") or "").casefold()
            or search_text in str(item.get("description") or "").casefold()
            or search_text in str(item.get("delivery_mode") or "").casefold()
        ]
    if available_only:
        filtered_items = [item for item in filtered_items if bool(item.get("available"))]

    total_filtered = len(filtered_items)
    try:
        safe_offset = max(0, int(offset or 0))
    except (ValueError, TypeError, KeyError, IndexError):
        safe_offset = 0
    try:
        requested_limit = int(limit or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        requested_limit = 0
    if limit is None or requested_limit <= 0:
        paged_items = filtered_items[safe_offset:]
        safe_limit = 0
    else:
        safe_limit = max(1, min(500, requested_limit))
        paged_items = filtered_items[safe_offset:safe_offset + safe_limit]
    return paged_items, len(items), total_filtered, safe_limit, safe_offset

def _api_status_payload(actor: dict):
    visible_product_count = sum(1 for pdata in products.values() if _api_is_catalog_visible_product(pdata))
    current_balance = _api_get_remaining_balance(actor)
    return {
        "version": API_V2_VERSION,
        "status": "online",
        "maintenance_mode": MAINTENANCE_MODE,
        "stock_count": len(available_links),
        "product_count": visible_product_count,
        "pending_orders": len(pending_orders),
        "your_balance": current_balance,
        "partner_name": actor.get("partner_name"),
        "is_admin": bool(actor.get("is_admin")),
    }

def _api_order_payload(order_data: dict, remaining_balance=None, idempotent_replay: bool = False):
    product_id = str(order_data.get("product_id") or order_data.get("api_product_id") or "")
    product_name = str(order_data.get("product_name") or "")
    product_exists = bool(product_id and isinstance(products.get(product_id), dict))
    try:
        quantity = int(order_data.get("quantity", 1) or 1)
    except (ValueError, TypeError, KeyError, IndexError):
        quantity = 1
    items = order_data.get("items")
    delivered_items = items if isinstance(items, list) else []
    payload = {
        "order_code": str(order_data.get("order_code", "")),
        "partner_ref": str(order_data.get("api_partner_ref") or ""),
        "status": str(order_data.get("status", "")),
        "price": int(order_data.get("amount", 0) or 0),
        "currency": "VND",
        "delivery_mode": str(order_data.get("delivery_method") or "unknown"),
        "link": str(order_data.get("link", "")),
        "product_id": product_id,
        "product_name": product_name,
        "quantity": quantity,
        "email": str(order_data.get("api_customer_email") or order_data.get("email") or ""),
        "created_at": int(order_data.get("timestamp", 0) or 0),
        "delivered_count": len(delivered_items),
        "idempotent_replay": bool(idempotent_replay),
    }
    if product_id:
        payload["product_deleted"] = not product_exists
    try:
        list_price = int(order_data.get("list_amount", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        list_price = 0
    if list_price > payload["price"]:
        payload["list_price"] = list_price
        payload["discount_type"] = str(order_data.get("discount_type") or "")
        try:
            payload["discount_percent"] = int(order_data.get("discount_percent", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            payload["discount_percent"] = 0
    if delivered_items:
        payload["items"] = delivered_items
    refunded_at = order_data.get("refunded_at")
    try:
        refunded_at_value = int(refunded_at or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        refunded_at_value = 0
    if refunded_at_value > 0:
        payload["refunded_at"] = refunded_at_value
        try:
            payload["refund_amount"] = int(order_data.get("refund_amount", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            payload["refund_amount"] = 0
        refund_reason = str(order_data.get("refund_reason") or "").strip()
        if refund_reason:
            payload["refund_reason"] = refund_reason
        refund_target = str(order_data.get("refund_target") or "").strip()
        if refund_target:
            payload["refund_target"] = refund_target
    try:
        auto_refunded_amount = int(order_data.get("ctt_auto_refunded_amount", 0) or 0)
    except (ValueError, TypeError, KeyError, IndexError):
        auto_refunded_amount = 0
    if auto_refunded_amount > 0:
        payload["partial_refund_amount"] = auto_refunded_amount
        payload["auto_refund_amount"] = auto_refunded_amount
        auto_refund_reason = str(order_data.get("ctt_auto_refund_reason") or "").strip()
        if auto_refund_reason:
            payload["auto_refund_reason"] = auto_refund_reason
        auto_refund_target = str(order_data.get("ctt_auto_refund_target") or "").strip()
        if auto_refund_target:
            payload["auto_refund_target"] = auto_refund_target
    if remaining_balance is not None:
        payload["remaining_balance"] = remaining_balance
    if order_data.get("is_social_source_service"):
        payload["is_social_source_service"] = True
        payload["target_link"] = str(order_data.get("ctt_target_link") or order_data.get("link") or "")
        payload["comments"] = str(order_data.get("ctt_comments") or "")
        payload["supplier_order_id"] = str(order_data.get("ctt_supplier_order_id") or "")
        payload["supplier_status"] = str(order_data.get("ctt_supplier_status") or "")
        try:
            payload["supplier_status_refreshed_at"] = int(order_data.get("ctt_status_refreshed_at", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            payload["supplier_status_refreshed_at"] = 0
        refresh_error = str(order_data.get("ctt_status_refresh_error") or "").strip()
        if refresh_error:
            payload["supplier_status_refresh_error"] = refresh_error
        if order_data.get("ctt_supplier_charge"):
            payload["supplier_charge"] = str(order_data.get("ctt_supplier_charge") or "")
        if order_data.get("ctt_supplier_remains"):
            payload["supplier_remains"] = str(order_data.get("ctt_supplier_remains") or "")
        if order_data.get("ctt_supplier_start_count"):
            payload["supplier_start_count"] = str(order_data.get("ctt_supplier_start_count") or "")
        try:
            payload["supplier_quantity"] = int(order_data.get("ctt_supplier_quantity", 0) or 0)
        except (ValueError, TypeError, KeyError, IndexError):
            payload["supplier_quantity"] = 0
        progress_counts = ctt_get_supplier_progress_counts(order_data)
        if progress_counts:
            payload["supplier_progress"] = progress_counts
            for source_key, payload_key in (
                ("initial_count", "supplier_initial_count"),
                ("increased_quantity", "supplier_increased_quantity"),
                ("remaining_quantity", "supplier_remaining_quantity"),
            ):
                if source_key in progress_counts:
                    payload[payload_key] = progress_counts[source_key]
    return payload

async def _api_notify_admin_order(order_data: dict, partner_name: str, remaining_balance):
    if not bot_instance or not isinstance(order_data, dict):
        return False
    if order_data.get("api_admin_notified_at"):
        return True
    try:
        balance_text = f"{remaining_balance:,} VNĐ" if isinstance(remaining_balance, int) else str(remaining_balance)
        product_name = order_data.get("product_name") or "N/A"
        quantity = int(order_data.get("quantity", 1) or 1)
        delivery_mode = order_data.get("delivery_method") or "unknown"
        link_value = str(order_data.get("link") or "")
        delivered_items = order_data.get("items")
        balance_value = order_data.get("api_partner_remaining_balance", remaining_balance)
        balance_text = f"{balance_value:,} VNĐ" if isinstance(balance_value, int) else html.escape(str(balance_value))
        sanitized_partner_name = html.escape(str(partner_name or "Unknown"))
        delivery_detail_line = ""
        preview_items = []
        if isinstance(delivered_items, list):
            preview_items = [str(item) for item in delivered_items if str(item).strip()]
        elif isinstance(delivered_items, (tuple, set)):
            preview_items = [str(item) for item in delivered_items if str(item).strip()]
        elif isinstance(delivered_items, str) and delivered_items.strip():
            preview_items = [delivered_items.strip()]
        if preview_items:
            preview_items = preview_items[:3]
            preview_text = "\n".join(
                f"• <code>{html.escape(str(item))}</code>" for item in preview_items
            )
            if isinstance(delivered_items, (list, tuple, set)) and len(delivered_items) > len(preview_items):
                preview_text += f"\n• ... và {len(delivered_items) - len(preview_items)} item khác"
            delivery_detail_line = f"<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Nội dung đã gửi:</b>\n{preview_text}\n"
        elif delivery_mode == "instant_link" and link_value:
            delivery_detail_line = f"<tg-emoji emoji-id=\"5231489647946768652\">🔗</tg-emoji> <b>Link:</b> <code>{html.escape(link_value)}</code>\n"
        admin_msg = (
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐƠN HÀNG API MỚI (V2)</b>\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Partner:</b> {partner_name}\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_data.get('order_code')}</code>\n"
            f"<tg-emoji emoji-id=\"6260059243605398502\">🏷</tg-emoji> <b>Ref:</b> <code>{order_data.get('api_partner_ref') or 'N/A'}</code>\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {html.escape(str(product_name))} x{quantity}\n"
            f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Email:</b> <code>{order_data.get('api_customer_email') or 'N/A'}</code>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Giá:</b> {int(order_data.get('amount', 0)):,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">🚚</tg-emoji> <b>Delivery:</b> <code>{delivery_mode}</code>\n"
            f"<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> <b>Số dư Partner:</b> {balance_text}\n"
            f"{delivery_detail_line}"
        )
        # Add approve/refund buttons for manual delivery API orders
        reply_markup = None
        if delivery_mode == "manual_pending":
            order_code = order_data.get('order_code', '')
            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Duyệt (Đã add)", callback_data=f"api_approve_{order_code}"),
                    InlineKeyboardButton("❌ Hoàn tiền", callback_data=f"api_refund_{order_code}"),
                ]
            ])
        sent_message = await safe_send_admin(bot_instance, admin_msg, reply_markup=reply_markup)
        if not sent_message:
            logger.warning(f"API admin notification send returned no message for order {order_data.get('order_code')}")
            return False
        order_data["api_admin_notified_at"] = time.time()
        try:
            await save_data(force=True)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as save_error:
            logger.warning(f"Không lưu được dấu đã báo admin cho đơn API {order_data.get('order_code')}: {save_error}")
        return True
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as notify_error:
        logger.error(f"Lỗi gửi thông báo Admin API V2: {notify_error}")


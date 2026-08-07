import re
import unicodedata


_DELIVERY_ACCOUNT_SECTION_MARKERS = (
    "tai khoan cua ban",
    "danh sach tai khoan",
)
_DELIVERY_METADATA_PREFIXES = (
    "ma don hang",
    "ngay mua",
    "san pham",
    "so luong",
    "thanh toan",
    "thoi han",
    "bao hanh",
    "luu y",
)


def _fold_delivery_text(value) -> str:
    plain = _plain_text_preserve_emoji(str(value or ""))
    normalized = unicodedata.normalize("NFKD", plain)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower().strip()


def _clean_delivery_line(value) -> str:
    plain = _plain_text_preserve_emoji(str(value or "")).replace("\r", "").strip()
    return re.sub(r"^\[\s*\d+\s*\]\s*", "", plain).strip()


def format_product_description_for_txt(product: dict | None, lang: str = "vi") -> str:
    if not isinstance(product, dict):
        return ""
    raw_description = (
        product.get(f"description_{lang}")
        or product.get("description")
        or product.get("shortDescription")
        or ""
    )
    plain = _plain_text_preserve_emoji(str(raw_description or ""))
    plain = re.sub(r"<[^>]+>", "", plain)
    plain = re.sub(r"\r\n?", "\n", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
    return plain


def _is_delivery_separator_line(value) -> bool:
    return bool(re.fullmatch(r"[=\-\s]{6,}", str(value or "").strip()))


def _is_delivery_metadata_line(value) -> bool:
    folded = _fold_delivery_text(value)
    return any(folded.startswith(prefix) for prefix in _DELIVERY_METADATA_PREFIXES)


def _looks_like_delivery_payload_line(raw_value, cleaned_value=None) -> bool:
    raw_text = str(raw_value or "").strip()
    cleaned = cleaned_value if cleaned_value is not None else _clean_delivery_line(raw_text)
    if not cleaned or _is_delivery_separator_line(cleaned):
        return False

    folded = _fold_delivery_text(cleaned)
    if re.match(r"^\[\s*\d+\s*\]", raw_text):
        return True
    return (
        "|" in cleaned
        or "http://" in folded
        or "https://" in folded
        or "www." in folded
        or ("@" in cleaned and " " not in cleaned)
    )


def _looks_like_supplier_summary_block(value) -> bool:
    folded = _fold_delivery_text(value)
    return (
        "thong tin don hang" in folded
        and (
            "tai khoan cua ban" in folded
            or "danh sach tai khoan" in folded
        )
    )


def normalize_delivered_items(raw_content) -> list[str]:
    """
    Normalize supplier-delivered payloads into clean account/item lines.
    This strips vendor summary templates and keeps only the actual delivered data.
    """
    normalized_items = []

    def _append_candidate(candidate) -> None:
        cleaned = _clean_delivery_line(candidate)
        if not cleaned or _is_delivery_separator_line(cleaned) or _is_delivery_metadata_line(cleaned):
            return
        normalized_items.append(cleaned)

    def _extend_from_text(value) -> None:
        plain = _plain_text_preserve_emoji(str(value or "")).replace("\r", "").strip()
        if not plain:
            return

        raw_lines = [line.strip() for line in plain.splitlines()]
        section_items = []
        saw_account_section = False

        for raw_line in raw_lines:
            cleaned = _clean_delivery_line(raw_line)
            if not cleaned or _is_delivery_separator_line(cleaned):
                continue

            folded = _fold_delivery_text(cleaned)
            if "thong tin don hang" in folded:
                continue
            if any(marker in folded for marker in _DELIVERY_ACCOUNT_SECTION_MARKERS):
                saw_account_section = True
                continue
            if folded.startswith("luu y"):
                if saw_account_section:
                    break
                continue
            if _is_delivery_metadata_line(cleaned):
                continue
            if saw_account_section:
                section_items.append(cleaned)

        if section_items:
            for item in section_items:
                _append_candidate(item)
            return

        compact_lines = []
        payload_lines = []
        separator_count = 0
        colon_count = 0
        for raw_line in raw_lines:
            if _is_delivery_separator_line(raw_line):
                separator_count += 1
            if ":" in str(raw_line):
                colon_count += 1
            cleaned = _clean_delivery_line(raw_line)
            if not cleaned or _is_delivery_separator_line(cleaned) or _is_delivery_metadata_line(cleaned):
                continue
            compact_lines.append(cleaned)
            if _looks_like_delivery_payload_line(raw_line, cleaned):
                payload_lines.append(cleaned)

        if compact_lines:
            if payload_lines and (separator_count >= 2 or colon_count >= 3 or len(raw_lines) >= 8):
                for item in payload_lines:
                    _append_candidate(item)
                return

            if _looks_like_supplier_summary_block(plain):
                for item in compact_lines:
                    folded_item = _fold_delivery_text(item)
                    if "|" in item or ":" in item or "http" in folded_item or "@" in item or len(item.split()) <= 6:
                        _append_candidate(item)
                return

            for item in compact_lines:
                _append_candidate(item)
            return

        _append_candidate(plain)

    if raw_content is None:
        return []

    if isinstance(raw_content, dict):
        for key, value in raw_content.items():
            key_text = _clean_delivery_line(key)
            value_text = _plain_text_preserve_emoji(str(value or "")).replace("\r", "").strip()
            if not key_text and not value_text:
                continue

            key_folded = _fold_delivery_text(key_text)
            if key_folded.startswith("item_") or key_text.isdigit():
                _extend_from_text(value_text)
                continue

            if value_text and ("\n" in value_text or _looks_like_supplier_summary_block(value_text)):
                before_count = len(normalized_items)
                _extend_from_text(value_text)
                if len(normalized_items) > before_count:
                    continue

            if key_text and not _is_delivery_metadata_line(key_text):
                if value_text:
                    _append_candidate(f"{key_text}|{value_text}")
                else:
                    _append_candidate(key_text)

        return list(dict.fromkeys(normalized_items))

    if isinstance(raw_content, (list, tuple, set)):
        for item in raw_content:
            if isinstance(item, dict):
                normalized_items.extend(normalize_delivered_items(item))
            else:
                _extend_from_text(item)
        return list(dict.fromkeys(normalized_items))

    _extend_from_text(raw_content)
    return list(dict.fromkeys(normalized_items))


def build_store_order_txt_content(
    order_code: str,
    product_name: str,
    quantity: int,
    amount: int,
    duration: str,
    warranty: str,
    items,
    description: str = "",
    purchase_ts: float | None = None,
) -> str:
    """Build deterministic .txt content for delivered account items."""
    ts = purchase_ts or time.time()
    purchase_date = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
    safe_items = normalize_delivered_items(items)
    lines = [
        "=" * 60,
        "THONG TIN DON HANG",
        "=" * 60,
        "",
        f"Ma don hang : {order_code}",
        f"Ngay mua    : {purchase_date}",
        f"San pham    : {product_name}",
        f"So luong    : {quantity}",
        f"Thanh toan  : {amount:,} VND",
    ]
    clean_description = str(description or "").strip()
    if clean_description:
        lines.extend(["", "Mo ta:", clean_description])
    lines.extend([
        "",
        f"Thoi han    : {duration}",
        f"Bao hanh    : {warranty}",
        "",
        "=" * 60,
        "DANH SACH TAI KHOAN",
        "=" * 60,
        "",
    ])
    for idx, item in enumerate(safe_items, 1):
        lines.append(f"{idx:03d}. {item}")
    lines.extend(["", "=" * 60])
    return "\n".join(lines)


def _chunk_delivery_lines(lines, max_chars: int = 3200, max_lines: int = 40):
    chunks = []
    current = []
    current_chars = 0
    for line in lines:
        line_len = len(line) + 1
        if current and (len(current) >= max_lines or current_chars + line_len > max_chars):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(line)
        current_chars += line_len
    if current:
        chunks.append(current)
    return chunks


async def deliver_items_as_txt(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    order_code: str,
    items,
    *,
    file_content: str,
    file_prefix: str = "DonHang",
    caption_html: str | None = None,
    reply_markup=None,
    max_attempts: int = 3,
):
    """
    Try document delivery first (with retries), then fallback to chunked plain text.
    Returns: {"delivered": bool, "method": "document|text|failed", "sent_items": int, "errors": list[str]}
    """
    safe_items = normalize_delivered_items(items)
    plain_file_content = _plain_text_preserve_emoji(str(file_content or "")).replace("\r\n", "\n").replace("\r", "\n")
    result = {"delivered": False, "method": "failed", "sent_items": 0, "errors": []}

    if not safe_items:
        result["errors"].append("no_items")
        return result

    for attempt in range(1, max_attempts + 1):
        try:
            file_obj = io.BytesIO(plain_file_content.encode("utf-8"))
            filename = f"{file_prefix}_{order_code}.txt"
            file_obj.name = filename
            file_obj.seek(0)
            send_kwargs = {"chat_id": chat_id, "document": file_obj, "filename": filename, "reply_markup": reply_markup}
            if caption_html:
                send_kwargs["caption"] = caption_html
                send_kwargs["parse_mode"] = ParseMode.HTML
            sent = await context.bot.send_document(**send_kwargs)
            if sent is not None:
                result.update({"delivered": True, "method": "document", "sent_items": len(safe_items)})
                return result
            result["errors"].append(f"document_attempt_{attempt}: empty_response")
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            result["errors"].append(f"document_attempt_{attempt}: {type(e).__name__}: {e}")
        await asyncio.sleep(min(attempt, 3))

    lines = [f"[{idx}] {item}" for idx, item in enumerate(safe_items, 1)]
    chunks = _chunk_delivery_lines(lines)
    sent_items = 0

    for chunk_idx, chunk_lines in enumerate(chunks, 1):
        chunk_body = "\n".join(chunk_lines)
        if chunk_idx == 1:
            text_payload = f"THONG TIN TAI KHOAN - Don {order_code}\n" + ("-" * 36) + f"\n{chunk_body}"
        else:
            text_payload = f"TIEP THEO ({chunk_idx}/{len(chunks)}) - Don {order_code}\n" + ("-" * 36) + f"\n{chunk_body}"
        try:
            sent_msg = await safe_send_message(context, chat_id, text_payload)
            if not sent_msg:
                result["errors"].append(f"text_chunk_{chunk_idx}: send_failed")
                break
            sent_items += len(chunk_lines)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            result["errors"].append(f"text_chunk_{chunk_idx}: {type(e).__name__}: {e}")
            break

    result["sent_items"] = sent_items
    if sent_items == len(safe_items):
        await safe_send_message(
            context,
            chat_id,
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không gửi được file .txt, hệ thống đã gửi dạng tin nhắn. Vui lòng lưu lại ngay.",
            reply_markup=reply_markup,
        )
        result.update({"delivered": True, "method": "text"})
        return result

    return result

async def generate_unique_order_code(prefix="ICLD", length=6, charset: str = '0123456789', extra_reserved=None):
    """
    FIX BUG #13: Generate Unique Order Code với collision detection
    Detect collision trong cả pending_orders và order_history
    """
    max_attempts = 10
    for _ in range(max_attempts):
        random_digits = ''.join(random.choices(charset, k=length))
        code = f"{prefix}{random_digits}"

        async with pending_orders_lock:
            if code in pending_orders or code in reserved_order_codes:
                continue
            if code in order_index:
                continue
            if extra_reserved and code in extra_reserved:
                continue
            reserved_order_codes.add(code)
            return code
    
    # Fallback vẫn phải giữ đúng format ICLD + 6 số để các regex parser hoạt động.
    for _ in range(100):
        if charset == '0123456789':
            fallback_digits = str(int(time.time() * 1000) % (10 ** length)).zfill(length)
        else:
            fallback_digits = ''.join(random.choices(charset, k=length))
        code = f"{prefix}{fallback_digits}"
        async with pending_orders_lock:
            if code in pending_orders or code in reserved_order_codes:
                pass
            elif code in order_index:
                pass
            elif extra_reserved and code in extra_reserved:
                pass
            else:
                reserved_order_codes.add(code)
                return code
        await asyncio.sleep(0.001)
    raise RuntimeError("Cannot generate unique order code")


_warranty_fallback_products_cache = None


def _fold_warranty_policy_text(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    variants = [raw]
    try:
        decoded = raw.encode("latin1").decode("utf-8")
        if decoded and decoded != raw:
            variants.append(decoded)
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
        pass

    folded_variants = []
    for variant in variants:
        normalized = unicodedata.normalize("NFKD", variant)
        folded = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        folded = folded.replace("đ", "d").replace("Đ", "D").casefold()
        folded = re.sub(r"\s+", " ", folded).strip()
        if folded:
            folded_variants.append(folded)
    return " ".join(dict.fromkeys(folded_variants))


def _load_warranty_fallback_products_catalog() -> dict:
    global _warranty_fallback_products_cache

    if isinstance(_warranty_fallback_products_cache, dict):
        return _warranty_fallback_products_cache

    import json as _json
    import os as _os

    base_dir = _os.path.dirname(__file__)
    app_dir = _os.path.dirname(base_dir)
    project_dir = _os.path.dirname(app_dir)
    candidate_paths = (
        _os.path.join(app_dir, "handlers", "data_products.json"),
        _os.path.join(project_dir, "data_products.json"),
    )

    for candidate_path in candidate_paths:
        try:
            if not _os.path.exists(candidate_path):
                continue
            with open(candidate_path, "r", encoding="utf-8") as handle:
                loaded = _json.load(handle)
            if isinstance(loaded, dict):
                _warranty_fallback_products_cache = loaded
                return _warranty_fallback_products_cache
        except (OSError, ValueError, TypeError):
            continue

    _warranty_fallback_products_cache = {}
    return _warranty_fallback_products_cache


def _parse_warranty_duration_seconds(text: str) -> int:
    folded = _fold_warranty_policy_text(text)
    if not folded:
        return 0

    unit_multipliers = (
        (365 * 24 * 60 * 60, ("nam", "year", "years")),
        (30 * 24 * 60 * 60, ("thang", "month", "months")),
        (7 * 24 * 60 * 60, ("tuan", "week", "weeks")),
        (24 * 60 * 60, ("ngay", "day", "days")),
        (60 * 60, ("gio", "tieng", "hour", "hours")),
    )
    for multiplier, units in unit_multipliers:
        for unit in units:
            match = re.search(rf"(\d+)\s*{re.escape(unit)}\b", folded)
            if match:
                return int(match.group(1)) * multiplier

    hour_match = re.search(r"\b(\d+)\s*h\b", folded)
    if hour_match:
        return int(hour_match.group(1)) * 60 * 60

    return 0


def _resolve_warranty_product(order: dict):
    if not isinstance(order, dict):
        return "", None

    product_id = str(order.get("product_id") or "").strip()
    if product_id:
        product = products.get(product_id) if isinstance(products, dict) else None
        if isinstance(product, dict):
            return product_id, product
        fallback_product = _load_warranty_fallback_products_catalog().get(product_id)
        if isinstance(fallback_product, dict):
            return product_id, fallback_product

    order_name = _fold_warranty_policy_text(order.get("product_name") or order.get("product"))
    if not order_name:
        return "", None

    relaxed_matches = []
    catalogs = []
    if isinstance(products, dict):
        catalogs.append(products)
    catalogs.append(_load_warranty_fallback_products_catalog())
    for catalog in catalogs:
        for current_product_id, product in catalog.items():
            if not isinstance(product, dict):
                continue
            product_name = _fold_warranty_policy_text(product.get("name"))
            if not product_name:
                continue
            if product_name == order_name:
                return current_product_id, product
            if order_name in product_name or product_name in order_name:
                relaxed_matches.append((current_product_id, product))

    if len(relaxed_matches) == 1:
        return relaxed_matches[0]
    return "", None


def resolve_order_warranty_info(order: dict, now_ts: float | None = None) -> dict:
    now_value = float(now_ts or time.time())
    if not isinstance(order, dict):
        return {"known": False, "expired": False, "reason": "invalid_order"}

    product_id, product = _resolve_warranty_product(order)
    warranty_text = str(
        order.get("warranty")
        or (product or {}).get("warranty")
        or ""
    ).strip()
    duration_text = str(
        order.get("duration")
        or (product or {}).get("duration")
        or ""
    ).strip()

    expires_at = order.get("warranty_expires")
    try:
        expires_at = float(expires_at) if expires_at not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        expires_at = None

    if expires_at:
        return {
            "known": True,
            "expired": now_value >= expires_at,
            "reason": "stored_expiry",
            "expires_at": expires_at,
            "warranty_text": warranty_text,
            "duration_text": duration_text,
            "product_id": product_id,
        }

    purchase_ts = order.get("timestamp") or order.get("created_at")
    try:
        purchase_ts = float(purchase_ts or 0)
    except (TypeError, ValueError):
        purchase_ts = 0

    folded_warranty = _fold_warranty_policy_text(warranty_text)
    if not folded_warranty:
        return {
            "known": False,
            "expired": False,
            "reason": "missing_warranty_text",
            "warranty_text": warranty_text,
            "duration_text": duration_text,
            "product_id": product_id,
        }

    if folded_warranty in {"khong", "none", "n/a", "na"} or any(
        token in folded_warranty for token in ("khong bao hanh", "khong bh", "no warranty")
    ):
        return {
            "known": True,
            "expired": True,
            "reason": "no_warranty",
            "expires_at": purchase_ts or None,
            "warranty_text": warranty_text,
            "duration_text": duration_text,
            "product_id": product_id,
        }

    if any(token in folded_warranty for token in ("vinh vien", "lifetime", "forever", "permanent")):
        return {
            "known": True,
            "expired": False,
            "reason": "lifetime_warranty",
            "expires_at": None,
            "warranty_text": warranty_text,
            "duration_text": duration_text,
            "product_id": product_id,
        }

    seconds = _parse_warranty_duration_seconds(warranty_text)
    if seconds <= 0 and any(token in folded_warranty for token in ("full thoi han", "full thoi gian", "full time", "suot thoi gian")):
        seconds = _parse_warranty_duration_seconds(duration_text)

    if seconds <= 0 or purchase_ts <= 0:
        return {
            "known": False,
            "expired": False,
            "reason": "unparsed_warranty_text",
            "warranty_text": warranty_text,
            "duration_text": duration_text,
            "product_id": product_id,
        }

    expires_at = purchase_ts + seconds
    return {
        "known": True,
        "expired": now_value >= expires_at,
        "reason": "derived_from_catalog",
        "expires_at": expires_at,
        "warranty_text": warranty_text,
        "duration_text": duration_text,
        "product_id": product_id,
    }


def apply_auto_reject_if_warranty_expired(order: dict, now_ts: float | None = None) -> dict:
    info = resolve_order_warranty_info(order, now_ts=now_ts)
    if not isinstance(order, dict) or not info.get("expired"):
        return info

    now_value = int(now_ts or time.time())
    order["support_status"] = "rejected_expired"
    order["support_rejected_at"] = now_value
    order["support_reject_reason"] = "auto_warranty_expired"
    if info.get("expires_at"):
        order["warranty_expires"] = info["expires_at"]
    if info.get("warranty_text"):
        order["support_warranty_text"] = info["warranty_text"]
    return info


def _format_warranty_expiry_text(timestamp_value) -> str:
    try:
        return datetime.fromtimestamp(float(timestamp_value)).strftime("%H:%M %d/%m/%Y")
    except (TypeError, ValueError, OSError, OverflowError):
        return "N/A"


def build_auto_warranty_rejection_text(order_code: str, warranty_info: dict) -> str:
    reason = str((warranty_info or {}).get("reason") or "")
    warranty_text = str((warranty_info or {}).get("warranty_text") or "N/A")
    expires_at = (warranty_info or {}).get("expires_at")
    expiry_line = ""
    if expires_at:
        expiry_line = f"\n{E_CALENDAR} <b>Het han:</b> {_format_warranty_expiry_text(expires_at)}"

    if reason == "no_warranty":
        detail = "Don hang nay khong co chinh sach bao hanh."
    else:
        detail = "Don hang nay da het han bao hanh."

    return (
        f"{E_LIMIT} <b>TU CHOI HO TRO</b>\n\n"
        f"{detail}\n"
        f"<b>Ma don:</b> <code>{html.escape(str(order_code or ''))}</code>\n"
        f"{E_SHIELD} <b>Bao hanh:</b> {html.escape(warranty_text)}"
        f"{expiry_line}\n\n"
        "<i>He thong da tu dong tu choi yeu cau nay de tranh gui lap lai cho admin.</i>"
    )


def is_under_warranty(order):
    """
    Kiểm tra xem đơn hàng còn trong thời gian bảo hành không
    Args:
        order: dict chứa thông tin đơn hàng (phải có 'warranty_expires' hoặc 'timestamp')
    Returns:
        bool: True nếu còn bảo hành, False nếu hết
    """
    # Ưu tiên check warranty_expires nếu có
    warranty_expires = order.get('warranty_expires')
    
    if warranty_expires:
        return time.time() < warranty_expires
    
    # Fallback: Tính từ timestamp nếu không có warranty_expires
    # Giả định 20 ngày bảo hành mặc định
    timestamp = order.get('timestamp', 0)
    if timestamp:
        default_warranty_days = 20
        expiry = timestamp + (default_warranty_days * 24 * 60 * 60)
        return time.time() < expiry
    
    # Nếu không có thông tin gì, coi như hết bảo hành
    return False

def get_warranty_status_text(order):
    """
    Lấy text mô tả trạng thái bảo hành
    Returns: tuple (status_emoji, status_text, days_left)
    """
    warranty_expires = order.get('warranty_expires')
    
    if not warranty_expires:
        # Fallback: tính từ timestamp
        timestamp = order.get('timestamp', 0)
        if timestamp:
            warranty_expires = timestamp + (20 * 24 * 60 * 60)
        else:
            return (E_LIMIT, "Hết bảo hành", 0)
    
    time_left = warranty_expires - time.time()
    
    if time_left <= 0:
        return (E_LIMIT, "Hết bảo hành", 0)
    
    days_left = int(time_left / (24 * 60 * 60))
    
    if days_left > 14:
        return (E_SUCCESS, f"Còn {days_left} ngày", days_left)
    elif days_left > 7:
        return (E_ERROR, f"Còn {days_left} ngày", days_left)
    elif days_left > 0:
        return ("<tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji>", f"Còn {days_left} ngày (sắp hết)", days_left)
    else:
        hours_left = int(time_left / 3600)
        return ("<tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji>", f"Còn {hours_left} giờ (sắp hết)", 0)


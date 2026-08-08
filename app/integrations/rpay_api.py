# --- RPAY USDT INTEGRATION ---
# Cong thanh toan USDT duy nhat cua shop. Thay hoan toan Binance Pay / Binance
# Spot / quet vi BEP20 trong RPC truoc day.
#
# Duong chinh la callback: RPay POST ve /webhook/rpay ngay khi hoa don
# completed. Poll (rpay_poll_pending_invoices) chi la du phong doi soat lai khi
# callback bi mat (VPS restart, mang loi, chua tro domain).
#
# Ca hai duong deu chuan hoa ve cung 1 dang {"transactionID", "description",
# "amount"} roi nap vao pipeline khop-don/cong-tien co san trong
# app/jobs/payment_monitor.py (check_payment_job) - giong het cach sepay_api
# dang lam. Nho vay 1 hoa don thay 2 lan (callback + poll) van chi duoc cong 1
# lan, vi db_claim_transaction() khoa theo transactionID duy nhat.
#
# Quan trong ve bao mat: RPay khong ky HMAC callback, no chi gui lai
# merchant_id/api_key trong body. Vi vay:
#   1. api_key duoc so sanh bang hmac.compare_digest, khong bao gio log ra.
#   2. So tien cong cho khach LUON lay tu don pending cua ta, khong bao gio lay
#      tu payload callback - nguoi ngoai doan duoc order_code cung khong tu dat
#      duoc so tien.
#   3. request_id la bi mat ngau nhien gan vao don, callback phai khop dung.

# Hang doi hoa don RPay da xac nhan qua callback, cho payment_monitor rut ra
# moi vong quet. Single-process asyncio, khong co await xen giua append/drain
# nen khong can lock.
rpay_callback_inbox: list = []

RPAY_INVOICE_PATH = "/AddInvoice"
RPAY_STATUS_PATH = "/GetInvoiceStatus"
RPAY_HISTORY_PATH = "/GetInvoiceHistory"
RPAY_NETWORKS_PATH = "/GetNetworks"


def is_rpay_enabled() -> bool:
    """RPay chi bat khi co du merchant_id + api_key va khong bi tat bang env."""
    return bool(ENABLE_PAYMENT_RPAY and RPAY_MERCHANT_ID and RPAY_API_KEY)


def rpay_normalize_ref(trans_id) -> str:
    return f"RPAY{trans_id}"


def rpay_build_request_id(order_code: str) -> str:
    """`<order_code>:<bi mat 32 hex>`.

    Order code (ICLD######) doan duoc, nen phan bi mat moi la thu xac minh
    callback that su. Giu order_code o dau de tra don O(1) khi callback ve.
    """
    import secrets

    return f"{order_code}:{secrets.token_hex(16)}"


def rpay_order_code_from_request_id(request_id) -> str:
    return str(request_id or "").split(":", 1)[0].strip()


def _rpay_decimal(raw, default=None):
    """'12.001' / 12.001 / None -> Decimal. Loi -> default."""
    try:
        text = str(raw if raw is not None else "").strip()
        if not text:
            return default
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return default


def rpay_callback_url() -> str:
    """URL RPay se POST ket qua ve.

    Uu tien RPAY_CALLBACK_URL cau hinh tay (domain that qua Caddy). Neu trong
    thi bam theo PUBLIC_API_URL. Khong co ca hai -> tra "" va rpay_create_invoice
    tao hoa don khong callback; luc do chi con duong poll doi soat.
    """
    configured = str(RPAY_CALLBACK_URL or "").strip().rstrip("/")
    if configured:
        return configured
    base = str(PUBLIC_API_URL or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/webhook/rpay"


async def _rpay_request(path: str, payload: dict) -> dict:
    """POST form-encoded len RPay va tra ve khoi `data`.

    RPay tra {"data": {...}, "status": "success"|"error", "msg": "..."}. Bat ky
    status khac success deu raise RuntimeError de caller hoan tien/bao loi.
    """
    import httpx

    body = {
        "merchant_id": RPAY_MERCHANT_ID,
        "api_key": RPAY_API_KEY,
    }
    body.update({key: value for key, value in payload.items() if value not in (None, "")})

    url = f"{RPAY_API_BASE_URL}{path}"
    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=RPAY_TIMEOUT_SECONDS)
    owns_client = client is not http_client
    try:
        response = await client.post(url, data=body, timeout=RPAY_TIMEOUT_SECONDS)
        response_text = response.text
        try:
            data = response.json()
        except ValueError:
            data = {}
    finally:
        if owns_client:
            await client.aclose()

    if not isinstance(data, dict):
        data = {}
    if response.status_code >= 400:
        message = str(data.get("msg") or response_text or f"HTTP {response.status_code}").strip()
        raise RuntimeError(f"RPay {path} HTTP {response.status_code}: {message[:300]}")
    if str(data.get("status") or "").strip().lower() != "success":
        message = str(data.get("msg") or "request failed").strip()
        raise RuntimeError(f"RPay {path} error: {message[:300]}")
    return data.get("data") or {}


async def rpay_create_invoice(
    *,
    order_code: str,
    request_id: str,
    amount_usdt,
    name: str,
    description: str = "",
    expire_minutes: int | None = None,
) -> dict:
    """Tao hoa don USDT. Raise neu RPay tu choi hoac mang loi."""
    if not is_rpay_enabled():
        raise RuntimeError("RPay chua duoc cau hinh (RPAY_MERCHANT_ID / RPAY_API_KEY)")

    amount = _rpay_decimal(amount_usdt)
    if amount is None or amount <= 0:
        raise ValueError("RPay amount must be greater than 0")

    minutes = int(expire_minutes or (ORDER_EXPIRATION_SECONDS // 60) or 1)
    minutes = max(1, min(1440, minutes))

    callback_url = rpay_callback_url()
    if not callback_url:
        # RPay coi callback_url la bat buoc, nen thieu no thi AddInvoice se bi
        # tu choi. Bao ro nguyen nhan thay vi de loi RPay chung chung noi len.
        logger.error(
            "RPay: chua co callback URL. Dat RPAY_CALLBACK_URL hoac PUBLIC_API_URL "
            "(vd https://shop.example/webhook/rpay)."
        )

    payload = {
        "name": str(name or order_code)[:255],
        "description": str(description or "")[:255],
        "amount": format(amount, "f"),
        "token": RPAY_TOKEN,
        "network": RPAY_NETWORK,
        "address": RPAY_WALLET_ADDRESS,
        "expireMinutes": str(minutes),
        "request_id": request_id,
        "callback_url": callback_url,
    }
    data = await _rpay_request(RPAY_INVOICE_PATH, payload)
    if not str(data.get("trans_id") or "").strip():
        raise RuntimeError("RPay AddInvoice khong tra ve trans_id")
    return data


async def rpay_get_invoice_status(trans_id: str) -> dict:
    if not is_rpay_enabled():
        return {}
    if not str(trans_id or "").strip():
        raise ValueError("trans_id is required")
    return await _rpay_request(RPAY_STATUS_PATH, {"trans_id": str(trans_id).strip()})


async def rpay_get_networks() -> list:
    """Danh sach network/token RPay dang bat. Dung cho lenh admin kiem tra."""
    data = await _rpay_request(RPAY_NETWORKS_PATH, {})
    items = data.get("items")
    return items if isinstance(items, list) else []


def rpay_verify_credentials(body: dict) -> bool:
    """So khop merchant_id + api_key trong callback body.

    RPay khong ky HMAC, day la toan bo thu xac thuc no gui. Chua cau hinh key
    -> luon False (fail-safe: tha mat callback con hon de ho endpoint cong tien).
    """
    import hmac

    expected_key = str(RPAY_API_KEY or "").strip()
    expected_merchant = str(RPAY_MERCHANT_ID or "").strip()
    if not expected_key or not expected_merchant:
        logger.error("RPay callback: chua dat RPAY_MERCHANT_ID/RPAY_API_KEY -> tu choi request")
        return False
    if not isinstance(body, dict):
        return False
    provided_key = str(body.get("api_key") or "").strip()
    provided_merchant = str(body.get("merchant_id") or "").strip()
    if not provided_key or not provided_merchant:
        return False
    return hmac.compare_digest(provided_key, expected_key) and hmac.compare_digest(
        provided_merchant, expected_merchant
    )


def rpay_match_pending_invoice(request_id: str, trans_id: str):
    """Tim don pending khop `request_id` bi mat va `trans_id` da luu.

    Tra (order_code, details) hoac (None, None). Doc truc tiep pending_orders
    (khong qua lock) vi chi doc, va callback chay cung event loop.
    """
    import hmac

    order_code = rpay_order_code_from_request_id(request_id)
    if not order_code:
        return None, None
    details = pending_orders.get(order_code)
    if not isinstance(details, dict):
        return None, None
    if details.get("provider") != "rpay":
        return None, None

    stored_request_id = str(details.get("rpay_request_id") or "").strip()
    if not stored_request_id or not hmac.compare_digest(stored_request_id, str(request_id or "").strip()):
        return None, None

    stored_trans_id = str(details.get("rpay_trans_id") or "").strip()
    if stored_trans_id and stored_trans_id != str(trans_id or "").strip():
        return None, None
    return order_code, details


def rpay_normalize_completed_invoice(payload: dict) -> dict | None:
    """Chuan hoa 1 hoa don RPay `completed` ve dang chung cua pipeline.

    Nhan duoc ca payload callback lan payload GetInvoiceStatus (cung khoa).
    Tra None neu chua completed / khong khop don / thieu tien.

    So tien tra ve LUON la VND cua don pending, khong bao gio lay tu payload.
    """
    if not isinstance(payload, dict):
        return None
    if str(payload.get("status") or "").strip().lower() != "completed":
        return None

    trans_id = str(payload.get("trans_id") or "").strip()
    request_id = str(payload.get("request_id") or "").strip()
    if not trans_id or not request_id:
        return None

    order_code, details = rpay_match_pending_invoice(request_id, trans_id)
    if not order_code:
        logger.warning("RPay: hoa don %s khong khop don pending nao", trans_id)
        return None

    expected_usdt = _rpay_decimal(details.get("rpay_amount"))
    received_usdt = _rpay_decimal(payload.get("received"), Decimal("0"))
    if expected_usdt is None or expected_usdt <= 0:
        logger.error("RPay: don %s thieu rpay_amount da luu -> bo qua", order_code)
        return None
    if received_usdt < (expected_usdt - RPAY_UNDERPAY_TOLERANCE):
        logger.warning(
            "RPay: don %s nhan thieu (%s < %s USDT) -> cho doi soat tay",
            order_code,
            received_usdt,
            expected_usdt,
        )
        return None

    expected_vnd = int(details.get("amount", 0) or 0)
    if expected_vnd <= 0:
        return None

    return {
        "transactionID": rpay_normalize_ref(trans_id),
        "description": order_code,
        "amount": expected_vnd,
    }


async def rpay_poll_pending_invoices() -> list:
    """Doi soat lai: hoi GetInvoiceStatus cho tung don RPay dang cho.

    Chi de vet hoa don callback bi sot. Loi mang -> bo qua don do, khong lam
    gian doan cac scan khac.
    """
    if not is_rpay_enabled():
        return []

    results = []
    for order_code, details in list(pending_orders.items()):
        if not isinstance(details, dict):
            continue
        if details.get("provider") != "rpay" or details.get("status") != "pending_payment":
            continue
        trans_id = str(details.get("rpay_trans_id") or "").strip()
        if not trans_id:
            continue
        if db_check_tx_exists(rpay_normalize_ref(trans_id)):
            continue
        try:
            data = await rpay_get_invoice_status(trans_id)
        except Exception as e:
            logger.warning(f"RPay poll {order_code} ({trans_id}) failed: {e}")
            continue
        normalized = rpay_normalize_completed_invoice(data)
        if normalized:
            results.append(normalized)
    return results

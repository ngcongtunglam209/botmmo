# --- GPMPAY INTEGRATION (docs.gpmpay.com) ---
# Webhook la duong chinh (GPM Pay push giao dich ve trong 1-2 giay).
# Poll (gpmpay_fetch_history) chi la du phong doi soat lai: bat khi webhook bi
# mat (VPS restart, mang loi) hoac chua kip cau hinh webhook tren dashboard.
#
# Ca hai duong deu chuan hoa ve cung 1 dang {"transactionID", "description",
# "amount"} roi nap vao pipeline khop-don/cong-tien co san trong
# app/jobs/payment_monitor.py (check_payment_job) - giong het cach
# _scan_nowpayments_payments dang lam. Nho vay
# 1 giao dich thay 2 lan (webhook + poll) van chi duoc cong 1 lan, vi
# db_claim_transaction() ben duoi khoa theo transactionID duy nhat.
#
# Chi nhan giao dich source=REAL: giao dich SIMULATED (trang Simulator) ai vao
# duoc dashboard GPM Pay cung tao duoc, khong duoc phep cong tien that.

# Hang doi giao dich GPM Pay push qua webhook, cho payment_monitor rut ra moi
# vong quet (mac dinh 15s/lan). Single-process asyncio, khong co await xen
# giua append/drain nen khong can lock.
gpmpay_webhook_inbox: list = []

# Lech dong ho toi da giua timestamp trong chu ky va gio server (chong replay).
GPMPAY_SIGNATURE_TOLERANCE_SECONDS = 300
# Server chan limit o 50/trang; 10 trang = 500 giao dich trong cua so lookback.
_GPMPAY_POLL_PAGE_LIMIT = 50
_GPMPAY_POLL_MAX_PAGES = 10


def gpmpay_normalize_ref(gpmpay_transaction_id) -> str:
    return f"GPM{gpmpay_transaction_id}"


def _gpmpay_parse_amount(raw) -> int:
    """'30000' / '1,000,000' / '30000.00' / 30000 -> int VND. Loi -> 0.

    API /transactions tra `amount` dang chuoi (Prisma Decimal), webhook tra so.
    """
    if raw is None:
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    cleaned = str(raw).strip().replace(",", "").replace(" ", "")
    if not cleaned:
        return 0
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[0]
    try:
        return int(cleaned)
    except ValueError:
        return 0


def gpmpay_verify_signature(raw_body: bytes, signature_header: str | None, now: float | None = None) -> bool:
    """Xac thuc header `X-GPMPay-Signature: t=<unix>,v1=<hex>` (che do HMAC).

    v1 = HMAC_SHA256(GPMPAY_WEBHOOK_SECRET, f"{t}.{raw_body}"). Phai ky tren
    raw body, khong duoc parse JSON roi dump lai. Chua cau hinh secret -> luon
    False (fail-safe: tha mat webhook con hon de ho endpoint cong tien).
    """
    import hashlib
    import hmac
    import time

    secret = (GPMPAY_WEBHOOK_SECRET or "").strip()
    if not secret:
        logger.error("GPMPay webhook: chua dat GPMPAY_WEBHOOK_SECRET -> tu choi request")
        return False
    if not signature_header:
        return False

    parts = {}
    for item in str(signature_header).split(","):
        key, sep, val = item.strip().partition("=")
        if sep:
            parts[key.strip()] = val.strip()
    try:
        timestamp = int(parts.get("t", ""))
    except ValueError:
        return False
    signature = parts.get("v1", "").lower()
    if not signature:
        return False

    current = time.time() if now is None else now
    if abs(current - timestamp) > GPMPAY_SIGNATURE_TOLERANCE_SECONDS:
        return False

    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def gpmpay_normalize_webhook_payload(body: dict) -> dict | None:
    """Chuan hoa payload webhook GPM Pay ve dang dung chung voi cac scan crypto.

    Bo qua (tra None): goi tin xac minh `test: true` GPM Pay ban khi tao/sua
    webhook, giao dich tien ra, va giao dich SIMULATED.
    """
    if not isinstance(body, dict) or body.get("test"):
        return None
    if str(body.get("transferType") or "").strip().lower() != "in":
        return None
    if str(body.get("source") or "").strip().upper() != "REAL":
        return None
    tx_id = str(body.get("id") or "").strip()
    if not tx_id:
        return None
    amount = _gpmpay_parse_amount(body.get("transferAmount"))
    if amount <= 0:
        return None
    description = str(body.get("content") or body.get("description") or "").strip()
    return {
        "transactionID": gpmpay_normalize_ref(tx_id),
        "description": description,
        "amount": amount,
    }


async def _gpmpay_api_get(path: str, params: dict, log_label: str) -> dict | None:
    """GET mot endpoint public API cua GPM Pay. Thieu token / loi mang -> None."""
    token = (GPMPAY_API_TOKEN or "").strip()
    if not token:
        return None

    url = f"{GPMPAY_API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}

    import httpx

    try:
        client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=15.0)
        owns_client = client is not http_client
        try:
            response = await client.get(url, params=params, headers=headers)
            payload = response.json() if response.status_code == 200 else None
            if response.status_code != 200:
                logger.warning(f"GPMPay API {log_label} HTTP {response.status_code}")
        finally:
            if owns_client:
                await client.aclose()
    except Exception as e:
        logger.warning(f"GPMPay API {log_label} request failed: {e}")
        return None

    return payload if isinstance(payload, dict) else None


def gpmpay_parse_transactions_page(payload: dict | None) -> tuple[list, int]:
    """Boc envelope {"data": {"data": [...], "meta": {...}}} cua GET /transactions.

    Tra (giao dich da chuan hoa, totalPages).
    """
    page = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(page, dict):
        return [], 0
    raw_list = page.get("data") or []
    if not isinstance(raw_list, list):
        return [], 0
    meta = page.get("meta") if isinstance(page.get("meta"), dict) else {}
    try:
        total_pages = int(meta.get("totalPages") or 0)
    except (TypeError, ValueError):
        total_pages = 0

    results = []
    for tx in raw_list:
        if not isinstance(tx, dict):
            continue
        if str(tx.get("type") or "").upper() != "IN" or str(tx.get("source") or "").upper() != "REAL":
            continue
        tx_id = str(tx.get("id") or "").strip()
        amount = _gpmpay_parse_amount(tx.get("amount"))
        if not tx_id or amount <= 0:
            continue
        results.append({
            "transactionID": gpmpay_normalize_ref(tx_id),
            "description": str(tx.get("transferContent") or ""),
            "amount": amount,
        })
    return results, total_pages


async def gpmpay_fetch_history(lookback_minutes: int | None = None) -> list:
    """Doi soat lai: GET /transactions?type=IN&source=REAL&startDate=...

    Chi dung de vet giao dich webhook bi sot. Loi mang/thieu token -> tra []
    (caller tu log, khong lam gian doan cac scan khac).
    """
    import datetime

    window_minutes = lookback_minutes or GPMPAY_POLL_LOOKBACK_MINUTES
    start = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=window_minutes)
    params = {
        "type": "IN",
        "source": "REAL",
        "startDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": str(_GPMPAY_POLL_PAGE_LIMIT),
        "sortBy": "createdAt",
        "sortOrder": "desc",
    }

    results: list = []
    for page_no in range(1, _GPMPAY_POLL_MAX_PAGES + 1):
        payload = await _gpmpay_api_get("/transactions", {**params, "page": str(page_no)}, "poll")
        items, total_pages = gpmpay_parse_transactions_page(payload)
        results.extend(items)
        if page_no >= total_pages:
            break
    return results

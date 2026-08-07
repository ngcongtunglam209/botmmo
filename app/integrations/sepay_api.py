# --- SEPAY INTEGRATION ---
# Webhook la duong chinh (SePay tu push giao dich ve, gan nhu tuc thi).
# Poll (sepay_fetch_history) chi la du phong doi soat lai: bat khi webhook bi
# mat (VPS restart, mang loi) hoac chua kip cau hinh webhook tren dashboard.
#
# Ca hai duong deu chuan hoa ve cung 1 dang {"transactionID", "description",
# "amount"} roi nap vao pipeline khop-don/cong-tien co san trong
# app/jobs/payment_monitor.py (check_payment_job) - giong het cach
# _scan_usdt_bep20_payments / _scan_binance_pay_payments dang lam. Nho vay
# 1 giao dich thay 2 lan (webhook + poll) van chi duoc cong 1 lan, vi
# db_claim_transaction() ben duoi khoa theo transactionID duy nhat.

# Hang doi giao dich SePay push qua webhook, cho payment_monitor rut ra moi
# vong quet (mac dinh 15s/lan). Single-process asyncio, khong co await xen
# giua append/drain nen khong can lock.
sepay_webhook_inbox: list = []


def sepay_normalize_ref(sepay_transaction_id) -> str:
    return f"SEPAY{sepay_transaction_id}"


def _sepay_parse_amount(raw) -> int:
    """'30000' / '1,000,000' / '30000.00' / 30000 -> int VND. Loi -> 0."""
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


def sepay_verify_webhook_key(auth_header: str | None) -> bool:
    """Xac thuc header `Authorization: Apikey <SEPAY_WEBHOOK_API_KEY>`.

    Chua cau hinh key -> luon False (fail-safe: tha mat webhook con hon de ho
    endpoint cong tien cho nguoi la).
    """
    import hmac

    expected = (SEPAY_WEBHOOK_API_KEY or "").strip()
    if not expected:
        logger.error("SePay webhook: chua dat SEPAY_WEBHOOK_API_KEY -> tu choi request")
        return False
    if not auth_header:
        return False
    provided = auth_header.strip()
    if provided.startswith("Apikey "):
        provided = provided[len("Apikey "):].strip()
    elif provided.startswith("Bearer "):
        provided = provided[len("Bearer "):].strip()
    return hmac.compare_digest(provided, expected)


def sepay_normalize_webhook_payload(body: dict) -> dict | None:
    """Chuan hoa payload webhook SePay ve dang dung chung voi mbbank/crypto scan.

    Chi nhan giao dich tien VAO (`transferType == "in"`). Tra None neu bo qua.
    """
    if not isinstance(body, dict):
        return None
    if str(body.get("transferType") or "").strip().lower() != "in":
        return None
    tx_id = str(body.get("id") or "").strip()
    if not tx_id:
        return None
    amount = _sepay_parse_amount(body.get("transferAmount"))
    if amount <= 0:
        return None
    description = str(
        body.get("content") or body.get("code") or body.get("description") or ""
    ).strip()
    return {
        "transactionID": sepay_normalize_ref(tx_id),
        "description": description,
        "amount": amount,
    }


async def sepay_fetch_history(limit: int = 200, lookback_minutes: int | None = None) -> list:
    """Doi soat lai (docs.sepay.vn -> API Giao dich): GET /userapi/transactions/list.

    Chi dung de vet giao dich webhook bi sot. Loi mang/thieu token -> tra []
    (caller tu log, khong lam gian doan cac scan khac).
    """
    import datetime

    token = (SEPAY_API_TOKEN or "").strip()
    if not token:
        return []

    window_minutes = lookback_minutes or SEPAY_POLL_LOOKBACK_MINUTES
    date_min = (datetime.datetime.now() - datetime.timedelta(minutes=window_minutes)).strftime("%Y-%m-%d")
    params = {"limit": str(limit), "transaction_date_min": date_min}
    if SEPAY_ACCOUNT_NUMBER:
        params["account_number"] = SEPAY_ACCOUNT_NUMBER
    url = f"{SEPAY_API_BASE_URL}/userapi/transactions/list"
    headers = {"Authorization": f"Bearer {token}"}

    import httpx

    try:
        client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=15.0)
        owns_client = client is not http_client
        try:
            response = await client.get(url, params=params, headers=headers)
            payload = response.json() if response.status_code == 200 else None
        finally:
            if owns_client:
                await client.aclose()
    except Exception as e:
        logger.warning(f"SePay API poll request failed: {e}")
        return []

    if not isinstance(payload, dict):
        return []
    raw_list = payload.get("transactions") or []
    if not isinstance(raw_list, list):
        return []

    results = []
    for tx in raw_list:
        try:
            tx_id = str(tx.get("id") or "").strip()
            if not tx_id:
                continue
            amount_in = _sepay_parse_amount(tx.get("amount_in"))
            if amount_in <= 0:
                continue
            results.append({
                "transactionID": sepay_normalize_ref(tx_id),
                "description": str(tx.get("transaction_content") or tx.get("code") or ""),
                "amount": amount_in,
            })
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    return results

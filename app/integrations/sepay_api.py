# --- SEPAY INTEGRATION ---
# Webhook la duong chinh (SePay tu push giao dich ve, gan nhu tuc thi).
# Poll (sepay_fetch_history) chi la du phong doi soat lai: bat khi webhook bi
# mat (VPS restart, mang loi) hoac chua kip cau hinh webhook tren dashboard.
#
# Ca hai duong deu chuan hoa ve cung 1 dang {"transactionID", "description",
# "amount"} roi nap vao pipeline khop-don/cong-tien co san trong
# app/jobs/payment_monitor.py (check_payment_job) - giong het cach
# _scan_rpay_payments dang lam. Nho vay
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
    """Chuan hoa payload webhook SePay ve dang dung chung voi cac scan crypto.

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


async def _sepay_api_get(path: str, params: dict, log_label: str) -> dict | None:
    """GET mot endpoint userapi cua SePay. Thieu token / loi mang -> None."""
    token = (SEPAY_API_TOKEN or "").strip()
    if not token:
        return None

    url = f"{SEPAY_API_BASE_URL}{path}"
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
        logger.warning(f"SePay API {log_label} request failed: {e}")
        return None

    return payload if isinstance(payload, dict) else None


async def sepay_fetch_history(limit: int = 200, lookback_minutes: int | None = None) -> list:
    """Doi soat lai (docs.sepay.vn -> API Giao dich): GET /userapi/transactions/list.

    Chi dung de vet giao dich webhook bi sot. Loi mang/thieu token -> tra []
    (caller tu log, khong lam gian doan cac scan khac).
    """
    import datetime

    window_minutes = lookback_minutes or SEPAY_POLL_LOOKBACK_MINUTES
    date_min = (datetime.datetime.now() - datetime.timedelta(minutes=window_minutes)).strftime("%Y-%m-%d")
    params = {"limit": str(limit), "transaction_date_min": date_min}
    if SEPAY_ACCOUNT_NUMBER:
        params["account_number"] = SEPAY_ACCOUNT_NUMBER

    payload = await _sepay_api_get("/userapi/transactions/list", params, "poll")
    if not payload:
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


def sepay_extract_account_balance(payload: dict | None, account_no: str) -> dict | None:
    """Loc tai khoan dang cau hinh ra khoi payload /userapi/bankaccounts/list.

    `account_no` rong -> lay tai khoan dau tien (shop chi gan 1 tai khoan).
    """
    if not isinstance(payload, dict):
        return None
    accounts = payload.get("bankaccounts") or payload.get("bank_accounts") or []
    if not isinstance(accounts, list):
        return None

    expected = str(account_no or "").strip()
    for raw_account in accounts:
        if not isinstance(raw_account, dict):
            continue
        current = str(raw_account.get("account_number") or raw_account.get("accountNumber") or "").strip()
        if expected and current != expected:
            continue
        return {
            "account_no": current,
            "account_name": str(raw_account.get("account_holder_name") or raw_account.get("label") or "").strip(),
            "bank": str(raw_account.get("bank_short_name") or raw_account.get("bank_full_name") or "").strip(),
            "currency": "VND",
            "current_balance": _sepay_parse_amount(raw_account.get("accumulated")),
        }
    return None


async def sepay_fetch_account_balance(account_no: str | None = None) -> dict | None:
    """So du luy ke cua tai khoan ngan hang gan tren SePay.

    Nguon: docs.sepay.vn -> API Tai khoan ngan hang (GET /userapi/bankaccounts/list),
    truong `accumulated`. Thieu token / loi mang / khong khop tai khoan -> None.
    """
    target = str(account_no if account_no is not None else SEPAY_ACCOUNT_NUMBER or "").strip()
    payload = await _sepay_api_get("/userapi/bankaccounts/list", {}, "bankaccounts")
    return sepay_extract_account_balance(payload, target)

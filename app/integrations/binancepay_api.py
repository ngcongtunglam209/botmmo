# --- BINANCE PAY (qua feed lich su sieuthicode.com) ---
# Khach chuyen USDT thang vao Binance ID cua shop. Shop khong tao duoc hoa don
# rieng cho tung don (Binance Pay ID khong co API invoice), nen doi soat bang
# cach doc lich su giao dich va khop lai.
#
# KHAC BIET QUAN TRONG SO VOI SEPAY / RPAY:
# Feed nay khong tra ve noi dung chuyen khoan - `description` gan nhu luon
# rong. Vi vay KHONG the khop don theo ma ICLD nhu duong ngan hang. Thu duy
# nhat phan biet duoc hai don la SO TIEN. Toan bo thiet ke ben duoi xoay quanh
# viec bao dam so tien la duy nhat:
#
#   1. Moi don duoc cap mot so le rieng o chu so thu BINANCE_PAY_AMOUNT_DECIMALS
#      (mac dinh 4), chon sao cho khong dung so tien cua bat ky don Binance Pay
#      nao dang cho. Xem allocate_binance_pay_amount().
#   2. Luc doi soat, neu vi ly do nao do van co hai don cung so tien thi CA HAI
#      deu bi bo qua chu khong doan bua - cong nham don la mat hang. Xem
#      _scan_binance_pay_payments() trong app/jobs/payment_monitor.py.
#   3. Giao dich phai roi trong cua so thoi gian cua don.
#
# Token cua feed nam trong URL nen no lot vao log truy cap cua moi proxy tren
# duong di - coi nhu bi mat yeu. Do do feed chi duoc phep tra loi cau hoi "co
# giao dich dung so tien nay khong", con SO TIEN CONG CHO KHACH luon lay tu don
# pending cua ta.

BINANCE_PAY_TRANSACTION_IN = "IN"


def is_binance_pay_enabled() -> bool:
    return bool(ENABLE_PAYMENT_BINANCE_PAY and BINANCE_PAY_ID and BINANCE_PAY_HISTORY_URL)


def binance_pay_normalize_ref(transaction_id) -> str:
    return f"BINPAY{transaction_id}"


def _binance_pay_decimal(raw, default=None):
    try:
        text = str(raw if raw is not None else "").strip()
        if not text:
            return default
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return default


def get_binance_pay_quantizer():
    return Decimal("1").scaleb(-BINANCE_PAY_AMOUNT_DECIMALS)


def binance_pay_amount_text(value) -> str:
    """Chuoi so tien dung de khop don, cat bot chu so thua thay vi lam tron.

    Feed tra so tien day du 8 chu so (vi du "91.4817877") con don chi giu
    BINANCE_PAY_AMOUNT_DECIMALS chu so. Lam tron se keo mot khoan tra hut nhu
    1.54005 len thanh 1.5401 va khop nham don cua nguoi khac. Cat xuong thi sai
    so luon nghieng ve phia "khong khop" - don do roi xuong doi soat tay, khong
    ai bi giao nham hang.
    """
    return format(
        Decimal(value).quantize(get_binance_pay_quantizer(), rounding=ROUND_DOWN),
        f".{BINANCE_PAY_AMOUNT_DECIMALS}f",
    )


def iter_pending_binance_pay_records():
    """(ma, ban ghi) cua moi thu dang cho tra bang Binance Pay.

    Gop CA don hang lan lenh nap vi: hai ho so nay o hai dictionary khac nhau
    nhung chung mot cach doi soat (khop theo so tien), nen mot so tien bi don
    hang chiem cung phai bi coi la da chiem voi lenh nap - khong thi mot lenh
    nap co the an mat tien cua mot don hang.
    """
    for order_code, details in list(pending_orders.items()):
        if not isinstance(details, dict):
            continue
        if details.get("provider") != "binance_pay" or details.get("status") != "pending_payment":
            continue
        yield str(order_code), details
    for topup_code, details in list(pending_user_topups.items()):
        if not isinstance(details, dict):
            continue
        if details.get("provider") != "binance_pay":
            continue
        yield str(topup_code), details


def collect_pending_binance_pay_amounts(exclude_order_code: str = "") -> set:
    """So tien (chuoi da chuan hoa) ma cac don Binance Pay dang cho chiem giu."""
    taken = set()
    for order_code, details in iter_pending_binance_pay_records():
        if exclude_order_code and order_code == exclude_order_code:
            continue
        amount = _binance_pay_decimal(details.get("binance_pay_amount"))
        if amount is not None:
            taken.add(binance_pay_amount_text(amount))
    return taken


def allocate_binance_pay_amount(base_amount):
    """Gan cho don mot so tien khong don nao dang cho dang giu.

    `base_amount` la so USDT da lam tron len o do chinh xac hien thi (vi du
    1.54). Ham cong them 0.0001, 0.0002, ... cho den khi ra so chua bi chiem.
    Luon cong LEN nen khach khong bao gio tra it hon gia.

    Raise RuntimeError neu khong con so trong - tha tu choi tao don con hon tao
    hai don trung so tien roi cong nham nguoi.
    """
    quantizer = get_binance_pay_quantizer()
    step = quantizer
    taken = collect_pending_binance_pay_amounts()

    amount = Decimal(base_amount).quantize(quantizer, rounding=ROUND_UP)
    # Voi 4 chu so thap phan va hien thi 2 chu so, con 99 khe giua hai muc gia
    # lien tiep. Vuot qua nghia la shop dang co qua nhieu don Binance Pay cho
    # cung mot muc gia.
    max_slots = 10 ** (BINANCE_PAY_AMOUNT_DECIMALS - USDT_DISPLAY_DECIMALS)
    for _ in range(max_slots):
        text = binance_pay_amount_text(amount)
        if text not in taken:
            return amount, text
        amount += step
    raise RuntimeError(
        "Khong con so tien Binance Pay trong cho muc gia nay; thu lai sau khi cac don cho het han"
    )


def normalize_binance_pay_transaction(raw) -> dict | None:
    """Chuan hoa 1 ban ghi cua feed. Tra None neu khong phai tien VAO hop le."""
    if not isinstance(raw, dict):
        return None
    if str(raw.get("type") or "").strip().upper() != BINANCE_PAY_TRANSACTION_IN:
        return None
    currency = str(raw.get("currency") or "").strip().upper()
    if currency and currency != "USDT":
        return None
    transaction_id = str(raw.get("transactionID") or raw.get("transaction_id") or "").strip()
    if not transaction_id:
        return None
    amount = _binance_pay_decimal(raw.get("amount"))
    if amount is None or amount <= 0:
        return None

    timestamp_ms = 0
    try:
        timestamp_ms = int(raw.get("timestamp") or 0)
    except (TypeError, ValueError):
        timestamp_ms = 0
    if timestamp_ms <= 0:
        # Feed luon kem `timestamp`; `transactionDate` chi la du phong va chi co
        # do chinh xac toi ngay.
        raw_date = str(raw.get("transactionDate") or "").strip()
        if raw_date:
            import datetime

            try:
                parsed = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
                timestamp_ms = int(parsed.timestamp() * 1000)
            except ValueError:
                timestamp_ms = 0

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "amount_text": binance_pay_amount_text(amount),
        "timestamp_ms": timestamp_ms,
        "description": str(raw.get("description") or "").strip(),
    }


async def fetch_binance_pay_transactions() -> list:
    """Doc feed lich su. Loi mang / payload la -> [] (caller tu log)."""
    if not is_binance_pay_enabled():
        return []

    import httpx

    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=BINANCE_PAY_TIMEOUT_SECONDS)
    owns_client = client is not http_client
    try:
        response = await client.get(BINANCE_PAY_HISTORY_URL, timeout=BINANCE_PAY_TIMEOUT_SECONDS)
        if response.status_code != 200:
            # Khong log response.text: feed vong lai token trong mot so thong
            # bao loi.
            raise RuntimeError(f"HTTP {response.status_code}")
        payload = response.json()
    finally:
        if owns_client:
            await client.aclose()

    if not isinstance(payload, dict):
        raise RuntimeError("payload khong phai JSON object")
    if str(payload.get("status") or "").strip().lower() != "success":
        raise RuntimeError(str(payload.get("msg") or "feed tra ve status khac success")[:200])

    raw_list = payload.get("transactions")
    if not isinstance(raw_list, list):
        return []

    results = []
    for raw in raw_list:
        normalized = normalize_binance_pay_transaction(raw)
        if normalized:
            results.append(normalized)
    return results


def build_binance_pay_checkout_keyboard(order_code: str, amount_text: str, user_id=None):
    rows = []
    if BINANCE_PAY_ID:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép ID Binance", "📋 Copy Binance ID", "📋 复制 Binance ID"),
            copy_text=CopyTextButton(BINANCE_PAY_ID),
        )])
    if amount_text:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép số tiền", "📋 Copy amount", "📋 复制金额"),
            copy_text=CopyTextButton(amount_text),
        )])
    rows.append([InlineKeyboardButton(_cancel_payment_label(user_id), callback_data=f"cancel_order:{order_code}")])
    return InlineKeyboardMarkup(rows)


def binance_pay_qr_photo():
    """QR chua Binance ID de khach quet trong app Binance."""
    if not BINANCE_PAY_ID:
        return None
    from urllib.parse import quote

    return f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={quote(BINANCE_PAY_ID, safe='')}"


async def create_binance_pay_order(order_code: str, amount_vnd: int) -> dict:
    """Quy doi VND -> USDT roi cap so tien duy nhat cho `order_code`.

    Khong goi API nao ca: Binance Pay ID khong co endpoint tao hoa don. Don chi
    ton tai ben phia bot, doi soat sau bang feed lich su.
    """
    from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

    if not is_binance_pay_enabled():
        raise RuntimeError("Binance Pay chua duoc cau hinh (BINANCE_PAY_ID / BINANCE_PAY_HISTORY_URL)")

    live_rate = await get_live_usdt_vnd_rate()
    base_amount = convert_vnd_to_usdt(amount_vnd, rate=live_rate)
    amount, amount_text = allocate_binance_pay_amount(base_amount)
    return {
        "binance_pay_id": BINANCE_PAY_ID,
        "base_amount": base_amount,
        "amount": amount,
        "amount_text": amount_text,
        "rate": live_rate,
        "decimals": BINANCE_PAY_AMOUNT_DECIMALS,
    }

# --- BINANCE PAY (qua GET /sapi/v1/pay/transactions cua chinh Binance) ---
# Khach chuyen USDT thang vao Binance ID cua shop. Shop khong tao duoc hoa don
# rieng cho tung don (can tai khoan merchant, ma merchant lai can giay phep kinh
# doanh), nen doi soat bang cach doc lich su giao dich va khop lai.
#
# KHAC BIET QUAN TRONG SO VOI SEPAY / RPAY:
# Endpoint nay khong he co truong memo/description, va o chieu NHAN tien Binance
# chi tra ve nickname nguoi gui chu khong tra ve UID. Vi vay KHONG the khop don
# theo ma ICLD nhu duong ngan hang, cung khong khop duoc theo danh tinh nguoi
# tra. Thu duy nhat phan biet duoc hai don la SO TIEN. Toan bo thiet ke ben duoi
# xoay quanh viec bao dam so tien la duy nhat:
#
#   1. Moi don duoc cap mot so le rieng o chu so thu BINANCE_PAY_AMOUNT_DECIMALS
#      (mac dinh 4), chon sao cho khong dung so tien cua bat ky don Binance Pay
#      nao dang cho. Xem allocate_binance_pay_amount().
#   2. Luc doi soat, neu vi ly do nao do van co hai don cung so tien thi CA HAI
#      deu bi bo qua chu khong doan bua - cong nham don la mat hang. Xem
#      _scan_binance_pay_payments() trong app/jobs/payment_monitor.py.
#   3. Giao dich phai roi trong cua so thoi gian cua don.
#
# API key chi can quyen doc va nen whitelist IP cua VPS. Du vay no van chi duoc
# phep tra loi cau hoi "co giao dich dung so tien nay khong", con SO TIEN CONG
# CHO KHACH luon lay tu don pending cua ta.

BINANCE_PAY_HISTORY_PATH = "/sapi/v1/pay/transactions"
# Tran cua endpoint. Vong quet chay moi BANK_CHECK_INTERVAL_SECONDS nen 100 giao
# dich gan nhat thua suc phu het cac don con han.
BINANCE_PAY_HISTORY_LIMIT = 100
# Chieu tien VAO. PAY_REFUND / PAYOUT cung co the mang so duong (tien hoan ve
# vi shop) nhung do la tien cua chinh shop chay vong lai, khong phai khach tra -
# cong no cho mot don dang cho la giao hang khong cong.
BINANCE_PAY_INCOMING_ORDER_TYPES = frozenset({"PAY", "C2C"})


_binance_pay_credentials_warned = False


def is_binance_pay_enabled() -> bool:
    """Binance Pay chi bat khi co ca Pay ID lan API key/secret de doi soat.

    Thieu key ma van bat cong: khach bam duoc nut Binance Pay va tra tien vao
    mot don khong bao gio doi soat duoc. Tha tat cong con hon nhan tien ma khong
    cong duoc, nhung phai keu to len mot lan vi day la loi cau hinh im lang.
    """
    global _binance_pay_credentials_warned
    if not (ENABLE_PAYMENT_BINANCE_PAY and BINANCE_PAY_ID):
        return False
    if not (BINANCE_API_KEY and BINANCE_API_SECRET):
        if not _binance_pay_credentials_warned:
            _binance_pay_credentials_warned = True
            logger.error(
                "ENABLE_PAYMENT_BINANCE_PAY dang bat nhung thieu BINANCE_API_KEY / "
                "BINANCE_API_SECRET -> tat Binance Pay. Tao key chi-doc trong tai "
                "khoan Binance nhan tien va whitelist IP cua VPS."
            )
        return False
    return True


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


# So tien da phat ra gan day -> thoi diem het thoi gian giu cho.
# Chi giu trong RAM: sau restart chi mat phan giu cho cua don DA het han, con
# don dang cho van duoc tinh qua iter_pending_binance_pay_records().
_binance_pay_amount_cooldown: dict[str, float] = {}


def binance_pay_cooldown_seconds() -> int:
    """Bao lau mot so tien van bi giu sau khi don chiem no bien mat.

    Phai phu het cua so ma payment_monitor con chap nhan giao dich cho don cu:
    han don + hai lan leeway hai dau cua so.
    """
    return int(ORDER_EXPIRATION_SECONDS) + 2 * int(BINANCE_PAY_MATCH_LEEWAY_SECONDS)


def _prune_binance_pay_cooldown(now: float | None = None) -> None:
    current = time.time() if now is None else now
    for text in [key for key, until in _binance_pay_amount_cooldown.items() if until <= current]:
        _binance_pay_amount_cooldown.pop(text, None)


def collect_pending_binance_pay_amounts(exclude_order_code: str = "") -> set:
    """So tien (chuoi da chuan hoa) dang bi chiem giu.

    Gom hai nguon:
      1. Don Binance Pay dang cho tra.
      2. So tien vua phat ra nhung don da bien mat (het han / bi huy) va con
         trong thoi gian giu cho.

    Chi dua vao (1) la khong du: don het han bi _cleanup_expired_pending_orders
    pop ra khoi pending_orders, so tien duoc "tra lai" ngay lap tuc, nen don ke
    tiep cung muc gia nhan dung so do. Khach cu tra tien muon -> giao dich khop
    vao don MOI -> nguoi khac duoc giao hang bang tien cua ho.
    """
    _prune_binance_pay_cooldown()
    taken = set(_binance_pay_amount_cooldown)
    for order_code, details in iter_pending_binance_pay_records():
        if exclude_order_code and order_code == exclude_order_code:
            continue
        amount = _binance_pay_decimal(details.get("binance_pay_amount"))
        if amount is not None:
            taken.add(binance_pay_amount_text(amount))
    if exclude_order_code:
        # Cap lai so cu cho chinh don do thi khong sao.
        for _code, details in iter_pending_binance_pay_records():
            if _code != exclude_order_code:
                continue
            amount = _binance_pay_decimal(details.get("binance_pay_amount"))
            if amount is not None:
                taken.discard(binance_pay_amount_text(amount))
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
            # Giu cho so nay ke ca khi don bi huy/het han som, de mot lan tra
            # muon cua don cu khong khop nham vao don sau.
            _binance_pay_amount_cooldown[text] = time.time() + binance_pay_cooldown_seconds()
            return amount, text
        amount += step
    raise RuntimeError(
        "Khong con so tien Binance Pay trong cho muc gia nay; thu lai sau khi cac don cho het han"
    )


def normalize_binance_pay_transaction(raw) -> dict | None:
    """Chuan hoa 1 ban ghi cua API. Tra None neu khong phai tien VAO hop le.

    Binance khong co truong type IN/OUT: huong tien nam o DAU cua `amount`
    ("Positive means income; negative means expenditure"). Nhung chi xet dau la
    chua du - tien hoan (PAY_REFUND) chay ve vi shop cung mang dau duong, nen
    phai loc them theo `orderType`.
    """
    if not isinstance(raw, dict):
        return None
    if str(raw.get("orderType") or "").strip().upper() not in BINANCE_PAY_INCOMING_ORDER_TYPES:
        return None
    if str(raw.get("currency") or "").strip().upper() != "USDT":
        return None
    transaction_id = str(raw.get("transactionId") or "").strip()
    if not transaction_id:
        return None
    amount = _binance_pay_decimal(raw.get("amount"))
    if amount is None or amount <= 0:
        return None

    try:
        timestamp_ms = int(raw.get("transactionTime") or 0)
    except (TypeError, ValueError):
        return None
    # Khong co moc thoi gian thi khong kiem tra duoc cua so cua don; bo qua chu
    # khong khop bang moi so tien.
    if timestamp_ms <= 0:
        return None

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "amount_text": binance_pay_amount_text(amount),
        "timestamp_ms": timestamp_ms,
    }


def _binance_signed_history_url() -> str:
    """URL da ky HMAC-SHA256 cho GET /sapi/v1/pay/transactions."""
    from urllib.parse import urlencode

    # Chu ky tinh tren DUNG chuoi query duoc gui di, nen phai dung lai `query`
    # chu khong dung params lan nua - httpx co the sap xep/encode khac di.
    query = urlencode({
        "limit": BINANCE_PAY_HISTORY_LIMIT,
        "recvWindow": BINANCE_PAY_RECV_WINDOW_MS,
        "timestamp": int(time.time() * 1000),
    })
    signature = hmac.new(
        BINANCE_API_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{BINANCE_API_BASE_URL}{BINANCE_PAY_HISTORY_PATH}?{query}&signature={signature}"


async def fetch_binance_pay_transactions() -> list:
    """Doc lich su Binance Pay. Loi mang / payload la -> raise (caller tu log)."""
    if not is_binance_pay_enabled():
        return []

    import httpx

    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=BINANCE_PAY_TIMEOUT_SECONDS)
    owns_client = client is not http_client
    try:
        try:
            response = await client.get(
                _binance_signed_history_url(),
                headers={"X-MBX-APIKEY": BINANCE_API_KEY},
                timeout=BINANCE_PAY_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            # Loi cua httpx kem ca URL, ma URL chua chu ky - khong de no roi vao
            # log. Ten exception la du de biet mang hong hay Binance chan.
            raise RuntimeError(f"{type(exc).__name__} khi goi {BINANCE_PAY_HISTORY_PATH}") from None
        try:
            payload = response.json()
        except ValueError:
            payload = None
    finally:
        if owns_client:
            await client.aclose()

    if response.status_code != 200:
        # Binance tra {"code":-1021,"msg":...} (lech dong ho) hoac -2015 (key/IP
        # sai). Giu lai vi day la thu duy nhat chan doan duoc, va no khong chua
        # secret.
        detail = ""
        if isinstance(payload, dict):
            detail = f" {payload.get('code')}: {payload.get('msg') or payload.get('message')}"
        raise RuntimeError(f"HTTP {response.status_code}{detail}"[:200])

    if not isinstance(payload, dict):
        raise RuntimeError("payload khong phai JSON object")
    if payload.get("success") is not True or str(payload.get("code") or "").strip() != "000000":
        raise RuntimeError(
            f"{payload.get('code')}: {payload.get('message') or payload.get('msg') or 'khong ro'}"[:200]
        )

    raw_list = payload.get("data")
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
    ton tai ben phia bot, doi soat sau bang lich su giao dich.
    """
    from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

    if not is_binance_pay_enabled():
        raise RuntimeError(
            "Binance Pay chua duoc cau hinh (BINANCE_PAY_ID / BINANCE_API_KEY / BINANCE_API_SECRET)"
        )

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

# --- NOWPAYMENTS (USDT da mang: BSC, Polygon, ...) ---
# Khac han Binance Pay: o day MOI DON co ma rieng. `order_id` ta gui luc tao
# payment quay ve nguyen ven trong IPN, nen khop don la khop truc tiep - khong
# con tro cap so le de phan biet hai don nhu binancepay_api.py.
#
# Duong chinh la IPN callback (POST /webhook/nowpayments), duong du phong la
# poll GET /v1/payment/<id> cho cac don da het han: NOWPayments NGUNG gui IPN
# sau khi payment het han nhung tien van co the vao, nen don tra muon se bien
# mat im lang neu chi tin callback.
#
# BA CAI BAY CUA NOWPAYMENTS - deu dan toi "giao hang ma chua duoc tra du":
#
#   1. RE-DEPOSIT. Khach gui them tien vao dung dia chi cu sau khi don da xong.
#      Giao dich do van duoc gan status "finished"/"partially_paid" va co
#      `parent_payment_id` tro ve payment goc. Chinh NOWPayments khuyen cao
#      khong tu dong giao hang theo trang thai cua re-deposit. Ta chan thang:
#      `parent_payment_id` khac None -> khong bao gio tu cong, chi log.
#   2. WRONG-ASSET DEPOSIT. Khach gui nham mang/nham token. Neu bat
#      auto-processing ben dashboard, NOWPayments quy doi theo gia hien tai va
#      VAN co the gan "finished" du so tien hut. Vi vay khong bao gio tin
#      `payment_status` mot minh.
#   3. TRA THIEU. Luon so `actually_paid` voi `pay_amount`; chi tha qua
#      NOWPAYMENTS_UNDERPAY_TOLERANCE (phi mang).
#
# SO TIEN CONG CHO KHACH luon lay tu don pending cua ta (VND), khong bao gio
# lay tu payload - y het quy tac cua Binance Pay.

NOWPAYMENTS_STATUS_FINISHED = "finished"
NOWPAYMENTS_STATUS_PARTIAL = "partially_paid"
# Trang thai con dang chay, chua the giao hang. Liet ke ra de log cho ro thay
# vi im lang bo qua.
NOWPAYMENTS_STATUS_IN_FLIGHT = frozenset({"waiting", "confirming", "confirmed", "sending"})

# IPN da xac thuc chu ky, cho payment_monitor rut o vong quet ke tiep.
nowpayments_ipn_inbox: list = []

# Nut "Coin khac": khong tao payment theo mang co dinh ma mo trang hoa don cua
# NOWPayments de khach tu chon coin. Sentinel nay di qua cac callback
# `nowpaynet_` / `topup_npnet:` nhu mot ma dong tien binh thuong.
NOWPAYMENTS_INVOICE_CHOICE = "any"


def is_nowpayments_enabled() -> bool:
    """Bat khi co du API key, IPN secret va it nhat mot ma dong tien.

    Thieu IPN secret ma van bat cong la trang thai nguy hiem nhat: khach tra
    duoc tien nhung moi callback deu bi tu choi, don khong bao gio duoc cong.
    """
    return bool(
        ENABLE_PAYMENT_NOWPAYMENTS
        and NOWPAYMENTS_API_KEY
        and NOWPAYMENTS_IPN_SECRET
        and NOWPAYMENTS_CURRENCIES
    )


def nowpayments_invoice_available() -> bool:
    """Trang hoa don chi dung duoc khi IPN toi duoc: payment_id cua don hoa don
    ta chi biet qua IPN dau tien, khong co no thi duong poll du phong mu."""
    return is_nowpayments_enabled() and bool(nowpayments_callback_url())


def nowpayments_normalize_ref(payment_id) -> str:
    return f"NOWPAY{payment_id}"


def _nowpayments_decimal(raw, default=None):
    try:
        text = str(raw if raw is not None else "").strip()
        if not text:
            return default
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return default


def nowpayments_canonical_payload(body: dict) -> str:
    """Chuoi ma NOWPayments dung de ky: JSON sap xep khoa, khong khoang trang.

    `separators=(',', ':')` la bat buoc - `json.dumps` mac dinh chen mot dau
    cach sau moi dau phay va sau dau hai cham, ra chuoi khac han cai NOWPayments
    da ky. `sort_keys=True` sap xep de quy nen object long nhau (`fee`) cung
    dung thu tu.
    """
    return json.dumps(body, separators=(",", ":"), sort_keys=True)


def nowpayments_verify_signature(body: dict, signature: str | None) -> bool:
    """Kiem tra header `x-nowpayments-sig` (HMAC-SHA512).

    Chua cau hinh secret -> luon False. Day la endpoint cong tien, tha bo lo
    callback con hon mo cua cho nguoi la day payload gia vao.
    """
    secret = (NOWPAYMENTS_IPN_SECRET or "").strip()
    if not secret:
        logger.error("NOWPayments IPN: chua dat NOWPAYMENTS_IPN_SECRET -> tu choi request")
        return False
    if not signature or not isinstance(body, dict):
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        nowpayments_canonical_payload(body).encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()
    # compare_digest chu khong phai == : chu ky la bi mat suy dien duoc bang
    # timing attack neu so sanh thoat som.
    return hmac.compare_digest(expected, str(signature).strip())


def nowpayments_normalize_payment(body: dict) -> dict | None:
    """Chuan hoa 1 payment (IPN hoac poll). None = khong duoc phep cong tien.

    Moi ly do tu choi deu duoc log: mot don tra thieu hay mot re-deposit bi im
    lang bo qua se hien ra thanh "khach bao da tra ma bot khong nhan", va khong
    ai lan ra duoc nguyen nhan.
    """
    if not isinstance(body, dict):
        return None

    payment_id = str(body.get("payment_id") or "").strip()
    if not payment_id:
        return None

    order_code = str(body.get("order_id") or "").strip()
    if not order_code:
        logger.warning("NOWPayments: payment %s khong co order_id -> bo qua", payment_id)
        return None

    # Bay 1: re-deposit. Khong bao gio tu dong giao hang theo trang thai cua no.
    parent_payment_id = body.get("parent_payment_id")
    if parent_payment_id not in (None, "", 0):
        logger.error(
            "NOWPayments: payment %s la re-deposit cua %s (don %s) -> KHONG tu cong, "
            "can doi soat tay",
            payment_id,
            parent_payment_id,
            order_code,
        )
        return None

    status = str(body.get("payment_status") or "").strip().lower()
    if status != NOWPAYMENTS_STATUS_FINISHED:
        if status == NOWPAYMENTS_STATUS_PARTIAL:
            logger.warning(
                "NOWPayments: payment %s (don %s) moi tra mot phan -> cho tiep",
                payment_id,
                order_code,
            )
        elif status not in NOWPAYMENTS_STATUS_IN_FLIGHT:
            logger.warning(
                "NOWPayments: payment %s (don %s) o trang thai %s -> bo qua",
                payment_id,
                order_code,
                status or "rong",
            )
        return None

    # Bay 2+3: khong tin moi payment_status. Wrong-asset deposit duoc quy doi tu
    # dong van co the mang nhan "finished" du so tien hut.
    pay_amount = _nowpayments_decimal(body.get("pay_amount"))
    actually_paid = _nowpayments_decimal(body.get("actually_paid"))
    if pay_amount is None or pay_amount <= 0:
        logger.warning("NOWPayments: payment %s khong doc duoc pay_amount -> bo qua", payment_id)
        return None
    if actually_paid is None or actually_paid <= 0:
        logger.warning("NOWPayments: payment %s khong doc duoc actually_paid -> bo qua", payment_id)
        return None
    pay_currency = str(body.get("pay_currency") or "").strip().lower()
    # Dung sai tuyet doi (0.01) chi co nghia voi stablecoin. Don hoa don cho
    # khach chon coin bat ky: 0.01 BTC la ca trieu dong, nen coin khac phai tra du.
    tolerance = NOWPAYMENTS_UNDERPAY_TOLERANCE if pay_currency.startswith(("usdt", "usdc")) else Decimal("0")
    if actually_paid < (pay_amount - tolerance):
        logger.error(
            "NOWPayments: payment %s (don %s) tra thieu %s/%s %s -> KHONG cong",
            payment_id,
            order_code,
            actually_paid,
            pay_amount,
            pay_currency,
        )
        return None

    return {
        "transaction_ref": nowpayments_normalize_ref(payment_id),
        "payment_id": payment_id,
        "order_code": order_code,
        "pay_amount": pay_amount,
        "actually_paid": actually_paid,
        "pay_currency": pay_currency,
    }


def nowpayments_remember_payment_id(body: dict) -> bool:
    """IPN dau tien cua don hoa don la luc duy nhat ta biet payment_id -> ghi vao
    ban ghi pending de duong poll du phong co ma ma hoi lai. Don tao bang
    create_nowpayments_payment da co payment_id tu dau nen khong bi dung toi.

    ponytail: don hoa don ma IPN chet hoan toan thi poll mu; nang cap = GET
    /v1/payment/?invoiceId= (can JWT dang nhap email/password).
    """
    if not isinstance(body, dict):
        return False
    payment_id = str(body.get("payment_id") or "").strip()
    order_code = str(body.get("order_id") or "").strip()
    if not payment_id or not order_code:
        return False
    for code, details in iter_pending_nowpayments_records():
        if code != order_code or details.get("nowpayments_payment_id"):
            continue
        details["nowpayments_payment_id"] = payment_id
        pay_currency = str(body.get("pay_currency") or "").strip().lower()
        if pay_currency:
            details["nowpayments_currency"] = pay_currency
        logger.info("NOWPayments: don hoa don %s gan payment %s (%s)", order_code, payment_id, pay_currency)
        return True
    return False


def nowpayments_pay_currency_label(currency: str) -> str:
    """Nhan cho khach. "usdtbsc" khong noi gi, "USDT (BEP20)" thi co."""
    labels = {
        "usdtbsc": "USDT (BEP20 - BNB Smart Chain)",
        "usdtmatic": "USDT (Polygon)",
        "usdttrc20": "USDT (TRC20 - TRON)",
        "usdterc20": "USDT (ERC20 - Ethereum)",
        "usdtsol": "USDT (Solana)",
        "usdtarb": "USDT (Arbitrum)",
        "usdtton": "USDT (TON)",
    }
    key = str(currency or "").strip().lower()
    return labels.get(key, key.upper())


async def _nowpayments_request(method: str, path: str, payload: dict | None = None) -> dict:
    """Goi API NOWPayments. Loi mang / HTTP != 200 -> raise (caller tu log)."""
    import httpx

    url = f"{NOWPAYMENTS_BASE_URL}{path}"
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}

    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=NOWPAYMENTS_TIMEOUT_SECONDS)
    owns_client = client is not http_client
    try:
        try:
            response = await client.request(
                method,
                url,
                json=payload,
                headers=headers,
                timeout=NOWPAYMENTS_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"{type(exc).__name__} khi goi {path}") from None
        try:
            body = response.json()
        except ValueError:
            body = None
    finally:
        if owns_client:
            await client.aclose()

    if response.status_code not in (200, 201):
        detail = ""
        if isinstance(body, dict):
            detail = f" {body.get('code') or ''} {body.get('message') or ''}".rstrip()
        raise RuntimeError(f"HTTP {response.status_code}{detail}"[:200])
    if not isinstance(body, dict):
        raise RuntimeError("payload khong phai JSON object")
    return body


# So tien toi thieu moi mang, cache lai vi no bam theo phi mang va doi trong
# ngay. Dict duoc SUA TAI CHO chu khong gan lai: section loader copy symbol sang
# moi module khac nen gan lai bien se khong lan sang cac ban sao.
_nowpayments_min_amount_cache: dict = {}
NOWPAYMENTS_MIN_AMOUNT_CACHE_SECONDS = 900


async def nowpayments_min_amount(currency: str):
    """So USDT toi thieu mang `currency` nhan duoc. None = khong hoi duoc.

    Chenh lech giua cac mang rat lon (TRC20 quanh 11 USDT trong khi BEP20 duoi
    0.1), nen khong the dung mot nguong chung cho ca cong.
    """
    key = str(currency or "").strip().lower()
    if not key:
        return None

    cached = _nowpayments_min_amount_cache.get(key)
    if cached and cached[1] > time.time():
        return cached[0]

    target = NOWPAYMENTS_PAYOUT_CURRENCY or key
    body = await _nowpayments_request("GET", f"/min-amount?currency_from={key}&currency_to={target}")
    minimum = _nowpayments_decimal(body.get("min_amount"))
    if minimum is None or minimum < 0:
        return None
    _nowpayments_min_amount_cache[key] = (minimum, time.time() + NOWPAYMENTS_MIN_AMOUNT_CACHE_SECONDS)
    return minimum


async def nowpayments_currencies_for_amount(usdt_amount) -> list:
    """Loc NOWPAYMENTS_CURRENCIES con nhung mang tra duoc so tien nay.

    Hien nut cua mot mang co san cao hon gia tri don la day khach vao mot hoa
    don chac chan hong. Hoi khong duoc san thi GIU mang do: tha de NOWPayments
    tu choi luc tao payment con hon am tham giau mat phuong thuc thanh toan vi
    mot loi mang thoang qua.
    """
    amount = _nowpayments_decimal(usdt_amount)
    if amount is None:
        return list(NOWPAYMENTS_CURRENCIES)

    available = []
    for currency in NOWPAYMENTS_CURRENCIES:
        try:
            minimum = await nowpayments_min_amount(currency)
        except Exception as exc:
            logger.warning("NOWPayments: khong lay duoc min-amount cua %s: %s", currency, exc)
            available.append(currency)
            continue
        if minimum is None or amount >= minimum:
            available.append(currency)
    return available


async def create_nowpayments_payment(order_code: str, amount_vnd: int, pay_currency: str) -> dict:
    """Tao payment va tra ve dia chi + so tien khach phai gui.

    `order_code` di thang vao `order_id` - day la thu duy nhat dung de khop don
    khi IPN quay ve, nen no phai la ma don that chu khong phai mo ta.
    """
    from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

    if not is_nowpayments_enabled():
        raise RuntimeError(
            "NOWPayments chua duoc cau hinh (NOWPAYMENTS_API_KEY / NOWPAYMENTS_IPN_SECRET / "
            "NOWPAYMENTS_CURRENCIES)"
        )
    currency = str(pay_currency or "").strip().lower()
    if currency == NOWPAYMENTS_INVOICE_CHOICE:
        return await create_nowpayments_invoice(order_code, amount_vnd)
    if currency not in NOWPAYMENTS_CURRENCIES:
        raise RuntimeError(f"Ma dong tien khong nam trong NOWPAYMENTS_CURRENCIES: {currency}")

    live_rate = await get_live_usdt_vnd_rate()
    price_amount = convert_vnd_to_usdt(amount_vnd, rate=live_rate)

    # Duoi san cua mang thi NOWPayments tu choi. Chan o day de loi noi ro ly do
    # thay vi tra ve "HTTP 400" tran trui, va de con duong nao goi thang ham nay
    # ma quen loc bang nowpayments_currencies_for_amount() cung khong tao ra hoa
    # don chet.
    try:
        minimum = await nowpayments_min_amount(currency)
    except Exception as exc:
        logger.warning("NOWPayments: bo qua kiem min-amount cua %s: %s", currency, exc)
        minimum = None
    if minimum is not None and _nowpayments_decimal(price_amount, Decimal("0")) < minimum:
        raise RuntimeError(
            f"So tien {price_amount} thap hon muc toi thieu {minimum} cua mang {currency}"
        )

    payload = {
        "price_amount": float(price_amount),
        # Ta niem yet VND nhung quy doi san sang USDT, nen price_currency la
        # dong USDT chu khong phai "vnd" - de NOWPayments quy doi lan nua se ra
        # con so khac cai da hien cho khach.
        "price_currency": currency,
        "pay_currency": currency,
        "order_id": order_code,
        "order_description": f"Order {order_code}",
    }
    if NOWPAYMENTS_PAYOUT_CURRENCY:
        payload["payout_currency"] = NOWPAYMENTS_PAYOUT_CURRENCY
    callback_url = nowpayments_callback_url()
    if callback_url:
        payload["ipn_callback_url"] = callback_url

    body = await _nowpayments_request("POST", "/payment", payload)

    pay_address = str(body.get("pay_address") or "").strip()
    pay_amount = _nowpayments_decimal(body.get("pay_amount"))
    if not pay_address or pay_amount is None or pay_amount <= 0:
        raise RuntimeError("NOWPayments khong tra ve pay_address/pay_amount hop le")

    return {
        "payment_id": str(body.get("payment_id") or "").strip(),
        "pay_address": pay_address,
        "pay_amount": pay_amount,
        "pay_currency": str(body.get("pay_currency") or currency).strip().lower(),
        # payin_extra_id la memo/tag cua vai mang. Bo qua no o mang can memo la
        # khach mat tien, nen phai chuyen tiep len giao dien.
        "payin_extra_id": str(body.get("payin_extra_id") or "").strip(),
        "rate": live_rate,
    }


async def create_nowpayments_invoice(order_code: str, amount_vnd: int) -> dict:
    """Hoa don mo tren trang NOWPayments, khach tu chon coin + mang o do.

    Tra ve cung dang voi create_nowpayments_payment nhung khong co dia chi:
    `invoice_url` thay cho `pay_address`, `payment_id` rong cho toi khi IPN
    dau tien bao ve (nowpayments_remember_payment_id).
    """
    from app.integrations.payments_core import convert_vnd_to_usdt, get_live_usdt_vnd_rate

    if not nowpayments_invoice_available():
        raise RuntimeError("NOWPayments invoice can PUBLIC_API_URL de nhan IPN")

    live_rate = await get_live_usdt_vnd_rate()
    price_amount = convert_vnd_to_usdt(amount_vnd, rate=live_rate)
    # Niem yet bang dong USDT dang dung cho cac nut mang co dinh, de so khach
    # thay trong bot va tren trang hoa don la mot.
    price_currency = NOWPAYMENTS_PAYOUT_CURRENCY or NOWPAYMENTS_CURRENCIES[0]
    payload = {
        "price_amount": float(price_amount),
        "price_currency": price_currency,
        "order_id": order_code,
        "order_description": f"Order {order_code}",
        "ipn_callback_url": nowpayments_callback_url(),
    }
    body = await _nowpayments_request("POST", "/invoice", payload)

    invoice_url = str(body.get("invoice_url") or "").strip()
    invoice_id = str(body.get("id") or "").strip()
    if not invoice_url.lower().startswith("https://") or not invoice_id:
        raise RuntimeError("NOWPayments khong tra ve invoice_url/id hop le")

    return {
        "payment_id": "",
        "pay_address": "",
        "pay_amount": _nowpayments_decimal(price_amount, Decimal("0")),
        "pay_currency": NOWPAYMENTS_INVOICE_CHOICE,
        "payin_extra_id": "",
        "rate": live_rate,
        "invoice_id": invoice_id,
        "invoice_url": invoice_url,
    }


def nowpayments_callback_url() -> str:
    """URL IPN. De trong PUBLIC_API_URL thi khong gui - NOWPayments se khong
    goi lai duoc va ta chi con duong poll."""
    base = str(PUBLIC_API_URL or "").strip().rstrip("/")
    if not base.lower().startswith(("http://", "https://")):
        return ""
    return f"{base}/webhook/nowpayments"


async def nowpayments_fetch_payment(payment_id: str) -> dict | None:
    """Doc lai trang thai mot payment. Dung cho duong poll du phong."""
    if not is_nowpayments_enabled():
        return None
    body = await _nowpayments_request("GET", f"/payment/{payment_id}")
    return nowpayments_normalize_payment(body)


async def nowpayments_poll_pending_payments() -> list:
    """Hoi lai tung payment dang cho - luoi do cho cac don IPN khong toi.

    NOWPayments ngung gui IPN sau khi payment het han, nhung tien van vao duoc.
    Khong co vong nay thi khach tra muon mat tien im lang.
    """
    if not is_nowpayments_enabled():
        return []

    results = []
    for reference_code, details in iter_pending_nowpayments_records():
        payment_id = str(details.get("nowpayments_payment_id") or "").strip()
        if not payment_id:
            continue
        try:
            normalized = await nowpayments_fetch_payment(payment_id)
        except Exception as exc:
            logger.warning("NOWPayments poll %s that bai: %s", payment_id, exc)
            continue
        if normalized and normalized["order_code"] == reference_code:
            results.append(normalized)
    return results


def iter_pending_nowpayments_records():
    """(ma, ban ghi) cua moi thu dang cho tra bang NOWPayments."""
    for order_code, details in list(pending_orders.items()):
        if not isinstance(details, dict):
            continue
        if details.get("provider") != "nowpayments" or details.get("status") != "pending_payment":
            continue
        yield str(order_code), details
    for topup_code, details in list(pending_user_topups.items()):
        if not isinstance(details, dict):
            continue
        if details.get("provider") != "nowpayments":
            continue
        yield str(topup_code), details


def nowpayments_qr_photo(pay_address: str):
    """QR chua dia chi nhan tien de khach quet bang vi."""
    if not pay_address:
        return None
    from urllib.parse import quote as _quote

    return f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={_quote(str(pay_address), safe='')}"


def nowpayments_invoice_button_label(user_id=None) -> str:
    return lt(user_id, "🌐 Mở trang thanh toán", "🌐 Open payment page", "🌐 打开支付页面")


def nowpayments_invoice_choice_label(user_id=None) -> str:
    return lt(user_id, "Coin khác (trang NOWPayments)", "Other coin (NOWPayments page)", "其他币种（NOWPayments 页面）")


def build_nowpayments_checkout_keyboard(order_code: str, pay_address: str, amount_text: str, user_id=None, invoice_url: str = ""):
    rows = []
    if invoice_url:
        rows.append([InlineKeyboardButton(nowpayments_invoice_button_label(user_id), url=invoice_url)])
    if pay_address:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép địa chỉ", "📋 Copy address", "📋 复制地址"),
            copy_text=CopyTextButton(pay_address),
        )])
    # Hoa don: so tien that do trang NOWPayments quyet dinh theo coin khach chon,
    # copy con so USDT uoc tinh chi gay nham.
    if amount_text and not invoice_url:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép số tiền", "📋 Copy amount", "📋 复制金额"),
            copy_text=CopyTextButton(amount_text),
        )])
    rows.append([InlineKeyboardButton(_cancel_payment_label(user_id), callback_data=f"cancel_order:{order_code}")])
    return InlineKeyboardMarkup(rows)

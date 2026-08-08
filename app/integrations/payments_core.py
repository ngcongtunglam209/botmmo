import time


REQUIRED_GROUP_MEMBERSHIP_CACHE_TTL_SECONDS = 300
REQUIRED_GROUP_NON_MEMBER_CACHE_TTL_SECONDS = 8
_required_group_membership_cache = {}


async def _is_required_group_member(update, *, force_refresh: bool = False) -> bool:
    if not REQUIRED_GROUP_ID:
        return True
    user_id = update.effective_user.id
    now = time.monotonic()
    cached = _required_group_membership_cache.get(user_id)
    if (
        not force_refresh
        and isinstance(cached, tuple)
        and len(cached) == 2
        and float(cached[1]) > now
    ):
        return bool(cached[0])

    member = await update.get_bot().get_chat_member(
        chat_id=REQUIRED_GROUP_ID,
        user_id=user_id,
    )
    is_joined = member.status in ["member", "creator", "administrator"] or (
        member.status == "restricted" and getattr(member, "is_member", False)
    )
    cache_ttl = (
        REQUIRED_GROUP_MEMBERSHIP_CACHE_TTL_SECONDS
        if is_joined
        else REQUIRED_GROUP_NON_MEMBER_CACHE_TTL_SECONDS
    )
    _required_group_membership_cache[user_id] = (is_joined, now + cache_ttl)
    if len(_required_group_membership_cache) > 10_000:
        expired_user_ids = [
            cached_user_id
            for cached_user_id, cached_value in _required_group_membership_cache.items()
            if not isinstance(cached_value, tuple)
            or len(cached_value) != 2
            or float(cached_value[1]) <= now
        ]
        for cached_user_id in expired_user_ids:
            _required_group_membership_cache.pop(cached_user_id, None)
    logger.debug("Membership check: user_id=%s status=%s is_member=%s", user_id, member.status, is_joined)
    return is_joined


async def check_if_banned(update) -> bool:
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if user_id in banned_users:
        message = f"{E_LIMIT} Bạn đã bị cấm sử dụng bot này. Vui lòng liên hệ Admin."
        if update.message: await update.message.reply_text(message)
        elif update.callback_query: await safe_answer(update.callback_query, message, show_alert=True)
        return True

    from app.core.config_env import ADMIN_USER_ID
    if user_id != ADMIN_USER_ID and REQUIRED_GROUP_ID and SUPPORT_GROUP_LINK:
        try:
            is_joined = await _is_required_group_member(update)
        except Exception as e:
            logger.exception("Membership check failed for user_id=%s: %s", user_id, e)
            is_joined = False
        if not is_joined:
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(lt(user_id, "Tham gia nhóm", "Join the group", "加入群组"), url=SUPPORT_GROUP_LINK)],
                [InlineKeyboardButton(
                    lt(user_id, "✅ Đã tham gia · Kiểm tra lại", "✅ Joined · Check again", "✅ 已加入 · 重新检查"),
                    callback_data="check_membership",
                )],
            ])
            msg = lt(
                user_id,
                "⚠️ Bạn cần tham gia nhóm Lâm Shop trước khi dùng bot.",
                "⚠️ Please join the Lâm Shop group before using the bot.",
                "⚠️ 使用机器人前请先加入 Lâm Shop 群组。",
            )
            if update.message:
                await update.message.reply_text(msg, reply_markup=markup)
            elif update.callback_query:
                await safe_answer(update.callback_query, msg, show_alert=True)
                try:
                    await update.callback_query.message.reply_text(msg, reply_markup=markup)
                except Exception:
                    pass
            return True
    return False


async def handle_membership_check(update) -> None:
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    query = update.callback_query
    user_id = update.effective_user.id if update.effective_user else None
    try:
        is_joined = await _is_required_group_member(update, force_refresh=True)
    except Exception as e:
        logger.exception("Membership callback check failed for user_id=%s: %s", user_id, e)
        await query.answer(
            lt(
                user_id,
                f"Không kiểm tra được tư cách thành viên: {e}",
                f"Could not check your membership: {e}",
                f"无法检查群成员身份：{e}",
            ),
            show_alert=True,
        )
        return
    if is_joined:
        await query.answer(lt(user_id, "Xác minh thành công", "Verified", "验证成功"))
        await query.edit_message_text(
            lt(
                user_id,
                "✅ Đã xác minh bạn tham gia nhóm. Bấm tiếp tục để dùng bot.",
                "✅ Membership verified. Tap continue to use the bot.",
                "✅ 已验证您已加入群组。点击继续即可使用机器人。",
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(lt(user_id, "🚀 Tiếp tục", "🚀 Continue", "🚀 继续"), callback_data="back_to_main")
            ]]),
        )
    else:
        await query.answer(
            lt(
                user_id,
                "Bot chưa thấy bạn trong nhóm. Hãy tham gia rồi thử lại.",
                "We cannot see you in the group yet. Join it and try again.",
                "机器人尚未在群里看到您，请加入后重试。",
            ),
            show_alert=True,
        )


async def clear_user_state(context):
    keys_to_clear = [
        'state', 'purchase_email', 'purchase_coupon_code', 'report_order_code',
        'report_photo_id', 'report_photo_chat_id', 'report_photo_message_id',
        'support_query', 'reply_to_user_id', 'store_coupon_applied',
        'store_coupon_discount', 'store_coupon_prod_id', 'store_coupon_qty',
        'pending_manual_order', 'waiting_message_id', 'waiting_chat_id',
        'admin_waiting_message_id', 'api_rotate_source_key', 'api_rotate_source_chat_id',
        'api_rotate_source_message_id', 'api_rotate_confirm_chat_id', 'api_rotate_confirm_message_id',
        'warranty_claim_order', 'warranty_description',
        'refund_bank_order_code',
    ]
    for key in keys_to_clear: context.user_data.pop(key, None)

def get_active_store_coupon_context(context, prod_id: str, qty: int):
    coupon_code = context.user_data.get('store_coupon_applied')
    discount = int(context.user_data.get('store_coupon_discount', 0) or 0)
    coupon_prod_id = context.user_data.get('store_coupon_prod_id')
    coupon_qty = int(context.user_data.get('store_coupon_qty', 0) or 0)
    if not coupon_code or discount <= 0: return None, 0
    if coupon_prod_id != prod_id or coupon_qty != int(qty): return None, 0
    return str(coupon_code).upper(), discount

def clear_store_coupon_context(context):
    for key in ('store_coupon_applied', 'store_coupon_discount', 'store_coupon_prod_id', 'store_coupon_qty'):
        context.user_data.pop(key, None)

def is_bank_transfer_enabled() -> bool:
    """QR chuyen khoan chay qua SePay (webhook + poll doi soat)."""
    from app.core.config_env import ENABLE_PAYMENT_SEPAY
    return bool(ENABLE_PAYMENT_SEPAY)

def is_usdt_payment_enabled() -> bool:
    """USDT chay hoan toan qua RPay (app/integrations/rpay_api.py)."""
    from app.integrations.rpay_api import is_rpay_enabled
    return is_rpay_enabled()

def _sanitize_invoice_text(value: str, fallback: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value: raw_value = fallback
    raw_value = raw_value.replace('"', " ").replace("'", " ")
    cleaned = re.sub(r"[^A-Za-z0-9 _.,:/()\-+#]", " ", raw_value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned or fallback)[:200]

def _decimal_to_plain_text(value) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text

def _cancel_payment_label(user_id=None) -> str:
    return lt(user_id, "⬅️ Hủy giao dịch", "⬅️ Cancel payment", "⬅️ 取消付款")


def _decimal_to_fixed_text(value, decimals: int) -> str:
    return format(value, f".{decimals}f")


def _get_usdt_quantizer():
    return Decimal("1").scaleb(-USDT_DISPLAY_DECIMALS)


_cached_live_usdt_rate = None
_cached_live_usdt_rate_time = 0


async def get_live_usdt_vnd_rate():
    """Ty gia USDT/VND lay tu bang quang cao P2P cong khai, cache 5 phut.

    Day chi la nguon gia tham khao (san pham niem yet VND, RPay thu USDT) nen
    khong dinh gi den cong thanh toan. Loi mang -> rot ve
    USDT_RATE_VND_PER_USDT cau hinh tay.
    """
    global _cached_live_usdt_rate, _cached_live_usdt_rate_time
    import time, httpx
    from decimal import Decimal
    now = time.time()
    if _cached_live_usdt_rate and now - _cached_live_usdt_rate_time < 300:
        return _cached_live_usdt_rate
    try:
        payload = {"fiat": "VND", "page": 1, "rows": 1, "tradeType": "SELL", "asset": "USDT", "countries": [], "proMerchantAds": False, "shieldMerchantAds": False, "publisherType": None}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(USDT_RATE_SOURCE_URL, json=payload)
            data = resp.json()
            price = data['data'][0]['adv']['price']
            _cached_live_usdt_rate = Decimal(str(price))
            _cached_live_usdt_rate_time = now
            return _cached_live_usdt_rate
    except Exception:
        return USDT_RATE_VND_PER_USDT


def get_cached_usdt_rate() -> Decimal:
    from decimal import Decimal
    if _cached_live_usdt_rate:
        return _cached_live_usdt_rate
    return Decimal(str(USDT_RATE_VND_PER_USDT))


def convert_vnd_to_usdt(amount_vnd: int, rate: Decimal = None, quantizer=None):
    """VND -> USDT, lam tron LEN de shop khong bao gio thu thieu."""
    amount_decimal = Decimal(str(int(amount_vnd or 0)))
    if amount_decimal <= 0: raise ValueError("USDT amount must be greater than 0")
    rate = rate or USDT_RATE_VND_PER_USDT
    if rate <= 0: raise ValueError("Khong co ty gia USDT/VND (USDT_RATE_VND_PER_USDT chua dat va khong lay duoc gia live)")
    quantizer = quantizer or _get_usdt_quantizer()
    return (amount_decimal / rate).quantize(quantizer, rounding=ROUND_UP)


async def create_rpay_order(order_code: str, amount_vnd: int, goods_name: str, goods_detail: str) -> dict:
    """Quy doi VND -> USDT roi tao hoa don RPay cho `order_code`.

    Tra ve khoi `data` cua RPay, bo sung cac khoa ta tu tinh:
    `request_id`, `amount_usdt`, `amount_text`, `rate`, `rate_text`.
    """
    from app.integrations.rpay_api import rpay_build_request_id, rpay_create_invoice

    live_rate = await get_live_usdt_vnd_rate()
    quantizer = _get_usdt_quantizer()
    amount_usdt = convert_vnd_to_usdt(amount_vnd, rate=live_rate, quantizer=quantizer)
    request_id = rpay_build_request_id(order_code)

    invoice = await rpay_create_invoice(
        order_code=order_code,
        request_id=request_id,
        amount_usdt=amount_usdt,
        name=_sanitize_invoice_text(goods_name, "Digital Goods"),
        description=_sanitize_invoice_text(goods_detail, order_code),
        expire_minutes=ORDER_EXPIRATION_SECONDS // 60,
    )
    invoice["request_id"] = request_id
    invoice["amount_usdt"] = amount_usdt
    invoice["amount_text"] = _decimal_to_fixed_text(amount_usdt, USDT_DISPLAY_DECIMALS)
    invoice["rate"] = live_rate
    invoice["rate_text"] = _decimal_to_plain_text(live_rate)
    invoice["display_decimals"] = USDT_DISPLAY_DECIMALS
    return invoice


def rpay_qr_photo(invoice: dict):
    """Anh QR gui kem hoa don.

    RPay tra `qrcode` la data URL base64 - Telegram khong nhan data URL nen
    phai giai ra bytes. Thieu qrcode thi dung `qr_content` (dia chi vi) qua
    dich vu QR cong khai.
    """
    import base64, io

    raw = str(invoice.get("qrcode") or "").strip()
    if raw.startswith("data:") and "," in raw:
        try:
            payload = base64.b64decode(raw.split(",", 1)[1], validate=False)
            if payload:
                return io.BytesIO(payload)
        except (ValueError, TypeError, base64.binascii.Error):
            pass
    if raw.startswith("http"):
        return raw
    qr_content = str(invoice.get("qr_content") or invoice.get("address") or "").strip()
    if not qr_content:
        return None
    from urllib.parse import quote
    return f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={quote(qr_content, safe='')}"


def build_rpay_checkout_keyboard(invoice: dict, order_code: str, user_id=None):
    rows = []
    url_payment = str(invoice.get("url_payment") or "").strip()
    address = str(invoice.get("address") or "").strip()
    amount_text = str(invoice.get("amount_text") or "").strip()
    if url_payment.startswith("http"):
        rows.append([InlineKeyboardButton(
            lt(user_id, "🌐 Mở trang thanh toán", "🌐 Open payment page", "🌐 打开支付页面"),
            url=url_payment,
        )])
    if address:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép địa chỉ ví", "📋 Copy wallet address", "📋 复制钱包地址"),
            copy_text=CopyTextButton(address),
        )])
    if amount_text:
        rows.append([InlineKeyboardButton(
            lt(user_id, "📋 Sao chép số tiền", "📋 Copy amount", "📋 复制金额"),
            copy_text=CopyTextButton(amount_text),
        )])
    rows.append([InlineKeyboardButton(_cancel_payment_label(user_id), callback_data=f"cancel_order:{order_code}")])
    return InlineKeyboardMarkup(rows)


# SQLite chay WAL nen con ghi them <db>-wal va <db>-shm ben canh file. Ca ba
# phai nam cung mot thu muc duoc mount ra host, khong thi WAL chua checkpoint
# se mat khi container dung. Dat DB_PATH tro vao thu muc do.
#
# Mac dinh la duong dan tuyet doi theo goc project, khong phai "database.sqlite"
# tuong doi: app/web/settings.py cung giai ra dung duong nay, va mot duong tuong
# doi se tro sang file khac neu process doi working directory.
DB_PATH = os.getenv("DB_PATH", "").strip() or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "database.sqlite",
)

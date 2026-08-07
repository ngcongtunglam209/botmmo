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
                [InlineKeyboardButton("Tham gia nhóm", url=SUPPORT_GROUP_LINK)],
                [InlineKeyboardButton("✅ Đã tham gia · Kiểm tra lại", callback_data="check_membership")],
            ])
            msg = "⚠️ Bạn phải tham gia nhóm Lâm Shop để có thể sử dụng Bot!"
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
    try:
        is_joined = await _is_required_group_member(update, force_refresh=True)
    except Exception as e:
        logger.exception("Membership callback check failed for user_id=%s: %s", update.effective_user.id, e)
        await query.answer(f"Không kiểm tra được thành viên: {e}", show_alert=True)
        return
    if is_joined:
        await query.answer("Xác minh thành công!")
        await query.edit_message_text(
            "✅ Đã xác minh bạn tham gia nhóm. Bấm tiếp tục để dùng bot.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Tiếp tục", callback_data="back_to_main")
            ]]),
        )
    else:
        await query.answer("Bot chưa thấy bạn trong nhóm. Hãy tham gia rồi thử lại.", show_alert=True)


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

def is_binance_pay_enabled() -> bool:
    return bool(BINANCE_PAY_CERT_SN and BINANCE_PAY_SECRET_KEY and BINANCE_PAY_RATE_VND_PER_USDT > 0)

def is_usdt_bep20_enabled() -> bool:
    return bool(USDT_BEP20_WALLET_ADDRESS and USDT_TRC20_RATE_VND_PER_USDT > 0)

def is_usdt_trc20_enabled() -> bool:
    """Compatibility alias for checkout code migrated from TRC20 to BEP20."""
    return is_usdt_bep20_enabled()

def is_binance_spot_enabled() -> bool:
    from app.core.config_env import BINANCE_SPOT_API_KEY, BINANCE_SPOT_API_SECRET, ENABLE_PAYMENT_BINANCE_SPOT, USDT_TRC20_RATE_VND_PER_USDT
    if not ENABLE_PAYMENT_BINANCE_SPOT: return False
    return bool(BINANCE_SPOT_API_KEY and BINANCE_SPOT_API_SECRET and USDT_TRC20_RATE_VND_PER_USDT > 0)

def is_binance_pay_id_enabled() -> bool:
    return bool(BINANCE_PAY_ID and is_binance_spot_enabled())

def _sanitize_binance_goods_text(value: str, fallback: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value: raw_value = fallback
    raw_value = raw_value.replace('"', " ").replace("'", " ")
    cleaned = re.sub(r"[^A-Za-z0-9 _.,:/()\-+#]", " ", raw_value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned or fallback)[:256]

def _decimal_to_plain_text(value) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text

def convert_vnd_to_binance_usdt(amount_vnd: int):
    amount_decimal = Decimal(str(int(amount_vnd or 0)))
    if amount_decimal <= 0: raise ValueError("Binance amount must be greater than 0")
    if BINANCE_PAY_RATE_VND_PER_USDT <= 0: raise ValueError("BINANCE_PAY_RATE_VND_PER_USDT is not configured")
    return (amount_decimal / BINANCE_PAY_RATE_VND_PER_USDT).quantize(Decimal("0.00000001"), rounding=ROUND_UP)

def _build_binance_signature(timestamp_ms: str, nonce: str, body_json: str) -> str:
    payload = f"{timestamp_ms}\n{nonce}\n{body_json}\n"
    signature = hmac.new(BINANCE_PAY_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha512).hexdigest()
    return signature.upper()

def _build_binance_headers(body_json: str):
    timestamp_ms = str(int(time.time() * 1000))
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    return {
        "Content-Type": "application/json",
        "BinancePay-Timestamp": timestamp_ms,
        "BinancePay-Nonce": nonce,
        "BinancePay-Certificate-SN": BINANCE_PAY_CERT_SN,
        "BinancePay-Signature": _build_binance_signature(timestamp_ms, nonce, body_json),
    }

async def binance_pay_request(path: str, payload: dict) -> dict:
    if not is_binance_pay_enabled(): raise RuntimeError("Binance Pay is not configured")
    body_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    url = f"{BINANCE_PAY_HOST}{path}"
    headers = _build_binance_headers(body_json)
    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=10.0)
    owns_client = client is not http_client
    try:
        response = await client.post(url, content=body_json.encode("utf-8"), headers=headers)
        response_text = response.text
        try: data = response.json()
        except ValueError: data = {}
    finally:
        if owns_client: await client.aclose()
    if response.status_code >= 400:
        error_code = str(data.get("code") or "").strip()
        error_message = str(data.get("errorMessage") or data.get("msg") or response_text or f"HTTP {response.status_code}").strip()
        raise RuntimeError(f"HTTP {response.status_code} Binance Pay error{' ' + error_code if error_code else ''}: {error_message[:500]}")
    if data.get("status") != "SUCCESS" or data.get("code") != "000000":
        raise RuntimeError(f"Binance Pay error {data.get('code') or 'UNKNOWN'}: {data.get('errorMessage') or data.get('msg') or 'request failed'}")
    return data.get("data") or {}

async def create_binance_pay_order(order_code: str, amount_vnd: int, goods_name: str, goods_detail: str, reference_goods_id: str, buyer_email: str = "") -> dict:
    order_amount = convert_vnd_to_binance_usdt(amount_vnd)
    order_expire_time = int((time.time() + ORDER_EXPIRATION_SECONDS) * 1000)
    sanitized_goods_name = _sanitize_binance_goods_text(goods_name, "Digital Goods")
    sanitized_goods_detail = _sanitize_binance_goods_text(goods_detail, "Telegram order")
    payload = {
        "env": {"terminalType": BINANCE_PAY_TERMINAL_TYPE},
        "merchantTradeNo": order_code,
        "orderAmount": float(order_amount),
        "currency": "USDT",
        "description": sanitized_goods_detail,
        "goodsDetails": [{
            "goodsType": "02",
            "goodsCategory": BINANCE_PAY_GOODS_CATEGORY,
            "referenceGoodsId": _sanitize_binance_goods_text(reference_goods_id, "DIGITAL-GOODS")[:64],
            "goodsName": sanitized_goods_name,
            "goodsDetail": sanitized_goods_detail,
        }],
        "orderExpireTime": order_expire_time,
        "passThroughInfo": f"user_order={order_code}",
    }
    if BINANCE_PAY_SUB_MERCHANT_ID: payload["merchant"] = {"subMerchantId": BINANCE_PAY_SUB_MERCHANT_ID}
    if BINANCE_PAY_SUPPORT_PAY_CURRENCY: payload["supportPayCurrency"] = BINANCE_PAY_SUPPORT_PAY_CURRENCY
    if buyer_email: payload["buyer"] = {"buyerEmail": str(buyer_email).strip().lower()}
    data = await binance_pay_request("/binancepay/openapi/v3/order", payload)
    data["quoted_usdt"] = _decimal_to_plain_text(order_amount)
    data["vnd_rate"] = _decimal_to_plain_text(BINANCE_PAY_RATE_VND_PER_USDT)
    return data

async def query_binance_pay_order(order_code: str = "", prepay_id: str = "") -> dict:
    payload = {}
    if prepay_id: payload["prepayId"] = prepay_id
    elif order_code: payload["merchantTradeNo"] = order_code
    else: raise ValueError("order_code or prepay_id is required")
    return await binance_pay_request("/binancepay/openapi/v2/order/query", payload)

async def close_binance_pay_order(order_code: str = "", prepay_id: str = "") -> bool:
    payload = {}
    if prepay_id: payload["prepayId"] = prepay_id
    elif order_code: payload["merchantTradeNo"] = order_code
    else: raise ValueError("order_code or prepay_id is required")
    data = await binance_pay_request("/binancepay/openapi/order/close", payload)
    return bool(data)

async def fetch_binance_spot_deposits(start_timestamp_ms: int = 0) -> list[dict]:
    from app.core.config_env import BINANCE_SPOT_API_KEY, BINANCE_SPOT_API_SECRET
    if not is_binance_spot_enabled(): return []
    import hmac, hashlib, time, httpx
    from urllib.parse import urlencode
    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=10.0)
    owns_client = client is not http_client
    try:
        server_time_ms = int(time.time() * 1000)
        try:
            time_resp = await client.get("https://api.binance.com/api/v3/time")
            server_time_ms = time_resp.json().get("serverTime", server_time_ms)
        except Exception:
            pass # fallback to local time
            
        params = {"timestamp": server_time_ms, "recvWindow": 10000}
        if start_timestamp_ms > 0: params["startTime"] = int(start_timestamp_ms)
        query_string = urlencode(params)
        signature = hmac.new(BINANCE_SPOT_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/sapi/v1/capital/deposit/hisrec?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": BINANCE_SPOT_API_KEY}
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as exc:
            logger.error(f"Binance Spot API error: {exc} | Response: {exc.response.text}")
            return []
        except Exception as e:
            logger.error(f"Binance Spot API error: {e}")
            return []
    finally:
        if owns_client:
            await client.aclose()

def build_binance_checkout_keyboard(binance_order: dict, order_code: str):
    rows = []
    checkout_url = str(binance_order.get("checkoutUrl") or "").strip()
    universal_url = str(binance_order.get("universalUrl") or "").strip()
    if checkout_url: rows.append([InlineKeyboardButton("Open Binance Checkout", url=checkout_url)])
    elif universal_url: rows.append([InlineKeyboardButton("Open Binance Pay", url=universal_url)])
    rows.append([InlineKeyboardButton("⬅️ Hủy giao dịch", callback_data=f"cancel_order:{order_code}")])
    return InlineKeyboardMarkup(rows)

def _get_usdt_trc20_quantizer():
    return Decimal("1").scaleb(-USDT_TRC20_TOKEN_DECIMALS)

def _get_usdt_trc20_user_quantizer():
    return Decimal("1").scaleb(-min(3, USDT_TRC20_TOKEN_DECIMALS))

def _decimal_to_fixed_text(value, decimals: int) -> str:
    return format(value, f".{decimals}f")

def convert_vnd_to_usdt_trc20(amount_vnd: int, rate: Decimal = None, quantizer=None):
    amount_decimal = Decimal(str(int(amount_vnd or 0)))
    if amount_decimal <= 0: raise ValueError("USDT TRC20 amount must be greater than 0")
    rate = rate or USDT_TRC20_RATE_VND_PER_USDT
    if rate <= 0: raise ValueError("USDT_TRC20_RATE_VND_PER_USDT is not configured")
    quantizer = quantizer or _get_usdt_trc20_quantizer()
    return (amount_decimal / rate).quantize(quantizer, rounding=ROUND_UP)

_cached_live_usdt_rate = None
_cached_live_usdt_rate_time = 0

async def get_live_usdt_vnd_rate():
    global _cached_live_usdt_rate, _cached_live_usdt_rate_time
    import time, httpx
    from decimal import Decimal
    now = time.time()
    if _cached_live_usdt_rate and now - _cached_live_usdt_rate_time < 300:
        return _cached_live_usdt_rate
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        payload = {"fiat": "VND", "page": 1, "rows": 1, "tradeType": "SELL", "asset": "USDT", "countries": [], "proMerchantAds": False, "shieldMerchantAds": False, "publisherType": None}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            price = data['data'][0]['adv']['price']
            _cached_live_usdt_rate = Decimal(str(price))
            _cached_live_usdt_rate_time = now
            return _cached_live_usdt_rate
    except Exception:
        return USDT_TRC20_RATE_VND_PER_USDT

def get_cached_usdt_rate() -> Decimal:
    from decimal import Decimal
    if _cached_live_usdt_rate:
        return _cached_live_usdt_rate
    return Decimal(str(USDT_TRC20_RATE_VND_PER_USDT))

async def get_usdt_trc20_order_quote(order_code: str, amount_vnd: int) -> dict:
    live_rate = await get_live_usdt_vnd_rate()
    user_quantizer = _get_usdt_trc20_user_quantizer()
    display_decimals = abs(user_quantizer.as_tuple().exponent)
    base_amount = convert_vnd_to_usdt_trc20(amount_vnd, rate=live_rate, quantizer=user_quantizer)
    unique_delta = Decimal("0")
    exact_amount = base_amount
    amount_text = _decimal_to_fixed_text(exact_amount, display_decimals)
    token_scale = Decimal(10) ** USDT_TRC20_TOKEN_DECIMALS
    quant = str(int((exact_amount * token_scale).to_integral_value(rounding=ROUND_UP)))
    return {
        "currency": "USDT", "network": "TRON (TRC20)", "base_amount": base_amount, "unique_delta": unique_delta,
        "amount_decimal": exact_amount, "amount_text": amount_text, "amount_quant": quant,
        "rate_text": _decimal_to_plain_text(live_rate), "wallet_address": USDT_TRC20_WALLET_ADDRESS, "display_decimals": display_decimals,
        "live_rate": live_rate
    }

def _legacy_build_usdt_trc20_checkout_keyboard(order_code: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Hủy giao dịch", callback_data=f"cancel_order:{order_code}")]])

def build_usdt_trc20_checkout_keyboard(order_code: str, wallet_address: str = ""):
    rows = []
    wallet_address = str(wallet_address or "").strip()
    if BINANCE_PAY_ID:
        rows.append([InlineKeyboardButton("📋 Sao chép ID Binance", copy_text=CopyTextButton(BINANCE_PAY_ID))])
    if wallet_address:
        rows.append([InlineKeyboardButton("📋 Sao chép địa chỉ ví BEP20", copy_text=CopyTextButton(wallet_address))])
    rows.append([InlineKeyboardButton("⬅️ Hủy giao dịch", callback_data=f"cancel_order:{order_code}")])
    return InlineKeyboardMarkup(rows)

async def _bsc_rpc(client, method: str, params: list):
    response = await client.post(
        BSC_RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        headers={"Accept": "application/json", "User-Agent": "LamShopBot/2.0"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"BSC RPC {method} failed: {payload['error']}")
    return payload.get("result")

_bsc_last_scanned_block = None

async def fetch_usdt_bep20_transfers(address: str, start_timestamp_ms: int = 0, limit: int = 50, max_pages: int = 3) -> list[dict]:
    global _bsc_last_scanned_block
    if not address or not BSC_RPC_URL or not BSC_USDT_CONTRACT_ADDRESS:
        return []
    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=10.0)
    owns_client = client is not http_client
    transfers = []
    try:
        latest_block = int(await _bsc_rpc(client, "eth_blockNumber", []), 16)
        confirmed_block = max(0, latest_block - int(BSC_CONFIRMATIONS))
        destination_topic = "0x" + ("0" * 24) + address.lower().removeprefix("0x")
        transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        chunk_size = 5000
        first_block = max(0, confirmed_block - (chunk_size * max_pages) + 1)
        if _bsc_last_scanned_block is not None:
            first_block = max(first_block, int(_bsc_last_scanned_block) + 1)
        raw_logs = []
        for from_block in range(first_block, confirmed_block + 1, chunk_size):
            to_block = min(confirmed_block, from_block + chunk_size - 1)
            batch = await _bsc_rpc(client, "eth_getLogs", [{
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "address": BSC_USDT_CONTRACT_ADDRESS,
                "topics": [transfer_topic, None, destination_topic],
            }]) or []
            raw_logs.extend(batch)

        block_timestamps = {}
        for event in reversed(raw_logs):
            block_hex = str(event.get("blockNumber") or "")
            tx_hash = str(event.get("transactionHash") or "").strip()
            if not block_hex or not tx_hash:
                continue
            if block_hex not in block_timestamps:
                block = await _bsc_rpc(client, "eth_getBlockByNumber", [block_hex, False]) or {}
                block_timestamps[block_hex] = int(str(block.get("timestamp") or "0x0"), 16) * 1000
            timestamp_ms = block_timestamps[block_hex]
            if start_timestamp_ms > 0 and timestamp_ms < int(start_timestamp_ms):
                continue
            raw_amount = int(str(event.get("data") or "0x0"), 16)
            transfers.append({
                "hash": tx_hash,
                "amount_display": _decimal_to_plain_text(
                    Decimal(raw_amount) / (Decimal(10) ** USDT_TRC20_TOKEN_DECIMALS)
                ),
                "block_timestamp": timestamp_ms,
                "confirmed": True,
            })
            if len(transfers) >= limit:
                break
        _bsc_last_scanned_block = confirmed_block
    finally:
        if owns_client: await client.aclose()
    return transfers

async def fetch_usdt_trc20_transfers(address: str, start_timestamp_ms: int = 0, limit: int = 50, max_pages: int = 3) -> list[dict]:
    """Compatibility alias; the configured on-chain network is now BEP20."""
    return await fetch_usdt_bep20_transfers(address, start_timestamp_ms, limit, max_pages)

async def fetch_binance_pay_id_transactions(start_timestamp_ms: int = 0) -> list[dict]:
    from app.core.config_env import BINANCE_SPOT_API_KEY, BINANCE_SPOT_API_SECRET
    if not is_binance_spot_enabled(): return []
    import hmac, hashlib, time, httpx
    from urllib.parse import urlencode
    client = http_client if http_client and not http_client.is_closed else httpx.AsyncClient(timeout=10.0)
    owns_client = client is not http_client
    try:
        server_time_ms = int(time.time() * 1000)
        try:
            time_resp = await client.get("https://api.binance.com/api/v3/time")
            server_time_ms = time_resp.json().get("serverTime", server_time_ms)
        except Exception:
            pass
            
        params = {"timestamp": server_time_ms}
        if start_timestamp_ms > 0: params["startTime"] = int(start_timestamp_ms)
        query_string = urlencode(params)
        signature = hmac.new(BINANCE_SPOT_API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        url = f"https://api.binance.com/sapi/v1/pay/transactions?{query_string}&signature={signature}"
        headers = {"X-MBX-APIKEY": BINANCE_SPOT_API_KEY}
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if str(data.get("code")) == "000000":
                return data.get("data") or []
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(f"Binance Pay History API error: {exc} | Response: {exc.response.text}")
            return []
        except Exception as e:
            logger.error(f"Binance Pay History API error: {e}")
            return []
    finally:
        if owns_client:
            await client.aclose()

DB_PATH = "database.sqlite"

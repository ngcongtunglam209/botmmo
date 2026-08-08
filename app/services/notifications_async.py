
def mask_name(name: str) -> str:
    if not name: return "Khách hàng"
    name = name.strip()
    if len(name) <= 3: return name[0] + "***"
    parts = name.split()
    if len(parts) > 1:
        return " ".join(parts[:-1]) + " " + parts[-1][0] + "***"
    return name[:2] + "***"

async def send_live_order_notification(context: ContextTypes.DEFAULT_TYPE, full_name: str, amount: int, product_name: str = "Sản phẩm", quantity: int = 1, order_code: str = None):
    """
    UPDATED: Gửi thông báo đơn hàng mới đến channel
    Hỗ trợ store products
    """
    if not LIVE_ORDERS_CHANNEL_ID: return
    try:
        masked_name = mask_name(full_name)
        time_str = datetime.now().strftime('%H:%M %d/%m/%Y')
        
        # Format số lượng (chỉ hiện nếu > 1)
        qty_text = f" x{quantity}" if quantity > 1 else ""
        
        # Format mã đơn (nếu có)
        order_text = f"\n{E_TAG} <b>Mã đơn:</b> <code>{order_code}</code>" if order_code else ""
        
        msg = (
            f"{E_SUCCESS} <b>VỪA CÓ KHÁCH HÀNG MUA THÀNH CÔNG!</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách hàng:</b> {masked_name}\n"
            f"{E_TAG} <b>Sản phẩm:</b> {product_name}{qty_text}\n"
            f"{E_TAG} <b>Thanh toán:</b> {amount:,} VNĐ\n"
            f"{E_LOADING} <b>Thời gian:</b> {time_str}"
            f"{order_text}\n\n"
            f"{E_TIP} <i>Mua ngay tại: @{context.bot.username}</i>"
        )
        await context.bot.send_message(chat_id=LIVE_ORDERS_CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML)
        logger.info(f"{E_SUCCESS} Đã gửi live order notification: {product_name} - {amount:,}đ")
    except BadRequest as e:
        if "Chat not found" in str(e):
            logger.warning(f"{E_ERROR} Cảnh báo Live Orders: Bot chưa tham gia kênh {LIVE_ORDERS_CHANNEL_ID} hoặc ID kênh sai. Vui lòng kiểm tra lại.")
        else:
            logger.error(f"Lỗi gửi tin nhắn Live Orders (Telegram API): {e}")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi gửi tin nhắn Live Orders: {e}")

async def notify_admin_store_order(
    context: ContextTypes.DEFAULT_TYPE,
    order_code: str,
    user_id: int,
    full_name: str,
    username: str | None,
    product_name: str,
    quantity: int,
    amount: int,
    payment_method: str = "balance",
    items: list | None = None,
    delivery_method: str | None = None,
):
    payment_labels = {
        "balance": "Số dư",
        "bank_transfer": "Chuyển khoản",
        "usdt_trc20": "USDT TRC20",
        "binance_pay": "Binance Pay",
    }
    payment_label = payment_labels.get(str(payment_method or "").strip().lower(), str(payment_method or "N/A"))
    username_text = f" (@{html.escape(str(username))})" if username else ""

    preview_line = ""
    valid_items = [str(item).strip() for item in (items or []) if str(item).strip()]
    if valid_items:
        preview_items = valid_items[:3]
        preview_text = "\n".join(
            f"• <code>{html.escape(item)}</code>" for item in preview_items
        )
        if len(valid_items) > len(preview_items):
            preview_text += f"\n• ... và {len(valid_items) - len(preview_items)} item khác"
        preview_line = f"\n\n<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Nội dung đã gửi:</b>\n{preview_text}"


    delivery_line = ""
    if delivery_method:
        delivery_line = f"\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Delivery:</b> <code>{html.escape(str(delivery_method))}</code>"

    msg = (
        f"{E_SUCCESS} <b>ĐƠN HÀNG STORE MỚI</b>\n\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{html.escape(str(order_code))}</code>\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách:</b> {html.escape(str(full_name or 'N/A'))}{username_text} (ID: <code>{user_id}</code>)\n"
        f"{E_TAG} <b>Sản phẩm:</b> {html.escape(str(product_name))} x{int(quantity or 1)}\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Giá:</b> {int(amount or 0):,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Thanh toán:</b> {html.escape(payment_label)}"
        f"{delivery_line}"
        f"{preview_line}"
    )

    try:
        sent = await safe_send_admin(context.bot, msg)
        return sent is not None
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi gửi thông báo store order cho admin: {e}")
        return False

async def _cleanup_blocked_users(blocked_ids: list):
    """Disable broadcasts without deleting wallet, orders, or financial history."""
    marked = 0
    blocked_at = time.time()
    for uid in blocked_ids:
        uid_str = str(uid)
        profile = user_data_db.get(uid_str)
        if not isinstance(profile, dict):
            continue
        profile["bot_blocked_at"] = blocked_at
        profile["broadcast_disabled"] = True
        marked += 1
    if marked:
        await save_data(force=True, tables=[USERS_FILE])
        logger.info(f"Disabled broadcasts for {marked} blocked users; financial data retained")
    return marked

async def broadcast_out_of_stock(context: ContextTypes.DEFAULT_TYPE, product_name: str, product_id: str = None):
    """
    NEW: Broadcast thông báo hết hàng cho toàn bộ users
    """

    
    # Tránh spam: Chỉ thông báo 1 lần cho mỗi product
    if product_id and product_id in notified_out_of_stock:
        logger.info(f"{E_LOADING} Bỏ qua broadcast hết hàng cho {product_name} (đã thông báo)")
        return
    
    # Đánh dấu đã thông báo
    if product_id:
        notified_out_of_stock.add(product_id)
    
    # Tạo message
    message = (
        f"{E_ERROR} <b>THÔNG BÁO HẾT HÀNG</b>\n\n"
        f"{E_TAG} Sản phẩm vừa hết hàng:\n"
        f"<b>{html.escape(product_name)}</b>\n\n"
        f"{E_SOS} Chúng tôi sẽ thông báo khi có lại hàng.\n"
        f"{E_GLOBE} Liên hệ Admin để đặt trước: @{ADMIN_USERNAME}"
    )
    
    success_count = 0
    fail_count = 0
    blocked_ids = []
    
    for user_id_str in list(user_data_db.keys()):
        try:
            user_id = int(user_id_str)
            profile = user_data_db.get(user_id_str, {})
            if user_id in banned_users or (isinstance(profile, dict) and profile.get("broadcast_disabled")):
                continue
            
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            success_count += 1
            await asyncio.sleep(0.05)
            
        except Forbidden:
            fail_count += 1
            blocked_ids.append(user_id_str)
        except (ValueError, TypeError, KeyError, IndexError) as e:
            fail_count += 1
            if fail_count <= 3:
                logger.warning(f"Lỗi broadcast đến user {user_id_str}: {e}")
    
    if blocked_ids:
        await _cleanup_blocked_users(blocked_ids)
    
    # Thông báo cho Admin
    admin_msg = (
        f"{E_SOS} <b>ĐÃ BROADCAST HẾT HÀNG</b>\n\n"
        f"{E_TAG} <b>Sản phẩm:</b> {product_name}\n"
        f"{E_SUCCESS} <b>Gửi thành công:</b> {success_count}\n"
        f"{E_LIMIT} <b>Thất bại:</b> {fail_count}\n"
        f"{E_STAT} <b>Tổng users:</b> {len(user_data_db)}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=admin_msg,
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Không gửi được báo cáo broadcast cho admin: {e}")
    
    logger.info(f"{E_SOS} Broadcast hết hàng '{product_name}': {success_count} thành công, {fail_count} thất bại")

def create_background_task(coro, *, fatal=False):
    """
    FIX BUG #6: Helper để track background tasks
    Tránh tasks bị cancel khi shutdown và memory leak
    """
    task = asyncio.create_task(coro)
    background_tasks.add(task)

    def _finish(completed):
        background_tasks.discard(completed)
        if completed.cancelled():
            return
        try:
            error = completed.exception()
        except asyncio.CancelledError:
            return
        if error is not None:
            logger.error("Background task failed", exc_info=(type(error), error, error.__traceback__))
            if fatal:
                logger.critical("Fatal background service failed; terminating for supervisor restart")
                os._exit(1)

    task.add_done_callback(_finish)
    return task

async def get_product_lock(product_id: str):
    """
    FIX BUG #5: Lấy lock cho product để tránh race condition
    """
    if product_id not in product_stock_locks:
        product_stock_locks[product_id] = asyncio.Lock()
    return product_stock_locks[product_id]

async def get_api_key_lock(api_key: str):
    """Per-API-key lock to avoid concurrent balance race conditions."""
    key = api_key or "__anonymous__"
    async with api_key_locks_guard:
        if key not in api_key_locks:
            api_key_locks[key] = asyncio.Lock()
        return api_key_locks[key]


async def get_refund_lock(order_code: str):
    """Serialize refund decisions for one order."""
    key = str(order_code or "").strip() or "__unknown__"
    async with refund_locks_guard:
        if key not in refund_locks:
            refund_locks[key] = asyncio.Lock()
        return refund_locks[key]


async def get_withdrawal_lock(request_id: str):
    """Serialize approval/rejection for one withdrawal request."""
    key = str(request_id or "").strip() or "__unknown__"
    async with withdrawal_locks_guard:
        if key not in withdrawal_locks:
            withdrawal_locks[key] = asyncio.Lock()
        return withdrawal_locks[key]


async def record_wallet_refund(
    context,
    *,
    order_code: str,
    user_id,
    amount: int,
    product_name: str,
    reason: str,
    order_data: dict | None = None,
):
    """Audit a wallet refund and offer an eligible bank payout consistently."""
    normalized_code = str(order_code or "").strip().upper()
    refund_amount = max(0, int(amount or 0))
    if not normalized_code or refund_amount <= 0:
        return None

    existing = order_index.get(normalized_code)
    record = existing if isinstance(existing, dict) else dict(order_data or {})
    now_ts = time.time()
    record.update(
        {
            "order_code": normalized_code,
            "user_id": user_id,
            "amount": int(record.get("amount", refund_amount) or refund_amount),
            "product_name": str(product_name or record.get("product_name") or "Sản phẩm"),
            "status": "♻️ Đã hoàn tiền (Ví Bot)",
            "refunded_at": now_ts,
            "refund_amount": refund_amount,
            "refund_reason": str(reason or "Lỗi đơn hàng"),
            "refund_target": "Ví Bot",
        }
    )
    record.setdefault("timestamp", now_ts)
    record.setdefault("type", "store_product")
    db_add_order(record, schedule_save=False)
    await save_data(force=True, tables=[HISTORY_FILE])

    if refund_amount >= BANK_REFUND_MIN_AMOUNT:
        safe_code = html.escape(normalized_code)
        safe_product = html.escape(str(record.get("product_name") or "Sản phẩm"))
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=lt(
                    user_id,
                    f"🏦 <b>TÙY CHỌN NHẬN TIỀN HOÀN</b>\n\n"
                    f"Mã đơn: <code>{safe_code}</code>\n"
                    f"Sản phẩm: {safe_product}\n"
                    f"Số tiền: <b>{refund_amount:,} VNĐ</b>\n\n"
                    "Tiền đã được hoàn vào Ví Bot. Bạn có thể yêu cầu chuyển khoản hoàn này về ngân hàng.",
                    f"🏦 <b>HOW WOULD YOU LIKE THE REFUND</b>\n\n"
                    f"Order code: <code>{safe_code}</code>\n"
                    f"Product: {safe_product}\n"
                    f"Amount: <b>{refund_amount:,} VND</b>\n\n"
                    "The money is back in your bot wallet. You can ask for it to be transferred to your bank instead.",
                    f"🏦 <b>退款方式</b>\n\n"
                    f"订单号：<code>{safe_code}</code>\n"
                    f"商品：{safe_product}\n"
                    f"金额：<b>{refund_amount:,} VND</b>\n\n"
                    "款项已退回机器人钱包。您也可以申请转账到银行账户。",
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    _btn(
                        lt(user_id, "Yêu cầu hoàn về ngân hàng", "Request a bank transfer", "申请银行转账"),
                        icon_id="5278467510604160626",
                        callback_data=f"refund_bank:{normalized_code}",
                    )
                ]]),
            )
            record["bank_refund_option_notified_at"] = time.time()
            await save_data(force=True, tables=[HISTORY_FILE])
        except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as exc:
            record["bank_refund_option_error"] = str(exc)[:300]
            await save_data(force=True, tables=[HISTORY_FILE])
            logger.error(f"Cannot notify bank-refund option for {normalized_code}: {exc}")
    return record

def _api_get_partner_wallet_owner_user_id(key_data: dict | None):
    if not isinstance(key_data, dict):
        return None
    try:
        owner_user_id = int(key_data.get("user_id", 0) or 0)
    except (TypeError, ValueError):
        owner_user_id = 0
    return owner_user_id if owner_user_id > 0 else None

def _api_get_partner_effective_balance(api_key: str | None = None, key_data: dict | None = None):
    normalized = key_data if isinstance(key_data, dict) else _api_normalize_partner_key(api_key)
    if normalized is None:
        return None

    try:
        legacy_balance = int(normalized.get("balance", 0) or 0)
    except (TypeError, ValueError):
        legacy_balance = 0

    owner_user_id = _api_get_partner_wallet_owner_user_id(normalized)
    if not owner_user_id:
        normalized["wallet_mode"] = "legacy_api_wallet"
        normalized["balance"] = legacy_balance
        return legacy_balance

    user_id_str = str(owner_user_id)
    profile = user_data_db.get(user_id_str)
    if not isinstance(profile, dict):
        profile = {"user_id": owner_user_id, "balance": 0}
        user_data_db[user_id_str] = profile

    try:
        user_balance = int(profile.get("balance", 0) or 0)
    except (TypeError, ValueError):
        user_balance = 0

    wallet_mode = str(normalized.get("wallet_mode") or "").strip().lower()
    if wallet_mode != "shared_user_wallet":
        merged_balance = max(0, user_balance) + max(0, legacy_balance)
        profile["balance"] = merged_balance
        normalized["wallet_mode"] = "shared_user_wallet"
        normalized["shared_wallet_enabled"] = True
        normalized["balance"] = merged_balance
        return merged_balance

    normalized["shared_wallet_enabled"] = True
    normalized["balance"] = user_balance
    return user_balance

def _api_set_partner_effective_balance_unlocked(
    api_key: str,
    key_data: dict | None,
    new_balance: int,
    *,
    reason: str | None = None,
):
    normalized = key_data if isinstance(key_data, dict) else _api_normalize_partner_key(api_key)
    if normalized is None:
        return None, None

    safe_new_balance = int(new_balance or 0)
    owner_user_id = _api_get_partner_wallet_owner_user_id(normalized)
    if owner_user_id:
        user_id_str = str(owner_user_id)
        profile = user_data_db.get(user_id_str)
        if not isinstance(profile, dict):
            profile = {"user_id": owner_user_id, "balance": 0}
            user_data_db[user_id_str] = profile

        if reason:
            db_update_balance(owner_user_id, safe_new_balance, reason=reason)
        else:
            profile["balance"] = safe_new_balance

        normalized["wallet_mode"] = "shared_user_wallet"
        normalized["shared_wallet_enabled"] = True
        normalized["balance"] = safe_new_balance
        return safe_new_balance, normalized

    normalized["wallet_mode"] = "legacy_api_wallet"
    normalized["balance"] = safe_new_balance
    return safe_new_balance, normalized

async def _api_maybe_alert_low_balance(api_key: str, key_data: dict, balance: int):
    if not isinstance(key_data, dict) or key_data.get("low_balance_alert_enabled") is False:
        return
    try:
        threshold = max(0, int(key_data.get("low_balance_threshold", 100000) or 0))
        last_alert = float(key_data.get("low_balance_alerted_at", 0) or 0)
    except (TypeError, ValueError):
        threshold, last_alert = 100000, 0
    if int(balance) > threshold or time.time() - last_alert < 86400 or not bot_instance:
        return
    key_data["low_balance_alerted_at"] = time.time()
    await save_data(force=True, tables=[API_KEYS_FILE])
    partner_name = html.escape(str(key_data.get("name") or "Partner"))
    text = (
        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>CẢNH BÁO SỐ DƯ API THẤP</b>\n\n"
        f"Partner: <b>{partner_name}</b>\n"
        f"Số dư: <b>{int(balance):,} VNĐ</b>\n"
        f"Ngưỡng: {threshold:,} VNĐ"
    )
    recipients = {ADMIN_USER_ID}
    owner_id = _api_get_partner_wallet_owner_user_id(key_data)
    if owner_id:
        recipients.add(owner_id)
    for recipient in recipients:
        try:
            await bot_instance.send_message(recipient, text, parse_mode=ParseMode.HTML)
        except (TelegramError, ValueError, KeyError, AttributeError):
            logger.debug("Cannot send low API balance alert to %s", recipient)


async def safe_api_set_balance(
    api_key: str,
    amount: int,
    save: bool = False,
    reason: str | None = None,
    *,
    ledger_type: str = "adjustment",
    reference: str = "",
    idempotency_key: str = "",
    admin_actor: str = "",
):
    key = str(api_key or "").strip()
    if not key:
        return False, None, None
    lock = await get_api_key_lock(key)
    async with lock:
        key_data = _api_normalize_partner_key(key)
        if key_data is None:
            return False, None, None
        old_balance = _api_get_partner_effective_balance(key, key_data)
        requested_balance = int(amount or 0)
        if old_balance is None or requested_balance < 0:
            return False, old_balance, key_data
        new_balance, key_data = _api_set_partner_effective_balance_unlocked(key, key_data, requested_balance, reason=reason)
        delta = int(new_balance) - int(old_balance)
        if delta:
            db_record_api_partner_ledger(
                _api_key_fingerprint(key), key_data.get("name") or "Partner", ledger_type, delta,
                int(old_balance), int(new_balance), reference=reference, reason=reason or "Set partner balance",
                admin_actor=admin_actor, idempotency_key=idempotency_key,
            )
    if save:
        tables = [API_KEYS_FILE]
        if _api_get_partner_wallet_owner_user_id(key_data):
            tables.extend([USERS_FILE, TRANSACTION_HISTORY_FILE])
        await save_data(force=True, tables=tables)
    await _api_maybe_alert_low_balance(key, key_data, int(new_balance or 0))
    return True, new_balance, key_data


async def safe_api_adjust_balance(
    api_key: str,
    delta: int,
    save: bool = False,
    reason: str | None = None,
    *,
    ledger_type: str | None = None,
    reference: str = "",
    idempotency_key: str = "",
    admin_actor: str = "",
):
    """Adjust partner balance atomically and append its immutable ledger event."""
    key = str(api_key or "").strip()
    if not key:
        return False, None, None

    lock = await get_api_key_lock(key)
    async with lock:
        key_data = _api_normalize_partner_key(key)
        if key_data is None:
            return False, None, None
        current_balance = _api_get_partner_effective_balance(key, key_data)
        if current_balance is None:
            return False, None, None
        signed_delta = int(delta or 0)
        new_balance = int(current_balance) + signed_delta
        if new_balance < 0:
            return False, current_balance, key_data
        new_balance, key_data = _api_set_partner_effective_balance_unlocked(key, key_data, new_balance, reason=reason)
        if signed_delta:
            inferred_type = ledger_type
            if not inferred_type:
                inferred_type = "refund" if signed_delta > 0 and "refund" in str(reason or "").lower() else "deposit" if signed_delta > 0 else "adjustment"
            db_record_api_partner_ledger(
                _api_key_fingerprint(key), key_data.get("name") or "Partner", inferred_type, signed_delta,
                int(current_balance), int(new_balance), reference=reference, reason=reason or "Partner balance adjustment",
                admin_actor=admin_actor, idempotency_key=idempotency_key,
            )

    if save:
        tables_to_save = [API_KEYS_FILE]
        if _api_get_partner_wallet_owner_user_id(key_data):
            tables_to_save.extend([USERS_FILE, TRANSACTION_HISTORY_FILE])
        await save_data(force=True, tables=tables_to_save)
    await _api_maybe_alert_low_balance(key, key_data, int(new_balance or 0))
    return True, new_balance, key_data

def find_api_key_by_fingerprint(partner_key_hash: str):
    target_hash = str(partner_key_hash or "").strip()
    if not target_hash:
        return None

    for api_key, ak_data in api_keys.items():
        if isinstance(ak_data, str):
            ak_data = {"name": ak_data, "balance": 0}
            api_keys[api_key] = ak_data
        if not isinstance(ak_data, dict):
            continue
        if _api_key_fingerprint(api_key) == target_hash:
            return api_key
    return None

async def safe_api_adjust_balance_by_hash(partner_key_hash: str, delta: int, save: bool = False, reason: str | None = None):
    """Thread-safe: Adjust partner balance by stored key fingerprint."""
    api_key = find_api_key_by_fingerprint(partner_key_hash)
    if not api_key:
        return False, None, None
    return await safe_api_adjust_balance(api_key, delta, save=save, reason=reason)

# ==============================================================================
#  SAFE HELPERS: Locked access to pending_orders & API balance
# ==============================================================================

async def pending_set(order_code: str, data: dict):
    """Thread-safe: Set pending_orders[order_code] = data."""
    async with pending_orders_lock:
        reserved_order_codes.discard(order_code)
        pending_orders[order_code] = data

async def pending_pop(order_code: str, default=None):
    """Thread-safe: Pop from pending_orders."""
    async with pending_orders_lock:
        return pending_orders.pop(order_code, default)

async def pending_get(order_code: str, default=None):
    """Thread-safe: Get from pending_orders."""
    async with pending_orders_lock:
        return pending_orders.get(order_code, default)

async def pending_items_snapshot():
    """Thread-safe snapshot of pending_orders items."""
    async with pending_orders_lock:
        return list(pending_orders.items())

async def get_user_pending_order(user_id: int):
    """First unpaid order of a user, so we never stack two pending checkouts."""
    for code, order in await pending_items_snapshot():
        if order.get('user_id') == user_id and order.get('status') == 'pending_payment':
            return code, order
    return None, None

async def release_reserved_order_code(order_code: str):
    if not order_code:
        return
    async with pending_orders_lock:
        reserved_order_codes.discard(order_code)

async def safe_api_refund_balance(partner_key_hash: str, amount: int) -> bool:
    """Thread-safe: Refund amount to partner shared wallet by key hash."""
    if not partner_key_hash or int(amount or 0) <= 0:
        return False
    refunded, new_balance, _ = await safe_api_adjust_balance_by_hash(
        partner_key_hash,
        int(amount),
        save=True,
        reason=f"API Refund +{int(amount or 0):,} VND",
    )
    if refunded:
        logger.info(f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> API Refund: +{amount:,} VNĐ (new balance: {int(new_balance or 0):,})")
    return refunded

async def notify_admin_manual_order(context: ContextTypes.DEFAULT_TYPE, order_code: str, user_id: int, full_name: str, email: str, product_name: str, quantity: int, amount: int):
    """
    NEW: Gửi thông báo cho Admin về đơn hàng cần xử lý thủ công (requires_gmail)
    """
    msg = (
        f"{E_GLOBE} <b>ĐƠN HÀNG MỚI - CẦN XỬ LÝ THỦ CÔNG</b>\n\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách hàng:</b> {html.escape(full_name)} (ID: <code>{user_id}</code>)\n"
        f"{E_GLOBE} <b>Email nhận:</b> <code>{html.escape(email)}</code>\n"
        f"{E_TAG} <b>Sản phẩm:</b> {html.escape(product_name)}\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Số lượng:</b> {quantity}\n"
        f"{E_TAG} <b>Đã thanh toán:</b> {amount:,} VNĐ\n\n"
        f"{E_ERROR} <b>HÀNH ĐỘNG CẦN LÀM:</b>\n"
        f"1. Setup/Gửi sản phẩm cho email: <code>{html.escape(email)}</code>\n"
        f"2. Bấm nút bên dưới khi hoàn thành\n"
        f"3. Bot sẽ tự động thông báo khách check mail"
    )
    
    keyboard = [
        [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã hoàn thành - Thông báo khách", callback_data=f"manual_done:{order_code}")],
        [InlineKeyboardButton("❌ Gặp vấn đề - Hoàn tiền", callback_data=f"manual_refund:{order_code}")]
    ]
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi thông báo manual order {order_code} cho Admin")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Lỗi gửi thông báo manual order cho admin: {e}")

async def broadcast_back_in_stock(context: ContextTypes.DEFAULT_TYPE, product_name: str, product_id: str, stock_count: int):
    """
    Broadcast thông báo có hàng trở lại
    """

    
    # Chỉ broadcast nếu trước đó đã thông báo hết hàng
    if product_id not in notified_out_of_stock:
        return
    
    # Xóa khỏi danh sách đã thông báo (để có thể thông báo lại lần sau)
    notified_out_of_stock.discard(product_id)
    
    # Tạo message
    message = (
        f"{E_SUCCESS} <b>ĐÃ CÓ HÀNG TRỞ LẠI!</b>\n\n"
        f"{E_TAG} <b>Sản phẩm:</b> {html.escape(product_name)}\n"
        f"{E_STAT} <b>Số lượng:</b> {stock_count} sản phẩm\n\n"
        f"<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Đặt hàng ngay:</b> /start\n"
        f"{E_LOADING} <b>Nhanh tay kẻo hết!</b>"
    )
    
    success_count = 0
    fail_count = 0
    blocked_ids = []
    
    for user_id_str in list(user_data_db.keys()):
        try:
            user_id = int(user_id_str)
            profile = user_data_db.get(user_id_str, {})
            if user_id in banned_users or (isinstance(profile, dict) and profile.get("broadcast_disabled")):
                continue
            
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            success_count += 1
            await asyncio.sleep(0.05)
            
        except Forbidden:
            fail_count += 1
            blocked_ids.append(user_id_str)
        except (ValueError, TypeError, KeyError, IndexError):
            fail_count += 1
    
    if blocked_ids:
        await _cleanup_blocked_users(blocked_ids)
    
    logger.info(f"<tg-emoji emoji-id=\"6129860303619363484\">📢</tg-emoji> Broadcast có hàng '{product_name}': {success_count} thành công, {fail_count} thất bại")


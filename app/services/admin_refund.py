"""
Admin refund service — handles order refund callbacks.

Extracted from callback_admin.py to reduce monolithic file size.
Handles: admrf_f_{code}, admrf_p_{code} (full and prorated refunds)

This module runs inside the shared exec() namespace so all globals
(order_index, api_keys, user_data_db, etc.) are available implicitly.
"""


def _calculate_order_refund(order: dict, *, prorated: bool, now_ts: float | None = None) -> dict:
    """Calculate a full or whole-day prorated refund without mutating the order."""
    import math

    amount = max(0, int(order.get('amount', 0) or 0))
    if not prorated:
        return {
            "amount": amount,
            "reason": "100%",
            "duration_days": 0,
            "used_days": 0,
            "unused_days": 0,
        }

    duration_days = _resolve_order_duration_days(order)
    if duration_days <= 0:
        raise ValueError("order_duration_unknown")

    current_time = float(now_ts if now_ts is not None else time.time())
    started_at = float(order.get('completed_at') or order.get('timestamp') or current_time)
    elapsed_seconds = max(0.0, current_time - started_at)
    # A started day counts as used; remaining whole days are refundable.
    used_days = min(duration_days, int(math.ceil(elapsed_seconds / 86400)))
    unused_days = max(0, duration_days - used_days)
    refund_amount = (amount * unused_days) // duration_days
    return {
        "amount": refund_amount,
        "reason": f"Còn {unused_days}/{duration_days} ngày chưa sử dụng",
        "duration_days": duration_days,
        "used_days": used_days,
        "unused_days": unused_days,
    }


async def _handle_admin_refund_unlocked(query, context, update):
    """Process admin refund callbacks (full or prorated).

    Supports both regular user refunds (to bot wallet) and
    API partner refunds (to shared partner wallet).
    """
    order_code = query.data.replace('admrf_f_', '').replace('admrf_p_', '')
    is_prorated = query.data.startswith('admrf_p_')

    order = order_index.get(order_code)
    if not order:
        await safe_answer(query, "❌ Không tìm thấy đơn hàng!", show_alert=True)
        return

    if order.get('refunded_at'):
        await safe_answer(query, "\u003ctg-emoji emoji-id=\"5447644880824181073\"\u003e⚠️\u003c/tg-emoji\u003e Đơn hàng này đã được hoàn tiền rồi!", show_alert=True)
        return

    uid = order.get('user_id')
    if not uid:
        await safe_answer(query, "❌ Không tìm thấy user ID trong đơn hàng.", show_alert=True)
        return

    if is_prorated:
        resolved_product_id, resolved_product = _resolve_order_product(order)
        if resolved_product_id and not order.get('product_id'):
            order['product_id'] = resolved_product_id
        if resolved_product and resolved_product.get('duration') and not order.get('product_duration'):
            order['product_duration'] = resolved_product.get('duration')

    try:
        refund_quote = _calculate_order_refund(order, prorated=is_prorated)
    except ValueError:
        if is_prorated:
            await safe_answer(query, "❌ Lỗi: Không thể tự động tính ngày do thời hạn sản phẩm không rõ ràng.", show_alert=True)
            return
        raise

    refund_amount = int(refund_quote["amount"])
    refund_reason = str(refund_quote["reason"])
    if refund_amount <= 0:
        await safe_answer(query, "⚠️ Gói đã hết hạn, số tiền hoàn = 0.", show_alert=True)
        return

    # --- Execute refund ---
    refund_target_label = "Ví Bot"
    is_api_partner_order = _api_is_order_record(order)
    notify_chat_id = None
    new_balance = 0

    if is_api_partner_order:
        partner_name = ""
        if isinstance(uid, str) and uid.startswith("PARTNER_"):
            partner_name = uid.replace("PARTNER_", "", 1).strip()
        if not partner_name:
            partner_name = str(order.get("full_name") or "").replace("Partner: ", "").strip()

        partner_key_hash = str(order.get("api_partner_key_hash") or "")
        adjusted, new_balance, key_data = await safe_api_adjust_balance_by_hash(
            partner_key_hash,
            refund_amount,
            save=True,
            reason=f"Admin refund {order_code}",
        )
        if not adjusted and partner_name:
            target_key = None
            for api_key, api_data in api_keys.items():
                current_partner_name = api_data if isinstance(api_data, str) else api_data.get("name")
                if current_partner_name == partner_name:
                    target_key = api_key
                    break
            if target_key:
                adjusted, new_balance, key_data = await safe_api_adjust_balance(
                    target_key,
                    refund_amount,
                    save=True,
                    reason=f"Admin refund {order_code}",
                )

        if not adjusted:
            display_partner = partner_name or str(uid)
            await safe_answer(
                query,
                f"⚠️ Không tìm thấy Key của Partner '{display_partner}'. Không thể hoàn tiền tự động.",
                show_alert=True,
            )
            return

        refund_target_label = "Ví chung"
        try:
            notify_chat_id = int((key_data or {}).get("user_id", 0) or 0)
        except (TypeError, ValueError):
            notify_chat_id = None
    else:
        user_id_str = str(uid)
        current_balance = int(user_data_db.get(user_id_str, {}).get('balance', 0))
        new_balance = current_balance + refund_amount
        db_update_balance(user_id_str, new_balance, reason=f"Admin Refund {order_code}")
        try:
            notify_chat_id = int(uid)
        except (TypeError, ValueError):
            notify_chat_id = None

    # --- Update order record ---
    order['status'] = (
        "\u003ctg-emoji emoji-id=\"5462956611033117422\"\u003e♻️\u003c/tg-emoji\u003e Đã hoàn tiền (Ví chung)"
        if is_api_partner_order
        else "\u003ctg-emoji emoji-id=\"5462956611033117422\"\u003e♻️\u003c/tg-emoji\u003e Đã hoàn tiền (Ví Bot)"
    )
    order['refunded_at'] = time.time()
    order['refund_amount'] = refund_amount
    order['refund_reason'] = refund_reason
    order['refund_target'] = refund_target_label

    tables_to_save = [HISTORY_FILE]
    if not is_api_partner_order:
        tables_to_save.extend([USERS_FILE, TRANSACTION_HISTORY_FILE])
    await save_data(force=True, tables=tables_to_save)

    # --- Notify customer ---
    if notify_chat_id:
        try:
            if is_api_partner_order:
                bank_refund_markup = None
                if refund_amount >= BANK_REFUND_MIN_AMOUNT:
                    bank_refund_markup = InlineKeyboardMarkup([[
                        _btn(
                            "Yêu cầu hoàn về ngân hàng",
                            icon_id="5278467510604160626",
                            callback_data=f"refund_bank:{order_code}",
                        )
                    ]])
                await context.bot.send_message(
                    chat_id=notify_chat_id,
                    text=(
                        f"💸 \u003cb\u003eĐƠN HÀNG ĐƯỢC HOÀN TIỀN\u003c/b\u003e\n\n"
                        f"Mã đơn: \u003ccode\u003e{order_code}\u003c/code\u003e\n"
                        f"Sản phẩm: {order.get('product_name')}\n"
                        f"Số tiền hoàn: \u003cb\u003e{refund_amount:,} VNĐ\u003c/b\u003e ({refund_reason})\n"
                        f"Nơi hoàn: \u003cb\u003e{refund_target_label}\u003c/b\u003e\n"
                        f"Số dư ví chung mới: \u003cb\u003e{int(new_balance or 0):,} VNĐ\u003c/b\u003e"
                    ),
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=notify_chat_id,
                    text=(
                        f"💸 \u003cb\u003eĐƠN HÀNG ĐƯỢC HOÀN TIỀN\u003c/b\u003e\n\n"
                        f"Mã đơn: \u003ccode\u003e{order_code}\u003c/code\u003e\n"
                        f"Sản phẩm: {order.get('product_name')}\n"
                        f"Số tiền hoàn: \u003cb\u003e{refund_amount:,} VNĐ\u003c/b\u003e ({refund_reason})\n"
                        f"Nơi hoàn: \u003cb\u003e{refund_target_label}\u003c/b\u003e\n\n"
                        f"\u003ci\u003eTiền đã được cộng vào số dư của bạn.\u003c/i\u003e"
                        + (
                            f"\n\nKhoản hoàn từ <b>{BANK_REFUND_MIN_AMOUNT:,} VNĐ</b> có thể yêu cầu chuyển về ngân hàng."
                            if refund_amount >= BANK_REFUND_MIN_AMOUNT else
                            f"\n\nKhoản hoàn dưới <b>{BANK_REFUND_MIN_AMOUNT:,} VNĐ</b> chỉ hoàn vào Ví Bot."
                        )
                    ),
                    parse_mode='HTML',
                    reply_markup=bank_refund_markup,
                )
        except (TelegramError, ValueError):
            pass

    # --- Update admin message ---
    try:
        msg_html = get_query_message_html(query)
        action_time = datetime.fromtimestamp(time.time()).strftime('%H:%M:%S %d/%m/%Y')
        await safe_edit_message(
            query,
            text=(
                f"{msg_html}\n\n"
                f"--- 💸 \u003cb\u003eĐÃ HOÀN TIỀN LÚC:\u003c/b\u003e {action_time} ---\n"
                f"💰 Số tiền hoàn: \u003cb\u003e{refund_amount:,} VNĐ\u003c/b\u003e ({refund_reason})\n"
                f"💳 Nơi hoàn: \u003cb\u003e{refund_target_label}\u003c/b\u003e\n"
                f"💼 Số dư mới: \u003cb\u003e{int(new_balance or 0):,} VNĐ\u003c/b\u003e"
            ),
            parse_mode='HTML'
        )
    except TelegramError:
        pass

    logger.info(
        f"Admin history refund applied: {order_code} -> +{refund_amount:,} VND into {refund_target_label} "
        f"(new balance: {int(new_balance or 0):,})"
    )
    await safe_answer(query, f"✅ Đã hoàn {refund_amount:,}đ vào {refund_target_label} cho mã {order_code}!")


async def handle_admin_refund(query, context, update):
    """Serialize the refund decision and balance mutation per order."""
    order_code = query.data.replace('admrf_f_', '').replace('admrf_p_', '')
    lock = await get_refund_lock(order_code)
    async with lock:
        await _handle_admin_refund_unlocked(query, context, update)


async def begin_bank_refund_request(query, context, command: str):
    """Let an eligible customer request manual bank payout of a wallet refund."""
    order_code = str(command or "").split(":", 1)[1].strip()
    order = order_index.get(order_code)
    user = getattr(query, "from_user", None)
    if not order or not user or str(order.get("user_id")) != str(user.id):
        await safe_answer(query, "❌ Yêu cầu hoàn tiền không hợp lệ.", show_alert=True)
        return
    if not order.get("refunded_at"):
        await safe_answer(query, "❌ Đơn chưa được duyệt hoàn tiền.", show_alert=True)
        return

    refund_amount = int(order.get("refund_amount", 0) or 0)
    if refund_amount < BANK_REFUND_MIN_AMOUNT:
        await safe_answer(
            query,
            f"Khoản hoàn dưới {BANK_REFUND_MIN_AMOUNT:,}đ chỉ nhận qua Ví Bot.",
            show_alert=True,
        )
        return

    previous_request_id = str(order.get("bank_refund_request_id") or "")
    previous_request = withdrawal_requests.get(previous_request_id) if previous_request_id else None
    if previous_request and previous_request.get("status") in {"pending", "approved"}:
        await safe_answer(query, "⚠️ Yêu cầu hoàn ngân hàng đã được gửi hoặc xử lý.", show_alert=True)
        return

    context.user_data["state"] = "awaiting_refund_bank_info"
    context.user_data["refund_bank_order_code"] = order_code
    await safe_answer(query)
    await query.message.reply_text(
        "🏦 <b>NHẬP THÔNG TIN NHẬN TIỀN</b>\n\n"
        f"Mã đơn: <code>{order_code}</code>\n"
        f"Số tiền: <b>{refund_amount:,} VNĐ</b>\n\n"
        "Nhập theo mẫu:\n"
        "<code>Tên ngân hàng - Số tài khoản - Tên chủ tài khoản</code>\n\n"
        "Ví dụ: <code>MB Bank - 0123456789 - NGUYEN VAN A</code>\n"
        "Gõ <code>/cancel</code> để hủy.",
        parse_mode=ParseMode.HTML,
    )


async def handle_refund_bank_info_input(update, context):
    """Create an audited manual bank payout request for an eligible refund."""
    import html as html_lib
    import secrets

    order_code = str(context.user_data.get("refund_bank_order_code") or "").strip()
    raw_bank_info = str(getattr(update.message, "text", "") or "").strip()
    if raw_bank_info.casefold() in {"/cancel", "cancel", "huy", "hủy"}:
        context.user_data.pop("state", None)
        context.user_data.pop("refund_bank_order_code", None)
        await update.message.reply_text("Đã hủy yêu cầu hoàn về ngân hàng.")
        return

    normalized_bank_info, validation_error = normalize_bank_info(raw_bank_info)
    if validation_error:
        await update.message.reply_text(
            f"❌ {html_lib.escape(validation_error)}\n"
            "Vui lòng nhập: <code>Tên ngân hàng - Số tài khoản - Tên chủ tài khoản</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    order = order_index.get(order_code)
    user = getattr(update, "effective_user", None)
    if not order or not user or str(order.get("user_id")) != str(user.id):
        await update.message.reply_text("❌ Không tìm thấy đơn hoàn tiền hợp lệ.")
        context.user_data.pop("state", None)
        context.user_data.pop("refund_bank_order_code", None)
        return

    refund_amount = int(order.get("refund_amount", 0) or 0)
    if refund_amount < BANK_REFUND_MIN_AMOUNT:
        await update.message.reply_text(
            f"❌ Khoản hoàn dưới {BANK_REFUND_MIN_AMOUNT:,}đ chỉ nhận qua Ví Bot."
        )
        context.user_data.pop("state", None)
        context.user_data.pop("refund_bank_order_code", None)
        return

    lock = await get_refund_lock(order_code)
    async with lock:
        previous_request_id = str(order.get("bank_refund_request_id") or "")
        previous_request = withdrawal_requests.get(previous_request_id) if previous_request_id else None
        if previous_request and previous_request.get("status") in {"pending", "approved"}:
            await update.message.reply_text("⚠️ Yêu cầu hoàn ngân hàng đã tồn tại.")
            return

        user_id_str = str(user.id)
        current_balance = int(user_data_db.get(user_id_str, {}).get("balance", 0) or 0)
        if current_balance < refund_amount:
            await update.message.reply_text(
                "❌ Số dư Ví Bot không còn đủ khoản tiền hoàn để chuyển sang ngân hàng. "
                "Vui lòng liên hệ Admin."
            )
            return

        request_id = f"RF_{int(time.time())}_{secrets.token_hex(2).upper()}"
        withdrawal_requests[request_id] = {
            "user_id": user.id,
            "full_name": getattr(user, "full_name", "") or "Unknown",
            "username": getattr(user, "username", "") or "",
            "amount": refund_amount,
            "bank_info": normalized_bank_info,
            "status": "pending",
            "timestamp": time.time(),
            "source": "order_refund",
            "order_code": order_code,
        }
        db_update_balance(user.id, current_balance - refund_amount, reason=f"Bank refund request {order_code}")
        order["bank_refund_request_id"] = request_id
        order["bank_refund_status"] = "pending"
        await save_data(
            force=True,
            tables=[WITHDRAWALS_FILE, USERS_FILE, TRANSACTION_HISTORY_FILE, HISTORY_FILE],
        )

    context.user_data.pop("state", None)
    context.user_data.pop("refund_bank_order_code", None)
    await update.message.reply_text(
        "✅ <b>ĐÃ GỬI YÊU CẦU HOÀN NGÂN HÀNG</b>\n\n"
        f"Mã yêu cầu: <code>{request_id}</code>\n"
        f"Mã đơn: <code>{order_code}</code>\n"
        f"Số tiền: <b>{refund_amount:,} VNĐ</b>\n"
        f"Thông tin: <code>{html_lib.escape(normalized_bank_info)}</code>\n\n"
        "Admin sẽ kiểm tra và xác nhận sau khi chuyển khoản.",
        parse_mode=ParseMode.HTML,
    )
    await notify_admin_withdrawal(context, request_id)

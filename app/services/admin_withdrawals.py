"""
Admin withdrawal & API registration service.

Extracted from callback_admin.py to reduce monolithic file size.
Handles: approve_withdraw:, reject_withdraw:, approve_api:, reject_api:

This module runs inside the shared exec() namespace so all globals
are available implicitly.
"""


async def _handle_withdrawal_action_unlocked(query, context, command, user_id):
    """Process withdrawal approval or rejection."""
    request_id = command.split(':', 1)[1]
    req = withdrawal_requests.get(request_id)

    if not req or req['status'] != 'pending':
        await safe_edit_message(
            query,
            text=f"{(query.message.text_html or query.message.text or '')}\n\n❌ Yêu cầu này không tồn tại hoặc đã được xử lý."
        )
        return

    is_approve = command.startswith('approve_withdraw:')
    user_id_str = str(req['user_id'])

    if is_approve:
        # Tiền đã bị trừ lúc request (handle_withdrawal_input)
        # Chỉ cần lấy số dư hiện tại để báo cáo
        current_balance = user_data_db.get(user_id_str, {}).get('balance', 0)
        new_balance = current_balance

        # Update request
        req['status'] = 'approved'
        req['processed_at'] = time.time()
        withdrawal_requests[request_id] = req
        if req.get("source") == "order_refund":
            refund_order = order_index.get(str(req.get("order_code") or ""))
            if refund_order:
                refund_order["refund_target"] = "Ngân hàng"
                refund_order["bank_refund_status"] = "approved"
                refund_order["bank_refunded_at"] = time.time()
        await save_data()

        # Notify User
        try:
            await context.bot.send_message(
                req['user_id'],
                f"{E_SUCCESS} <b>YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC DUYỆT!</b>\n\n"
                f"{E_TAG} Số tiền: {req['amount']:,} VNĐ\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> Đã chuyển về: <code>{html.escape(str(req['bank_info']))}</code>\n"
                f"{E_TAG} Số dư còn lại: {new_balance:,} VNĐ\n\n"
                f"Cảm ơn bạn đã đồng hành cùng Lâm Shop! {E_MENU}",
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Cannot notify withdrawal approval to user {req.get('user_id')}: {e}")

        # Update Admin Msg
        processed_time = datetime.fromtimestamp(time.time()).strftime('%H:%M %d/%m')
        await safe_edit_message(
            query,
            text=(
                f"{(query.message.text_html or query.message.text or '')}\n\n"
                f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ DUYỆT & CHUYỂN KHOẢN</b>\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {processed_time}"
            )
        )

    else:
        # FIX BUG: Admin Reject -> Hoàn lại tiền cho User
        current_balance = user_data_db.get(user_id_str, {}).get('balance', 0)
        refund_balance = current_balance + req['amount']
        db_update_balance(req['user_id'], refund_balance, reason=f"Hoàn tiền rút thất bại {request_id}")

        # Reject
        req['status'] = 'rejected'
        req['processed_at'] = time.time()
        withdrawal_requests[request_id] = req
        if req.get("source") == "order_refund":
            refund_order = order_index.get(str(req.get("order_code") or ""))
            if refund_order:
                refund_order["refund_target"] = "Ví Bot"
                refund_order["bank_refund_status"] = "rejected"
        await save_data()

        # Notify User
        try:
            await context.bot.send_message(
                req['user_id'],
                f"{E_LIMIT} <b>YÊU CẦU RÚT TIỀN BỊ TỪ CHỐI</b>\n\n"
                f"{E_TAG} Số tiền: {req['amount']:,} VNĐ\n"
                f"Tiền đã được trả lại Ví Bot. Vui lòng liên hệ Admin để biết thêm chi tiết.",
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Cannot notify withdrawal rejection to user {req.get('user_id')}: {e}")

        # Update Admin Msg
        processed_time = datetime.fromtimestamp(time.time()).strftime('%H:%M %d/%m')
        await safe_edit_message(
            query,
            text=(
                f"{(query.message.text_html or query.message.text or '')}\n\n"
                f"❌ <b>ĐÃ TỪ CHỐI</b>\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {processed_time}"
            )
        )


async def handle_withdrawal_action(query, context, command, user_id):
    """Atomically process a withdrawal approval or rejection exactly once."""
    request_id = command.split(':', 1)[1]
    lock = await get_withdrawal_lock(request_id)
    async with lock:
        await _handle_withdrawal_action_unlocked(query, context, command, user_id)


async def handle_api_registration_action(query, context, command, user_id):
    """Process API partner registration approval or rejection."""
    target_uid = int(command.split(':')[1])
    is_approve = command.startswith('approve_api:')

    if is_approve:
        # Generate Key
        new_key = f"sk_live_{secrets.token_hex(16)}"

        try:
            target_user = await context.bot.get_chat(target_uid)
            partner_name = target_user.username or target_user.full_name or f"User_{target_uid}"
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Cannot resolve partner name for user {target_uid}: {e}")
            partner_name = f"User_{target_uid}"

        api_keys[new_key] = {"name": partner_name, "balance": 0, "user_id": target_uid}
        await save_data(force=True)

        if target_uid in pending_api_registrations:
            pending_api_registrations.remove(target_uid)

        await safe_edit_message(
            query,
            text=f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã duyệt API cho <b>{partner_name}</b>.\nKey: <code>{new_key}</code>",
            parse_mode=ParseMode.HTML
        )

        try:
            msg = (
                f"<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>ĐĂNG KÝ API THÀNH CÔNG!</b>\n\n"
                f"🔐 <b>API Key của bạn:</b> <code>{new_key}</code>\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư:</b> 0 VNĐ\n\n"
                f"<b>Hướng dẫn bắt đầu nhanh:</b>\n"
                f"1. Nạp tiền: <code>/napapi 500000</code>\n"
                f"2. Sản phẩm thường: <code>GET /api/v2/catalog</code> → <code>POST /api/v2/orders</code>\n"
                f"3. Social media: <code>GET /api/social/catalog</code> → <code>POST /api/social/orders</code>\n"
                f"4. Tra social: <code>GET /api/social/orders/{{order_code}}</code>\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vào <code>/start</code> để mở tài liệu API đầy đủ.\n\n"
                f"<i>Hai nhóm dùng chung API key và số dư ví.</i>"
            )
            await context.bot.send_message(target_uid, msg, parse_mode=ParseMode.HTML)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            await safe_send_admin(context.bot, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể nhắn tin cho user {target_uid}: {e}")
    else:
        # Reject
        if target_uid in pending_api_registrations:
            pending_api_registrations.remove(target_uid)

        await safe_edit_message(
            query,
            text=f"❌ Đã từ chối yêu cầu API của ID {target_uid}."
        )
        try:
            await context.bot.send_message(target_uid, "❌ Yêu cầu đăng ký API của bạn đã bị từ chối.")
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Cannot notify API rejection to user {target_uid}: {e}")

"""
Admin order management service — API orders + manual orders.

Extracted from callback_admin.py to reduce monolithic file size.
Handles: api_approve_, api_refund_, complete_manual_, refund_manual_

This module runs inside the shared exec() namespace so all globals
(order_index, api_keys, pending_manual_orders, etc.) are available implicitly.
"""


async def handle_api_order_approval(query, context, update):
    """Process API order approval/refund callbacks."""
    order_code = query.data.replace('api_approve_', '').replace('api_refund_', '')
    is_approve = query.data.startswith('api_approve_')

    order = order_index.get(order_code)
    if not order:
        await safe_answer(query, "❌ Không tìm thấy đơn hàng!", show_alert=True)
        return

    if order.get('status') in ['Hoàn thành', 'Đã hoàn tiền']:
        await safe_answer(query, "\u003ctg-emoji emoji-id=\"5447644880824181073\"\u003e⚠️\u003c/tg-emoji\u003e Đơn hàng này đã được xử lý rồi!", show_alert=True)
        return

    partner_name = str(order.get('full_name') or 'Unknown').replace('Partner: ', '')
    product_name = order.get('product_name', 'Sản phẩm')
    amount = int(order.get('amount', 0))
    email = order.get('api_customer_email') or order.get('email') or 'N/A'
    action_time = datetime.fromtimestamp(time.time()).strftime('%H:%M %d/%m/%Y')

    if is_approve:
        order['status'] = 'Hoàn thành'
        order['completed_at'] = time.time()
        order['delivery_method'] = 'manual_completed'
        await save_data(force=True)

        try:
            await safe_edit_message(
                query,
                text=(
                    f"{get_query_message_html(query)}\n\n"
                    f"--- \u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e \u003cb\u003eĐÃ DUYỆT\u003c/b\u003e ---\n"
                    f"\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏰\u003c/tg-emoji\u003e Lúc: {action_time}"
                ),
                parse_mode='HTML'
            )
        except (ValueError, TypeError, KeyError, IndexError):
            logger.debug("Suppressed error at L10176")

        await safe_answer(query, f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã duyệt đơn {order_code}!")
        logger.info(f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e API Manual Order APPROVED: {order_code} (Partner: {partner_name})")

    else:
        partner_key_hash = order.get('api_partner_key_hash', '')
        refunded = await safe_api_refund_balance(partner_key_hash, amount)

        if refunded:
            order['status'] = "\u003ctg-emoji emoji-id=\"5462956611033117422\"\u003e♻️\u003c/tg-emoji\u003e Đã hoàn tiền (Ví chung)"
            order['refunded_at'] = time.time()
            await save_data(force=True)

            try:
                await safe_edit_message(
                    query,
                    text=(
                        f"{get_query_message_html(query)}\n\n"
                        f"--- \u003ctg-emoji emoji-id=\"5462956611033117422\"\u003e♻️\u003c/tg-emoji\u003e \u003cb\u003eĐÃ HOÀN TIỀN\u003c/b\u003e ---\n"
                        f"\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏰\u003c/tg-emoji\u003e Lúc: {action_time}\n"
                        f"\u003ctg-emoji emoji-id=\"5278467510604160626\"\u003e💰\u003c/tg-emoji\u003e Hoàn: {amount:,} VNĐ vào ví chung"
                    ),
                    parse_mode='HTML'
                )
            except (ValueError, TypeError, KeyError, IndexError):
                logger.debug("Suppressed error at api_refund edit")

            await safe_answer(query, f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã hoàn {amount:,}đ cho Partner!")
            logger.info(f"♻️ API Order REFUNDED: {order_code} -> {amount:,} VND (Partner: {partner_name})")
        else:
            await safe_answer(query, "⚠️ Không thể hoàn tiền! Không tìm thấy key partner.", show_alert=True)


async def handle_manual_order_action(query, context, update):
    """Process manual order completion or refund."""
    user_id = update.effective_user.id
    order_code = query.data.replace('complete_manual_', '').replace('refund_manual_', '')
    is_complete = query.data.startswith('complete_manual_')

    order = pending_manual_orders.get(order_code)
    if not order:
        await safe_answer(query, "❌ Không tìm thấy đơn hàng hoặc đã xử lý!", show_alert=True)
        return

    user_id = order.get('user_id')
    email = order.get('email', 'N/A')
    product_name = order.get('product_name', 'Sản phẩm')
    amount = order.get('amount', 0)

    if is_complete:
        order['status'] = 'completed'
        order['completed_at'] = time.time()

        completed_order = {
            'order_code': order_code,
            'user_id': user_id,
            'email': email,
            'amount': amount,
            'status': 'Hoàn thành',
            'type': 'store_product',
            'product_id': order.get('product_id'),
            'link': f'Manual: {product_name}',
            'timestamp': order.get('timestamp', time.time()),
            'completed_at': time.time(),
            'full_name': order.get('full_name'),
            'username': order.get('username'),
            'product_name': product_name,
            'quantity': order.get('quantity', 1),
            'manual_fulfillment': True
        }
        db_add_order(completed_order)

        pending_manual_orders.pop(order_code, None)
        await save_data()

        completed_time = datetime.fromtimestamp(time.time()).strftime('%H:%M %d/%m/%Y')
        await safe_edit_message(
            query,
            text=(
                f"{(query.message.text_html or query.message.text or '')}\n\n"
                f"--- \u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e \u003cb\u003eĐÃ HOÀN THÀNH\u003c/b\u003e ---\n"
                f"\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏰\u003c/tg-emoji\u003e Lúc: {completed_time}"
            ),
            parse_mode='HTML'
        )

        await safe_send_message(
            context,
            user_id,
            f"{E_SUCCESS} \u003cb\u003eĐƠN HÀNG ĐÃ HOÀN THÀNH!\u003c/b\u003e\n\n"
            f"\u003ctg-emoji emoji-id=\"5972022360025336988\"\u003e🔸\u003c/tg-emoji\u003e \u003cb\u003eMã đơn:\u003c/b\u003e \u003ccode\u003e{order_code}\u003c/code\u003e\n"
            f"{E_TAG} \u003cb\u003eSản phẩm:\u003c/b\u003e {product_name}\n"
            f"{E_GLOBE} \u003cb\u003eEmail:\u003c/b\u003e \u003ccode\u003e{email}\u003c/code\u003e\n\n"
            f"\u003ctg-emoji emoji-id=\"5314638736462966754\"\u003e📬\u003c/tg-emoji\u003e \u003cb\u003eVui lòng kiểm tra email của bạn!\u003c/b\u003e\n"
            f"(Nếu không thấy, kiểm tra thư mục Spam/Junk)\n\n"
            f"{E_GLOBE} Nếu có vấn đề, liên hệ Admin để được hỗ trợ.",
            parse_mode='HTML'
        )

        await safe_answer(query, "\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã thông báo khách hàng!")

    else:
        user_info = db_get_user(user_id)
        new_balance = 0
        if user_info:
            current_balance = user_info.get('balance', 0)
            new_balance = current_balance + amount
            db_update_balance(user_id, new_balance, reason=f"Refund: Canceled Order {order_code}")
            await record_wallet_refund(
                context,
                order_code=order_code,
                user_id=user_id,
                amount=amount,
                product_name=product_name,
                reason="Admin hủy đơn manual",
                order_data=order,
            )

        pending_manual_orders.pop(order_code, None)
        await save_data()

        refund_time = datetime.fromtimestamp(time.time()).strftime('%H:%M %d/%m/%Y')
        await safe_edit_message(
            query,
            text=(
                f"{(query.message.text_html or query.message.text or '')}\n\n"
                f"--- ❌ \u003cb\u003eĐÃ HỦY & HOÀN TIỀN\u003c/b\u003e ---\n"
                f"\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏰\u003c/tg-emoji\u003e Lúc: {refund_time}\n"
                f"\u003ctg-emoji emoji-id=\"5278467510604160626\"\u003e💰\u003c/tg-emoji\u003e Đã hoàn: {amount:,} VNĐ"
            ),
            parse_mode='HTML'
        )

        await safe_send_message(
            context,
            user_id,
            f"{E_LIMIT} \u003cb\u003eĐƠN HÀNG ĐÃ BỊ HỦY\u003c/b\u003e\n\n"
            f"\u003ctg-emoji emoji-id=\"5972022360025336988\"\u003e🔸\u003c/tg-emoji\u003e \u003cb\u003eMã đơn:\u003c/b\u003e \u003ccode\u003e{order_code}\u003c/code\u003e\n"
            f"{E_TAG} \u003cb\u003eSản phẩm:\u003c/b\u003e {product_name}\n\n"
            f"{E_TAG} \u003cb\u003eSố tiền đã hoàn:\u003c/b\u003e {amount:,} VNĐ\n"
            f"{E_TAG} \u003cb\u003eSố dư mới:\u003c/b\u003e {new_balance:,} VNĐ\n\n"
            f"{E_GLOBE} Nếu có thắc mắc, vui lòng liên hệ Admin.",
            parse_mode='HTML'
        )

        await safe_answer(query, "\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã hoàn tiền cho khách!")

async def handle_legacy_manual_done_refund(query, context, command):
    """Process legacy manual order done/refund (acting on order_index)."""
    is_done = command.startswith('manual_done_')
    order_code = command.replace('manual_done_', '').replace('manual_refund_', '')
    found_order = order_index.get(order_code)

    if not found_order:
        await safe_edit_message(
            query,
            f"{(query.message.text_html or query.message.text or '')}\n\n❌ Không tìm thấy đơn hàng này!",
            parse_mode='HTML'
        )
        return

    if is_done:
        found_order['status'] = '<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn thành'
        await save_data(force=True)

        await safe_edit_message(
            query,
            f"{(query.message.text_html or query.message.text or '')}\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ HOÀN THÀNH!</b>",
            parse_mode='HTML'
        )

        customer_id = found_order.get('user_id')
        if customer_id:
            try:
                await context.bot.send_message(
                    customer_id,
                    f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐƠN HÀNG ĐÃ HOÀN THÀNH!</b>\n\n"
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {found_order.get('product_name', 'N/A')}\n"
                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                    f"Cảm ơn bạn đã sử dụng dịch vụ! <tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>",
                    parse_mode='HTML',
                    reply_markup=create_back_button_menu(user_id=customer_id)
                )
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.error(f"Could not notify customer {customer_id}: {e}")

        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> MANUAL ORDER DONE: {order_code} by Admin")
    else:
        customer_id = found_order.get('user_id')
        amount = found_order.get('amount', 0)
        new_balance = user_data_db.get(str(customer_id), {}).get('balance', 0) if customer_id else 0

        if customer_id and amount > 0:
            current_balance = user_data_db.get(str(customer_id), {}).get('balance', 0)
            new_balance = current_balance + amount
            db_update_balance(customer_id, new_balance)
            await record_wallet_refund(
                context,
                order_code=order_code,
                user_id=customer_id,
                amount=amount,
                product_name=found_order.get('product_name', 'Sản phẩm'),
                reason="Admin hủy đơn manual",
                order_data=found_order,
            )

        found_order['status'] = '❌ Đã hủy & hoàn tiền'
        found_order['refunded_at'] = time.time()
        await save_data(force=True)

        await safe_edit_message(
            query,
            f"{(query.message.text_html or query.message.text or '')}\n\n❌ <b>ĐÃ HỦY & HOÀN TIỀN!</b>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Đã hoàn {amount:,} VNĐ cho khách",
            parse_mode='HTML'
        )

        if customer_id:
            try:
                await context.bot.send_message(
                    customer_id,
                    f"❌ <b>ĐƠN HÀNG ĐÃ BỊ HỦY</b>\n\n"
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {found_order.get('product_name', 'N/A')}\n"
                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                    f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Đã hoàn tiền:</b> {amount:,} VNĐ\n"
                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Số dư mới:</b> {new_balance:,} VNĐ",
                    parse_mode='HTML',
                    reply_markup=create_back_button_menu(user_id=customer_id)
                )
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.error(f"Could not notify customer {customer_id}: {e}")

        logger.info(f"❌ MANUAL ORDER REFUNDED: {order_code} - Amount: {amount}")

async def handle_new_manual_done_refund(query, context, command):
    """Process new manual order done/refund (acting on pending_manual_orders)."""
    is_done = command.startswith('manual_done:')
    order_code = command.split(':', 1)[1]

    if order_code not in pending_manual_orders:
        await safe_answer(query, "❌ Đơn hàng không tồn tại hoặc đã xử lý!", show_alert=True)
        return

    order_info = pending_manual_orders[order_code]
    user_id = order_info['user_id']
    email = order_info['email']
    product_name = order_info['product_name']
    amount = order_info['amount']
    qty = order_info.get('quantity', 1)

    if is_done:
        order_data = {
            "order_code": order_code,
            "user_id": user_id,
            "email": email,
            "amount": amount,
            "status": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn thành (Manual)",
            "type": "store_product",
            "product_id": order_info.get('product_id'),
            "link": f"Manual - {product_name}",
            "timestamp": time.time(),
            "coupon_used": order_info.get('coupon_code') or "",
            "refunded_at": 0,
            "full_name": order_info.get('full_name', 'Unknown'),
            "username": order_info.get('username', 'Unknown'),
            "product_name": product_name,
            "quantity": qty,
            "manual_fulfillment": True
        }
        db_add_order(order_data)

        pending_manual_orders.pop(order_code, None)
        await save_data(force=True)

        new_caption = get_query_message_html(query) + f"\n\n<b>--- <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> ĐÃ HOÀN THÀNH ---</b>\n<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Lúc: {datetime.now().strftime('%H:%M %d/%m/%Y')}"
        disabled_btn = InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã xử lý", callback_data="ignore")

        await safe_edit_message(
            query,
            text=new_caption,
            reply_markup=InlineKeyboardMarkup([[disabled_btn]]),
            parse_mode=ParseMode.HTML
        )

        try:
            from app.core.emoji_runtime import upgrade_text_to_premium_emoji
            from app.handlers.flashsale_wheel import send_post_purchase_followups
            await safe_send_message(
                context,
                user_id,
                upgrade_text_to_premium_emoji(
                    f"{E_SUCCESS} <b>ĐƠN HÀNG ĐÃ HOÀN TẤT!</b>\n\n"
                    f"{E_TAG} <b>Sản phẩm:</b> {product_name} x{qty}\n"
                    f"{E_GLOBE} <b>Email:</b> <code>{email}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">🔖</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                    f"<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Vui lòng kiểm tra email của bạn!</b>\n"
                    f"<i>(Bao gồm cả thư mục Spam/Thư rác)</i>\n\n"
                    f"{E_TIP} Nếu có vấn đề, liên hệ Admin với mã đơn trên."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=create_success_menu(user_id=user_id)
            )
            create_background_task(
                send_post_purchase_followups(context, user_id, order_info.get("product_id"))
            )
            await safe_answer(query, "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã thông báo khách thành công!", show_alert=True)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đã lưu nhưng không gửi được tin cho khách: {e}", show_alert=True)
            logger.error(f"Lỗi thông báo manual complete cho user {user_id}: {e}")
    else:
        user_info = db_get_user(user_id)
        current_balance = user_info.get('balance', 0) if user_info else 0
        new_balance = current_balance + amount
        db_update_balance(user_id, new_balance)

        order_data = {
            "order_code": order_code,
            "user_id": user_id,
            "email": email,
            "amount": amount,
            "status": "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> Đã hoàn tiền (Manual)",
            "timestamp": time.time(),
            "coupon_used": order_info.get('coupon_code') or "",
            "full_name": order_info.get('full_name', 'Unknown'),
            "product_name": product_name,
            "quantity": qty,
            "refunded_at": time.time(),
            "refund_amount": amount,
            "refund_target": "Ví Bot",
            "refund_reason": "Admin hủy đơn manual",
        }
        await record_wallet_refund(
            context,
            order_code=order_code,
            user_id=user_id,
            amount=amount,
            product_name=product_name,
            reason="Admin hủy đơn manual",
            order_data=order_data,
        )

        pending_manual_orders.pop(order_code, None)
        await save_data(force=True)

        await safe_edit_message(
            query,
            text=get_query_message_html(query) + f"\n\n<b>--- <tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> ĐÃ HOÀN TIỀN ---</b>\n<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Lúc: {datetime.now().strftime('%H:%M %d/%m')}",
            parse_mode=ParseMode.HTML
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>ĐƠN HÀNG ĐÃ ĐƯỢC HOÀN TIỀN</b>\n\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">🔖</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
                    f"{E_TAG} <b>Hoàn lại:</b> {amount:,} VNĐ\n"
                    f"{E_TAG} <b>Số dư mới:</b> {new_balance:,} VNĐ\n\n"
                    f"<i>Admin đã hoàn tiền do gặp vấn đề kỹ thuật.</i>"
                ),
                parse_mode=ParseMode.HTML
            )
            await safe_answer(query, "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã hoàn tiền thành công!", show_alert=True)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Hoàn tiền nhưng không thông báo được khách: {e}", show_alert=True)

async def handle_cancel_order_payment(query, context, command):
    """Process cancel order and cancel payment."""
    if command.startswith('cancel_order:'):
        order_code = command.split(':', 1)[1].strip().upper()
        details = await pending_pop(order_code)
        if not details:
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn này không còn ở trạng thái chờ.", show_alert=True)
            return
        await safe_answer(query)

        try:
            await query.message.delete()
        except (Forbidden, BadRequest) as e:
            logger.debug(f"Cannot delete pending message on cancel order {order_code}: {e}")

        # RPay tu het han hoa don theo expireMinutes; khong co endpoint huy.
        refunded_amount = 0
        balance_used = int(details.get('balance_used', 0) or 0)
        if balance_used > 0:
            user_id_restore = details.get('user_id')
            user_info = db_get_user(user_id_restore) if user_id_restore else None
            if user_info:
                current_balance = user_info.get('balance', 0)
                db_update_balance(user_id_restore, current_balance + balance_used, reason=f"Refund: canceled payment {order_code}")
                refunded_amount = balance_used

        prod_name = details.get('product_name') or products.get(details.get('product_id', ''), {}).get('name') or "Sản phẩm"

        await save_data(force=True, tables=[PENDING_ORDERS_FILE, USERS_FILE, TRANSACTION_HISTORY_FILE])

        refund_msg = ""
        if refunded_amount > 0:
            refund_msg = f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> Đã hoàn lại <b>{refunded_amount:,} VNĐ</b> vào ví."

        await safe_send_message(
            context,
            query.from_user.id,
            text=f"❌ <b>ĐÃ HỦY GIAO DỊCH</b>\n\nSản phẩm: {html.escape(str(prod_name))}\nMã đơn: <code>{order_code}</code>{refund_msg}",
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu(user_id=getattr(getattr(query, 'from_user', None), 'id', None))
        )
    else:
        prod_id = command.replace('cancel_payment_', '')

        try:
            await query.message.delete()
        except (Forbidden, BadRequest) as e:
            logger.debug(f"Cannot delete QR message on cancel order: {e}")

        refunded_amount = 0
        if query.message and query.message.caption:
            match = re.search(r'ICLD(\d{6})', query.message.caption)
            if match:
                order_code = f"ICLD{match.group(1)}"
                details = await pending_pop(order_code)
                if details:
                    balance_used = details.get('balance_used', 0)
                    if balance_used > 0:
                        user_id_restore = details['user_id']
                        user_info = db_get_user(user_id_restore)
                        if user_info:
                            current_balance = user_info.get('balance', 0)
                            db_update_balance(user_id_restore, current_balance + balance_used, reason=f"Refund: Canceled QR payment {order_code}")
                            refunded_amount = balance_used
                            logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn {balance_used:,}đ cho user {user_id_restore}")
                    await save_data(force=True, tables=[PENDING_ORDERS_FILE, USERS_FILE, TRANSACTION_HISTORY_FILE])

        p = products.get(prod_id)
        prod_name = p['name'] if p else "Sản phẩm"

        refund_msg = ""
        if refunded_amount > 0:
            refund_msg = f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> Đã hoàn lại <b>{refunded_amount:,} VNĐ</b> vào ví."

        await safe_send_message(
            context,
            query.from_user.id,
            text=f"❌ <b>ĐÃ HỦY GIAO DỊCH</b>\n\nSản phẩm: {prod_name}{refund_msg}",
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu(user_id=getattr(getattr(query, 'from_user', None), 'id', None))
        )

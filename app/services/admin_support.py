"""
Admin support service — warranty, reports, live chat, resend links.

Extracted from callback_admin.py to reduce monolithic file size.
Handles: approve_warranty:, reject_warranty:, admin_open_chat:,
         admin_close_chat:, resend_link:, reject_expired:, reject_policy:,
         warranty_done:, dismiss_report:, replace_auto:, lienhe_admin

This module runs inside the shared exec() namespace so all globals
are available implicitly.
"""

from app.services.warranty_history import record_warranty_replacement


async def handle_warranty_approval(query, context, command):
    """Process warranty claim approval."""
    claim_id = command.split(':')[1]
    if claim_id in warranty_claims:
        warranty_claims[claim_id]['status'] = 'approved'
        await save_data()
        await query.edit_message_caption(f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã duyệt bảo hành {claim_id}")
        uid = warranty_claims[claim_id]['user_id']
        try:
            await context.bot.send_message(uid, f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Yêu cầu bảo hành {claim_id} của bạn đã được DUYỆT! Admin sẽ liên hệ sớm.")
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Cannot notify warranty approval to user {uid}: {e}")


async def handle_warranty_rejection(query, context, command):
    """Process warranty claim rejection."""
    claim_id = command.split(':')[1]
    if claim_id in warranty_claims:
        warranty_claims[claim_id]['status'] = 'rejected'
        await save_data()
        await query.edit_message_caption(f"❌ Đã từ chối bảo hành {claim_id}")
        uid = warranty_claims[claim_id]['user_id']
        try:
            await context.bot.send_message(uid, f"❌ Yêu cầu bảo hành {claim_id} của bạn đã bị TỪ CHỐI.")
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Cannot notify warranty rejection to user {uid}: {e}")


async def handle_admin_open_chat(query, context, command, user_id):
    """Open admin live chat session with a user."""
    target_uid = int(command.split(':')[1])
    context.user_data['admin_chatting_with'] = target_uid
    chat = live_chats.get(str(target_uid))

    if chat:
        chat['unread_by_admin'] = 0
        await save_data()
        try:
            await safe_answer(query, "Đã mở chat!")
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.debug(f"Cannot acknowledge admin_open_chat callback: {e}")

        msg = f"\u003ctg-emoji emoji-id=\"6129860303619363484\"\u003e💬\u003c/tg-emoji\u003e Chat với User ID: \u003ccode\u003e{target_uid}\u003c/code\u003e\n\n"
        for m in chat['messages'][-20:]:
            from_who = "User" if m['from'] == 'user' else "Admin"
            time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
            content = m.get('text', '[Image]')
            msg += f"\u003cb\u003e{from_who}\u003c/b\u003e ({time_str}):\n{content}\n\n"

        msg += "\u003ctg-emoji emoji-id=\"5460753627817723162\"\u003e💡\u003c/tg-emoji\u003e \u003cb\u003eReply tin nhắn này để chat với User.\u003c/b\u003e"
        kb = [[_btn("Chat", icon_id="5443038326535759644", callback_data=f"admin_close_chat:{target_uid}")]]
        try:
            await context.bot.send_message(user_id, msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Cannot send live chat transcript to user {user_id}: {e}")
    else:
        await safe_answer(query, "Chat không tồn tại", show_alert=True)


async def handle_admin_close_chat(query, context, command):
    """Close admin live chat session."""
    target_uid = int(command.split(':')[1])
    if context.user_data.get('admin_chatting_with') == target_uid:
        context.user_data.pop('admin_chatting_with', None)

    try:
        await safe_edit_message(
            query,
            text=f"{(query.message.text_html or query.message.text or '')}\n\n[ADMIN ĐÃ ĐÓNG CHAT]",
            parse_mode=ParseMode.HTML
        )
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.debug(f"Cannot edit admin_close_chat message: {e}")
    await safe_answer(query, "Đã đóng chat")


async def handle_resend_link(query, context, command, user_id):
    """Resend product link to user via email."""
    try:
        parts = command.split(':', 2)
        if len(parts) < 3:
            await safe_answer(query, "❌ Lỗi dữ liệu callback!", show_alert=True)
            return
        _, target_uid_str, target_email = parts
        target_uid = int(target_uid_str)
    except (ValueError, IndexError):
        await safe_answer(query, "❌ Lỗi dữ liệu callback!", show_alert=True)
        return

    if not available_links:
        await safe_answer(query, "❌ Kho link đang hết!", show_alert=True)
        return

    await safe_answer(query, "\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏳\u003c/tg-emoji\u003e Đang gửi email...")

    original_caption = query.message.caption or query.message.text or "Báo cáo lỗi"

    try:
        if query.message.caption:
            await query.edit_message_caption(
                caption=f"{original_caption}\n\n\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏳\u003c/tg-emoji\u003e \u003cb\u003eĐang gửi email... vui lòng đợi...\u003c/b\u003e",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                text=f"{original_caption}\n\n\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏳\u003c/tg-emoji\u003e \u003cb\u003eĐang gửi email... vui lòng đợi...\u003c/b\u003e",
                parse_mode=ParseMode.HTML
            )
    except BadRequest:
        pass

    link = next(iter(available_links)) if available_links else "No Link Available"

    create_background_task(
        _send_resend_link_email_background(context, query, target_email, target_uid, link, original_caption)
    )

    try:
        for r in pending_error_reports:
            if str(r['user_id']) == str(target_uid) and not r.get('resolved'):
                r['resolved'] = True
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot resolve pending error reports for user {user_id}: {e}")


async def handle_replace_manual(query, context, command):
    """Prompt admin for replacement accounts/links for a manual product."""
    order_code = command.split(":", 1)[1].strip().upper()
    order = order_index.get(order_code)
    if not order:
        await safe_answer(query, "Không tìm thấy đơn hàng.", show_alert=True)
        return

    context.user_data["state"] = "awaiting_manual_warranty_replacement"
    context.user_data["manual_warranty_order_code"] = order_code
    await safe_answer(query, "Hãy gửi acc/link bảo hành trong tin nhắn tiếp theo.")
    await query.message.reply_text(
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> "
        f"<b>CẤP BẢO HÀNH THỦ CÔNG</b>\n\n"
        f"Đơn: <code>{html.escape(order_code)}</code>\n"
        f"Sản phẩm: <b>{html.escape(str(order.get('product_name') or order.get('product_id') or 'N/A'))}</b>\n\n"
        "Gửi acc/link mới ở tin nhắn tiếp theo. Nếu có nhiều acc, nhập mỗi acc một dòng.\n"
        "Gõ <code>/cancel</code> để hủy.",
        parse_mode=ParseMode.HTML,
    )


async def handle_manual_warranty_replacement_input(update, context, user_input):
    """Deliver and persist a manually supplied warranty replacement."""
    if update.effective_user.id != ADMIN_USER_ID:
        return False
    if context.user_data.get("state") != "awaiting_manual_warranty_replacement":
        return False

    order_code = str(context.user_data.get("manual_warranty_order_code") or "").strip().upper()
    if str(user_input or "").strip().casefold() in {"/cancel", "cancel", "hủy", "huy"}:
        context.user_data.pop("manual_warranty_order_code", None)
        context.user_data.pop("state", None)
        await update.message.reply_text("Đã hủy cấp bảo hành thủ công.")
        return True

    order = order_index.get(order_code)
    if not order:
        context.user_data.pop("manual_warranty_order_code", None)
        context.user_data.pop("state", None)
        await update.message.reply_html(
            f"❌ Không còn tìm thấy đơn <code>{html.escape(order_code or 'N/A')}</code>."
        )
        return True

    replacement_items = list(
        dict.fromkeys(
            line.strip()
            for line in str(user_input or "").replace("\r", "").splitlines()
            if line.strip()
        )
    )
    if not replacement_items:
        await update.message.reply_text("Nội dung bảo hành đang trống. Hãy nhập lại hoặc gõ /cancel.")
        return True

    try:
        target_uid = int(order.get("user_id"))
    except (TypeError, ValueError):
        await update.message.reply_text("❌ Đơn không có user_id hợp lệ; chưa lưu bảo hành.")
        return True

    file_content = (
        f"BAO HANH DON HANG: {order_code}\n"
        f"SAN PHAM: {order.get('product_name') or order.get('product_id') or 'N/A'}\n"
        f"THOI GIAN: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n"
        + ("-" * 40)
        + "\n"
        + "\n".join(f"[{idx}] {item}" for idx, item in enumerate(replacement_items, 1))
    )
    delivery = await deliver_items_as_txt(
        context,
        target_uid,
        order_code,
        replacement_items,
        file_content=file_content,
        file_prefix="BaoHanh",
        caption_html=(
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> "
            f"<b>ACC/LINK BẢO HÀNH MỚI</b>\n"
            f"Đơn: <code>{html.escape(order_code)}</code>\n"
            "Vui lòng lưu lại thông tin này."
        ),
    )
    if not delivery.get("delivered"):
        await update.message.reply_text(
            "❌ Chưa gửi được nội dung bảo hành cho khách; dữ liệu chưa được ghi vào đơn. Hãy thử lại."
        )
        return True

    event = record_warranty_replacement(
        order,
        replacement_items,
        source="manual",
        admin_user_id=ADMIN_USER_ID,
        note="Manual warranty replacement",
    )
    for report in pending_error_reports:
        if isinstance(report, dict) and str(report.get("order_code") or "").upper() == order_code:
            report["resolved"] = True
    await save_data(force=True)

    context.user_data.pop("manual_warranty_order_code", None)
    context.user_data.pop("state", None)
    warranty_time = datetime.fromtimestamp(event["created_at"]).strftime("%H:%M %d/%m/%Y")
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> "
        f"<b>ĐÃ CẤP BẢO HÀNH THỦ CÔNG</b>\n\n"
        f"Đơn: <code>{html.escape(order_code)}</code>\n"
        f"Số item: <b>{len(replacement_items)}</b>\n"
        f"Thời gian: <b>{warranty_time}</b>\n\n"
        "Đã gửi khách và lưu vào lịch sử đơn hàng."
    )
    return True


async def handle_reject_report(query, context, command):
    """Reject support report (expired or policy violation)."""
    try:
        parts = command.split(':', 2)
        action_type = parts[0]
        target_uid = int(parts[1])
        order_code = parts[2]
    except (ValueError, IndexError):
        await safe_answer(query, "❌ Lỗi dữ liệu code", show_alert=True)
        return

    order = order_index.get(order_code)
    if not order:
        await safe_answer(query, "❌ Không tìm thấy đơn hàng", show_alert=True)
        return

    status_code = 'rejected_expired' if action_type == 'reject_expired' else 'rejected_policy'
    order['support_status'] = status_code
    await save_data()

    try:
        for r in pending_error_reports:
            if str(r['order_code']) == str(order_code):
                r['resolved'] = True
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.warning(f"Cannot resolve pending error reports for order {order_code}: {e}")

    reason_msg = ""
    if status_code == 'rejected_expired':
        reason_msg = "Sản phẩm đã hết hạn bảo hành."
        admin_note = "\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã từ chối (Hết Bảo Hành)"
    else:
        reason_msg = "Phát hiện vi phạm chính sách sử dụng (Share acc/Đổi pass...)."
        admin_note = "\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e Đã từ chối (Vi Phạm Chính Sách)"

    try:
        await context.bot.send_message(
            target_uid,
            f"\u003ctg-emoji emoji-id=\"5424857974784925603\"\u003e⛔\u003c/tg-emoji\u003e \u003cb\u003eTHÔNG BÁO TỪ ADMIN\u003c/b\u003e\n\n"
            f"Yêu cầu hỗ trợ cho đơn hàng \u003ccode\u003e{order_code}\u003c/code\u003e đã bị \u003cb\u003eTỪ CHỐI\u003c/b\u003e.\n"
            f"\u003ctg-emoji emoji-id=\"5460753627817723162\"\u003e💡\u003c/tg-emoji\u003e \u003cb\u003eLý do:\u003c/b\u003e {reason_msg}\n\n"
            f"\u003ci\u003eVui lòng không tiếp tục gửi yêu cầu cho đơn hàng này.\u003c/i\u003e",
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Cannot notify user about rejection: {e}")

    try:
        current_caption = query.message.caption or query.message.text
        new_caption = f"{current_caption}\n\n{admin_note}"
        if query.message.caption:
            await query.edit_message_caption(caption=new_caption, parse_mode=ParseMode.HTML, reply_markup=None)
        else:
            await query.edit_message_text(text=new_caption, parse_mode=ParseMode.HTML, reply_markup=None)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.debug(f"Cannot edit spam-block action message: {e}")

    await safe_answer(query, "Đã xử lý chặn spam!")


async def handle_warranty_done(query, context, command, user_id):
    """Mark warranty as completed and notify user."""
    order_code = command.split(':', 1)[1].strip()
    if not order_code:
        await safe_answer(query, "Lỗi dữ liệu mã đơn.", show_alert=True)
        return

    order = order_index.get(order_code)
    target_uid = None
    try:
        for r in pending_error_reports:
            if str(r.get('order_code')) == str(order_code):
                r['resolved'] = True
                if target_uid is None and r.get('user_id'):
                    target_uid = r.get('user_id')
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot resolve warranty-done report for order {order_code}: {e}")

    if target_uid is None and order:
        target_uid = order.get('user_id')

    if order:
        order['support_status'] = 'warranty_done'
        order['support_resolved_at'] = time.time()
        order['support_resolved_by'] = user_id
        await save_data(force=True)

    notify_ok = False
    try:
        if target_uid is None:
            raise ValueError("missing target user id")
        await context.bot.send_message(
            int(target_uid),
            f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e \u003cb\u003eTHÔNG BÁO BẢO HÀNH\u003c/b\u003e\n\n"
            f"Báo cáo lỗi cho đơn \u003ccode\u003e{html.escape(str(order_code))}\u003c/code\u003e đã được admin xử lý và đánh dấu \u003cb\u003eđã bảo hành\u003c/b\u003e.\n\n"
            "Vui lòng kiểm tra lại sản phẩm/tài khoản. Nếu vẫn còn lỗi, bạn có thể gửi lại báo cáo hoặc liên hệ hỗ trợ.",
            parse_mode=ParseMode.HTML
        )
        notify_ok = True
    except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot notify user about warranty done for order {order_code}: {e}")

    try:
        current_text = query.message.caption or query.message.text or ""
        note = (
            f"\n\n\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e "
            f"\u003cb\u003eAdmin đã đánh dấu đã bảo hành.\u003c/b\u003e\n"
            f"\u003ctg-emoji emoji-id=\"5350481781306958339\"\u003e💾\u003c/tg-emoji\u003e "
            f"Thông báo khách: \u003cb\u003e{'đã gửi' if notify_ok else 'chưa gửi được'}\u003c/b\u003e."
        )
        if query.message.caption:
            await query.edit_message_caption(caption=current_text + note, parse_mode=ParseMode.HTML, reply_markup=None)
        else:
            await query.edit_message_text(text=strip_tg_emoji(current_text + note), parse_mode=ParseMode.HTML, reply_markup=None)
    except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.debug(f"Cannot edit warranty-done message: {e}")

    if notify_ok:
        await safe_answer(query, "Đã đánh dấu bảo hành và báo cho khách.")
    else:
        await safe_answer(query, "Đã đánh dấu bảo hành nhưng chưa gửi được thông báo khách.", show_alert=True)


async def handle_dismiss_report(query, context, command):
    """Dismiss an error report without action."""
    order_code = command.split(':', 1)[1]
    try:
        for r in pending_error_reports:
            if str(r['order_code']) == str(order_code):
                r['resolved'] = True
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot mark report as resolved for order {order_code}: {e}")
    try:
        current_text = query.message.caption or query.message.text or ""
        note = "\n\n\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏭️\u003c/tg-emoji\u003e \u003cb\u003eAdmin đã bỏ qua báo cáo này.\u003c/b\u003e"
        if query.message.caption:
            await query.edit_message_caption(caption=current_text + note, parse_mode=ParseMode.HTML, reply_markup=None)
        else:
            await query.edit_message_text(text=strip_tg_emoji(current_text + note), parse_mode=ParseMode.HTML, reply_markup=None)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.debug(f"Cannot edit skip-report message: {e}")
    await safe_answer(query, "Đã bỏ qua báo cáo này!")


async def handle_replace_auto(query, context, command):
    """Automatically replace a product item from stock for warranty."""
    order_code = command.split(':', 1)[1]
    order = order_index.get(order_code)

    if not order:
        await safe_answer(query, "❌ Đơn hàng không tìm thấy!", show_alert=True)
        return

    prod_id = order.get('product_id')
    p = products.get(prod_id) if prod_id else None

    if not p:
        pname = order.get('product_name', '')
        if pname:
            for pid, pdata in products.items():
                if pdata.get('name') == pname:
                    p = pdata
                    prod_id = pid
                    break

    if not p or not prod_id:
        await safe_answer(query, "❌ Sản phẩm không tồn tại hoặc đã bị xóa!", show_alert=True)
        return

    await safe_answer(query, "\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏳\u003c/tg-emoji\u003e Đang cấp hàng mới...")

    lock = await get_product_lock(prod_id)
    async with lock:
        current_stock = products.get(prod_id, {}).get('stock', [])
        if not current_stock:
            fail_text = strip_tg_emoji(
                f"{query.message.caption or query.message.text or 'Báo lỗi'}\n\n"
                f"❌ \u003cb\u003eKHÔNG THỂ CẤP LẠI\u003c/b\u003e\n"
                f"Kho sản phẩm \u003cb\u003e{p['name']}\u003c/b\u003e vừa hết hàng."
            )
            try:
                if query.message.caption:
                    await safe_edit_message(query, caption=fail_text, parse_mode=ParseMode.HTML, reply_markup=None)
                else:
                    await safe_edit_message(query, text=fail_text, parse_mode=ParseMode.HTML, reply_markup=None)
            except (TelegramError, ValueError, KeyError, AttributeError):
                logger.debug("Suppressed error at L11429")
            return

        item = current_stock.pop(0)
        products[prod_id]['stock'] = current_stock
        record_warranty_replacement(
            order,
            [item],
            source="auto_stock",
            admin_user_id=ADMIN_USER_ID,
            note=f"Auto replacement from product {prod_id}",
        )
        await save_data(force=True)

    success_note = (
        f"\n\n\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e \u003cb\u003eĐÃ CẤP HÀNG MỚI\u003c/b\u003e\n"
        f"\u003ctg-emoji emoji-id=\"5854908544712707500\"\u003e📦\u003c/tg-emoji\u003e Item: \u003ccode\u003e{html.escape(str(item))}\u003c/code\u003e\n"
        f"\u003ctg-emoji emoji-id=\"5213349767672769194\"\u003e⏰\u003c/tg-emoji\u003e {datetime.now().strftime('%H:%M %d/%m')}"
    )
    try:
        current_content = strip_tg_emoji(query.message.caption or query.message.text or '')
        updated = current_content + success_note
        if query.message.caption:
            await safe_edit_message(query, caption=updated, parse_mode=ParseMode.HTML, reply_markup=None)
        else:
            await safe_edit_message(query, text=updated, parse_mode=ParseMode.HTML, reply_markup=None)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot edit admin message for replace_auto: {e}")
        try:
            await safe_send_admin(context.bot, f"\u003ctg-emoji emoji-id=\"6269163801178804220\"\u003e✅\u003c/tg-emoji\u003e \u003cb\u003eĐÃ CẤP HÀNG MỚI\u003c/b\u003e\nĐơn: \u003ccode\u003e{order_code}\u003c/code\u003e\n\u003ctg-emoji emoji-id=\"5854908544712707500\"\u003e📦\u003c/tg-emoji\u003e Item: \u003ccode\u003e{html.escape(str(item))}\u003c/code\u003e")
        except (TelegramError, ValueError, KeyError, AttributeError):
            logger.debug("Suppressed error at L11453")

    try:
        target_uid = order['user_id']
        await context.bot.send_message(
            target_uid,
            f"\u003ctg-emoji emoji-id=\"5447644880824181073\"\u003e🔔\u003c/tg-emoji\u003e \u003cb\u003eBẢO HÀNH ĐƠN HÀNG {order_code}\u003c/b\u003e\n\n"
            f"Admin đã cấp lại sản phẩm mới cho bạn:\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"\u003ccode\u003e{html.escape(str(item))}\u003c/code\u003e\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Xin lỗi vì sự bất tiện này!",
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot notify user about replacement: {e}")

    try:
        for r in pending_error_reports:
            if str(r['order_code']) == str(order_code):
                r['resolved'] = True
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot mark order report resolved from history for {order_code}: {e}")


async def handle_open_live_chat(query, context, user_id):
    """User opens live chat with admin."""
    try:
        await query.delete_message()
    except (Forbidden, BadRequest) as e:
        logger.debug(f"Cannot delete callback message before opening live chat: {e}")

    user_id_str = str(user_id)
    if user_id_str not in live_chats:
        live_chats[user_id_str] = {'messages': [], 'status': 'active', 'last_activity': time.time(), 'unread_by_admin': 0}
    context.user_data['state'] = 'in_live_chat'

    chat = live_chats[user_id_str]
    msg = '\u003ctg-emoji emoji-id="6129860303619363484"\u003e💬\u003c/tg-emoji\u003e \u003cb\u003eLIVE CHAT VỚI ADMIN\u003c/b\u003e\n\n'
    recent_msgs = chat['messages'][-10:]
    for m in recent_msgs:
        from_who = "\u003ctg-emoji emoji-id=\"5350778980158956492\"\u003e🧑\u003c/tg-emoji\u003e Bạn" if m['from'] == 'user' else "\u003ctg-emoji emoji-id=\"5350778980158956492\"\u003e👨\u003c/tg-emoji\u003e‍\u003ctg-emoji emoji-id=\"5854908544712707500\"\u003e💼\u003c/tg-emoji\u003e Admin"
        time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
        msg += f"{from_who} ({time_str}):\n{m['text']}\n\n"

    if not recent_msgs:
        msg += "\u003ci\u003eChưa có tin nhắn. Hãy gửi câu hỏi của bạn!\u003c/i\u003e\n\n"
    msg += '\u003ctg-emoji emoji-id="5460753627817723162"\u003e💡\u003c/tg-emoji\u003e Gửi tin nhắn để chat với Admin...'
    btns = [[InlineKeyboardButton("❌ Đóng chat", callback_data="close_live_chat")]]

    await safe_send_message(
        context,
        user_id,
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btns)
    )

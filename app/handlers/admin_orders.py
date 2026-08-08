from app.services.warranty_history import (
    get_latest_warranty_replacement,
    get_original_delivery_items,
    get_original_delivery_link,
)


async def duyet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Duyệt đơn hàng thủ công khi API không tự động duyệt
    Cú pháp: /duyet <mã đơn> hoặc chỉ /duyet để xem danh sách đơn chờ
    """
    # Hiển thị danh sách đơn chờ nếu không có args
    if not context.args:
        if not pending_orders:
            await update.message.reply_html(
                "<b><tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> KHÔNG CÓ ĐƠN HÀNG CHỜ DUYỆT</b>\n\n"
                "Tất cả đơn hàng đã được xử lý tự động.\n\n"
                "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Cách dùng:</b>\n"
                "<code>/duyet [mã đơn]</code>\n"
                "VD: <code>/duyet ICLD123456</code>"
            )
            return

        # Hiển thị danh sách đơn chờ
        message = "<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> DANH SÁCH ĐƠN HÀNG CHỜ DUYỆT</b>\n\n"
        for order_code, details in await pending_items_snapshot():
            time_ago = int((time.time() - details.get('time', 0)) / 60)
            message += (
                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <code>{order_code}</code>\n"
                f"   • Email: <b>{details.get('email', 'N/A')}</b>\n"
                f"   • Số tiền: <b>{details['amount']:,} VNĐ</b>\n"
                f"   • Chờ: <b>{time_ago} phút</b>\n"
                f"   • User: {details.get('full_name', 'N/A')}\n\n"
            )

        message += (
            "\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Để duyệt thủ công:</b>\n"
            "<code>/duyet [mã đơn]</code>\n"
            "VD: <code>/duyet ICLD123456</code>"
        )

        await update.message.reply_html(message)
        return

    # Duyệt đơn hàng thủ công
    order_code = context.args[0].upper()

    # Validate mã đơn
    if not ORDER_CODE_REGEX.match(order_code):
        await update.message.reply_html(
            "❌ <b>MÃ ĐƠN HÀNG KHÔNG HỢP LỆ</b>\n\n"
            "Mã đơn phải có dạng: <code>ICLD123456</code>"
        )
        return

    # Kiểm tra đơn hàng có trong pending không
    order_details = await pending_get(order_code)
    if not order_details:
        await update.message.reply_html(
            f"❌ <b>KHÔNG TÌM THẤY ĐƠN HÀNG</b>\n\n"
            f"Mã <code>{order_code}</code> không có trong danh sách chờ duyệt.\n\n"
            f"<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Dùng <code>/duyet</code> để xem tất cả đơn chờ."
        )
        return

    # Lấy thông tin đơn hàng
    user_id = order_details["user_id"]
    email = order_details.get("email", "N/A")
    amount = order_details["amount"]
    full_name = order_details.get("full_name", "Khách hàng")

    current_time = time.time()

    # Handle Store Product
    if order_details.get("type") == "store_product":
        prod_id = order_details.get("product_id")
        qty = order_details.get("quantity", 1)
        p = products.get(prod_id)
        stock = p.get('stock', []) if p else []

        if p and len(stock) >= qty:
            items_bought = []
            lock = await get_product_lock(prod_id)
            async with lock:
                current_stock = products[prod_id].get('stock', [])
                if len(current_stock) < qty:
                    await update.message.reply_html(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Hết hàng! Chỉ còn {len(current_stock)} sản phẩm.")
                    return
                for _ in range(qty):
                    items_bought.append(current_stock.pop(0))
                products[prod_id]['stock'] = current_stock
                await save_data(force=True, tables=[PRODUCTS_FILE])

            completed_order = {
                "user_id": user_id,
                "order_code": order_code,
                "amount": amount,
                "status": "Hoàn thành",
                "timestamp": current_time,
                "full_name": full_name,
                "username": order_details.get("username"),
                "type": "store_product",
                "product_name": p['name'],
                "quantity": qty,
                "items": items_bought,
                "manual_approval": True
            }

            # Send to User với thông tin chi tiết
            try:
                await context.bot.send_message(
                    user_id,
                    lt(
                        user_id,
                        f"{E_SUCCESS} <b>ĐƠN HÀNG ĐÃ ĐƯỢC DUYỆT THỦ CÔNG</b>\n\n"
                        f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
                        f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Số lượng:</b> {qty}\n"
                        f"{E_LOADING} <b>Thời hạn:</b> {p.get('duration', 'N/A')}\n"
                        f"{E_SHIELD} <b>Bảo hành:</b> {p.get('warranty', 'Không')}\n\n"
                        f"{E_TIP} <b>THÔNG TIN TÀI KHOẢN:</b>",
                        f"{E_SUCCESS} <b>YOUR ORDER HAS BEEN APPROVED MANUALLY</b>\n\n"
                        f"{E_TAG} <b>Product:</b> {p['name']}\n"
                        f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Quantity:</b> {qty}\n"
                        f"{E_LOADING} <b>Duration:</b> {p.get('duration', 'N/A')}\n"
                        f"{E_SHIELD} <b>Warranty:</b> {p.get('warranty', 'None')}\n\n"
                        f"{E_TIP} <b>ACCOUNT DETAILS:</b>",
                        f"{E_SUCCESS} <b>您的订单已人工审核通过</b>\n\n"
                        f"{E_TAG} <b>商品：</b>{p['name']}\n"
                        f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>数量：</b>{qty}\n"
                        f"{E_LOADING} <b>有效期：</b>{p.get('duration', 'N/A')}\n"
                        f"{E_SHIELD} <b>质保：</b>{p.get('warranty', '无')}\n\n"
                        f"{E_TIP} <b>账号信息：</b>",
                    ),
                    parse_mode=ParseMode.HTML
                )
            except (TelegramError, ValueError, KeyError, AttributeError):
                await context.bot.send_message(
                    user_id,
                    lt(
                        user_id,
                        f"✅ ĐƠN HÀNG ĐÃ ĐƯỢC DUYỆT THỦ CÔNG\n\n"
                        f"Sản phẩm: {p['name']}\nSố lượng: {qty}\n"
                        f"Thời hạn: {p.get('duration', 'N/A')}\nBảo hành: {p.get('warranty', 'Không')}\n\n"
                        f"THÔNG TIN TÀI KHOẢN:",
                        f"✅ YOUR ORDER HAS BEEN APPROVED MANUALLY\n\n"
                        f"Product: {p['name']}\nQuantity: {qty}\n"
                        f"Duration: {p.get('duration', 'N/A')}\nWarranty: {p.get('warranty', 'None')}\n\n"
                        f"ACCOUNT DETAILS:",
                        f"✅ 您的订单已人工审核通过\n\n"
                        f"商品：{p['name']}\n数量：{qty}\n"
                        f"有效期：{p.get('duration', 'N/A')}\n质保：{p.get('warranty', '无')}\n\n"
                        f"账号信息：",
                    ),
                )
            file_content = build_store_order_txt_content(
                order_code,
                p['name'],
                qty,
                amount,
                p.get('duration', 'N/A'),
                p.get('warranty', 'Không'),
                items_bought,
                purchase_ts=current_time,
                lang=get_user_lang(user_id),
            )
            delivery_result = await deliver_items_as_txt(
                context,
                user_id,
                order_code,
                items_bought,
                file_content=file_content,
                file_prefix="TaiKhoan",
                caption_html=lt(
                    user_id,
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Thông tin tài khoản đơn {order_code}</b>\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Vui lòng lưu lại cẩn thận.",
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Account details for order {order_code}</b>\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Please store this file safely.",
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>订单 {order_code} 的账号信息</b>\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 请妥善保存该文件。",
                ),
                reply_markup=create_success_menu(user_id=user_id),
            )
            completed_order["delivery_method"] = delivery_result.get("method", "failed")
            if not delivery_result.get("delivered"):
                completed_order["status"] = "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chờ gửi thủ công (Duyệt tay)"
                await safe_send_admin(
                    context.bot,
                    f"{E_SOS} <b>DELIVERY FAILED (DUYET TAY)</b>\n"
                    f"{E_ID} Đơn: <code>{order_code}</code>\n"
                    f"{E_USER} User: <code>{user_id}</code>\n"
                    f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                    f"{E_STAT} Fallback gửi: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                    f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                )
                await safe_send_message(
                    context,
                    user_id,
                    lt(
                        user_id,
                        f"❌ Có lỗi khi gửi tài khoản cho đơn <code>{order_code}</code>.\n"
                        "Admin đã nhận cảnh báo và sẽ gửi thủ công sớm nhất.",
                        f"❌ We could not deliver the accounts for order <code>{order_code}</code>.\n"
                        "The admin has been alerted and will send them manually shortly.",
                        f"❌ 订单 <code>{order_code}</code> 的账号发送失败。\n"
                        "管理员已收到提醒，会尽快人工发送。",
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(user_id=user_id),
                )

            # Notifications
            await send_live_order_notification(context, full_name, amount, product_name=p['name'], quantity=qty, order_code=order_code)
            if delivery_result.get("delivered"):
                admin_msg = f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ DUYỆT ĐƠN HÀNG THÀNH CÔNG!</b>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {p['name']} (x{qty})\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {amount:,} VNĐ"
            else:
                admin_msg = (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐÃ DUYỆT NHƯNG CẦN GỬI THỦ CÔNG!</b>\n"
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {p['name']} (x{qty})\n"
                    f"{E_ID} Mã: <code>{order_code}</code>\n"
                    f"{E_STAT} Delivery: {delivery_result.get('method', 'failed')}"
                )

        else:
             # Out of stock
            completed_order = {
                "user_id": user_id,
                "order_code": order_code,
                "amount": amount,
                "status": "Hết hàng (Đã thanh toán)",
                "timestamp": current_time,
                "full_name": full_name,
                "username": order_details.get("username"),
                "type": "store_product",
                "product_name": p['name'] if p else "Đã xóa",
                "quantity": qty,
                "manual_approval": True
            }
            await context.bot.send_message(user_id, "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ DUYỆT ĐƠN HÀNG</b>\n\nTuy nhiên, KHO KHÔNG ĐỦ HÀNG. Admin sẽ liên hệ xử lý sau.", parse_mode=ParseMode.HTML)
            admin_msg = f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>DUYỆT ĐƠN NHƯNG THIẾU HÀNG!</b>\nĐơn: {order_code}\nCần: {qty} | Có: {len(stock)}"

        # FIX BUG #12: Save & Cleanup với index update
        await pending_pop(order_code)
        db_add_order(completed_order)
        await process_referral_commission(context, user_id, amount)
        await save_data(force=True)
        try:
            await update.message.reply_html(admin_msg)
        except (TelegramError, ValueError, KeyError, AttributeError):
            await update.message.reply_text(strip_tg_emoji(admin_msg))
        return

    await update.message.reply_html(
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>KHÔNG HỖ TRỢ</b>\n\n"
        f"Đơn <code>{order_code}</code> không phải đơn sản phẩm trong kho nên không thể duyệt tự động."
    )
    return


async def find_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tìm thông tin đơn hàng theo mã
    Cú pháp: /find <mã đơn>
    """
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập mã đơn hàng. VD: /find ICLD123456")
        return

    order_code = context.args[0].upper()

    # Tìm trong pending_orders
    details = await pending_get(order_code)
    if details:
        status = "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang chờ thanh toán"
        timestamp = details.get("time", 0)

        # Format time
        time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d/%m/%Y')

        msg = (
            f"<tg-emoji emoji-id=\"5429571366384842791\">🔎</tg-emoji> <b>KẾT QUẢ TÌM KIẾM (PENDING)</b>\n\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>User:</b> {details.get('full_name')} (ID: <code>{details.get('user_id')}</code>)\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Email:</b> <code>{details.get('email')}</code>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {details.get('amount'):,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5377624166436445368\">🎟</tg-emoji> <b>Coupon:</b> {details.get('coupon_code') or 'Không'}\n"
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Thời gian tạo:</b> {time_str}\n"
            f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Trạng thái:</b> {status}"
        )
        await update.message.reply_html(msg)
        return

    # Tìm trong order_history
    # FIX: Dùng index O(1) thay vì loop O(n)
    found_order = order_index.get(order_code)

    if found_order:
        timestamp = found_order.get("timestamp", 0)
        time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d/%m/%Y')
        status = status_text(found_order.get("status"))

        email = found_order.get("email") # For auto orders
        if not email:
            # Maybe manual order stored input
            email = found_order.get("user_input_email", "Không có")

        msg = (
            f"<tg-emoji emoji-id=\"5429571366384842791\">🔎</tg-emoji> <b>KẾT QUẢ TÌM KIẾM (HISTORY)</b>\n\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>User:</b> {found_order.get('full_name', 'Unknown')} (ID: <code>{found_order.get('user_id')}</code>)\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {found_order.get('product_name', 'N/A')}\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Email:</b> <code>{email}</code>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Giá trị:</b> {int(found_order.get('amount', 0)):,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Thời gian:</b> {time_str}\n"
            f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Trạng thái:</b> {status}"
        )

        if found_order.get("refunded_at"):
            refund_time = datetime.fromtimestamp(found_order.get("refunded_at")).strftime('%H:%M:%S %d/%m/%Y')
            msg += f"\n<tg-emoji emoji-id=\"5863724849851011383\">💸</tg-emoji> <b>Hoàn tiền lúc:</b> {refund_time}"

        # Keep the original delivery separate from the most recent warranty item.
        latest_warranty = get_latest_warranty_replacement(found_order)
        delivered_items = normalize_delivered_items(get_original_delivery_items(found_order))
        delivered_link = get_original_delivery_link(found_order)
        original_label = "ACC/LINK GỐC" if latest_warranty else "Nội dung đã gửi khách"
        if delivered_items:
            items_text = "\n".join(f"• <code>{html.escape(str(item))}</code>" for item in delivered_items)
            msg += (
                f"\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> "
                f"<b>{original_label}:</b>\n{items_text}"
            )
        elif delivered_link:
            msg += (
                f"\n\n<tg-emoji emoji-id=\"5197288647275071607\">🔗</tg-emoji> "
                f"<b>{original_label}:</b>\n<code>{html.escape(str(delivered_link))}</code>"
            )

        if latest_warranty:
            replacement_items = normalize_delivered_items(latest_warranty.get("items"))
            replacement_text = "\n".join(
                f"• <code>{html.escape(str(item))}</code>" for item in replacement_items
            )
            try:
                replacement_time = datetime.fromtimestamp(
                    float(latest_warranty.get("created_at", 0) or 0)
                ).strftime("%H:%M:%S %d/%m/%Y")
            except (TypeError, ValueError, OSError, OverflowError):
                replacement_time = "N/A"
            source_labels = {
                "auto_stock": "Auto Stock",
                "manual": "Thủ công",
            }
            replacement_source = source_labels.get(
                str(latest_warranty.get("source") or ""),
                str(latest_warranty.get("source") or "N/A"),
            )
            msg += (
                f"\n\n<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> "
                f"<b>BẢO HÀNH GẦN NHẤT:</b>\n"
                f"{replacement_text}\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> "
                f"<b>Lúc:</b> {replacement_time}\n"
                f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> "
                f"<b>Nguồn:</b> {html.escape(replacement_source)}"
            )

        reply_markup = None
        if not found_order.get("refunded_at") and "Hoàn thành" in status_text(found_order.get("status", "")):
            keyboard = [
                [InlineKeyboardButton("Hoàn tiền Full (100%)", callback_data=f"admrf_f_{order_code}")],
            ]
            if _resolve_order_duration_days(found_order) > 0:
                keyboard.append([InlineKeyboardButton("Hoàn số ngày chưa sử dụng", callback_data=f"admrf_p_{order_code}")])
            reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_html(msg, reply_markup=reply_markup)
        return

    await update.message.reply_text(f"❌ Không tìm thấy đơn hàng nào với mã <b>{order_code}</b>", parse_mode=ParseMode.HTML)

async def setemail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_USER_ID: return
    """
    Admin: Đổi email khách hàng cho đơn hàng
    Cú pháp: /setemail <Mã Đơn> <Email Mới>
    """

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp sai. Dùng: <code>/setemail &lt;Mã Đơn&gt; &lt;Email Mới&gt;</code>", parse_mode='HTML')
        return

    order_code = args[0].upper()
    new_email = args[1].strip()

    # Check if email is valid
    if "@" not in new_email:
        await update.message.reply_text("❌ Email không hợp lệ.")
        return

    # Find Order (Priority: Pending -> History)
    target_order = None
    source = None

    target_order = await pending_get(order_code)
    if target_order:
        source = 'pending'
    elif order_code in order_index:
        target_order = order_index[order_code]
        source = 'history'

    if not target_order:
        await update.message.reply_text("❌ Không tìm thấy đơn hàng này.")
        return

    # Update Email
    old_email = target_order.get("email") or target_order.get("user_input_email") or "Trống"

    if source == 'pending':
        target_order['email'] = new_email
    else:
        if 'user_input_email' in target_order:
            target_order['user_input_email'] = new_email
        else:
            target_order['email'] = new_email

    await save_data()

    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ CẬP NHẬT EMAIL KHÁCH HÀNG</b>\n\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Đơn hàng:</b> <code>{order_code}</code>\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔻</tg-emoji> <b>Cũ:</b> <code>{old_email}</code>\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔺</tg-emoji> <b>Mới:</b> <code>{new_email}</code>\n"
        f"<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> Email mới sẽ được dùng khi gửi mail Invite/Thông báo."
    )

async def baotri_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Bật/tắt chế độ bảo trì
    Cú pháp: /baotri [on/off]
    """
    global MAINTENANCE_MODE

    if not context.args:
        status = "BẬT" if MAINTENANCE_MODE else "TẮT"
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> Chế độ bảo trì đang: <b>{status}</b>\n\nDùng <code>/baotri on</code> hoặc <code>/baotri off</code> để thay đổi.", parse_mode=ParseMode.HTML)
        return

    action = context.args[0].lower()

    if action == "on":
        MAINTENANCE_MODE = True
        from app.core.runtime_loader import sync_runtime_bindings
        sync_runtime_bindings(globals(), ["MAINTENANCE_MODE"])
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐÃ BẬT CHẾ ĐỘ BẢO TRÌ</b>\n\nNgười dùng sẽ không thể sử dụng bot (trừ Admin).", parse_mode=ParseMode.HTML)
    elif action == "off":
        MAINTENANCE_MODE = False
        from app.core.runtime_loader import sync_runtime_bindings
        sync_runtime_bindings(globals(), ["MAINTENANCE_MODE"])
        await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ TẮT CHẾ ĐỘ BẢO TRÌ</b>\n\nBot hoạt động bình thường trở lại.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ Cú pháp sai. Dùng: <code>/baotri on</code> hoặc <code>/baotri off</code>", parse_mode=ParseMode.HTML)

async def aimode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Bật/tắt AI tự động trả lời
    Cú pháp: /aimode [on/off]
    """
    global AI_AUTO_REPLY

    if not context.args:
        status = "BẬT <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>" if AI_AUTO_REPLY else "TẮT ❌"
        ai_status = "<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Bot sẽ tự động trả lời mọi tin nhắn bằng AI" if AI_AUTO_REPLY else "<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Chỉ trả lời khi có /ask"

        await update.message.reply_html(
            f"<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> <b>TRẠNG THÁI AI AUTO-REPLY</b>\n\n"
            f"Hiện tại: <b>{status}</b>\n"
            f"{ai_status}\n\n"
            f"Thay đổi:\n"
            f"• <code>/aimode on</code> - Bật AI tự động\n"
            f"• <code>/aimode off</code> - Tắt AI tự động"
        )
        return

    action = context.args[0].lower()

    if action == "on":
        AI_AUTO_REPLY = True
        from app.core.runtime_loader import sync_runtime_bindings
        sync_runtime_bindings(globals(), ["AI_AUTO_REPLY"])
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ BẬT AI AUTO-REPLY</b>\n\n"
            "<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Bot giờ sẽ tự động trả lời mọi tin nhắn bằng AI.\n"
            "Khách không cần dùng /ask nữa!\n\n"
            "<i>AI có context về sản phẩm, đơn hàng và thông tin khách.</i>"
        )
    elif action == "off":
        AI_AUTO_REPLY = False
        from app.core.runtime_loader import sync_runtime_bindings
        sync_runtime_bindings(globals(), ["AI_AUTO_REPLY"])
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">🔕</tg-emoji> <b>ĐÃ TẮT AI AUTO-REPLY</b>\n\n"
            "<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Bot chỉ trả lời khi khách dùng /ask\n"
            "Các chức năng khác hoạt động bình thường."
        )
    else:
        await update.message.reply_text("❌ Cú pháp sai. Dùng: <code>/aimode on</code> hoặc <code>/aimode off</code>", parse_mode=ParseMode.HTML)


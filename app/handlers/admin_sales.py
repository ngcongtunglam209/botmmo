async def sale_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tạo SALE event với % giảm giá và tự động broadcast cho tất cả users
    Cú pháp: /sale <% giảm> <số lượng> <số ngày>
    Ví dụ: /sale 30 50 7 (giảm 30%, 50 mã, hết hạn sau 7 ngày)
    """
    if len(context.args) != 3:
        await update.message.reply_html(
            "<b><tg-emoji emoji-id=\"6129860303619363484\">📢</tg-emoji> TẠO SALE EVENT</b>\n\n"
            "Cú pháp: <code>/sale [% giảm] [số lượng] [số ngày]</code>\n\n"
            "<b>Ví dụ:</b>\n"
            "<code>/sale 30 50 7</code>\n"
            "→ Giảm 30%, 50 mã, hết hạn sau 7 ngày\n\n"
            "<b>Bot sẽ tự động:</b>\n"
            "• Tạo mã giảm giá theo %\n"
            "• Broadcast thông báo SALE đẹp mắt\n"
            "• Gửi đến tất cả users"
        )
        return

    try:
        discount_percent = int(context.args[0])
        quantity = int(context.args[1])
        days = int(context.args[2])

        if not (1 <= discount_percent <= 100):
            await update.message.reply_text("❌ % giảm giá phải từ 1-100%")
            return

        if quantity < 1:
            await update.message.reply_text("❌ Số lượng phải > 0")
            return

        if days < 1:
            await update.message.reply_text("❌ Số ngày phải > 0")
            return

    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số hợp lệ!")
        return

    # Tính toán
    expires_date = datetime.now() + timedelta(days=days)
    expires_str = expires_date.strftime('%d-%m-%Y')

    # Tạo mã coupon đẹp
    sale_code = f"SALE{discount_percent}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

    # Lưu coupon vào database
    coupons[sale_code] = {
        "discount": discount_percent,
        "is_percent": True,
        "quantity": quantity,
        "expires": expires_str,
        "used": 0
    }
    await save_data()

    # Thông báo cho admin trước
    admin_preview = (
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ TẠO SALE EVENT THÀNH CÔNG!</b>\n\n"
        f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>Mã giảm giá:</b> <code>{sale_code}</code>\n"
        f"<tg-emoji emoji-id=\"5303290914041505430\">💥</tg-emoji> <b>Giảm:</b> {discount_percent}%\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Số lượng:</b> {quantity} mã\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Hết hạn:</b> {expires_str}\n"
        f"<tg-emoji emoji-id=\"5303290914041505430\">🚀</tg-emoji> <b>Đang broadcast đến {len(user_data_db)} users...</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <i>Bot vẫn hoạt động bình thường, broadcast chạy nền!</i>"
    )
    status_msg = await update.message.reply_html(admin_preview)

    # Tạo thông báo SALE siêu đẹp cho users
    sale_message = (
        f"<tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji><tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji><tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji> <b>FLASH SALE - GIẢM GIÁ SỐC!</b> <tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji><tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji><tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji>\n\n"
        f"<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>GIẢM NGAY {discount_percent}%</b> <tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji>\n"
        f"Áp dụng cho toàn bộ sản phẩm trong cửa hàng\n\n"
        f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>MÃ GIẢM GIÁ:</b>\n"
        f"<code>{sale_code}</code>\n"
        f"<i>(Chạm để copy)</i>\n\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Chỉ có {quantity} mã</b>\n"
        f"<tg-emoji emoji-id=\"5413879192267805083\">📅</tg-emoji> <b>Hết hạn:</b> {expires_date.strftime('%d/%m/%Y')}\n\n"
        f"<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>NHANH TAY KẺO HẾT!</b> <tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji>\n\n"
        f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Bấm /start để mua ngay!"
    )

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: CHẠY BROADCAST TRONG BACKGROUND TASK - KHÔNG BLOCK BOT!
    async def _broadcast_sale_background(msg_obj):
        """Background task để broadcast sale - không block bot"""
        success_count = 0
        fail_count = 0
        blocked_ids = []
        all_keys = list(user_data_db.keys())
        total_users = len(all_keys)

        for idx, user_id_str in enumerate(all_keys, 1):
            try:
                user_id = int(user_id_str)
                if user_id in banned_users:
                    continue

                result = await broadcast_send_message(
                    context.bot, user_id, sale_message, parse_mode=ParseMode.HTML
                )
                if result == "ok":
                    success_count += 1
                else:
                    fail_count += 1
                    if result in {"blocked", "invalid"}:
                        blocked_ids.append(user_id_str)
                    elif fail_count <= 3:
                        logger.warning(f"Không thể gửi SALE cho user {user_id_str}: {result}")
                await asyncio.sleep(0.05)

            except (ValueError, TypeError, KeyError, IndexError) as e:
                fail_count += 1
                if fail_count <= 3:
                    logger.warning(f"Không thể gửi SALE cho user {user_id_str}: {e}")

            if idx % 20 == 0 or idx == total_users:
                try:
                    progress = generate_progress_bar(idx, total_users)
                    await msg_obj.edit_text(
                        f"<tg-emoji emoji-id=\"5303290914041505430\">🚀</tg-emoji> <b>Đang gửi SALE broadcast...</b>\n"
                        f"{progress}\n"
                        f"{E_SUCCESS} {success_count} | ❌ {fail_count} | <tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> {idx}/{total_users}\n"
                        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Bot vẫn hoạt động bình thường!",
                        parse_mode=ParseMode.HTML
                    )
                except (ValueError, TypeError, KeyError, IndexError) as e:
                    logger.debug(f"Cannot update sale broadcast progress at {idx}/{total_users}: {e}")

        cleaned_count = 0
        if blocked_ids:
            cleaned_count = await _cleanup_blocked_users(blocked_ids)

        result_message = (
            f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>BÁO CÁO BROADCAST SALE</b>\n\n"
            f"{generate_progress_bar(total_users, total_users)}\n"
            f"{E_SUCCESS} <b>Gửi thành công:</b> {success_count}\n"
            f"❌ <b>Thất bại:</b> {fail_count}\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Tổng users:</b> {len(user_data_db)}\n\n"
            f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>Mã:</b> <code>{sale_code}</code>\n"
            f"<tg-emoji emoji-id=\"5303290914041505430\">💥</tg-emoji> <b>Giảm:</b> {discount_percent}%\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Còn lại:</b> {quantity} mã\n\n"
            f"<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>SALE EVENT ĐÃ KHỞI ĐỘNG!</b>"
        )
        if cleaned_count > 0:
            result_message += f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">🧹</tg-emoji> <b>Đã tự động xoá {cleaned_count} user block bot</b>"
        try:
            await msg_obj.edit_text(
                text=result_message,
                parse_mode=ParseMode.HTML
            )
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Cannot send broadcast report to admin: {e}")
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=result_message, parse_mode=ParseMode.HTML)

    # Chạy broadcast trong background - BOT KHÔNG BỊ ĐƠ!
    create_background_task(_broadcast_sale_background(status_msg))

async def refund_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Hoàn tiền đơn hàng (Hỗ trợ cả User thường và API Partner)
    Cú pháp: /refund <mã đơn>
    """
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập mã đơn hàng. VD: /refund ICLD123456")
        return

    order_code = context.args[0].upper()

    # FIX BUG #17: Tìm đơn hàng với O(1) index lookup thay vì O(n) scan
    found_order = db_get_order(order_code)

    if not found_order:
        await update.message.reply_text(f"❌ Không tìm thấy đơn hàng {order_code}")
        return

    # Kiểm tra trạng thái
    # So chu thuong: moi trang thai hoan tien ma code ghi ra deu la "Đã hoàn
    # tiền" (chu h thuong), nen so voi "Hoàn tiền" thi khong bao gio khop va
    # cung mot don co the hoan di hoan lai nhieu lan. Doc them refunded_at
    # giong nhanh nut bam o admin_refund.py.
    if found_order.get("refunded_at") or "hoàn tiền" in status_text(found_order.get("status")).lower():
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng {order_code} đã được hoàn tiền trước đó.")
        return

    user_id = found_order.get("user_id")
    amount = found_order.get("amount")

    # === TRƯỜNG HỢP 1: HOÀN TIỀN CHO API PARTNER ===
    if isinstance(user_id, str) and user_id.startswith("PARTNER_"):
        partner_name = user_id.replace("PARTNER_", "")

        partner_key_hash = str(found_order.get("api_partner_key_hash") or "")
        adjusted, new_bal, key_data = await safe_api_adjust_balance_by_hash(
            partner_key_hash,
            amount,
            save=True,
            reason=f"Admin refund {order_code}",
        )
        if not adjusted:
            target_key = None
            for k, v in api_keys.items():
                p_name = v if isinstance(v, str) else v.get("name")
                if p_name == partner_name:
                    target_key = k
                    break
            if target_key:
                adjusted, new_bal, key_data = await safe_api_adjust_balance(
                    target_key,
                    amount,
                    save=True,
                    reason=f"Admin refund {order_code}",
                )

        if adjusted:
            found_order["status"] = "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> Đã hoàn tiền (Ví chung)"
            found_order["refunded_at"] = time.time()
            found_order["refund_amount"] = int(amount or 0)
            found_order["refund_reason"] = "100%"
            found_order["refund_target"] = "Ví chung"
            await save_data(force=True, tables=[HISTORY_FILE])

            await update.message.reply_html(
                f"{E_SUCCESS} <b>ĐÃ HOÀN TIỀN API THÀNH CÔNG!</b>\n\n"
                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner_name}\n"
                f"{E_TAG} <b>Hoàn lại:</b> {amount:,} VNĐ\n"
                f"{E_TAG} <b>Số dư mới:</b> {int(new_bal):,} VNĐ"
            )
            try:
                notify_chat_id = int((key_data or {}).get("user_id", 0) or 0)
            except (TypeError, ValueError):
                notify_chat_id = 0
            if notify_chat_id > 0:
                try:
                    await context.bot.send_message(
                        chat_id=notify_chat_id,
                        text=(
                            f"{E_SOS} <b>THÔNG BÁO HOÀN TIỀN API</b>\n\n"
                            f"Mã đơn: <code>{order_code}</code>\n"
                            f"Sản phẩm: {found_order.get('product_name')}\n"
                            f"Số tiền hoàn: <b>+{int(amount or 0):,} VNĐ</b>\n"
                            f"Nơi hoàn: <b>Ví chung</b>\n"
                            f"Số dư ví chung hiện tại: <b>{int(new_bal or 0):,} VNĐ</b>"
                        ),
                        parse_mode=ParseMode.HTML
                    )
                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"Không thể gửi tin nhắn hoàn API cho partner {partner_name}: {e}")
        else:
            await update.message.reply_text(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không tìm thấy Key của Partner '{partner_name}'. Không thể hoàn tiền tự động.")
        return

    # === TRƯỜNG HỢP 2: HOÀN TIỀN CHO USER TELEGRAM ===
    # Dùng db_update_balance thay vì trực tiếp modify dict
    user_info = db_get_user(user_id)
    if not user_info:
        # Tạo user record nếu chưa tồn tại
        db_upsert_user(user_id, found_order.get("username"), found_order.get("full_name"), datetime.now().isoformat(), balance=0)
        user_info = db_get_user(user_id)

    current_balance = user_info.get("balance", 0)
    new_balance = current_balance + amount
    db_update_balance(user_id, new_balance)

    # Cập nhật trạng thái đơn hàng
    found_order["status"] = "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> Đã hoàn tiền (Ví Bot)"
    found_order["refunded_at"] = time.time()
    found_order["refund_amount"] = int(amount or 0)
    found_order["refund_reason"] = "100%"
    found_order["refund_target"] = "Ví Bot"

    await save_data(force=True, tables=[HISTORY_FILE, USERS_FILE, TRANSACTION_HISTORY_FILE])

    # Thông báo cho admin
    await update.message.reply_html(
        f"{E_SUCCESS} <b>ĐÃ HOÀN TIỀN THÀNH CÔNG!</b>\n\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
        f"{E_TAG} <b>Số tiền hoàn:</b> {amount:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>User:</b> {html.escape(str(found_order.get('full_name') or 'N/A'))}\n"
        f"{E_TAG} <b>Số dư mới:</b> {new_balance:,} VNĐ"
    )

    # Thông báo cho user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"{E_SOS} <b>THÔNG BÁO HOÀN TIỀN</b>\n\n"
                f"Đơn hàng <b>{order_code}</b> của bạn đã được hoàn tiền vào số dư Bot.\n\n"
                f"{E_TAG} <b>Số tiền:</b> +{amount:,} VNĐ\n"
                f"{E_TAG} <b>Số dư hiện tại:</b> {new_balance:,} VNĐ\n\n"
                f"Số dư này sẽ được tự động trừ vào đơn hàng tiếp theo của bạn."
            ),
            parse_mode=ParseMode.HTML
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"Không thể gửi tin nhắn hoàn tiền cho user {user_id}: {e}")


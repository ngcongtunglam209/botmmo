# ==============================================================================
#  CRON JOBS FOR ADVANCED FEATURES
# ==============================================================================

LIVE_CHAT_TIMEOUT_SECONDS = 180  # 3 phút không phản hồi sẽ tự đóng

async def auto_close_inactive_chats_job(context: ContextTypes.DEFAULT_TYPE):
    """Tự động đóng live chat nếu 3 phút không có phản hồi từ bất kỳ bên nào"""
    now = time.time()
    closed_any = False
    for uid_str, chat in list(live_chats.items()):
        if chat.get('status') != 'active':
            continue
        last = chat.get('last_activity', 0)
        if now - last >= LIVE_CHAT_TIMEOUT_SECONDS:
            chat['status'] = 'closed'
            closed_any = True
            try:
                user_id = int(uid_str)
                await context.bot.send_message(
                    user_id,
                    lt(user_id, '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Chat đã được tự động đóng</b> do không có phản hồi trong 3 phút.\nBạn có thể mở lại chat bất cứ lúc nào từ menu.', '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Chat was closed automatically</b> after 3 minutes of inactivity.\nYou can reopen it anytime from the menu.', '<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> 由于 3 分钟无响应，<b>聊天已自动关闭</b>。\n您可以随时从菜单重新打开。'),
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_main_menu(user_id=user_id)
                )
            except (TelegramError, ValueError, TypeError, KeyError, IndexError):
                logger.debug("Suppressed error at L1965")
            try:
                await context.bot.send_message(
                    ADMIN_USER_ID,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Chat với <code>{uid_str}</code> đã tự động đóng (3p không phản hồi).",
                    parse_mode=ParseMode.HTML
                )
            except (TelegramError, ValueError, TypeError, KeyError, IndexError):
                logger.debug("Suppressed error at L1973")
    if closed_any:
        await save_data()


async def warranty_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Send reminders for warranties expiring soon"""
    now = time.time()
    reminder_threshold = WARRANTY_REMINDER_DAYS * 24 * 60 * 60

    for order in order_history:
        warranty_expires = order.get('warranty_expires')
        warranty_status = order.get('warranty_status')

        if (warranty_expires and warranty_status == 'active' and
            not order.get('warranty_reminder_sent')):

            time_until_expiry = warranty_expires - now

            if 0 < time_until_expiry <= reminder_threshold:
                order['warranty_reminder_sent'] = True

                expiry_date = datetime.fromtimestamp(warranty_expires).strftime('%d/%m/%Y')
                user_id = order['user_id']
                order_code = order['order_code']
                prod_name = order.get('product_name', 'Sản phẩm')

                try:
                    await context.bot.send_message(
                        user_id,
                        lt(
                            user_id,
                            "{error} <b>BẢO HÀNH SẮP HẾT HẠN</b>\n\n{tag} <b>Sản phẩm:</b> {product}\n{tag} <b>Mã đơn:</b> <code>{code}</code>\n{calendar} <b>Hết hạn:</b> {date}\n\nNếu có vấn đề, vui lòng báo ngay!",
                            "{error} <b>WARRANTY EXPIRING SOON</b>\n\n{tag} <b>Product:</b> {product}\n{tag} <b>Order code:</b> <code>{code}</code>\n{calendar} <b>Expires:</b> {date}\n\nReport any issue before it expires.",
                            "{error} <b>保修即将到期</b>\n\n{tag} <b>商品：</b> {product}\n{tag} <b>订单号：</b> <code>{code}</code>\n{calendar} <b>到期日：</b> {date}\n\n如有问题，请在到期前立即报告。",
                            error=E_ERROR, tag=E_TAG, calendar=E_CALENDAR, product=prod_name, code=order_code, date=expiry_date,
                        ), parse_mode=ParseMode.HTML
                    )
                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                    logger.error(f"Cannot send warranty reminder to {user_id}: {e}")

    await save_data()



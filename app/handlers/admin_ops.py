def _extract_stock_channel_topic_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Tham so thu hai: message_thread_id cua topic. Thieu/sai -> 0."""
    args = getattr(context, "args", None) or []
    if len(args) < 2:
        return 0
    try:
        return max(0, int(str(args[1]).strip()))
    except ValueError:
        return 0


def _extract_stock_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lấy chat id từ tin nhắn được forward, hoặc từ ID admin gõ tay."""
    message = update.effective_message
    forward_chat = getattr(message, "forward_from_chat", None) if message else None
    if forward_chat is not None and getattr(forward_chat, "id", None):
        return int(forward_chat.id), str(getattr(forward_chat, "title", "") or "")

    if context.args:
        raw = str(context.args[0]).strip()
        if raw.lower() in {"off", "tat", "tắt", "0"}:
            return 0, ""
        try:
            return int(raw), ""
        except ValueError:
            return None, ""
    return None, ""


async def setstockchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Đặt kênh nhận thông báo nhập kho.

    Cú pháp: /setstockchannel <chat_id> | off, hoặc forward 1 tin từ kênh đó.
    """
    channel_id, title = _extract_stock_channel_id(update, context)
    topic_id = _extract_stock_channel_topic_id(context)

    if channel_id is None:
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>ĐẶT KÊNH THÔNG BÁO NHẬP KHO</b>\n\n"
            "<b>Cách 1:</b> Forward bất kỳ tin nhắn nào từ kênh đó vào đây kèm lệnh <code>/setstockchannel</code>\n"
            "<b>Cách 2:</b> <code>/setstockchannel -1001234567890</code>\n"
            "<b>Topic trong group forum:</b> <code>/setstockchannel -1001234567890 580</code>\n"
            "Số thứ hai lấy từ link topic <code>t.me/c/&lt;group&gt;/&lt;topic&gt;</code>.\n"
            "<b>Tắt:</b> <code>/setstockchannel off</code>\n\n"
            "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Nhớ add bot vào kênh và cấp quyền đăng bài trước.\n"
            "Xem cấu hình hiện tại: <code>/stockchannel</code>"
        )
        return

    if channel_id == 0:
        await set_stock_channel_id(0)
        await update.message.reply_html(
            f"{E_SUCCESS} <b>ĐÃ TẮT THÔNG BÁO NHẬP KHO.</b>\n\n"
            "Bật lại bằng <code>/setstockchannel &lt;chat_id&gt;</code>."
        )
        return

    # Gửi thử ngay để admin biết bot có đăng được không, thay vì phát hiện lúc nhập kho.
    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=f"{E_SUCCESS} <b>Kênh này đã được đặt làm nơi nhận thông báo nhập kho.</b>",
            parse_mode=ParseMode.HTML,
            **topic_kwargs(topic_id),
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await update.message.reply_html(
            f"{E_ERROR} <b>KHÔNG GỬI ĐƯỢC VÀO KÊNH <code>{channel_id}</code>"
            f"{f' TOPIC <code>{topic_id}</code>' if topic_id else ''}</b>\n\n"
            f"<code>{html.escape(str(e))}</code>\n\n"
            "Kiểm tra: bot đã vào kênh chưa, và đã có quyền đăng bài chưa. Chưa lưu cấu hình."
        )
        return

    await set_stock_channel_id(channel_id, topic_id)
    title_line = f"\n{E_TAG} <b>Tên kênh:</b> {html.escape(title)}" if title else ""
    topic_line = f"\n{E_TAG} <b>Topic:</b> <code>{topic_id}</code>" if topic_id else ""
    await update.message.reply_html(
        f"{E_SUCCESS} <b>ĐÃ ĐẶT KÊNH THÔNG BÁO NHẬP KHO</b>\n\n"
        f"{E_ID} <b>Chat ID:</b> <code>{channel_id}</code>{title_line}{topic_line}\n\n"
        "Từ giờ mỗi lần thêm kho, bot sẽ đăng bài lên kênh này."
    )


async def stockchannel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xem kênh nhập kho đang dùng."""
    channel_id = get_stock_channel_id()
    if not channel_id:
        await update.message.reply_html(
            f"{E_TAG} <b>THÔNG BÁO NHẬP KHO: ĐANG TẮT</b>\n\n"
            "Bật bằng <code>/setstockchannel &lt;chat_id&gt;</code> hoặc forward 1 tin từ kênh."
        )
        return

    source = "lệnh /setstockchannel" if isinstance(bot_settings, dict) and "stock_channel_id" in bot_settings else "biến môi trường STOCK_CHANNEL_ID"
    topic_id = get_stock_channel_topic_id()
    topic_line = f"{E_TAG} <b>Topic:</b> <code>{topic_id}</code>\n" if topic_id else ""
    await update.message.reply_html(
        f"{E_SUCCESS} <b>THÔNG BÁO NHẬP KHO: ĐANG BẬT</b>\n\n"
        f"{E_ID} <b>Chat ID:</b> <code>{channel_id}</code>\n"
        f"{topic_line}"
        f"{E_TAG} <b>Nguồn cấu hình:</b> {source}\n\n"
        "Tắt bằng <code>/setstockchannel off</code>."
    )


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Broadcast thông báo hết hàng thủ công
    Cú pháp: /notify <product_id> [out|back]
    """
    if not context.args:
        # Show product list
        if not products:
            await update.message.reply_text("❌ Chưa có sản phẩm nào.")
            return

        msg = "<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> DANH SÁCH SẢN PHẨM</b>\n\n"
        msg += "Cú pháp: <code>/notify [product_id] [out/back]</code>\n\n"

        for pid, p in products.items():
            stock = len(p.get('stock', []))
            status = "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>" if stock > 0 else "❌"
            msg += f"{status} <code>{pid}</code> - {p['name']} ({stock})\n"

        msg += "\n<b>Ví dụ:</b>\n"
        msg += "<code>/notify p_123 out</code> - Thông báo hết hàng\n"
        msg += "<code>/notify p_123 back</code> - Thông báo có hàng"

        await update.message.reply_html(msg)
        return

    # Parse arguments
    prod_id = context.args[0]
    action = context.args[1].lower() if len(context.args) > 1 else "out"

    # Validate product
    if prod_id not in products:
        await update.message.reply_text(f"❌ Không tìm thấy sản phẩm ID: {prod_id}")
        return

    p = products[prod_id]
    product_name = p['name']
    stock_count = len(p.get('stock', []))

    await update.message.reply_text(f"<tg-emoji emoji-id=\"6129860303619363484\">📢</tg-emoji> Đang broadcast thông báo cho <b>{product_name}</b>...", parse_mode=ParseMode.HTML)

    # Broadcast
    if action == "out":
        await broadcast_out_of_stock(context, product_name, prod_id)
    elif action == "back":
        await broadcast_back_in_stock(context, product_name, prod_id, stock_count)
    else:
        await update.message.reply_text("❌ Action phải là 'out' hoặc 'back'")
        return

    await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã broadcast thông báo!")

async def pending_manual_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Xem danh sách đơn hàng manual đang chờ Admin xử lý
    """
    if not pending_manual_orders:
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>KHÔNG CÓ ĐƠN HÀNG MANUAL NÀO!</b>\n\n"
            "Tất cả đơn hàng đã được xử lý."
        )
        return

    msg = f"<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> ĐƠN HÀNG MANUAL CHỜ XỬ LÝ ({len(pending_manual_orders)})</b>\n\n"

    # Group by product
    by_product = {}
    for order_code, info in pending_manual_orders.items():
        prod_id = info.get('product_id', 'unknown')
        if prod_id not in by_product:
            by_product[prod_id] = []
        by_product[prod_id].append((order_code, info))

    for prod_id, orders in by_product.items():
        p = products.get(prod_id)
        prod_name = p['name'] if p else "Sản phẩm đã xóa"
        max_limit = p.get('max_pending_orders', 10) if p else 10

        msg += f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{prod_name}</b> ({len(orders)}/{max_limit})\n"

        for order_code, info in orders:
            time_ago = int((time.time() - info.get('timestamp', 0)) / 60)
            email_status = "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>" if info.get('email') else "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji>"

            msg += (
                f"   {email_status} <code>{order_code}</code>\n"
                f"      • Email: <code>{info.get('email', 'Chưa nhập')}</code>\n"
                f"      • Khách: {html.escape(str(info.get('full_name') or 'N/A'))}\n"
                f"      • Chờ: {time_ago}'\n"
            )
        msg += "\n"

    msg += (
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Hành động:</b>\n"
        "1. Xử lý đơn (gửi email, setup...)\n"
        "2. Vào notification message từ bot\n"
        "3. Bấm <b><tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã hoàn thành</b>\n\n"
        f"<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> Tổng: {len(pending_manual_orders)} đơn chờ"
    )

    await update.message.reply_html(msg)

async def clearpending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Xóa đơn manual cũ/stuck (Admin tool)
    Cú pháp: /clearpending [order_code] hoặc /clearpending all
    """
    if not context.args:
        # Show list
        if not pending_manual_orders:
            await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Không có đơn manual nào.")
            return

        msg = "<b><tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> XÓA ĐƠN MANUAL</b>\n\n"
        msg += f"Tổng: {len(pending_manual_orders)} đơn\n\n"

        for code, info in list(pending_manual_orders.items())[:10]:
            time_ago = int((time.time() - info.get('timestamp', 0)) / 60)
            msg += f"• <code>{code}</code> - {info.get('product_name')} ({time_ago}')\n"

        msg += (
            "\n<b>Cú pháp:</b>\n"
            "<code>/clearpending [order_code]</code> - Xóa 1 đơn\n"
            "<code>/clearpending all</code> - Xóa tất cả"
        )

        await update.message.reply_html(msg)
        return

    action = context.args[0]

    if action.lower() == "all":
        count = len(pending_manual_orders)
        pending_manual_orders.clear()
        await save_data()
        await update.message.reply_html(f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>ĐÃ XÓA {count} ĐƠN MANUAL</b>\n\nTất cả slot đã được giải phóng.")
    else:
        order_code = action.upper()
        if order_code in pending_manual_orders:
            info = pending_manual_orders.pop(order_code)
            await save_data()
            await update.message.reply_html(
                f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>ĐÃ XÓA ĐƠN</b>\n\n"
                f"Mã: <code>{order_code}</code>\n"
                f"SP: {info.get('product_name')}\n\n"
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Nhớ hoàn tiền cho khách nếu đã thu!"
            )
        else:
            await update.message.reply_text(f"❌ Không tìm thấy đơn: {order_code}")

async def resetnotify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Reset danh sách sản phẩm đã thông báo hết hàng
    Để có thể broadcast lại
    """


    count = len(notified_out_of_stock)
    notified_out_of_stock.clear()

    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ RESET DANH SÁCH THÔNG BÁO</b>\n\n"
        f"Đã xóa {count} sản phẩm khỏi danh sách đã thông báo.\n"
        f"Giờ có thể broadcast lại cho các sản phẩm này."
    )

async def setlimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Đặt giới hạn đơn chờ xử lý cho sản phẩm manual."""
    if len(context.args) != 2:
        manual_products = {pid: p for pid, p in products.items() if p.get('requires_gmail')}
        if not manual_products:
            await update.message.reply_text("ℹ️ Không có sản phẩm manual nào.")
            return
        msg = "<b>📊 GIỚI HẠN ĐƠN CHỜ XỬ LÝ</b>\n\nCú pháp: <code>/setlimit [id] [số_đơn]</code>\n\n"
        for pid, product in manual_products.items():
            current_limit = product.get('max_pending_orders', 10)
            pending_count = sum(1 for order in pending_manual_orders.values() if order.get('product_id') == pid)
            msg += f"📧 <b>{product['name']}</b>\n   ID: <code>{pid}</code>\n   Giới hạn: {current_limit} đơn\n   Đang xử lý: {pending_count}/{current_limit}\n\n"
        msg += "\n<b>VD:</b> <code>/setlimit p_123 20</code>"
        await update.message.reply_html(msg)
        return

    prod_id = context.args[0]
    try:
        max_orders = int(context.args[1])
        if max_orders < 1:
            await update.message.reply_text("❌ Số đơn phải >= 1")
            return
    except ValueError:
        await update.message.reply_text("❌ Số đơn không hợp lệ")
        return
    if prod_id not in products:
        await update.message.reply_text(f"❌ Không tìm thấy product ID: {prod_id}")
        return
    if not products[prod_id].get('requires_gmail'):
        await update.message.reply_text("⚠️ Sản phẩm này là AUTO, không cần giới hạn đơn chờ.")
        return

    products[prod_id]['max_pending_orders'] = max_orders
    await save_data()
    pending_count = sum(1 for order in pending_manual_orders.values() if order.get('product_id') == prod_id)
    await update.message.reply_html(
        f"✅ <b>ĐÃ CẬP NHẬT GIỚI HẠN</b>\n\n"
        f"📦 <b>Sản phẩm:</b> {products[prod_id]['name']}\n"
        f"📊 <b>Giới hạn mới:</b> {max_orders} đơn\n"
        f"⏳ <b>Đang xử lý:</b> {pending_count}/{max_orders}"
    )


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    completed_orders = [
        order for order in order_history
        if is_completed_order(order) and not order.get("refunded_at")
    ]
    total_revenue = sum(int(order.get('amount', 0) or 0) for order in completed_orders)
    total_orders = len(completed_orders)
    week_ago = time.time() - (7 * 24 * 60 * 60)
    week_revenue = sum(
        int(order.get('amount', 0) or 0)
        for order in completed_orders
        if order.get('timestamp', 0) > week_ago
    )
    product_sales = {}
    for order in completed_orders:
        if order.get('type') != 'store_product':
            continue
        pid = order.get('product_id', 'Unknown')
        if pid not in product_sales:
            product_sales[pid] = {'name': order.get('product_name', 'Unknown'), 'count': 0}
        product_sales[pid]['count'] += order.get('quantity', 1)
    top_products = sorted(product_sales.items(), key=lambda item: item[1]['count'], reverse=True)[:5]
    msg = (
        f"<b>📈 THỐNG KÊ TỔNG QUAN</b>\n\n"
        f"💰 <b>Tổng doanh thu:</b> {total_revenue:,} VNĐ\n"
        f"📦 <b>Tổng đơn:</b> {total_orders}\n"
        f"📅 <b>Doanh thu 7 ngày:</b> {week_revenue:,} VNĐ\n\n"
        f"⭐️ <b>TOP SẢN PHẨM:</b>\n"
    )
    for rank, (_, data) in enumerate(top_products, 1):
        msg += f"{rank}. {data['name']}: {data['count']} đã bán\n"
    await update.message.reply_html(msg)

async def chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    """Admin: List all active chats"""

    active_chats = [(uid, chat) for uid, chat in live_chats.items() if chat['status'] == 'active']

    if not active_chats:
        await update.message.reply_text("Không có chat đang hoạt động")
        return

    header = "<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> <b>DANH SÁCH CHAT</b>\n\n"
    entries = []
    for uid_str, chat in active_chats:
        unread = chat.get('unread_by_admin', 0)
        last_msg = chat['messages'][-1] if chat['messages'] else None

        try:
            user = db_get_user(int(uid_str))
            name = user.get('first_name', 'User') if user else 'Unknown'
        except (TypeError, ValueError) as e:
            logger.debug(f"Cannot parse chat user id '{uid_str}': {e}")
            name = 'User'

        badge = f"<tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji> {unread}" if unread > 0 else "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>"
        safe_name = html.escape(name)
        entry = f"{badge} {safe_name} (ID: <code>{uid_str}</code>)\n"
        if last_msg:
            raw_preview = last_msg['text'][:30] if last_msg.get('text') else "[Image]"
            safe_preview = html.escape(raw_preview)
            entry += f"   {safe_preview}...\n"
        entry += "\n"
        entries.append(entry)

    # Chia nhỏ message để tránh lỗi "Message is too long" (Telegram max 4096 chars)
    msg = header
    for entry in entries:
        if len(msg) + len(entry) > 3900:
            await update.message.reply_html(msg)
            msg = ""
        msg += entry

    msg += "\nDùng /chat {user_id} để mở chat"
    await update.message.reply_html(msg)

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    """Admin: Open specific chat"""

    if not context.args:
        await update.message.reply_text("Dùng: /chat {user_id}")
        return

    target_user_id = context.args[0]

    if target_user_id not in live_chats:
        await update.message.reply_text("Chat không tồn tại")
        return

    chat = live_chats[target_user_id]
    chat['unread_by_admin'] = 0
    await save_data()

    # Show messages
    msg = f"<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Chat với User ID: <code>{target_user_id}</code>\n\n"
    for m in chat['messages'][-20:]:
        from_who = "User" if m['from'] == 'user' else "Admin"
        time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
        content = m.get('text', '[Image]')
        safe_content = html.escape(str(content))
        msg += f"<b>{from_who}</b> ({time_str}):\n{safe_content}\n\n"

    msg += "Reply tin nhắn này để trả lời user"

    kb = [[_btn("Chat", icon_id="5443038326535759644", callback_data=f"admin_close_chat:{target_user_id}")]]
    await update.message.reply_html(msg, reply_markup=InlineKeyboardMarkup(kb))
    context.user_data['admin_chatting_with'] = target_user_id

async def _legacy_nhapdata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin: Phục hồi dữ liệu từ file backup ZIP
    Cú pháp:
    1) Reply vào file ZIP do bot gửi trước đó và gõ /nhapdata
    2) Hoặc gửi trực tiếp file .zip kèm caption /nhapdata
    """
    if update.effective_user.id != ADMIN_USER_ID: return

    # Accept ZIP from replied message OR attached directly to command message
    source_document = None
    if update.message and getattr(update.message, "document", None):
        source_document = update.message.document
    elif (
        update.message
        and getattr(update.message, "reply_to_message", None)
        and getattr(update.message.reply_to_message, "document", None)
    ):
        source_document = update.message.reply_to_message.document

    if not source_document:
        await update.message.reply_text(
            f'{E_ERROR} <b>Không tìm thấy file ZIP.</b>\n\n'
            "Cách dùng:\n"
            "• Reply vào file ZIP backup rồi gõ <code>/nhapdata</code>\n"
            "• Hoặc gửi file <code>.zip</code> kèm caption <code>/nhapdata</code>",
            parse_mode=ParseMode.HTML
        )
        return

    document = source_document
    if not document.file_name or not document.file_name.lower().endswith('.zip'):
        await update.message.reply_text(
            f'{E_ERROR} <b>File không hợp lệ.</b> Phải là file <code>.zip</code>.',
            parse_mode=ParseMode.HTML
        )
        return

    msg = await update.message.reply_text("<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang tải file backup xuống...")
    try:
        # Download ZIP file
        file = await context.bot.get_file(document.file_id)
        temp_zip_path = f"temp_restore_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        await file.download_to_drive(temp_zip_path)

        await msg.edit_text("<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang giải nén và phục hồi dữ liệu...")

        # Unzip and overwrite files
        import zipfile
        base_dir = os.path.dirname(os.path.abspath(__file__))
        async with file_lock:
            with zipfile.ZipFile(temp_zip_path, 'r') as zipf:
                # Extract all files safely, overwriting existing JSON files
                for file_info in zipf.infolist():
                    # Security check: only allow json files in root directory
                    if file_info.filename.endswith('.json') and '/' not in file_info.filename and '\\' not in file_info.filename:
                        zipf.extract(file_info, path=base_dir)

            # Remove temp zip
            os.remove(temp_zip_path)

        # Reload DB into memory
        await msg.edit_text("<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang nạp lại dữ liệu vào bộ nhớ Cache...")

        # Clear SQLite DB so it is forced to read from the newly extracted JSON files
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                conn.execute("DELETE FROM kv_store")
                conn.commit()
        except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
            logger.error(f"Lỗi khi xóa DB cũ: {e}")

        load_data()
        await save_data(force=True) # Force full save to SQLite to sync new state

        await msg.edit_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>PHỤC HỒI DỮ LIỆU THÀNH CÔNG!</b>\n\nHệ thống đã được cập nhật với data từ bản backup.", parse_mode=ParseMode.HTML)
        logger.info(f"Admin restored data from backup: {document.file_name}")

    except (sqlite3.Error, aiosqlite.Error, ValueError) as e:
        logger.error(f"Lỗi phục hồi dữ liệu: {e}", exc_info=True)
        await msg.edit_text(f"❌ <b>Lỗi khi phục hồi dữ liệu:</b>\n<code>{e}</code>", parse_mode=ParseMode.HTML)

    finally:
        # Cleanup temp file if fails
        if 'temp_zip_path' in locals() and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except OSError as e:
                logger.debug(f"Cannot cleanup temp backup zip '{temp_zip_path}': {e}")

async def nhapdata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin: Phục hồi dữ liệu từ file backup ZIP
    Cú pháp:
    1) Reply vào file ZIP do bot gửi trước đó và gõ /nhapdata
    2) Hoặc gửi trực tiếp file .zip kèm caption /nhapdata
    """
    if update.effective_user.id != ADMIN_USER_ID:
        return

    source_document = None
    if update.message and getattr(update.message, "document", None):
        source_document = update.message.document
    elif (
        update.message
        and getattr(update.message, "reply_to_message", None)
        and getattr(update.message.reply_to_message, "document", None)
    ):
        source_document = update.message.reply_to_message.document

    if not source_document:
        await update.message.reply_text(
            f'{E_ERROR} <b>Không tìm thấy file ZIP.</b>\n\n'
            "Cách dùng:\n"
            "• Reply vào file ZIP backup rồi gõ <code>/nhapdata</code>\n"
            "• Hoặc gửi file <code>.zip</code> kèm caption <code>/nhapdata</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    document = source_document
    if not document.file_name or not document.file_name.lower().endswith('.zip'):
        await update.message.reply_text(
            f'{E_ERROR} <b>File không hợp lệ.</b> Phải là file <code>.zip</code>.',
            parse_mode=ParseMode.HTML,
        )
        return

    msg = await update.message.reply_text(
        "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang tải file backup xuống...",
        parse_mode=ParseMode.HTML,
    )
    safety_backup_path = None
    import json
    import zipfile

    try:
        file = await context.bot.get_file(document.file_id)
        temp_zip_path = os.path.join(
            os.path.dirname(os.path.abspath(DB_PATH)) or os.getcwd(),
            f"temp_restore_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip",
        )
        await file.download_to_drive(temp_zip_path)

        await msg.edit_text(
            "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang tạo backup an toàn trước khi phục hồi...",
            parse_mode=ParseMode.HTML,
        )
        await save_data(force=True)

        async with file_lock:
            safety_backup_path = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: create_backup_zip("backup_before_restore"),
            )
            if not safety_backup_path:
                raise ValueError("Không thể tạo bản backup an toàn trước khi nhập data.")

            await msg.edit_text(
                "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang kiểm tra file backup và phục hồi vào SQLite...",
                parse_mode=ParseMode.HTML,
            )
            restore_report = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: restore_backup_zip_to_db(temp_zip_path),
            )

        await msg.edit_text(
            "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang nạp lại dữ liệu vào bộ nhớ Cache...",
            parse_mode=ParseMode.HTML,
        )
        load_data()
        await save_data(force=True)

        restored_count = len(restore_report.get("restored_files", []))
        reset_count = len(restore_report.get("reset_files", []))
        success_lines = [
            "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>PHỤC HỒI DỮ LIỆU THÀNH CÔNG!</b>",
            "",
            f"Hệ thống đã nhận {restored_count} tệp dữ liệu từ backup.",
        ]
        if reset_count:
            success_lines.append(f"Đã xóa data cũ và reset {reset_count} bảng không có trong file backup.")
        if safety_backup_path:
            success_lines.append(f"Backup an toàn: <code>{html.escape(os.path.basename(safety_backup_path))}</code>")

        await msg.edit_text("\n".join(success_lines), parse_mode=ParseMode.HTML)
        logger.info(f"Admin restored data from backup: {document.file_name}")

    except (sqlite3.Error, aiosqlite.Error, ValueError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as e:
        logger.error(f"Lỗi phục hồi dữ liệu: {e}", exc_info=True)
        await msg.edit_text(
            f"❌ <b>Lỗi khi phục hồi dữ liệu:</b>\n<code>{html.escape(str(e))}</code>",
            parse_mode=ParseMode.HTML,
        )

    finally:
        if 'temp_zip_path' in locals() and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except OSError as e:
                logger.debug(f"Cannot cleanup temp backup zip '{temp_zip_path}': {e}")


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    """
    NEW: Manual Backup Trigger
    Cú pháp: /backup
    """

    msg = await update.message.reply_text("<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang khởi tạo tiến trình sao lưu...")

    await save_data(force=True)
    async with file_lock:
        zip_path = await asyncio.get_running_loop().run_in_executor(None, create_backup_zip)

    if zip_path and os.path.exists(zip_path):
        try:
            caption = (
                f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>MANUAL BACKUP SUCCESS</b>\n\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Thời gian:</b> {datetime.now().strftime('%H:%M %d/%m/%Y')}\n"
                f"<tg-emoji emoji-id=\"5854908544712707500\">📂</tg-emoji> <b>File:</b> <code>{os.path.basename(zip_path)}</code>\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Trigger bởi:</b> Admin"
            )
            with open(zip_path, 'rb') as backup_file:
                await update.message.reply_document(
                    document=backup_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            await msg.delete()

            try:
                os.remove(zip_path)
            except OSError as e:
                logger.debug(f"Cannot remove backup zip '{zip_path}': {e}")

        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            await msg.edit_text(f"❌ Lỗi gửi file: {e}")
    else:
        await msg.edit_text("❌ Lỗi: Không thể tạo file backup.")


async def _legacy_backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    """
    NEW: Manual Backup Trigger
    Cú pháp: /backup
    """

    msg = await update.message.reply_text("<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang khởi tạo tiến trình sao lưu...")

    # Flush data then create ZIP dưới file lock để tránh race với save_data trên Windows
    await save_data(force=True)
    async with file_lock:
        zip_path = await asyncio.get_running_loop().run_in_executor(None, create_backup_zip)

    if zip_path and os.path.exists(zip_path):
        try:
            caption = (
                f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>MANUAL BACKUP SUCCESS</b>\n\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Thời gian:</b> {datetime.now().strftime('%H:%M %d/%m/%Y')}\n"
                f"<tg-emoji emoji-id=\"5854908544712707500\">📂</tg-emoji> <b>File:</b> <code>{zip_path}</code>\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Trigger bởi:</b> Admin"
            )
            with open(zip_path, 'rb') as backup_file:
                await update.message.reply_document(
                    document=backup_file,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            await msg.delete()

            # Cleanup
            try:
                os.remove(zip_path)
            except OSError as e:
                logger.debug(f"Cannot remove backup zip '{zip_path}': {e}")

        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            await msg.edit_text(f"❌ Lỗi gửi file: {e}")
    else:
        await msg.edit_text("❌ Lỗi: Không thể tạo file backup.")

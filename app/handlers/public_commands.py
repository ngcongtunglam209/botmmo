# ==============================================================================
#  CÁC LỆNH
# ==============================================================================

USER_HISTORY_PAGE_SIZE = 10


def _coerce_user_history_page(page):
    try:
        return max(0, int(page or 0))
    except (TypeError, ValueError):
        return 0


def _truncate_history_button_text(text: str, limit: int = 56):
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _get_user_history_orders(user_id: int):
    normal_orders = list(user_order_index.get(str(user_id), []))
    api_orders = _api_get_orders_for_user(user_id)

    merged_orders = {}
    for order in normal_orders + api_orders:
        order_code = str(order.get('order_code') or "")
        if order_code:
            merged_orders[order_code] = order

    return sorted(
        merged_orders.values(),
        key=lambda order: float(order.get('timestamp', 0) or 0),
        reverse=True,
    )


def _get_user_history_page(sorted_orders, page=0):
    total_orders = len(sorted_orders)
    if total_orders <= 0:
        return [], 0, 1, 0, 0

    total_pages = max(1, (total_orders + USER_HISTORY_PAGE_SIZE - 1) // USER_HISTORY_PAGE_SIZE)
    safe_page = min(_coerce_user_history_page(page), total_pages - 1)
    start_index = safe_page * USER_HISTORY_PAGE_SIZE
    end_index = min(start_index + USER_HISTORY_PAGE_SIZE, total_orders)

    return sorted_orders[start_index:end_index], safe_page, total_pages, start_index + 1, end_index


def _build_user_history_view(user_id: int, page: int = 0):
    sorted_orders = _get_user_history_orders(user_id)
    if not sorted_orders:
        return None, None, 0, 1

    visible_orders, safe_page, total_pages, display_start, display_end = _get_user_history_page(sorted_orders, page)
    keyboard = []
    for order in visible_orders:
        code = order.get('order_code', 'N/A')
        ts = order.get('timestamp', 0)
        try:
            date = datetime.fromtimestamp(float(ts or 0)).strftime('%d/%m') if ts else "N/A"
        except (OSError, OverflowError, TypeError, ValueError):
            date = "N/A"
        item_name = get_order_item_name(order)
        status_info = status_text(order.get('status'))
        icon_id = "6269163801178804220" if is_completed_order(order) else "5447364299200678034"
        api_label = " | API" if _api_is_order_record(order) else ""
        btn_text = _truncate_history_button_text(f"{date} | [{code}]{api_label} | {item_name}")
        keyboard.append([_btn(btn_text, icon_id=icon_id, callback_data=f"view_order_history_{code}:{safe_page}")])

    if total_pages > 1:
        nav_row = []
        if safe_page > 0:
            nav_row.append(_btn(lt(user_id, "Đơn mới hơn", "Newer Orders", "较新订单"), callback_data=f"lichsu_page:{safe_page - 1}"))
        if safe_page < total_pages - 1:
            nav_row.append(_btn(lt(user_id, "Xem thêm đơn cũ hơn", "Older Orders", "较早订单"), callback_data=f"lichsu_page:{safe_page + 1}"))
        if nav_row:
            keyboard.append(nav_row)
    keyboard.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="back_to_main")])

    msg = lt(
        user_id,
        '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> LỊCH SỬ ĐƠN HÀNG CỦA BẠN</b>\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <i>Bấm vào đơn hàng để xem chi tiết:</i>\n<i>Hiển thị {start}-{end}/{total}</i>',
        '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> YOUR ORDER HISTORY</b>\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <i>Select an order to view details:</i>\n<i>Showing {start}-{end}/{total}</i>',
        '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> 您的订单历史</b>\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <i>点击订单查看详情：</i>\n<i>显示 {start}-{end}/{total}</i>',
        start=display_start, end=display_end, total=len(sorted_orders),
    )
    if total_pages > 1:
        msg += lt(user_id, "\n<i>Trang {page}/{pages}</i>", "\n<i>Page {page}/{pages}</i>", "\n<i>第 {page}/{pages} 页</i>", page=safe_page + 1, pages=total_pages)
    if any(_api_is_order_record(order) for order in sorted_orders):
        msg += lt(user_id, '\n\n<tg-emoji emoji-id="5436359785534466562">🔌</tg-emoji> <i>Danh sách này đã bao gồm cả đơn API Partner.</i>', '\n\n<tg-emoji emoji-id="5436359785534466562">🔌</tg-emoji> <i>This list includes API Partner orders.</i>', '\n\n<tg-emoji emoji-id="5436359785534466562">🔌</tg-emoji> <i>此列表包含 API 合作伙伴订单。</i>')
    return msg, InlineKeyboardMarkup(keyboard), safe_page, total_pages


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy command - giữ lại cho tương thích"""
    if await check_if_banned(update): return

    user_id = update.effective_user.id
    if MAINTENANCE_MODE and user_id != ADMIN_USER_ID:
        await update.message.reply_text(t("maintenance", user_id=user_id), parse_mode=ParseMode.HTML)
        return

    if not context.args:
        await update.message.reply_html(lt(user_id, '💡 <b>Bạn có thể hỏi trực tiếp mà không cần /ask!</b>\n\nVí dụ:\n• iCloud 2TB có gì hay?\n• Cách kích hoạt Netflix?\n• Sản phẩm nào phù hợp với tôi?\n\nHoặc: <code>/ask [câu hỏi]</code>', '💡 <b>You can ask directly without /ask!</b>\n\nExamples:\n• What are the benefits of iCloud 2TB?\n• How do I activate Netflix?\n• Which product suits me?\n\nOr: <code>/ask [question]</code>', '💡 <b>无需 /ask 即可直接提问！</b>\n\n示例：\n• iCloud 2TB 有什么优势？\n• 如何激活 Netflix？\n• 哪款商品适合我？\n\n或者：<code>/ask [问题]</code>'))
        return
    question = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    user_info = db_get_user(user_id)
    user_orders = db_get_user_orders(user_id, limit=10)
    user_context = {'orders_count': len(user_orders), 'balance': user_info.get('balance', 0) if user_info else 0}
    ai_answer = await ask_ai(question, user_context, user_id=user_id)
    await update.message.reply_html(lt(user_id, "🤖 <b>Trợ lý AI:</b>\n\n{answer}", "🤖 <b>AI Assistant:</b>\n\n{answer}", "🤖 <b>AI 助手：</b>\n\n{answer}", answer=ai_answer))

async def dkyapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cho phép user đăng ký API Key - Tự động cấp ngay không cần Admin duyệt"""
    if await check_if_banned(update):
        return

    user = update.effective_user
    user_id = user.id
    if MAINTENANCE_MODE and user_id != ADMIN_USER_ID:
        await safe_reply_html(update.message, t("maintenance", user_id=user_id))
        return
    logger.info(f"[API REG] Received /dkyapi from user {user_id}")
    existing_key, _existing_data = get_partner_api_entry_by_user(user_id)
    if existing_key:
        await safe_reply_html(update.message, lt(user_id, "✅ Bạn đã có API Key!\nKey: <code>{key}</code>", "✅ You already have an API key!\nKey: <code>{key}</code>", "✅ 您已有 API 密钥！\n密钥：<code>{key}</code>", key=existing_key))
        return

    # === AUTO-APPROVE: Tạo API Key ngay lập tức ===
    new_key = f"sk_live_{secrets.token_hex(16)}"
    partner_name = user.username or user.full_name or f"User_{user_id}"

    api_keys[new_key] = {"name": partner_name, "balance": 0, "user_id": user_id}
    await save_data(force=True)

    # Xóa khỏi pending nếu có (legacy)
    pending_api_registrations.discard(user_id)

    logger.info(f"[API REG] Auto-approved API key for user {user_id} ({partner_name})")

    await safe_reply_html(
        update.message,
        lt(
            user_id,
            "🎉 <b>ĐĂNG KÝ API THÀNH CÔNG!</b>\n\n🔐 <b>API Key:</b> <code>{key}</code>\n💰 <b>Số dư:</b> 0 VNĐ\n\n<b>Bắt đầu nhanh:</b>\n1. Nạp tiền: <code>/napapi 500000</code>\n2. Danh mục: <code>GET /api/v2/catalog</code>\n3. Tạo đơn: <code>POST /api/v2/orders</code>\n4. Tra cứu: <code>GET /api/v2/orders/{{order_code}}</code>\n\nVào <code>/start</code> để mở <b>API Partner</b>.\n\n<i>Tài khoản đã mua nằm trong <code>data.items</code>.</i>",
            "🎉 <b>API REGISTRATION SUCCESSFUL!</b>\n\n🔐 <b>API Key:</b> <code>{key}</code>\n💰 <b>Balance:</b> 0 VND\n\n<b>Quick start:</b>\n1. Top up: <code>/napapi 500000</code>\n2. Catalog: <code>GET /api/v2/catalog</code>\n3. Create order: <code>POST /api/v2/orders</code>\n4. Check order: <code>GET /api/v2/orders/{{order_code}}</code>\n\nOpen <code>/start</code> and select <b>API Partner</b>.\n\n<i>Purchased accounts are returned in <code>data.items</code>.</i>",
            "🎉 <b>API 注册成功！</b>\n\n🔐 <b>API 密钥：</b> <code>{key}</code>\n💰 <b>余额：</b> 0 VND\n\n<b>快速开始：</b>\n1. 充值：<code>/napapi 500000</code>\n2. 商品目录：<code>GET /api/v2/catalog</code>\n3. 创建订单：<code>POST /api/v2/orders</code>\n4. 查询订单：<code>GET /api/v2/orders/{{order_code}}</code>\n\n打开 <code>/start</code> 并选择 <b>API Partner</b>。\n\n<i>购买的账户位于 <code>data.items</code>。</i>",
            key=new_key,
        )
    )


async def lichsu_command(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False, page: int = 0) -> None:
    if await check_if_banned(update): return

    user_id = update.effective_user.id
    if MAINTENANCE_MODE and user_id != ADMIN_USER_ID:
        if is_callback:
            await safe_answer(update.callback_query, lt(user_id, "Hệ thống đang bảo trì!", "System is under maintenance!", "系统维护中！"), show_alert=True)
        else:
            await update.message.reply_text(t("maintenance", user_id=user_id), parse_mode=ParseMode.HTML)
        return

    chat_id = update.effective_chat.id
    msg, keyboard, _, _ = _build_user_history_view(user_id, page)

    if not msg or not keyboard:
        empty_msg = lt(user_id, "Bạn chưa có đơn hàng nào.", "You have no orders yet.", "您还没有订单。")
        if is_callback:
            await context.bot.send_message(chat_id, empty_msg, reply_markup=create_back_button_menu(text=lt(user_id, "Quay lại", "Back", "返回")))
        else:
            await update.message.reply_text(empty_msg)
        return

    if is_callback:
        try:
            await safe_edit_message(update.callback_query, text=msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        except (TelegramError, ValueError, KeyError, AttributeError):
            await context.bot.send_message(chat_id, msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_html(msg, reply_markup=keyboard)


async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return
    user_id = update.effective_user.id
    history = transaction_history.get(str(user_id), [])
    msg = lt(user_id, '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> LỊCH SỬ BIẾN ĐỘNG SỐ DƯ</b>\n\n', '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> BALANCE TRANSACTION HISTORY</b>\n\n', '<b><tg-emoji emoji-id="5350481781306958339">📜</tg-emoji> 余额变动历史</b>\n\n')
    if not history:
        msg += lt(user_id, "<i>Bạn chưa có giao dịch nào.</i>", "<i>You have no transactions yet.</i>", "<i>您还没有交易记录。</i>")
    else:
        for tx in list(reversed(history))[:15]:
            amount = tx.get('amount', 0)
            reason = tx.get('reason', 'Unknown')
            time_str = datetime.fromtimestamp(tx.get('timestamp', 0)).strftime('%H:%M %d/%m')
            icon = '<tg-emoji emoji-id="5397916757333654639">➕</tg-emoji>' if amount >= 0 else '<tg-emoji emoji-id="5406745771280187626">➖</tg-emoji>'
            sign = "+" if amount >= 0 else ""
            msg += f"{icon} <b>{sign}{amount:,} đ</b> | {time_str}\n   <i>{reason}</i>\n\n"
    await update.message.reply_html(msg)

async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Bạn không có quyền truy cập lệnh này.")
        return
    text = (
        "<tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji> <b>BẢNG ĐIỀU KHIỂN ADMIN</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Chọn mục cần quản lý:"
    )
    await update.message.reply_html(text, reply_markup=build_admin_main_menu())

async def delproduct_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Cú pháp: /delproduct <product_id>"); return
    prod_id = context.args[0]
    if prod_id in products:
        del products[prod_id]
        await save_data(force=True)
        await update.message.reply_text(f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> Đã xóa sản phẩm ID: {prod_id}")
    else:
        await update.message.reply_text("❌ Không tìm thấy sản phẩm này.")


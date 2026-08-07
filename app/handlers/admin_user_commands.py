ADMIN_USER_INFO_ORDER_PAGE_SIZE = 10


def _safe_admin_order_timestamp(order):
    try:
        return float(order.get('timestamp', 0) or 0)
    except (ValueError, TypeError, AttributeError):
        return 0.0


def _get_admin_user_history_orders(user_id: int):
    merged_orders = {}

    for order in db_get_user_orders(user_id, limit=None):
        order_code = str(order.get('order_code') or "")
        if order_code:
            merged_orders[order_code] = order

    for order in _api_get_orders_for_user(user_id):
        order_code = str(order.get('order_code') or "")
        if order_code:
            merged_orders[order_code] = order

    return sorted(
        merged_orders.values(),
        key=_safe_admin_order_timestamp,
        reverse=True,
    )


def _coerce_admin_page(page):
    try:
        return max(0, int(page or 0))
    except (TypeError, ValueError):
        return 0


def _get_admin_user_orders_page(user_orders, page=0):
    total_orders = len(user_orders)
    if total_orders <= 0:
        return [], 0, 1, 0, 0

    total_pages = max(1, (total_orders + ADMIN_USER_INFO_ORDER_PAGE_SIZE - 1) // ADMIN_USER_INFO_ORDER_PAGE_SIZE)
    safe_page = min(_coerce_admin_page(page), total_pages - 1)

    start_index = safe_page * ADMIN_USER_INFO_ORDER_PAGE_SIZE
    end_index = min(start_index + ADMIN_USER_INFO_ORDER_PAGE_SIZE, total_orders)
    visible_orders = user_orders[start_index:end_index]

    return visible_orders, safe_page, total_pages, start_index + 1, end_index


def _format_admin_first_seen(first_seen_value):
    if first_seen_value in (None, ""):
        return 'N/A'

    parsed_dt = None
    raw_value = first_seen_value
    if isinstance(first_seen_value, (int, float)):
        try:
            parsed_dt = datetime.fromtimestamp(float(first_seen_value))
        except (OSError, OverflowError, TypeError, ValueError):
            parsed_dt = None
    else:
        raw_value = str(first_seen_value).strip()
        if not raw_value:
            return 'N/A'

        normalized_iso = raw_value.replace("Z", "+00:00")
        try:
            parsed_dt = datetime.fromisoformat(normalized_iso)
        except ValueError:
            try:
                parsed_dt = datetime.fromtimestamp(float(raw_value))
            except (OSError, OverflowError, TypeError, ValueError):
                for fmt in ('%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d'):
                    try:
                        parsed_dt = datetime.strptime(raw_value, fmt)
                        break
                    except ValueError:
                        continue

    if parsed_dt is None:
        return html.escape(str(raw_value))

    return html.escape(parsed_dt.strftime('%d/%m/%Y %H:%M'))


def _build_admin_userinfo_keyboard(target_id: int, current_page: int, total_orders: int):
    total_pages = max(1, (total_orders + ADMIN_USER_INFO_ORDER_PAGE_SIZE - 1) // ADMIN_USER_INFO_ORDER_PAGE_SIZE)
    is_banned = target_id in banned_users

    keyboard = [
        [
            _btn(
                "Cộng tiền",
                icon_id="5397916757333654639",
                callback_data=f"adm_quick:addmoney:{target_id}",
                style="success",
            ),
            _btn(
                "Trừ tiền",
                icon_id="5406745771280187626",
                callback_data=f"adm_quick:submoney:{target_id}",
                style="danger",
            ),
        ],
        [
            _btn(
                "Cấm" if not is_banned else "Mở cấm",
                icon_id="5424857974784925603" if not is_banned else "6269163801178804220",
                callback_data=f"adm_quick:toggleban:{target_id}",
                style="danger" if not is_banned else "success",
            ),
            _btn(
                "Chat",
                icon_id="5443038326535759644",
                callback_data=f"adm_quick:chat:{target_id}",
                style="primary",
            ),
        ],
    ]

    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(
                _btn(
                    "Đơn mới hơn",
                    callback_data=f"adm_uo:{target_id}:{current_page - 1}",
                    style="primary",
                )
            )
        if current_page < total_pages - 1:
            nav_row.append(
                _btn(
                    "Xem thêm đơn cũ hơn",
                    callback_data=f"adm_uo:{target_id}:{current_page + 1}",
                    style="primary",
                )
            )
        if nav_row:
            keyboard.append(nav_row)

    return InlineKeyboardMarkup(keyboard)


def _legacy_build_admin_userinfo_panel(target_id: int, order_page: int = 0):
    target_id_str = str(target_id)
    user_info = user_data_db.get(target_id_str)
    if not user_info:
        return None, None, 0, 0

    first_name = html.escape(user_info.get('first_name', 'N/A'))
    username = user_info.get('username', None)
    username_display = html.escape(f"@{username}" if username else "Không có")
    user_link = f'<a href="tg://user?id={target_id}">{first_name}</a>'
    balance = user_info.get('balance', 0)
    first_seen = _format_admin_first_seen(user_info.get('first_seen'))
    ban_status = "<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Bị cấm" if target_id in banned_users else "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoạt động"

    rank_info = get_user_rank(target_id)
    rank_name = html.escape(str(rank_info['rank']['name']))
    base_rank = rank_info.get('base_rank') or rank_info['rank']
    next_rank = rank_info.get('next_rank')
    remaining = rank_info.get('remaining_to_next', 0)
    maintenance_status = rank_info.get('maintenance_status') or {}

    stats = calculate_user_stats(target_id)
    badges = calculate_badges(target_id)

    ref_data = referral_data.get(target_id_str, {})
    ref_count = len(ref_data.get('referred_users', []))
    ref_commission = ref_data.get('total_commission', 0)

    user_orders = _get_admin_user_history_orders(target_id)
    completed_orders = [o for o in user_orders if is_completed_order(o)]

    visible_orders, safe_page, total_pages, display_start, display_end = _get_admin_user_orders_page(user_orders, order_page)

    message = (
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>THÔNG TIN CHI TIẾT USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <b>ID:</b> <code>{target_id}</code>\n"
        f"<tg-emoji emoji-id=\"6260059243605398502\">📛</tg-emoji> <b>Tên:</b> {first_name}\n"
        f"<tg-emoji emoji-id=\"6260059243605398502\">🏷</tg-emoji> <b>Username:</b> {username_display}\n"
        f"<tg-emoji emoji-id=\"5231489647946768652\">🔗</tg-emoji> <b>User link:</b> {user_link}\n"
        f"<tg-emoji emoji-id=\"5413879192267805083\">📅</tg-emoji> <b>Tham gia:</b> {first_seen}\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Trạng thái:</b> {ban_status}\n\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>TÀI CHÍNH</b>\n"
        f"┣ Số dư: <b>{balance:,} VNĐ</b>\n"
        f"┣ Tổng chi tiêu: <b>{stats['total_spent']:,} VNĐ</b>\n"
        f"┗ Tiết kiệm coupon: {stats['coupon_savings']:,} VNĐ\n\n"
        f"⭐️ <b>HẠNG VIP:</b> {rank_name}"
    )

    message += "\n"
    if rank_info.get('demoted_by_maintenance'):
        message += (
            f"┣ Duy trì hạng tháng {html.escape(str(maintenance_status.get('period_label', 'trước')))}: "
            f"<b>{maintenance_status.get('monthly_spend', 0):,} VNĐ</b> / {VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ\n"
            f"┗ Đang bị tụt 1 bậc, cần thêm <b>{remaining:,} VNĐ</b> để lấy lại "
            f"{html.escape(str(base_rank['name']))} vào tháng sau\n"
        )
    elif next_rank:
        message += f"┗ Cần thêm <b>{remaining:,} VNĐ</b> → {html.escape(str(next_rank['name']))}\n"
    message += "\n"

    if badges:
        message += f"⭐️ <b>BADGES:</b> {' '.join(badges)}\n\n"

    message += (
        f"<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>ĐƠN HÀNG</b>\n"
        f"┣ Tổng đơn: {len(user_orders)}\n"
        f"┣ Hoàn thành: {len(completed_orders)}\n"
        f"┗ Đơn thành công: {stats['order_count']}\n\n"
    )

    if ref_count > 0 or ref_commission > 0:
        message += (
            f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>GIỚI THIỆU</b>\n"
            f"┣ Đã giới thiệu: {ref_count} người\n"
            f"┗ Hoa hồng: {ref_commission:,} VNĐ\n\n"
        )

    if user_orders:
        message += (
            f"<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> "
            f"LỊCH SỬ ĐƠN HÀNG ({display_start}-{display_end}/{len(user_orders)})</b>\n"
        )
        if total_pages > 1:
            message += f"<i>Trang {safe_page + 1}/{total_pages}</i>\n"
        for order in visible_orders:
            try:
                order_date = datetime.fromtimestamp(order['timestamp']).strftime('%d/%m %H:%M')
            except (ValueError, TypeError):
                order_date = 'N/A'
            order_code = order.get('order_code', 'N/A')
            status = status_text(order.get('status', ''))
            amount = order.get('amount', 0)
            message += f"• <code>{order_code}</code> | {order_date} | {amount:,}đ | {status}\n"
    else:
        message += (
            f"<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> LỊCH SỬ ĐƠN HÀNG (0/0)</b>\n"
            f"<i>Chưa có đơn hàng nào.</i>"
        )

    message = upgrade_text_to_premium_emoji(message)
    keyboard = _build_admin_userinfo_keyboard(target_id, safe_page, len(user_orders))
    return message, keyboard, safe_page, total_pages


def _format_admin_rank_name(rank_name):
    import re as _re

    clean_name = _re.sub(r'<[^>]+>', '', str(rank_name or '')).strip()
    lower_name = clean_name.lower()

    if "cao thủ" in lower_name or "cao thu" in lower_name or "👑" in clean_name or "🏆" in clean_name:
        return f"{E_MENU} Cao Thủ"
    if "kim cương" in lower_name or "kim cuong" in lower_name or "💎" in clean_name:
        return '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương'
    if "vàng" in lower_name or "vang" in lower_name or "🥇" in clean_name:
        return f"{E_STAR} Vàng"
    if "bạc" in lower_name or "bac" in lower_name or "🥈" in clean_name:
        return f"{E_STAR} Bạc"
    return f"{E_STAR} Đồng"


def _build_admin_userinfo_panel(target_id: int, order_page: int = 0):
    target_id_str = str(target_id)
    user_info = user_data_db.get(target_id_str)
    if not user_info:
        return None, None, 0, 0

    first_name = html.escape(user_info.get('first_name', 'N/A'))
    username = user_info.get('username', None)
    username_display = html.escape(f"@{username}" if username else "Không có")
    user_link = f'<a href="tg://user?id={target_id}">{first_name}</a>'
    balance = user_info.get('balance', 0)
    first_seen = _format_admin_first_seen(user_info.get('first_seen'))
    ban_status = f"{E_LIMIT} Bị cấm" if target_id in banned_users else f"{E_SUCCESS} Hoạt động"
    partner_api_key, _ = get_partner_api_entry_by_user(target_id)
    api_key_display = f"<code>{html.escape(partner_api_key)}</code>" if partner_api_key else "<i>Chưa có</i>"

    rank_info = get_user_rank(target_id)
    rank_name = _format_admin_rank_name(rank_info['rank']['name'])
    base_rank = rank_info.get('base_rank') or rank_info['rank']
    next_rank = rank_info.get('next_rank')
    remaining = rank_info.get('remaining_to_next', 0)
    maintenance_status = rank_info.get('maintenance_status') or {}

    stats = calculate_user_stats(target_id)
    badges = calculate_badges(target_id)

    ref_data = referral_data.get(target_id_str, {})
    ref_count = len(ref_data.get('referred_users', []))
    ref_commission = ref_data.get('total_commission', 0)

    user_orders = _get_admin_user_history_orders(target_id)
    completed_orders = [o for o in user_orders if is_completed_order(o)]

    visible_orders, safe_page, total_pages, display_start, display_end = _get_admin_user_orders_page(user_orders, order_page)

    message = (
        f"{E_USER} <b>THÔNG TIN CHI TIẾT USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{E_ID} <b>ID:</b> <code>{target_id}</code>\n"
        f"{E_TAG} <b>Tên:</b> {first_name}\n"
        f"{E_TAG} <b>Username:</b> {username_display}\n"
        f"{E_GLOBE} <b>User link:</b> {user_link}\n"
        f"{E_CALENDAR} <b>Tham gia:</b> {first_seen}\n"
        f"{E_STAT} <b>Trạng thái:</b> {ban_status}\n"
        f"{E_SHIELD} <b>API key:</b> {api_key_display}\n\n"
        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>TÀI CHÍNH</b>\n'
        f"{E_TAG} Số dư: <b>{balance:,} VNĐ</b>\n"
        f"{E_TAG} Tổng chi tiêu: <b>{stats['total_spent']:,} VNĐ</b>\n"
        f"{E_TAG} Tiết kiệm coupon: {stats['coupon_savings']:,} VNĐ\n\n"
        f"{E_STAR} <b>HẠNG VIP:</b> {rank_name}"
    )

    message += "\n"
    if rank_info.get('demoted_by_maintenance'):
        message += (
            f"{E_TAG} Duy trì hạng tháng {html.escape(str(maintenance_status.get('period_label', 'trước')))}: "
            f"<b>{maintenance_status.get('monthly_spend', 0):,} VNĐ</b> / {VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ\n"
            f"{E_TAG} Đang bị tụt 1 bậc, cần thêm <b>{remaining:,} VNĐ</b> để lấy lại "
            f"{_format_admin_rank_name(base_rank['name'])} vào tháng sau\n"
        )
    elif next_rank:
        message += f"{E_TAG} Cần thêm <b>{remaining:,} VNĐ</b> → {_format_admin_rank_name(next_rank['name'])}\n"
    message += "\n"

    if badges:
        message += f"{E_STAR} <b>BADGES:</b> {' '.join(badges)}\n\n"

    message += (
        f"{E_TAG} <b>ĐƠN HÀNG</b>\n"
        f"{E_STAT} Tổng đơn: {len(user_orders)}\n"
        f"{E_SUCCESS} Hoàn thành: {len(completed_orders)}\n"
        f"{E_TAG} Đơn thành công: {stats['order_count']}\n\n"
    )

    if ref_count > 0 or ref_commission > 0:
        message += (
            '<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>GIỚI THIỆU</b>\n'
            f"{E_STAT} Đã giới thiệu: {ref_count} người\n"
            f"{E_TAG} Hoa hồng: {ref_commission:,} VNĐ\n\n"
        )

    if user_orders:
        message += (
            f'<b><tg-emoji emoji-id="5373251851074415873">📋</tg-emoji> '
            f"LỊCH SỬ ĐƠN HÀNG ({display_start}-{display_end}/{len(user_orders)})</b>\n"
        )
        if total_pages > 1:
            message += f"<i>Trang {safe_page + 1}/{total_pages}</i>\n"
        for order in visible_orders:
            try:
                order_date = datetime.fromtimestamp(order['timestamp']).strftime('%d/%m %H:%M')
            except (ValueError, TypeError):
                order_date = 'N/A'
            order_code = order.get('order_code', 'N/A')
            status = upgrade_text_to_premium_emoji(status_text(order.get('status', '')))
            amount = order.get('amount', 0)
            message += f"{E_TAG} <code>{order_code}</code> | {order_date} | {amount:,}đ | {status}\n"
    else:
        message += (
            '<b><tg-emoji emoji-id="5373251851074415873">📋</tg-emoji> LỊCH SỬ ĐƠN HÀNG (0/0)</b>\n'
            f"<i>Chưa có đơn hàng nào.</i>"
        )

    message = upgrade_text_to_premium_emoji(message)
    keyboard = _build_admin_userinfo_keyboard(target_id, safe_page, len(user_orders))
    return message, keyboard, safe_page, total_pages


async def handle_admin_user_orders_pagination(query, context: ContextTypes.DEFAULT_TYPE):
    parts = query.data.split(":")
    if len(parts) != 3:
        await safe_answer(query, "Dữ liệu không hợp lệ", show_alert=True)
        return

    try:
        target_id = int(parts[1])
        requested_page = int(parts[2])
    except ValueError:
        await safe_answer(query, "Trang hoặc ID không hợp lệ", show_alert=True)
        return

    message, keyboard, safe_page, total_pages = _build_admin_userinfo_panel(target_id, requested_page)
    if not message or not keyboard:
        await safe_answer(query, "Không tìm thấy người dùng", show_alert=True)
        return

    await safe_answer(query)
    try:
        await safe_edit_message(
            query,
            text=message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            alert_text=f"Trang {safe_page + 1}/{total_pages}",
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as pagination_error:
        logger.warning(f"Admin user orders pagination fallback for target={target_id}, page={safe_page}: {pagination_error}")
        target_message = getattr(query, "message", None)
        chat_id = getattr(target_message, "chat_id", None)
        if chat_id is None:
            raise
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


async def pending_withdrawals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_USER_ID: return
    """Admin command: List pending withdrawals"""
    
    pending = [(req_id, req) for req_id, req in withdrawal_requests.items() if req.get('status') == 'pending']
    
    if not pending:
        await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Không có yêu cầu rút tiền nào đang chờ.")
        return
        
    await update.message.reply_text(f"<tg-emoji emoji-id=\"5863724849851011383\">💸</tg-emoji> <b>DANH SÁCH YÊU CẦU RÚT TIỀN ({len(pending)})</b>", parse_mode=ParseMode.HTML)
    
    for req_id, req in pending:
        safe_full_name = html.escape(str(req.get('full_name', 'Unknown')))
        safe_username = html.escape(str(req.get('username', 'N/A')))
        safe_bank_info = html.escape(str(req.get('bank_info', 'N/A')))
        
        msg = (
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: {safe_full_name} (@{safe_username})\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số tiền: <b>{req.get('amount', 0):,} VNĐ</b>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> Bank: <code>{safe_bank_info}</code>\n"
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Lúc: {datetime.fromtimestamp(req.get('timestamp', 0)).strftime('%H:%M %d/%m')}"
        )
        keyboard = [
            [_btn("DUYỆT", icon_id="5021905410089550576", callback_data=f"approve_withdraw:{req_id}")],
            [_btn("TỪ CHỐI", icon_id="6114086705512321034", callback_data=f"reject_withdraw:{req_id}")]
        ]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def _utf16_len_for_bc(text: str) -> int:
    return len(str(text or "").encode("utf-16-le")) // 2


def _build_bc_notice_text_and_entities(source_message):
    from telegram import MessageEntity

    source_text = getattr(source_message, "text", None) or getattr(source_message, "caption", None) or ""
    source_entities = list(getattr(source_message, "entities", None) or getattr(source_message, "caption_entities", None) or [])
    prefix = "🤩🤩🤩🤩🤩🎉\n"
    custom_emoji_ids = [
        "6197082928418135282",
        "6197492475024644805",
        "6197392256257760619",
        "6199422543133153316",
        "6196970997275433101",
        "5193209274452425995",
    ]
    entities = []
    offset = 0
    for emoji_id in custom_emoji_ids:
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=offset,
                length=2,
                custom_emoji_id=emoji_id,
            )
        )
        offset += 2

    shift = _utf16_len_for_bc(prefix)
    for entity in source_entities:
        entities.append(
            MessageEntity(
                type=entity.type,
                offset=int(entity.offset or 0) + shift,
                length=int(entity.length or 0),
                url=getattr(entity, "url", None),
                user=getattr(entity, "user", None),
                language=getattr(entity, "language", None),
                custom_emoji_id=getattr(entity, "custom_emoji_id", None),
            )
        )

    return prefix + source_text, entities


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.reply_to_message:
        await update.message.reply_html("<b><tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Hướng dẫn:</b>\n1. Soạn sẵn tin nhắn bạn muốn gửi.\n2. Gửi tin nhắn đó vào đây.\n3. Trả lời (Reply) lại tin nhắn vừa gửi bằng lệnh <code>/broadcast</code>.")
        return
    
    message_to_broadcast = update.message.reply_to_message
    all_users_ids = list(user_data_db.keys())
    
    # Thông báo admin NGAY - bot không đơ!
    status_msg = await update.message.reply_text(
        f"<tg-emoji emoji-id=\"5303290914041505430\">🚀</tg-emoji> Bắt đầu gửi broadcast đến {len(all_users_ids)} người dùng...\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Bot vẫn hoạt động bình thường, broadcast chạy nền!"
    )
    
    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: CHẠY TRONG BACKGROUND TASK - KHÔNG BLOCK BOT!
    async def _broadcast_background(msg_obj):
        """Background task để broadcast - không block bot"""
        success, fail, errors = 0, 0, []
        blocked_user_ids = []
        total_users = len(all_users_ids)
        
        start_time = time.time()
        
        for idx, user_id in enumerate(all_users_ids, 1):
            try:
                if getattr(message_to_broadcast, "text", None):
                    notice_text, notice_entities = _build_bc_notice_text_and_entities(message_to_broadcast)
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=notice_text,
                        entities=notice_entities,
                        reply_markup=getattr(message_to_broadcast, "reply_markup", None),
                    )
                else:
                    await context.bot.copy_message(
                        chat_id=int(user_id),
                        from_chat_id=update.message.chat_id,
                        message_id=message_to_broadcast.message_id,
                        reply_markup=getattr(message_to_broadcast, "reply_markup", None),
                    )
                success += 1
                await asyncio.sleep(0.05)
            except (Forbidden, BadRequest) as e:
                fail += 1
                blocked_user_ids.append(user_id)
                if len(errors) < 5:
                    errors.append(f"ID {user_id}: {type(e).__name__} - {e}")
            except (ValueError, TypeError, KeyError, IndexError, TelegramError) as e:
                fail += 1
                if len(errors) < 5:
                    errors.append(f"ID {user_id}: {type(e).__name__} - {e}")
            
            if idx % 20 == 0 or idx == total_users:
                try:
                    progress = generate_progress_bar(idx, total_users)
                    await msg_obj.edit_text(
                        f"<tg-emoji emoji-id=\"5303290914041505430\">🚀</tg-emoji> <b>Đang gửi broadcast...</b>\n"
                        f"{progress}\n"
                        f"{E_SUCCESS} {success} | ❌ {fail} | <tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> {idx}/{total_users}\n"
                        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Bot vẫn hoạt động bình thường!",
                        parse_mode=ParseMode.HTML
                    )
                except (ValueError, TypeError, KeyError, IndexError, TelegramError) as e:
                    logger.debug(f"Cannot update broadcast progress at {idx}/{total_users}: {e}")
        
        cleaned_count = 0
        if blocked_user_ids:
            cleaned_count = await _cleanup_blocked_users(blocked_user_ids)
        
        duration = int(time.time() - start_time)
        summary = (
            f"{E_SUCCESS} <b>GỬI BROADCAST HOÀN TẤT!</b>\n\n"
            f"{generate_progress_bar(total_users, total_users)}\n"
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏱️</tg-emoji> <b>Thời gian:</b> {duration}s\n"
            f"{E_SUCCESS} <b>Thành công:</b> {success}\n"
            f"❌ <b>Thất bại:</b> {fail}"
        )
        if cleaned_count > 0:
            summary += f"\n\n<tg-emoji emoji-id=\"5462956611033117422\">🧹</tg-emoji> <b>Đã tự động xoá {cleaned_count} user block bot</b>"
        if errors:
            summary += "\n\n<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>Chi tiết 5 lỗi đầu tiên:</b>\n" + "\n".join([f"- <code>{error}</code>" for error in errors])
        
        try:
            await msg_obj.edit_text(summary, parse_mode=ParseMode.HTML)
        except (ValueError, TypeError, KeyError, IndexError, TelegramError) as e:
            logger.error(f"Cannot send broadcast report: {e}")
            try:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=summary, parse_mode=ParseMode.HTML)
            except (ValueError, TypeError, KeyError, IndexError, TelegramError) as fallback_error:
                logger.error(f"Cannot send broadcast fallback report: {fallback_error}")
    
    # Chạy broadcast trong background
    create_background_task(_broadcast_background(status_msg))

async def bcsp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_USER_ID:
        return

    if not context.args:
        sample_ids = list(products.keys())[:10]
        sample_text = "\n".join([f"• <code>{html.escape(str(pid))}</code>" for pid in sample_ids]) or "Chưa có sản phẩm"
        await update.message.reply_html(
            f"<b>{E_TAG} Cách dùng:</b> <code>/bcsp product_id</code>\n\n"
            f"<b>Ví dụ:</b> <code>/bcsp {html.escape(str(sample_ids[0]))}</code>\n\n" if sample_ids else
            f"<b>{E_TAG} Cách dùng:</b> <code>/bcsp product_id</code>\n\n"
            f"<b>ID sản phẩm hiện có:</b>\n{sample_text}"
        )
        return

    prod_id = context.args[0].strip()
    product = products.get(prod_id)
    if not product:
        await update.message.reply_html(f"{E_ERROR} Không tìm thấy sản phẩm: <code>{html.escape(prod_id)}</code>")
        return

    name = html.escape(str(product.get('name') or prod_id))
    price = int(product.get('price', 0) or 0)
    duration = html.escape(str(product.get('duration') or 'Không giới hạn'))
    warranty = html.escape(str(product.get('warranty') or 'Không'))
    description = html.escape(str(product.get('description') or ''))
    if len(description) > 700:
        description = description[:697] + '...'

    text = (
        f"<b>{E_TAG} SẢN PHẨM ĐANG MỞ BÁN</b>\n\n"
        f"<b>{name}</b>\n"
        f"{E_TAG} Giá: <b>{price:,} VNĐ</b>\n"
        f"{E_TAG} Thời hạn: <b>{duration}</b>\n"
        f"{E_SHIELD} Bảo hành: <b>{warranty}</b>\n\n"
        f"<blockquote>{description}</blockquote>\n"
        f"Bấm nút bên dưới để mua ngay."
    )
    keyboard = InlineKeyboardMarkup([
        [_btn("Mua ngay", icon_id="5402186569006210455", callback_data=f"sel_qty_{prod_id}", style="success")],
        [_btn("Xem sản phẩm", icon_id="5350673958874679310", callback_data=f"view_prod_{prod_id}")],
    ])

    all_users_ids = list(user_data_db.keys())
    status_msg = await update.message.reply_html(
        f"{E_LOADING} Bắt đầu gửi sản phẩm <b>{name}</b> đến {len(all_users_ids)} user..."
    )

    async def _bcsp_background(msg_obj):
        success, fail, errors = 0, 0, []
        blocked_user_ids = []
        total_users = len(all_users_ids)
        start_time = time.time()

        for idx, user_id in enumerate(all_users_ids, 1):
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
                success += 1
                await asyncio.sleep(0.05)
            except (Forbidden, BadRequest) as e:
                fail += 1
                blocked_user_ids.append(user_id)
                if len(errors) < 5:
                    errors.append(f"ID {user_id}: {type(e).__name__} - {e}")
            except (ValueError, TypeError, KeyError, IndexError, TelegramError) as e:
                fail += 1
                if len(errors) < 5:
                    errors.append(f"ID {user_id}: {type(e).__name__} - {e}")

            if idx % 20 == 0 or idx == total_users:
                try:
                    await msg_obj.edit_text(
                        f"{E_LOADING} <b>Đang gửi /bcsp...</b>\n"
                        f"{generate_progress_bar(idx, total_users)}\n"
                        f"{E_SUCCESS} {success} | ❌ {fail} | {E_USER} {idx}/{total_users}",
                        parse_mode=ParseMode.HTML,
                    )
                except (ValueError, TypeError, KeyError, IndexError, TelegramError):
                    pass

        cleaned_count = await _cleanup_blocked_users(blocked_user_ids) if blocked_user_ids else 0
        duration_seconds = int(time.time() - start_time)
        summary = (
            f"{E_SUCCESS} <b>GỬI SẢN PHẨM HOÀN TẤT!</b>\n\n"
            f"{generate_progress_bar(total_users, total_users)}\n"
            f"<b>Sản phẩm:</b> {name}\n"
            f"<b>Thành công:</b> {success}\n"
            f"<b>Thất bại:</b> {fail}\n"
            f"<b>Thời gian:</b> {duration_seconds}s"
        )
        if cleaned_count > 0:
            summary += f"\n\nĐã tự động xoá {cleaned_count} user block bot"
        if errors:
            summary += "\n\n<b>5 lỗi đầu:</b>\n" + "\n".join([f"- <code>{html.escape(error)}</code>" for error in errors])

        try:
            await msg_obj.edit_text(summary, parse_mode=ParseMode.HTML)
        except (ValueError, TypeError, KeyError, IndexError, TelegramError):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=summary, parse_mode=ParseMode.HTML)

    create_background_task(_bcsp_background(status_msg))

async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not user_data_db:
        await update.message.reply_text("Chưa có người dùng nào.")
        return

    query_raw = " ".join(context.args).strip() if context.args else ""
    users_source = list(user_data_db.items())

    if query_raw:
        query = query_raw.lstrip('@').strip().lower()
        if not query:
            await update.message.reply_text("Cú pháp: /users [user_id | @username]")
            return

        matched = {}

        # Match exact ID
        if query.isdigit():
            exact_by_id = user_data_db.get(query)
            if exact_by_id:
                matched[query] = exact_by_id

        # Match exact username (case-insensitive)
        for uid, data in user_data_db.items():
            username = str(data.get('username') or '').strip().lower()
            if username and username == query:
                matched[str(uid)] = data

        # Fallback: contains username for convenience
        if not matched and not query.isdigit():
            for uid, data in user_data_db.items():
                username = str(data.get('username') or '').strip().lower()
                if username and query in username:
                    matched[str(uid)] = data

        if not matched:
            await update.message.reply_html(
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không tìm thấy user với từ khóa: <code>{html.escape(query_raw)}</code>"
            )
            return

        users_source = list(matched.items())
        header = (
            f"<b><tg-emoji emoji-id=\"5429571366384842791\">🔎</tg-emoji> "
            f"KẾT QUẢ TÌM USER ({len(users_source)})</b>\n\n"
        )
    else:
        header = (
            f"<b><tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> "
            f"DANH SÁCH NGƯỜI DÙNG ({len(user_data_db)})</b>\n\n"
        )

    # Sort by numeric user id descending for easier lookup
    try:
        users_source.sort(key=lambda x: int(str(x[0])), reverse=True)
    except (ValueError, TypeError, KeyError, IndexError):
        users_source.sort(key=lambda x: str(x[0]), reverse=True)

    message_parts, current_part = [], header
    for uid, data in users_source:
        username = str(data.get('username') or '').strip()
        username_text = f"@{html.escape(username)}" if username else "N/A"
        first_name = html.escape(str(data.get('first_name') or ''))
        line = f"- {first_name} ({username_text})\n  ID: <code>{uid}</code>\n"
        if len(current_part) + len(line) > 4096:
            message_parts.append(current_part)
            current_part = ""
        current_part += line

    if current_part != header:
        message_parts.append(current_part)

    for part in message_parts:
        await update.message.reply_html(part)
        await asyncio.sleep(0.2)

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Cú pháp: /info <user_id hoặc @username>")
        return

    query_input = context.args[0].strip()
    target_id = None
    target_id_str = None

    if query_input.startswith("@"):
        search_username = query_input[1:].lower()
        for uid_str, udata in user_data_db.items():
            stored_username = (udata.get('username') or '').lower()
            if stored_username == search_username:
                target_id_str = uid_str
                target_id = int(uid_str)
                break
        if target_id is None:
            await update.message.reply_text(f"❌ Không tìm thấy user với username @{search_username}")
            return
    else:
        try:
            target_id = int(query_input)
            target_id_str = str(target_id)
        except ValueError:
            search_name = query_input.lower()
            for uid_str, udata in user_data_db.items():
                stored_name = (udata.get('first_name') or '').lower()
                if search_name in stored_name:
                    target_id_str = uid_str
                    target_id = int(uid_str)
                    break
            if target_id is None:
                await update.message.reply_text("❌ ID không hợp lệ hoặc không tìm thấy user.")
                return

    user_info = user_data_db.get(target_id_str)
    if not user_info:
        await update.message.reply_text("❌ Không tìm thấy người dùng trong hệ thống.")
        return
    message, kb, _, _ = _build_admin_userinfo_panel(target_id, 0)
    await update.message.reply_html(message, reply_markup=kb)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Cú pháp: /ban <user_id>"); return
    try:
        target_id = int(context.args[0])
        if target_id == ADMIN_USER_ID: await update.message.reply_text("Không thể tự cấm mình."); return
        banned_users.add(target_id); await save_data(); await update.message.reply_text(f"<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Đã cấm người dùng ID: {target_id}.")
    except (ValueError, IndexError): await update.message.reply_text("ID không hợp lệ.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Cú pháp: /unban <user_id>"); return
    try:
        target_id = int(context.args[0])
        if target_id in banned_users: banned_users.remove(target_id); await save_data(); await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã bỏ cấm người dùng ID: {target_id}.")
        else: await update.message.reply_text("Người dùng này không bị cấm.")
    except (ValueError, IndexError): await update.message.reply_text("ID không hợp lệ.")

async def doanhthu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(); today_revenue, month_revenue, total_revenue = 0, 0, 0; today_orders, month_orders, total_orders = 0, 0, 0
    completed_orders = [o for o in order_history if "Hoàn thành" in status_text(o.get("status"))]
    for order in completed_orders:
        amount = order.get("amount", 0) or 0; total_revenue += amount; total_orders += 1
        if 'timestamp' in order:
            order_time = datetime.fromtimestamp(order['timestamp'])
            if order_time.date() == now.date(): today_revenue += amount; today_orders += 1
            if order_time.month == now.month and order_time.year == now.year: month_revenue += amount; month_orders += 1
    await update.message.reply_html(f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>THỐNG KÊ DOANH THU</b> <tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji>\n\n" f"⭐️ <b>Hôm nay ({now.strftime('%d/%m')}):</b> {today_revenue:,} VNĐ ({today_orders} đơn)\n" f"<tg-emoji emoji-id=\"5796522630441867305\">🌙</tg-emoji> <b>Tháng này ({now.strftime('%m/%Y')}):</b> {month_revenue:,} VNĐ ({month_orders} đơn)\n" f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Tổng cộng:</b> {total_revenue:,} VNĐ ({total_orders} đơn)")


async def promobudget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: View promo budget status"""
    status = get_promo_budget_status()
    today = _get_today_key()
    details_text = ""
    tracker = daily_promo_tracker.get(today, {})
    details = tracker.get('details', [])
    
    type_totals = {}
    for d in details:
        t = d.get('type', 'other')
        type_totals[t] = type_totals.get(t, 0) + d.get('amount', 0)
    
    if type_totals:
        details_text = "\n".join(f"  • {t}: {v:,}đ" for t, v in type_totals.items())
    else:
        details_text = "  Chưa có chi phí KM nào"
    
    pct = status['percent_used']
    bar_filled = int(pct / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    
    msg = (
        f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>NGÂN SÁCH KHUYẾN MÃI HÔM NAY</b>\n\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Doanh thu hôm nay: <b>{status['revenue']:,}đ</b>\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> Ngân sách KM ({DAILY_PROMO_BUDGET_PERCENT}%): <b>{status['budget']:,}đ</b>\n"
        f"<tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji> Đã chi KM: <b>{status['spent']:,}đ</b>\n"
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Còn lại: <b>{status['remaining']:,}đ</b>\n\n"
        f"[{bar}] {pct}%\n\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Chi tiết:</b>\n{details_text}\n\n"
        f"<i><tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> Hệ thống tự động tắt KM khi vượt ngân sách</i>"
    )
    await update.message.reply_html(msg)


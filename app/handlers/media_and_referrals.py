async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: SKIP channel posts/edited posts - context.user_data is None!
    if update.channel_post or update.edited_channel_post:
        return  # Ignore channel posts, chỉ xử lý user messages
    
    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: SKIP khi không có user_data (edge case)
    if context.user_data is None:
        return  # Không có user context, skip

    # Kiểm tra chế độ bảo trì
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nChúng tôi đang nâng cấp hệ thống để phục vụ bạn tốt hơn. Vui lòng quay lại sau ít phút.", parse_mode=ParseMode.HTML)
        return

    user_state = context.user_data.get('state')
    
    if user_state == 'awaiting_report_photo':
        if not update.message or not update.message.photo:
             await update.message.reply_text("❌ Vui lòng gửi ảnh hợp lệ.")
             return
        order_code = context.user_data.get('report_order_code')
        found_order = order_index.get(order_code) if order_code else None
        if found_order and found_order.get('refunded_at'):
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa."
            )
            await clear_user_state(context)
            return
        if found_order and await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        photo_id = update.message.photo[-1].file_id
        try:
            # Validate file_id early to reduce Document_invalid at admin forwarding step.
            await context.bot.get_file(photo_id)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"[REPORT] ảnh báo lỗi không hợp lệ ở bước nhận ({e})")
            await update.message.reply_text(
                "❌ Ảnh không hợp lệ. Vui lòng gửi lại ảnh dạng <b>Photo</b> (không phải file/document).",
                parse_mode=ParseMode.HTML
            )
            return

        context.user_data['report_photo_id'] = photo_id
        context.user_data['report_photo_chat_id'] = update.message.chat_id
        context.user_data['report_photo_message_id'] = update.message.message_id
        context.user_data['state'] = 'awaiting_report_description'

        await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã nhận ảnh. Cuối cùng, vui lòng <b>mô tả ngắn gọn</b> vấn đề của bạn là gì.", parse_mode=ParseMode.HTML)
 
    elif user_state == 'awaiting_warranty_photo':
        order_code = context.user_data.get('warranty_claim_order')
        found_order = order_index.get(order_code) if order_code else None
        if found_order and await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        photo_id = update.message.photo[-1].file_id
        desc = context.user_data.get('warranty_description', 'No description')
        
        # Save claim
        claim_id = f"CLM-{int(time.time())}"
        warranty_claims[claim_id] = {
            'user_id': update.effective_user.id,
            'order_code': order_code,
            'description': desc,
            'photo_id': photo_id,
            'status': 'pending',
            'timestamp': time.time()
        }
        await save_data()
        
        # Notify Admin
        admin_msg = (
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>YÊU CẦU BẢO HÀNH MỚI</b>\n"
            f"User: {format_user_mention_html(update.effective_user)}\n"
            f"Order: {order_code}\n"
            f"Lý do: {desc}"
        )
        btns = [
            [_btn("Duyệt", icon_id="5021905410089550576", callback_data=f"approve_warranty:{claim_id}")],
            [_btn("Từ chối", icon_id="6114086705512321034", callback_data=f"reject_warranty:{claim_id}")]
        ]
        try:
            await context.bot.send_photo(ADMIN_USER_ID, photo_id, caption=admin_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Cannot notify admin about warranty claim {claim_id}: {e}")
        
        await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Yêu cầu bảo hành đã được gửi. Admin sẽ xem xét sớm.", reply_markup=create_main_menu(user_id=update.effective_user.id))
        await clear_user_state(context)

def _build_my_stats_panel(user):
    user_id = user.id
    stats = calculate_user_stats(user_id)
    badges = calculate_badges(user_id)
    rank_info = get_user_rank(user_id)
    current_rank = rank_info.get('rank') or {}
    base_rank = rank_info.get('base_rank') or current_rank
    next_rank = rank_info.get('next_rank')
    user_info = db_get_user(user_id)
    balance = user_info.get('balance', 0) if user_info else 0
    maintenance_status = rank_info.get('maintenance_status') or {}
    current_rank_name = format_rank_entry_premium(current_rank)
    base_rank_name = format_rank_entry_premium(base_rank)
    next_rank_name = format_rank_entry_premium(next_rank) if next_rank else ""
    discount_suffix = ""

    try:
        current_rank_threshold = int(current_rank.get("min_spent", current_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        current_rank_threshold = 0

    try:
        base_rank_threshold = int(base_rank.get("min_spent", base_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        base_rank_threshold = 0

    maintenance_minimum = int(
        maintenance_status.get("minimum_required", VIP_MONTHLY_MAINTENANCE_MIN_SPEND)
        or VIP_MONTHLY_MAINTENANCE_MIN_SPEND
    )
    show_maintenance_status = base_rank_threshold > 0 or current_rank_threshold > 0

    achievements_block = ""
    if badges:
        badge_rows = []
        for idx in range(0, len(badges), 2):
            badge_rows.append("   ".join(badges[idx:idx + 2]))
        badge_text = "\n".join(badge_rows)
        achievements_block = (
            f'<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Thành tựu</b>\n'
            f'<blockquote>{badge_text}</blockquote>\n\n'
        )

    rank_lines = [
        f'<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Hạng hiện tại: {current_rank_name}{discount_suffix}',
    ]

    if show_maintenance_status:
        maintenance_icon = "6269163801178804220" if maintenance_status.get("met_requirement") else "5447644880824181073"
        maintenance_glyph = "✅" if maintenance_status.get("met_requirement") else "⚠️"
        rank_lines.append(
            f'<tg-emoji emoji-id="{maintenance_icon}">{maintenance_glyph}</tg-emoji> '
            f'Duy trì {maintenance_status.get("period_label", "tháng trước")}: '
            f'<b>{maintenance_status.get("monthly_spend", 0):,} VNĐ</b> / '
            f'<b>{maintenance_minimum:,} VNĐ</b>'
        )

    if rank_info.get("demoted_by_maintenance"):
        rank_lines.append(
            f'<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> '
            f'Đang tạm tụt 1 bậc, cần thêm <b>{rank_info.get("remaining_to_next", 0):,} VNĐ</b> '
            f'để lấy lại {base_rank_name} vào tháng sau'
        )
    elif next_rank:
        rank_lines.append(
            f'<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> '
            f'Cần thêm <b>{rank_info.get("remaining_to_next", 0):,} VNĐ</b> để lên {next_rank_name}'
        )
    elif current_rank_threshold > 0:
        rank_lines.append(
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> Bạn đang ở hạng VIP cao nhất.'
        )

    rank_text = "\n".join(rank_lines)

    msg = (
        f'<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>THỐNG KÊ CÁ NHÂN</b>\n'
        f'━━━━━━━━━━━━━━━━━━\n\n'
        f'<tg-emoji emoji-id="5350778980158956492">👤</tg-emoji> <b>Tài khoản</b>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5350778980158956492">👤</tg-emoji> Tên: <b>{format_user_name_html(user=user)}</b>\n'
        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Số dư: <b>{balance:,} VNĐ</b>\n'
        f'<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> ID: <code>{user_id}</code>'
        f'</blockquote>\n\n'
        f'<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>Mua sắm</b>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Tổng chi tiêu: <b>{stats["total_spent"]:,} VNĐ</b>\n'
        f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> Đơn hoàn thành: <b>{stats["order_count"]}</b>\n'
        f'<tg-emoji emoji-id="6260059243605398502">🏷️</tg-emoji> Tiết kiệm mã giảm: <b>{stats["coupon_savings"]:,} VNĐ</b>'
        f'</blockquote>\n\n'
        f'<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>Giới thiệu ({REFERRAL_COMMISSION_PERCENT}% hoa hồng)</b>\n'
        f'<blockquote>'
        f'<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> Đã giới thiệu: <b>{stats["referral_count"]}</b> người\n'
        f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Hoa hồng nhận: <b>{stats["commission_earned"]:,} VNĐ</b>'
        f'</blockquote>\n\n'
        f'{achievements_block}'
        f'<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Hạng VIP</b>\n'
        f'<blockquote>{rank_text}</blockquote>'
    )

    btns = [[_btn("Link giới thiệu", icon_id="5193085063998224234", callback_data='my_referral')]]
    return msg, btns


def _build_my_stats_text_with_entities(user):
    import html
    import re
    from telegram import MessageEntity

    def _strip_markup(value):
        text = str(value or "")
        text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)
        return html.unescape(text).strip()

    def _utf16_len(value: str) -> int:
        return len((value or "").encode("utf-16-le")) // 2

    stats = calculate_user_stats(user.id)
    badges = calculate_badges(user.id)
    rank_info = get_user_rank(user.id)
    current_rank = rank_info.get('rank') or {}
    base_rank = rank_info.get('base_rank') or current_rank
    next_rank = rank_info.get('next_rank')
    user_info = db_get_user(user.id)
    balance = user_info.get('balance', 0) if user_info else 0
    maintenance_status = rank_info.get('maintenance_status') or {}

    current_rank_name = _strip_markup(format_rank_entry_premium(current_rank))
    base_rank_name = _strip_markup(format_rank_entry_premium(base_rank))
    next_rank_name = _strip_markup(format_rank_entry_premium(next_rank)) if next_rank else ""

    badge_names = [_strip_markup(badge) for badge in badges]
    badge_rows = []
    for idx in range(0, len(badge_names), 2):
        badge_rows.append(" | ".join(badge_names[idx:idx + 2]))

    discount_suffix = ""

    try:
        current_rank_threshold = int(current_rank.get("min_spent", current_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        current_rank_threshold = 0

    try:
        base_rank_threshold = int(base_rank.get("min_spent", base_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        base_rank_threshold = 0

    maintenance_minimum = int(
        maintenance_status.get("minimum_required", VIP_MONTHLY_MAINTENANCE_MIN_SPEND)
        or VIP_MONTHLY_MAINTENANCE_MIN_SPEND
    )

    parts = []
    entities = []

    def _add(text: str):
        parts.append(text)

    def _offset() -> int:
        return _utf16_len("".join(parts))

    def _add_custom(glyph: str, emoji_id: str):
        start = _offset()
        parts.append(glyph)
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=start,
                length=_utf16_len(glyph),
                custom_emoji_id=str(emoji_id),
            )
        )

    def _line(glyph: str, emoji_id: str, text: str):
        _add_custom(glyph, emoji_id)
        _add(f" {text}\n")

    _line("📊", "6059654836918423763", "THONG KE CA NHAN")
    _add("━━━━━━━━━━━━━━━━━━\n\n")

    _line("👤", "5350778980158956492", "Tai khoan")
    if getattr(user, "is_premium", False):
        _add_custom("💎", "5240228673738527951")
        _add(" ")
    _line("👤", "5350778980158956492", f"Ten: {getattr(user, 'full_name', None) or getattr(user, 'first_name', 'N/A')}")
    _line("💰", "5278467510604160626", f"So du: {balance:,} VNĐ")
    _line("🆔", "5334890573281114250", f"ID: {user.id}")
    _add("\n")

    _line("🛒", "5247134066322447995", "Mua sam")
    _line("💰", "5278467510604160626", f"Tong chi tieu: {stats['total_spent']:,} VNĐ")
    _line("📦", "5854908544712707500", f"Don hoan thanh: {stats['order_count']}")
    _line("🏷️", "6260059243605398502", f"Tiet kiem ma giam: {stats['coupon_savings']:,} VNĐ")
    _add("\n")

    _line("🤝", "6293853394910057834", f"Gioi thieu ({REFERRAL_COMMISSION_PERCENT}% hoa hong)")
    _line("👥", "5350778980158956492", f"Da gioi thieu: {stats['referral_count']} nguoi")
    _line("💰", "5278467510604160626", f"Hoa hong nhan: {stats['commission_earned']:,} VNĐ")
    _add("\n")

    if badge_rows:
        _line("🎁", "5449800250032143374", "Thanh tuu")
        for row in badge_rows:
            _add(f"• {row}\n")
        _add("\n")

    _line("💎", "5240228673738527951", "Hang VIP")
    _line("💎", "5240228673738527951", f"Hang hien tai: {current_rank_name}{discount_suffix}")

    if base_rank_threshold > 0 or current_rank_threshold > 0:
        maintenance_ok = maintenance_status.get("met_requirement")
        _line(
            "✅" if maintenance_ok else "⚠️",
            "6269163801178804220" if maintenance_ok else "5447644880824181073",
            f"Duy tri {maintenance_status.get('period_label', 'thang truoc')}: "
            f"{maintenance_status.get('monthly_spend', 0):,} VNĐ / {maintenance_minimum:,} VNĐ",
        )

    if rank_info.get("demoted_by_maintenance"):
        _line(
            "⚠️",
            "5447644880824181073",
            f"Dang tam tut 1 bac, can them {rank_info.get('remaining_to_next', 0):,} VNĐ "
            f"de lay lai {base_rank_name} vao thang sau",
        )
    elif next_rank:
        _line(
            "📊",
            "6059654836918423763",
            f"Can them {rank_info.get('remaining_to_next', 0):,} VNĐ de len {next_rank_name}",
        )
    elif current_rank_threshold > 0:
        _line("👑", "6124902618574625426", "Ban dang o hang VIP cao nhat")

    text = "".join(parts).rstrip()
    btns = [[_btn("Link giới thiệu", icon_id="5193085063998224234", callback_data='my_referral')]]
    return text, entities, btns


def _build_my_stats_text_with_entities_v2(user):
    import html
    import re
    from telegram import MessageEntity

    def _utf16_len(value: str) -> int:
        return len((value or "").encode("utf-16-le")) // 2

    def _strip_markup(value):
        text = str(value or "")
        text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)
        return html.unescape(text).strip()

    def _rank_label(rank):
        if not isinstance(rank, dict):
            return "Dong"
        min_spent = int(rank.get("min_spent", rank.get("min_spend", 0)) or 0)
        if min_spent >= 10000000:
            return "Cao Thu"
        if min_spent >= 5000000:
            return "Kim Cuong"
        if min_spent >= 1000000:
            return "Vang"
        if min_spent >= 500000:
            return "Bac"
        return "Dong"

    stats = calculate_user_stats(user.id)
    badges = calculate_badges(user.id)
    rank_info = get_user_rank(user.id)
    current_rank = rank_info.get("rank") or {}
    base_rank = rank_info.get("base_rank") or current_rank
    next_rank = rank_info.get("next_rank")
    user_info = db_get_user(user.id)
    balance = user_info.get("balance", 0) if user_info else 0
    maintenance_status = rank_info.get("maintenance_status") or {}

    current_rank_name = _rank_label(current_rank) or _strip_markup(format_rank_entry_premium(current_rank))
    base_rank_name = _rank_label(base_rank) or _strip_markup(format_rank_entry_premium(base_rank))
    next_rank_name = _rank_label(next_rank) if next_rank else ""

    discount_suffix = ""

    try:
        current_rank_threshold = int(current_rank.get("min_spent", current_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        current_rank_threshold = 0

    try:
        base_rank_threshold = int(base_rank.get("min_spent", base_rank.get("min_spend", 0)) or 0)
    except (TypeError, ValueError, AttributeError):
        base_rank_threshold = 0

    maintenance_minimum = int(
        maintenance_status.get("minimum_required", VIP_MONTHLY_MAINTENANCE_MIN_SPEND)
        or VIP_MONTHLY_MAINTENANCE_MIN_SPEND
    )

    badge_names = [_strip_markup(badge) for badge in badges]

    parts = []
    entities = []

    def _append(text: str):
        parts.append(text)

    def _offset() -> int:
        return _utf16_len("".join(parts))

    def _emoji(glyph: str, emoji_id: str):
        start = _offset()
        parts.append(glyph)
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=start,
                length=_utf16_len(glyph),
                custom_emoji_id=str(emoji_id),
            )
        )

    def _line(glyph: str, emoji_id: str, text: str):
        _emoji(glyph, emoji_id)
        _append(f" {text}\n")

    _line("\U0001F4CA", "6059654836918423763", "THONG KE CA NHAN")
    _append("━━━━━━━━━━━━━━━━━━\n\n")

    _line("\U0001F464", "5350778980158956492", "Tai khoan")
    if getattr(user, "is_premium", False):
        _emoji("\U0001F48E", "5240228673738527951")
        _append(" ")
    _line("\U0001F464", "5350778980158956492", f"Ten: {getattr(user, 'full_name', None) or getattr(user, 'first_name', 'N/A')}")
    _line("\U0001F4B0", "5278467510604160626", f"So du: {balance:,} VND")
    _line("\U0001F194", "5334890573281114250", f"ID: {user.id}")
    _append("\n")

    _line("\U0001F6D2", "5247134066322447995", "Mua sam")
    _line("\U0001F4B0", "5278467510604160626", f"Tong chi tieu: {stats['total_spent']:,} VND")
    _line("\U0001F4E6", "5854908544712707500", f"Don hoan thanh: {stats['order_count']}")
    _line("\U0001F3F7\uFE0F", "6260059243605398502", f"Tiet kiem ma giam: {stats['coupon_savings']:,} VND")
    _append("\n")

    _line("\U0001F91D", "6293853394910057834", f"Gioi thieu ({REFERRAL_COMMISSION_PERCENT}% hoa hong)")
    _line("\U0001F465", "5350778980158956492", f"Da gioi thieu: {stats['referral_count']} nguoi")
    _line("\U0001F4B0", "5278467510604160626", f"Hoa hong nhan: {stats['commission_earned']:,} VND")
    _append("\n")

    if badge_names:
        _line("\U0001F381", "5449800250032143374", "Thanh tuu")
        for idx in range(0, len(badge_names), 2):
            _append(f"* {' | '.join(badge_names[idx:idx + 2])}\n")
        _append("\n")

    _line("\U0001F48E", "5240228673738527951", "Hang VIP")
    _line("\U0001F48E", "5240228673738527951", f"Hang hien tai: {current_rank_name}{discount_suffix}")

    if base_rank_threshold > 0 or current_rank_threshold > 0:
        maintenance_ok = maintenance_status.get("met_requirement")
        _line(
            "\u2705" if maintenance_ok else "\u26A0\uFE0F",
            "6269163801178804220" if maintenance_ok else "5447644880824181073",
            f"Duy tri {maintenance_status.get('period_label', 'thang truoc')}: "
            f"{maintenance_status.get('monthly_spend', 0):,} VND / {maintenance_minimum:,} VND",
        )

    if rank_info.get("demoted_by_maintenance"):
        _line(
            "\u26A0\uFE0F",
            "5447644880824181073",
            f"Dang tam tut 1 bac, can them {rank_info.get('remaining_to_next', 0):,} VND "
            f"de lay lai {base_rank_name} vao thang sau",
        )
    elif next_rank:
        _line(
            "\U0001F4CA",
            "6059654836918423763",
            f"Can them {rank_info.get('remaining_to_next', 0):,} VND de len {next_rank_name}",
        )
    elif current_rank_threshold > 0:
        _line("\U0001F451", "6124902618574625426", "Ban dang o hang VIP cao nhat")

    text = "".join(parts)
    btns = [[_btn("Link giới thiệu", icon_id="5193085063998224234", callback_data='my_referral')]]
    return text, entities, btns


async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    if await check_if_banned(update): return
    user_id = update.effective_user.id
    stats = calculate_user_stats(user_id)
    badges = calculate_badges(user_id)
    rank_info = get_user_rank(user_id)
    current_rank = rank_info.get('rank') or {}
    base_rank = rank_info.get('base_rank') or current_rank
    next_rank = rank_info.get('next_rank')
    user_info = db_get_user(user_id)
    balance = user_info.get('balance', 0) if user_info else 0
    maintenance_status = rank_info.get('maintenance_status') or {}
    current_rank_name = format_rank_entry_premium(current_rank)
    base_rank_name = format_rank_entry_premium(base_rank)
    next_rank_name = format_rank_entry_premium(next_rank) if next_rank else ""

    achievements_block = ""
    if badges:
        achievements_block = lt(
            user_id,
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Thành tựu</b>\n<blockquote>{badges}</blockquote>',
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Achievements</b>\n<blockquote>{badges}</blockquote>',
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>成就</b>\n<blockquote>{badges}</blockquote>',
            badges="\n".join(f"• {badge}" for badge in badges),
        )

    rank_block = lt(
        user_id,
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Hạng VIP</b>\n<blockquote>• Hiện tại: <b>{rank}</b>\n',
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>VIP Rank</b>\n<blockquote>• Current: <b>{rank}</b>\n',
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>VIP 等级</b>\n<blockquote>• 当前：<b>{rank}</b>\n', rank=current_rank_name,
    )
    remaining = rank_info.get("remaining_to_next", 0)
    if rank_info.get("demoted_by_maintenance"):
        rank_block += lt(
            user_id,
            '• Tháng {period} đã chi <b>{spent:,} VNĐ</b> / yêu cầu <b>{minimum:,} VNĐ</b>\n• Đang bị tụt 1 bậc, cần thêm <b>{remaining:,} VNĐ</b> để lấy lại <b>{base}</b> vào tháng sau\n• Quy tắc duy trì: tháng trước chi dưới <b>{minimum:,} VNĐ</b> sẽ tụt 1 bậc\n',
            '• Spent <b>{spent:,} VND</b> / required <b>{minimum:,} VND</b> in {period}\n• Temporarily down one rank; spend <b>{remaining:,} VND</b> more to restore <b>{base}</b> next month\n• Maintenance rule: spending below <b>{minimum:,} VND</b> in the previous month lowers one rank\n',
            '• {period}消费 <b>{spent:,} VND</b> / 要求 <b>{minimum:,} VND</b>\n• 当前暂降一级；再消费 <b>{remaining:,} VND</b>，下月恢复 <b>{base}</b>\n• 保级规则：上月消费低于 <b>{minimum:,} VND</b> 将降一级\n',
            period=maintenance_status.get("period_label", "trước"), spent=maintenance_status.get("monthly_spend", 0),
            minimum=VIP_MONTHLY_MAINTENANCE_MIN_SPEND, remaining=remaining, base=base_rank_name,
        )
    elif next_rank:
        rank_block += lt(user_id, '• Cần thêm <b>{amount:,} VNĐ</b> để lên <b>{rank}</b>\n', '• Spend <b>{amount:,} VND</b> more to reach <b>{rank}</b>\n', '• 再消费 <b>{amount:,} VND</b> 即可升级至 <b>{rank}</b>\n', amount=remaining, rank=next_rank_name)
    rank_block += '</blockquote>'

    msg = lt(
        user_id,
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>THỐNG KÊ CÁ NHÂN</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>Tài khoản</b>\n<blockquote>• Tên: <b>{name}</b>\n• Số dư: <b>{balance:,} VNĐ</b>\n• ID: <code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>Mua sắm</b>\n<blockquote>• Tổng chi tiêu: <b>{spent:,} VNĐ</b>\n• Đơn hoàn thành: <b>{orders}</b>\n• Tiết kiệm mã giảm: <b>{saved:,} VNĐ</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>Giới thiệu ({percent}% hoa hồng)</b>\n<blockquote>• Đã giới thiệu: <b>{refs}</b> người\n• Hoa hồng thực nhận: <b>{earned:,} VNĐ</b></blockquote>{achievements}',
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>PERSONAL STATISTICS</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>Account</b>\n<blockquote>• Name: <b>{name}</b>\n• Balance: <b>{balance:,} VND</b>\n• ID: <code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>Purchases</b>\n<blockquote>• Total spent: <b>{spent:,} VND</b>\n• Completed orders: <b>{orders}</b>\n• Coupon savings: <b>{saved:,} VND</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>Referrals ({percent}% commission)</b>\n<blockquote>• Referred: <b>{refs}</b> people\n• Commission earned: <b>{earned:,} VND</b></blockquote>{achievements}',
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>个人统计</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>账户</b>\n<blockquote>• 姓名：<b>{name}</b>\n• 余额：<b>{balance:,} VND</b>\n• ID：<code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>购物</b>\n<blockquote>• 总消费：<b>{spent:,} VND</b>\n• 已完成订单：<b>{orders}</b>\n• 优惠码节省：<b>{saved:,} VND</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>推荐（{percent}% 佣金）</b>\n<blockquote>• 已推荐：<b>{refs}</b> 人\n• 已获佣金：<b>{earned:,} VND</b></blockquote>{achievements}',
        name=format_user_name_html(user=update.effective_user), balance=balance, id=user_id,
        spent=stats["total_spent"], orders=stats["order_count"], saved=stats["coupon_savings"],
        percent=REFERRAL_COMMISSION_PERCENT, refs=stats["referral_count"], earned=stats["commission_earned"],
        achievements=achievements_block, rank=rank_block,
    )
    btns = [[_btn(lt(user_id, "Link giới thiệu", "Referral Link", "推荐链接"), icon_id="5193085063998224234", callback_data='my_referral')]]
    msg = upgrade_text_to_premium_emoji(msg)
    if is_callback:
        btns.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='back_to_main')])
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))


async def show_my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.effective_user.id
    stats = calculate_user_stats(user_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    balance = user_data_db.get(str(user_id), {}).get('balance', 0)
    msg = lt(
        user_id,
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>CHƯƠNG TRÌNH ĐỐI TÁC MMO</b>\n━━━━━━━━━━━━━━━━━━\nGiới thiệu bạn bè để nhận <b>{percent}%</b> hoa hồng cho tất cả giao dịch của họ. Hoa hồng được cộng vào số dư để mua sản phẩm tại Dino Store.\n\n<b>Link Giới Thiệu Của Bạn:</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>Thống Kê Nhanh:</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> Đã mời: <b>{count}</b> người\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> Đã kiếm: <b>{earned:,} VNĐ</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> Số dư mua hàng: <b>{balance:,} VNĐ</b>\n',
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>MMO PARTNER PROGRAM</b>\n━━━━━━━━━━━━━━━━━━\nRefer friends and earn <b>{percent}%</b> commission on their transactions. Commission is added to your balance for purchases at Dino Store.\n\n<b>Your Referral Link:</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>Quick Stats:</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> Invited: <b>{count}</b> people\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> Earned: <b>{earned:,} VND</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> Purchase balance: <b>{balance:,} VND</b>\n',
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>MMO 合作伙伴计划</b>\n━━━━━━━━━━━━━━━━━━\n邀请好友，获得其交易的 <b>{percent}%</b> 佣金。佣金将计入 Dino Store 的购物余额。\n\n<b>您的推荐链接：</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>快速统计：</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> 已邀请：<b>{count}</b> 人\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> 已赚取：<b>{earned:,} VND</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> 购物余额：<b>{balance:,} VND</b>\n',
        percent=REFERRAL_COMMISSION_PERCENT, link=ref_link, count=stats["referral_count"], earned=stats["commission_earned"], balance=balance,
    )
    keyboard = [[_btn(lt(user_id, "Top giới thiệu", "Top Referrers", "推荐排行"), icon_id="6129805886383723340", callback_data='top_referrers')]]
    if is_callback:
        keyboard.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='back_to_main')])
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_top_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.effective_user.id
    top_list = get_top_referrers(limit=10)
    msg = lt(user_id, "⭐️ <b>TOP 10 NGƯỜI GIỚI THIỆU</b>\n\n", "⭐️ <b>TOP 10 REFERRERS</b>\n\n", "⭐️ <b>推荐排行榜前 10 名</b>\n\n")
    if not top_list:
        msg += lt(user_id, "<i>Chưa có dữ liệu</i>", "<i>No data yet</i>", "<i>暂无数据</i>")
    else:
        for item in top_list:
            rank = item['rank']
            medal = "⭐️" if rank <= 3 else f"{rank}."
            name = item['full_name'] if item.get('is_fake') else mask_name(item['full_name'])
            msg += f"{medal} <b>{name}</b>\n"
            msg += lt(user_id, '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} người · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission:,}đ\n\n', '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} people · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission:,} VND\n\n', '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} 人 · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission:,} VND\n\n', count=item['referral_count'], commission=item['total_commission'])
    btns = [[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='my_referral')]]
    if is_callback:
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

# ==============================================================================
#  HELPER: Background Email Task for Resend Link (Fix VPS Timeout)
# ==============================================================================
async def _send_resend_link_email_background(
    context: ContextTypes.DEFAULT_TYPE,
    query,
    target_email: str,
    target_uid: int,
    link: str,
    original_caption: str
):
    """
    FIX: Send email in background to prevent callback timeout on VPS.
    VPS SMTP connections are slow (>10s) causing Telegram callback timeout.
    This runs as background task so callback handler returns immediately.
    """
    try:
        # Send email (slow operation on VPS)
        email_sent, email_error = await send_activation_email(
            target_email,
            "[Hỗ Trợ] Link kích hoạt iCloud (Mới)",
            "Khách hàng",
            link
        )
        if not email_sent:
            raise RuntimeError(email_error or "Unknown email error")

        # Keep order history consistent with resend action
        target_uid_str = str(target_uid)
        for order in reversed(order_history):
            if str(order.get("user_id")) == target_uid_str and str(order.get("email", "")).lower() == target_email.lower():
                order.update({"link": link, "status": OrderStatus.COMPLETED_RESENT.value})
                break
        await save_data(force=True)
        
        # Update UI with success
        success_msg = (
            f"{original_caption}\n\n"
            f"{E_SUCCESS} <b>ĐÃ GỬI LINK MỚI</b>\n"
            f"{E_GLOBE} Email: {target_email}\n"
            f"{E_GLOBE} Link: <code>{link}</code>\n"
            f"{E_LOADING} {datetime.now().strftime('%H:%M %d/%m')}"
        )
        
        try:
            if query.message.caption:
                await query.edit_message_caption(
                    caption=success_msg,
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    text=success_msg,
                    parse_mode=ParseMode.HTML
                )
        except BadRequest:
            pass  # Ignore if message was deleted
        
        # Notify user
        try:
            await context.bot.send_message(
                target_uid,
                f"{E_SOS} <b>THÔNG BÁO TỪ ADMIN</b>\n\n"
                f"Admin đã gửi cho bạn một link kích hoạt mới theo yêu cầu báo lỗi.\n"
                f"{E_GLOBE} Email: <code>{target_email}</code>\n\n"
                f"Vui lòng kiểm tra hộp thư (cả mục Spam/Junk) nhé!",
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Cannot notify user {target_uid} about resent link: {e}")
    
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Background email send failed: {e}")
        
        # NOTE: Không cần revert link vì link không bị xóa khỏi kho
        # Link vẫn tồn tại cho lần gửi tiếp theo
        
        # Update UI with error
        error_msg = (
            f"{original_caption}\n\n"
            f"❌ <b>LỖI GỬI EMAIL:</b> {str(e)[:100]}"
        )
        
        try:
            if query.message.caption:
                await query.edit_message_caption(
                    caption=error_msg,
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    text=error_msg,
                    parse_mode=ParseMode.HTML
                )
        except BadRequest:
            pass


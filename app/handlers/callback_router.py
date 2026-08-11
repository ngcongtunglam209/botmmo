
from __future__ import annotations

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


API_PREM_WARN = '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>'
API_PREM_OK = '<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>'
API_PREM_STOP = '<tg-emoji emoji-id="5424857974784925603">⛔</tg-emoji>'
API_PREM_FAIL = '❌'
API_PREM_USER = '<tg-emoji emoji-id="5350778980158956492">👤</tg-emoji>'
API_PREM_SHIELD = '<tg-emoji emoji-id="5197288647275071607">🛡️</tg-emoji>'
API_PREM_LOCK = '🔐'
API_PREM_MONEY = '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>'
API_PREM_NOTE = '<tg-emoji emoji-id="5350481781306958339">💾</tg-emoji>'

def _callback_requires_manual_answer(command: str) -> bool:
    command = str(command or "")
    manual_answer_commands = {
        'api_register_request',
        'ask_ai_confirm',
        'create_ticket_confirm',
        'join_ga_action',
        'withdraw_request',
    }
    manual_answer_prefixes = (
        'topup_cancel:',
        'topup_pay:',
        'topup_rpaynet:',
        'adm_quick:',
        'adm_uo:',
        'admin_open_chat:',
        'admin_close_chat:',
        'api_approve_',
        'api_refund_',
        'api_member_',
        'approve_api:',
        'approve_warranty:',
        'approve_withdraw:',
        'buy_again:',
        'cancel_order:',
        'cancel_payment_',
        'claim_warranty:',
        'complete_manual_',
        'dice_prize_',
        'dismiss_report:',
        'manual_done_',
        'manual_done:',
        'manual_refund_',
        'manual_refund:',
        'refund_manual_',
        'refund_bank:',
        'reject_api:',
        'reject_warranty:',
        'reject_withdraw:',
        'reject_policy:',
        'reject_expired:',
        'replace_auto:',
        'replace_manual:',
        'reply_to_ticket:',
        'resend_order_items:',
        'report_specific_order:',
        'warranty_done:',
        'view_order_history_',
    )
    return command in manual_answer_commands or command.startswith(manual_answer_prefixes)


def _normalize_order_product_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


_fallback_products_cache = None


def _load_fallback_products_catalog() -> dict:
    global _fallback_products_cache

    if isinstance(_fallback_products_cache, dict):
        return _fallback_products_cache

    import json as _json
    import os as _os

    base_dir = _os.path.dirname(__file__)
    candidate_paths = (
        _os.path.join(base_dir, "data_products.json"),
        _os.path.join(_os.path.dirname(_os.path.dirname(base_dir)), "data_products.json"),
    )

    for candidate_path in candidate_paths:
        try:
            if not _os.path.exists(candidate_path):
                continue
            with open(candidate_path, encoding="utf-8") as handle:
                loaded = _json.load(handle)
            if isinstance(loaded, dict):
                _fallback_products_cache = loaded
                return _fallback_products_cache
        except (OSError, ValueError, TypeError):
            continue

    _fallback_products_cache = {}
    return _fallback_products_cache


def _parse_duration_days_from_text(text: str) -> int:
    normalized = _normalize_order_product_key(text)
    if not normalized:
        return 0

    if any(token in normalized for token in ("vĩnh viễn", "vinh vien", "lifetime", "permanent", "forever")):
        return 0

    unit_multipliers = (
        (365, ("năm", "nam", "year", "years")),
        (30, ("tháng", "thang", "month", "months")),
        (7, ("tuần", "tuan", "week", "weeks")),
        (1, ("ngày", "ngay", "day", "days")),
    )
    for multiplier, units in unit_multipliers:
        for unit in units:
            match = re.search(rf"(\d+)\s*{re.escape(unit)}\b", normalized)
            if match:
                return int(match.group(1)) * multiplier

    return 0


def _resolve_order_product(order: dict):
    product_id = str(order.get('product_id') or '').strip()
    if product_id:
        product = products.get(product_id)
        if product:
            return product_id, product
        fallback_product = _load_fallback_products_catalog().get(product_id)
        if fallback_product:
            return product_id, fallback_product

    order_name_key = _normalize_order_product_key(order.get('product_name'))
    if not order_name_key:
        return "", None

    relaxed_matches = []
    for catalog in (products, _load_fallback_products_catalog()):
        for current_product_id, product in catalog.items():
            product_name_key = _normalize_order_product_key(product.get('name'))
            if not product_name_key:
                continue
            if product_name_key == order_name_key:
                return current_product_id, product
            if order_name_key in product_name_key or product_name_key in order_name_key:
                relaxed_matches.append((current_product_id, product))

    if len(relaxed_matches) == 1:
        return relaxed_matches[0]

    return "", None


def _resolve_repurchase_product(order: dict):
    if not isinstance(order, dict) or _api_is_order_record(order):
        return "", None
    product_id, _resolved_product = _resolve_order_product(order)
    current_product = products.get(product_id)
    if not product_id or not isinstance(current_product, dict):
        return "", None
    return product_id, current_product


def _resolve_order_duration_days(order: dict) -> int:
    _, product = _resolve_order_product(order)
    candidates = (
        order.get('product_duration'),
        order.get('duration'),
        order.get('duration_text'),
        product.get('duration') if product else "",
        order.get('product_name'),
        product.get('name') if product else "",
        product.get('description') if product else "",
    )
    for candidate in candidates:
        duration_days = _parse_duration_days_from_text(candidate)
        if duration_days > 0:
            return duration_days
    return 0


async def _complete_partner_api_key_rotation(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    partner_key: str,
    partner_data: dict,
    source_chat_id: int | None = None,
    source_message_id: int | None = None,
):
    current_balance = _api_get_partner_display_balance(partner_key, partner_data)
    partner_name = partner_data.get("name", "Partner")
    old_key = str(partner_key or "").strip()
    new_key = f"sk_live_{secrets.token_hex(16)}"
    while new_key in api_keys:
        new_key = f"sk_live_{secrets.token_hex(16)}"

    rotation_ts = int(time.time())
    old_partner_snapshot = dict(partner_data)
    new_partner_data = dict(partner_data)
    new_partner_data["balance"] = current_balance
    new_partner_data["enabled"] = True
    new_partner_data["rotated_from"] = old_key
    new_partner_data["rotated_at"] = rotation_ts
    partner_data["balance"] = current_balance
    partner_data["enabled"] = False
    partner_data["rotated_to"] = new_key
    partner_data["rotated_at"] = rotation_ts
    api_keys[new_key] = new_partner_data

    updated_pending_refs = []
    for pending_details in pending_api_deposits.values():
        if not isinstance(pending_details, dict):
            continue
        try:
            pending_user_id = int(pending_details.get("user_id", 0) or 0)
        except (TypeError, ValueError):
            pending_user_id = 0
        if pending_user_id != user_id:
            continue
        pending_details["api_key"] = new_key
        pending_details["partner_name"] = partner_name
        updated_pending_refs.append(pending_details)

    await save_data(force=True, tables=[API_KEYS_FILE, "data_pending_api_deposits.json"])
    resolved_key, resolved_partner_data = get_partner_api_entry_by_user(user_id)
    if resolved_key != new_key or not isinstance(resolved_partner_data, dict):
        direct_partner_data = api_keys.get(new_key)
        try:
            direct_user_id = int((direct_partner_data or {}).get("user_id", 0) or 0)
        except (TypeError, ValueError, AttributeError):
            direct_user_id = 0
        if isinstance(direct_partner_data, dict) and direct_user_id == user_id:
            resolved_key, resolved_partner_data = new_key, direct_partner_data
    if resolved_key != new_key or not isinstance(resolved_partner_data, dict):
        api_keys.pop(new_key, None)
        partner_data.clear()
        partner_data.update(old_partner_snapshot)
        for pending_details in updated_pending_refs:
            pending_details["api_key"] = old_key
            pending_details["partner_name"] = partner_name
        await save_data(force=True, tables=[API_KEYS_FILE, "data_pending_api_deposits.json"])
        logger.error("API key rotation failed for user %s", user_id)
        await safe_send_message(
            context,
            chat_id,
            (
                "❌ "
                "<b>Không thể hoàn tất đổi API key.</b>\n\n"
                "Hệ thống đã giữ nguyên key cũ để tránh gián đoạn. Hãy thử lại sau."
            ),
            parse_mode=ParseMode.HTML,
        )
        return False

    logger.info("API key rotated for user %s", user_id)
    if source_chat_id and source_message_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=source_chat_id,
                message_id=source_message_id,
                caption=(
                    f"{API_PREM_WARN} <b>QR/API KEY CŨ ĐÃ HẾT HIỆU LỰC</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"{API_PREM_SHIELD} <b>Key cũ:</b> <code>{old_key}</code>\n"
                    f"{API_PREM_LOCK} <b>Key mới:</b> <code>{new_key}</code>\n\n"
                    "<i>Vui lòng dùng key hoặc QR ở tin nhắn mới nhất bên dưới. Không dùng lại ảnh QR cũ này.</i>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=None,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            logger.debug("Cannot update stale API wallet QR message for user %s", user_id)

    text = (
        f"{API_PREM_LOCK} <b>ĐÃ ĐỔI API KEY</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{API_PREM_USER} <b>Partner:</b> {html.escape(str(partner_name))}\n"
        f"{API_PREM_NOTE} <b>API Key mới:</b> <code>{new_key}</code>\n"
        f"{API_PREM_MONEY} <b>Số dư ví chung:</b> {current_balance:,} VNĐ\n\n"
        f"<i>{API_PREM_WARN} API key cũ đã bị vô hiệu hóa để bảo mật. Hãy cập nhật key mới trong hệ thống của bạn.</i>"
    )
    kb = InlineKeyboardMarkup([
        [_btn(lt(user_id, "Nạp Ví", "Top up wallet", "充值钱包"), icon_id="5278467510604160626", callback_data="api_member_wallet")],
        [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
    ])
    await safe_send_message(
        context,
        chat_id,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return True


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return
    query = update.callback_query
    command = getattr(query, "data", "") if query else ""
    user_id = update.effective_user.id if update.effective_user else 0
    logger.info(f"[CALLBACK] user={user_id} data={command}")

    # Kiểm tra chế độ bảo trì
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await safe_answer(update.callback_query, "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> Hệ thống đang bảo trì!", show_alert=True)
        return

    # Check Store Callback
    if await handle_store_callback(update, context):
        return

    # Check Admin Menu Callbacks

    # Check Admin Quick Action Callbacks (from /info panel)

    # Check Admin Quick Action Callbacks (from /info panel)

    # Check Admin History Refund Callbacks (Full vs Prorate)

    # Check API Manual Order Callbacks (Admin only) - Approve/Refund for API partner orders

    # Check Manual Order Callbacks (Admin only)


    # Check Rate Limit
    if not await check_rate_limit(update.effective_user.id):
        try: await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Thao tác quá nhanh!", show_alert=False)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.debug(f"Cannot answer rate-limit callback for user {update.effective_user.id}: {e}")
        return

    command, user_id = query.data, update.effective_user.id
    # Navigation callbacks should stop Telegram's loading spinner before any
    # rendering or I/O. Actions that may need a success/error alert opt out via
    # _callback_requires_manual_answer and answer at the decision point.
    if not _callback_requires_manual_answer(command):
        await safe_answer(query)

    if await handle_admin_callbacks(update, context, command): return
    if await handle_games_callbacks(update, context, command): return

    # Centralized permission gate for sensitive admin callbacks
    admin_only_prefixes = (
        'approve_withdraw:',
        'reject_withdraw:',
        'approve_warranty:',
        'reject_warranty:',
        'approve_api:',
        'reject_api:',
        'manual_done:',
        'manual_refund:',
        'manual_done_',
        'manual_refund_',
        'admin_open_chat:',
        'admin_close_chat:',
        'reply_to_ticket:',
        'replace_auto:',
        'replace_manual:',
        'reject_expired:',
        'reject_policy:',
        'dismiss_report:',
        'warranty_done:',
    )


    if command == 'back_to_main':
        # CHECK REFUND PENDING ORDERS
        user_pending_order, _ = await get_user_pending_order(user_id)
        if user_pending_order:
            details = await pending_pop(user_pending_order)
            if not details:
                await clear_user_state(context)
                return
            balance_used = details.get('balance_used', 0)
            if balance_used > 0:
                user_info = user_data_db.get(str(user_id))
                if user_info:
                    new_balance = user_info.get('balance', 0) + balance_used
                    db_update_balance(user_id, new_balance)
                    try:
                        await safe_send_message(
                            context,
                            user_id,
                            f"<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>Đã hoàn lại:</b> +{balance_used:,} VNĐ vào ví (Do hủy đơn).",
                            parse_mode=ParseMode.HTML
                        )
                    except (TelegramError, ValueError, KeyError, AttributeError) as e:
                        logger.debug(f"Cannot notify refunded balance while leaving checkout: {e}")
            await save_data(force=True, tables=[PENDING_ORDERS_FILE, USERS_FILE, TRANSACTION_HISTORY_FILE])

        await clear_user_state(context)

        # Send main menu to private chat when possible.
        # If user has never started private chat, Telegram returns Forbidden.
        try:
            await context.bot.send_message(
                user_id,
                get_main_menu_text(user_id=user_id),
                parse_mode=ParseMode.HTML,
                reply_markup=create_main_menu(user_id=user_id)
            )
            try:
                await query.delete_message()
            except BadRequest:
                pass
        except Forbidden:
            deep_link = f"https://t.me/{BOT_USERNAME}?start=start"
            fallback_text = (
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Không thể nhắn riêng cho bạn.</b>\n\n"
                "Vui lòng mở chat riêng với bot và gửi <code>/start</code> trước,\n"
                "sau đó quay lại thao tác này."
            )
            fallback_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("<tg-emoji emoji-id=\"6129860303619363484\">📩</tg-emoji> Mở chat bot", url=deep_link)]
            ])
            try:
                await safe_edit_message(
                    query,
                    text=fallback_text,
                    parse_mode='HTML',
                    reply_markup=fallback_kb
                )
            except BadRequest:
                pass
            return

    elif command == 'language_menu':
        current = get_user_lang(user_id)
        await safe_edit_message(
            query,
            text=t("lang_menu_title", user_id=user_id, current=lang_display_name(current, user_id=user_id)),
            parse_mode='HTML',
            reply_markup=create_language_menu(user_id=user_id),
        )
        return

    elif command.startswith('set_lang:'):
        new_lang = set_user_lang(user_id, command.split(':', 1)[1])
        await save_data(force=True, tables=[USERS_FILE])
        await safe_answer(
            query,
            t("lang_changed", user_id=user_id, lang=lang_display_name(new_lang, user_id=user_id)).replace('<b>', '').replace('</b>', ''),
            show_alert=False,
        )
        try:
            await context.bot.send_message(
                user_id,
                f"{t('lang_changed', user_id=user_id, lang=lang_display_name(new_lang, user_id=user_id))}\n\n{get_main_menu_text(user_id=user_id)}",
                parse_mode=ParseMode.HTML,
                reply_markup=create_main_menu(user_id=user_id),
            )
            try:
                await query.delete_message()
            except BadRequest:
                pass
        except Forbidden:
            await safe_edit_message(
                query,
                text=f"{t('lang_changed', user_id=user_id, lang=lang_display_name(new_lang, user_id=user_id))}\n\n{get_main_menu_text(user_id=user_id)}",
                parse_mode='HTML',
                reply_markup=create_main_menu(user_id=user_id),
            )
        return

    elif command == 'guide_baoloi_menu':
        await huongdan_baoloi_command(update, context)
        return

    elif command == 'withdraw_request':
        context.user_data.pop('state', None)
        context.user_data.pop('withdrawal_amount', None)
        await safe_answer(query, "Tính năng rút tiền đã được tắt. Số dư chỉ dùng để mua hàng.", show_alert=True)
        return

    elif command.startswith('refund_bank:'):
        await begin_bank_refund_request(query, context, command)
        return


    # ===== LUCKY WHEEL CALLBACKS =====


    # ===== ADVANCED FEATURES CALLBACKS =====
    elif command == 'my_stats':
        await show_my_stats(update, context, is_callback=True)

    elif command == 'topup_start':
        await start_user_topup_flow(update, context, is_callback=True)

    elif command.startswith('topup_pay:'):
        await handle_topup_method_choice(update, context, command.split(':', 1)[1])

    elif command.startswith('topup_rpaynet:'):
        await handle_topup_network_choice(update, context, command.split(':', 1)[1])

    elif command.startswith('topup_cancel:'):
        await cancel_user_topup(update, context, command.split(':', 1)[1])

    elif command == 'my_referral':
        await show_my_referral(update, context, is_callback=True)

    elif command == 'top_referrers':
        await show_top_referrers(update, context, is_callback=True)

    # ===== NEW FEATURES CALLBACKS (RATING / WARRANTY / CHAT) =====
    elif command == 'join_ga_action':
        # Derive GA ID from message
        ga_key = f"{query.message.chat.id}_{query.message.message_id}"

        if ga_key not in active_giveaways:
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Giveaway này đã kết thúc hoặc bị xóa!", show_alert=True)
            return

        ga = active_giveaways[ga_key]
        if ga['status'] != 'active':
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Giveaway đã kết thúc!", show_alert=True)
            return

        # Normalize participants to support both old format
        # (list of {"id": ...}) and new format (list of int/str user_id).
        raw_participants = ga.get('participants', [])
        normalized_participants = []
        for participant in raw_participants:
            pid = participant.get('id') if isinstance(participant, dict) else participant
            try:
                normalized_participants.append(int(pid))
            except (TypeError, ValueError):
                continue

        # De-duplicate and persist normalized structure
        ga['participants'] = list(dict.fromkeys(normalized_participants))

        if user_id in ga['participants']:
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đã tham gia rồi!", show_alert=True)
            return

        # Add participant
        ga['participants'].append(user_id)
        await save_data()

        await safe_answer(query, "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Tham gia thành công! Chúc may mắn!", show_alert=True)

        # Update UI count (Debounced preferred but simple edit here)
        try:
            ud = ga
            end_ts = ud.get('end_time', 0)
            end_str = datetime.fromtimestamp(end_ts).strftime('%H:%M %d/%m') if end_ts > 0 else "Khi Admin kết thúc"

            msg_text = (
                f"<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>SỰ KIỆN GIVEAWAY: {ud.get('title', 'EVENT').upper()}</b> <tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>\n\n"
                f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Phần thưởng:</b> {ud.get('prize_qty', 1)}x {ud.get('prize_name', 'Món quà bí ẩn')}\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>Kết thúc:</b> {end_str}\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>Người tham gia:</b> {len(ga['participants'])}\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> <i>Bấm nút bên dưới để thử vận may!</i>"
            )

            await query.edit_message_caption(caption=msg_text, parse_mode='HTML', reply_markup=query.message.reply_markup)
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass # Ignore if edit fails (e.g., race condition)

    elif command.startswith('claim_warranty:'):
        order_code = command.split(':', 1)[1]
        order = order_index.get(order_code)
        if order and order['user_id'] == user_id:
            if await _auto_reject_expired_support_message(query.message, context, order, order_code):
                await safe_answer(query, "Don nay da het han bao hanh.", show_alert=True)
                return
            context.user_data['warranty_claim_order'] = order_code
            context.user_data['state'] = 'awaiting_warranty_description'
            await query.edit_message_text(
                lt(
                    user_id,
                    "<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>YÊU CẦU BẢO HÀNH</b>\n\nVui lòng <b>mô tả vấn đề</b> bạn gặp phải:\n<i>(Gửi tin nhắn mô tả chi tiết)</i>",
                    "<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>WARRANTY REQUEST</b>\n\nPlease <b>describe the problem</b> you ran into:\n<i>(Send a message with the details)</i>",
                    "<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>质保申请</b>\n\n请<b>描述您遇到的问题</b>：\n<i>（发送一条包含详细信息的消息）</i>",
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(lt(user_id, "❌ Hủy", "❌ Cancel", "❌ 取消"), callback_data="main_menu")]])
            )

    elif command == 'open_live_chat':
        user_id_str = str(user_id)
        if user_id_str not in live_chats:
            live_chats[user_id_str] = {'messages': [], 'status': 'active', 'last_activity': time.time(), 'unread_by_admin': 0}
        context.user_data['state'] = 'in_live_chat'
        chat = live_chats[user_id_str]
        msg = f'<tg-emoji emoji-id="6129860303619363484">💬</tg-emoji> <b>{t("live_chat_title", user_id=user_id)}</b>\n\n'
        recent_msgs = chat['messages'][-10:]
        for m in recent_msgs:
            from_who = (
                f'<tg-emoji emoji-id="5350778980158956492">🧑</tg-emoji> {t("live_chat_you", user_id=user_id)}'
                if m['from'] == 'user'
                else f'<tg-emoji emoji-id="5350778980158956492">👨</tg-emoji>‍<tg-emoji emoji-id="5854908544712707500">💼</tg-emoji> {t("live_chat_admin", user_id=user_id)}'
            )
            time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
            msg += f"{from_who} ({time_str}):\n{m['text']}\n\n"
        if not recent_msgs:
            msg += f'<i>{t("live_chat_empty", user_id=user_id)}</i>\n\n'
        msg += f'<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> {t("live_chat_prompt", user_id=user_id)}'
        btns = [[InlineKeyboardButton(f'❌ {t("live_chat_close", user_id=user_id)}', callback_data="close_live_chat")]]
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

    elif command == 'close_live_chat':
        await clear_user_state(context)
        await query.edit_message_text(t("live_chat_closed", user_id=user_id), reply_markup=create_main_menu(user_id=user_id))

    elif command == 'lienhe_admin':
        try: await query.delete_message()
        except (Forbidden, BadRequest) as e:
            logger.debug(f"Cannot delete callback message before opening live chat: {e}")
        user_id_str = str(user_id)
        if user_id_str not in live_chats:
            live_chats[user_id_str] = {'messages': [], 'status': 'active', 'last_activity': time.time(), 'unread_by_admin': 0}
        context.user_data['state'] = 'in_live_chat'
        chat = live_chats[user_id_str]
        msg = f'<tg-emoji emoji-id="6129860303619363484">💬</tg-emoji> <b>{t("live_chat_title", user_id=user_id)}</b>\n\n'
        recent_msgs = chat['messages'][-10:]
        for m in recent_msgs:
            from_who = (
                f'<tg-emoji emoji-id="5350778980158956492">🧑</tg-emoji> {t("live_chat_you", user_id=user_id)}'
                if m['from'] == 'user'
                else f'<tg-emoji emoji-id="5350778980158956492">👨</tg-emoji>‍<tg-emoji emoji-id="5854908544712707500">💼</tg-emoji> {t("live_chat_admin", user_id=user_id)}'
            )
            time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
            msg += f"{from_who} ({time_str}):\n{m['text']}\n\n"
        if not recent_msgs:
            msg += f'<i>{t("live_chat_empty", user_id=user_id)}</i>\n\n'
        msg += f'<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> {t("live_chat_prompt", user_id=user_id)}'
        btns = [[InlineKeyboardButton(f'❌ {t("live_chat_close", user_id=user_id)}', callback_data="close_live_chat")]]
        await safe_send_message(context, user_id, msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

    elif command in {'api_register_request', 'api_register_guide'}:
        if command == 'api_register_guide':
            text = (
                "<tg-emoji emoji-id=\"5350481781306958339\">📘</tg-emoji> <b>HƯỚNG DẪN ĐĂNG KÝ API PARTNER</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "1. Nhấn nút <b>Gửi yêu cầu đăng ký</b> bên dưới.\n"
                "2. Chờ Admin duyệt tài khoản.\n"
                "3. Bot gửi API Key cho bạn qua tin nhắn.\n"
                "4. Nạp ví bằng lệnh <code>/napapi [số_tiền]</code>.\n"
                "5. Vào lại <code>/start</code> để thấy menu <b>API Partner</b>.\n\n"
                "<i>Menu API chỉ hiện sau khi được Admin duyệt.</i>"
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Gửi yêu cầu đăng ký", "Send a registration request", "提交注册申请"), icon_id="5436359785534466562", callback_data="api_register_request")],
                [_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="back_to_main")]
            ])
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        await safe_answer(query)
        fake_update = update_from_callback(query)
        await dkyapi_command(fake_update, context)
        return

    elif command in {'api_member_menu', 'api_member_wallet', 'api_member_docs', 'api_member_topup_help', 'api_member_endpoints', 'api_member_rotate_key'}:
        partner_key, partner_data = get_partner_api_entry_by_user(user_id)
        if not partner_key or not isinstance(partner_data, dict):
            await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> Bạn chưa được Admin duyệt API.", show_alert=True)
            return
        await safe_answer(query)

        partner_name = partner_data.get("name", "Partner")
        partner_balance = _api_get_partner_display_balance(partner_key, partner_data)
        base_url = get_public_api_base_url()
        docs_url = f"{base_url.rstrip('/')}/docs"
        safe_docs_url = html.escape(docs_url, quote=True)
        if command == 'api_member_topup_help':
            command = 'api_member_wallet'

        if command == 'api_member_rotate_key':
            user_data = getattr(context, 'user_data', None)
            if not isinstance(user_data, dict):
                await _complete_partner_api_key_rotation(
                    context,
                    query.message.chat_id,
                    user_id,
                    partner_key,
                    partner_data,
                    source_chat_id=getattr(query.message, 'chat_id', None),
                    source_message_id=getattr(query.message, 'message_id', None),
                )
                return

            user_data['state'] = 'awaiting_api_rotate_confirmation'
            user_data['api_rotate_source_key'] = str(partner_key or "")
            user_data['api_rotate_source_chat_id'] = query.message.chat_id
            user_data['api_rotate_source_message_id'] = getattr(query.message, 'message_id', None)
            sent_confirmation = await safe_send_message(
                context,
                query.message.chat_id,
                (
                    f"{API_PREM_WARN} "
                    "<b>XÁC NHẬN ĐỔI API KEY</b>\n\n"
                    "Để tránh bấm nhầm, hãy nhập <code>sure</code> vào chat để xác nhận đổi key.\n"
                    "Nếu không muốn đổi nữa, hãy gõ <code>/cancel</code>."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
                ]),
            )
            if sent_confirmation:
                user_data['api_rotate_confirm_chat_id'] = sent_confirmation.chat_id
                user_data['api_rotate_confirm_message_id'] = sent_confirmation.message_id
            return

            current_balance = _api_get_partner_display_balance(partner_key, partner_data)
            old_key = str(partner_key or "").strip()
            new_key = f"sk_live_{secrets.token_hex(16)}"
            while new_key in api_keys:
                new_key = f"sk_live_{secrets.token_hex(16)}"

            rotation_ts = int(time.time())
            old_partner_snapshot = dict(partner_data)
            new_partner_data = dict(partner_data)
            new_partner_data["balance"] = current_balance
            new_partner_data["enabled"] = True
            new_partner_data["rotated_from"] = old_key
            new_partner_data["rotated_at"] = rotation_ts
            partner_data["balance"] = current_balance
            partner_data["enabled"] = False
            partner_data["rotated_to"] = new_key
            partner_data["rotated_at"] = rotation_ts
            api_keys[new_key] = new_partner_data

            updated_pending_refs = []
            for pending_details in pending_api_deposits.values():
                if not isinstance(pending_details, dict):
                    continue
                try:
                    pending_user_id = int(pending_details.get("user_id", 0) or 0)
                except (TypeError, ValueError):
                    pending_user_id = 0
                if pending_user_id != user_id:
                    continue
                pending_details["api_key"] = new_key
                pending_details["partner_name"] = partner_name
                updated_pending_refs.append(pending_details)

            await save_data(force=True, tables=[API_KEYS_FILE, "data_pending_api_deposits.json"])
            resolved_key, resolved_partner_data = get_partner_api_entry_by_user(user_id)
            if resolved_key != new_key or not isinstance(resolved_partner_data, dict):
                api_keys.pop(new_key, None)
                partner_data.clear()
                partner_data.update(old_partner_snapshot)
                for pending_details in updated_pending_refs:
                    pending_details["api_key"] = old_key
                    pending_details["partner_name"] = partner_name
                await save_data(force=True, tables=[API_KEYS_FILE, "data_pending_api_deposits.json"])
                logger.error("API key rotation failed for user %s", user_id)
                await safe_send_message(
                    context,
                    query.message.chat_id,
                    (
                        "❌ "
                        "<b>Không thể hoàn tất đổi API key.</b>\n\n"
                        "Hệ thống đã giữ nguyên key cũ để tránh gián đoạn. Hãy thử lại sau."
                    ),
                    parse_mode=ParseMode.HTML,
                )
                return

            logger.info("API key rotated for user %s", user_id)

            text = (
                "\U0001F511 <b>ĐÃ ĐỔI API KEY</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"\U0001F464 <b>Partner:</b> {html.escape(str(partner_name))}\n"
                f"\U0001F6E1 <b>API Key mới:</b> <code>{new_key}</code>\n"
                f"\U0001F4B0 <b>Số dư ví chung:</b> {current_balance:,} VNĐ\n\n"
                "<i>\u26A0\uFE0F API key cũ đã bị vô hiệu hóa để bảo mật. Hãy cập nhật key mới trong hệ thống của bạn.</i>"
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Nạp Ví", "Top up wallet", "充值钱包"), icon_id="5278467510604160626", callback_data="api_member_wallet")],
                [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            from app.core.emoji_runtime import upgrade_text_to_premium_emoji
            await safe_send_message(
                context,
                query.message.chat_id,
                upgrade_text_to_premium_emoji(text),
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            return

        if command == 'api_member_menu':
            text = lt(
                user_id,
                "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>MENU API PARTNER (THÀNH VIÊN)</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư ví chung:</b> {balance:,} VNĐ\n\n<b>Full lệnh/API cho thành viên:</b>\n• <code>/napapi [số_tiền]</code> - tạo QR nạp ví chung\n• <code>/lichsu</code> - xem lịch sử đơn thường + đơn API\n• <code>GET /api/v2/me</code> - kiểm tra key + số dư\n• <code>GET /api/v2/catalog</code> - lấy danh mục sản phẩm\n• <code>GET /api/v2/orders</code> - lấy lịch sử đơn API\n• <code>POST /api/v2/orders</code> - tạo đơn mua\n• <code>GET /api/v2/orders/{{order_code}}</code> - tra cứu đơn\n• <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - tra theo mã đối tác\n\n<i>Menu này chỉ hiển thị khi tài khoản đã được Admin duyệt API.</i>",
                "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>API PARTNER MENU (MEMBER)</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Shared wallet balance:</b> {balance:,} VND\n\n<b>Member commands/API:</b>\n• <code>/napapi [amount]</code> - create a shared-wallet top-up QR\n• <code>/lichsu</code> - view regular and API orders\n• <code>GET /api/v2/me</code> - verify key and balance\n• <code>GET /api/v2/catalog</code> - get product catalog\n• <code>GET /api/v2/orders</code> - get API order history\n• <code>POST /api/v2/orders</code> - create an order\n• <code>GET /api/v2/orders/{{order_code}}</code> - look up an order\n• <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - look up by partner reference\n\n<i>This menu appears only after Admin approves API access.</i>",
                "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>API 合作伙伴菜单（成员）</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>合作伙伴：</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key：</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>共享钱包余额：</b> {balance:,} VND\n\n<b>成员命令/API：</b>\n• <code>/napapi [金额]</code> - 创建共享钱包充值二维码\n• <code>/lichsu</code> - 查看普通订单和 API 订单\n• <code>GET /api/v2/me</code> - 检查密钥和余额\n• <code>GET /api/v2/catalog</code> - 获取商品目录\n• <code>GET /api/v2/orders</code> - 获取 API 订单历史\n• <code>POST /api/v2/orders</code> - 创建订单\n• <code>GET /api/v2/orders/{{order_code}}</code> - 查询订单\n• <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - 按合作伙伴编号查询\n\n<i>仅在管理员批准 API 权限后显示此菜单。</i>",
                partner=html.escape(str(partner_name)), key=partner_key, balance=partner_balance,
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Ví Chung", "Shared Wallet", "共享钱包"), icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn(lt(user_id, "Lịch Sử", "History", "历史"), icon_id="5444856076954520455", callback_data="lichsu_entry")],
                [_btn(lt(user_id, "Nạp Ví", "Top Up", "充值"), icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn(lt(user_id, "Tài Liệu API", "API Docs", "API 文档"), icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
                [_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="back_to_main")]
            ])
            if getattr(query.message, "photo", None):
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            else:
                await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        if command == 'api_member_wallet':
            qr_url, transfer_content = await create_partner_api_topup_request(
                partner_key,
                partner_name,
                user_id,
            )
            caption = lt(
                user_id,
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>QR NẠP VÍ CHUNG</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Số dư hiện tại:</b> {balance:,} VNĐ\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung CK:</b> <code>{content}</code>\n\n<b>Quét QR rồi nhập số tiền bạn muốn nạp trong app ngân hàng.</b>\n\n<i>Hệ thống sẽ tự cộng tiền khi nhận được giao dịch có nội dung đúng Telegram ID của bạn.</i>",
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>SHARED WALLET TOP-UP QR</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Current balance:</b> {balance:,} VND\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Transfer content:</b> <code>{content}</code>\n\n<b>Scan the QR and enter your top-up amount in your banking app.</b>\n\n<i>The system credits your wallet automatically when the transfer content matches your Telegram ID.</i>",
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>共享钱包充值二维码</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> <b>合作伙伴：</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key：</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>当前余额：</b> {balance:,} VND\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>转账内容：</b> <code>{content}</code>\n\n<b>扫描二维码，然后在银行应用中输入充值金额。</b>\n\n<i>收到转账内容与您的 Telegram ID 匹配的交易后，系统将自动入账。</i>",
                partner=html.escape(str(partner_name)), key=partner_key,
                balance=partner_balance, content=transfer_content,
            )
            kb = InlineKeyboardMarkup([[
                _btn(lt(user_id, "Đổi API Key", "Rotate API Key", "更换 API Key"), icon_id="5352716320093695452", callback_data="api_member_rotate_key"),
                _btn(lt(user_id, "Quay lại menu API", "Back to API Menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")
            ]])
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=qr_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            return

        if command == 'api_member_topup_help':
            text = (
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>HƯỚNG DẪN NẠP VÍ CHUNG</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "1. Gõ lệnh: <code>/napapi [số_tiền]</code>\n"
                "2. Bot trả về QR + nội dung chuyển khoản (NAPI...)\n"
                "3. Chuyển đúng số tiền và đúng nội dung\n"
                "4. Chờ 1-3 phút hệ thống tự cộng vào ví chung\n\n"
                "<b>Ví dụ:</b>\n"
                "• <code>/napapi 200000</code>\n"
                "• <code>/napapi 500000</code>"
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Ví Chung", "Shared wallet", "共享钱包"), icon_id="5278467510604160626", callback_data="api_member_wallet")],
                [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        base_url_note = (
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Link hiện tại là Cloudflare Quick Tunnel.</b> Nếu server restart hoặc mở lại cloudflared thì URL có thể đổi.\n\n"
            if "trycloudflare.com" in base_url
            else "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Link này đang lấy từ cấu hình PUBLIC_API_URL hiện tại.</b>\n\n"
        )

        if command == 'api_member_endpoints':
            text = (
                "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> <b>DANH SÁCH ENDPOINT PARTNER</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
                f"{base_url_note}"
                f"<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Tài liệu Web:</b> "
                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
                "<b>Sản phẩm thường:</b>\n"
                "• <code>GET /api/v2/me</code>\n"
                "• <code>GET /api/v2/catalog</code>\n"
                "• <code>POST /api/v2/orders</code>\n"
                "• <code>GET /api/v2/orders/{order_code}</code>\n\n"
                "<b>Headers dùng chung:</b>\n"
                f"• <code>x-api-key: {partner_key}</code>\n"
                "• <code>x-idempotency-key: MA_DON_DOI_TAC</code>\n\n"
                "<b>Mã phản hồi:</b> <code>200</code> OK · <code>400</code> sai endpoint/field · <code>401</code> sai key · <code>402</code> thiếu tiền · <code>404</code> không tìm thấy"
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "Tài Liệu API", "API documentation", "API 文档"), icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        if command == 'api_member_docs':
            guide_sent = False
            guide_status = (
                "<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> "
                "<b>Mình đã gửi file tài liệu chi tiết ở tin nhắn bên dưới.</b>\n\n"
            )
            try:
                from telegram import InputFile
                from app.core.section_manifest import PROJECT_ROOT

                guide_path = PROJECT_ROOT / "docs" / "API_PARTNER_GUIDE.md"
                if guide_path.exists():
                    with guide_path.open("rb") as guide_stream:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=InputFile(guide_stream, filename="API_PARTNER_GUIDE.md"),
                            caption=(
                                "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> "
                                "<b>Tài liệu API Partner chi tiết</b>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> "
                                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n"
                                "<i>File này có ví dụ tạo đơn, poll đơn, nhận sản phẩm, quantity và các response mẫu.</i>"
                            ),
                            parse_mode='HTML',
                        )
                    guide_sent = True
            except (TelegramError, OSError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Cannot send API partner guide document to user {user_id}: {e}")

            if not guide_sent:
                guide_status = (
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
                    "<b>Chưa gửi được file tài liệu.</b> Bạn vẫn có thể xem bản tóm tắt bên dưới.\n\n"
                )

            text = (
                "<tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji> <b>TÀI LIỆU API DÀNH CHO THÀNH VIÊN</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"{guide_status}"
                f"<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
                f"{base_url_note}"
                f"<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Tài liệu Web:</b> "
                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
                f"<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key của bạn:</b> <code>{partner_key}</code>\n\n"
                "<b>Gọi API cần các header:</b>\n"
                f"• <code>x-api-key: {partner_key}</code>\n"
                "• <code>x-idempotency-key: MA_DON_DOI_TAC</code> (khuyến nghị)\n\n"
                "<b>Luồng tích hợp:</b>\n"
                "1. <code>GET /api/v2/catalog</code> → <code>POST /api/v2/orders</code>\n"
                "3. Đơn poll tại <code>/api/v2/orders/{order_code}</code>\n"
                "4. Retry phải giữ nguyên partner_ref\n\n"
                "<b>Ghi nhớ:</b>\n"
                "• Sản phẩm thường giao ngay nằm trong <code>data.items</code>\n"
                "• Retry phải giữ nguyên <code>partner_ref</code> và <code>x-idempotency-key</code>\n"
                "• Gặp <code>402</code>: nạp ví bằng <code>/napapi [số_tiền]</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(lt(user_id, "Mở tài liệu Web", "Open the web documentation", "打开网页文档"), url=docs_url)],
                [_btn(lt(user_id, "Ví Chung", "Shared wallet", "共享钱包"), icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
                [_btn(lt(user_id, "Gửi lại tài liệu", "Resend the documentation", "重新发送文档"), icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        # command == 'api_member_docs'
        text = (
            "<tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji> <b>TÀI LIỆU API DÀNH CHO THÀNH VIÊN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
            f"{base_url_note}"
            f"<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Tài liệu Web:</b> "
            f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key của bạn:</b> <code>{partner_key}</code>\n\n"
            "<b>Headers khi gọi API:</b>\n"
            f"• <code>x-api-key: {partner_key}</code>\n"
            "• <code>x-idempotency-key: MA_DON_DOI_TAC</code> (khuyến nghị)\n\n"
            "<b>Mẫu cURL mua đơn AUTO (Tài khoản có sẵn):</b>\n"
            "<pre>curl -X POST " + f"{base_url}/api/v2/orders" + " \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -H 'x-api-key: " + f"{partner_key}" + "' \\\n"
            "  -H 'x-idempotency-key: ORDER_12345' \\\n"
            "  -d '{\n"
            '    "partner_ref": "ORDER_12345",\n'
            '    "product_id": "p_1700000000",\n'
            '    "quantity": 1,\n'
            '    "customer_id": "telegram_9988",\n'
            '    "note": "don tu bot doi tac"\n'
            "  }'</pre>\n\n"
            "<b>Mẫu cURL mua đơn MANUAL (Yêu cầu nhập mail):</b>\n"
            "<pre>curl -X POST " + f"{base_url}/api/v2/orders" + " \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -H 'x-api-key: " + f"{partner_key}" + "' \\\n"
            "  -H 'x-idempotency-key: ORDER_12346' \\\n"
            "  -d '{\n"
            '    "partner_ref": "ORDER_12346",\n'
            '    "product_id": "p_1700000001",\n'
            '    "quantity": 1,\n'
            '    "customer_email": "khach@example.com",\n'
            '    "customer_id": "telegram_9988",\n'
            '    "note": "youtube premium cho khach"\n'
            "  }'</pre>\n"
            "<b>Test nhanh (Dành cho Shell/cURL):</b>\n"
            "<pre>curl -X GET " + f"{base_url}/api/v2/me" + "\\\n"
            "  -H 'x-api-key: " + f"{partner_key}" + "'</pre>\n\n"
            "<b>Kết quả test mẫu (thực tế):</b>\n"
            "• <code>GET /api/v2/status -> 200 OK</code>\n"
            "• <code>GET /api/v2/me -> 200 OK</code>\n"
            "• <code>GET /api/v2/catalog -> 200 OK</code>\n"
            "• <code>GET /api/v2/orders -> 200 OK</code>\n"
            "• <code>POST /api/v2/orders -> 402 Payment Required</code> (khi ví chung = 0)\n"
            "• Cách xử lý: nạp ví chung bằng <code>/napapi [số_tiền]</code> rồi gọi lại đơn.\n\n"
            "<b>Nội dung tài khoản trả về:</b>\n"
            "• Đọc ở <code>data.items</code>\n"
            "• Thường dạng <code>email|password</code>\n"
            "• Nếu đơn manual/pending thì chưa có items ngay"
        )
        kb = InlineKeyboardMarkup([
            [_btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
            [_btn(lt(user_id, "Quay lại menu API", "Back to API menu", "返回 API 菜单"), icon_id="6206032691075223572", callback_data="api_member_menu")]
        ])
        await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
        return

    elif command in {'huongdan', 'chinhsach'}:
        is_guide = command == "huongdan"
        menu = create_guide_policy_menu("guide" if is_guide else "policy", user_id=user_id)
        full_text = get_guide_text(user_id) if is_guide else get_policy_text(user_id)
        if len(full_text) <= 4000:
            await safe_edit_message(
                query,
                text=full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=menu,
            )
        else:
            # Text quá dài cho edit_message_text (limit 4096) → gửi tin mới
            try:
                await safe_edit_message(
                    query,
                    text='<tg-emoji emoji-id="5350481781306958339">📚</tg-emoji> '
                         '<b>Xem nội dung chi tiết ở tin nhắn bên dưới.</b>',
                    parse_mode=ParseMode.HTML,
                    reply_markup=menu,
                )
            except Exception:
                pass
            await safe_send_message(
                context,
                query.message.chat_id,
                full_text,
                parse_mode=ParseMode.HTML,
            )
    elif command == 'lichsu_entry':
        try: await query.delete_message()
        except (Forbidden, BadRequest) as e:
            logger.debug(f"Cannot delete callback message for lichsu_entry: {e}")
        await lichsu_command(update, context, is_callback=True)
    elif command.startswith('lichsu_page:'):
        try:
            requested_page = int(command.split(':', 1)[1])
        except (ValueError, IndexError):
            requested_page = 0
        await lichsu_command(update, context, is_callback=True, page=requested_page)

    elif command.startswith('buy_again:'):
        repurchase_payload = command.split(':', 1)[1]
        order_code, separator, history_page_raw = repurchase_payload.rpartition(':')
        if not separator:
            order_code = repurchase_payload
            history_page_raw = "0"
        try:
            history_page = max(0, int(history_page_raw or 0))
        except ValueError:
            history_page = 0

        order = find_order_by_code_or_supplier_id(order_code)
        if not order or not _api_user_can_access_order(user_id, order):
            await safe_answer(query, lt(user_id, "Không tìm thấy đơn hàng.", "Order not found.", "未找到订单。"), show_alert=True)
            return
        if _api_is_order_record(order):
            await safe_answer(query, lt(user_id, "Đơn API Partner cần mua lại qua API.", "API Partner orders must be reordered through the API.", "API 合作伙伴订单需要通过 API 重新购买。"), show_alert=True)
            return

        product_id, current_product = _resolve_repurchase_product(order)
        if not product_id or not isinstance(current_product, dict):
            await safe_answer(
                query,
                lt(
                    user_id,
                    "Sản phẩm này đã ngừng bán hoặc không còn trong cửa hàng.",
                    "This product is no longer available in the store.",
                    "该商品已停售或不再存在于商店中。",
                ),
                show_alert=True,
            )
            return

        await safe_answer(query, lt(user_id, "Đang kiểm tra giá và tồn kho mới...", "Checking the latest price and stock...", "正在检查最新价格和库存……"))
        await _show_store_product_detail(
            query,
            context,
            product_id,
            back_callback_data=f"view_order_history_{order_code}:{history_page}",
            back_button_text=lt(user_id, "Quay lại đơn hàng", "Back to Order", "返回订单"),
            already_answered=True,
        )
        return

    # NEW: Handle Resend Link (Admin Action)

    # NEW: Admin reject warranty (Block Spam)







    # NEW: Handle Replace Auto (Admin Action)

    elif command.startswith('view_order_history_'):
        order_payload = command.replace('view_order_history_', '', 1)
        order_code, _, history_page_raw = order_payload.partition(':')
        try:
            history_page = int(history_page_raw) if history_page_raw else 0
        except ValueError:
            history_page = 0

        # FIX: Dùng index O(1)
        order = find_order_by_code_or_supplier_id(order_code)

        if not order:
            await safe_answer(query, lt(user_id, "Đơn hàng không tồn tại", "Order not found", "订单不存在"), show_alert=True)
            await lichsu_command(update, context, is_callback=True, page=history_page)
            return

        if not _api_user_can_access_order(user_id, order):
            await safe_answer(query, lt(user_id, "Bạn không có quyền xem đơn này", "You cannot access this order", "您无权查看此订单"), show_alert=True)
            return
        if order.get('refunded_at'):
            await safe_answer(query, lt(user_id, "Đơn hàng đã được hoàn tiền và không thể xem lại", "This order was refunded and can no longer be viewed", "此订单已退款，无法再次查看"), show_alert=True)
            return

        await safe_answer(query)

        # Format details
        ts = order.get('timestamp', 0)
        time_str = datetime.fromtimestamp(ts).strftime('%H:%M %d/%m/%Y') if ts else "N/A"
        amount = order.get('amount', 0)
        status = status_text(order.get('status'))

        detail_msg = lt(
            user_id,
            '🔎 <b>CHI TIẾT ĐƠN HÀNG</b>\n\n🔸 <b>Mã đơn:</b> <code>{code}</code>\n✍️ <b>Thời gian:</b> {time}\n🏷 <b>Thanh toán:</b> {amount:,} VNĐ\n📊 <b>Trạng thái:</b> {status}\n',
            '🔎 <b>ORDER DETAILS</b>\n\n🔸 <b>Order code:</b> <code>{code}</code>\n✍️ <b>Time:</b> {time}\n🏷 <b>Payment:</b> {amount:,} VND\n📊 <b>Status:</b> {status}\n',
            '🔎 <b>订单详情</b>\n\n🔸 <b>订单号：</b> <code>{code}</code>\n✍️ <b>时间：</b> {time}\n🏷 <b>付款：</b> {amount:,} VND\n📊 <b>状态：</b> {status}\n',
            code=order_code, time=time_str, amount=amount, status=status,
        )

        is_api_order = _api_is_order_record(order)
        if is_api_order:
            detail_msg += lt(user_id, '🔌 <b>Nguồn:</b> API Partner\n', '🔌 <b>Source:</b> API Partner\n', '🔌 <b>来源：</b> API Partner\n')

        item_name = get_order_item_name(order)
        detail_msg += lt(user_id, '\n🏷 <b>Sản phẩm:</b> {item}\n0️⃣ <b>Số lượng:</b> {quantity}\n', '\n🏷 <b>Product:</b> {item}\n0️⃣ <b>Quantity:</b> {quantity}\n', '\n🏷 <b>商品：</b> {item}\n0️⃣ <b>数量：</b> {quantity}\n', item=html.escape(item_name), quantity=order.get('quantity', 1))
        if order.get('email') and order.get('email') != "N/A":
            detail_msg += f'🌐 <b>Email:</b> <code>{html.escape(str(order.get("email")))}</code>\n'

        link_value = str(order.get("link") or "")
        delivery_mode = str(order.get("delivery_method") or "")
        placeholder_links = {"Store Product", "Sản phẩm khác"}
        should_show_link = bool(link_value) and (
            delivery_mode == "instant_link"
            or (link_value not in placeholder_links and not link_value.startswith("Manual - "))
        )
        if should_show_link:
             detail_msg += f'\n<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Link:</b> <code>{html.escape(link_value)}</code>\n'

        delivered_items = order.get("items")
        delivered_count = len(delivered_items) if isinstance(delivered_items, list) else 0
        if delivered_count:
            detail_msg += (
                f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Nội dung đã lưu:</b> {delivered_count} item\n'
            )

        if is_api_order:
            partner_ref = str(order.get("api_partner_ref") or "")
            customer_id = str(order.get("api_customer_id") or "")
            customer_email = str(order.get("api_customer_email") or order.get("email") or "")
            api_note = str(order.get("api_note") or "")
            delivery_mode = str(order.get("delivery_method") or "unknown")
            if partner_ref:
                detail_msg += f'<tg-emoji emoji-id="5972022360025336988">🔸</tg-emoji> <b>Partner ref:</b> <code>{html.escape(partner_ref)}</code>\n'
            if customer_email and customer_email != "N/A":
                detail_msg += f'<tg-emoji emoji-id="5447410659077661506">🌐</tg-emoji> <b>Khách API:</b> <code>{html.escape(customer_email)}</code>\n'
            if customer_id:
                detail_msg += f'<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> <b>Customer ID:</b> <code>{html.escape(customer_id)}</code>\n'
            detail_msg += f'🔌 <b>Delivery:</b> <code>{html.escape(delivery_mode)}</code>\n'
            if api_note:
                detail_msg += f'<tg-emoji emoji-id="5460753627817723162">💡</tg-emoji> <b>Ghi chú:</b> {html.escape(api_note)}\n'

        # Check warranty expiry
        warranty_info = resolve_order_warranty_info(order)
        warranty_expires = warranty_info.get("expires_at")
        is_expired = bool(warranty_info.get("expired"))
        is_refunded = bool(order.get('refunded_at'))
        if warranty_expires:
            if time.time() > warranty_expires:
                is_expired = True
                detail_msg += lt(user_id, "\n⚠️ <b>Bảo hành:</b> Đã hết hạn", "\n⚠️ <b>Warranty:</b> Expired", "\n⚠️ <b>保修：</b> 已过期")
            else:
                exp_date = datetime.fromtimestamp(warranty_expires).strftime('%d/%m/%Y')
                detail_msg += lt(user_id, "\n🛡️ <b>Bảo hành:</b> Đến {date}", "\n🛡️ <b>Warranty:</b> Until {date}", "\n🛡️ <b>保修：</b> 至 {date}", date=exp_date)
        elif warranty_info.get("known") and is_expired:
            detail_msg += lt(user_id, "\n⚠️ <b>Bảo hành:</b> Đã hết hạn", "\n⚠️ <b>Warranty:</b> Expired", "\n⚠️ <b>保修：</b> 已过期")
        elif warranty_info.get("reason") == "lifetime_warranty":
            detail_msg += lt(user_id, "\n🛡️ <b>Bảo hành:</b> Không giới hạn", "\n🛡️ <b>Warranty:</b> Lifetime", "\n🛡️ <b>保修：</b> 终身")

        btns = []
        if order.get('items') and 'Hoàn thành' in str(status):
            btns.append([_btn(lt(user_id, "Lấy lại thông tin đơn hàng", "Retrieve Order Details", "重新获取订单信息"), icon_id="5373059489568205167", callback_data=f"resend_order_items:{order_code}:{history_page}")])
        repurchase_product_id, repurchase_product = _resolve_repurchase_product(order)
        if repurchase_product_id and isinstance(repurchase_product, dict):
            btns.append([
                _btn(
                    lt(user_id, "Mua lại sản phẩm này", "Buy This Product Again", "再次购买此商品"),
                    icon_id="5402186569006210455",
                    callback_data=f"buy_again:{order_code}:{history_page}",
                    style="success",
                )
            ])
        if not is_expired and not is_api_order and not is_refunded:
            btns.append([_btn(lt(user_id, "Báo lỗi đơn này", "Report This Order", "报告此订单"), icon_id="5273914604752216432", callback_data=f"report_specific_order:{order_code}")])
        btns.append([_btn(lt(user_id, "Quay lại danh sách", "Back to List", "返回列表"), icon_id="6206032691075223572", callback_data=f"lichsu_page:{history_page}")])

        await safe_edit_message(
            query,
            text=detail_msg,
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode=ParseMode.HTML
        )
    elif command == 'report_error':
        context.user_data['state'] = 'awaiting_report_order_code'
        try: await query.delete_message()
        except BadRequest: pass
        await safe_send_message(
            context,
            user_id,
            "<b>Báo cáo lỗi & Yêu cầu hỗ trợ</b>\n\nBắt đầu bằng cách nhập <b>Mã đơn hàng</b> của bạn (ví dụ: ICLD123456).\n\nGõ /cancel để hủy.",
            parse_mode=ParseMode.HTML
        )
    elif command.startswith('resend_order_items:'):
        parts = command.split(':', 2)
        order_code = parts[1] if len(parts) > 1 else ""
        try:
            history_page = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            history_page = 0
        back_to_history_callback = f"lichsu_page:{history_page}"
        await safe_answer(query, "<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Đang gửi lại thông tin...")

        # Tìm order trong DB
        order = db_get_order(order_code)
        if not order:
            await safe_edit_message(
                query,
                text=f"❌ Không tìm thấy đơn hàng <code>{html.escape(order_code)}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        # Kiểm tra quyền. Đơn API lưu user_id theo PARTNER_<name>, không phải Telegram user_id thật.
        if _api_is_order_record(order):
            has_access = _api_user_can_access_order(user_id, order)
        else:
            has_access = order.get('user_id') == user_id
        if not has_access:
            await safe_edit_message(
                query,
                text=f"❌ Bạn không có quyền xem lại đơn <code>{html.escape(order_code)}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        # FIX: Prevent resending items from refunded orders
        if order.get('refunded_at'):
            await safe_edit_message(
                query,
                text=f"❌ Đơn hàng <code>{html.escape(order_code)}</code> đã được hoàn tiền và không thể gửi lại thông tin",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        items = normalize_delivered_items(order.get('items'))
        if not items or len(items) == 0:
            await safe_edit_message(
                query,
                text=(
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng <code>{html.escape(order_code)}</code> không có thông tin tài khoản được lưu.\n\n"
                    "Vui lòng liên hệ admin để được hỗ trợ."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        # Gửi lại items dưới dạng file .txt
        product_name = order.get('product_name') or order.get('product', 'Sản phẩm')
        file_content = f"ĐƠN HÀNG: {order_code}\n"
        file_content += f"Sản phẩm: {product_name}\n"
        file_content += f"Số lượng: {len(items)}\n"
        file_content += "=" * 40 + "\n\n"
        for idx, item in enumerate(items, 1):
            file_content += f"[{idx}] {item}\n"

        delivery = await deliver_items_as_txt(
            context, user_id, order_code, items,
            file_content=file_content,
            file_prefix="GuiLai",
            caption_html=(
                f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>GỬI LẠI THÔNG TIN ĐƠN HÀNG</b>\n\n"
                f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã đơn: <code>{html.escape(order_code)}</code>\n"
                f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> Sản phẩm: <b>{html.escape(str(product_name))}</b>\n"
                f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> Số lượng: {len(items)}\n"
            )
        )

        if delivery.get('delivered'):
            await safe_edit_message(
                query,
                text=(
                    f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi lại thông tin đơn hàng <code>{html.escape(order_code)}</code> thành công!\n\n"
                    "Kiểm tra file phía trên nhé."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại danh sách", "Back to the list", "返回列表"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
        else:
            await safe_edit_message(
                query,
                text="<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể gửi lại thông tin. Vui lòng thử lại sau hoặc liên hệ admin.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn(lt(user_id, "Quay lại danh sách", "Back to the list", "返回列表"), icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
        return
    elif command.startswith('report_specific_order:'):
        order_code = command.split(':', 1)[1]
        order = db_get_order(order_code)

        if not order:
            await safe_answer(query, "❌ Không tìm thấy đơn hàng này.", show_alert=True)
            return

        if not _api_user_can_access_order(user_id, order):
            await safe_answer(query, "❌ Bạn không có quyền báo lỗi đơn này.", show_alert=True)
            return

        if order.get('refunded_at'):
            await safe_answer(
                query,
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa.",
                show_alert=True,
            )
            return

        if await _auto_reject_expired_support_message(query.message, context, order, order_code):
            await safe_answer(query, "Don nay da het han bao hanh.", show_alert=True)
            return

        try:
            await query.message.edit_text(
                lt(user_id,
                   f"Đang xử lý yêu cầu báo lỗi cho đơn hàng <code>{order_code}</code>...",
                   f"Working on the problem report for order <code>{order_code}</code>...",
                   f"正在处理订单 <code>{order_code}</code> 的问题报告…"),
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        except BadRequest:
            pass  # Ignore if message is not modified

        context.user_data['state'] = 'awaiting_report_photo'
        context.user_data['report_order_code'] = order_code
        context.user_data.pop('report_photo_id', None)
        context.user_data.pop('report_photo_chat_id', None)
        context.user_data.pop('report_photo_message_id', None)
        await query.message.reply_text(
            lt(
                user_id,
                "Tiếp theo, vui lòng gửi <b>một ảnh chụp màn hình</b> về lỗi bạn đang gặp phải.",
                "Next, please send <b>a screenshot</b> of the problem.",
                "接下来，请发送<b>问题截图</b>。",
            ),
            parse_mode=ParseMode.HTML
        )
    elif command == 'ask_ai_confirm':

        await query.edit_message_text(lt(user_id, "Đang kết nối với Trợ lý AI, vui lòng chờ trong giây lát...", "Connecting you to the AI assistant, one moment...", "正在连接 AI 助手，请稍候…"))

        question = context.user_data.get('support_query')

        if question:

            try:

                await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)

            except (Forbidden, BadRequest):

                pass

            ai_answer = await ask_ai(question)

            await query.edit_message_text(
                lt(
                    user_id,
                    f'<tg-emoji emoji-id="6271362510901747485">🤖</tg-emoji> <b>Trợ lý AI Lâm Shop trả lời:</b>\n\n{ai_answer}',
                    f'<tg-emoji emoji-id="6271362510901747485">🤖</tg-emoji> <b>The Lâm Shop AI assistant says:</b>\n\n{ai_answer}',
                    f'<tg-emoji emoji-id="6271362510901747485">🤖</tg-emoji> <b>LÂM SHOP AI 助手回复：</b>\n\n{ai_answer}',
                ),
                parse_mode=ParseMode.HTML,
            )

        else: await query.edit_message_text(lt(user_id, "Đã có lỗi xảy ra. Vui lòng bắt đầu lại.", "Something went wrong. Please start again.", "出现错误，请重新开始。"))

        await clear_user_state(context)

    elif command == 'create_ticket_confirm':

        query_text, user = context.user_data.get('support_query'), update.effective_user

        ticket_id = f"TICKET-{random.randint(1000, 9999)}"

        admin_message_text = (f'<tg-emoji emoji-id="5377624166436445368">🎟️</tg-emoji> <b>PHIẾU HỖ TRỢ MỚI</b> ({ticket_id}) <tg-emoji emoji-id="5377624166436445368">🎟️</tg-emoji>\n\n'

                              f'<b>Từ:</b> {format_user_mention_html(user)} (ID: <code>{user.id}</code>)\n'

                              f'<b>Username:</b> @{user.username or "Không có"}\n\n'

                              f'<b>Nội dung:</b>\n<i>{query_text}</i>')

        reply_button = InlineKeyboardButton('<tg-emoji emoji-id="5350752364246606166">✍️</tg-emoji> Phản hồi User', callback_data=f"reply_to_ticket:{user.id}")

        await safe_send_admin(context.bot, admin_message_text, reply_markup=InlineKeyboardMarkup([[reply_button]]))

        await query.edit_message_text(
            lt(
                user_id,
                f'<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji> Đã tạo phiếu hỗ trợ mã <b>{ticket_id}</b>. Admin sẽ phản hồi sớm.',
                f'<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji> Support ticket <b>{ticket_id}</b> created. The admin will reply shortly.',
                f'<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji> 工单 <b>{ticket_id}</b> 已创建，管理员会尽快回复。',
            ),
            parse_mode=ParseMode.HTML,
        )

        await clear_user_state(context)

    elif command.startswith('reply_to_ticket:'):

        target_user_id = int(command.split(':', 1)[1]); context.user_data['state'] = f'awaiting_admin_reply:{target_user_id}'

        await safe_edit_message(

            query.message,

            text=get_query_message_html(query) + "\n\n<i>(Đang chờ phản hồi...)</i>",

            parse_mode=ParseMode.HTML,

            reply_markup=None

        )

        await safe_answer(query); await safe_send_admin(context.bot, f'<tg-emoji emoji-id="5458382591121964689">✍️</tg-emoji> Vui lòng nhập nội dung phản hồi cho người dùng ID: <code>{target_user_id}</code>')



async def priority_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query

    data = getattr(query, "data", "") or ""

    if data == "check_membership":
        await handle_membership_check(update)
        raise ApplicationHandlerStop



    # FIX: Callbacks that belong to ConversationHandlers must NOT be

    # intercepted here. If we call button_handler + raise ApplicationHandlerStop

    # for these, the ConversationHandler in group 0 never receives them and

    # the bot appears frozen (user taps button, nothing happens).

    _conversation_only_prefixes = (

        # /newproduct conversation

        "name_suggest_", "desc_choice_", "ai_desc_",

        "prod_gmail_", "prod_confirm_",

        # /editproduct conversation

        "edit_sel_", "edit_page_", "edit_field_",

        "ai_edit_desc_", "cancel_edit",

        # /addstock conversation

        "sel_stock_", "stock_page_",

        # /viewstock / /delstock conversation

        "view_stock_", "del_stock_sel_",

        # /create_ga conversation

        "ga_mode_",

    )

    if any(data == prefix or data.startswith(prefix) for prefix in _conversation_only_prefixes):

        logger.debug(f"[PRIORITY_BTN] Skipping conversation callback: {data}")

        return  # Let ConversationHandler (group 0) handle it



    await button_handler(update, context)

    raise ApplicationHandlerStop



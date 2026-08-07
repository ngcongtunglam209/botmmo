
from __future__ import annotations

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


API_PREM_WARN = '<tg-emoji emoji-id="5447644880824181073">âš ï¸</tg-emoji>'
API_PREM_OK = '<tg-emoji emoji-id="6269163801178804220">âœ…</tg-emoji>'
API_PREM_STOP = '<tg-emoji emoji-id="5424857974784925603">â›”</tg-emoji>'
API_PREM_FAIL = 'âŒ'
API_PREM_USER = '<tg-emoji emoji-id="5350778980158956492">ðŸ‘¤</tg-emoji>'
API_PREM_SHIELD = '<tg-emoji emoji-id="5197288647275071607">ðŸ›¡ï¸</tg-emoji>'
API_PREM_LOCK = 'ðŸ”'
API_PREM_MONEY = '<tg-emoji emoji-id="5278467510604160626">ðŸ’°</tg-emoji>'
API_PREM_NOTE = '<tg-emoji emoji-id="5350481781306958339">ðŸ’¾</tg-emoji>'

def _callback_requires_manual_answer(command: str) -> bool:
    command = str(command or "")
    manual_answer_commands = {
        'api_register_request',
        'ask_ai_confirm',
        'create_ticket_confirm',
        'icloud_pay_binance',
        'join_ga_action',
        'withdraw_request',
    }
    manual_answer_prefixes = (
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
        'resend_link:',
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
            with open(candidate_path, "r", encoding="utf-8") as handle:
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

    if any(token in normalized for token in ("vÄ©nh viá»…n", "vinh vien", "lifetime", "permanent", "forever")):
        return 0

    unit_multipliers = (
        (365, ("nÄƒm", "nam", "year", "years")),
        (30, ("thÃ¡ng", "thang", "month", "months")),
        (7, ("tuáº§n", "tuan", "week", "weeks")),
        (1, ("ngÃ y", "ngay", "day", "days")),
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
    if not _ctt_is_catalog_visible(current_product):
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


def _format_social_service_display_status(order: dict, fallback_status: str) -> str:
    raw_status = str((order or {}).get("ctt_supplier_status") or "").strip()
    if not raw_status:
        return fallback_status

    normalized = raw_status.casefold()
    if normalized in {"completed", "complete"}:
        label = "âœ… HoÃ n thÃ nh"
    elif normalized in {"in progress", "processing", "running"}:
        label = "ðŸ”µ Äang cháº¡y"
    elif normalized in {"pending", "queued"}:
        label = "â³ Äang chá»"
    elif normalized in {"partial"}:
        label = "âš ï¸ HoÃ n thÃ nh má»™t pháº§n"
    elif normalized in {"canceled", "cancelled"}:
        label = "âŒ ÄÃ£ há»§y"
    else:
        label = raw_status
    return f"{html.escape(label)} (Social Service)"


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
                "âŒ "
                "<b>KhÃ´ng thá»ƒ hoÃ n táº¥t Ä‘á»•i API key.</b>\n\n"
                "Há»‡ thá»‘ng Ä‘Ã£ giá»¯ nguyÃªn key cÅ© Ä‘á»ƒ trÃ¡nh giÃ¡n Ä‘oáº¡n. HÃ£y thá»­ láº¡i sau."
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
                    f"{API_PREM_WARN} <b>QR/API KEY CÅ¨ ÄÃƒ Háº¾T HIá»†U Lá»°C</b>\n"
                    "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                    f"{API_PREM_SHIELD} <b>Key cÅ©:</b> <code>{old_key}</code>\n"
                    f"{API_PREM_LOCK} <b>Key má»›i:</b> <code>{new_key}</code>\n\n"
                    "<i>Vui lÃ²ng dÃ¹ng key hoáº·c QR á»Ÿ tin nháº¯n má»›i nháº¥t bÃªn dÆ°á»›i. KhÃ´ng dÃ¹ng láº¡i áº£nh QR cÅ© nÃ y.</i>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=None,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            logger.debug("Cannot update stale API wallet QR message for user %s", user_id)

    text = (
        f"{API_PREM_LOCK} <b>ÄÃƒ Äá»”I API KEY</b>\n"
        "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
        f"{API_PREM_USER} <b>Partner:</b> {html.escape(str(partner_name))}\n"
        f"{API_PREM_NOTE} <b>API Key má»›i:</b> <code>{new_key}</code>\n"
        f"{API_PREM_MONEY} <b>Sá»‘ dÆ° vÃ­ chung:</b> {current_balance:,} VNÄ\n\n"
        f"<i>{API_PREM_WARN} API key cÅ© Ä‘Ã£ bá»‹ vÃ´ hiá»‡u hÃ³a Ä‘á»ƒ báº£o máº­t. HÃ£y cáº­p nháº­t key má»›i trong há»‡ thá»‘ng cá»§a báº¡n.</i>"
    )
    kb = InlineKeyboardMarkup([
        [_btn("Náº¡p VÃ­", icon_id="5278467510604160626", callback_data="api_member_wallet")],
        [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
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

    # Kiá»ƒm tra cháº¿ Ä‘á»™ báº£o trÃ¬
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await safe_answer(update.callback_query, "<tg-emoji emoji-id=\"5215392879320505675\">ðŸ› ï¸</tg-emoji> Há»‡ thá»‘ng Ä‘ang báº£o trÃ¬!", show_alert=True)
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
        try: await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Thao tÃ¡c quÃ¡ nhanh!", show_alert=False)
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
        'resend_link:',
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
                            f"<tg-emoji emoji-id=\"5462956611033117422\">â™»ï¸</tg-emoji> <b>ÄÃ£ hoÃ n láº¡i:</b> +{balance_used:,} VNÄ vÃ o vÃ­ (Do há»§y Ä‘Æ¡n).",
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
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>KhÃ´ng thá»ƒ nháº¯n riÃªng cho báº¡n.</b>\n\n"
                "Vui lÃ²ng má»Ÿ chat riÃªng vá»›i bot vÃ  gá»­i <code>/start</code> trÆ°á»›c,\n"
                "sau Ä‘Ã³ quay láº¡i thao tÃ¡c nÃ y."
            )
            fallback_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“©</tg-emoji> Má»Ÿ chat bot", url=deep_link)]
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

    # iCloud Purchase Start
    elif command == 'muahang_start':
        try:
            from app.core.config_env import ENABLE_ICLOUD_SALES
        except ImportError:
            ENABLE_ICLOUD_SALES = True

        if not ENABLE_ICLOUD_SALES:
            await safe_answer(query, "âŒ Dá»‹ch vá»¥ iCloud hiá»‡n Ä‘ang táº¡m Ä‘Ã³ng.", show_alert=True)
            return

        # Check stock
        if not available_links:
            try:
                await query.edit_message_text(
                    "âŒ <b>Táº M Háº¾T HÃ€NG!</b>\n\n"
                    "<tg-emoji emoji-id=\"5231489647946768652\">â˜ï¸</tg-emoji> GÃ³i iCloud 2TB hiá»‡n Ä‘ang háº¿t link kÃ­ch hoáº¡t.\n\n"
                    f"{E_TIP} Vui lÃ²ng quay láº¡i sau hoáº·c liÃªn há»‡ Admin Ä‘á»ƒ Ä‘Æ°á»£c thÃ´ng bÃ¡o khi cÃ³ hÃ ng!",
                    parse_mode='HTML',
                    reply_markup=create_back_button_menu()
                )
            except BadRequest:
                await safe_answer(query, "âŒ Háº¿t hÃ ng! Vui lÃ²ng quay láº¡i sau.", show_alert=True)
            return
        
        # Clear any existing state
        await clear_user_state(context)
        
        # Set state for email purchase
        context.user_data['state'] = 'awaiting_email'
        
        msg = (
            f"<tg-emoji emoji-id=\"5231489647946768652\">â˜ï¸</tg-emoji> <b>MUA GÃ“I iCLOUD 2TB</b>\n\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>GiÃ¡:</b> {ICLOUD_PACKAGE_PRICE:,} VNÄ\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>Tráº¡ng thÃ¡i:</b> <tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> CÃ²n hÃ ng\n\n"
            f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> <b>Vui lÃ²ng nháº­p email Ä‘á»ƒ nháº­n link kÃ­ch hoáº¡t:</b>\n"
            f"<i>(Email sáº½ Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ gá»­i link kÃ­ch hoáº¡t iCloud)</i>"
        )
        
        await query.edit_message_text(
            msg,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("âŒ Há»§y", callback_data="back_to_main")]
            ])
        )
    

    # Dice Game Callback
    
    # Dice Game Prize Selection Callbacks
    
    
    # Manual Order Admin Callbacks
    
        
    # NEW: Withdrawal Callbacks
    elif command == 'withdraw_request':
        context.user_data.pop('state', None)
        context.user_data.pop('withdrawal_amount', None)
        await safe_answer(query, "TÃ­nh nÄƒng rÃºt tiá»n Ä‘Ã£ Ä‘Æ°á»£c táº¯t. Sá»‘ dÆ° chá»‰ dÃ¹ng Ä‘á»ƒ mua hÃ ng.", show_alert=True)
        return

    elif command.startswith('refund_bank:'):
        await begin_bank_refund_request(query, context, command)
        return
        
    
    # ===== LUCKY WHEEL CALLBACKS =====


    # ===== ADVANCED FEATURES CALLBACKS =====
    elif command == 'my_stats':
        await show_my_stats(update, context, is_callback=True)
    
    elif command == 'my_referral':
        await show_my_referral(update, context, is_callback=True)
    
    elif command == 'top_referrers':
        await show_top_referrers(update, context, is_callback=True)

    # ===== NEW FEATURES CALLBACKS (RATING / WARRANTY / CHAT) =====
    elif command == 'join_ga_action':
        # Derive GA ID from message
        ga_key = f"{query.message.chat.id}_{query.message.message_id}"
        
        if ga_key not in active_giveaways:
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Giveaway nÃ y Ä‘Ã£ káº¿t thÃºc hoáº·c bá»‹ xÃ³a!", show_alert=True)
            return
            
        ga = active_giveaways[ga_key]
        if ga['status'] != 'active':
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Giveaway Ä‘Ã£ káº¿t thÃºc!", show_alert=True)
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
            await safe_answer(query, "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Báº¡n Ä‘Ã£ tham gia rá»“i!", show_alert=True)
            return
            
        # Add participant
        ga['participants'].append(user_id)
        await save_data()
        
        await safe_answer(query, "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Tham gia thÃ nh cÃ´ng! ChÃºc may máº¯n!", show_alert=True)
        
        # Update UI count (Debounced preferred but simple edit here)
        try:
            ud = ga
            end_ts = ud.get('end_time', 0)
            end_str = datetime.fromtimestamp(end_ts).strftime('%H:%M %d/%m') if end_ts > 0 else "Khi Admin káº¿t thÃºc"
            
            msg_text = (
                f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> <b>Sá»° KIá»†N GIVEAWAY: {ud.get('title', 'EVENT').upper()}</b> <tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji>\n\n"
                f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ</tg-emoji> <b>Pháº§n thÆ°á»Ÿng:</b> {ud.get('prize_qty', 1)}x {ud.get('prize_name', 'MÃ³n quÃ  bÃ­ áº©n')}\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> <b>Káº¿t thÃºc:</b> {end_str}\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>NgÆ°á»i tham gia:</b> {len(ga['participants'])}\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> <i>Báº¥m nÃºt bÃªn dÆ°á»›i Ä‘á»ƒ thá»­ váº­n may!</i>"
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
                "<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>YÃŠU Cáº¦U Báº¢O HÃ€NH</b>\n\nVui lÃ²ng <b>mÃ´ táº£ váº¥n Ä‘á»</b> báº¡n gáº·p pháº£i:\n<i>(Gá»­i tin nháº¯n mÃ´ táº£ chi tiáº¿t)</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("âŒ Há»§y", callback_data="main_menu")]])
            )

    elif command == 'open_live_chat':
        user_id_str = str(user_id)
        if user_id_str not in live_chats:
            live_chats[user_id_str] = {'messages': [], 'status': 'active', 'last_activity': time.time(), 'unread_by_admin': 0}
        context.user_data['state'] = 'in_live_chat'
        chat = live_chats[user_id_str]
        msg = f'<tg-emoji emoji-id="6129860303619363484">ðŸ’¬</tg-emoji> <b>{t("live_chat_title", user_id=user_id)}</b>\n\n'
        recent_msgs = chat['messages'][-10:]
        for m in recent_msgs:
            from_who = (
                f'<tg-emoji emoji-id="5350778980158956492">ðŸ§‘</tg-emoji> {t("live_chat_you", user_id=user_id)}'
                if m['from'] == 'user'
                else f'<tg-emoji emoji-id="5350778980158956492">ðŸ‘¨</tg-emoji>â€<tg-emoji emoji-id="5854908544712707500">ðŸ’¼</tg-emoji> {t("live_chat_admin", user_id=user_id)}'
            )
            time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
            msg += f"{from_who} ({time_str}):\n{m['text']}\n\n"
        if not recent_msgs:
            msg += f'<i>{t("live_chat_empty", user_id=user_id)}</i>\n\n'
        msg += f'<tg-emoji emoji-id="5460753627817723162">ðŸ’¡</tg-emoji> {t("live_chat_prompt", user_id=user_id)}'
        btns = [[InlineKeyboardButton(f'âŒ {t("live_chat_close", user_id=user_id)}', callback_data="close_live_chat")]]
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
        msg = f'<tg-emoji emoji-id="6129860303619363484">ðŸ’¬</tg-emoji> <b>{t("live_chat_title", user_id=user_id)}</b>\n\n'
        recent_msgs = chat['messages'][-10:]
        for m in recent_msgs:
            from_who = (
                f'<tg-emoji emoji-id="5350778980158956492">ðŸ§‘</tg-emoji> {t("live_chat_you", user_id=user_id)}'
                if m['from'] == 'user'
                else f'<tg-emoji emoji-id="5350778980158956492">ðŸ‘¨</tg-emoji>â€<tg-emoji emoji-id="5854908544712707500">ðŸ’¼</tg-emoji> {t("live_chat_admin", user_id=user_id)}'
            )
            time_str = datetime.fromtimestamp(m['timestamp']).strftime('%H:%M')
            msg += f"{from_who} ({time_str}):\n{m['text']}\n\n"
        if not recent_msgs:
            msg += f'<i>{t("live_chat_empty", user_id=user_id)}</i>\n\n'
        msg += f'<tg-emoji emoji-id="5460753627817723162">ðŸ’¡</tg-emoji> {t("live_chat_prompt", user_id=user_id)}'
        btns = [[InlineKeyboardButton(f'âŒ {t("live_chat_close", user_id=user_id)}', callback_data="close_live_chat")]]
        await safe_send_message(context, user_id, msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

    elif command in {'api_register_request', 'api_register_guide'}:
        if command == 'api_register_guide':
            text = (
                "<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“˜</tg-emoji> <b>HÆ¯á»šNG DáºªN ÄÄ‚NG KÃ API PARTNER</b>\n"
                "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                "1. Nháº¥n nÃºt <b>Gá»­i yÃªu cáº§u Ä‘Äƒng kÃ½</b> bÃªn dÆ°á»›i.\n"
                "2. Chá» Admin duyá»‡t tÃ i khoáº£n.\n"
                "3. Bot gá»­i API Key cho báº¡n qua tin nháº¯n.\n"
                "4. Náº¡p vÃ­ báº±ng lá»‡nh <code>/napapi [sá»‘_tiá»n]</code>.\n"
                "5. VÃ o láº¡i <code>/start</code> Ä‘á»ƒ tháº¥y menu <b>API Partner</b>.\n\n"
                "<i>Menu API chá»‰ hiá»‡n sau khi Ä‘Æ°á»£c Admin duyá»‡t.</i>"
            )
            kb = InlineKeyboardMarkup([
                [_btn("Gá»­i yÃªu cáº§u Ä‘Äƒng kÃ½", icon_id="5436359785534466562", callback_data="api_register_request")],
                [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="back_to_main")]
            ])
            kb = InlineKeyboardMarkup([
                [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
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
            await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">â›”</tg-emoji> Báº¡n chÆ°a Ä‘Æ°á»£c Admin duyá»‡t API.", show_alert=True)
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
                    "<b>XÃC NHáº¬N Äá»”I API KEY</b>\n\n"
                    "Äá»ƒ trÃ¡nh báº¥m nháº§m, hÃ£y nháº­p <code>sure</code> vÃ o chat Ä‘á»ƒ xÃ¡c nháº­n Ä‘á»•i key.\n"
                    "Náº¿u khÃ´ng muá»‘n Ä‘á»•i ná»¯a, hÃ£y gÃµ <code>/cancel</code>."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
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
                        "âŒ "
                        "<b>KhÃ´ng thá»ƒ hoÃ n táº¥t Ä‘á»•i API key.</b>\n\n"
                        "Há»‡ thá»‘ng Ä‘Ã£ giá»¯ nguyÃªn key cÅ© Ä‘á»ƒ trÃ¡nh giÃ¡n Ä‘oáº¡n. HÃ£y thá»­ láº¡i sau."
                    ),
                    parse_mode=ParseMode.HTML,
                )
                return

            logger.info("API key rotated for user %s", user_id)

            text = (
                "\U0001F511 <b>ÄÃƒ Äá»”I API KEY</b>\n"
                "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"\U0001F464 <b>Partner:</b> {html.escape(str(partner_name))}\n"
                f"\U0001F6E1 <b>API Key má»›i:</b> <code>{new_key}</code>\n"
                f"\U0001F4B0 <b>Sá»‘ dÆ° vÃ­ chung:</b> {current_balance:,} VNÄ\n\n"
                "<i>\u26A0\uFE0F API key cÅ© Ä‘Ã£ bá»‹ vÃ´ hiá»‡u hÃ³a Ä‘á»ƒ báº£o máº­t. HÃ£y cáº­p nháº­t key má»›i trong há»‡ thá»‘ng cá»§a báº¡n.</i>"
            )
            kb = InlineKeyboardMarkup([
                [_btn("Náº¡p VÃ­", icon_id="5278467510604160626", callback_data="api_member_wallet")],
                [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
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
                "<tg-emoji emoji-id=\"6271362510901747485\">ðŸ¤–</tg-emoji> <b>MENU API PARTNER (THÃ€NH VIÃŠN)</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>Sá»‘ dÆ° vÃ­ chung:</b> {balance:,} VNÄ\n\n<b>Full lá»‡nh/API cho thÃ nh viÃªn:</b>\nâ€¢ <code>/napapi [sá»‘_tiá»n]</code> - táº¡o QR náº¡p vÃ­ chung\nâ€¢ <code>/lichsu</code> - xem lá»‹ch sá»­ Ä‘Æ¡n thÆ°á»ng + Ä‘Æ¡n API\nâ€¢ <code>GET /api/v2/me</code> - kiá»ƒm tra key + sá»‘ dÆ°\nâ€¢ <code>GET /api/v2/catalog</code> - láº¥y danh má»¥c sáº£n pháº©m\nâ€¢ <code>GET /api/v2/orders</code> - láº¥y lá»‹ch sá»­ Ä‘Æ¡n API\nâ€¢ <code>POST /api/v2/orders</code> - táº¡o Ä‘Æ¡n mua\nâ€¢ <code>GET /api/v2/orders/{{order_code}}</code> - tra cá»©u Ä‘Æ¡n\nâ€¢ <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - tra theo mÃ£ Ä‘á»‘i tÃ¡c\n\n<i>Menu nÃ y chá»‰ hiá»ƒn thá»‹ khi tÃ i khoáº£n Ä‘Ã£ Ä‘Æ°á»£c Admin duyá»‡t API.</i>",
                "<tg-emoji emoji-id=\"6271362510901747485\">ðŸ¤–</tg-emoji> <b>API PARTNER MENU (MEMBER)</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>Shared wallet balance:</b> {balance:,} VND\n\n<b>Member commands/API:</b>\nâ€¢ <code>/napapi [amount]</code> - create a shared-wallet top-up QR\nâ€¢ <code>/lichsu</code> - view regular and API orders\nâ€¢ <code>GET /api/v2/me</code> - verify key and balance\nâ€¢ <code>GET /api/v2/catalog</code> - get product catalog\nâ€¢ <code>GET /api/v2/orders</code> - get API order history\nâ€¢ <code>POST /api/v2/orders</code> - create an order\nâ€¢ <code>GET /api/v2/orders/{{order_code}}</code> - look up an order\nâ€¢ <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - look up by partner reference\n\n<i>This menu appears only after Admin approves API access.</i>",
                "<tg-emoji emoji-id=\"6271362510901747485\">ðŸ¤–</tg-emoji> <b>API åˆä½œä¼™ä¼´èœå•ï¼ˆæˆå‘˜ï¼‰</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>åˆä½œä¼™ä¼´ï¼š</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Keyï¼š</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>å…±äº«é’±åŒ…ä½™é¢ï¼š</b> {balance:,} VND\n\n<b>æˆå‘˜å‘½ä»¤/APIï¼š</b>\nâ€¢ <code>/napapi [é‡‘é¢]</code> - åˆ›å»ºå…±äº«é’±åŒ…å……å€¼äºŒç»´ç \nâ€¢ <code>/lichsu</code> - æŸ¥çœ‹æ™®é€šè®¢å•å’Œ API è®¢å•\nâ€¢ <code>GET /api/v2/me</code> - æ£€æŸ¥å¯†é’¥å’Œä½™é¢\nâ€¢ <code>GET /api/v2/catalog</code> - èŽ·å–å•†å“ç›®å½•\nâ€¢ <code>GET /api/v2/orders</code> - èŽ·å– API è®¢å•åŽ†å²\nâ€¢ <code>POST /api/v2/orders</code> - åˆ›å»ºè®¢å•\nâ€¢ <code>GET /api/v2/orders/{{order_code}}</code> - æŸ¥è¯¢è®¢å•\nâ€¢ <code>GET /api/v2/orders/by-ref/{{partner_ref}}</code> - æŒ‰åˆä½œä¼™ä¼´ç¼–å·æŸ¥è¯¢\n\n<i>ä»…åœ¨ç®¡ç†å‘˜æ‰¹å‡† API æƒé™åŽæ˜¾ç¤ºæ­¤èœå•ã€‚</i>",
                partner=html.escape(str(partner_name)), key=partner_key, balance=partner_balance,
            )
            kb = InlineKeyboardMarkup([
                [_btn(lt(user_id, "VÃ­ Chung", "Shared Wallet", "å…±äº«é’±åŒ…"), icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn(lt(user_id, "Lá»‹ch Sá»­", "History", "åŽ†å²"), icon_id="5444856076954520455", callback_data="lichsu_entry")],
                [_btn(lt(user_id, "Náº¡p VÃ­", "Top Up", "å……å€¼"), icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn(lt(user_id, "TÃ i Liá»‡u API", "API Docs", "API æ–‡æ¡£"), icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
                [_btn(lt(user_id, "Quay láº¡i", "Back", "è¿”å›ž"), icon_id="6206032691075223572", callback_data="back_to_main")]
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
                "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>QR Náº P VÃ CHUNG</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>Sá»‘ dÆ° hiá»‡n táº¡i:</b> {balance:,} VNÄ\n<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>Ná»™i dung CK:</b> <code>{content}</code>\n\n<b>QuÃ©t QR rá»“i nháº­p sá»‘ tiá»n báº¡n muá»‘n náº¡p trong app ngÃ¢n hÃ ng.</b>\n\n<i>Há»‡ thá»‘ng sáº½ tá»± cá»™ng tiá»n khi nháº­n Ä‘Æ°á»£c giao dá»‹ch cÃ³ ná»™i dung Ä‘Ãºng Telegram ID cá»§a báº¡n.</i>",
                "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>SHARED WALLET TOP-UP QR</b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key:</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>Current balance:</b> {balance:,} VND\n<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>Transfer content:</b> <code>{content}</code>\n\n<b>Scan the QR and enter your top-up amount in your banking app.</b>\n\n<i>The system credits your wallet automatically when the transfer content matches your Telegram ID.</i>",
                "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>å…±äº«é’±åŒ…å……å€¼äºŒç»´ç </b>\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¥</tg-emoji> <b>åˆä½œä¼™ä¼´ï¼š</b> {partner}\n<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Keyï¼š</b> <code>{key}</code>\n<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>å½“å‰ä½™é¢ï¼š</b> {balance:,} VND\n<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>è½¬è´¦å†…å®¹ï¼š</b> <code>{content}</code>\n\n<b>æ‰«æäºŒç»´ç ï¼Œç„¶åŽåœ¨é“¶è¡Œåº”ç”¨ä¸­è¾“å…¥å……å€¼é‡‘é¢ã€‚</b>\n\n<i>æ”¶åˆ°è½¬è´¦å†…å®¹ä¸Žæ‚¨çš„ Telegram ID åŒ¹é…çš„äº¤æ˜“åŽï¼Œç³»ç»Ÿå°†è‡ªåŠ¨å…¥è´¦ã€‚</i>",
                partner=html.escape(str(partner_name)), key=partner_key,
                balance=partner_balance, content=transfer_content,
            )
            kb = InlineKeyboardMarkup([[
                _btn(lt(user_id, "Äá»•i API Key", "Rotate API Key", "æ›´æ¢ API Key"), icon_id="5352716320093695452", callback_data="api_member_rotate_key"),
                _btn(lt(user_id, "Quay láº¡i menu API", "Back to API Menu", "è¿”å›ž API èœå•"), icon_id="6206032691075223572", callback_data="api_member_menu")
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
                "<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>HÆ¯á»šNG DáºªN Náº P VÃ CHUNG</b>\n"
                "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                "1. GÃµ lá»‡nh: <code>/napapi [sá»‘_tiá»n]</code>\n"
                "2. Bot tráº£ vá» QR + ná»™i dung chuyá»ƒn khoáº£n (NAPI...)\n"
                "3. Chuyá»ƒn Ä‘Ãºng sá»‘ tiá»n vÃ  Ä‘Ãºng ná»™i dung\n"
                "4. Chá» 1-3 phÃºt há»‡ thá»‘ng tá»± cá»™ng vÃ o vÃ­ chung\n\n"
                "<b>VÃ­ dá»¥:</b>\n"
                "â€¢ <code>/napapi 200000</code>\n"
                "â€¢ <code>/napapi 500000</code>"
            )
            kb = InlineKeyboardMarkup([
                [_btn("VÃ­ Chung", icon_id="5278467510604160626", callback_data="api_member_wallet")],
                [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        base_url_note = (
            "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Link hiá»‡n táº¡i lÃ  Cloudflare Quick Tunnel.</b> Náº¿u server restart hoáº·c má»Ÿ láº¡i cloudflared thÃ¬ URL cÃ³ thá»ƒ Ä‘á»•i.\n\n"
            if "trycloudflare.com" in base_url
            else "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>Link nÃ y Ä‘ang láº¥y tá»« cáº¥u hÃ¬nh PUBLIC_API_URL hiá»‡n táº¡i.</b>\n\n"
        )

        if command == 'api_member_endpoints':
            text = (
                "<tg-emoji emoji-id=\"5215392879320505675\">ðŸ› ï¸</tg-emoji> <b>DANH SÃCH ENDPOINT PARTNER</b>\n"
                "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"<tg-emoji emoji-id=\"5447410659077661506\">ðŸŒ</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
                f"{base_url_note}"
                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“–</tg-emoji> <b>TÃ i liá»‡u Web:</b> "
                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
                "<b>Sáº£n pháº©m thÆ°á»ng:</b>\n"
                "â€¢ <code>GET /api/v2/me</code>\n"
                "â€¢ <code>GET /api/v2/catalog</code>\n"
                "â€¢ <code>POST /api/v2/orders</code>\n"
                "â€¢ <code>GET /api/v2/orders/{order_code}</code>\n\n"
                "<b>Social Media:</b>\n"
                "â€¢ <code>GET /api/social/catalog</code>\n"
                "â€¢ <code>POST /api/social/orders</code>\n"
                "â€¢ <code>GET /api/social/orders?limit=20&amp;offset=0</code>\n"
                "â€¢ <code>GET /api/social/orders/{order_code}</code>\n"
                "â€¢ <code>GET /api/social/orders/by-ref/{partner_ref}</code>\n\n"
                "<b>Headers dÃ¹ng chung:</b>\n"
                f"â€¢ <code>x-api-key: {partner_key}</code>\n"
                "â€¢ <code>x-idempotency-key: MA_DON_DOI_TAC</code>\n\n"
                "<b>MÃ£ pháº£n há»“i:</b> <code>200</code> OK Â· <code>400</code> sai endpoint/field Â· <code>401</code> sai key Â· <code>402</code> thiáº¿u tiá»n Â· <code>404</code> khÃ´ng tÃ¬m tháº¥y"
            )
            kb = InlineKeyboardMarkup([
                [_btn("TÃ i Liá»‡u API", icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        if command == 'api_member_docs':
            guide_sent = False
            guide_status = (
                "<tg-emoji emoji-id=\"5303290914041505430\">âš¡ï¸</tg-emoji> "
                "<b>MÃ¬nh Ä‘Ã£ gá»­i file tÃ i liá»‡u chi tiáº¿t á»Ÿ tin nháº¯n bÃªn dÆ°á»›i.</b>\n\n"
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
                                "<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“š</tg-emoji> "
                                "<b>TÃ i liá»‡u API Partner chi tiáº¿t</b>\n"
                                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“–</tg-emoji> "
                                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n"
                                "<i>File nÃ y cÃ³ vÃ­ dá»¥ táº¡o Ä‘Æ¡n, poll Ä‘Æ¡n, nháº­n sáº£n pháº©m, quantity vÃ  cÃ¡c response máº«u.</i>"
                            ),
                            parse_mode='HTML',
                        )
                    guide_sent = True
            except (TelegramError, OSError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"Cannot send API partner guide document to user {user_id}: {e}")

            if not guide_sent:
                guide_status = (
                    "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> "
                    "<b>ChÆ°a gá»­i Ä‘Æ°á»£c file tÃ i liá»‡u.</b> Báº¡n váº«n cÃ³ thá»ƒ xem báº£n tÃ³m táº¯t bÃªn dÆ°á»›i.\n\n"
                )

            text = (
                "<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“œ</tg-emoji> <b>TÃ€I LIá»†U API DÃ€NH CHO THÃ€NH VIÃŠN</b>\n"
                "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"{guide_status}"
                f"<tg-emoji emoji-id=\"5447410659077661506\">ðŸŒ</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
                f"{base_url_note}"
                f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“–</tg-emoji> <b>TÃ i liá»‡u Web:</b> "
                f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
                f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key cá»§a báº¡n:</b> <code>{partner_key}</code>\n\n"
                "<b>Gá»i API cáº§n cÃ¡c header:</b>\n"
                f"â€¢ <code>x-api-key: {partner_key}</code>\n"
                "â€¢ <code>x-idempotency-key: MA_DON_DOI_TAC</code> (khuyáº¿n nghá»‹)\n\n"
                "<b>Hai luá»“ng tÃ­ch há»£p:</b>\n"
                "1. Sáº£n pháº©m thÆ°á»ng: <code>GET /api/v2/catalog</code> â†’ <code>POST /api/v2/orders</code>\n"
                "2. Social: <code>GET /api/social/catalog</code> â†’ <code>POST /api/social/orders</code>\n"
                "3. ÄÆ¡n thÆ°á»ng poll táº¡i <code>/api/v2/orders/{order_code}</code>\n"
                "4. ÄÆ¡n social poll táº¡i <code>/api/social/orders/{order_code}</code>\n\n"
                "<b>Ghi nhá»›:</b>\n"
                "â€¢ Hai nhÃ³m dÃ¹ng chung API key vÃ  vÃ­ partner\n"
                "â€¢ Sáº£n pháº©m thÆ°á»ng giao ngay náº±m trong <code>data.items</code>\n"
                "â€¢ Social Ä‘á»c <code>supplier_status</code> vÃ  <code>supplier_remains</code>\n"
                "â€¢ Retry pháº£i giá»¯ nguyÃªn <code>partner_ref</code> vÃ  <code>x-idempotency-key</code>\n"
                "â€¢ Gáº·p <code>402</code>: náº¡p vÃ­ báº±ng <code>/napapi [sá»‘_tiá»n]</code>"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Má»Ÿ tÃ i liá»‡u Web", url=docs_url)],
                [_btn("VÃ­ Chung", icon_id="5278467510604160626", callback_data="api_member_wallet"),
                 _btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
                [_btn("Gá»­i láº¡i tÃ i liá»‡u", icon_id="5350481781306958339", callback_data="api_member_docs")],
                [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
            ])
            await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
            return

        # command == 'api_member_docs'
        text = (
            "<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“œ</tg-emoji> <b>TÃ€I LIá»†U API DÃ€NH CHO THÃ€NH VIÃŠN</b>\n"
            "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            f"<tg-emoji emoji-id=\"5447410659077661506\">ðŸŒ</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n"
            f"{base_url_note}"
            f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ“–</tg-emoji> <b>TÃ i liá»‡u Web:</b> "
            f"<a href=\"{safe_docs_url}\">{safe_docs_url}</a>\n\n"
            f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡</tg-emoji> <b>API Key cá»§a báº¡n:</b> <code>{partner_key}</code>\n\n"
            "<b>Headers khi gá»i API:</b>\n"
            f"â€¢ <code>x-api-key: {partner_key}</code>\n"
            "â€¢ <code>x-idempotency-key: MA_DON_DOI_TAC</code> (khuyáº¿n nghá»‹)\n\n"
            "<b>Máº«u cURL mua Ä‘Æ¡n AUTO (TÃ i khoáº£n cÃ³ sáºµn):</b>\n"
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
            "<b>Máº«u cURL mua Ä‘Æ¡n MANUAL (YÃªu cáº§u nháº­p mail):</b>\n"
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
            "<b>Test nhanh (DÃ nh cho Shell/cURL):</b>\n"
            "<pre>curl -X GET " + f"{base_url}/api/v2/me" + "\\\n"
            "  -H 'x-api-key: " + f"{partner_key}" + "'</pre>\n\n"
            "<b>Káº¿t quáº£ test máº«u (thá»±c táº¿):</b>\n"
            "â€¢ <code>GET /api/v2/status -> 200 OK</code>\n"
            "â€¢ <code>GET /api/v2/me -> 200 OK</code>\n"
            "â€¢ <code>GET /api/v2/catalog -> 200 OK</code>\n"
            "â€¢ <code>GET /api/v2/orders -> 200 OK</code>\n"
            "â€¢ <code>POST /api/v2/orders -> 402 Payment Required</code> (khi vÃ­ chung = 0)\n"
            "â€¢ CÃ¡ch xá»­ lÃ½: náº¡p vÃ­ chung báº±ng <code>/napapi [sá»‘_tiá»n]</code> rá»“i gá»i láº¡i Ä‘Æ¡n.\n\n"
            "<b>Ná»™i dung tÃ i khoáº£n tráº£ vá»:</b>\n"
            "â€¢ Äá»c á»Ÿ <code>data.items</code>\n"
            "â€¢ ThÆ°á»ng dáº¡ng <code>email|password</code>\n"
            "â€¢ Náº¿u Ä‘Æ¡n manual/pending thÃ¬ chÆ°a cÃ³ items ngay"
        )
        kb = InlineKeyboardMarkup([
            [_btn("Endpoints", icon_id="5215039453487893428", callback_data="api_member_endpoints")],
            [_btn("Quay láº¡i menu API", icon_id="6206032691075223572", callback_data="api_member_menu")]
        ])
        await safe_edit_message(query, text=text, parse_mode='HTML', reply_markup=kb)
        return

    elif command in {'huongdan', 'chinhsach'}:
        text_map = {'huongdan': HUONGDAN_TEXT, 'chinhsach': CHINHSACH_TEXT}
        menu = create_guide_policy_menu("guide" if command == "huongdan" else "policy")
        full_text = text_map[command]
        if len(full_text) <= 4000:
            await safe_edit_message(
                query,
                text=full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=menu,
            )
        else:
            # Text quÃ¡ dÃ i cho edit_message_text (limit 4096) â†’ gá»­i tin má»›i
            try:
                await safe_edit_message(
                    query,
                    text='<tg-emoji emoji-id="5350481781306958339">ðŸ“š</tg-emoji> '
                         '<b>Xem ná»™i dung chi tiáº¿t á»Ÿ tin nháº¯n bÃªn dÆ°á»›i.</b>',
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
            await safe_answer(query, lt(user_id, "KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng.", "Order not found.", "æœªæ‰¾åˆ°è®¢å•ã€‚"), show_alert=True)
            return
        if _api_is_order_record(order):
            await safe_answer(query, lt(user_id, "ÄÆ¡n API Partner cáº§n mua láº¡i qua API.", "API Partner orders must be reordered through the API.", "API åˆä½œä¼™ä¼´è®¢å•éœ€è¦é€šè¿‡ API é‡æ–°è´­ä¹°ã€‚"), show_alert=True)
            return

        product_id, current_product = _resolve_repurchase_product(order)
        if not product_id or not isinstance(current_product, dict):
            await safe_answer(
                query,
                lt(
                    user_id,
                    "Sáº£n pháº©m nÃ y Ä‘Ã£ ngá»«ng bÃ¡n hoáº·c khÃ´ng cÃ²n trong cá»­a hÃ ng.",
                    "This product is no longer available in the store.",
                    "è¯¥å•†å“å·²åœå”®æˆ–ä¸å†å­˜åœ¨äºŽå•†åº—ä¸­ã€‚",
                ),
                show_alert=True,
            )
            return

        await safe_answer(query, lt(user_id, "Äang kiá»ƒm tra giÃ¡ vÃ  tá»“n kho má»›i...", "Checking the latest price and stock...", "æ­£åœ¨æ£€æŸ¥æœ€æ–°ä»·æ ¼å’Œåº“å­˜â€¦â€¦"))
        if current_product.get("is_supplier_source_resell"):
            await _refresh_resell_product_entries([(product_id, current_product)])

        await _show_store_product_detail(
            query,
            context,
            product_id,
            back_callback_data=f"view_order_history_{order_code}:{history_page}",
            back_button_text=lt(user_id, "Quay láº¡i Ä‘Æ¡n hÃ ng", "Back to Order", "è¿”å›žè®¢å•"),
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

        # FIX: DÃ¹ng index O(1)
        order = find_order_by_code_or_supplier_id(order_code)
        
        if not order:
            await safe_answer(query, lt(user_id, "ÄÆ¡n hÃ ng khÃ´ng tá»“n táº¡i", "Order not found", "è®¢å•ä¸å­˜åœ¨"), show_alert=True)
            await lichsu_command(update, context, is_callback=True, page=history_page)
            return

        if not _api_user_can_access_order(user_id, order):
            await safe_answer(query, lt(user_id, "Báº¡n khÃ´ng cÃ³ quyá»n xem Ä‘Æ¡n nÃ y", "You cannot access this order", "æ‚¨æ— æƒæŸ¥çœ‹æ­¤è®¢å•"), show_alert=True)
            return
        if order.get('refunded_at'):
            await safe_answer(query, lt(user_id, "ÄÆ¡n hÃ ng Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n vÃ  khÃ´ng thá»ƒ xem láº¡i", "This order was refunded and can no longer be viewed", "æ­¤è®¢å•å·²é€€æ¬¾ï¼Œæ— æ³•å†æ¬¡æŸ¥çœ‹"), show_alert=True)
            return
        
        await safe_answer(query)
        await refresh_ctt_order_status(order)
            
        # Format details
        ts = order.get('timestamp', 0)
        time_str = datetime.fromtimestamp(ts).strftime('%H:%M %d/%m/%Y') if ts else "N/A"
        amount = order.get('amount', 0)
        status = status_text(order.get('status'))
        if order.get("is_social_source_service"):
            status = _format_social_service_display_status(order, status)
        
        detail_msg = lt(
            user_id,
            'ðŸ”Ž <b>CHI TIáº¾T ÄÆ N HÃ€NG</b>\n\nðŸ”¸ <b>MÃ£ Ä‘Æ¡n:</b> <code>{code}</code>\nâœï¸ <b>Thá»i gian:</b> {time}\nðŸ· <b>Thanh toÃ¡n:</b> {amount:,} VNÄ\nðŸ“Š <b>Tráº¡ng thÃ¡i:</b> {status}\n',
            'ðŸ”Ž <b>ORDER DETAILS</b>\n\nðŸ”¸ <b>Order code:</b> <code>{code}</code>\nâœï¸ <b>Time:</b> {time}\nðŸ· <b>Payment:</b> {amount:,} VND\nðŸ“Š <b>Status:</b> {status}\n',
            'ðŸ”Ž <b>è®¢å•è¯¦æƒ…</b>\n\nðŸ”¸ <b>è®¢å•å·ï¼š</b> <code>{code}</code>\nâœï¸ <b>æ—¶é—´ï¼š</b> {time}\nðŸ· <b>ä»˜æ¬¾ï¼š</b> {amount:,} VND\nðŸ“Š <b>çŠ¶æ€ï¼š</b> {status}\n',
            code=order_code, time=time_str, amount=amount, status=status,
        )

        is_api_order = _api_is_order_record(order)
        if order.get("is_social_source_service"):
            supplier_order_id = str(order.get("ctt_supplier_order_id") or "").strip()
            supplier_status = str(order.get("ctt_supplier_status") or "").strip()
            supplier_remains = str(order.get("ctt_supplier_remains") or "").strip()
            supplier_charge = str(order.get("ctt_supplier_charge") or "").strip()
            refresh_error = str(order.get("ctt_status_refresh_error") or "").strip()
            supplier_progress_text = ctt_build_supplier_progress_text(order)
            detail_msg += '\n<tg-emoji emoji-id="6059654836918423763">ðŸ“Š</tg-emoji> <b>Tráº¡ng thÃ¡i nguá»“n social</b>\n'
            if supplier_order_id:
                detail_msg += f'<tg-emoji emoji-id="5373251851074415873">ðŸ“</tg-emoji> <b>MÃ£ supplier:</b> <code>{html.escape(supplier_order_id)}</code>\n'
            if supplier_status:
                detail_msg += f'<tg-emoji emoji-id="5231200819986047254">ðŸ“Š</tg-emoji> <b>Tráº¡ng thÃ¡i nguá»“n:</b> {html.escape(supplier_status)}\n'
            if supplier_remains:
                detail_msg += f'<tg-emoji emoji-id="5334890573281114250">ðŸ”¢</tg-emoji> <b>Remains:</b> {html.escape(supplier_remains)}\n'
            if supplier_progress_text:
                detail_msg += f'<tg-emoji emoji-id="5334890573281114250">ðŸ”¢</tg-emoji> <b>{html.escape(supplier_progress_text)}</b>\n'
            if supplier_charge:
                detail_msg += f'<tg-emoji emoji-id="5278467510604160626">ðŸ’°</tg-emoji> <b>Charge:</b> {html.escape(supplier_charge)}\n'
            if refresh_error:
                detail_msg += f'<tg-emoji emoji-id="5447644880824181073">âš ï¸</tg-emoji> <b>Refresh:</b> {html.escape(refresh_error)}\n'

        if is_api_order:
            detail_msg += lt(user_id, 'ðŸ”Œ <b>Nguá»“n:</b> API Partner\n', 'ðŸ”Œ <b>Source:</b> API Partner\n', 'ðŸ”Œ <b>æ¥æºï¼š</b> API Partner\n')

        item_name = get_order_item_name(order)
        if item_name != "GÃ³i iCloud 2TB":
            detail_msg += lt(user_id, '\nðŸ· <b>Sáº£n pháº©m:</b> {item}\n0ï¸âƒ£ <b>Sá»‘ lÆ°á»£ng:</b> {quantity}\n', '\nðŸ· <b>Product:</b> {item}\n0ï¸âƒ£ <b>Quantity:</b> {quantity}\n', '\nðŸ· <b>å•†å“ï¼š</b> {item}\n0ï¸âƒ£ <b>æ•°é‡ï¼š</b> {quantity}\n', item=html.escape(item_name), quantity=order.get('quantity', 1))
            if order.get('email') and order.get('email') != "N/A":
                detail_msg += f'ðŸŒ <b>Email:</b> <code>{html.escape(str(order.get("email")))}</code>\n'
        else:
            detail_msg += lt(user_id, '\nðŸ· <b>GÃ³i:</b> iCloud 2TB\nðŸŒ <b>Email:</b> {email}\n', '\nðŸ· <b>Package:</b> iCloud 2TB\nðŸŒ <b>Email:</b> {email}\n', '\nðŸ· <b>å¥—é¤ï¼š</b> iCloud 2TB\nðŸŒ <b>é‚®ç®±ï¼š</b> {email}\n', email=html.escape(str(order.get('email', 'N/A'))))
            
        link_value = str(order.get("link") or "")
        delivery_mode = str(order.get("delivery_method") or "")
        placeholder_links = {"Store Product", "Resell Product", "Resell Product (Pending Source)", "Sáº£n pháº©m khÃ¡c"}
        should_show_link = bool(link_value) and (
            delivery_mode == "instant_link"
            or (link_value not in placeholder_links and not link_value.startswith("Manual - "))
        )
        if should_show_link:
             detail_msg += f'\n<tg-emoji emoji-id=\"5447410659077661506\">ðŸŒ</tg-emoji> <b>Link:</b> <code>{html.escape(link_value)}</code>\n'

        delivered_items = order.get("items")
        delivered_count = len(delivered_items) if isinstance(delivered_items, list) else 0
        if delivered_count:
            detail_msg += (
                f'<tg-emoji emoji-id="5854908544712707500">ðŸ“¦</tg-emoji> <b>Ná»™i dung Ä‘Ã£ lÆ°u:</b> {delivered_count} item\n'
            )

        if is_api_order:
            partner_ref = str(order.get("api_partner_ref") or "")
            customer_id = str(order.get("api_customer_id") or "")
            customer_email = str(order.get("api_customer_email") or order.get("email") or "")
            api_note = str(order.get("api_note") or "")
            delivery_mode = str(order.get("delivery_method") or "unknown")
            if partner_ref:
                detail_msg += f'<tg-emoji emoji-id="5972022360025336988">ðŸ”¸</tg-emoji> <b>Partner ref:</b> <code>{html.escape(partner_ref)}</code>\n'
            if customer_email and customer_email != "N/A":
                detail_msg += f'<tg-emoji emoji-id="5447410659077661506">ðŸŒ</tg-emoji> <b>KhÃ¡ch API:</b> <code>{html.escape(customer_email)}</code>\n'
            if customer_id:
                detail_msg += f'<tg-emoji emoji-id="5334890573281114250">ðŸ†”</tg-emoji> <b>Customer ID:</b> <code>{html.escape(customer_id)}</code>\n'
            detail_msg += f'ðŸ”Œ <b>Delivery:</b> <code>{html.escape(delivery_mode)}</code>\n'
            if api_note:
                detail_msg += f'<tg-emoji emoji-id="5460753627817723162">ðŸ’¡</tg-emoji> <b>Ghi chÃº:</b> {html.escape(api_note)}\n'
             
        # Check warranty expiry
        warranty_info = resolve_order_warranty_info(order)
        warranty_expires = warranty_info.get("expires_at")
        is_expired = bool(warranty_info.get("expired"))
        is_refunded = bool(order.get('refunded_at'))
        if warranty_expires:
            if time.time() > warranty_expires:
                is_expired = True
                detail_msg += lt(user_id, "\nâš ï¸ <b>Báº£o hÃ nh:</b> ÄÃ£ háº¿t háº¡n", "\nâš ï¸ <b>Warranty:</b> Expired", "\nâš ï¸ <b>ä¿ä¿®ï¼š</b> å·²è¿‡æœŸ")
            else:
                exp_date = datetime.fromtimestamp(warranty_expires).strftime('%d/%m/%Y')
                detail_msg += lt(user_id, "\nðŸ›¡ï¸ <b>Báº£o hÃ nh:</b> Äáº¿n {date}", "\nðŸ›¡ï¸ <b>Warranty:</b> Until {date}", "\nðŸ›¡ï¸ <b>ä¿ä¿®ï¼š</b> è‡³ {date}", date=exp_date)
        elif warranty_info.get("known") and is_expired:
            detail_msg += lt(user_id, "\nâš ï¸ <b>Báº£o hÃ nh:</b> ÄÃ£ háº¿t háº¡n", "\nâš ï¸ <b>Warranty:</b> Expired", "\nâš ï¸ <b>ä¿ä¿®ï¼š</b> å·²è¿‡æœŸ")
        elif warranty_info.get("reason") == "lifetime_warranty":
            detail_msg += lt(user_id, "\nðŸ›¡ï¸ <b>Báº£o hÃ nh:</b> KhÃ´ng giá»›i háº¡n", "\nðŸ›¡ï¸ <b>Warranty:</b> Lifetime", "\nðŸ›¡ï¸ <b>ä¿ä¿®ï¼š</b> ç»ˆèº«")

        btns = []
        if order.get('items') and 'HoÃ n thÃ nh' in str(status):
            btns.append([_btn(lt(user_id, "Láº¥y láº¡i thÃ´ng tin Ä‘Æ¡n hÃ ng", "Retrieve Order Details", "é‡æ–°èŽ·å–è®¢å•ä¿¡æ¯"), icon_id="5373059489568205167", callback_data=f"resend_order_items:{order_code}:{history_page}")])
        repurchase_product_id, repurchase_product = _resolve_repurchase_product(order)
        if repurchase_product_id and isinstance(repurchase_product, dict):
            btns.append([
                _btn(
                    lt(user_id, "Mua láº¡i sáº£n pháº©m nÃ y", "Buy This Product Again", "å†æ¬¡è´­ä¹°æ­¤å•†å“"),
                    icon_id="5402186569006210455",
                    callback_data=f"buy_again:{order_code}:{history_page}",
                    style="success",
                )
            ])
        if not is_expired and not is_api_order and not is_refunded:
            btns.append([_btn(lt(user_id, "BÃ¡o lá»—i Ä‘Æ¡n nÃ y", "Report This Order", "æŠ¥å‘Šæ­¤è®¢å•"), icon_id="5273914604752216432", callback_data=f"report_specific_order:{order_code}")])
        btns.append([_btn(lt(user_id, "Quay láº¡i danh sÃ¡ch", "Back to List", "è¿”å›žåˆ—è¡¨"), icon_id="6206032691075223572", callback_data=f"lichsu_page:{history_page}")])
        
        await safe_edit_message(
            query,
            text=detail_msg,
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode=ParseMode.HTML
        )
    elif command.startswith('use_last_email:'):
        email = command.split(':', 1)[1]; context.user_data['purchase_email'] = email; context.user_data['state'] = 'awaiting_coupon_choice'
        keyboard = [[_btn(lt(user_id, "CÃ³", "Yes", "æœ‰"), callback_data='coupon_yes'), _btn(lt(user_id, "KhÃ´ng", "No", "æ²¡æœ‰"), callback_data='coupon_no')]]
        await query.message.edit_text(lt(user_id, "Tuyá»‡t vá»i! Báº¡n cÃ³ mÃ£ giáº£m giÃ¡ khÃ´ng?", "Great! Do you have a coupon code?", "å¾ˆå¥½ï¼æ‚¨æœ‰ä¼˜æƒ ç å—ï¼Ÿ"), reply_markup=InlineKeyboardMarkup(keyboard))
    elif command == 'enter_new_email':
        context.user_data['state'] = 'awaiting_email'; await query.message.edit_text(lt(user_id, "ðŸ“§ Vui lÃ²ng nháº­p email nháº­n link kÃ­ch hoáº¡t.", "ðŸ“§ Enter the email that will receive the activation link.", "ðŸ“§ è¯·è¾“å…¥æŽ¥æ”¶æ¿€æ´»é“¾æŽ¥çš„é‚®ç®±ã€‚"), reply_markup=create_back_button_menu(lt(user_id, "Há»§y", "Cancel", "å–æ¶ˆ"), "back_to_main"))
    elif command == 'coupon_yes':
        context.user_data['state'] = 'awaiting_coupon_code'; await query.message.edit_text(lt(user_id, "ðŸ“ Vui lÃ²ng nháº­p mÃ£ giáº£m giÃ¡.", "ðŸ“ Enter your coupon code.", "ðŸ“ è¯·è¾“å…¥ä¼˜æƒ ç ã€‚"))
    elif command == 'coupon_no':
        email = context.user_data.get('purchase_email')
        await show_icloud_payment_method_menu(update, context, email)
    elif command == 'icloud_pay_bank':
        email = context.user_data.get('purchase_email')
        coupon_code = context.user_data.get('purchase_coupon_code')
        try:
            await query.delete_message()
        except BadRequest:
            pass
        await clear_user_state(context)
        await generate_icloud_payment_checkout(update, context, email, coupon_code, payment_provider="bank")
    elif command == 'icloud_pay_binance':
        await safe_answer(
            query,
            "USDT (TRC20) da duoc tat. Vui long chon Ngan hang (QR).",
            show_alert=True,
        )
        email = context.user_data.get('purchase_email')
        coupon_code = context.user_data.get('purchase_coupon_code')
        if email:
            await show_icloud_payment_method_menu(update, context, email, coupon_code)
        return
    elif command == 'report_error':
        context.user_data['state'] = 'awaiting_report_order_code'
        try: await query.delete_message()
        except BadRequest: pass
        await safe_send_message(
            context,
            user_id,
            "<b>BÃ¡o cÃ¡o lá»—i & YÃªu cáº§u há»— trá»£</b>\n\nBáº¯t Ä‘áº§u báº±ng cÃ¡ch nháº­p <b>MÃ£ Ä‘Æ¡n hÃ ng</b> cá»§a báº¡n (vÃ­ dá»¥: ICLD123456).\n\nGÃµ /cancel Ä‘á»ƒ há»§y.",
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
        await safe_answer(query, "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> Äang gá»­i láº¡i thÃ´ng tin...")
        
        # TÃ¬m order trong DB
        order = db_get_order(order_code)
        if not order:
            await safe_edit_message(
                query,
                text=f"âŒ KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng <code>{html.escape(order_code)}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return
        
        # Kiá»ƒm tra quyá»n. ÄÆ¡n API lÆ°u user_id theo PARTNER_<name>, khÃ´ng pháº£i Telegram user_id tháº­t.
        if _api_is_order_record(order):
            has_access = _api_user_can_access_order(user_id, order)
        else:
            has_access = order.get('user_id') == user_id
        if not has_access:
            await safe_edit_message(
                query,
                text=f"âŒ Báº¡n khÃ´ng cÃ³ quyá»n xem láº¡i Ä‘Æ¡n <code>{html.escape(order_code)}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        # FIX: Prevent resending items from refunded orders
        if order.get('refunded_at'):
            await safe_edit_message(
                query,
                text=f"âŒ ÄÆ¡n hÃ ng <code>{html.escape(order_code)}</code> Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n vÃ  khÃ´ng thá»ƒ gá»­i láº¡i thÃ´ng tin",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return

        items = normalize_delivered_items(order.get('items'))
        if not items or len(items) == 0:
            await safe_edit_message(
                query,
                text=(
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÆ¡n hÃ ng <code>{html.escape(order_code)}</code> khÃ´ng cÃ³ thÃ´ng tin tÃ i khoáº£n Ä‘Æ°á»£c lÆ°u.\n\n"
                    "Vui lÃ²ng liÃªn há»‡ admin Ä‘á»ƒ Ä‘Æ°á»£c há»— trá»£."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
            return
        
        # Gá»­i láº¡i items dÆ°á»›i dáº¡ng file .txt
        product_name = order.get('product_name') or order.get('product', 'Sáº£n pháº©m')
        file_content = f"ÄÆ N HÃ€NG: {order_code}\n"
        file_content += f"Sáº£n pháº©m: {product_name}\n"
        file_content += f"Sá»‘ lÆ°á»£ng: {len(items)}\n"
        file_content += "=" * 40 + "\n\n"
        for idx, item in enumerate(items, 1):
            file_content += f"[{idx}] {item}\n"
        
        delivery = await deliver_items_as_txt(
            context, user_id, order_code, items,
            file_content=file_content,
            file_prefix="GuiLai",
            caption_html=(
                f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>Gá»¬I Láº I THÃ”NG TIN ÄÆ N HÃ€NG</b>\n\n"
                f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> MÃ£ Ä‘Æ¡n: <code>{html.escape(order_code)}</code>\n"
                f"<tg-emoji emoji-id=\"6260059243605398502\">ðŸ“Œ</tg-emoji> Sáº£n pháº©m: <b>{html.escape(str(product_name))}</b>\n"
                f"<tg-emoji emoji-id=\"6059654836918423763\">ðŸ“Š</tg-emoji> Sá»‘ lÆ°á»£ng: {len(items)}\n"
            )
        )
        
        if delivery.get('delivered'):
            await safe_edit_message(
                query,
                text=(
                    f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ gá»­i láº¡i thÃ´ng tin Ä‘Æ¡n hÃ ng <code>{html.escape(order_code)}</code> thÃ nh cÃ´ng!\n\n"
                    "Kiá»ƒm tra file phÃ­a trÃªn nhÃ©."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i danh sÃ¡ch", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
        else:
            await safe_edit_message(
                query,
                text=f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> KhÃ´ng thá»ƒ gá»­i láº¡i thÃ´ng tin. Vui lÃ²ng thá»­ láº¡i sau hoáº·c liÃªn há»‡ admin.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[_btn("Quay láº¡i danh sÃ¡ch", icon_id="6206032691075223572", callback_data=back_to_history_callback)]])
            )
        return
    elif command.startswith('report_specific_order:'):
        order_code = command.split(':', 1)[1]
        order = db_get_order(order_code)

        if not order:
            await safe_answer(query, "âŒ KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng nÃ y.", show_alert=True)
            return

        if not _api_user_can_access_order(user_id, order):
            await safe_answer(query, "âŒ Báº¡n khÃ´ng cÃ³ quyá»n bÃ¡o lá»—i Ä‘Æ¡n nÃ y.", show_alert=True)
            return

        if order.get('refunded_at'):
            await safe_answer(
                query,
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n nÃªn khÃ´ng thá»ƒ bÃ¡o lá»—i ná»¯a.",
                show_alert=True,
            )
            return

        if await _auto_reject_expired_support_message(query.message, context, order, order_code):
            await safe_answer(query, "Don nay da het han bao hanh.", show_alert=True)
            return
        
        try:
            await query.message.edit_text(
                f"Äang xá»­ lÃ½ yÃªu cáº§u bÃ¡o lá»—i cho Ä‘Æ¡n hÃ ng <code>{order_code}</code>...", 
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
            "Tiáº¿p theo, vui lÃ²ng gá»­i <b>má»™t áº£nh chá»¥p mÃ n hÃ¬nh</b> vá» lá»—i báº¡n Ä‘ang gáº·p pháº£i.",
            parse_mode=ParseMode.HTML
        )
    elif command == 'ask_ai_confirm':

        await query.edit_message_text("Äang káº¿t ná»‘i vá»›i Trá»£ lÃ½ AI, vui lÃ²ng chá» trong giÃ¢y lÃ¡t...")

        question = context.user_data.get('support_query')

        if question:

            try:

                await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)

            except (Forbidden, BadRequest):

                pass

            ai_answer = await ask_ai(question)

            await query.edit_message_text(f'<tg-emoji emoji-id="6271362510901747485">ðŸ¤–</tg-emoji> <b>Trá»£ lÃ½ AI Dino tráº£ lá»i:</b>\n\n{ai_answer}', parse_mode=ParseMode.HTML)  # FIX: ask_gemini -> ask_ai

        else: await query.edit_message_text("ÄÃ£ cÃ³ lá»—i xáº£y ra. Vui lÃ²ng báº¯t Ä‘áº§u láº¡i.")

        await clear_user_state(context)

    elif command == 'create_ticket_confirm':

        query_text, user = context.user_data.get('support_query'), update.effective_user

        ticket_id = f"TICKET-{random.randint(1000, 9999)}"

        admin_message_text = (f'<tg-emoji emoji-id="5377624166436445368">ðŸŽŸï¸</tg-emoji> <b>PHIáº¾U Há»– TRá»¢ Má»šI</b> ({ticket_id}) <tg-emoji emoji-id="5377624166436445368">ðŸŽŸï¸</tg-emoji>\n\n'

                              f'<b>Tá»«:</b> {format_user_mention_html(user)} (ID: <code>{user.id}</code>)\n'

                              f'<b>Username:</b> @{user.username or "KhÃ´ng cÃ³"}\n\n'

                              f'<b>Ná»™i dung:</b>\n<i>{query_text}</i>')

        reply_button = InlineKeyboardButton('<tg-emoji emoji-id="5350752364246606166">âœï¸</tg-emoji> Pháº£n há»“i User', callback_data=f"reply_to_ticket:{user.id}")

        await safe_send_admin(context.bot, admin_message_text, reply_markup=InlineKeyboardMarkup([[reply_button]]))

        await query.edit_message_text(f'<tg-emoji emoji-id="6269163801178804220">âœ…</tg-emoji> ÄÃ£ táº¡o phiáº¿u há»— trá»£ vá»›i mÃ£ <b>{ticket_id}</b>. Admin sáº½ sá»›m pháº£n há»“i. Cáº£m Æ¡n báº¡n!', parse_mode=ParseMode.HTML)

        await clear_user_state(context)

    elif command.startswith('reply_to_ticket:'):

        target_user_id = int(command.split(':', 1)[1]); context.user_data['state'] = f'awaiting_admin_reply:{target_user_id}'

        await safe_edit_message(

            query.message,

            text=get_query_message_html(query) + "\n\n<i>(Äang chá» pháº£n há»“i...)</i>",

            parse_mode=ParseMode.HTML,

            reply_markup=None

        )

        await safe_answer(query); await safe_send_admin(context.bot, f'<tg-emoji emoji-id="5458382591121964689">âœï¸</tg-emoji> Vui lÃ²ng nháº­p ná»™i dung pháº£n há»“i cho ngÆ°á»i dÃ¹ng ID: <code>{target_user_id}</code>')



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



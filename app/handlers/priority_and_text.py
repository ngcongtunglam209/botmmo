from __future__ import annotations

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


API_PREM_WARN = '<tg-emoji emoji-id="5447644880824181073">âš ï¸</tg-emoji>'
API_PREM_OK = '<tg-emoji emoji-id="6269163801178804220">âœ…</tg-emoji>'
API_PREM_STOP = '<tg-emoji emoji-id="5424857974784925603">â›”</tg-emoji>'
API_PREM_LOCK = 'ðŸ”'

CHINESE_TEXT_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002b73f"
    r"\U0002b740-\U0002b81f\U0002b820-\U0002ceaf"
    r"\U0002ceb0-\U0002ebef\U00030000-\U0003134f]"
)

def _message_contains_chinese_text(message) -> bool:
    text = " ".join(
        part for part in (
            getattr(message, "text", None),
            getattr(message, "caption", None),
        )
        if part
    )
    return bool(text and CHINESE_TEXT_RE.search(text))

async def _bot_can_delete_in_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
    cache_key = f"can_delete_messages:{chat_id}"
    cached = context.bot_data.get(cache_key)
    now = time.time()
    if isinstance(cached, dict) and cached.get("expires_at", 0) > now:
        return bool(cached.get("allowed"))

    allowed = False
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        status = str(getattr(bot_member, "status", "") or "").lower()
        allowed = status == "creator" or (
            status == "administrator" and bool(getattr(bot_member, "can_delete_messages", False))
        )
    except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as exc:
        logger.debug(f"Cannot check delete permission in chat {chat_id}: {exc}")

    context.bot_data[cache_key] = {
        "allowed": allowed,
        "expires_at": now + 300,
    }
    return allowed

async def chinese_language_guard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return
    if str(getattr(chat, "type", "") or "") not in {"group", "supergroup"}:
        return
    if not _message_contains_chinese_text(message):
        return
    if not await _bot_can_delete_in_chat(context, chat.id):
        return

    try:
        await message.delete()
        logger.info(f"Deleted Chinese-language message {message.message_id} in chat {chat.id}")
        raise ApplicationHandlerStop
    except (Forbidden, BadRequest, TelegramError) as exc:
        logger.debug(f"Cannot delete Chinese-language message {getattr(message, 'message_id', None)} in chat {chat.id}: {exc}")

async def priority_email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler Æ°u tiÃªn cao nháº¥t, cháº¡y á»Ÿ Group -1.
    ChuyÃªn trá»‹ váº¥n Ä‘á» bot khÃ´ng nháº­n email do conflict handler.
    Cáº£i tiáº¿n: Tá»± Ä‘á»™ng trÃ­ch xuáº¥t email tá»« cÃ¢u (khÃ´ng cáº§n chÃ­nh xÃ¡c 100% lÃ  email).
    """
    message = update.message or update.channel_post
    if not message or not message.text: return
    
    text = message.text.strip()
    
    # IMPROVED: DÃ¹ng search thay vÃ¬ match Ä‘á»ƒ báº¯t Ä‘Æ°á»£c "Email cá»§a tui lÃ  abc@gmail.com"
    # Regex khÃ´ng cÃ³ ^ vÃ  $ Ä‘á»ƒ tÃ¬m trong chuá»—i
    email_extract_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    match = email_extract_pattern.search(text)
    
    if not match:
        return 
        
    extracted_email = match.group(0).lower() 
    user = update.effective_user
    if not user: return
    
    # Check Pending Manual Orders of this user
    user_pending = None
    user_pending_code = None
    
    # TÃ¬m order nÃ o Ä‘ang chá» email cá»§a user nÃ y
    for order_code, info in pending_manual_orders.items():
        # So sÃ¡nh user_id dáº¡ng string cho cháº¯c cháº¯n
        if str(info.get('user_id')) == str(user.id) and info.get('status') == 'awaiting_email':
             user_pending = info
             user_pending_code = order_code
             break
             
    if user_pending:
        logging.info(f"â­ï¸ PRIORITY HANDLER: Found email '{extracted_email}' for Order {user_pending_code}")
        
        try:
            # 1. Update Order
            user_pending['email'] = extracted_email
            user_pending['status'] = 'pending_admin'
            user_pending['timestamp_email'] = time.time()
            
            # Save only the changed table to avoid full DB write in hot path.
            await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])
            
            # 2. Notify User
            await message.reply_text(
                f"{E_SUCCESS} <b>ÄÃƒ NHáº¬N EMAIL:</b> {extracted_email}\n"
                f"{E_LOADING} ÄÆ¡n hÃ ng <code>{user_pending_code}</code> Ä‘Ã£ Ä‘Æ°á»£c chuyá»ƒn cho Admin xá»­ lÃ½.\n"
                f"{E_LOADING} Vui lÃ²ng Ä‘á»£i trong 1-30 phÃºt...",
                parse_mode=ParseMode.HTML
            )
            
            # 3. Notify Admin
            await notify_admin_manual_order(
                context, 
                user_pending_code, 
                user_pending['user_id'],
                user_pending.get('full_name', 'Unknown'),
                extracted_email, # Use extracted email
                user_pending.get('product_name', 'Product'),
                int(user_pending.get('quantity', 1)),
                int(user_pending.get('amount', 0))
            )
            
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logging.error(f"âŒ Error in priority_email_handler: {e}", exc_info=True)
            # Fallback: Notify user of error
            try:
                await message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> CÃ³ lá»—i xáº£y ra khi lÆ°u Ä‘Æ¡n hÃ ng. Vui lÃ²ng thá»­ láº¡i hoáº·c liÃªn há»‡ Admin.")
            except (ValueError, TypeError, KeyError, IndexError) as notify_err:
                logger.debug(f"Cannot send fallback error to user {update.effective_user.id}: {notify_err}")
        
        # 4. Clear State if any (Cleanup)
        if context.user_data and context.user_data.get('state') == 'awaiting_manual_email':
             context.user_data['state'] = None
             
        # 5. STOP PROPAGATION
        # NgÄƒn khÃ´ng cho cÃ¡c handler khÃ¡c (nhÆ° AI chat) xá»­ lÃ½ tiáº¿p
        raise ApplicationHandlerStop

async def _auto_reject_expired_support_message(message, context, order: dict, order_code: str) -> bool:
    warranty_info = apply_auto_reject_if_warranty_expired(order)
    if not warranty_info.get("expired"):
        return False

    try:
        await save_data(force=True, tables=[HISTORY_FILE])
    except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot persist auto warranty rejection for {order_code}: {e}")

    try:
        if message:
            await message.reply_text(
                build_auto_warranty_rejection_text(order_code, warranty_info),
                parse_mode=ParseMode.HTML,
            )
    except (TelegramError, ValueError, TypeError, KeyError, AttributeError) as e:
        logger.warning(f"Cannot notify user about auto warranty rejection for {order_code}: {e}")

    await clear_user_state(context)
    return True


def _remove_utf16_span(text: str, offset_units: int, length_units: int) -> str:
    try:
        encoded = str(text or "").encode("utf-16-le")
        start = max(0, int(offset_units or 0)) * 2
        end = start + (max(0, int(length_units or 0)) * 2)
        return (encoded[:start] + encoded[end:]).decode("utf-16-le", errors="ignore")
    except (TypeError, ValueError, UnicodeError):
        return str(text or "")


def _extract_custom_store_icon_config(raw_text: str) -> tuple[str, str]:
    try:
        payload = json.loads(str(raw_text or "").strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return "", ""
    if not isinstance(payload, dict):
        return "", ""

    message_payload = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    icon_id = str(
        payload.get("custom_emoji_id")
        or message_payload.get("custom_emoji_id")
        or ""
    ).strip()
    keyword = str(
        payload.get("keyword")
        or payload.get("label")
        or payload.get("name")
        or message_payload.get("keyword")
        or message_payload.get("label")
        or message_payload.get("name")
        or ""
    ).strip()

    text_value = str(message_payload.get("text") or payload.get("text") or "").strip()
    entities = message_payload.get("entities") or payload.get("entities") or []
    if isinstance(entities, list):
        custom_entities = [
            entity for entity in entities
            if isinstance(entity, dict) and str(entity.get("type") or "") == "custom_emoji"
        ]
        if custom_entities and not icon_id:
            icon_id = str(custom_entities[0].get("custom_emoji_id") or "").strip()
        if text_value and not keyword:
            cleaned_text = text_value
            for entity in sorted(custom_entities, key=lambda item: int(item.get("offset", 0) or 0), reverse=True):
                cleaned_text = _remove_utf16_span(
                    cleaned_text,
                    int(entity.get("offset", 0) or 0),
                    int(entity.get("length", 0) or 0),
                )
            keyword = cleaned_text.strip()

    keyword = re.sub(r"\s+", " ", keyword).strip().lower()
    icon_id = re.sub(r"\D", "", icon_id)
    if not keyword or not icon_id:
        return "", ""
    return keyword[:80], icon_id


async def handle_custom_store_icon_json_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_input: str,
    *,
    from_icon_command: bool = False,
) -> bool:
    user = update.effective_user
    if not user or user.id != ADMIN_USER_ID:
        return False
    if not from_icon_command and not str(user_input or "").lstrip().startswith("{"):
        return False

    keyword, icon_id = _extract_custom_store_icon_config(user_input)
    if not keyword or not icon_id:
        if from_icon_command or (
            context.user_data is not None
            and context.user_data.get("state") == "awaiting_custom_store_icon_json"
        ):
            await update.message.reply_html(
                f"{E_LIMIT} <b>JSON icon khÃ´ng há»£p lá»‡.</b>\n\n"
                "Gá»­i JSON Telegram update cÃ³ <code>custom_emoji_id</code>, hoáº·c dáº¡ng ngáº¯n:\n"
                '<code>{"label":"Cursor","custom_emoji_id":"6273793612715138423"}</code>'
            )
            return True
        return False

    custom_store_icons[keyword] = icon_id
    if context.user_data is not None:
        context.user_data.pop("state", None)
    await save_data(force=True, tables=[CUSTOM_STORE_ICONS_FILE])
    try:
        from app.core.runtime_loader import sync_runtime_bindings

        sync_runtime_bindings(globals(), ["custom_store_icons"])
    except (ValueError, TypeError, KeyError, AttributeError, ImportError):
        pass

    await update.message.reply_html(
        f"{E_SUCCESS} <b>ÄÃ£ lÆ°u custom icon</b>\n\n"
        f"Keyword: <code>{html.escape(keyword)}</code>\n"
        f"Emoji ID: <code>{html.escape(icon_id)}</code>\n\n"
        "CÃ¡c nÃºt/sáº£n pháº©m chá»©a keyword nÃ y sáº½ tá»± dÃ¹ng icon má»›i."
    )
    return True


async def icon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await clear_user_state(context)
    raw_json = " ".join(context.args or []).strip()
    if raw_json:
        handled = await handle_custom_store_icon_json_message(
            update,
            context,
            raw_json,
            from_icon_command=True,
        )
        if not handled:
            await update.message.reply_html(f"{E_LIMIT} KhÃ´ng Ä‘á»c Ä‘Æ°á»£c JSON icon.")
        return

    if context.user_data is not None:
        context.user_data["state"] = "awaiting_custom_store_icon_json"
    await update.message.reply_html(
        f"{E_TAG} <b>Gá»­i JSON custom emoji</b>\n\n"
        "Gá»­i JSON Telegram update nhÆ° máº«u cÃ³ <code>entities[].custom_emoji_id</code>, hoáº·c dáº¡ng ngáº¯n:\n"
        '<code>{"label":"Cursor","custom_emoji_id":"6273793612715138423"}</code>\n\n'
        "Bot sáº½ tá»± lÆ°u keyword vÃ  dÃ¹ng icon Ä‘Ã³ cho sáº£n pháº©m/nÃºt cÃ³ keyword tÆ°Æ¡ng á»©ng."
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return
    
    # <tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> FIX: SKIP channel posts - context.user_data is None!
    if update.channel_post or update.edited_channel_post:
        return
    
    if context.user_data is None:
        return
    
    # Kiá»ƒm tra cháº¿ Ä‘á»™ báº£o trÃ¬
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("<tg-emoji emoji-id=\"5215392879320505675\">ðŸ› ï¸</tg-emoji> <b>Há»† THá»NG ÄANG Báº¢O TRÃŒ</b>\n\nChÃºng tÃ´i Ä‘ang nÃ¢ng cáº¥p há»‡ thá»‘ng Ä‘á»ƒ phá»¥c vá»¥ báº¡n tá»‘t hÆ¡n. Vui lÃ²ng quay láº¡i sau Ã­t phÃºt.\n\nXin lá»—i vÃ¬ sá»± báº¥t tiá»‡n nÃ y!", parse_mode=ParseMode.HTML)
        return

    # FIX BUG: Check if message exists (edited messages might be handled differently or ignored here if needed)
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_input = update.message.text.strip()
    if user.id == ADMIN_USER_ID and context.user_data.get("state") == "awaiting_custom_store_icon_json":
        await handle_custom_store_icon_json_message(update, context, user_input, from_icon_command=True)
        return
    if await handle_custom_store_icon_json_message(update, context, user_input):
        return
    user_state = context.user_data.get('state')
    if user_state:
        logger.info(
            "[TEXT_STATE] user=%s state=%s input_len=%s",
            user.id,
            user_state,
            len(user_input),
        )

    state_from_store_callback = bool(
        user_state
        and (
            user_state.startswith('awaiting_custom_qty:')
            or user_state.startswith('awaiting_ctt_')
            or user_state in {'awaiting_store_coupon'}
        )
    )
    if user.id != ADMIN_USER_ID and not is_user_registered(user.id) and not state_from_store_callback:
        await handle_registration_challenge_answer(update, context, user_input)
        return

    if user.id == ADMIN_USER_ID and user_state == "awaiting_manual_warranty_replacement":
        await handle_manual_warranty_replacement_input(update, context, user_input)
        return
    
    # NEW: Handle Admin Quick Action (Cá»™ng / Trá»« tiá»n)
    if "quick_action" in context.user_data:
        quick_action = context.user_data['quick_action']
        if user_input.lower() == '/cancel':
            context.user_data.pop('quick_action', None)
            await update.message.reply_text("<tg-emoji emoji-id=\"5424857974784925603\">ðŸš«</tg-emoji> ÄÃ£ há»§y thao tÃ¡c.")
            return
            
        parts = quick_action.split(":")
        if len(parts) >= 2:
            action = parts[0]
            target_id_str = parts[1]
            try:
                target_id = int(target_id_str)
                amount = int(user_input.replace(',', '').replace('.', ''))
            except ValueError:
                await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Sá»‘ tiá»n khÃ´ng há»£p lá»‡. Vui lÃ²ng nháº­p sá»‘ (vd: 10000) hoáº·c gÃµ /cancel Ä‘á»ƒ há»§y.")
                return

            user_info = user_data_db.get(str(target_id), {})
            name = user_info.get('first_name', 'N/A')
            
            if action == "addmoney":
                old_balance = user_info.get('balance', 0)
                user_info['balance'] = old_balance + amount
                user_data_db[str(target_id)] = user_info
                await save_data()
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃ£ cá»™ng {amount:,} VNÄ</b> cho {name}\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° má»›i: {user_info['balance']:,} VNÄ", parse_mode='HTML')
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"<tg-emoji emoji-id=\"5422896593412035313\">ðŸŽ</tg-emoji> <b>Báº N ÄÆ¯á»¢C Cá»˜NG TIá»€N</b>\n\n<tg-emoji emoji-id=\"5397916757333654639\">âž•</tg-emoji> Sá»‘ tiá»n: <code>+{amount:,} VNÄ</code>\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° má»›i: <code>{user_info['balance']:,} VNÄ</code>\n\n<i>(Cá»™ng bá»Ÿi Admin)</i>",
                        parse_mode='HTML'
                    )
                except (ValueError, TypeError, KeyError, IndexError):
                    pass
                    
            elif action == "submoney":
                old_balance = user_info.get('balance', 0)
                user_info['balance'] = max(0, old_balance - amount)
                user_data_db[str(target_id)] = user_info
                await save_data()
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃ£ trá»« {amount:,} VNÄ</b> cá»§a {name}\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° má»›i: {user_info['balance']:,} VNÄ", parse_mode='HTML')
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"<tg-emoji emoji-id=\"5409062331583842187\">ðŸ’¸</tg-emoji> <b>TÃ€I KHOáº¢N Bá»Š TRá»ª TIá»€N</b>\n\n<tg-emoji emoji-id=\"5406745771280187626\">âž–</tg-emoji> Sá»‘ tiá»n: <code>-{amount:,} VNÄ</code>\n<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Sá»‘ dÆ° má»›i: <code>{user_info['balance']:,} VNÄ</code>\n\n<i>(Trá»« bá»Ÿi Admin)</i>",
                        parse_mode='HTML'
                    )
                except (TelegramError, ValueError, KeyError, AttributeError):
                    pass

        context.user_data.pop('quick_action', None)
        return
    
    if user_state == 'awaiting_refund_bank_info':
        await handle_refund_bank_info_input(update, context)
        return

    # NEW: Handle Withdrawal Inputs
    if user_state in ('awaiting_withdrawal_amount', 'awaiting_bank_info'):
        await handle_withdrawal_input(update, context)
        return

    if user_state == "awaiting_ctt_catalog_search":
        lowered_input = user_input.strip().casefold()
        if lowered_input in {"/cancel", "cancel", "huy", "há»§y"}:
            _clear_ctt_search_state(context)
            await update.message.reply_text(
                _get_ctt_root_panel_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=create_ctt_source_category_menu(page=0),
            )
            return


        search_query = user_input.strip()
        await _ensure_ctt_catalog_ready()
        matches = _get_ctt_search_result_entries(search_query)
        if not matches:
            await update.message.reply_text(
                "KhÃ´ng tÃ¬m tháº¥y dá»‹ch vá»¥ social phÃ¹ há»£p.\n"
                "Vui lÃ²ng nháº­p tá»« khÃ³a khÃ¡c hoáº·c gÃµ <code>há»§y</code> Ä‘á»ƒ quay láº¡i.",
                parse_mode=ParseMode.HTML,
            )
            return

        _clear_ctt_search_state(context, clear_query=False)
        context.user_data["ctt_search_query"] = search_query
        await update.message.reply_text(
            _get_ctt_search_result_panel_text(search_query),
            parse_mode=ParseMode.HTML,
            reply_markup=create_ctt_search_result_menu(search_query, page=0),
        )
        return

    if user_state and user_state.startswith('awaiting_ctt_'):
        lowered_input = user_input.strip().casefold()
        if lowered_input in {'/cancel', 'cancel', 'huy', 'há»§y'}:
            await clear_user_state(context)
            await update.message.reply_text("ÄÃ£ há»§y táº¡o Ä‘Æ¡n social.")
            return

        draft = context.user_data.get('pending_ctt_checkout')
        if not isinstance(draft, dict):
            await update.message.reply_text("KhÃ´ng tÃ¬m tháº¥y phiÃªn Ä‘áº·t dá»‹ch vá»¥ social. Vui lÃ²ng chá»n láº¡i sáº£n pháº©m.")
            await clear_user_state(context)
            return

        prod_id = str(draft.get("prod_id") or "").strip()
        p = products.get(prod_id)
        if not _is_ctt_store_product(p):
            await update.message.reply_text("Sáº£n pháº©m social khÃ´ng cÃ²n kháº£ dá»¥ng. Vui lÃ²ng chá»n láº¡i.")
            await clear_user_state(context)
            return

        field_name = user_state.replace('awaiting_ctt_', '', 1).strip()
        value, error_text = _ctt_validate_field_value(field_name, user_input)
        if error_text:
            await update.message.reply_text(error_text)
            return

        collected_inputs = dict(draft.get("collected_inputs") or {})
        collected_inputs[field_name] = value
        draft["collected_inputs"] = collected_inputs
        fields = list(draft.get("fields") or _ctt_required_input_fields(p))

        next_field = next((fname for fname in fields if fname and fname not in collected_inputs), None)
        if next_field:
            context.user_data['pending_ctt_checkout'] = draft
            context.user_data['state'] = f'awaiting_ctt_{next_field}'
            await update.message.reply_text(
                _ctt_build_checkout_prompt(p, int(draft.get("qty", 1) or 1), next_field),
                parse_mode=ParseMode.HTML,
            )
            return

        qty = int(draft.get("qty", 1) or 1)
        payment_flow = str(draft.get("payment_flow") or "balance")
        balance_used = int(draft.get("balance_used", 0) or 0)
        extra_pending_data = _ctt_build_pending_payment_data(p, qty, collected_inputs)

        context.user_data.pop('state', None)
        context.user_data.pop('pending_ctt_checkout', None)
        context.user_data.pop('pending_ctt_payment_balance_used', None)

        if payment_flow == "balance":
            completed_draft = dict(draft)
            completed_draft["collected_inputs"] = collected_inputs
            await _complete_ctt_balance_purchase(update, context, completed_draft)
            return

        if payment_flow == "usdt_trc20":
            await update.message.reply_text(
                "USDT (TRC20) da duoc tat. Vui long quay lai va chon So du hoac Chuyen khoan (QR).",
                reply_markup=InlineKeyboardMarkup([
                    [_btn("Chon lai thanh toan", callback_data=f"buy_prod_confirm_{prod_id}_{qty}")]
                ]),
            )
            return

        if balance_used > 0:
            user_info_ctt = db_get_user(user.id)
            current_balance_ctt = int((user_info_ctt or {}).get('balance', 0) or 0)
            if current_balance_ctt < balance_used:
                await update.message.reply_text("Sá»‘ dÆ° hiá»‡n táº¡i khÃ´ng cÃ²n Ä‘á»§ Ä‘á»ƒ giá»¯ pháº§n vÃ­ cho Ä‘Æ¡n social nÃ y.")
                return
            db_update_balance(user.id, current_balance_ctt - balance_used, reason=f"SOCIAL_SOURCE combo payment hold: {prod_id}")

        await generate_product_payment_qr(
            update,
            context,
            prod_id,
            qty,
            balance_used=balance_used,
            extra_pending_data=extra_pending_data,
        )
        return

    if user_state == 'awaiting_api_rotate_confirmation':
        lowered_input = user_input.strip().casefold()
        confirm_chat_id = context.user_data.get('api_rotate_confirm_chat_id')
        confirm_message_id = context.user_data.get('api_rotate_confirm_message_id')
        if lowered_input in {'/cancel', 'cancel', 'huy', 'há»§y'}:
            prompt_updated = False
            if confirm_chat_id and confirm_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=confirm_chat_id,
                        message_id=confirm_message_id,
                        text=f"{API_PREM_STOP} <b>ÄÃƒ Há»¦Y Äá»”I API KEY</b>",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None,
                    )
                    prompt_updated = True
                except (TelegramError, ValueError, KeyError, AttributeError):
                    logger.debug("Cannot update API rotate confirmation prompt for user %s", user.id)
            await clear_user_state(context)
            if not prompt_updated:
                await update.message.reply_text(
                    f"{API_PREM_STOP} ÄÃ£ há»§y Ä‘á»•i API key.",
                    parse_mode='HTML',
                    reply_markup=create_main_menu(user_id=user.id),
                )
            return

        if lowered_input != 'sure':
            await update.message.reply_text(
                f"{API_PREM_WARN} Äá»ƒ xÃ¡c nháº­n Ä‘á»•i API key, hÃ£y nháº­p Ä‘Ãºng <code>sure</code>.\n"
                "Náº¿u Ä‘á»•i Ã½, báº¡n cÃ³ thá»ƒ gÃµ <code>/cancel</code>.",
                parse_mode='HTML',
            )
            return

        expected_key = str(context.user_data.get('api_rotate_source_key') or '').strip()
        source_chat_id = context.user_data.get('api_rotate_source_chat_id')
        source_message_id = context.user_data.get('api_rotate_source_message_id')
        if confirm_chat_id and confirm_message_id:
            try:
                    await context.bot.edit_message_text(
                        chat_id=confirm_chat_id,
                        message_id=confirm_message_id,
                        text=f"{API_PREM_OK} <b>ÄÃƒ XÃC NHáº¬N Äá»”I API KEY</b>\n\nHá»‡ thá»‘ng Ä‘ang táº¡o key má»›i...",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None,
                )
            except (TelegramError, ValueError, KeyError, AttributeError):
                logger.debug("Cannot mark API rotate confirmation prompt as completed for user %s", user.id)
        partner_key, partner_data = get_partner_api_entry_by_user(user.id)
        await clear_user_state(context)
        if not partner_key or not isinstance(partner_data, dict):
            await update.message.reply_text(
                f"{API_PREM_WARN} KhÃ´ng tÃ¬m tháº¥y API key Ä‘ang hoáº¡t Ä‘á»™ng. Vui lÃ²ng thá»­ láº¡i tá»« menu API.",
                parse_mode='HTML',
            )
            return
        if expected_key and str(partner_key).strip() != expected_key:
            await update.message.reply_text(
                f"{API_PREM_WARN} YÃªu cáº§u xÃ¡c nháº­n Ä‘Ã£ háº¿t hiá»‡u lá»±c. HÃ£y báº¥m láº¡i nÃºt Ä‘á»•i API key náº¿u báº¡n váº«n muá»‘n tiáº¿p tá»¥c.",
                parse_mode='HTML',
            )
            return

        await _complete_partner_api_key_rotation(
            context,
            update.effective_chat.id,
            user.id,
            partner_key,
            partner_data,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
        )
        return
    
    # NEW: Handle Dice Game iCloud Prize Email
    if user_state == 'awaiting_dice_email':
        email_input = user_input.lower()
        
        if not EMAIL_REGEX.match(email_input):
            await update.message.reply_text(
                "âŒ Email khÃ´ng há»£p lá»‡!\n\n"
                "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Vui lÃ²ng nháº­p email Ä‘Ãºng Ä‘á»‹nh dáº¡ng.\n"
                "<i>VÃ­ dá»¥: example@gmail.com</i>",
                parse_mode='HTML'
            )
            return
        
        # Get saved link
        link = context.user_data.get('dice_prize_link')
        if not link:
            await update.message.reply_text("âŒ Lá»—i: KhÃ´ng tÃ¬m tháº¥y link. Vui lÃ²ng thá»­ láº¡i.")
            await clear_user_state(context)
            return
        
        # Clear winner flag and state (both ephemeral and persistent)
        context.user_data.pop('dice_winner', None)
        context.user_data.pop('dice_prize_link', None)
        context.user_data.pop('state', None)
        record_promo_cost(ICLOUD_PACKAGE_PRICE, 'dice_icloud')
        dice_game_data.pop(f"winner_{user.id}", None)
        
        # Send email
        try:
            email_sent, email_error = await send_activation_email(
                email_input,
                "<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> [Dice Prize] Link kÃ­ch hoáº¡t iCloud 2TB",
                user.full_name,
                link,
            )
            if not email_sent:
                await update.message.reply_text(
                    "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÃ£ ghi nháº­n email nhÆ°ng gá»­i mail pháº§n thÆ°á»Ÿng tháº¥t báº¡i.\n"
                    "Vui lÃ²ng liÃªn há»‡ Admin Ä‘á»ƒ Ä‘Æ°á»£c gá»­i láº¡i link.",
                    reply_markup=create_back_button_menu(),
                )
                await safe_send_admin(
                    context.bot,
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>DICE EMAIL FAILED</b>\n"
                    f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> User: {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
                    f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Email: <code>{html.escape(email_input)}</code>\n"
                    f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸ”—</tg-emoji> Link: <code>{html.escape(link)}</code>\n"
                    f"<tg-emoji emoji-id=\"5350481781306958339\">ðŸ§¾</tg-emoji> Lá»—i: <code>{html.escape(str(email_error or 'Unknown error'))}</code>",
                )
                return

            await update.message.reply_text(
                f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> <b>CHÃšC Má»ªNG!</b>\n\n"
                f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Link kÃ­ch hoáº¡t Ä‘Ã£ Ä‘Æ°á»£c gá»­i Ä‘áº¿n:\n"
                f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> <code>{email_input}</code>\n\n"
                f"<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> Vui lÃ²ng kiá»ƒm tra há»™p thÆ° (ká»ƒ cáº£ Spam)!",
                parse_mode='HTML',
                reply_markup=create_back_button_menu()
            )
            
            # Log order
            order_code = f"DICE{int(time.time())}"
            order_data = {
                "order_code": order_code,
                "user_id": user.id,
                "email": email_input,
                "amount": 0,
                "status": "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> HoÃ n thÃ nh (Dice Game)",
                "link": link,
                "timestamp": time.time(),
                "full_name": user.full_name,
                "username": user.username,
                "product_name": "iCloud 2TB (Dice Prize)",
                "quantity": 1
            }
            db_add_order(order_data)
            
            # Notify admin
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5226711870492126219\">ðŸŽ²</tg-emoji> <b>DICE PRIZE DELIVERED (iCloud)</b>\n\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>User:</b> {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
                f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> <b>Email:</b> <code>{email_input}</code>\n"
                f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ</tg-emoji> <b>Prize:</b> iCloud 2TB",
                parse_mode='HTML'
            )
            
            logger.info(f"<tg-emoji emoji-id=\"5226711870492126219\">ðŸŽ²</tg-emoji> DICE iCloud PRIZE: User {user.id} - Email: {email_input}")
            
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.error(f"Error sending dice iCloud prize email: {e}")
            await update.message.reply_text(
                f"âŒ Lá»—i gá»­i email: {str(e)[:50]}\n\n"
                f"Vui lÃ²ng liÃªn há»‡ Admin!",
                reply_markup=create_back_button_menu()
            )
        return

    
    # NEW: Handle Manual Order Email (tá»« balance purchase flow)
    if user_state == 'awaiting_manual_email':
        email_input = user_input.lower()
        
        if not EMAIL_REGEX.match(email_input):
            await update.message.reply_text(
                "âŒ Email khÃ´ng há»£p lá»‡!\n\n"
                "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Vui lÃ²ng nháº­p email Ä‘Ãºng Ä‘á»‹nh dáº¡ng.\n"
                "<i>VÃ­ dá»¥: example@gmail.com</i>",
                parse_mode='HTML'
            )
            return
        
        # Get pending order info
        pending_order = context.user_data.get('pending_manual_order')
        if not pending_order:
            await update.message.reply_text("âŒ Lá»—i: KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng. Vui lÃ²ng thá»­ láº¡i.")
            await clear_user_state(context)
            return
        
        order_code = pending_order.get('order_code')
        prod_id = pending_order.get('product_id') or pending_order.get('prod_id')  # FIX: Support both keys
        qty = pending_order.get('quantity') or pending_order.get('qty', 1)  # FIX: Support both keys
        amount = pending_order.get('amount', 0)
        
        # Get product info
        p = products.get(prod_id, {})
        prod_name = p.get('name', 'Sáº£n pháº©m')
        
        # 1. XÃ³a tin nháº¯n "Chá» nháº­p email" cá»§a user
        waiting_msg_id = context.user_data.get('waiting_message_id')
        waiting_chat_id = context.user_data.get('waiting_chat_id')
        if waiting_msg_id and waiting_chat_id:
            try:
                await context.bot.delete_message(waiting_chat_id, waiting_msg_id)
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.debug(f"Could not delete waiting message: {e}")
        
        # 2. XÃ³a tin nháº¯n "Äang chá» email" cá»§a admin
        admin_waiting_msg_id = context.user_data.get('admin_waiting_message_id')
        if admin_waiting_msg_id:
            try:
                await context.bot.delete_message(ADMIN_USER_ID, admin_waiting_msg_id)
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.debug(f"Could not delete admin waiting message: {e}")
        
        # Clear state vÃ  data
        context.user_data.pop('state', None)
        context.user_data.pop('pending_manual_order', None)
        context.user_data.pop('waiting_message_id', None)
        context.user_data.pop('waiting_chat_id', None)
        context.user_data.pop('admin_waiting_message_id', None)
        
        # 3. ThÃ´ng bÃ¡o cho khÃ¡ch hÃ ng
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ÄÃƒ NHáº¬N EMAIL!</b>\n\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sáº£n pháº©m:</b> {prod_name} x{qty}\n"
            f"{E_TAG} <b>Sá»‘ tiá»n:</b> {amount:,} VNÄ\n\n"
            f"{E_LOADING} <b>Admin Ä‘ang xá»­ lÃ½ Ä‘Æ¡n hÃ ng...</b>\n"
            f"{E_SOS} Báº¡n sáº½ nháº­n thÃ´ng bÃ¡o khi hoÃ n táº¥t!\n\n"
            f"{E_TIP} <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>",
            parse_mode='HTML',
            reply_markup=create_back_button_menu()
        )
        
        # 4. Log order
        order_data = {
            "order_code": order_code,
            "user_id": user.id,
            "email": email_input,
            "amount": amount,
            "status": "<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Chá» Admin xá»­ lÃ½",
            "link": "Manual Order",
            "timestamp": time.time(),
            "full_name": user.full_name,
            "username": user.username,
            "product_name": prod_name,
            "product_id": prod_id,
            "quantity": qty,
            "type": "manual_order"
        }
        db_add_order(order_data)
        await save_data(force=True, tables=[HISTORY_FILE])
        
        # 5. Gá»­i thÃ´ng bÃ¡o chi tiáº¿t cho Admin vá»›i button xá»­ lÃ½
        admin_keyboard = [
            [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ xá»­ lÃ½", callback_data=f"manual_done_{order_code}")],
            [InlineKeyboardButton("âŒ Há»§y & HoÃ n tiá»n", callback_data=f"manual_refund_{order_code}")]
        ]
        
        await context.bot.send_message(
            ADMIN_USER_ID,
            f"{E_TAG} <b>ÄÆ N MANUAL Cáº¦N Xá»­ LÃ</b>\n\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¤</tg-emoji> <b>KhÃ¡ch:</b> {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sáº£n pháº©m:</b> {prod_name} x{qty}\n"
            f"{E_TAG} <b>Sá»‘ tiá»n:</b> {amount:,} VNÄ\n\n"
            f"{E_LOADING} Vui lÃ²ng xá»­ lÃ½ Ä‘Æ¡n hÃ ng vÃ  báº¥m nÃºt bÃªn dÆ°á»›i!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
        
        logger.info(f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> MANUAL ORDER: {order_code} - User {user.id} - Email: {email_input}")
        return
    
    # Check náº¿u user Ä‘ang cÃ³ pending manual order cáº§n email
    user_pending = None
    for order_code, info in pending_manual_orders.items():
        if info.get('user_id') == user.id and info.get('status') == 'awaiting_email':
            user_pending = (order_code, info)
            break
    
    # FIX BUG: Bá» Ä‘iá»u kiá»‡n `and not user_state` Ä‘á»ƒ luÃ´n Æ°u tiÃªn xá»­ lÃ½ Ä‘Æ¡n hÃ ng Ä‘ang chá» email
    # (Thanh toÃ¡n QR khÃ´ng set context.user_data['state'] vÃ¬ cháº¡y trong background thread)
    if user_pending and EMAIL_REGEX.match(user_input):
        # User reply vá»›i email cho pending manual order
        order_code, order_info = user_pending
        email_input = user_input.lower()
        
        if not EMAIL_REGEX.match(email_input):
            await update.message.reply_text("<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Email khÃ´ng há»£p lá»‡. Vui lÃ²ng nháº­p láº¡i email chÃ­nh xÃ¡c.")
            return
        
        # Update order vá»›i email
        order_info['email'] = email_input
        order_info['status'] = 'pending_admin'
        await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])
        
        # ThÃ´ng bÃ¡o khÃ¡ch
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ÄÃƒ NHáº¬N EMAIL!</b>\n\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sáº£n pháº©m:</b> {order_info['product_name']} x{order_info['quantity']}\n\n"
            f"{E_LOADING} <b>Admin Ä‘ang xá»­ lÃ½ Ä‘Æ¡n hÃ ng...</b>\n"
            f"{E_SOS} Báº¡n sáº½ nháº­n thÃ´ng bÃ¡o khi hoÃ n táº¥t\n\n"
            f"{E_TIP} <b>MÃ£ Ä‘Æ¡n:</b> <code>{order_code}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu()
        )
        
        # Gá»­i cho Admin
        await notify_admin_manual_order(
            context, order_code, user.id, user.full_name,
            email_input, order_info['product_name'], order_info['quantity'], order_info['amount']
        )
        
        return
    if user_state == 'awaiting_email':
        if not EMAIL_REGEX.match(user_input):  # Tá»‘i Æ°u: compiled regex
            await update.message.reply_text("<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> Email khÃ´ng há»£p lá»‡, vui lÃ²ng kiá»ƒm tra vÃ  gá»­i láº¡i."); return
        context.user_data['purchase_email'] = user_input.lower(); context.user_data['state'] = 'awaiting_coupon_choice'
        keyboard = [[_btn("CÃ³", icon_id="5021905410089550576", callback_data='coupon_yes'), _btn("KhÃ´ng", icon_id="5273914604752216432", callback_data='coupon_no')]]
        await update.message.reply_text("<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji> Báº¡n cÃ³ mÃ£ giáº£m giÃ¡ khÃ´ng?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif user_state == 'awaiting_coupon_code':
        email = context.user_data.get('purchase_email')
        if not email:
            await update.message.reply_text("âŒ Lá»—i: KhÃ´ng tÃ¬m tháº¥y email. Vui lÃ²ng báº¯t Ä‘áº§u láº¡i báº±ng /start")
            await clear_user_state(context)
            return
        await show_icloud_payment_method_menu(update, context, email, user_input)
    elif user_state == 'awaiting_icloud_payment_method':
        await update.message.reply_text("<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‰</tg-emoji> HÃ£y báº¥m nÃºt thanh toÃ¡n bÃªn trÃªn Ä‘á»ƒ chá»n NgÃ¢n hÃ ng (QR).")
    elif user_state == 'awaiting_store_coupon':
        prod_id = context.user_data.get('store_coupon_prod_id')
        qty = context.user_data.get('store_coupon_qty', 1)
        await clear_user_state(context)
        if not prod_id or prod_id not in products:
            await update.message.reply_text("\u274c S\u1ea3n ph\u1ea9m kh\xf4ng t\u1ed3n t\u1ea1i. Vui l\xf2ng th\u1eed l\u1ea1i.")
            return
        p = products[prod_id]
        coupon_input = user_input.strip().upper()
        coupon_details = coupons.get(coupon_input)
        if not coupon_details:
            await update.message.reply_text(f"\u274c M\xe3 <b>{html.escape(coupon_input)}</b> kh\xf4ng h\u1ee3p l\u1ec7.", parse_mode=ParseMode.HTML)
            return
        qty_limit = coupon_details.get('quantity', 0)
        used = coupon_details.get('used', 0)
        is_used_up = (qty_limit != '\u221e' and isinstance(qty_limit, int) and used >= qty_limit)
        expires_str = coupon_details.get('expires', '')
        is_expired = False
        if expires_str:
            try:
                exp_date = datetime.strptime(expires_str, '%d-%m-%Y').replace(hour=23, minute=59, second=59)
                is_expired = datetime.now() > exp_date
            except (TelegramError, ValueError, KeyError, AttributeError):
                logger.debug("Suppressed error at L9433")
        if is_used_up or is_expired:
            await update.message.reply_text(f"\u274c M\xe3 <b>{coupon_input}</b> \u0111\xe3 h\u1ebft h\u1ea1n ho\u1eb7c h\u1ebft l\u01b0\u1ee3t s\u1eed d\u1ee5ng.", parse_mode=ParseMode.HTML)
            return
        discount_val = coupon_details.get('discount', 0)
        base_price = p['price']
        if coupon_details.get('is_percent', False):
            discount_amount = int(base_price * discount_val / 100)
            discount_text = f"{discount_val}% = {discount_amount:,}\u0111"
        else:
            discount_amount = discount_val
            discount_text = f"{discount_amount:,}\u0111"
        is_ctt_product = _is_ctt_store_product(p)
        discounted_unit = max(0, base_price - discount_amount)
        total_price = _get_ctt_store_total_price(user.id, context, prod_id, p, qty) if is_ctt_product else discounted_unit * qty
        base_price_text = f"{base_price:,}\u0111"
        discounted_unit_text = f"{discounted_unit:,}\u0111"
        if is_ctt_product:
            base_price_text = f"~{_ctt_format_vnd_decimal(_ctt_get_base_unit_price_decimal(p))}\u0111"
            discounted_unit_text = f"~{_ctt_format_vnd_decimal(_ctt_get_base_unit_price_decimal(p) - discount_amount)}\u0111"
        user_id_c = update.effective_user.id
        user_info_c = db_get_user(user_id_c)
        balance_c = user_info_c.get('balance', 0) if user_info_c else 0
        context.user_data['store_coupon_applied'] = coupon_input
        context.user_data['store_coupon_discount'] = discount_amount
        context.user_data['store_coupon_prod_id'] = prod_id
        context.user_data['store_coupon_qty'] = qty
        btns = []
        bal_text = f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> Sá»‘ dÆ° ({balance_c:,}Ä‘)"
        if balance_c >= total_price:
            btns.append([InlineKeyboardButton(bal_text, callback_data=f"pay_prod_bal_{prod_id}_{qty}")])
        elif balance_c > 0:
            remaining_c = total_price - balance_c
            btns.append([InlineKeyboardButton(
                f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> DÃ¹ng {balance_c:,}Ä‘ + QR {remaining_c:,}Ä‘",
                callback_data=f"pay_prod_combo_{prod_id}_{qty}"
            )])
        else:
            btns.append([_btn("KhÃ´ng", icon_id="5273914604752216432", callback_data="ignore")])
        from app.integrations.payments_core import is_usdt_trc20_enabled, is_binance_pay_id_enabled
        if is_usdt_trc20_enabled() or is_binance_pay_id_enabled():
            btns.append([_btn("USDT (Binance ID / BEP20)", icon_id="5281029063459234079", callback_data=f"pay_prod_usdt_trc20_{prod_id}_{qty}")])
        from app.core.config_env import ENABLE_PAYMENT_MBBANK
        if ENABLE_PAYMENT_MBBANK:
            btns.append([_btn("Chuyá»ƒn khoáº£n (QR)", icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}")])
        btns.append([InlineKeyboardButton("\u2b05\ufe0f Quay l\u1ea1i", callback_data=f"buy_prod_confirm_{prod_id}_{qty}")])
        await update.message.reply_text(
            f"\u2705 <b>M\xc3 GI\u1ea2M GI\xc1 \u0110\xc3 \xc1P D\u1ee4NG!</b>\n\n"
            f"\U0001f3f7 S\u1ea3n ph\u1ea9m: {html.escape(p['name'])}\n"
            f"\U0001f522 S\u1ed1 l\u01b0\u1ee3ng: {qty}\n"
            f"\U0001f3ab M\xe3: <code>{coupon_input}</code> (Gi\u1ea3m {discount_text})\n"
            f"\U0001f4b0 \u0110\u01a1n gi\xe1: <s>{base_price_text}</s> \u2192 <b>{discounted_unit_text}</b>\n"
            f"\U0001f4b5 T\u1ed5ng: <b>{total_price:,}\u0111</b>\n\n"
            f"Ch\u1ecdn ph\u01b0\u01a1ng th\u1ee9c thanh to\xe1n:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btns)
        )
    elif user_state == 'awaiting_report_order_code':
        order_code = user_input.upper()
        if not USER_ORDER_CODE_REGEX.match(order_code):  # Tá»‘i Æ°u: compiled regex
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> MÃ£ Ä‘Æ¡n hÃ ng khÃ´ng há»£p lá»‡. Vui lÃ²ng nháº­p láº¡i hoáº·c /cancel Ä‘á»ƒ há»§y."); return
        # FIX: DÃ¹ng index O(1)
        found_order = order_index.get(order_code)
        if not found_order or found_order.get("user_id") != user.id: await update.message.reply_text("âŒ KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng nÃ y hoáº·c Ä‘Æ¡n hÃ ng khÃ´ng thuá»™c vá» báº¡n. Vui lÃ²ng kiá»ƒm tra láº¡i mÃ£ hoáº·c /cancel Ä‘á»ƒ há»§y."); return
        if found_order.get('refunded_at'):
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n nÃªn khÃ´ng thá»ƒ bÃ¡o lá»—i ná»¯a.\n"
                "Vui lÃ²ng nháº­p mÃ£ Ä‘Æ¡n khÃ¡c hoáº·c gÃµ /cancel Ä‘á»ƒ há»§y."
            )
            return
        
        # <tg-emoji emoji-id=\"5424857974784925603\">â›”</tg-emoji> BLOCK SPAM: Check if order support was rejected
        support_status = found_order.get('support_status', 'active')
        if support_status == 'rejected_expired':
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5424857974784925603\">â›”</tg-emoji> <b>Tá»ª CHá»I Há»– TRá»¢</b>\n\n"
                "ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ bá»‹ tá»« chá»‘i báº£o hÃ nh do <b>Háº¾T Háº N Báº¢O HÃ€NH</b>.\n"
                "Vui lÃ²ng khÃ´ng tiáº¿p tá»¥c bÃ¡o lá»—i spam.", parse_mode=ParseMode.HTML
            )
            await clear_user_state(context)
            return
        elif support_status == 'rejected_policy':
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5424857974784925603\">â›”</tg-emoji> <b>Tá»ª CHá»I Há»– TRá»¢</b>\n\n"
                "ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ bá»‹ tá»« chá»‘i há»— trá»£ do <b>VI PHáº M CHÃNH SÃCH</b>.\n"
                "Vui lÃ²ng khÃ´ng tiáº¿p tá»¥c bÃ¡o lá»—i spam.", parse_mode=ParseMode.HTML
            )
            await clear_user_state(context)
            return
        if await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return

        context.user_data['report_order_code'] = order_code
        context.user_data.pop('report_photo_id', None)
        context.user_data.pop('report_photo_chat_id', None)
        context.user_data.pop('report_photo_message_id', None)
        context.user_data['state'] = 'awaiting_report_photo'
        await update.message.reply_text(
            "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ xÃ¡c nháº­n Ä‘Æ¡n hÃ ng. "
            "Tiáº¿p theo, vui lÃ²ng gá»­i <b>má»™t áº£nh chá»¥p mÃ n hÃ¬nh</b> vá» lá»—i báº¡n Ä‘ang gáº·p pháº£i.",
            parse_mode=ParseMode.HTML
        )
    elif user_state == 'awaiting_report_photo':
        await update.message.reply_text(
            "âŒ Vui lÃ²ng gá»­i <b>áº£nh chá»¥p mÃ n hÃ¬nh lá»—i</b> trÆ°á»›c Ä‘á»ƒ tiáº¿p tá»¥c bÃ¡o cÃ¡o.",
            parse_mode=ParseMode.HTML
        )
        return
    elif user_state == 'awaiting_report_description':
        description = user_input
        order_code = context.user_data.get('report_order_code')
        photo_id = context.user_data.get('report_photo_id')
        photo_chat_id = context.user_data.get('report_photo_chat_id')
        photo_message_id = context.user_data.get('report_photo_message_id')
        if not all([order_code, photo_id]):
            await update.message.reply_text("âŒ ÄÃ£ cÃ³ lá»—i trong quÃ¡ trÃ¬nh bÃ¡o cÃ¡o. Vui lÃ²ng báº¯t Ä‘áº§u láº¡i.")
            await clear_user_state(context)
            return
        if not all([photo_chat_id, photo_message_id]):
            context.user_data['state'] = 'awaiting_report_photo'
            context.user_data.pop('report_photo_id', None)
            context.user_data.pop('report_photo_chat_id', None)
            context.user_data.pop('report_photo_message_id', None)
            await update.message.reply_text(
                "âŒ Thiáº¿u dá»¯ liá»‡u áº£nh gá»‘c. Vui lÃ²ng gá»­i láº¡i áº£nh lá»—i Ä‘á»ƒ há»‡ thá»‘ng chuyá»ƒn tiáº¿p cho admin."
            )
            return
        # FIX: DÃ¹ng index O(1)
        found_order = order_index.get(order_code)
        if not found_order:
            await update.message.reply_text("âŒ KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng nÃ y trong lá»‹ch sá»­. Vui lÃ²ng báº¯t Ä‘áº§u láº¡i.")
            await clear_user_state(context)
            return
        if found_order.get('refunded_at'):
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÆ¡n hÃ ng nÃ y Ä‘Ã£ Ä‘Æ°á»£c hoÃ n tiá»n nÃªn khÃ´ng thá»ƒ bÃ¡o lá»—i ná»¯a."
            )
            await clear_user_state(context)
            return
        if await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        email_val = found_order.get('email', 'KhÃ´ng cÃ³')
        purchase_time = found_order.get('timestamp', 0)
        purchase_date_str = datetime.fromtimestamp(purchase_time).strftime('%d/%m/%Y') if purchase_time else "N/A"
        
        # 1. <tg-emoji emoji-id=\"5303290914041505430\">ðŸš€</tg-emoji> SEND TO ADMIN IMMEDIATELY (Hybrid Mode)
        # Determine product type & action buttons
        btns = []
        prod_id_check = found_order.get('product_id')
        p_check = products.get(prod_id_check) if prod_id_check else None
        product_name = found_order.get('product_name') or (p_check.get('name') if p_check else 'N/A')
        order_type = found_order.get('type', 'unknown')
        
        # Fallback: tÃ¬m product báº±ng product_name náº¿u khÃ´ng cÃ³ product_id
        if not p_check and product_name and product_name != 'N/A':
            for pid, pdata in products.items():
                if pdata.get('name') == product_name:
                    p_check = pdata
                    prod_id_check = pid
                    break
        
        is_auto_stock = False
        is_icloud_link = False
        is_manual_product = False
        product_name_folded = str(product_name or "").casefold()
        if order_type == 'icloud':
            is_icloud_link = True
        elif order_type == 'store_product':
            if p_check and p_check.get('requires_gmail'):
                is_manual_product = True
            else:
                is_auto_stock = True
        elif p_check:
            if p_check.get('requires_gmail'):
                is_manual_product = True
            else:
                is_auto_stock = True
        if "icloud" in product_name_folded or "i cloud" in product_name_folded:
            is_icloud_link = True
            is_manual_product = False
        
        if is_auto_stock:
            type_label = "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> Store (Auto Stock)"
            btns.append([_btn("Cáº¥p Acc Má»›i (Auto)", icon_id="6129870117619634982", callback_data=f"replace_auto:{order_code}")])
        elif is_icloud_link:
            type_label = "<tg-emoji emoji-id=\"5231489647946768652\">â˜ï¸</tg-emoji> iCloud (Link)"
            btns.append([_btn("Gá»­i Láº¡i Link", icon_id="6129870117619634982", callback_data=f"resend_link:{found_order.get('user_id')}:{email_val}")])
        elif is_manual_product:
            type_label = "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> Sáº£n pháº©m thá»§ cÃ´ng"
            btns.append([_btn("Cáº¥p Acc/Link Má»›i (Thá»§ cÃ´ng)", icon_id="6129870117619634982", callback_data=f"replace_manual:{order_code}")])
        else:
            type_label = "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> KhÃ¡c / thá»§ cÃ´ng"
            btns.append([_btn("Cáº¥p Acc/Link Má»›i (Thá»§ cÃ´ng)", icon_id="6129870117619634982", callback_data=f"replace_manual:{order_code}")])

        if _resolve_order_duration_days(found_order) > 0:
            btns.append([_btn(
                "HoÃ n tiá»n ngÃ y chÆ°a sá»­ dá»¥ng",
                icon_id="5278467510604160626",
                callback_data=f"admrf_p_{order_code}",
            )])
        else:
            btns.append([_btn(
                "HoÃ n tiá»n lá»—i (100%)",
                icon_id="5278467510604160626",
                callback_data=f"admrf_f_{order_code}",
            )])
            
        btns.append([
            _btn("Tá»« chá»‘i: Háº¿t BH", icon_id="5465665476971471368", callback_data=f"reject_expired:{found_order.get('user_id')}:{order_code}"),
            _btn("Tá»« chá»‘i: Vi pháº¡m", icon_id="5273914604752216432", callback_data=f"reject_policy:{found_order.get('user_id')}:{order_code}")
        ])
        btns.append([_btn("ÄÃ£ báº£o hÃ nh", icon_id="6269163801178804220", callback_data=f"warranty_done:{order_code}")])
        btns.append([_btn("Bá» qua", icon_id="5364075889669718872", callback_data=f"dismiss_report:{order_code}")])

        safe_username = html.escape(f"@{user.username}" if user.username else "KhÃ´ng cÃ³")
        safe_type_label = type_label
        safe_email_val = html.escape(str(email_val))
        safe_purchase_date = html.escape(str(purchase_date_str))
        safe_description = html.escape(str(description))

        admin_report_text = (
            f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>BÃO CÃO Lá»–I Má»šI</b> <tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji>\n\n" 
            f"<b>Tá»«:</b> {format_user_mention_html(user)} (ID: <code>{user.id}</code>)\n" 
            f"<b>Username:</b> {safe_username}\n\n" 
            f"<b>CHI TIáº¾T ÄÆ N HÃ€NG:</b>\n" 
            f"  - MÃ£ Ä‘Æ¡n: <code>{found_order.get('order_code', 'N/A')}</code>\n" 
            f"  - Sáº£n pháº©m: <b>{html.escape(str(product_name))}</b>\n"
            f"  - Loáº¡i: {safe_type_label}\n"
            f"  - Email: <code>{safe_email_val}</code>\n" 
            f"  - NgÃ y mua: {safe_purchase_date}\n\n" 
            f"<b>MÃ” Táº¢ Cá»¦A KHÃCH:</b>\n" 
            f"<i>{safe_description}</i>"
        )
        
        sent_msg = None
        image_forwarded = False
        forward_errors = []
        try:
            await context.bot.copy_message(
                chat_id=ADMIN_USER_ID,
                from_chat_id=int(photo_chat_id),
                message_id=int(photo_message_id)
            )
            image_forwarded = True
        except (ValueError, TypeError, KeyError, IndexError) as copy_err:
            forward_errors.append(f"copy_message: {copy_err}")
            try:
                await context.bot.forward_message(
                    chat_id=ADMIN_USER_ID,
                    from_chat_id=int(photo_chat_id),
                    message_id=int(photo_message_id)
                )
                image_forwarded = True
            except (ValueError, TypeError, KeyError, IndexError) as fwd_err:
                forward_errors.append(f"forward_message: {fwd_err}")

        if not image_forwarded:
            err_text = " | ".join(forward_errors) if forward_errors else "unknown_error"
            logger.error(f"[REPORT] khÃ´ng thá»ƒ chuyá»ƒn tiáº¿p áº£nh bÃ¡o lá»—i ({err_text})")
            await safe_send_admin(
                context.bot,
                (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> "
                    f"<b>BÃO CÃO Lá»–I áº¢NH</b>\n"
                    f"Order: <code>{order_code}</code>\n"
                    f"User ID: <code>{user.id}</code>\n"
                    f"LÃ½ do: <code>{html.escape(err_text)}</code>"
                ),
            )
            context.user_data['state'] = 'awaiting_report_photo'
            context.user_data.pop('report_photo_id', None)
            context.user_data.pop('report_photo_chat_id', None)
            context.user_data.pop('report_photo_message_id', None)
            await update.message.reply_text(
                "âŒ KhÃ´ng thá»ƒ chuyá»ƒn tiáº¿p áº£nh cho admin. Vui lÃ²ng gá»­i láº¡i áº£nh lá»—i dÆ°á»›i dáº¡ng Photo."
            )
            return

        sent_msg = await safe_send_admin(
            context.bot,
            admin_report_text,
            reply_markup=InlineKeyboardMarkup(btns),
        )


        # 2. <tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¥</tg-emoji> TRACKING FOR REMINDER (Unresolved List)
        # Check if already tracked, increment count
        existing_report = next((r for r in pending_error_reports if r['order_code'] == order_code and not r['resolved']), None)
        
        if existing_report:
            existing_report['report_count'] += 1
            if sent_msg:
                existing_report['last_msg_id'] = sent_msg.message_id
            existing_report['timestamp'] = time.time() # Update time
        else:
            report_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'order_code': order_code,
                'description': description,
                'timestamp': time.time(),
                'product_name': found_order.get('product_name', 'Sáº£n pháº©m'),
                'purchase_date': purchase_date_str,
                'resolved': False, # Status tracking
                'report_count': 1,
                'last_msg_id': sent_msg.message_id if sent_msg else None
            }
            pending_error_reports.append(report_data)
        
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ÄÃƒ Gá»¬I BÃO CÃO!</b>\n\n"
            "Admin Ä‘Ã£ nháº­n Ä‘Æ°á»£c thÃ´ng tin vÃ  sáº½ kiá»ƒm tra sá»›m nháº¥t.\n",
            parse_mode=ParseMode.HTML
        )
        await clear_user_state(context)
    elif user_state == 'awaiting_support_query':
        query = update.message.text.strip(); context.user_data['support_query'] = query
        
        # Sá»­ dá»¥ng intelligent_ticket_classifier Ä‘á»ƒ xá»­ lÃ½ truy váº¥n há»— trá»£
        ai_result = await intelligent_ticket_classifier(query, user.id)
        
        if ai_result['auto_resolved']:
            # Náº¿u AI tá»± Ä‘á»™ng giáº£i quyáº¿t Ä‘Æ°á»£c
            await update.message.reply_html(ai_result['response'])
            await clear_user_state(context)
        else:
            # Náº¿u khÃ´ng thá»ƒ tá»± Ä‘á»™ng giáº£i quyáº¿t
            keyboard = [
                [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Há»i Trá»£ lÃ½ AI", callback_data='ask_ai_confirm')], 
                [InlineKeyboardButton("<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> Táº¡o phiáº¿u há»— trá»£ cho Admin", callback_data='create_ticket_confirm')]
            ]
            await update.message.reply_text(
                "CÃ¢u há»i cá»§a báº¡n cáº§n sá»± tÆ° váº¥n chi tiáº¿t hÆ¡n. Báº¡n cÃ³ muá»‘n há»i Trá»£ lÃ½ AI cá»§a chÃºng tÃ´i khÃ´ng?", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif user_state and user_state.startswith('awaiting_custom_qty:'):
        # NEW: Xá»­ lÃ½ nháº­p sá»‘ lÆ°á»£ng tÃ¹y chá»‰nh
        prod_id = user_state.split(':', 1)[1]
        p = products.get(prod_id)
        
        if not p:
            await update.message.reply_text("âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!")
            await clear_user_state(context)
            return
        
        # Validate input
        try:
            qty = int(user_input.strip())
        except ValueError:
            await update.message.reply_text(
                "âŒ <b>Sá»‘ lÆ°á»£ng khÃ´ng há»£p lá»‡!</b>\n\n"
                "Vui lÃ²ng nháº­p má»™t sá»‘ nguyÃªn.\n"
                "VÃ­ dá»¥: 200",
                parse_mode=ParseMode.HTML
            )
            return
        
        
        if _is_ctt_store_product(p):
            stock_count = _ctt_get_max_package_purchase(p)
            is_resell = False
            is_ctt_product = True
            quantity_error = _ctt_validate_purchase_quantity(p, qty)
        # BUG FIX: Sáº£n pháº©m resell dÃ¹ng supplier_source_stock
        elif p.get('is_supplier_source_resell'):
            try:
                stock_count = int(p.get('supplier_source_stock', 0) or 0)
            except (TypeError, ValueError, KeyError):
                stock_count = 0
            is_resell = True
            is_ctt_product = False
            quantity_error = ""
        else:
            stock_count = len(p.get('stock', []))
            is_resell = False
            is_ctt_product = False
            quantity_error = ""
        
        # Check range
        if qty < 1:
            await update.message.reply_text(
                "âŒ Sá»‘ lÆ°á»£ng pháº£i Ã­t nháº¥t lÃ  1!",
                parse_mode=ParseMode.HTML
            )
            return
        elif is_ctt_product and quantity_error:
            await update.message.reply_text(
                f"âŒ <b>Sá» LÆ¯á»¢NG KHÃ”NG Há»¢P Lá»†!</b>\n\n{html.escape(quantity_error)}",
                parse_mode=ParseMode.HTML,
            )
            return
        elif is_resell and stock_count <= 0:
            await update.message.reply_text(
                "âŒ <b>Sáº¢N PHáº¨M ÄANG Háº¾T HÃ€NG!</b>\n\n"
                "Nguá»“n SupplierSource hiá»‡n khÃ´ng cÃ²n hÃ ng. Vui lÃ²ng quay láº¡i sau.",
                parse_mode=ParseMode.HTML
            )
            await clear_user_state(context)
            return
        elif qty > stock_count and not is_resell and not is_ctt_product:
            # Chá»‰ block náº¿u KHÃ”NG pháº£i resell (resell check láº¡i lÃºc thanh toÃ¡n)
            await update.message.reply_text(
                f"âŒ <b>KHÃ”NG Äá»¦ HÃ€NG!</b>\n\n"
                f"Báº¡n muá»‘n: <b>{qty}</b>\n"
                f"Tá»“n kho: <b>{stock_count}</b>\n\n"
                f"Vui lÃ²ng nháº­p sá»‘ nhá» hÆ¡n hoáº·c báº±ng {stock_count}",
                parse_mode=ParseMode.HTML
            )
            return
        elif qty > stock_count and is_resell and stock_count > 0:
            await update.message.reply_text(
                f"âŒ <b>Sá» LÆ¯á»¢NG VÆ¯á»¢T QUÃ KHO!</b>\n\n"
                f"Báº¡n muá»‘n: <b>{qty}</b>\n"
                f"Kho hiá»‡n táº¡i: <b>{stock_count}</b>\n\n"
                f"Vui lÃ²ng nháº­p sá»‘ nhá» hÆ¡n hoáº·c báº±ng {stock_count}.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Valid quantity - show confirmation
        await clear_user_state(context)
        
        total_price = _get_ctt_store_total_price(user.id, context, prod_id, p, qty) if is_ctt_product else p['price'] * qty
        user_info = db_get_user(user.id)
        balance = user_info.get('balance', 0) if user_info else 0
        
        btns = []
        bal_text = f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> Sá»‘ dÆ° ({balance:,}Ä‘)"
        if balance >= total_price:
            btns.append([InlineKeyboardButton(bal_text, callback_data=f"pay_prod_bal_{prod_id}_{qty}")])
        else:
            btns.append([_btn("KhÃ´ng", icon_id="5273914604752216432", callback_data="ignore")])
        
        from app.integrations.payments_core import is_usdt_trc20_enabled, is_binance_pay_id_enabled
        if is_usdt_trc20_enabled() or is_binance_pay_id_enabled():
            btns.append([_btn("USDT (Binance ID / BEP20)", icon_id="5281029063459234079", callback_data=f"pay_prod_usdt_trc20_{prod_id}_{qty}")])
        from app.core.config_env import ENABLE_PAYMENT_MBBANK
        if ENABLE_PAYMENT_MBBANK:
            btns.append([_btn("Chuyá»ƒn khoáº£n (QR)", icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}")])
        btns.append([_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=f"sel_qty_{prod_id}")])
        
        supplier_units_line = ""
        if is_ctt_product:
            supplier_units_line = (
                f'<tg-emoji emoji-id="6059654836918423763">ðŸ“Š</tg-emoji> '
                f'<b>ÄÆ¡n vá»‹ nguá»“n:</b> {_ctt_get_total_supplier_quantity(p, qty):,}\n'
            )
        
        confirm_text = (
            f'<tg-emoji emoji-id="5247134066322447995">ðŸ›</tg-emoji> <b>XÃC NHáº¬N MUA HÃ€NG</b>\n\n'
            f'<tg-emoji emoji-id="5240228673738527951">ðŸ·</tg-emoji> <b>Sáº£n pháº©m:</b> {p["name"]}\n'
            f'<tg-emoji emoji-id="5305749482170758709">0ï¸âƒ£</tg-emoji> <b>Sá»‘ lÆ°á»£ng:</b> {qty}\n'
            f'{supplier_units_line}'
            f'<tg-emoji emoji-id="5240228673738527951">ðŸ·</tg-emoji> <b>Tá»•ng tiá»n:</b> {total_price:,} VNÄ\n\n'
            f'<tg-emoji emoji-id="6186252635805323641">ðŸ‘‡</tg-emoji> Vui lÃ²ng chá»n phÆ°Æ¡ng thá»©c thanh toÃ¡n:'
        )
        render_entities = globals().get("_render_text_with_custom_emoji_entities")
        if callable(render_entities):
            rendered_text, rendered_entities = render_entities(confirm_text)
            await update.message.reply_text(
                rendered_text,
                entities=rendered_entities,
                reply_markup=InlineKeyboardMarkup(btns),
            )
        else:
            await update.message.reply_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(btns),
                parse_mode=ParseMode.HTML,
            )
        return
    
    elif user_state and user_state.startswith('awaiting_admin_reply'):
        if update.effective_user.id != ADMIN_USER_ID: return
        target_user_id = int(user_state.split(':', 1)[1])
        try:
            await context.bot.send_message(chat_id=target_user_id, text="<tg-emoji emoji-id=\"5314638736462966754\">ðŸ“¬</tg-emoji> <b>Báº¡n cÃ³ pháº£n há»“i tá»« Admin:</b>", parse_mode=ParseMode.HTML)
            await context.bot.copy_message(chat_id=target_user_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> Tin nháº¯n cá»§a báº¡n Ä‘Ã£ Ä‘Æ°á»£c gá»­i tá»›i ngÆ°á»i dÃ¹ng.")
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"Gá»­i pháº£n há»“i tháº¥t báº¡i. Lá»—i: {e}"); await update.message.reply_text("âŒ Gá»­i pháº£n há»“i tháº¥t báº¡i, vui lÃ²ng kiá»ƒm tra bot admin logs.")
        finally: await clear_user_state(context)
    else:
        # Náº¿u khÃ´ng cÃ³ tráº¡ng thÃ¡i Ä‘áº·c biá»‡t nÃ o -> Chat vá»›i AI
        await chat_with_ai(update, context)



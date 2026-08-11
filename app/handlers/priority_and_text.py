from __future__ import annotations

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


API_PREM_WARN = '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>'
API_PREM_OK = '<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji>'
API_PREM_STOP = '<tg-emoji emoji-id="5424857974784925603">⛔</tg-emoji>'
API_PREM_LOCK = '🔐'

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
    Handler ưu tiên cao nhất, chạy ở Group -1.
    Chuyên trị vấn đề bot không nhận email do conflict handler.
    Cải tiến: Tự động trích xuất email từ câu (không cần chính xác 100% là email).
    """
    message = update.message or update.channel_post
    if not message or not message.text: return

    text = message.text.strip()

    # IMPROVED: Dùng search thay vì match để bắt được "Email của tui là abc@gmail.com"
    # Regex không có ^ và $ để tìm trong chuỗi
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

    # Tìm order nào đang chờ email của user này
    for order_code, info in pending_manual_orders.items():
        # So sánh user_id dạng string cho chắc chắn
        if str(info.get('user_id')) == str(user.id) and info.get('status') == 'awaiting_email':
             user_pending = info
             user_pending_code = order_code
             break

    if user_pending:
        logging.info(f"⭐️ PRIORITY HANDLER: Found email '{extracted_email}' for Order {user_pending_code}")

        try:
            # 1. Update Order
            user_pending['email'] = extracted_email
            user_pending['status'] = 'pending_admin'
            user_pending['timestamp_email'] = time.time()

            # Save only the changed table to avoid full DB write in hot path.
            await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])

            # 2. Notify User
            await message.reply_text(
                lt(
                    user.id,
                    f"{E_SUCCESS} <b>ĐÃ NHẬN EMAIL:</b> {extracted_email}\n{E_LOADING} Đơn hàng <code>{user_pending_code}</code> đã được chuyển cho Admin xử lý.\n{E_LOADING} Vui lòng đợi trong 1-30 phút.",
                    f"{E_SUCCESS} <b>EMAIL RECEIVED:</b> {extracted_email}\n{E_LOADING} Order <code>{user_pending_code}</code> has been passed to the admin.\n{E_LOADING} This usually takes 1-30 minutes.",
                    f"{E_SUCCESS} <b>已收到邮箱：</b>{extracted_email}\n{E_LOADING} 订单 <code>{user_pending_code}</code> 已转交管理员处理。\n{E_LOADING} 通常需要 1-30 分钟。",
                ),
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
            logging.error(f"❌ Error in priority_email_handler: {e}", exc_info=True)
            # Fallback: Notify user of error
            try:
                await message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Có lỗi xảy ra khi lưu đơn hàng. Vui lòng thử lại hoặc liên hệ Admin.")
            except (ValueError, TypeError, KeyError, IndexError) as notify_err:
                logger.debug(f"Cannot send fallback error to user {update.effective_user.id}: {notify_err}")

        # 4. Clear State if any (Cleanup)
        if context.user_data and context.user_data.get('state') == 'awaiting_manual_email':
             context.user_data['state'] = None

        # 5. STOP PROPAGATION
        # Ngăn không cho các handler khác (như AI chat) xử lý tiếp
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
                build_auto_warranty_rejection_text(
                    order_code,
                    warranty_info,
                    user_id=getattr(getattr(message, "from_user", None), "id", None),
                ),
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
                f"{E_LIMIT} <b>JSON icon không hợp lệ.</b>\n\n"
                "Gửi JSON Telegram update có <code>custom_emoji_id</code>, hoặc dạng ngắn:\n"
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
        f"{E_SUCCESS} <b>Đã lưu custom icon</b>\n\n"
        f"Keyword: <code>{html.escape(keyword)}</code>\n"
        f"Emoji ID: <code>{html.escape(icon_id)}</code>\n\n"
        "Các nút/sản phẩm chứa keyword này sẽ tự dùng icon mới."
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
            await update.message.reply_html(f"{E_LIMIT} Không đọc được JSON icon.")
        return

    if context.user_data is not None:
        context.user_data["state"] = "awaiting_custom_store_icon_json"
    await update.message.reply_html(
        f"{E_TAG} <b>Gửi JSON custom emoji</b>\n\n"
        "Gửi JSON Telegram update như mẫu có <code>entities[].custom_emoji_id</code>, hoặc dạng ngắn:\n"
        '<code>{"label":"Cursor","custom_emoji_id":"6273793612715138423"}</code>\n\n'
        "Bot sẽ tự lưu keyword và dùng icon đó cho sản phẩm/nút có keyword tương ứng."
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: SKIP channel posts - context.user_data is None!
    if update.channel_post or update.edited_channel_post:
        return

    if context.user_data is None:
        return

    # Kiểm tra chế độ bảo trì
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(t("maintenance", user_id=update.effective_user.id), parse_mode=ParseMode.HTML)
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
            or user_state in {'awaiting_store_coupon'}
        )
    )
    if user.id != ADMIN_USER_ID and not is_user_registered(user.id) and not state_from_store_callback:
        await handle_registration_challenge_answer(update, context, user_input)
        return

    if user.id == ADMIN_USER_ID and user_state == "awaiting_manual_warranty_replacement":
        await handle_manual_warranty_replacement_input(update, context, user_input)
        return

    # NEW: Handle Admin Quick Action (Cộng / Trừ tiền)
    if "quick_action" in context.user_data:
        quick_action = context.user_data['quick_action']
        if user_input.lower() == '/cancel':
            context.user_data.pop('quick_action', None)
            await update.message.reply_text("<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Đã hủy thao tác.")
            return

        parts = quick_action.split(":")
        if len(parts) >= 2:
            action = parts[0]
            target_id_str = parts[1]
            try:
                target_id = int(target_id_str)
                amount = int(user_input.replace(',', '').replace('.', ''))
            except ValueError:
                await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Số tiền không hợp lệ. Vui lòng nhập số (vd: 10000) hoặc gõ /cancel để hủy.")
                return

            user_info = user_data_db.get(str(target_id), {})
            name = user_info.get('first_name', 'N/A')

            if action == "addmoney":
                old_balance = user_info.get('balance', 0)
                user_info['balance'] = old_balance + amount
                user_data_db[str(target_id)] = user_info
                await save_data()
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Đã cộng {amount:,} VNĐ</b> cho {name}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư mới: {user_info['balance']:,} VNĐ", parse_mode='HTML')
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=lt(
                            target_id,
                            f"<tg-emoji emoji-id=\"5422896593412035313\">🎁</tg-emoji> <b>BẠN ĐƯỢC CỘNG TIỀN</b>\n\n<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> Số tiền: <code>+{amount:,} VNĐ</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư mới: <code>{user_info['balance']:,} VNĐ</code>\n\n<i>(Cộng bởi Admin)</i>",
                            f"<tg-emoji emoji-id=\"5422896593412035313\">🎁</tg-emoji> <b>YOUR BALANCE WENT UP</b>\n\n<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> Amount: <code>+{amount:,} VND</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> New balance: <code>{user_info['balance']:,} VND</code>\n\n<i>(Added by the admin)</i>",
                            f"<tg-emoji emoji-id=\"5422896593412035313\">🎁</tg-emoji> <b>余额已增加</b>\n\n<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> 金额：<code>+{amount:,} VND</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 新余额：<code>{user_info['balance']:,} VND</code>\n\n<i>（由管理员添加）</i>",
                        ),
                        parse_mode='HTML'
                    )
                except (ValueError, TypeError, KeyError, IndexError):
                    pass

            elif action == "submoney":
                old_balance = user_info.get('balance', 0)
                user_info['balance'] = max(0, old_balance - amount)
                user_data_db[str(target_id)] = user_info
                await save_data()
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Đã trừ {amount:,} VNĐ</b> của {name}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư mới: {user_info['balance']:,} VNĐ", parse_mode='HTML')
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=lt(
                            target_id,
                            f"<tg-emoji emoji-id=\"5409062331583842187\">💸</tg-emoji> <b>TÀI KHOẢN BỊ TRỪ TIỀN</b>\n\n<tg-emoji emoji-id=\"5406745771280187626\">➖</tg-emoji> Số tiền: <code>-{amount:,} VNĐ</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư mới: <code>{user_info['balance']:,} VNĐ</code>\n\n<i>(Trừ bởi Admin)</i>",
                            f"<tg-emoji emoji-id=\"5409062331583842187\">💸</tg-emoji> <b>YOUR BALANCE WENT DOWN</b>\n\n<tg-emoji emoji-id=\"5406745771280187626\">➖</tg-emoji> Amount: <code>-{amount:,} VND</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> New balance: <code>{user_info['balance']:,} VND</code>\n\n<i>(Deducted by the admin)</i>",
                            f"<tg-emoji emoji-id=\"5409062331583842187\">💸</tg-emoji> <b>余额已扣减</b>\n\n<tg-emoji emoji-id=\"5406745771280187626\">➖</tg-emoji> 金额：<code>-{amount:,} VND</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 新余额：<code>{user_info['balance']:,} VND</code>\n\n<i>（由管理员扣减）</i>",
                        ),
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


    if user_state == 'awaiting_api_rotate_confirmation':
        lowered_input = user_input.strip().casefold()
        confirm_chat_id = context.user_data.get('api_rotate_confirm_chat_id')
        confirm_message_id = context.user_data.get('api_rotate_confirm_message_id')
        if lowered_input in {'/cancel', 'cancel', 'huy', 'hủy'}:
            prompt_updated = False
            if confirm_chat_id and confirm_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=confirm_chat_id,
                        message_id=confirm_message_id,
                        text=f"{API_PREM_STOP} <b>ĐÃ HỦY ĐỔI API KEY</b>",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None,
                    )
                    prompt_updated = True
                except (TelegramError, ValueError, KeyError, AttributeError):
                    logger.debug("Cannot update API rotate confirmation prompt for user %s", user.id)
            await clear_user_state(context)
            if not prompt_updated:
                await update.message.reply_text(
                    f"{API_PREM_STOP} Đã hủy đổi API key.",
                    parse_mode='HTML',
                    reply_markup=create_main_menu(user_id=user.id),
                )
            return

        if lowered_input != 'sure':
            await update.message.reply_text(
                f"{API_PREM_WARN} Để xác nhận đổi API key, hãy nhập đúng <code>sure</code>.\n"
                "Nếu đổi ý, bạn có thể gõ <code>/cancel</code>.",
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
                        text=f"{API_PREM_OK} <b>ĐÃ XÁC NHẬN ĐỔI API KEY</b>\n\nHệ thống đang tạo key mới...",
                        parse_mode=ParseMode.HTML,
                        reply_markup=None,
                )
            except (TelegramError, ValueError, KeyError, AttributeError):
                logger.debug("Cannot mark API rotate confirmation prompt as completed for user %s", user.id)
        partner_key, partner_data = get_partner_api_entry_by_user(user.id)
        await clear_user_state(context)
        if not partner_key or not isinstance(partner_data, dict):
            await update.message.reply_text(
                f"{API_PREM_WARN} Không tìm thấy API key đang hoạt động. Vui lòng thử lại từ menu API.",
                parse_mode='HTML',
            )
            return
        if expected_key and str(partner_key).strip() != expected_key:
            await update.message.reply_text(
                f"{API_PREM_WARN} Yêu cầu xác nhận đã hết hiệu lực. Hãy bấm lại nút đổi API key nếu bạn vẫn muốn tiếp tục.",
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

    # NEW: Handle Manual Order Email (từ balance purchase flow)
    if user_state == 'awaiting_manual_email':
        email_input = user_input.lower()

        if not EMAIL_REGEX.match(email_input):
            await update.message.reply_text(
                "❌ Email không hợp lệ!\n\n"
                "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Vui lòng nhập email đúng định dạng.\n"
                "<i>Ví dụ: example@gmail.com</i>",
                parse_mode='HTML'
            )
            return

        # Get pending order info
        pending_order = context.user_data.get('pending_manual_order')
        if not pending_order:
            await update.message.reply_text("❌ Lỗi: Không tìm thấy đơn hàng. Vui lòng thử lại.")
            await clear_user_state(context)
            return

        order_code = pending_order.get('order_code')
        prod_id = pending_order.get('product_id') or pending_order.get('prod_id')  # FIX: Support both keys
        qty = pending_order.get('quantity') or pending_order.get('qty', 1)  # FIX: Support both keys
        amount = pending_order.get('amount', 0)

        # Get product info
        p = products.get(prod_id, {})
        prod_name = p.get('name', 'Sản phẩm')

        # 1. Xóa tin nhắn "Chờ nhập email" của user
        waiting_msg_id = context.user_data.get('waiting_message_id')
        waiting_chat_id = context.user_data.get('waiting_chat_id')
        if waiting_msg_id and waiting_chat_id:
            try:
                await context.bot.delete_message(waiting_chat_id, waiting_msg_id)
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.debug(f"Could not delete waiting message: {e}")

        # 2. Xóa tin nhắn "Đang chờ email" của admin
        admin_waiting_msg_id = context.user_data.get('admin_waiting_message_id')
        if admin_waiting_msg_id:
            try:
                await context.bot.delete_message(ADMIN_USER_ID, admin_waiting_msg_id)
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.debug(f"Could not delete admin waiting message: {e}")

        # Clear state và data
        context.user_data.pop('state', None)
        context.user_data.pop('pending_manual_order', None)
        context.user_data.pop('waiting_message_id', None)
        context.user_data.pop('waiting_chat_id', None)
        context.user_data.pop('admin_waiting_message_id', None)

        # 3. Thông báo cho khách hàng
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ĐÃ NHẬN EMAIL!</b>\n\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sản phẩm:</b> {prod_name} x{qty}\n"
            f"{E_TAG} <b>Số tiền:</b> {amount:,} VNĐ\n\n"
            f"{E_LOADING} <b>Admin đang xử lý đơn hàng...</b>\n"
            f"{E_SOS} Bạn sẽ nhận thông báo khi hoàn tất!\n\n"
            f"{E_TIP} <b>Mã đơn:</b> <code>{order_code}</code>",
            parse_mode='HTML',
            reply_markup=create_back_button_menu(user_id=update.effective_user.id if update.effective_user else None)
        )

        # 4. Log order
        order_data = {
            "order_code": order_code,
            "user_id": user.id,
            "email": email_input,
            "amount": amount,
            "status": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Chờ Admin xử lý",
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

        # 5. Gửi thông báo chi tiết cho Admin với button xử lý
        admin_keyboard = [
            [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã xử lý", callback_data=f"manual_done_{order_code}")],
            [InlineKeyboardButton("❌ Hủy & Hoàn tiền", callback_data=f"manual_refund_{order_code}")]
        ]

        await context.bot.send_message(
            ADMIN_USER_ID,
            f"{E_TAG} <b>ĐƠN MANUAL CẦN Xử LÝ</b>\n\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách:</b> {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sản phẩm:</b> {prod_name} x{qty}\n"
            f"{E_TAG} <b>Số tiền:</b> {amount:,} VNĐ\n\n"
            f"{E_LOADING} Vui lòng xử lý đơn hàng và bấm nút bên dưới!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )

        logger.info(f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> MANUAL ORDER: {order_code} - User {user.id} - Email: {email_input}")
        return

    # Check nếu user đang có pending manual order cần email
    user_pending = None
    for order_code, info in pending_manual_orders.items():
        if info.get('user_id') == user.id and info.get('status') == 'awaiting_email':
            user_pending = (order_code, info)
            break

    # FIX BUG: Bỏ điều kiện `and not user_state` để luôn ưu tiên xử lý đơn hàng đang chờ email
    # (Thanh toán QR không set context.user_data['state'] vì chạy trong background thread)
    if user_pending and EMAIL_REGEX.match(user_input):
        # User reply với email cho pending manual order
        order_code, order_info = user_pending
        email_input = user_input.lower()

        if not EMAIL_REGEX.match(email_input):
            await update.message.reply_text("<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Email không hợp lệ. Vui lòng nhập lại email chính xác.")
            return

        # Update order với email
        order_info['email'] = email_input
        order_info['status'] = 'pending_admin'
        await save_data(force=True, tables=[PENDING_MANUAL_ORDERS_FILE])

        # Thông báo khách
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ĐÃ NHẬN EMAIL!</b>\n\n"
            f"{E_GLOBE} <b>Email:</b> <code>{email_input}</code>\n"
            f"{E_TAG} <b>Sản phẩm:</b> {order_info['product_name']} x{order_info['quantity']}\n\n"
            f"{E_LOADING} <b>Admin đang xử lý đơn hàng...</b>\n"
            f"{E_SOS} Bạn sẽ nhận thông báo khi hoàn tất\n\n"
            f"{E_TIP} <b>Mã đơn:</b> <code>{order_code}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu(user_id=update.effective_user.id if update.effective_user else None)
        )

        # Gửi cho Admin
        await notify_admin_manual_order(
            context, order_code, user.id, user.full_name,
            email_input, order_info['product_name'], order_info['quantity'], order_info['amount']
        )

        return
    if user_state == 'awaiting_topup_amount':
        await handle_topup_amount_input(update, context, user_input)
        return

    if user_state == 'awaiting_store_coupon':
        prod_id = context.user_data.get('store_coupon_prod_id')
        qty = context.user_data.get('store_coupon_qty', 1)
        await clear_user_state(context)
        if not prod_id or prod_id not in products:
            await update.message.reply_text(
                lt(
                    user.id,
                    "❌ Sản phẩm không tồn tại. Vui lòng thử lại.",
                    "❌ This product no longer exists. Please try again.",
                    "❌ 该商品不存在，请重试。",
                )
            )
            return
        p = products[prod_id]
        coupon_input = user_input.strip().upper()
        coupon_details = coupons.get(coupon_input)
        if not coupon_details:
            await update.message.reply_text(
                lt(
                    user.id,
                    f"❌ Mã <b>{html.escape(coupon_input)}</b> không hợp lệ.",
                    f"❌ The code <b>{html.escape(coupon_input)}</b> is not valid.",
                    f"❌ 优惠码 <b>{html.escape(coupon_input)}</b> 无效。",
                ),
                parse_mode=ParseMode.HTML,
            )
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
            await update.message.reply_text(
                lt(
                    user.id,
                    f"❌ Mã <b>{coupon_input}</b> đã hết hạn hoặc hết lượt sử dụng.",
                    f"❌ The code <b>{coupon_input}</b> has expired or has no uses left.",
                    f"❌ 优惠码 <b>{coupon_input}</b> 已过期或已用完。",
                ),
                parse_mode=ParseMode.HTML,
            )
            return
        discount_val = coupon_details.get('discount', 0)
        base_price = p['price']
        if coupon_details.get('is_percent', False):
            discount_amount = int(base_price * discount_val / 100)
            discount_text = f"{discount_val}% = {discount_amount:,}\u0111"
        else:
            discount_amount = discount_val
            discount_text = f"{discount_amount:,}\u0111"
        discounted_unit = max(0, base_price - discount_amount)
        total_price = discounted_unit * qty
        base_price_text = f"{base_price:,}đ"
        discounted_unit_text = f"{discounted_unit:,}đ"
        user_id_c = update.effective_user.id
        user_info_c = db_get_user(user_id_c)
        balance_c = user_info_c.get('balance', 0) if user_info_c else 0
        context.user_data['store_coupon_applied'] = coupon_input
        context.user_data['store_coupon_discount'] = discount_amount
        context.user_data['store_coupon_prod_id'] = prod_id
        context.user_data['store_coupon_qty'] = qty
        btns = []
        bal_text = lt(user.id, f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư ({balance_c:,}đ)", f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Wallet ({balance_c:,}đ)", f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> 钱包 ({balance_c:,}đ)")
        if balance_c >= total_price:
            btns.append([InlineKeyboardButton(bal_text, callback_data=f"pay_prod_bal_{prod_id}_{qty}")])
        elif balance_c > 0:
            remaining_c = total_price - balance_c
            btns.append([InlineKeyboardButton(
                f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Dùng {balance_c:,}đ + QR {remaining_c:,}đ",
                callback_data=f"pay_prod_combo_{prod_id}_{qty}"
            )])
        else:
            btns.append([_btn(lt(user.id, "Không", "No", "否"), icon_id="5273914604752216432", callback_data="ignore")])
        from app.integrations.payments_core import is_usdt_payment_enabled
        if is_usdt_payment_enabled():
            btns.append([_btn("USDT (RPay)", icon_id="5281029063459234079", callback_data=f"pay_prod_rpay_{prod_id}_{qty}")])
        from app.integrations.binancepay_api import is_binance_pay_enabled
        if is_binance_pay_enabled():
            btns.append([_btn("Binance Pay", icon_id=CRYPTO_BUTTON_ICON_ID, callback_data=f"pay_prod_binance_{prod_id}_{qty}")])
        from app.integrations.payments_core import is_bank_transfer_enabled
        if is_bank_transfer_enabled():
            btns.append([_btn(lt(user.id, "Chuyển khoản (QR)", "Bank transfer (QR)", "银行转账（QR）"), icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}")])
        btns.append([InlineKeyboardButton(lt(user.id, "⬅️ Quay lại", "⬅️ Back", "⬅️ 返回"), callback_data=f"buy_prod_confirm_{prod_id}_{qty}")])
        await update.message.reply_text(
            lt(
                user.id,
                f"✅ <b>ĐÃ ÁP DỤNG MÃ GIẢM GIÁ</b>\n\n"
                f"🏷 Sản phẩm: {html.escape(p['name'])}\n"
                f"🔢 Số lượng: {qty}\n"
                f"🎫 Mã: <code>{coupon_input}</code> (giảm {discount_text})\n"
                f"💰 Đơn giá: <s>{base_price_text}</s> → <b>{discounted_unit_text}</b>\n"
                f"💵 Tổng: <b>{total_price:,}đ</b>\n\n"
                f"Chọn phương thức thanh toán:",
                f"✅ <b>DISCOUNT CODE APPLIED</b>\n\n"
                f"🏷 Product: {html.escape(p['name'])}\n"
                f"🔢 Quantity: {qty}\n"
                f"🎫 Code: <code>{coupon_input}</code> (saves {discount_text})\n"
                f"💰 Unit price: <s>{base_price_text}</s> → <b>{discounted_unit_text}</b>\n"
                f"💵 Total: <b>{total_price:,}đ</b>\n\n"
                f"Choose a payment method:",
                f"✅ <b>优惠码已生效</b>\n\n"
                f"🏷 商品: {html.escape(p['name'])}\n"
                f"🔢 数量: {qty}\n"
                f"🎫 优惠码: <code>{coupon_input}</code> (减 {discount_text})\n"
                f"💰 单价: <s>{base_price_text}</s> → <b>{discounted_unit_text}</b>\n"
                f"💵 合计: <b>{total_price:,}đ</b>\n\n"
                f"请选择支付方式：",
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btns)
        )
    elif user_state == 'awaiting_report_order_code':
        order_code = user_input.upper()
        if not USER_ORDER_CODE_REGEX.match(order_code):  # Tối ưu: compiled regex
            await update.message.reply_text(lt(
                user.id,
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Mã đơn hàng không hợp lệ. Vui lòng nhập lại hoặc /cancel để hủy.",
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> That order code is not valid. Send it again or /cancel to stop.",
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 订单号无效。请重新输入，或输入 /cancel 取消。",
            )); return
        # FIX: Dùng index O(1)
        found_order = order_index.get(order_code)
        if not found_order or found_order.get("user_id") != user.id: await update.message.reply_text(lt(
                user.id,
                "❌ Không tìm thấy đơn hàng này hoặc đơn hàng không thuộc về bạn. Vui lòng kiểm tra lại mã hoặc /cancel để hủy.",
                "❌ We cannot find that order, or it does not belong to you. Check the code or /cancel to stop.",
                "❌ 未找到该订单，或该订单不属于您。请检查订单号，或输入 /cancel 取消。",
            )); return
        if found_order.get('refunded_at'):
            await update.message.reply_text(
                lt(
                    user.id,
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa.\nVui lòng nhập mã đơn khác hoặc gõ /cancel để hủy.",
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> This order was refunded, so it can no longer be reported.\nSend another order code or /cancel to stop.",
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 该订单已退款，无法再提交问题报告。\n请输入其他订单号，或输入 /cancel 取消。",
                )
            )
            return

        # <tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> BLOCK SPAM: Check if order support was rejected
        support_status = found_order.get('support_status', 'active')
        if support_status == 'rejected_expired':
            await update.message.reply_text(
                lt(
                    user.id,
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>TỪ CHỐI HỖ TRỢ</b>\n\nĐơn hàng này đã bị từ chối bảo hành do <b>HẾT HẠN BẢO HÀNH</b>.\nVui lòng không gửi lại yêu cầu.",
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>SUPPORT DECLINED</b>\n\nThis order was declined because the <b>WARRANTY HAS EXPIRED</b>.\nPlease do not send the request again.",
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>支持请求已拒绝</b>\n\n该订单因<b>质保已过期</b>被拒绝。\n请勿重复提交。",
                ), parse_mode=ParseMode.HTML
            )
            await clear_user_state(context)
            return
        elif support_status == 'rejected_policy':
            await update.message.reply_text(
                lt(
                    user.id,
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>TỪ CHỐI HỖ TRỢ</b>\n\nĐơn hàng này đã bị từ chối hỗ trợ do <b>VI PHẠM CHÍNH SÁCH</b>.\nVui lòng không gửi lại yêu cầu.",
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>SUPPORT DECLINED</b>\n\nThis order was declined for a <b>POLICY BREACH</b>.\nPlease do not send the request again.",
                    "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>支持请求已拒绝</b>\n\n该订单因<b>违反条款</b>被拒绝。\n请勿重复提交。",
                ), parse_mode=ParseMode.HTML
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
            lt(
                user.id,
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã xác nhận đơn hàng. Tiếp theo, vui lòng gửi <b>một ảnh chụp màn hình</b> về lỗi bạn gặp phải.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Order confirmed. Next, please send <b>a screenshot</b> of the problem.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> 订单已确认。接下来请发送<b>问题截图</b>。",
            ),
            parse_mode=ParseMode.HTML
        )
    elif user_state == 'awaiting_report_photo':
        await update.message.reply_text(
            lt(
                user.id,
                "❌ Vui lòng gửi <b>ảnh chụp màn hình lỗi</b> trước để tiếp tục báo cáo.",
                "❌ Send <b>a screenshot of the problem</b> first so the report can continue.",
                "❌ 请先发送<b>问题截图</b>，然后才能继续提交。",
            ),
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
            await update.message.reply_text(lt(
                user.id,
                "❌ Đã có lỗi trong quá trình báo cáo. Vui lòng bắt đầu lại.",
                "❌ Something went wrong with the report. Please start again.",
                "❌ 提交问题报告时出错，请重新开始。",
            ))
            await clear_user_state(context)
            return
        if not all([photo_chat_id, photo_message_id]):
            context.user_data['state'] = 'awaiting_report_photo'
            context.user_data.pop('report_photo_id', None)
            context.user_data.pop('report_photo_chat_id', None)
            context.user_data.pop('report_photo_message_id', None)
            await update.message.reply_text(
                lt(
                    user.id,
                    "❌ Thiếu dữ liệu ảnh gốc. Vui lòng gửi lại ảnh lỗi để hệ thống chuyển tiếp cho admin.",
                    "❌ The original photo is missing. Send it again so we can forward it to the admin.",
                    "❌ 缺少原始图片。请重新发送，以便转交管理员。",
                )
            )
            return
        # FIX: Dùng index O(1)
        found_order = order_index.get(order_code)
        if not found_order:
            await update.message.reply_text(lt(
                user.id,
                "❌ Không tìm thấy đơn hàng này trong lịch sử. Vui lòng bắt đầu lại.",
                "❌ That order is not in your history. Please start again.",
                "❌ 历史记录中没有该订单，请重新开始。",
            ))
            await clear_user_state(context)
            return
        if found_order.get('refunded_at'):
            await update.message.reply_text(
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa."
            )
            await clear_user_state(context)
            return
        if await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        email_val = found_order.get('email', 'Không có')
        purchase_time = found_order.get('timestamp', 0)
        purchase_date_str = datetime.fromtimestamp(purchase_time).strftime('%d/%m/%Y') if purchase_time else "N/A"

        # 1. <tg-emoji emoji-id=\"5303290914041505430\">🚀</tg-emoji> SEND TO ADMIN IMMEDIATELY (Hybrid Mode)
        # Determine product type & action buttons
        btns = []
        prod_id_check = found_order.get('product_id')
        p_check = products.get(prod_id_check) if prod_id_check else None
        product_name = found_order.get('product_name') or (p_check.get('name') if p_check else 'N/A')
        order_type = found_order.get('type', 'unknown')

        # Fallback: tìm product bằng product_name nếu không có product_id
        if not p_check and product_name and product_name != 'N/A':
            for pid, pdata in products.items():
                if pdata.get('name') == product_name:
                    p_check = pdata
                    prod_id_check = pid
                    break

        is_auto_stock = False
        is_manual_product = False
        if order_type == 'store_product':
            if p_check and p_check.get('requires_gmail'):
                is_manual_product = True
            else:
                is_auto_stock = True
        elif p_check:
            if p_check.get('requires_gmail'):
                is_manual_product = True
            else:
                is_auto_stock = True

        if is_auto_stock:
            type_label = "<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Store (Auto Stock)"
            btns.append([_btn("Cấp Acc Mới (Auto)", icon_id="6129870117619634982", callback_data=f"replace_auto:{order_code}")])
        elif is_manual_product:
            type_label = "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> Sản phẩm thủ công"
            btns.append([_btn("Cấp Acc/Link Mới (Thủ công)", icon_id="6129870117619634982", callback_data=f"replace_manual:{order_code}")])
        else:
            type_label = "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> Khác / thủ công"
            btns.append([_btn("Cấp Acc/Link Mới (Thủ công)", icon_id="6129870117619634982", callback_data=f"replace_manual:{order_code}")])

        if _resolve_order_duration_days(found_order) > 0:
            btns.append([_btn(
                "Hoàn tiền ngày chưa sử dụng",
                icon_id="5278467510604160626",
                callback_data=f"admrf_p_{order_code}",
            )])
        else:
            btns.append([_btn(
                "Hoàn tiền lỗi (100%)",
                icon_id="5278467510604160626",
                callback_data=f"admrf_f_{order_code}",
            )])

        btns.append([
            _btn("Từ chối: Hết BH", icon_id="5465665476971471368", callback_data=f"reject_expired:{found_order.get('user_id')}:{order_code}"),
            _btn("Từ chối: Vi phạm", icon_id="5273914604752216432", callback_data=f"reject_policy:{found_order.get('user_id')}:{order_code}")
        ])
        btns.append([_btn("Đã bảo hành", icon_id="6269163801178804220", callback_data=f"warranty_done:{order_code}")])
        btns.append([_btn("Bỏ qua", icon_id="5364075889669718872", callback_data=f"dismiss_report:{order_code}")])

        safe_username = html.escape(f"@{user.username}" if user.username else "Không có")
        safe_type_label = type_label
        safe_email_val = html.escape(str(email_val))
        safe_purchase_date = html.escape(str(purchase_date_str))
        safe_description = html.escape(str(description))

        admin_report_text = (
            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>BÁO CÁO LỖI MỚI</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n"
            f"<b>Từ:</b> {format_user_mention_html(user)} (ID: <code>{user.id}</code>)\n"
            f"<b>Username:</b> {safe_username}\n\n"
            f"<b>CHI TIẾT ĐƠN HÀNG:</b>\n"
            f"  - Mã đơn: <code>{found_order.get('order_code', 'N/A')}</code>\n"
            f"  - Sản phẩm: <b>{html.escape(str(product_name))}</b>\n"
            f"  - Loại: {safe_type_label}\n"
            f"  - Email: <code>{safe_email_val}</code>\n"
            f"  - Ngày mua: {safe_purchase_date}\n\n"
            f"<b>MÔ TẢ CỦA KHÁCH:</b>\n"
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
            logger.error(f"[REPORT] không thể chuyển tiếp ảnh báo lỗi ({err_text})")
            await safe_send_admin(
                context.bot,
                (
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
                    f"<b>BÁO CÁO LỖI ẢNH</b>\n"
                    f"Order: <code>{order_code}</code>\n"
                    f"User ID: <code>{user.id}</code>\n"
                    f"Lý do: <code>{html.escape(err_text)}</code>"
                ),
            )
            context.user_data['state'] = 'awaiting_report_photo'
            context.user_data.pop('report_photo_id', None)
            context.user_data.pop('report_photo_chat_id', None)
            context.user_data.pop('report_photo_message_id', None)
            await update.message.reply_text(
                lt(
                    user.id,
                    "❌ Không thể chuyển tiếp ảnh cho admin. Vui lòng gửi lại ảnh lỗi dưới dạng Photo.",
                    "❌ We could not forward the photo to the admin. Send it again as a Photo.",
                    "❌ 无法将图片转交管理员。请以图片形式重新发送。",
                )
            )
            return

        sent_msg = await safe_send_admin(
            context.bot,
            admin_report_text,
            reply_markup=InlineKeyboardMarkup(btns),
        )


        # 2. <tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> TRACKING FOR REMINDER (Unresolved List)
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
                'product_name': found_order.get('product_name', 'Sản phẩm'),
                'purchase_date': purchase_date_str,
                'resolved': False, # Status tracking
                'report_count': 1,
                'last_msg_id': sent_msg.message_id if sent_msg else None
            }
            pending_error_reports.append(report_data)

        await update.message.reply_text(
            lt(
                user.id,
                f"{E_SUCCESS} <b>ĐÃ GỬI BÁO CÁO</b>\n\nAdmin đã nhận được thông tin và sẽ kiểm tra sớm nhất.",
                f"{E_SUCCESS} <b>REPORT SENT</b>\n\nThe admin has the details and will look into it shortly.",
                f"{E_SUCCESS} <b>报告已提交</b>\n\n管理员已收到信息，会尽快查看。",
            ),
            parse_mode=ParseMode.HTML
        )
        await clear_user_state(context)
    elif user_state == 'awaiting_support_query':
        query = update.message.text.strip(); context.user_data['support_query'] = query

        # Sử dụng intelligent_ticket_classifier để xử lý truy vấn hỗ trợ
        ai_result = await intelligent_ticket_classifier(query, user.id)

        if ai_result['auto_resolved']:
            # Nếu AI tự động giải quyết được
            await update.message.reply_html(ai_result['response'])
            await clear_user_state(context)
        else:
            # Nếu không thể tự động giải quyết
            keyboard = [
                [InlineKeyboardButton(lt(user.id, "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hỏi Trợ lý AI", "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Ask the AI assistant", "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> 咨询 AI 助手"), callback_data='ask_ai_confirm')],
                [InlineKeyboardButton(lt(user.id, "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Tạo phiếu hỗ trợ cho Admin", "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Open a support ticket", "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> 创建工单"), callback_data='create_ticket_confirm')]
            ]
            await update.message.reply_text(
                lt(
                    user.id,
                    "Câu hỏi của bạn cần tư vấn chi tiết hơn. Bạn có muốn hỏi Trợ lý AI không?",
                    "Your question needs a closer look. Would you like to ask our AI assistant?",
                    "您的问题需要更详细的解答。要咨询我们的 AI 助手吗？",
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif user_state and user_state.startswith('awaiting_custom_qty:'):
        # NEW: Xử lý nhập số lượng tùy chỉnh
        prod_id = user_state.split(':', 1)[1]
        p = products.get(prod_id)

        if not p:
            await update.message.reply_text(lt(user.id, "❌ Sản phẩm không tồn tại.", "❌ This product no longer exists.", "❌ 该商品不存在。"))
            await clear_user_state(context)
            return

        # Validate input
        try:
            qty = int(user_input.strip())
        except ValueError:
            await update.message.reply_text(
                lt(
                    user.id,
                    "❌ <b>Số lượng không hợp lệ</b>\n\nVui lòng nhập một số nguyên.\nVí dụ: 200",
                    "❌ <b>That quantity is not valid</b>\n\nSend a whole number.\nFor example: 200",
                    "❌ <b>数量无效</b>\n\n请输入整数。\n例如：200",
                ),
                parse_mode=ParseMode.HTML
            )
            return


        stock_count = len(p.get('stock', []))

        # Check range
        if qty < 1:
            await update.message.reply_text(
                lt(user.id, "❌ Số lượng phải ít nhất là 1.", "❌ The quantity must be at least 1.", "❌ 数量至少为 1。"),
                parse_mode=ParseMode.HTML
            )
            return
        elif qty > stock_count:
            await update.message.reply_text(
                lt(
                    user.id,
                    f"❌ <b>KHÔNG ĐỦ HÀNG</b>\n\nBạn muốn: <b>{qty}</b>\nTồn kho: <b>{stock_count}</b>\n\nVui lòng nhập số nhỏ hơn hoặc bằng {stock_count}.",
                    f"❌ <b>NOT ENOUGH STOCK</b>\n\nYou asked for: <b>{qty}</b>\nIn stock: <b>{stock_count}</b>\n\nSend a number no larger than {stock_count}.",
                    f"❌ <b>库存不足</b>\n\n您想要：<b>{qty}</b>\n库存：<b>{stock_count}</b>\n\n请输入不超过 {stock_count} 的数字。",
                ),
                parse_mode=ParseMode.HTML
            )
            return

        # Valid quantity - show confirmation
        await clear_user_state(context)

        total_price = p['price'] * qty
        user_info = db_get_user(user.id)
        balance = user_info.get('balance', 0) if user_info else 0

        btns = []
        bal_text = lt(user.id, f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư ({balance:,}đ)", f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Wallet ({balance:,}đ)", f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> 钱包 ({balance:,}đ)")
        if balance >= total_price:
            btns.append([InlineKeyboardButton(bal_text, callback_data=f"pay_prod_bal_{prod_id}_{qty}")])
        else:
            btns.append([_btn(lt(user.id, "Không", "No", "否"), icon_id="5273914604752216432", callback_data="ignore")])

        from app.integrations.payments_core import is_usdt_payment_enabled
        if is_usdt_payment_enabled():
            btns.append([_btn("USDT (RPay)", icon_id="5281029063459234079", callback_data=f"pay_prod_rpay_{prod_id}_{qty}")])
        from app.integrations.binancepay_api import is_binance_pay_enabled
        if is_binance_pay_enabled():
            btns.append([_btn("Binance Pay", icon_id=CRYPTO_BUTTON_ICON_ID, callback_data=f"pay_prod_binance_{prod_id}_{qty}")])
        from app.integrations.payments_core import is_bank_transfer_enabled
        if is_bank_transfer_enabled():
            btns.append([_btn(lt(user.id, "Chuyển khoản (QR)", "Bank transfer (QR)", "银行转账（QR）"), icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}")])
        btns.append([_btn(lt(user.id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data=f"sel_qty_{prod_id}")])

        confirm_text = (
            f'<tg-emoji emoji-id="5247134066322447995">🛍</tg-emoji> <b>XÁC NHẬN MUA HÀNG</b>\n\n'
            f'<tg-emoji emoji-id="5240228673738527951">🏷</tg-emoji> <b>Sản phẩm:</b> {p["name"]}\n'
            f'<tg-emoji emoji-id="5305749482170758709">0️⃣</tg-emoji> <b>Số lượng:</b> {qty}\n'
            f'<tg-emoji emoji-id="5240228673738527951">🏷</tg-emoji> <b>Tổng tiền:</b> {total_price:,} VNĐ\n\n'
            f'<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> Vui lòng chọn phương thức thanh toán:'
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
            await context.bot.send_message(chat_id=target_user_id, text="<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Bạn có phản hồi từ Admin:</b>", parse_mode=ParseMode.HTML)
            await context.bot.copy_message(chat_id=target_user_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await update.message.reply_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Tin nhắn của bạn đã được gửi tới người dùng.")
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"Gửi phản hồi thất bại. Lỗi: {e}"); await update.message.reply_text("❌ Gửi phản hồi thất bại, vui lòng kiểm tra bot admin logs.")
        finally: await clear_user_state(context)
    else:
        # Nếu không có trạng thái đặc biệt nào -> Chat với AI
        await chat_with_ai(update, context)



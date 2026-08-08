# --- USER WALLET TOP-UP ---
#
# Nap tien vao vi de mua hang. Tien nap KHONG duoc rut ra: phan so du den tu
# nap duoc theo doi rieng o user_data_db[uid]["balance_topup"], va
# get_withdrawable_balance() tru phan do ra. Cach nay giu shop khoi bi dung
# lam kenh chuyen tien (nap roi rut sang tai khoan khac ma khong mua gi).


def _topup_amount_bounds_text(user_id) -> str:
    return lt(
        user_id,
        "Số tiền nạp từ <b>{min:,}</b> đến <b>{max:,}</b> VNĐ.",
        "Top-up amount must be between <b>{min:,}</b> and <b>{max:,}</b> VND.",
        "充值金额需在 <b>{min:,}</b> 至 <b>{max:,}</b> VND 之间。",
        min=MIN_USER_TOPUP_AMOUNT,
        max=MAX_USER_TOPUP_AMOUNT,
    )


def get_user_topup_balance(user_id) -> int:
    """Phan so du den tu nap tien (khong duoc rut)."""
    profile = user_data_db.get(str(user_id))
    if not isinstance(profile, dict):
        return 0
    try:
        return max(0, int(profile.get("balance_topup", 0) or 0))
    except (TypeError, ValueError):
        return 0


def get_withdrawable_balance(user_id) -> int:
    """So du rut duoc = tong so du tru phan tu nap."""
    profile = user_data_db.get(str(user_id))
    if not isinstance(profile, dict):
        return 0
    try:
        balance = int(profile.get("balance", 0) or 0)
    except (TypeError, ValueError):
        balance = 0
    return max(0, balance - get_user_topup_balance(user_id))


def _generate_user_topup_code(user_id) -> str:
    for _ in range(50):
        code = f"NAPU{int(user_id)}{random.randint(1000, 9999)}"
        if code not in pending_user_topups:
            return code
    return f"NAPU{int(user_id)}{int(time.time() * 1000) % 100000}"


def get_user_pending_topup(user_id):
    """Ma nap dang cho cua user (moi user chi giu 1 ma tai mot thoi diem)."""
    user_id_int = int(user_id)
    for code, details in pending_user_topups.items():
        if isinstance(details, dict) and int(details.get("user_id", 0) or 0) == user_id_int:
            return code, details
    return None, None


def build_user_topup_qr_url(code: str, amount: int) -> str:
    return (
        f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NUMBER}-print.png"
        f"?amount={int(amount)}&addInfo={quote(str(code))}&accountName={quote(ACCOUNT_NAME)}"
    )


def _build_topup_caption(user_id, code: str, amount: int) -> str:
    minutes = max(1, USER_TOPUP_EXPIRATION_SECONDS // 60)
    return lt(
        user_id,
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>NẠP TIỀN VÀO VÍ</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount:,} VNĐ\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung:</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Hiệu lực:</b> {minutes} phút\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chuyển <b>đúng số tiền</b> và <b>đúng nội dung</b>. "
        "Bot tự cộng tiền sau 1-3 phút.\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Tiền trong ví chỉ dùng để mua hàng, không rút ra được.",
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>TOP UP YOUR WALLET</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Amount:</b> {amount:,} VND\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Transfer note:</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Valid for:</b> {minutes} minutes\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Send the <b>exact amount</b> with the <b>exact note</b>. "
        "The bot credits your wallet within 1-3 minutes.\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Wallet funds can only be spent on purchases, not withdrawn.",
        "<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>钱包充值</b>\n\n"
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>金额：</b> {amount:,} VND\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>转账备注：</b> <code>{code}</code>\n"
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>有效期：</b> {minutes} 分钟\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 请转账<b>准确金额</b>并填写<b>准确备注</b>，机器人将在 1-3 分钟内入账。\n"
        "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> 钱包余额仅可用于购物，不可提现。",
        amount=amount,
        code=code,
        minutes=minutes,
    )


def _build_topup_keyboard(user_id, code: str):
    return InlineKeyboardMarkup([
        [_btn(lt(user_id, "Hủy lệnh nạp", "Cancel top-up", "取消充值"),
              icon_id="5273914604752216432", callback_data=f"topup_cancel:{code}")],
        [_btn(lt(user_id, "Quay lại", "Back", "返回"),
              icon_id="6206032691075223572", callback_data="my_stats")],
    ])


async def create_user_topup_request(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int) -> bool:
    """Tao ma nap + QR. Tra False neu khong tao duoc (da co ma cho / sai so tien)."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    if amount < MIN_USER_TOPUP_AMOUNT or amount > MAX_USER_TOPUP_AMOUNT:
        await safe_bot_send_html(context.bot, chat_id, f"{E_LIMIT} " + _topup_amount_bounds_text(user.id))
        return False

    existing_code, existing_details = get_user_pending_topup(user.id)
    if existing_code:
        await safe_bot_send_html(
            context.bot,
            chat_id,
            lt(
                user.id,
                "{limit} Bạn đang có lệnh nạp <code>{code}</code> ({amount:,} VNĐ) chưa hoàn tất.\n"
                "Hoàn tất hoặc hủy lệnh cũ trước khi tạo lệnh mới.",
                "{limit} You already have a pending top-up <code>{code}</code> ({amount:,} VND).\n"
                "Finish or cancel it before creating a new one.",
                "{limit} 您已有待处理的充值 <code>{code}</code>（{amount:,} VND）。\n请先完成或取消后再创建。",
                limit=E_LIMIT,
                code=existing_code,
                amount=int((existing_details or {}).get("amount", 0) or 0),
            ),
            reply_markup=_build_topup_keyboard(user.id, existing_code),
        )
        return False

    code = _generate_user_topup_code(user.id)
    pending_user_topups[code] = {
        "code": code,
        "user_id": int(user.id),
        "amount": int(amount),
        "time": time.time(),
        "full_name": user.full_name,
        "username": user.username,
    }
    await save_data(force=True, tables=[USER_TOPUP_FILE])

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=build_user_topup_qr_url(code, amount),
            caption=_build_topup_caption(user.id, code, amount),
            parse_mode=ParseMode.HTML,
            reply_markup=_build_topup_keyboard(user.id, code),
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"[topup] Khong gui duoc QR nap tien cho {user.id}: {e}")
        await safe_bot_send_html(
            context.bot,
            chat_id,
            _build_topup_caption(user.id, code, amount),
            reply_markup=_build_topup_keyboard(user.id, code),
        )
    return True


async def start_user_topup_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
    """Hoi so tien can nap."""
    if await check_if_banned(update):
        return
    user_id = update.effective_user.id
    await clear_user_state(context)
    context.user_data['state'] = 'awaiting_topup_amount'

    msg = lt(
        user_id,
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>NẠP TIỀN VÀO VÍ</b>\n\n"
        "Nhập số tiền muốn nạp (chỉ số).\n{bounds}\n\n"
        "Ví dụ: <code>100000</code>\n\nGõ /cancel để hủy.",
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>TOP UP YOUR WALLET</b>\n\n"
        "Enter the amount you want to add (numbers only).\n{bounds}\n\n"
        "Example: <code>100000</code>\n\nSend /cancel to abort.",
        "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>钱包充值</b>\n\n"
        "请输入充值金额（仅数字）。\n{bounds}\n\n示例：<code>100000</code>\n\n发送 /cancel 取消。",
        bounds=_topup_amount_bounds_text(user_id),
    )
    keyboard = InlineKeyboardMarkup([
        [_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="my_stats")]
    ])
    if is_callback:
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def naptien_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/naptien [so_tien]"""
    if await check_if_banned(update):
        return
    if context.args:
        try:
            amount = int(str(context.args[0]).replace(",", "").replace(".", "").strip())
        except (TypeError, ValueError):
            await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(update.effective_user.id))
            return
        await clear_user_state(context)
        await create_user_topup_request(update, context, amount)
        return
    await start_user_topup_flow(update, context, is_callback=False)


async def handle_topup_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    user_id = update.effective_user.id
    try:
        amount = int(str(user_input).replace(",", "").replace(".", "").replace(" ", "").strip())
    except (TypeError, ValueError):
        await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(user_id))
        return
    if amount < MIN_USER_TOPUP_AMOUNT or amount > MAX_USER_TOPUP_AMOUNT:
        await update.message.reply_html(f"{E_LIMIT} " + _topup_amount_bounds_text(user_id))
        return
    await clear_user_state(context)
    await create_user_topup_request(update, context, amount)


async def cancel_user_topup(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str) -> bool:
    """Huy lenh nap dang cho. Chi chu so huu duoc huy."""
    query = update.callback_query
    details = pending_user_topups.get(code)
    if not isinstance(details, dict) or int(details.get("user_id", 0) or 0) != int(update.effective_user.id):
        await safe_answer(query, lt(update.effective_user.id, "Lệnh nạp không tồn tại.", "Top-up request not found.", "找不到该充值请求。"), show_alert=True)
        return True

    pending_user_topups.pop(code, None)
    await save_data(force=True, tables=[USER_TOPUP_FILE])
    await safe_answer(query, lt(update.effective_user.id, "Đã hủy lệnh nạp.", "Top-up cancelled.", "已取消充值。"))
    try:
        await query.delete_message()
    except (TelegramError, ValueError, AttributeError):
        pass
    return True


def cleanup_expired_user_topups(current_time: float) -> bool:
    expired = [
        code for code, details in list(pending_user_topups.items())
        if not isinstance(details, dict)
        or current_time - float(details.get("time", 0) or 0) > USER_TOPUP_EXPIRATION_SECONDS
    ]
    for code in expired:
        pending_user_topups.pop(code, None)
    return bool(expired)


def find_pending_user_topup_reference(description: str):
    """Tim ma NAPU trong noi dung chuyen khoan."""
    raw_description = str(description or "")
    match = NAPU_PATTERN.search(raw_description) or NAPU_PATTERN.search(raw_description.replace(" ", ""))
    if match:
        return match.group(1).upper()
    return None


async def credit_user_topup(context: ContextTypes.DEFAULT_TYPE, code: str, amount_received: int) -> bool:
    """Cong tien nap vao vi. Tra True neu da xu ly xong ma nap nay."""
    details = pending_user_topups.get(code)
    if not isinstance(details, dict):
        return False

    user_id = int(details.get("user_id", 0) or 0)
    amount_expected = int(details.get("amount", 0) or 0)
    amount_received = int(amount_received)

    # Chuyen thieu tien: khong tu cong, de admin doi soat tay.
    if amount_received < amount_expected:
        pending_user_topups.pop(code, None)
        await safe_send_admin(
            context.bot,
            f"{E_LIMIT} <b>NẠP VÍ SAI SỐ TIỀN</b>\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{code}</code>\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: <code>{user_id}</code>\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Nhận {amount_received:,} / cần {amount_expected:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Cộng tay: <code>/addmoney {user_id} {amount_received}</code>"
        )
        try:
            await context.bot.send_message(
                user_id,
                lt(
                    user_id,
                    "{limit} Số tiền chuyển không khớp lệnh nạp <code>{code}</code>. Admin sẽ kiểm tra và xử lý thủ công.",
                    "{limit} The transferred amount does not match top-up <code>{code}</code>. An admin will handle it manually.",
                    "{limit} 转账金额与充值单 <code>{code}</code> 不符，管理员将手动处理。",
                    limit=E_LIMIT, code=code,
                ),
                parse_mode=ParseMode.HTML,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass
        return True

    user_record = db_get_user(user_id)
    current_balance = int((user_record or {}).get("balance", 0) or 0)
    new_balance = current_balance + amount_received
    db_update_balance(user_id, new_balance, reason=f"Topup: {code}")
    pending_user_topups.pop(code, None)
    await save_data(force=True, tables=[USERS_FILE, USER_TOPUP_FILE])

    try:
        await context.bot.send_message(
            user_id,
            lt(
                user_id,
                "{ok} <b>NẠP TIỀN THÀNH CÔNG</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Đã nạp:</b> +{amount:,} VNĐ\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>Số dư mới:</b> {balance:,} VNĐ\n\n"
                "Gõ /start để mua hàng ngay.",
                "{ok} <b>TOP-UP SUCCESSFUL</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Added:</b> +{amount:,} VND\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>New balance:</b> {balance:,} VND\n\n"
                "Send /start to shop now.",
                "{ok} <b>充值成功</b>\n\n"
                "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>已充值：</b> +{amount:,} VND\n"
                "<tg-emoji emoji-id=\"4967667085606912536\">👛</tg-emoji> <b>新余额：</b> {balance:,} VND\n\n"
                "发送 /start 立即购物。",
                ok=E_SUCCESS, amount=amount_received, balance=new_balance,
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=create_back_button_menu(user_id=user_id),
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"[topup] Khong bao duoc cho user {user_id}: {e}")

    await safe_send_admin(
        context.bot,
        f"{E_SUCCESS} <b>NẠP VÍ THÀNH CÔNG</b>\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: <code>{code}</code>\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: <code>{user_id}</code>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> +{amount_received:,} VNĐ | Số dư: {new_balance:,} VNĐ"
    )
    return True

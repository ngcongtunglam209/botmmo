# ==============================================================================
#  DICE GAME SYSTEM (MAY MẮN XÚC XẮC)
# ==============================================================================

DICE_COOLDOWN_HOURS = 24  # 24 hours cooldown
DICE_MAX_PRODUCT_PRICE = 36000  # Only products under 36k VNĐ

# Winning combinations - CHỈ 111 VÀ 222 MỚI CÓ GIẢI (Tỷ lệ thắng 0.92%)
WINNING_TRIPLES = [(1,1,1), (2,2,2)]
# WINNING_SEQUENCES = [(1,2,3), (2,3,4), (3,4,5), (4,5,6)]  # ĐÃ TẮT để giảm tỷ lệ thắng

def is_dice_winning_combination(dice_values):
    """
    Check if dice combination is a winner
    dice_values: tuple of (dice1, dice2, dice3)
    
    CHỈ 111 VÀ 222 THẮNG!
    Tỷ lệ: 2/216 = 0.92%
    """
    # CHỈ CHECK TRIPLES - 111, 222
    if dice_values in WINNING_TRIPLES:
        return True
    
    # ĐÃ TẮT sequences để giảm tỷ lệ thắng (tránh lỗ vốn)
    # if dice_values in WINNING_SEQUENCES:
    #     return True
    
    return False

def get_available_dice_products():
    """Get all products under DICE_MAX_PRODUCT_PRICE with stock available"""
    eligible = []
    
    # Check store products
    for pid, p in products.items():
        price = p.get('price', 0)
        stock = p.get('stock', [])
        requires_gmail = p.get('requires_gmail', False)
        
        # Only AUTO products with stock and price < 36k
        if price < DICE_MAX_PRODUCT_PRICE and not requires_gmail and len(stock) > 0:
            eligible.append({
                'type': 'product',
                'id': pid,
                'name': p['name'],
                'price': price,
                'stock_count': len(stock)
            })
    
    return eligible





# ==============================================================================
#  WITHDRAWAL SYSTEM (RÚT TIỀN)
# ==============================================================================

async def withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_if_banned(update):
        return
    user = update.effective_user
    user_id = user.id
    context.user_data.pop('state', None)
    context.user_data.pop('withdrawal_amount', None)
    await context.bot.send_message(
        update.effective_chat.id,
        lt(
            user_id,
            "ℹ️ <b>TÍNH NĂNG RÚT TIỀN ĐÃ ĐƯỢC TẮT</b>\n\nSố dư tài khoản chỉ được dùng để mua sản phẩm và dịch vụ tại Lâm Shop.",
            "ℹ️ <b>WITHDRAWALS ARE DISABLED</b>\n\nYour account balance can only be used to purchase products and services at Lâm Shop.",
            "ℹ️ <b>提现功能已关闭</b>\n\n账户余额仅可用于购买 Lâm Shop 的产品和服务。",
        ), parse_mode=ParseMode.HTML,
    )


async def handle_withdrawal_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    context.user_data.pop('state', None)
    context.user_data.pop('withdrawal_amount', None)
    await update.message.reply_text(
        lt(
            user_id,
            "ℹ️ Tính năng rút tiền đã được tắt. Số dư chỉ dùng để mua hàng tại Lâm Shop.",
            "ℹ️ Withdrawals are disabled. Your balance can only be used for purchases at Lâm Shop.",
            "ℹ️ 提现功能已关闭。余额仅可用于在 Lâm Shop 购物。",
        )
    )
    return

    # Luồng dưới đây chỉ được giữ để đọc dữ liệu/yêu cầu lịch sử; không thể truy cập.
    user_id_str = str(user_id)
    state = context.user_data.get('state')
    text = update.message.text.strip()
    if state == 'awaiting_withdrawal_amount':
        try:
            amount = int(text.replace(',', '').replace('.', ''))
        except ValueError:
            await update.message.reply_text(lt(user_id, f"{E_LIMIT} Vui lòng nhập số tiền hợp lệ (chỉ số).", f"{E_LIMIT} Enter a valid amount using numbers only.", f"{E_LIMIT} 请输入有效金额（仅数字）。"))
            return
        balance = user_data_db.get(user_id_str, {}).get('balance', 0)
        if amount < MIN_WITHDRAWAL_AMOUNT:
            await update.message.reply_text(lt(user_id, "{limit} Số tiền rút tối thiểu là {amount:,} VNĐ.", "{limit} Minimum withdrawal is {amount:,} VND.", "{limit} 最低提现金额为 {amount:,} VND。", limit=E_LIMIT, amount=MIN_WITHDRAWAL_AMOUNT))
            return
        if amount > balance:
            await update.message.reply_text(lt(user_id, "{limit} Số dư không đủ (Hiện tại: {balance:,} VNĐ).", "{limit} Insufficient balance (Current: {balance:,} VND).", "{limit} 余额不足（当前：{balance:,} VND）。", limit=E_LIMIT, balance=balance))
            return
        context.user_data['withdrawal_amount'] = amount
        context.user_data['state'] = 'awaiting_bank_info'
        await update.message.reply_text(
            lt(
                user_id,
                "{success} <b>XÁC NHẬN SỐ TIỀN:</b> {amount:,} VNĐ\n\n{tag} <b>Vui lòng nhập thông tin nhận tiền:</b>\n<i>(Ngân hàng, Số tài khoản, Tên chủ tài khoản)</i>\n\nVí dụ: <code>Vietcombank - 0123456789 - NGUYEN VAN A</code>",
                "{success} <b>AMOUNT CONFIRMED:</b> {amount:,} VND\n\n{tag} <b>Enter receiving bank details:</b>\n<i>(Bank, Account number, Account holder)</i>\n\nExample: <code>Vietcombank - 0123456789 - NGUYEN VAN A</code>",
                "{success} <b>金额已确认：</b> {amount:,} VND\n\n{tag} <b>请输入收款信息：</b>\n<i>（银行、账号、账户名）</i>\n\n示例：<code>Vietcombank - 0123456789 - NGUYEN VAN A</code>",
                success=E_SUCCESS, tag=E_TAG, amount=amount,
            ), parse_mode=ParseMode.HTML,
        )
    elif state == 'awaiting_bank_info':
        amount = context.user_data.get('withdrawal_amount')
        bank_info, validation_error = normalize_bank_info(text)
        if validation_error:
            await update.message.reply_text(f"{E_LIMIT} {validation_error}")
            return
        withdrawal_lock = await get_api_key_lock(f"__withdrawal__:{user_id_str}")
        async with withdrawal_lock:
            current_balance = user_data_db.get(user_id_str, {}).get('balance', 0)
            if amount > current_balance:
                await update.message.reply_text(lt(user_id, "{limit} Số dư hiện tại không đủ ({balance:,} VNĐ). Yêu cầu đã bị hủy.", "{limit} Current balance is insufficient ({balance:,} VND). Request cancelled.", "{limit} 当前余额不足（{balance:,} VND），申请已取消。", limit=E_LIMIT, balance=current_balance))
                context.user_data.pop('state', None)
                context.user_data.pop('withdrawal_amount', None)
                return
            request_id = f"WD_{int(time.time())}_{random.randint(1000, 9999)}"
            withdrawal_requests[request_id] = {'user_id': user.id, 'full_name': user.full_name, 'username': user.username, 'amount': amount, 'bank_info': bank_info, 'status': 'pending', 'timestamp': time.time()}
            db_update_balance(user.id, current_balance - amount, reason=f"Yêu cầu rút tiền {request_id}")
            await save_data()
        await update.message.reply_text(
            lt(
                user_id,
                "{success} <b>GỬI YÊU CẦU THÀNH CÔNG!</b>\n\n{id_icon} Mã yêu cầu: <code>{request_id}</code>\n{tag} Số tiền: {amount:,} VNĐ\n{tag} Thông tin: {bank}\n\n{loading} Admin sẽ duyệt và chuyển khoản trong 24h.",
                "{success} <b>REQUEST SUBMITTED!</b>\n\n{id_icon} Request ID: <code>{request_id}</code>\n{tag} Amount: {amount:,} VND\n{tag} Details: {bank}\n\n{loading} Admin will review and transfer within 24 hours.",
                "{success} <b>申请提交成功！</b>\n\n{id_icon} 申请编号：<code>{request_id}</code>\n{tag} 金额：{amount:,} VND\n{tag} 收款信息：{bank}\n\n{loading} 管理员将在 24 小时内审核并转账。",
                success=E_SUCCESS, id_icon=E_ID, tag=E_TAG, loading=E_LOADING, request_id=request_id, amount=amount, bank=bank_info,
            ), parse_mode=ParseMode.HTML,
        )
        await notify_admin_withdrawal(context, request_id)
        
        # Clear state
        context.user_data.pop('state', None)
        context.user_data.pop('withdrawal_amount', None)

def normalize_bank_info(raw_bank_info: str) -> tuple[str | None, str | None]:
    """Validate and normalize ``Bank - account number - account holder`` input."""
    import re

    raw = " ".join(str(raw_bank_info or "").strip().split())
    if len(raw) > 160:
        return None, "Thông tin ngân hàng quá dài (tối đa 160 ký tự)."
    parts = [part.strip() for part in raw.split("-", 2)]
    if len(parts) != 3:
        return None, "Vui lòng nhập đúng mẫu: Ngân hàng - Số tài khoản - Tên chủ tài khoản."

    bank_name, account_number, account_holder = parts
    account_number = re.sub(r"\s+", "", account_number)
    if not 2 <= len(bank_name) <= 50 or not re.fullmatch(r"[0-9A-Za-z .&()]+", bank_name):
        return None, "Tên ngân hàng không hợp lệ."
    if not re.fullmatch(r"\d{6,19}", account_number):
        return None, "Số tài khoản phải gồm 6-19 chữ số."
    if not 2 <= len(account_holder) <= 70 or any(ch in "<>" for ch in account_holder):
        return None, "Tên chủ tài khoản không hợp lệ."
    return f"{bank_name} - {account_number} - {account_holder}", None


async def notify_admin_withdrawal(context: ContextTypes.DEFAULT_TYPE, request_id: str):
    """Notify admin about new withdrawal request"""
    req = withdrawal_requests.get(request_id)
    if not req: return
    
    is_order_refund = req.get("source") == "order_refund"
    request_title = "YÊU CẦU HOÀN VỀ NGÂN HÀNG" if is_order_refund else "YÊU CẦU RÚT TIỀN MỚI"
    safe_order_code = html.escape(str(req.get("order_code") or ""))
    safe_full_name = html.escape(str(req.get("full_name") or "Unknown"))
    safe_username = html.escape(str(req.get("username") or ""))
    safe_bank_info = html.escape(str(req.get("bank_info") or ""))
    safe_request_id = html.escape(str(request_id))
    order_line = f"{E_ID} Mã đơn: <code>{safe_order_code}</code>\n" if is_order_refund else ""
    msg = (
        f"{E_TAG} <b>{request_title}</b>\n\n"
        f"{E_USER} User: {safe_full_name} (@{safe_username})\n"
        f"{order_line}"
        f"{E_TAG} Số tiền: <b>{req['amount']:,} VNĐ</b>\n"
        f"{E_TAG} Bank: <code>{safe_bank_info}</code>\n"
        f"{E_ID} ID: <code>{safe_request_id}</code>"
    )
    
    keyboard = [
        [_btn("ĐÃ CHUYỂN KHOẢN", icon_id="6129870117619634982", callback_data=f"approve_withdraw:{request_id}")],
        [_btn("TỪ CHỐI", icon_id="5445353829304387411", callback_data=f"reject_withdraw:{request_id}")]
    ]
    
    try:
        await context.bot.send_message(
            ADMIN_USER_ID,
            msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        req["admin_notified_at"] = time.time()
        req.pop("admin_notification_error", None)
        notification_sent = True
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Cannot notify admin about withdrawal: {e}")
        req["admin_notification_error"] = str(e)[:300]
        notification_sent = False
    await save_data(force=True, tables=[WITHDRAWALS_FILE])
    return notification_sent

async def ga_comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle comments (replies) to Giveaway posts"""
    message = update.message
    if not message or not message.reply_to_message: return
    
    # FIX BUG: Skip private chats - GA chỉ hoạt động trong groups/channels
    # Điều này giúp email replies trong private chat không bị chặn
    if message.chat.type == 'private':
        return
    reply_to = message.reply_to_message
    
    # Simple case: Direct reply in Group
    ga_key = f"{message.chat.id}_{reply_to.message_id}"
    
    # If not found, try to see if it's a linked channel post (more complex, skip for now or assume simple)
    # Let's assume the bot is in the group/channel where GA is posted.
    
    if ga_key not in active_giveaways:
         return # Not a GA post

    ga = active_giveaways[ga_key]
    if ga['status'] != 'active': return
    if ga.get('mode') != 'comment': return # Only for Prediction/Comment mode
    
    # Record the entry
    user = message.from_user
    text = message.text.strip()
    
    # Check if user already commented? 
    # For prediction, maybe allow multiple? Or only first?
    # Let's simple: Record ALL, filtering logic will decide (e.g., take Earliest valid).
    
    entry = {
        'user_id': user.id,
        'full_name': user.full_name,
        'username': user.username,
        'text': text,
        'timestamp': time.time(),
        'message_id': message.message_id,
        'edited': False
    }
    
    ga.setdefault('comments', []).append(entry)
    
    # Add to participants list for stats
    if user.id not in ga['participants']:
        ga['participants'].append(user.id)
        
    await save_data()
    
    # Feedback (React to message to confirm)
    try:
        await message.set_reaction("<tg-emoji emoji-id=\"6269163801178804220\">👍</tg-emoji>")
    except (Forbidden, BadRequest) as e:
        logger.debug(f"Cannot set reaction in giveaway comment: {e}") # Bot might not have permission

async def ga_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edited messages to disqualify"""
    edited_msg = update.edited_message
    if not edited_msg or not edited_msg.reply_to_message: return
    
    reply_to = edited_msg.reply_to_message
    ga_key = f"{edited_msg.chat.id}_{reply_to.message_id}"
    
    if ga_key not in active_giveaways: return
    
    ga = active_giveaways[ga_key]
    if ga.get('mode') != 'comment': return
    
    # Find entry and mark edited
    if 'comments' in ga:
        for entry in ga['comments']:
            if entry['message_id'] == edited_msg.message_id:
                entry['edited'] = True
                entry['text'] = edited_msg.text # Update text but flag as edited
                await save_data()
                
                # feedback
                try:
                    await edited_msg.reply_text(
                        f"{E_ERROR} <b>CẢNH BÁO:</b> Bạn đã sửa tin nhắn! Kết quả này sẽ KHÔNG được tính.",
                        parse_mode='HTML'
                    )
                except (Forbidden, BadRequest) as e:
                    logger.debug(f"Cannot notify edited giveaway comment: {e}")
                break

# ==============================================================================
#  BUTTON HANDLER (XỬ LÝ NÚT BẤM)ONLY)
# ==============================================================================
# Removed legacy SQLite functions to unify project storage around JSON.
# All data is now handled via load_data/save_data and in-memory globals.

# --- DB Helper Functions (Shimmed to use Globals) ---
def db_upsert_user(user_id, username, full_name, first_seen, balance=0):
    """Shim: Updates user_data_db global dict directly.
    FIX BUG #15: Normalize user_id consistently như db_get_user
    """
    # FIX: Normalize user_id to match db_get_user behavior
    user_id_str = str(int(user_id)) if user_id else None
    if not user_id_str:
        logger.error(f"Invalid user_id provided to db_upsert_user: {user_id}")
        return
    
    if user_id_str not in user_data_db:
         user_data_db[user_id_str] = {
             "user_id": int(user_id_str), 
             "username": username, 
             "full_name": full_name, # Fallback
             "first_name": full_name, # Consistent key
             "first_seen": first_seen, 
             "balance": int(balance)
         }
    else:
        # Update info but keep balance (don't overwrite)
        user_data_db[user_id_str]["username"] = username
        user_data_db[user_id_str]["first_name"] = full_name
        user_data_db[user_id_str]["user_id"] = int(user_id_str)
        # Balance is NOT overwritten unless explicitly set in future updates
    # Note: save_data() will be called periodically by the job queue.

def db_get_user(user_id):
    """Shim: Gets user from user_data_db global dict.
    FIX BUG #9: Always normalize numeric user_id to string for consistency.
    Gracefully ignore non-numeric IDs such as PARTNER_<name>.
    """
    user_id_str = _normalize_numeric_user_id(user_id)
    if not user_id_str:
        return None
    return user_data_db.get(user_id_str)

def is_user_registered(user_id) -> bool:
    """
    Registration gate check:
    - No profile => not registered
    - Legacy profile without `is_registered` => considered registered (backward compatibility)
    """
    user_id_str = _normalize_numeric_user_id(user_id)
    if not user_id_str:
        return False
    profile = user_data_db.get(user_id_str)
    if not profile:
        return False
    return bool(profile.get("is_registered", True))

def _normalize_numeric_user_id(user_id):
    """Normalize Telegram user ids and reject non-numeric identifiers safely."""
    if user_id in (None, ""):
        return None
    try:
        return str(int(user_id))
    except (TypeError, ValueError):
        return None

def db_update_balance(user_id, new_balance, reason="Unknown transaction"):
    """Update balance and append its transaction audit entry."""
    user_id_str = _normalize_numeric_user_id(user_id)
    if not user_id_str:
        logger.error(f"Invalid user_id provided to db_update_balance: {user_id}")
        return
    old_balance = user_data_db.get(user_id_str, {}).get("balance", 0)
    if user_id_str in user_data_db:
        user_data_db[user_id_str]["balance"] = int(new_balance)
    else:
        user_data_db[user_id_str] = {"balance": int(new_balance), "user_id": int(user_id_str)}
    amount_change = int(new_balance) - old_balance
    if amount_change != 0:
        transaction_history.setdefault(user_id_str, []).append({
            "amount": amount_change, "new_balance": int(new_balance), "reason": reason,
            "timestamp": time.time(), "tx_id": f"TX{int(time.time()*1000)}_{user_id_str}",
        })
        transaction_history[user_id_str] = transaction_history[user_id_str][-50:]
        create_background_task(save_data(tables=[TRANSACTION_HISTORY_FILE]))
    create_background_task(save_data(tables=[USERS_FILE]))


def _normalize_order_code(order_code) -> str:
    return str(order_code or "").strip().upper()


def _get_order_ref_key(order_data: dict) -> str:
    return str(order_data.get("api_partner_ref_key") or order_data.get("api_partner_ref") or "").upper()


def _index_order_record(order_data: dict):
    order_code = _normalize_order_code(order_data.get("order_code"))
    if order_code:
        order_data["order_code"] = order_code
        order_index[order_code] = order_data
    uid = str(order_data.get("user_id", "") or "")
    if uid:
        user_order_index.setdefault(uid, []).append(order_data)
    effective_uid = _api_get_effective_order_user_id(order_data)
    if effective_uid and str(effective_uid) != uid:
        user_order_index.setdefault(str(effective_uid), []).append(order_data)
    ref_key = _get_order_ref_key(order_data)
    if ref_key:
        api_partner_ref_index.setdefault(ref_key, []).append(order_data)


def _rebuild_order_indexes():
    order_index.clear(); user_order_index.clear(); api_partner_ref_index.clear()
    for order in order_history:
        _index_order_record(order)


def _dedupe_order_history_in_place() -> int:
    seen_codes, deduped_reversed = set(), []
    removed = 0
    for order in reversed(order_history):
        code = _normalize_order_code(order.get("order_code"))
        if code:
            order["order_code"] = code
            if code in seen_codes:
                removed += 1
                continue
            seen_codes.add(code)
        deduped_reversed.append(order)
    if removed:
        order_history[:] = list(reversed(deduped_reversed))
    return removed


def _snapshot_order_cost(order_data: dict):
    """Capture immutable cost data once; leave unknown costs unset."""
    if not isinstance(order_data, dict) or order_data.get("cost_total") is not None:
        return
    from decimal import Decimal, InvalidOperation
    try:
        quantity = max(0, int(order_data.get("quantity", 1) or 1))
    except (TypeError, ValueError):
        quantity = 1
    product = products.get(str(order_data.get("product_id") or ""))
    if not isinstance(product, dict):
        name = str(order_data.get("product_name") or "").strip().casefold()
        matches = [p for p in products.values() if isinstance(p, dict) and str(p.get("name") or "").strip().casefold() == name]
        product = matches[0] if len(matches) == 1 else None
    cost_total = cost_unit = None
    cost_source = ""
    if isinstance(product, dict):
        source_field = "cost_price"
        try:
            cost_unit = int(product[source_field])
            if cost_unit >= 0:
                cost_total, cost_source = cost_unit * quantity, source_field
        except (KeyError, TypeError, ValueError):
            pass
    if cost_total is None or cost_total < 0:
        order_data["cost_snapshot_missing"] = True
        return
    order_data.pop("cost_snapshot_missing", None)
    if cost_unit is not None:
        order_data["cost_unit"] = cost_unit
    order_data.update(cost_total=int(cost_total), cost_source=cost_source, cost_snapshot_at=time.time())


def db_add_order(order_data, schedule_save=True):
    """Add or replace an order while preserving its first cost snapshot."""
    order_code = _normalize_order_code(order_data.get("order_code"))
    existing_order = order_index.get(order_code) if order_code else None
    if isinstance(existing_order, dict) and existing_order.get("cost_total") is not None:
        for field in ("cost_unit", "cost_total", "cost_source", "cost_snapshot_at"):
            if field in existing_order:
                order_data[field] = existing_order[field]
        order_data.pop("cost_snapshot_missing", None)
    else:
        _snapshot_order_cost(order_data)
    if order_code:
        order_data["order_code"] = order_code
        old_count = len(order_history)
        order_history[:] = [o for o in order_history if _normalize_order_code(o.get("order_code")) != order_code]
        replaced = len(order_history) != old_count
    else:
        replaced = False
    order_history.append(order_data)
    reserved_order_codes.discard(order_code)
    _rebuild_order_indexes() if replaced else _index_order_record(order_data)
    if schedule_save:
        create_background_task(save_data(tables=[HISTORY_FILE]))

def db_get_order(order_code):
    """Shim: Finds order in order_history."""
    # FIX: Dùng index O(1) thay vì linear search O(n)
    return order_index.get(order_code)

def find_order_by_code_or_supplier_id(order_code):
    normalized_code = _normalize_order_code(order_code)
    if not normalized_code:
        return None
    return order_index.get(normalized_code)

def db_get_user_orders(user_id, limit=5):
    """Shim: Filters order_history using user_order_index for O(1) lookup."""
    orders = user_order_index.get(str(user_id), [])
    return list(reversed(orders))[:limit]

def db_check_tx_exists(tx_id):
    """Check the durable provider transaction registry."""
    return db_transaction_exists(tx_id)

def db_add_tx(tx_id):
    """Mark a claimed provider transaction as completed."""
    return db_complete_transaction(tx_id)


# Tối ưu: HTTP connection pooling với limits
# FIX: Bỏ httpx.Limits để tránh lỗi AsyncLibraryNotFoundError trên một số môi trường Windows cũ
# http_client = httpx.AsyncClient(
#     timeout=httpx.Timeout(15.0, connect=5.0),
#     limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
# )

# FIX: HTTP client sẽ được khởi tạo trong post_init và đóng trong pre_shutdown
http_client = None

def _get_http_client(timeout: float = 30.0) -> httpx.AsyncClient:

    if http_client and not http_client.is_closed:
        return http_client
    return httpx.AsyncClient(timeout=timeout)

# Cache để giảm database reads
_cache = {
    "last_save_time": 0,
    "save_debounce": 2.0,
    "pending_save": False,
    "last_cleanup_time": 0
}

# Throttle spam log cho lỗi Conflict (nhiều instance polling cùng token)
_last_conflict_report_time = 0.0
_conflict_report_cooldown = 60.0

class OrderStatus(Enum):
    COMPLETED = f"{E_SUCCESS} Hoàn thành"
    COMPLETED_RESENT = f"{E_SUCCESS} Hoàn thành (Gửi lại)"
    PENDING_LINK = f"{E_LOADING} Chờ link"

def status_text(s):
    return s.value if isinstance(s, OrderStatus) else str(s or "")

def is_completed_order(order: dict) -> bool:
    if not isinstance(order, dict):
        return False

    normalized_status = status_text(order.get("status")).strip().lower()
    if not normalized_status:
        return False

    if "hoàn thành" in normalized_status or "hoan thanh" in normalized_status:
        return True
    if normalized_status == "completed":
        return True
    if _api_is_order_record(order) and "api sold" in normalized_status:
        return True
    return False

def get_order_item_name(order: dict) -> str:
    """Resolve ten hien thi cho lich su don hang."""
    product_name = str(order.get("product_name") or "").strip()
    return product_name or "Sản phẩm"



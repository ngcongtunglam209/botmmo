def _get_payment_origin_message(update: Update):
    callback_query = getattr(update, "callback_query", None)
    if callback_query is not None and getattr(callback_query, "message", None) is not None:
        return callback_query.message
    return getattr(update, "message", None)


async def _reply_payment_generation_error(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    parse_mode='HTML',
):
    origin_message = _get_payment_origin_message(update)
    if origin_message is not None:
        await origin_message.reply_text(text, parse_mode=parse_mode)
        return

    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
    if chat_id is None and getattr(update, "effective_user", None) is not None:
        chat_id = update.effective_user.id
    if chat_id is not None:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)


async def _prompt_private_start_required(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tell the button presser to open private chat before we DM invoices."""
    user = getattr(update, "effective_user", None)
    query = getattr(update, "callback_query", None)
    deep_link = f"https://t.me/{BOT_USERNAME}?start=start"
    text = (
        "<b>Bot chua the nhan rieng cho ban.</b>\n\n"
        "Vui long bam nut ben duoi, gui <code>/start</code> trong chat rieng voi bot, "
        "roi quay lai tao don lai."
    )
    keyboard = InlineKeyboardMarkup([[
        _btn("Mo chat bot va gui /start", url=deep_link)
    ]])

    if query is not None:
        try:
            await query.answer(
                "Vui long mo chat rieng voi bot va gui /start truoc.",
                show_alert=True,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass

    origin_message = _get_payment_origin_message(update)
    if origin_message is not None:
        try:
            await origin_message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
            return
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass

    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
    if chat_id is not None and (user is None or chat_id != user.id):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=keyboard,
            )
        except (TelegramError, ValueError, KeyError, AttributeError):
            pass


def _build_payment_legal_notice(user_id: int) -> str:
    return "\n\n" + lt(
        user_id,
        "🛡️ <b>Tuân thủ pháp luật:</b> QR chỉ dùng để thanh toán đơn hàng hợp pháp tại Lâm Shop. Nghiêm cấm gian lận, rửa tiền, chiếm đoạt tài sản và mọi hành vi trái pháp luật.",
        "🛡️ <b>Legal compliance:</b> This QR is only for lawful Lâm Shop orders. Fraud, money laundering, misappropriation, and all unlawful activities are strictly prohibited.",
        "🛡️ <b>合法合规：</b> 此二维码仅用于支付 Lâm Shop 的合法订单。严禁欺诈、洗钱、侵占财产及任何违法行为。",
    )


def _refund_balance_used_if_needed(user_id: int, balance_used: int, reason: str):
    if int(balance_used or 0) <= 0:
        return
    current_info = db_get_user(user_id)
    current_bal = current_info.get('balance', 0) if current_info else 0
    db_update_balance(user_id, current_bal + int(balance_used or 0), reason=reason)


def _get_product_checkout_total_amount(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    prod_id: str,
    product_data: dict,
    quantity: int,
) -> int:
    price_base = product_data['price']
    price, _, _ = get_best_discount(user_id, prod_id, price_base)
    _store_coupon_code, store_coupon_discount = get_active_store_coupon_context(context, prod_id, quantity)
    if store_coupon_discount > 0:
        coupon_unit_price = max(0, price_base - store_coupon_discount)
        price = min(price, coupon_unit_price)
    return int(price or 0) * int(quantity or 0)


async def _send_product_qr_photo_or_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    order_code: str,
    prod_id: str,
    balance_used: int,
    **kwargs,
):
    try:
        return await context.bot.send_photo(**kwargs)
    except Forbidden:
        await release_reserved_order_code(order_code)
        user = getattr(update, "effective_user", None)
        if user is not None and balance_used > 0:
            _refund_balance_used_if_needed(
                user.id,
                balance_used,
                f"Refund: Private chat not started {prod_id}",
            )
        user_id = getattr(user, "id", "unknown")
        logger.info(f"Cannot send product QR to {user_id}: user has not started private chat")
        await _prompt_private_start_required(update, context)
        return None


async def generate_product_payment_qr(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prod_id: str,
    quantity: int = 1,
    balance_used: int = 0,
    extra_pending_data: dict | None = None,
):
    """Generates Payment QR for Store Products."""
    user = update.effective_user

    pending_code, _pending_detail = await get_user_pending_order(user.id)
    if pending_code:
        await context.bot.send_message(
            user.id,
            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn <b>{pending_code}</b> chưa hoàn thành!\n"
            "Vui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.",
            parse_mode='HTML',
        )
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: Already has pending order {pending_code}")
        return

    p = products.get(prod_id)
    if not p:
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: Product missing {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            "❌ Sản phẩm không tồn tại hoặc đã bị xóa.",
        )
        return

    store_coupon_code, _store_coupon_discount = get_active_store_coupon_context(context, prod_id, quantity)
    total_amount = _get_product_checkout_total_amount(user.id, context, prod_id, p, quantity)
    qr_amount = total_amount - balance_used if balance_used > 0 else total_amount

    try:
        order_code = await generate_unique_order_code(prefix="ICLD", length=6)
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        logger.error(f"Cannot generate unique order code: {exc}")
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: QR order code failed {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            "❌ Lỗi hệ thống. Vui lòng thử lại sau 30 giây.",
        )
        return

    secret_transfer_code = generate_secret_transfer_code()
    transfer_content = build_transfer_content(secret_transfer_code)
    qr_link = create_vietqr_link(qr_amount, transfer_content)
    if not qr_link:
        await release_reserved_order_code(order_code)
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: QR link failed {prod_id}")
        await _reply_payment_generation_error(update, context, "❌ Lỗi hệ thống tạo mã QR.")
        return

    lang = get_user_lang(user.id)
    qr_text = {
        "vi": {"invoice": "HÓA ĐƠN ĐIỆN TỬ", "product": "Sản phẩm", "quantity": "Số lượng", "total": "Tổng giá", "wallet": "Đã trừ ví", "due": "Cần CK", "payment": "Thanh toán", "order": "Mã đơn", "payment_code": "Mã thanh toán", "content": "Nội dung CK", "instruction": "Vui lòng chuyển đúng số tiền và nội dung để bot lên đơn tự động nhé!", "cancel_after": "Đơn hàng sẽ bị hủy sau {minutes} phút.", "refund": " Ví sẽ được hoàn lại nếu hủy.", "expires": "Hết hạn lúc", "cancel": "Hủy giao dịch"},
        "en": {"invoice": "ELECTRONIC INVOICE", "product": "Product", "quantity": "Quantity", "total": "Total", "wallet": "Wallet deducted", "due": "Bank transfer due", "payment": "Payment", "order": "Order code", "payment_code": "Payment code", "content": "Transfer content", "instruction": "Transfer the exact amount with the exact content for automatic processing.", "cancel_after": "The order will be cancelled after {minutes} minutes.", "refund": " Wallet funds will be refunded if cancelled.", "expires": "Expires at", "cancel": "Cancel payment"},
        "zh": {"invoice": "电子账单", "product": "商品", "quantity": "数量", "total": "总价", "wallet": "已扣钱包余额", "due": "需银行转账", "payment": "付款金额", "order": "订单号", "payment_code": "付款代码", "content": "转账内容", "instruction": "请准确转账指定金额并填写转账内容，以便系统自动处理订单。", "cancel_after": "订单将在 {minutes} 分钟后取消。", "refund": " 取消后钱包余额将退还。", "expires": "到期时间", "cancel": "取消付款"},
    }[lang]
    product_name = p.get(f"name_{lang}") or p.get("name") or prod_id

    if balance_used > 0:
        balance_line = (
            f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>{qr_text["total"]}:</b> {total_amount:,} VNĐ\n'
            f'<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>{qr_text["wallet"]}:</b> -{balance_used:,} VNĐ\n'
            f'<tg-emoji emoji-id="5278467510604160626">🏦</tg-emoji> <b>{qr_text["due"]}:</b> <b>{qr_amount:,} VNĐ</b>\n'
        )
    else:
        balance_line = f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>{qr_text["payment"]}:</b> {qr_amount:,} VNĐ\n'

    order_code_label = qr_text["order"]
    caption = (
        f'<tg-emoji emoji-id="5240228673738527951">🏷</tg-emoji> <b>{qr_text["invoice"]}</b>\n'
        f"━━━━━━━━━━━━━━━━━━\n<blockquote>"
        f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>{qr_text["product"]}:</b> <i>{html.escape(str(product_name))}</i>\n'
        f'<tg-emoji emoji-id="5305749482170758709">0️⃣</tg-emoji> <b>{qr_text["quantity"]}:</b> {quantity}\n'
        f'{balance_line}'
        f'<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>{order_code_label}:</b> <code>{order_code}</code>\n'
        f'<tg-emoji emoji-id="5373251851074415873">📝</tg-emoji> <b>{qr_text["content"]}:</b> <code>{transfer_content}</code></blockquote>\n\n'
        f'<tg-emoji emoji-id="5411225014148014586">🔴</tg-emoji> <i>{qr_text["instruction"]}</i>\n'
        f'<tg-emoji emoji-id="5458382591121964689">✍️</tg-emoji> {qr_text["cancel_after"].format(minutes=ORDER_EXPIRATION_SECONDS // 60)}'
        f'{qr_text["refund"] if balance_used > 0 else ""}\n'
        f'<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>{qr_text["expires"]}:</b> {(datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)).strftime("%H:%M:%S")}'
    )
    caption += _build_payment_legal_notice(user.id)

    try:
        created_ts = time.time()
        sent_message = await _send_product_qr_photo_or_prompt(
            update, context, order_code, prod_id, balance_used,
            chat_id=user.id, photo=qr_link, caption=caption, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                _btn(qr_text["cancel"], icon_id="6186252635805323641", callback_data=f"cancel_payment_{prod_id}", style="danger")
            ]]),
        )
        if sent_message is None:
            return False
        pending_payload = {
            "user_id": user.id,
            "type": "store_product",
            "product_id": prod_id,
            "amount": qr_amount,
            "total_amount": total_amount,
            "balance_used": balance_used,
            "quantity": quantity,
            "time": created_ts,
            "timestamp": created_ts,
            "status": "pending_payment",
            "full_name": user.full_name,
            "username": user.username,
            "message_id": sent_message.message_id,
            "coupon_code": store_coupon_code,
            "product_name": p['name'],
            "payment_method": "bank_transfer",
            "secret_transfer_code": secret_transfer_code,
            "transfer_content": transfer_content,
        }
        if isinstance(extra_pending_data, dict):
            pending_payload.update(extra_pending_data)
        await pending_set(order_code, pending_payload)
        await save_data(force=True, tables=[PENDING_ORDERS_FILE])
        clear_store_coupon_context(context)
        return True
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        await release_reserved_order_code(order_code)
        logger.error(f"Error sending product QR: {exc}")
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: QR generation failed {prod_id}")
            await context.bot.send_message(
                user.id,
                f"❌ Không thể tạo mã QR. Đã hoàn lại {balance_used:,}đ vào ví.\nVui lòng thử lại sau.",
            )
        else:
            await context.bot.send_message(user.id, "❌ Không thể tạo mã QR. Vui lòng thử lại sau.")


        return False


async def generate_product_payment_rpay(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prod_id: str,
    quantity: int = 1,
    balance_used: int = 0,
    extra_pending_data: dict | None = None,
    network: str = "",
):
    """Tao hoa don USDT qua RPay cho san pham trong cua hang."""
    user = update.effective_user
    if not is_usdt_payment_enabled():
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Phương thức thanh toán này chưa được cấu hình.", "This payment method is not configured yet.", "此付款方式尚未配置。"),
        )
        return

    pending_code, _pending_detail = await get_user_pending_order(user.id)
    if pending_code:
        await context.bot.send_message(
            user.id,
            lt(user.id, '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Bạn đang có đơn <b>{code}</b> chưa hoàn thành!\nVui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.', '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> You have an unfinished order <b>{code}</b>!\nComplete or cancel it before creating a new order.', '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> 您有一个未完成订单 <b>{code}</b>！\n请先完成或取消该订单。', code=pending_code),
            parse_mode='HTML',
        )
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: Already has pending order {pending_code}")
        return

    p = products.get(prod_id)
    if not p:
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: Product missing {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Sản phẩm không tồn tại hoặc đã bị xóa.", "Product does not exist or was removed.", "商品不存在或已被删除。"),
        )
        return

    store_coupon_code, _store_coupon_discount = get_active_store_coupon_context(context, prod_id, quantity)
    total_amount = _get_product_checkout_total_amount(user.id, context, prod_id, p, quantity)
    amount_due = total_amount - balance_used if balance_used > 0 else total_amount

    try:
        order_code = await generate_unique_order_code(prefix="ICLD", length=6)
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        logger.error(f"Cannot generate unique RPay order code: {exc}")
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: RPay order code failed {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Lỗi hệ thống. Vui lòng thử lại sau 30 giây.", "System error. Try again in 30 seconds.", "系统错误，请在 30 秒后重试。"),
        )
        return

    try:
        invoice = await create_rpay_order(
            order_code=order_code,
            amount_vnd=amount_due,
            goods_name=p["name"],
            goods_detail=f"{p['name']} x{quantity}",
            network=network,
        )
    except Exception as exc:
        await release_reserved_order_code(order_code)
        logger.error(f"Error creating RPay invoice for {order_code}: {exc}")
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: RPay invoice failed {prod_id}")
            await context.bot.send_message(user.id, lt(user.id, "Không thể tạo hóa đơn USDT. Đã hoàn lại {amount:,}đ vào ví.\nVui lòng thử lại sau.", "Could not create the USDT invoice. {amount:,} VND was refunded to your wallet.\nPlease try again later.", "无法创建 USDT 账单。{amount:,} VND 已退回钱包。\n请稍后重试。", amount=balance_used))
        else:
            await context.bot.send_message(user.id, lt(user.id, "Không thể tạo hóa đơn USDT. Vui lòng thử lại sau.", "Could not create the USDT invoice. Please try again later.", "无法创建 USDT 账单，请稍后重试。"))
        return

    network_name = str(invoice.get("network_name") or invoice.get("network") or "").strip()
    token_symbol = str(invoice.get("token") or "USDT").strip()
    expires_at = str(invoice.get("expires_at") or "").strip() or (
        datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)
    ).strftime('%H:%M:%S')

    balance_line = lt(user.id, '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Tổng giá:</b> {total:,} VNĐ\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>Đã trừ ví:</b> -{used:,} VNĐ\n', '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Total:</b> {total:,} VND\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>Wallet used:</b> -{used:,} VND\n', '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>总价：</b> {total:,} VND\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>钱包抵扣：</b> -{used:,} VND\n', total=total_amount, used=balance_used) if balance_used > 0 else ""
    caption = lt(
        user.id,
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>THANH TOÁN {token} ({network})</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Sản phẩm:</b> <i>{product}</i> x{quantity}\n{balance}• <b>Cần thanh toán:</b> {due:,} VNĐ\n\n• <b>Số tiền {token}:</b> <code>{crypto}</code>\n• <b>Địa chỉ ví:</b> <code>{wallet}</code>\n• <b>Mạng lưới:</b> {network}\n• <b>Tỉ giá:</b> 1 USDT = {rate:,} VNĐ\n• <b>Mã đơn:</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>LƯU Ý QUAN TRỌNG:</b>\n- Chuyển <b>đúng số tiền ở trên</b> để hệ thống tự nhận diện.\n- Chỉ dùng mạng <b>{network}</b>. Chuyển sai mạng sẽ mất tiền.\n- Hết hạn sau {minutes} phút.{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Hết hạn lúc:</b> {expires}',
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>{token} PAYMENT ({network})</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Product:</b> <i>{product}</i> x{quantity}\n{balance}• <b>Amount due:</b> {due:,} VND\n\n• <b>{token} amount:</b> <code>{crypto}</code>\n• <b>Wallet address:</b> <code>{wallet}</code>\n• <b>Network:</b> {network}\n• <b>Rate:</b> 1 USDT = {rate:,} VND\n• <b>Order code:</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>IMPORTANT:</b>\n- Send the <b>exact amount above</b> for automatic detection.\n- Use only the <b>{network}</b> network. Funds sent through another network may be lost.\n- Expires in {minutes} minutes.{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Expires at:</b> {expires}',
        '<tg-emoji emoji-id="5281029063459234079">🤑</tg-emoji> <b>{token} 支付（{network}）</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>商品：</b> <i>{product}</i> x{quantity}\n{balance}• <b>应付：</b> {due:,} VND\n\n• <b>{token} 金额：</b> <code>{crypto}</code>\n• <b>钱包地址：</b> <code>{wallet}</code>\n• <b>网络：</b> {network}\n• <b>汇率：</b> 1 USDT = {rate:,} VND\n• <b>订单号：</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>重要提示：</b>\n- 请转入<b>上方准确金额</b>以便系统自动识别。\n- 仅使用 <b>{network}</b> 网络，转错网络可能造成资金丢失。\n- {minutes} 分钟后过期。{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>到期时间：</b> {expires}',
        token=html.escape(token_symbol), network=html.escape(network_name or "USDT"), product=html.escape(str(p['name'])), quantity=quantity, balance=balance_line, due=amount_due, crypto=html.escape(str(invoice.get("amount_text") or "")), wallet=html.escape(str(invoice.get("address") or "")), rate=invoice.get("rate", USDT_RATE_VND_PER_USDT), code=order_code, minutes=ORDER_EXPIRATION_SECONDS // 60, refund=lt(user.id, " Ví sẽ được hoàn lại nếu hủy.", " Wallet funds will be refunded if cancelled.", " 取消后钱包资金将退回。") if balance_used > 0 else "", expires=html.escape(expires_at),
    )
    caption += _build_payment_legal_notice(user.id)

    try:
        created_ts = time.time()
        qr_photo = rpay_qr_photo(invoice)
        if qr_photo is None:
            raise ValueError(f"RPay invoice {invoice.get('trans_id')} khong co QR")

        sent_message = await _send_product_qr_photo_or_prompt(
            update,
            context,
            order_code,
            prod_id,
            balance_used,
            chat_id=user.id,
            photo=qr_photo,
            caption=caption,
            parse_mode='HTML',
            reply_markup=build_rpay_checkout_keyboard(invoice, order_code, user_id=user.id),
        )
        if sent_message is None:
            return
        pending_payload = {
            "user_id": user.id,
            "type": "store_product",
            "product_id": prod_id,
            "product_name": p['name'],
            "amount": amount_due,
            "original_price": total_amount,
            "total_amount": total_amount,
            "balance_used": balance_used,
            "quantity": quantity,
            "time": created_ts,
            "timestamp": created_ts,
            "status": "pending_payment",
            "full_name": user.full_name,
            "username": user.username,
            "message_id": sent_message.message_id,
            "coupon_code": store_coupon_code,
            "payment_method": "usdt_rpay",
            "provider": "rpay",
            "rpay_trans_id": str(invoice.get("trans_id") or ""),
            "rpay_request_id": str(invoice.get("request_id") or ""),
            "rpay_amount": str(invoice.get("amount_text") or ""),
            "rpay_token": token_symbol,
            "rpay_network": str(invoice.get("network") or ""),
            "rpay_network_name": network_name,
            "rpay_address": str(invoice.get("address") or ""),
            "rpay_url_payment": str(invoice.get("url_payment") or ""),
            "rpay_expires_at": expires_at,
            "rpay_rate": str(invoice.get("rate", USDT_RATE_VND_PER_USDT)),
        }
        if isinstance(extra_pending_data, dict):
            pending_payload.update(extra_pending_data)
        await pending_set(order_code, pending_payload)
        await save_data(force=True, tables=[PENDING_ORDERS_FILE])
        clear_store_coupon_context(context)
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        await release_reserved_order_code(order_code)
        logger.error(f"Error sending RPay product invoice: {exc}")
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: RPay invoice send failed {prod_id}")
            await context.bot.send_message(user.id, lt(user.id, "Không thể gửi hóa đơn USDT. Đã hoàn lại {amount:,}đ vào ví.\nVui lòng thử lại sau.", "Could not send the USDT invoice. {amount:,} VND was refunded to your wallet.\nPlease try again later.", "无法发送 USDT 账单。{amount:,} VND 已退回钱包。\n请稍后重试。", amount=balance_used))
        else:
            await context.bot.send_message(user.id, lt(user.id, "Không thể gửi hóa đơn USDT. Vui lòng thử lại sau.", "Could not send the USDT invoice. Please try again later.", "无法发送 USDT 账单，请稍后重试。"))


async def generate_product_payment_binance_pay(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prod_id: str,
    quantity: int = 1,
    balance_used: int = 0,
    extra_pending_data: dict | None = None,
):
    """Hoa don Binance Pay: khach chuyen thang vao Binance ID cua shop.

    Khong co API tao hoa don, doi soat bang feed lich su nen so tien phai duy
    nhat - xem app/integrations/binancepay_api.py.
    """
    user = update.effective_user
    if not is_binance_pay_enabled():
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Phương thức thanh toán này chưa được cấu hình.", "This payment method is not configured yet.", "此付款方式尚未配置。"),
        )
        return

    pending_code, _pending_detail = await get_user_pending_order(user.id)
    if pending_code:
        await context.bot.send_message(
            user.id,
            lt(user.id, '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> Bạn đang có đơn <b>{code}</b> chưa hoàn thành!\nVui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.', '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> You have an unfinished order <b>{code}</b>!\nComplete or cancel it before creating a new order.', '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> 您有一个未完成订单 <b>{code}</b>！\n请先完成或取消该订单。', code=pending_code),
            parse_mode='HTML',
        )
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: Already has pending order {pending_code}")
        return

    p = products.get(prod_id)
    if not p:
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: Product missing {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Sản phẩm không tồn tại hoặc đã bị xóa.", "Product does not exist or was removed.", "商品不存在或已被删除。"),
        )
        return

    store_coupon_code, _store_coupon_discount = get_active_store_coupon_context(context, prod_id, quantity)
    total_amount = _get_product_checkout_total_amount(user.id, context, prod_id, p, quantity)
    amount_due = total_amount - balance_used if balance_used > 0 else total_amount

    try:
        order_code = await generate_unique_order_code(prefix="ICLD", length=6)
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        logger.error(f"Cannot generate unique Binance Pay order code: {exc}")
        _refund_balance_used_if_needed(user.id, balance_used, f"Refund: Binance Pay order code failed {prod_id}")
        await _reply_payment_generation_error(
            update,
            context,
            lt(user.id, "Lỗi hệ thống. Vui lòng thử lại sau 30 giây.", "System error. Try again in 30 seconds.", "系统错误，请在 30 秒后重试。"),
        )
        return

    try:
        quote = await create_binance_pay_order(order_code=order_code, amount_vnd=amount_due)
    except Exception as exc:
        await release_reserved_order_code(order_code)
        logger.error(f"Error creating Binance Pay quote for {order_code}: {exc}")
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: Binance Pay quote failed {prod_id}")
            await context.bot.send_message(user.id, lt(user.id, "Không thể tạo hóa đơn Binance Pay. Đã hoàn lại {amount:,}đ vào ví.\nVui lòng thử lại sau.", "Could not create the Binance Pay invoice. {amount:,} VND was refunded to your wallet.\nPlease try again later.", "无法创建 Binance Pay 账单。{amount:,} VND 已退回钱包。\n请稍后重试。", amount=balance_used))
        else:
            await context.bot.send_message(user.id, lt(user.id, "Không thể tạo hóa đơn Binance Pay. Vui lòng thử lại sau.", "Could not create the Binance Pay invoice. Please try again later.", "无法创建 Binance Pay 账单，请稍后重试。"))
        return

    amount_text = str(quote.get("amount_text") or "")
    balance_line = lt(user.id, '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Tổng giá:</b> {total:,} VNĐ\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>Đã trừ ví:</b> -{used:,} VNĐ\n', '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Total:</b> {total:,} VND\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>Wallet used:</b> -{used:,} VND\n', '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>总价：</b> {total:,} VND\n<tg-emoji emoji-id="5213403875670765022">💳</tg-emoji> <b>钱包抵扣：</b> -{used:,} VND\n', total=total_amount, used=balance_used) if balance_used > 0 else ""
    caption = lt(
        user.id,
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>THANH TOÁN BINANCE PAY</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Sản phẩm:</b> <i>{product}</i> x{quantity}\n{balance}• <b>Cần thanh toán:</b> {due:,} VNĐ\n\n• <b>Số tiền USDT:</b> <code>{crypto}</code>\n• <b>ID Binance:</b> <code>{payid}</code>\n• <b>Tỉ giá:</b> 1 USDT = {rate:,} VNĐ\n• <b>Mã đơn:</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>LƯU Ý QUAN TRỌNG:</b>\n- Chuyển <b>đúng số tiền {crypto} USDT</b> — kể cả số lẻ cuối. Số lẻ đó là thứ duy nhất giúp bot nhận ra đơn của bạn.\n- Chuyển thiếu hoặc thừa dù chỉ 0.0001 USDT thì bot <b>không tự nhận</b> được, phải liên hệ hỗ trợ đối soát tay.\n- Chỉ chuyển qua <b>Binance Pay</b> tới đúng ID ở trên.\n- Hết hạn sau {minutes} phút.{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Hết hạn lúc:</b> {expires}',
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>BINANCE PAY PAYMENT</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Product:</b> <i>{product}</i> x{quantity}\n{balance}• <b>Amount due:</b> {due:,} VND\n\n• <b>USDT amount:</b> <code>{crypto}</code>\n• <b>Binance ID:</b> <code>{payid}</code>\n• <b>Rate:</b> 1 USDT = {rate:,} VND\n• <b>Order code:</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>IMPORTANT:</b>\n- Send <b>exactly {crypto} USDT</b>, including the trailing decimals. Those decimals are the only thing that identifies your order.\n- If you send even 0.0001 USDT more or less, the bot <b>cannot match it automatically</b> and support has to reconcile it by hand.\n- Send via <b>Binance Pay</b> to the ID above only.\n- Expires in {minutes} minutes.{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>Expires at:</b> {expires}',
        '<tg-emoji emoji-id="{icon}">🌐</tg-emoji> <b>BINANCE PAY 支付</b>\n━━━━━━━━━━━━━━━━━━\n<blockquote><tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>商品：</b> <i>{product}</i> x{quantity}\n{balance}• <b>应付：</b> {due:,} VND\n\n• <b>USDT 金额：</b> <code>{crypto}</code>\n• <b>Binance ID：</b> <code>{payid}</code>\n• <b>汇率：</b> 1 USDT = {rate:,} VND\n• <b>订单号：</b> <code>{code}</code></blockquote>\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>重要提示：</b>\n- 请转入<b>准确的 {crypto} USDT</b>，包括末尾小数。该小数是识别您订单的唯一依据。\n- 多转或少转哪怕 0.0001 USDT，机器人都<b>无法自动识别</b>，需联系客服人工核对。\n- 仅通过 <b>Binance Pay</b> 转至上方 ID。\n- {minutes} 分钟后过期。{refund}\n<tg-emoji emoji-id="5213349767672769194">⏰</tg-emoji> <b>到期时间：</b> {expires}',
        icon=CRYPTO_BUTTON_ICON_ID, product=html.escape(str(p['name'])), quantity=quantity, balance=balance_line, due=amount_due, crypto=html.escape(amount_text), payid=html.escape(str(quote.get("binance_pay_id") or "")), rate=quote.get("rate", USDT_RATE_VND_PER_USDT), code=order_code, minutes=ORDER_EXPIRATION_SECONDS // 60, refund=lt(user.id, " Ví sẽ được hoàn lại nếu hủy.", " Wallet funds will be refunded if cancelled.", " 取消后钱包资金将退回。") if balance_used > 0 else "", expires=(datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)).strftime('%H:%M:%S'),
    )
    caption += _build_payment_legal_notice(user.id)

    try:
        created_ts = time.time()
        sent_message = await _send_product_qr_photo_or_prompt(
            update,
            context,
            order_code,
            prod_id,
            balance_used,
            chat_id=user.id,
            photo=binance_pay_qr_photo(),
            caption=caption,
            parse_mode='HTML',
            reply_markup=build_binance_pay_checkout_keyboard(order_code, amount_text, user_id=user.id),
        )
        if sent_message is None:
            return
        pending_payload = {
            "user_id": user.id,
            "type": "store_product",
            "product_id": prod_id,
            "product_name": p['name'],
            "amount": amount_due,
            "original_price": total_amount,
            "total_amount": total_amount,
            "balance_used": balance_used,
            "quantity": quantity,
            "time": created_ts,
            "timestamp": created_ts,
            "status": "pending_payment",
            "full_name": user.full_name,
            "username": user.username,
            "message_id": sent_message.message_id,
            "coupon_code": store_coupon_code,
            "payment_method": "binance_pay",
            "provider": "binance_pay",
            # Doi soat khop theo dung chuoi nay, nen no phai duoc luu y het nhu
            # da hien cho khach.
            "binance_pay_amount": amount_text,
            "binance_pay_id": str(quote.get("binance_pay_id") or ""),
            "binance_pay_rate": str(quote.get("rate", USDT_RATE_VND_PER_USDT)),
        }
        if isinstance(extra_pending_data, dict):
            pending_payload.update(extra_pending_data)
        await pending_set(order_code, pending_payload)
        await save_data(force=True, tables=[PENDING_ORDERS_FILE])
        clear_store_coupon_context(context)
    except (TelegramError, ValueError, KeyError, AttributeError) as exc:
        await release_reserved_order_code(order_code)
        logger.error(f"Error sending Binance Pay product invoice: {exc}")
        if balance_used > 0:
            current_info = db_get_user(user.id)
            current_bal = current_info.get('balance', 0) if current_info else 0
            db_update_balance(user.id, current_bal + balance_used, reason=f"Refund: Binance Pay invoice send failed {prod_id}")
            await context.bot.send_message(user.id, lt(user.id, "Không thể gửi hóa đơn Binance Pay. Đã hoàn lại {amount:,}đ vào ví.\nVui lòng thử lại sau.", "Could not send the Binance Pay invoice. {amount:,} VND was refunded to your wallet.\nPlease try again later.", "无法发送 Binance Pay 账单。{amount:,} VND 已退回钱包。\n请稍后重试。", amount=balance_used))
        else:
            await context.bot.send_message(user.id, lt(user.id, "Không thể gửi hóa đơn Binance Pay. Vui lòng thử lại sau.", "Could not send the Binance Pay invoice. Please try again later.", "无法发送 Binance Pay 账单，请稍后重试。"))

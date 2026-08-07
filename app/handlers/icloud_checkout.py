
async def generate_payment_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, email: str, coupon_code: str = None, quantity: int = 1, payment_provider: str = "bank"):
    user = update.effective_user
    final_price = ICLOUD_PACKAGE_PRICE
    coupon_applied_text = ""

    pending_code, pending_detail = await get_user_pending_order(user.id)
    if pending_code:
        await context.bot.send_message(user.id, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn <b>{pending_code}</b> chưa hoàn thành!\nVui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.", parse_mode='HTML')
        return
    
    if not email or not EMAIL_REGEX.match(email):
        await context.bot.send_message(user.id, "❌ Email không hợp lệ. Vui lòng nhập lại hoặc bắt đầu lại bằng /start")
        return

    # Xử lý coupon với nhiều kiểm tra
    try:
        if coupon_code:
            coupon_details = coupons.get(coupon_code.upper())
            if coupon_details:
                # Kiểm tra hạn sử dụng coupon
                try:
                    is_expired = datetime.now() > datetime.strptime(
                        coupon_details.get('expires', '01-01-1970'), 
                        '%d-%m-%Y'
                    ).replace(hour=23, minute=59, second=59)
                except (ValueError, TypeError):
                    is_expired = True

                # Kiểm tra số lượng sử dụng
                is_used_up = (
                    isinstance(coupon_details.get('quantity'), int) and 
                    coupon_details.get('used', 0) >= coupon_details.get('quantity')
                )

                if is_used_up or is_expired:
                    await context.bot.send_message(
                        user.id, 
                        f"{E_TAG} Rất tiếc, mã <b>{coupon_code}</b> đã hết hạn hoặc hết lượt sử dụng.", 
                        parse_mode=ParseMode.HTML
                    )
                    coupon_code = None
                else:
                    discount = coupon_details.get('discount', 0)
                    if coupon_details.get('is_percent', False):
                        discount_amount = int(ICLOUD_PACKAGE_PRICE * discount / 100)
                        final_price = max(0, ICLOUD_PACKAGE_PRICE - discount_amount)
                        coupon_applied_text = f"{E_SUCCESS} Đã áp dụng coupon <b>{coupon_code.upper()}</b> (Giảm {discount}% = {discount_amount:,} VNĐ)\n\n"
                    else:
                        final_price = max(0, ICLOUD_PACKAGE_PRICE - discount)
                        coupon_applied_text = f"{E_SUCCESS} Đã áp dụng coupon <b>{coupon_code.upper()}</b> (Giảm {discount:,} VNĐ)\n\n"
            else:
                await context.bot.send_message(user.id, f"{E_TAG} Mã giảm giá không hợp lệ.")
                coupon_code = None
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"Lỗi khi xử lý coupon: {e}")
        coupon_code = None

    # Tạo mã đơn hàng an toàn
    try:
        order_code = await generate_unique_order_code(prefix="ICLD", length=6)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"❌ CRITICAL: Cannot generate unique order code: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi hệ thống. Vui lòng thử lại sau 30 giây.")
        return

    # --- XỬ LÝ THANH TOÁN BẰNG SỐ DƯ ---
    user_id_str = str(user.id)
    user_record = user_data_db.setdefault(user_id_str, {})
    user_balance = user_record.get("balance", 0)
    balance_used = 0
    balance_text = ""

    if user_balance > 0:
        if user_balance >= final_price:
            balance_used = final_price
            final_price = 0
        else:
            balance_used = user_balance
            final_price -= user_balance

        balance_text = f"{E_TAG} <b>Sử dụng số dư:</b> -{balance_used:,} VNĐ\n"
    if final_price == 0 and balance_used > 0:
        db_update_balance(user.id, user_balance - balance_used, reason=f"Purchase iCloud: {order_code}")
        await save_data(tables=[USERS_FILE])
        async with global_stock_lock:
            if available_links:
                link_to_send = next(iter(available_links))
                # REMOVED available_links.discard(link_to_send) for '1-Link Mode'
                completed_order = {
                    "user_id": user.id,
                    "order_code": order_code,
                    "email": email,
                    "amount": balance_used,
                    "coupon_used": coupon_code,
                    "link": link_to_send,
                    "status": OrderStatus.COMPLETED.value,
                    "timestamp": time.time(),
                    "full_name": user.full_name,
                    "username": user.username,
                    "payment_method": "balance",
                    "type": "icloud",
                    "product_name": "iCloud 2TB"
                }
                
                db_add_order(completed_order)
                if coupon_code and coupon_code.upper() in coupons:
                    coupons[coupon_code.upper()]['used'] = coupons[coupon_code.upper()].get('used', 0) + 1
                
                await save_data(force=True)
                has_link = True
            else:
                 # Hết link
                has_link = False
                completed_order = {
                    "user_id": user.id,
                    "order_code": order_code,
                    "email": email,
                    "amount": balance_used,
                    "coupon_used": coupon_code,
                    "link": "",
                    "status": OrderStatus.PENDING_LINK.value,
                    "timestamp": time.time(),
                    "full_name": user.full_name,
                    "username": user.username,
                    "payment_method": "balance",
                    "type": "icloud",
                    "product_name": "iCloud 2TB"
                }
                # FIX BUG #12: Dùng db_add_order để update cả index
                db_add_order(completed_order)
                # db_add_order now handles saving
                # await save_data(force=True)

        if has_link:
            email_sent, email_error = await send_activation_email(
                email,
                f"Link kích hoạt gói iCloud 2TB - {order_code}",
                user.full_name,
                link_to_send,
            )

            if email_sent:
                await context.bot.send_message(
                    user.id,
                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG (SỐ DƯ)</b> {E_SUCCESS}\n\n"
                    f"Mã đơn: <code>{order_code}</code>\n"
                    f"Đã trừ số dư: {balance_used:,} VNĐ\n"
                    f"Link kích hoạt đã được gửi đến email <b>{email}</b>.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(),
                )
            else:
                await context.bot.send_message(
                    user.id,
                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG (SỐ DƯ)</b> {E_SUCCESS}\n\n"
                    f"Mã đơn: <code>{order_code}</code>\n"
                    f"Đã trừ số dư: {balance_used:,} VNĐ\n\n"
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Gửi email kích hoạt thất bại. Vui lòng liên hệ Admin và cung cấp mã đơn.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(),
                )
                await safe_send_admin(
                    context.bot,
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>EMAIL GIAO HÀNG THẤT BẠI (BALANCE FLOW)</b>\n"
                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã đơn: <code>{order_code}</code>\n"
                    f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
                    f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Email: <code>{html.escape(email)}</code>\n"
                    f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lỗi: <code>{html.escape(str(email_error or 'Unknown error'))}</code>",
                )
            
            # Gửi thông báo Live Orders
            await send_live_order_notification(context, user.full_name, balance_used, product_name="iCloud 2TB", quantity=1, order_code=order_code)
            
            # Notify Admin
            await context.bot.send_message(
                ADMIN_USER_ID, 
                f"{E_SUCCESS} <b>ĐƠN HÀNG MỚI (SỐ DƯ)</b>\n"
                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách:</b> {format_user_name_html(user=user)}\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Thanh toán:</b> {balance_used:,} VNĐ (Balance)\n"
                f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Email:</b> <code>{email}</code>", 
                parse_mode=ParseMode.HTML
            )
        else:
            await context.bot.send_message(user.id, f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b>\n\nTuy nhiên, hệ thống đang tạm hết link. Admin sẽ gửi link cho bạn sớm nhất.", parse_mode=ParseMode.HTML)
            await safe_send_admin(context.bot, f"{E_SOS} <b>CẢNH BÁO: HẾT LINK!</b> {E_SOS}\n\nKhách <b>{email}</b> đã thanh toán bằng số dư. Vui lòng <code>/addlink</code>.")
            
        return
    
    secret_transfer_code = generate_secret_transfer_code()
    transfer_content = build_transfer_content(secret_transfer_code)
    # Mã hóa thông tin để tránh lỗi
    try:
        encoded_add_info = quote(transfer_content)
        encoded_account_name = quote(ACCOUNT_NAME)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi mã hóa thông tin: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi hệ thống. Vui lòng thử lại sau.")
        return

    # Tạo QR link với nhiều kiểm tra
    qr_link = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NUMBER}-print.png?amount={final_price}&addInfo={encoded_add_info}&accountName={encoded_account_name}"
    
    # Kiểm tra QR link với timeout và xử lý lỗi
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(qr_link)
            response.raise_for_status()  # Ném ngoại lệ nếu status code không thành công
    except httpx.RequestError as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi kiểm tra QR code URL: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi khi tạo mã QR. Vui lòng thử lại sau.")
        return
    except (httpx.HTTPError, ValueError, KeyError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi không xác định khi tạo QR: {e}")
        await context.bot.send_message(user.id, "❌ Đã có lỗi xảy ra. Vui lòng liên hệ hỗ trợ.")
        return

    # Tạo caption an toàn
    try:
        caption = (
            f"<tg-emoji emoji-id=\"6260059243605398502\">🏷</tg-emoji> <b>HÓA ĐƠN GIA HẠN iCLOUD</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Account:</b> {email}\n"
            f"{coupon_applied_text}{balance_text}"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Phải thanh toán:</b> {final_price:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung CK:</b> <code>{transfer_content}</code></blockquote>\n\n"
            f"{E_ERROR} <i><tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Vui lòng chuyển đúng số tiền và nội dung để bot lên đơn tự động nhé!</i>\n"
            f"{E_LOADING} Đơn hàng sẽ bị hủy sau {int(ORDER_EXPIRATION_SECONDS / 60)} phút.\n"
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> \u003cb\u003eHết hạn lúc:\u003c/b\u003e {(datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)).strftime('%H:%M:%S')}"
        )
    except (httpx.HTTPError, ValueError, KeyError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi tạo caption: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi định dạng thông báo. Vui lòng thử lại.")
        return

    # Gửi QR với nhiều lớp xử lý lỗi
    try:
        sent_message = await context.bot.send_photo(
            chat_id=user.id, 
            photo=qr_link, 
            caption=caption, 
            parse_mode=ParseMode.HTML
        )
        
        # Lưu thông tin đơn hàng
        await pending_set(order_code, {
            "user_id": user.id, 
            "full_name": user.full_name, 
            "username": user.username, 
            "email": email, 
            "amount": final_price, 
            "original_price": final_price + balance_used,
            "balance_used": balance_used,
            "coupon_code": coupon_code, 
            "time": time.time(), 
            "message_id": sent_message.message_id,
            "secret_transfer_code": secret_transfer_code,
            "transfer_content": transfer_content,
        })
        if balance_used > 0:
            db_update_balance(user.id, user_balance - balance_used, reason=f"Partial balance: {order_code}")
            await save_data(tables=[PENDING_ORDERS_FILE, USERS_FILE])
        else:
            await save_data(tables=[PENDING_ORDERS_FILE])
        
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi gửi mã QR cho user {user.id}: {e}")
        await context.bot.send_message(user.id, "Đã có lỗi xảy ra khi tạo mã QR. Vui lòng thử lại sau.")

async def generate_icloud_payment_usdt_trc20(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    order_code: str,
    email: str,
    coupon_code: str,
    final_price: int,
    balance_used: int,
    user_balance: int,
    coupon_applied_text: str = "",
    balance_text: str = "",
):
    user = update.effective_user

    try:
        usdt_quote = await get_usdt_trc20_order_quote(order_code, final_price)
    except Exception as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi tạo USDT TRC20 quote cho iCloud {order_code}: {e}")
        await context.bot.send_message(user.id, "❌ Không thể tạo hóa đơn USDT TRC20. Vui lòng thử lại sau.")
        return

    caption = (
        f'<tg-emoji emoji-id="{BINANCE_BUTTON_ICON_ID}">🌐</tg-emoji> <b>HÓA ĐƠN USDT TRC20</b>\n'
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Account:</b> {html.escape(email)}\n"
        f"{coupon_applied_text}{balance_text}"
        f"<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>Cần thanh toán:</b> {final_price:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5379773896352355687\">🪙</tg-emoji> <b>Gửi đúng:</b> <code>{html.escape(usdt_quote['amount_text'])}</code> USDT\n"
        f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>Đuôi random:</b> <code>+{html.escape(_decimal_to_fixed_text(usdt_quote['unique_delta'], int(usdt_quote.get('display_decimals') or 3)))}</code> USDT\n"
        f"<tg-emoji emoji-id=\"5231489647946768652\">🌐</tg-emoji> <b>Mạng:</b> TRON (TRC20)\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> <b>ID Binance:</b> <code>{html.escape(usdt_quote['wallet_address'])}</code>\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📈</tg-emoji> <b>Tỷ giá tự động (Binance P2P):</b> 1 USDT ≈ {usdt_quote.get('live_rate', USDT_TRC20_RATE_VND_PER_USDT):,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code></blockquote>\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Bot sẽ tự quét lịch sử nạp USDT và duyệt đơn khi ví nhận đúng số tiền trên.</i>\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Chỉ chuyển USDT qua TRC20. Sai network hoặc sai số tiền sẽ không tự duyệt.</i>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Đơn hàng sẽ bị hủy sau {int(ORDER_EXPIRATION_SECONDS / 60)} phút.\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>Hết hạn lúc:</b> {(datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)).strftime('%H:%M:%S')}"
    )

    try:
        created_ts = time.time()
        sent_message = await context.bot.send_message(
            chat_id=user.id,
            text=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=build_usdt_trc20_checkout_keyboard(
                order_code,
                usdt_quote.get("wallet_address") or USDT_TRC20_WALLET_ADDRESS,
            ),
        )
        await pending_set(order_code, {
            "user_id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "email": email,
            "amount": final_price,
            "original_price": final_price + balance_used,
            "balance_used": balance_used,
            "coupon_code": coupon_code,
            "time": created_ts,
            "timestamp": created_ts,
            "status": "pending_payment",
            "message_id": sent_message.message_id,
            "message_kind": "text",
            "payment_method": "usdt_trc20",
            "provider": "usdt_trc20",
            "product_name": "iCloud 2TB",
            "type": "icloud",
            "usdt_trc20_currency": usdt_quote.get("currency") or "USDT",
            "usdt_trc20_network": usdt_quote.get("network") or "TRON (TRC20)",
            "usdt_trc20_wallet_address": usdt_quote.get("wallet_address") or USDT_TRC20_WALLET_ADDRESS,
            "usdt_trc20_amount": usdt_quote.get("amount_text"),
            "usdt_trc20_amount_quant": usdt_quote.get("amount_quant"),
            "usdt_trc20_base_amount": _decimal_to_plain_text(usdt_quote.get("base_amount") or Decimal("0")),
            "usdt_trc20_unique_delta": _decimal_to_plain_text(usdt_quote.get("unique_delta") or Decimal("0")),
            "usdt_trc20_rate": str(usdt_quote.get("live_rate", USDT_TRC20_RATE_VND_PER_USDT)),
        })
        if balance_used > 0:
            db_update_balance(user.id, user_balance - balance_used, reason=f"Partial balance (USDT TRC20): {order_code}")
            await save_data(tables=[PENDING_ORDERS_FILE, USERS_FILE])
        else:
            await save_data(tables=[PENDING_ORDERS_FILE])
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi gửi hóa đơn USDT TRC20 cho user {user.id}: {e}")
        await context.bot.send_message(user.id, "Đã có lỗi xảy ra khi tạo hóa đơn USDT TRC20. Vui lòng thử lại sau.")


async def generate_icloud_payment_checkout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email: str,
    coupon_code: str = None,
    payment_provider: str = "bank",
):
    user = update.effective_user
    quote = prepare_icloud_checkout_quote(user.id, coupon_code)
    final_price = int(quote["amount_due"])
    balance_used = int(quote["balance_used"])
    user_balance = int(quote["user_balance"])
    coupon_code = quote.get("coupon_code")
    coupon_applied_text = quote.get("coupon_applied_text", "")
    balance_text = f"{E_TAG} <b>Sử dụng số dư:</b> -{balance_used:,} VNĐ\n" if balance_used > 0 else ""

    pending_code, _pending_detail = await get_user_pending_order(user.id)
    if pending_code:
        await context.bot.send_message(
            user.id,
            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn <b>{pending_code}</b> chưa hoàn thành!\nVui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.",
            parse_mode=ParseMode.HTML,
        )
        return

    if not email or not EMAIL_REGEX.match(email):
        await context.bot.send_message(
            user.id,
            "❌ Email không hợp lệ. Vui lòng nhập lại hoặc bắt đầu lại bằng /start",
        )
        return

    if quote.get("coupon_notice_text"):
        await context.bot.send_message(user.id, quote["coupon_notice_text"], parse_mode=ParseMode.HTML)

    try:
        order_code = await generate_unique_order_code(prefix="ICLD", length=6)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"❌ CRITICAL: Cannot generate unique iCloud order code: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi hệ thống. Vui lòng thử lại sau 30 giây.")
        return

    if final_price == 0 and balance_used > 0:
        db_update_balance(user.id, user_balance - balance_used, reason=f"Purchase iCloud: {order_code}")
        await save_data(tables=[USERS_FILE])
        async with global_stock_lock:
            if available_links:
                link_to_send = next(iter(available_links))
                # REMOVED available_links.discard(link_to_send) for '1-Link Mode'
                completed_order = {
                    "user_id": user.id,
                    "order_code": order_code,
                    "email": email,
                    "amount": balance_used,
                    "coupon_used": coupon_code,
                    "link": link_to_send,
                    "status": OrderStatus.COMPLETED.value,
                    "timestamp": time.time(),
                    "full_name": user.full_name,
                    "username": user.username,
                    "payment_method": "balance",
                    "type": "icloud",
                    "product_name": "iCloud 2TB",
                }
                db_add_order(completed_order)
                if coupon_code and coupon_code.upper() in coupons:
                    coupons[coupon_code.upper()]['used'] = coupons[coupon_code.upper()].get('used', 0) + 1
                await save_data(force=True)
                has_link = True
            else:
                has_link = False
                completed_order = {
                    "user_id": user.id,
                    "order_code": order_code,
                    "email": email,
                    "amount": balance_used,
                    "coupon_used": coupon_code,
                    "link": "",
                    "status": OrderStatus.PENDING_LINK.value,
                    "timestamp": time.time(),
                    "full_name": user.full_name,
                    "username": user.username,
                    "payment_method": "balance",
                    "type": "icloud",
                    "product_name": "iCloud 2TB",
                }
                db_add_order(completed_order)
                
        if has_link:
            email_sent, email_error = await send_activation_email(
                email,
                f"Link kích hoạt gói iCloud 2TB - {order_code}",
                user.full_name,
                link_to_send,
            )
            if email_sent:
                await context.bot.send_message(
                    user.id,
                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG (SỐ DƯ)</b> {E_SUCCESS}\n\n"
                    f"Mã đơn: <code>{order_code}</code>\n"
                    f"Đã trừ số dư: {balance_used:,} VNĐ\n"
                    f"Link kích hoạt đã được gửi đến email <b>{email}</b>.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(),
                )
            else:
                await context.bot.send_message(
                    user.id,
                    f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG (SỐ DƯ)</b> {E_SUCCESS}\n\n"
                    f"Mã đơn: <code>{order_code}</code>\n"
                    f"Đã trừ số dư: {balance_used:,} VNĐ\n\n"
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Gửi email kích hoạt thất bại. Vui lòng liên hệ Admin và cung cấp mã đơn.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(),
                )
                await safe_send_admin(
                    context.bot,
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>EMAIL GIAO HÀNG THẤT BẠI (BALANCE FLOW)</b>\n"
                    f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã đơn: <code>{order_code}</code>\n"
                    f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: {format_user_name_html(user=user)} (<code>{user.id}</code>)\n"
                    f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Email: <code>{html.escape(email)}</code>\n"
                    f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> Lỗi: <code>{html.escape(str(email_error or 'Unknown error'))}</code>",
                )

            await send_live_order_notification(context, user.full_name, balance_used, product_name="iCloud 2TB", quantity=1, order_code=order_code)
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"{E_SUCCESS} <b>ĐƠN HÀNG MỚI (SỐ DƯ)</b>\n"
                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Khách:</b> {format_user_name_html(user=user)}\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Thanh toán:</b> {balance_used:,} VNĐ (Balance)\n"
                f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Email:</b> <code>{email}</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await context.bot.send_message(
                user.id,
                f"{E_SUCCESS} <b>THANH TOÁN THÀNH CÔNG</b>\n\nTuy nhiên, hệ thống đang tạm hết link. Admin sẽ gửi link cho bạn sớm nhất.",
                parse_mode=ParseMode.HTML,
            )
            await safe_send_admin(
                context.bot,
                f"{E_SOS} <b>CẢNH BÁO: HẾT LINK!</b> {E_SOS}\n\nKhách <b>{email}</b> đã thanh toán bằng số dư. Vui lòng <code>/addlink</code>."
            )
        return

    if payment_provider in {"binance", "usdt_trc20"}:
        if not is_usdt_trc20_enabled():
            await release_reserved_order_code(order_code)
            await context.bot.send_message(user.id, "❌ USDT TRC20 chưa được cấu hình đầy đủ. Vui lòng dùng thanh toán ngân hàng.")
            return

        await generate_icloud_payment_usdt_trc20(
            update,
            context,
            order_code=order_code,
            email=email,
            coupon_code=coupon_code,
            final_price=final_price,
            balance_used=balance_used,
            user_balance=user_balance,
            coupon_applied_text=coupon_applied_text,
            balance_text=balance_text,
        )
        return

    secret_transfer_code = generate_secret_transfer_code()
    transfer_content = build_transfer_content(secret_transfer_code)
    try:
        encoded_add_info = quote(transfer_content)
        encoded_account_name = quote(ACCOUNT_NAME)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi mã hóa thông tin: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi hệ thống. Vui lòng thử lại sau.")
        return

    qr_link = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NUMBER}-print.png?amount={final_price}&addInfo={encoded_add_info}&accountName={encoded_account_name}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(qr_link)
            response.raise_for_status()
    except httpx.RequestError as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi kiểm tra QR code URL: {e}")
        await context.bot.send_message(user.id, "❌ Lỗi khi tạo mã QR. Vui lòng thử lại sau.")
        return
    except (httpx.HTTPError, ValueError, KeyError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi không xác định khi tạo QR: {e}")
        await context.bot.send_message(user.id, "❌ Đã có lỗi xảy ra. Vui lòng liên hệ hỗ trợ.")
        return

    caption = (
        f"<tg-emoji emoji-id=\"6260059243605398502\">🏷</tg-emoji> <b>HÓA ĐƠN GIA HẠN iCLOUD</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Account:</b> {email}\n"
        f"{coupon_applied_text}{balance_text}"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Phải thanh toán:</b> {final_price:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung CK:</b> <code>{transfer_content}</code></blockquote>\n\n"
        f"{E_ERROR} <i><tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Vui lòng chuyển đúng số tiền và nội dung để bot lên đơn tự động nhé!</i>\n"
        f"{E_LOADING} Đơn hàng sẽ bị hủy sau {int(ORDER_EXPIRATION_SECONDS / 60)} phút.\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>Hết hạn lúc:</b> {(datetime.now() + timedelta(seconds=ORDER_EXPIRATION_SECONDS)).strftime('%H:%M:%S')}"
    )

    try:
        created_ts = time.time()
        sent_message = await context.bot.send_photo(
            chat_id=user.id,
            photo=qr_link,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
        await pending_set(order_code, {
            "user_id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "email": email,
            "amount": final_price,
            "original_price": final_price + balance_used,
            "balance_used": balance_used,
            "coupon_code": coupon_code,
            "time": created_ts,
            "timestamp": created_ts,
            "status": "pending_payment",
            "message_id": sent_message.message_id,
            "payment_method": "bank_transfer",
            "product_name": "iCloud 2TB",
            "type": "icloud",
            "secret_transfer_code": secret_transfer_code,
            "transfer_content": transfer_content,
        })
        if balance_used > 0:
            db_update_balance(user.id, user_balance - balance_used, reason=f"Partial balance: {order_code}")
            await save_data(tables=[PENDING_ORDERS_FILE, USERS_FILE])
        else:
            await save_data(tables=[PENDING_ORDERS_FILE])
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        await release_reserved_order_code(order_code)
        logger.error(f"Lỗi khi gửi mã QR cho user {user.id}: {e}")
        await context.bot.send_message(user.id, "Đã có lỗi xảy ra khi tạo mã QR. Vui lòng thử lại sau.")


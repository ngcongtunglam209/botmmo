async def listproducts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Xem danh sách tất cả sản phẩm với thông tin chi tiết
    """
    visible_products = {
        prod_id: p
        for prod_id, p in products.items()
        if not (isinstance(p, dict) and p.get("is_social_source_service"))
    }

    if not visible_products:
        await update.message.reply_text("<tg-emoji emoji-id=\"5854908544712707500\">📭</tg-emoji> Chưa có sản phẩm nào trong hệ thống.\n\nDùng /newproduct để tạo mới.")
        return
    
    # Phân loại products
    auto_products = {}
    manual_products = {}
    
    for prod_id, p in visible_products.items():
        if p.get('requires_gmail', False):
            manual_products[prod_id] = p
        else:
            auto_products[prod_id] = p
    
    msg = f"<b><tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> DANH SÁCH SẢN PHẨM ({len(visible_products)})</b>\n\n"
    
    # AUTO PRODUCTS (Có stock)
    if auto_products:
        msg += "<b><tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> SẢN PHẨM TỰ ĐỘNG (Có kho hàng):</b>\n\n"
        for prod_id, p in auto_products.items():
            stock = len(p.get('stock', []))
            status_icon = "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>" if stock > 0 else "❌"
            
            prod_info = (
                f"{status_icon} <b>{p['name']}</b>\n"
                f"   <tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <code>{prod_id}</code>\n"
                f"   <tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {p['price']:,}đ | <tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {p.get('duration', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> Tồn kho: {stock}\n\n"
            )
            if len(msg) + len(prod_info) > 3500:
                await update.message.reply_html(msg)
                msg = ""
            msg += prod_info
    
    # MANUAL PRODUCTS (Không cần stock)
    if manual_products:
        msg += "<b><tg-emoji emoji-id=\"5350778980158956492\">👨</tg-emoji>‍<tg-emoji emoji-id=\"5854908544712707500\">💼</tg-emoji> SẢN PHẨM THỦ CÔNG (Admin xử lý):</b>\n\n"
        for prod_id, p in manual_products.items():
            prod_info = (
                f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>{p['name']}</b>\n"
                f"   <tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <code>{prod_id}</code>\n"
                f"   <tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {p['price']:,}đ | <tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {p.get('duration', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> BH: {p.get('warranty', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"5462956611033117422\">⚙️</tg-emoji> Xử lý manual khi có đơn\n\n"
            )
            if len(msg) + len(prod_info) > 3500:
                await update.message.reply_html(msg)
                msg = ""
            msg += prod_info
    
    msg += "\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Lệnh:</b>\n"
    msg += "• /addstock - Thêm kho (chỉ SP tự động)\n"
    msg += "• /pending - Xem đơn manual chờ xử lý\n"
    msg += "• /delproduct [id] - Xóa sản phẩm"
    
    if msg.strip():
        await update.message.reply_html(msg)

async def kholink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with global_stock_lock:
        if not available_links: 
            await update.message.reply_text("<tg-emoji emoji-id=\"5854908544712707500\">📭</tg-emoji> Kho link hiện đang trống.")
        else: 
            await update.message.reply_html(f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>LINK MỜI ĐANG SỬ DỤNG (DÙNG LẠI):</b>\n\n<code>{next(iter(available_links))}</code>")

async def addlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Cú pháp: /addlink <link_mới>"); return
    
    # CHẾ ĐỘ 1 LINK DUY NHẤT (THEO YÊU CẦU MỚI)
    new_link = context.args[0]
    async with global_stock_lock:
        available_links.clear() # Xoá link cũ
        available_links.add(new_link) # Thêm link mới
    
    await save_data()
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ CẬP NHẬT LINK GỐC!</b>\n\n"
        f"<tg-emoji emoji-id=\"5231489647946768652\">🔗</tg-emoji> <b>Link mới:</b> <code>{new_link}</code>\n"
        f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> <i>Link này sẽ được bán cho tất cả đơn hàng cho đến khi bạn thay đổi.</i>"
    )

async def removelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cleared = False
    async with global_stock_lock:
        if available_links: 
            available_links.clear()
            cleared = True
    if cleared:
        await save_data()
        await update.message.reply_text("<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> Đã xóa link mời khỏi kho.")
    else: 
        await update.message.reply_text("Kho đã trống sẵn rồi.")

async def guilink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2: await update.message.reply_text("Cú pháp: /guilink <email> <link>"); return
    email_to_find, link_to_send = context.args[0].lower(), context.args[1]
    order_found = next((o for o in reversed(order_history) if o["email"] == email_to_find and "Chờ link" in status_text(o.get("status"))), None)
    if order_found:
        try:
            # FIX 3.4: Use .value to store string instead of Enum object
            order_found.update({"link": link_to_send, "status": OrderStatus.COMPLETED_RESENT.value}); await save_data()
            full_name = order_found.get("full_name", "bạn")
            await context.bot.send_message(order_found["user_id"], "<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>Admin đã gửi link kích hoạt cho bạn!</b>\nVui lòng kiểm tra email.", parse_mode=ParseMode.HTML, reply_markup=create_success_menu())
            email_sent, email_error = await send_activation_email(email_to_find, "[Từ Admin] Link kích hoạt iCloud", full_name, link_to_send)
            if email_sent:
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi link thủ công thành công cho: {email_to_find}.")
            else:
                await update.message.reply_text(
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đã cập nhật đơn nhưng gửi email thủ công thất bại cho {email_to_find}.\n"
                    f"Lỗi: {email_error}"
                )
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"Lỗi khi gửi link thủ công: {e}"); await update.message.reply_text("❌ Gửi link thất bại! Vui lòng kiểm tra logs.")
    else: await update.message.reply_text("<tg-emoji emoji-id=\"5429571366384842791\">🔎</tg-emoji> Không tìm thấy đơn hàng nào đang 'Chờ link' với email này.")

async def rewardtop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("<tg-emoji emoji-id=\"5429571366384842791\">🔎</tg-emoji> Bắt đầu tìm và tặng thưởng...")
    completed_orders = [o for o in order_history if is_completed_order(o)]
    if not completed_orders: await context.bot.send_message(update.effective_chat.id, "Chưa có đơn hàng hoàn tất để xếp hạng."); return
    eligible_user_ids = [
        resolved_uid for resolved_uid in (_api_get_effective_order_user_id(order) for order in completed_orders)
        if resolved_uid
    ]
    user_purchase_counts = Counter(eligible_user_ids)
    top_users = user_purchase_counts.most_common(2)
    admin_feedback = "⭐️ <b>KẾT QUẢ TẶNG THƯỞNG KHÁCH HÀNG THÂN THIẾT</b> ⭐️\n\n"; discount_amount = int(ICLOUD_PACKAGE_PRICE * 0.3)
    for user_id, purchase_count in top_users:
        user_info = user_data_db.get(str(user_id), {}); user_mention = user_info.get("first_name", f"ID {user_id}")
        coupon_code = f"VIP30-{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
        expires_str = (datetime.now() + timedelta(days=30)).strftime('%d-%m-%Y')
        coupons[coupon_code] = {"discount": discount_amount, "quantity": 1, "expires": expires_str, "used": 0}
        reward_message = (f"<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>CHÚC MỪNG KHÁCH HÀNG THÂN THIẾT</b> <tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>\n\nCảm ơn bạn đã ủng hộ Lâm Shop!\n" f"Chúng tôi xin gửi tặng bạn mã giảm giá <b>30%</b> cho lần mua tiếp theo: <code>{coupon_code}</code>\n" f"<i>(Mã dùng 1 lần, hết hạn ngày {expires_str})</i>")
        try: await context.bot.send_message(user_id, reward_message, parse_mode=ParseMode.HTML); admin_feedback += f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi coupon <code>{coupon_code}</code> cho {user_mention} ({purchase_count} đơn).\n"
        except (TelegramError, ValueError, KeyError, AttributeError) as e: admin_feedback += f"❌ Lỗi khi gửi coupon cho {user_mention}: {e}\n"
    await save_data(); await context.bot.send_message(update.effective_chat.id, admin_feedback, parse_mode=ParseMode.HTML)

async def addcoupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 4: 
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Sai cú pháp!</b>\n\n"
            "Sử dụng: <code>/addcoupon <MÃ> <LƯỢNG> <TIỀN> <SỐ_NGÀY></code>\n"
            "Ví dụ: <code>/addcoupon TET2025 100 35000 30</code>"
        )
        return

    code, quantity_str, amount_str, days_str = context.args
    
    try: 
        quantity = int(quantity_str)
        discount = int(amount_str)
        days = int(days_str)
        
        if quantity < 0 or discount < 0 or days < 0:
             await update.message.reply_text("❌ Lượng, tiền và ngày phải là số dương.")
             return
             
    except ValueError: 
        await update.message.reply_text("❌ Lỗi định dạng số. Vui lòng kiểm tra lại.")
        return

    expires_str = (datetime.now() + timedelta(days=days)).strftime('%d-%m-%Y')
    
    # Đảm bảo biến coupons là dict
    global coupons
    if not isinstance(coupons, dict):
        coupons = {}

    coupons[code.upper()] = {
        "discount": discount, 
        "quantity": quantity, 
        "expires": expires_str, 
        "used": 0
    }
    
    await save_data(force=True)
    
    # Escape HTML để tránh lỗi
    safe_code = code.upper().replace("<", "&lt;").replace(">", "&gt;")
    
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ THÊM MÃ GIẢM GIÁ</b>\n\n"
        f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> Mã: <b>{safe_code}</b>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Giảm: <b>{discount:,} VNĐ</b>\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Số lượng: <b>{quantity}</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Hết hạn: <b>{expires_str}</b>"
    )

async def delcoupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("Cú pháp: /delcoupon <TÊN_MÃ>"); return
    code = context.args[0].upper()
    if code in coupons: coupons.pop(code, None); await save_data(); await update.message.reply_html(f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> Đã xóa coupon <b>{code}</b>.")
    else: await update.message.reply_text("❌ Không tìm thấy coupon này.")

async def listcoupons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not coupons: await update.message.reply_text("Hiện không có mã giảm giá nào."); return
    message = "<b><tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> DANH SÁCH MÃ GIẢM GIÁ <tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji></b>\n\n";
    for code, details in coupons.items(): message += (f"- <code>{code}</code> | Giảm: <b>{details.get('discount', 0):,}đ</b>\n" f"  Đã dùng: <b>{details.get('used', 0)}/{details.get('quantity', '∞')}</b> | Hết hạn: <b>{details.get('expires', 'N/A')}</b>\n")
    await update.message.reply_html(message)



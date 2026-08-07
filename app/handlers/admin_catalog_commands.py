async def listproducts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    NEW: Xem danh sÃ¡ch táº¥t cáº£ sáº£n pháº©m vá»›i thÃ´ng tin chi tiáº¿t
    """
    visible_products = {
        prod_id: p
        for prod_id, p in products.items()
        if not (isinstance(p, dict) and p.get("is_social_source_service"))
    }

    if not visible_products:
        await update.message.reply_text("<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“­</tg-emoji> ChÆ°a cÃ³ sáº£n pháº©m nÃ o trong há»‡ thá»‘ng.\n\nDÃ¹ng /newproduct Ä‘á»ƒ táº¡o má»›i.")
        return
    
    # PhÃ¢n loáº¡i products
    auto_products = {}
    manual_products = {}
    
    for prod_id, p in visible_products.items():
        if p.get('requires_gmail', False):
            manual_products[prod_id] = p
        else:
            auto_products[prod_id] = p
    
    msg = f"<b><tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> DANH SÃCH Sáº¢N PHáº¨M ({len(visible_products)})</b>\n\n"
    
    # AUTO PRODUCTS (CÃ³ stock)
    if auto_products:
        msg += "<b><tg-emoji emoji-id=\"6271362510901747485\">ðŸ¤–</tg-emoji> Sáº¢N PHáº¨M Tá»° Äá»˜NG (CÃ³ kho hÃ ng):</b>\n\n"
        for prod_id, p in auto_products.items():
            stock = len(p.get('stock', []))
            status_icon = "<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji>" if stock > 0 else "âŒ"
            
            prod_info = (
                f"{status_icon} <b>{p['name']}</b>\n"
                f"   <tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> <code>{prod_id}</code>\n"
                f"   <tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> {p['price']:,}Ä‘ | <tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> {p.get('duration', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"6059654836918423763\">ðŸ“Š</tg-emoji> Tá»“n kho: {stock}\n\n"
            )
            if len(msg) + len(prod_info) > 3500:
                await update.message.reply_html(msg)
                msg = ""
            msg += prod_info
    
    # MANUAL PRODUCTS (KhÃ´ng cáº§n stock)
    if manual_products:
        msg += "<b><tg-emoji emoji-id=\"5350778980158956492\">ðŸ‘¨</tg-emoji>â€<tg-emoji emoji-id=\"5854908544712707500\">ðŸ’¼</tg-emoji> Sáº¢N PHáº¨M THá»¦ CÃ”NG (Admin xá»­ lÃ½):</b>\n\n"
        for prod_id, p in manual_products.items():
            prod_info = (
                f"<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> <b>{p['name']}</b>\n"
                f"   <tg-emoji emoji-id=\"5334890573281114250\">ðŸ†”</tg-emoji> <code>{prod_id}</code>\n"
                f"   <tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> {p['price']:,}Ä‘ | <tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> {p.get('duration', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> BH: {p.get('warranty', 'N/A')}\n"
                f"   <tg-emoji emoji-id=\"5462956611033117422\">âš™ï¸</tg-emoji> Xá»­ lÃ½ manual khi cÃ³ Ä‘Æ¡n\n\n"
            )
            if len(msg) + len(prod_info) > 3500:
                await update.message.reply_html(msg)
                msg = ""
            msg += prod_info
    
    msg += "\n<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> <b>Lá»‡nh:</b>\n"
    msg += "â€¢ /addstock - ThÃªm kho (chá»‰ SP tá»± Ä‘á»™ng)\n"
    msg += "â€¢ /pending - Xem Ä‘Æ¡n manual chá» xá»­ lÃ½\n"
    msg += "â€¢ /delproduct [id] - XÃ³a sáº£n pháº©m"
    
    if msg.strip():
        await update.message.reply_html(msg)

async def kholink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with global_stock_lock:
        if not available_links: 
            await update.message.reply_text("<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“­</tg-emoji> Kho link hiá»‡n Ä‘ang trá»‘ng.")
        else: 
            await update.message.reply_html(f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>LINK Má»œI ÄANG Sá»¬ Dá»¤NG (DÃ™NG Láº I):</b>\n\n<code>{next(iter(available_links))}</code>")

async def addlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("CÃº phÃ¡p: /addlink <link_má»›i>"); return
    
    # CHáº¾ Äá»˜ 1 LINK DUY NHáº¤T (THEO YÃŠU Cáº¦U Má»šI)
    new_link = context.args[0]
    async with global_stock_lock:
        available_links.clear() # XoÃ¡ link cÅ©
        available_links.add(new_link) # ThÃªm link má»›i
    
    await save_data()
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃƒ Cáº¬P NHáº¬T LINK Gá»C!</b>\n\n"
        f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸ”—</tg-emoji> <b>Link má»›i:</b> <code>{new_link}</code>\n"
        f"<tg-emoji emoji-id=\"6260059243605398502\">ðŸ“Œ</tg-emoji> <i>Link nÃ y sáº½ Ä‘Æ°á»£c bÃ¡n cho táº¥t cáº£ Ä‘Æ¡n hÃ ng cho Ä‘áº¿n khi báº¡n thay Ä‘á»•i.</i>"
    )

async def removelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cleared = False
    async with global_stock_lock:
        if available_links: 
            available_links.clear()
            cleared = True
    if cleared:
        await save_data()
        await update.message.reply_text("<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘ï¸</tg-emoji> ÄÃ£ xÃ³a link má»i khá»i kho.")
    else: 
        await update.message.reply_text("Kho Ä‘Ã£ trá»‘ng sáºµn rá»“i.")

async def guilink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2: await update.message.reply_text("CÃº phÃ¡p: /guilink <email> <link>"); return
    email_to_find, link_to_send = context.args[0].lower(), context.args[1]
    order_found = next((o for o in reversed(order_history) if o["email"] == email_to_find and "Chá» link" in status_text(o.get("status"))), None)
    if order_found:
        try:
            # FIX 3.4: Use .value to store string instead of Enum object
            order_found.update({"link": link_to_send, "status": OrderStatus.COMPLETED_RESENT.value}); await save_data()
            full_name = order_found.get("full_name", "báº¡n")
            await context.bot.send_message(order_found["user_id"], "<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> <b>Admin Ä‘Ã£ gá»­i link kÃ­ch hoáº¡t cho báº¡n!</b>\nVui lÃ²ng kiá»ƒm tra email.", parse_mode=ParseMode.HTML, reply_markup=create_success_menu())
            email_sent, email_error = await send_activation_email(email_to_find, "[Tá»« Admin] Link kÃ­ch hoáº¡t iCloud", full_name, link_to_send)
            if email_sent:
                await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ gá»­i link thá»§ cÃ´ng thÃ nh cÃ´ng cho: {email_to_find}.")
            else:
                await update.message.reply_text(
                    f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÃ£ cáº­p nháº­t Ä‘Æ¡n nhÆ°ng gá»­i email thá»§ cÃ´ng tháº¥t báº¡i cho {email_to_find}.\n"
                    f"Lá»—i: {email_error}"
                )
        except (TelegramError, ValueError, KeyError, AttributeError) as e: logger.error(f"Lá»—i khi gá»­i link thá»§ cÃ´ng: {e}"); await update.message.reply_text("âŒ Gá»­i link tháº¥t báº¡i! Vui lÃ²ng kiá»ƒm tra logs.")
    else: await update.message.reply_text("<tg-emoji emoji-id=\"5429571366384842791\">ðŸ”Ž</tg-emoji> KhÃ´ng tÃ¬m tháº¥y Ä‘Æ¡n hÃ ng nÃ o Ä‘ang 'Chá» link' vá»›i email nÃ y.")

async def rewardtop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("<tg-emoji emoji-id=\"5429571366384842791\">ðŸ”Ž</tg-emoji> Báº¯t Ä‘áº§u tÃ¬m vÃ  táº·ng thÆ°á»Ÿng...")
    completed_orders = [o for o in order_history if is_completed_order(o)]
    if not completed_orders: await context.bot.send_message(update.effective_chat.id, "ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng hoÃ n táº¥t Ä‘á»ƒ xáº¿p háº¡ng."); return
    eligible_user_ids = [
        resolved_uid for resolved_uid in (_api_get_effective_order_user_id(order) for order in completed_orders)
        if resolved_uid
    ]
    user_purchase_counts = Counter(eligible_user_ids)
    top_users = user_purchase_counts.most_common(2)
    admin_feedback = "â­ï¸ <b>Káº¾T QUáº¢ Táº¶NG THÆ¯á»žNG KHÃCH HÃ€NG THÃ‚N THIáº¾T</b> â­ï¸\n\n"; discount_amount = int(ICLOUD_PACKAGE_PRICE * 0.3)
    for user_id, purchase_count in top_users:
        user_info = user_data_db.get(str(user_id), {}); user_mention = user_info.get("first_name", f"ID {user_id}")
        coupon_code = f"VIP30-{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
        expires_str = (datetime.now() + timedelta(days=30)).strftime('%d-%m-%Y')
        coupons[coupon_code] = {"discount": discount_amount, "quantity": 1, "expires": expires_str, "used": 0}
        reward_message = (f"<tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji> <b>CHÃšC Má»ªNG KHÃCH HÃ€NG THÃ‚N THIáº¾T</b> <tg-emoji emoji-id=\"5449800250032143374\">ðŸŽ‰</tg-emoji>\n\nCáº£m Æ¡n báº¡n Ä‘Ã£ á»§ng há»™ DinoTools!\n" f"ChÃºng tÃ´i xin gá»­i táº·ng báº¡n mÃ£ giáº£m giÃ¡ <b>30%</b> cho láº§n mua tiáº¿p theo: <code>{coupon_code}</code>\n" f"<i>(MÃ£ dÃ¹ng 1 láº§n, háº¿t háº¡n ngÃ y {expires_str})</i>")
        try: await context.bot.send_message(user_id, reward_message, parse_mode=ParseMode.HTML); admin_feedback += f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ gá»­i coupon <code>{coupon_code}</code> cho {user_mention} ({purchase_count} Ä‘Æ¡n).\n"
        except (TelegramError, ValueError, KeyError, AttributeError) as e: admin_feedback += f"âŒ Lá»—i khi gá»­i coupon cho {user_mention}: {e}\n"
    await save_data(); await context.bot.send_message(update.effective_chat.id, admin_feedback, parse_mode=ParseMode.HTML)

async def addcoupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 4: 
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Sai cÃº phÃ¡p!</b>\n\n"
            "Sá»­ dá»¥ng: <code>/addcoupon <MÃƒ> <LÆ¯á»¢NG> <TIá»€N> <Sá»_NGÃ€Y></code>\n"
            "VÃ­ dá»¥: <code>/addcoupon TET2025 100 35000 30</code>"
        )
        return

    code, quantity_str, amount_str, days_str = context.args
    
    try: 
        quantity = int(quantity_str)
        discount = int(amount_str)
        days = int(days_str)
        
        if quantity < 0 or discount < 0 or days < 0:
             await update.message.reply_text("âŒ LÆ°á»£ng, tiá»n vÃ  ngÃ y pháº£i lÃ  sá»‘ dÆ°Æ¡ng.")
             return
             
    except ValueError: 
        await update.message.reply_text("âŒ Lá»—i Ä‘á»‹nh dáº¡ng sá»‘. Vui lÃ²ng kiá»ƒm tra láº¡i.")
        return

    expires_str = (datetime.now() + timedelta(days=days)).strftime('%d-%m-%Y')
    
    # Äáº£m báº£o biáº¿n coupons lÃ  dict
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
    
    # Escape HTML Ä‘á»ƒ trÃ¡nh lá»—i
    safe_code = code.upper().replace("<", "&lt;").replace(">", "&gt;")
    
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃƒ THÃŠM MÃƒ GIáº¢M GIÃ</b>\n\n"
        f"<tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji> MÃ£: <b>{safe_code}</b>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> Giáº£m: <b>{discount:,} VNÄ</b>\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> Sá»‘ lÆ°á»£ng: <b>{quantity}</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Háº¿t háº¡n: <b>{expires_str}</b>"
    )

async def delcoupon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args: await update.message.reply_text("CÃº phÃ¡p: /delcoupon <TÃŠN_MÃƒ>"); return
    code = context.args[0].upper()
    if code in coupons: coupons.pop(code, None); await save_data(); await update.message.reply_html(f"<tg-emoji emoji-id=\"5424857974784925603\">ðŸ—‘ï¸</tg-emoji> ÄÃ£ xÃ³a coupon <b>{code}</b>.")
    else: await update.message.reply_text("âŒ KhÃ´ng tÃ¬m tháº¥y coupon nÃ y.")

async def listcoupons_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not coupons: await update.message.reply_text("Hiá»‡n khÃ´ng cÃ³ mÃ£ giáº£m giÃ¡ nÃ o."); return
    message = "<b><tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji> DANH SÃCH MÃƒ GIáº¢M GIÃ <tg-emoji emoji-id=\"5377624166436445368\">ðŸŽŸï¸</tg-emoji></b>\n\n";
    for code, details in coupons.items(): message += (f"- <code>{code}</code> | Giáº£m: <b>{details.get('discount', 0):,}Ä‘</b>\n" f"  ÄÃ£ dÃ¹ng: <b>{details.get('used', 0)}/{details.get('quantity', 'âˆž')}</b> | Háº¿t háº¡n: <b>{details.get('expires', 'N/A')}</b>\n")
    await update.message.reply_html(message)



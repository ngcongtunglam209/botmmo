# ===================== FLASH SALE =====================
async def flashsale_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin flash sale management
    /flashsale <% giam> <so phut> [product_id hoac "all"]
    /flashsale list
    /flashsale stop <sale_id>
    """

    args = context.args

    if not args:
        await update.message.reply_html(
            "<b><tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> FLASH SALE</b>\n\n"
            "<b>Tạo Flash Sale:</b>\n"
            "<code>/flashsale [% giảm] [số phút] [product_id / all]</code>\n\n"
            "<b>Ví dụ:</b>\n"
            "<code>/flashsale 30 60 all</code> — Giảm 30% tất cả SP trong 60 phút\n"
            "<code>/flashsale 50 30 netflix_1</code> — Giảm 50% SP cụ thể trong 30 phút\n\n"
            "<b>Quản lý:</b>\n"
            "<code>/flashsale list</code> — Xem Flash Sale đang chạy\n"
            "<code>/flashsale stop [sale_id]</code> — Dừng Flash Sale"
        )
        return

    if args[0] == "list":
        now = time.time()
        active = {sid: s for sid, s in flash_sales.items() if s.get('active', True) and s['end_time'] > now}
        if not active:
            await update.message.reply_html("<b><tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> Không có Flash Sale nào đang chạy.</b>")
            return
        msg = "<b><tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> FLASH SALE ĐANG CHẠY:</b>\n\n"
        for sid, s in active.items():
            remaining = int(s['end_time'] - now)
            mins = remaining // 60
            product_text = "Tất cả SP" if s.get('all_products') else ", ".join(s.get('product_ids', []))
            msg += (
                f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <code>{sid}</code>\n"
                f"<tg-emoji emoji-id=\"6059654836918423763\">📉</tg-emoji> Giảm: <b>{s['discount_percent']}%</b>\n"
                f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {product_text}\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Còn: {mins} phút\n\n"
            )
        msg += "Dừng: <code>/flashsale stop [sale_id]</code>"
        await update.message.reply_html(msg)
        return

    if args[0] == "stop":
        if len(args) < 2:
            await update.message.reply_html("Cú pháp: <code>/flashsale stop [sale_id]</code>")
            return
        sale_id = args[1]
        if sale_id in flash_sales:
            flash_sales[sale_id]['active'] = False
            flash_sales[sale_id]['end_time'] = time.time()
            await save_data(tables=[FLASH_SALES_FILE])
            await update.message.reply_html(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã dừng Flash Sale <code>{sale_id}</code>")
        else:
            await update.message.reply_html(f"❌ Không tìm thấy Flash Sale <code>{sale_id}</code>")
        return

    if len(args) < 3:
        await update.message.reply_html("Cú pháp: <code>/flashsale [% giảm] [số phút] [product_id / all]</code>")
        return

    try:
        discount_pct = int(args[0])
        duration_mins = int(args[1])
        target = args[2]
    except ValueError:
        await update.message.reply_html("❌ % giảm và số phút phải là số nguyên!")
        return

    if not 1 <= discount_pct <= 90:
        await update.message.reply_html("❌ % giảm phải từ 1-90!")
        return
    if duration_mins < 1:
        await update.message.reply_html("❌ Thời gian phải ít nhất 1 phút!")
        return

    now = time.time()
    sale_id = f"FS{int(now)}"

    if target.lower() == "all":
        sale_data = {
            'discount_percent': discount_pct,
            'start_time': now,
            'end_time': now + duration_mins * 60,
            'all_products': True,
            'product_ids': [],
            'name': f"Flash Sale {discount_pct}%",
            'active': True
        }
        product_text = "TẤT CẢ sản phẩm"
    else:
        if target not in products:
            await update.message.reply_html(f"❌ Không tìm thấy sản phẩm <code>{target}</code>")
            return
        sale_data = {
            'discount_percent': discount_pct,
            'start_time': now,
            'end_time': now + duration_mins * 60,
            'all_products': False,
            'product_ids': [target],
            'name': f"Flash Sale {discount_pct}% - {products[target]['name']}",
            'active': True
        }
        product_text = products[target]['name']

    flash_sales[sale_id] = sale_data
    await save_data(tables=[FLASH_SALES_FILE])

    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> <b>FLASH SALE ĐÃ BẮT ĐẦU!</b>\n\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> ID: <code>{sale_id}</code>\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📉</tg-emoji> Giảm: <b>{discount_pct}%</b>\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Áp dụng: {product_text}\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Kéo dài: {duration_mins} phút\n\n"
        f"Dừng: <code>/flashsale stop {sale_id}</code>"
    )

    broadcast_msg = (
        f"<tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> <b>FLASH SALE - GIẢM {discount_pct}%!</b> <tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji>\n\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {product_text}\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Chỉ trong {duration_mins} phút!\n\n"
        f"<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Mua ngay: /start"
    )

    async def _flash_sale_broadcast(bot, msg, sale_id_bg):
        success_count = 0
        fail_count = 0
        blocked_ids = []
        for uid_str in list(user_data_db.keys()):
            try:
                uid = int(uid_str)
            except (ValueError, TypeError):
                continue
            if uid in banned_users:
                continue
            result = await broadcast_send_message(bot, uid, msg, parse_mode=ParseMode.HTML)
            if result == "ok":
                success_count += 1
            else:
                fail_count += 1
                if result in {"blocked", "invalid"}:
                    blocked_ids.append(uid_str)
            await asyncio.sleep(0.05)
        if blocked_ids:
            await _cleanup_blocked_users(blocked_ids)
        logger.info(
            f"Flash Sale {sale_id_bg}: broadcast to {success_count} users "
            f"({fail_count} that bai, {len(blocked_ids)} da chan/xoa)"
        )

    create_background_task(_flash_sale_broadcast(context.bot, broadcast_msg, sale_id))


async def cleanup_flash_sales_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-cleanup expired flash sales"""

    now = time.time()
    expired = [sid for sid, s in flash_sales.items() if s['end_time'] <= now and s.get('active', True)]
    if expired:
        for sid in expired:
            flash_sales[sid]['active'] = False
        await save_data(tables=[FLASH_SALES_FILE])
        logger.info(f"Flash Sale cleanup: deactivated {len(expired)} expired sales")


# ===================== COMBO / UPSELL =====================
async def combo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Admin combo management
    /combo create <prod_id1> <prod_id2> <discount%>
    /combo list
    /combo delete <combo_id>
    """

    args = context.args

    if not args:
        await update.message.reply_html(
            "<b><tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> COMBO DEALS</b>\n\n"
            "<b>Tạo Combo:</b>\n"
            "<code>/combo create [prod_id1] [prod_id2] [% giảm thêm]</code>\n\n"
            "<b>Ví dụ:</b>\n"
            "<code>/combo create netflix_1 spotify_1 15</code>\n\n"
            "<b>Quản lý:</b>\n"
            "<code>/combo list</code> — Xem combos\n"
            "<code>/combo delete [combo_id]</code> — Xóa combo"
        )
        return

    if args[0] == "list":
        if not combo_deals:
            await update.message.reply_html("<b><tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> Chưa có combo nào.</b>")
            return
        msg = "<b><tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> DANH SÁCH COMBO:</b>\n\n"
        for cid, c in combo_deals.items():
            p_names = []
            for pid in c.get('products', []):
                p = products.get(pid)
                p_names.append(p['name'] if p else pid)
            msg += f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <code>{cid}</code>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {' + '.join(p_names)}\n<tg-emoji emoji-id=\"6059654836918423763\">📉</tg-emoji> Giảm thêm: {c['discount_percent']}%\n\n"
        await update.message.reply_html(msg)
        return

    if args[0] == "delete":
        if len(args) < 2:
            await update.message.reply_html("Cú pháp: <code>/combo delete [combo_id]</code>")
            return
        cid = args[1]
        if cid in combo_deals:
            del combo_deals[cid]
            await save_data(tables=[COMBO_DEALS_FILE])
            await update.message.reply_html(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã xóa combo <code>{cid}</code>")
        else:
            await update.message.reply_html(f"❌ Không tìm thấy combo <code>{cid}</code>")
        return

    if args[0] == "create":
        if len(args) < 4:
            await update.message.reply_html("Cú pháp: <code>/combo create [prod_id1] [prod_id2] [% giảm]</code>")
            return
        pid1, pid2 = args[1], args[2]
        try:
            discount = int(args[3])
        except ValueError:
            await update.message.reply_html("❌ % giảm phải là số nguyên!")
            return

        if pid1 not in products or pid2 not in products:
            await update.message.reply_html("❌ Một trong hai sản phẩm không tồn tại!")
            return

        combo_id = f"COMBO{int(time.time())}"
        combo_deals[combo_id] = {
            'products': [pid1, pid2],
            'discount_percent': discount,
            'name': f"{products[pid1]['name']} + {products[pid2]['name']}"
        }
        await save_data(tables=[COMBO_DEALS_FILE])

        total = products[pid1]['price'] + products[pid2]['price']
        combo_price = int(total * (100 - discount) / 100)
        await update.message.reply_html(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ TẠO COMBO!</b>\n\n"
            f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> ID: <code>{combo_id}</code>\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {products[pid1]['name']} + {products[pid2]['name']}\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Giá gốc: {format_money(total)}\n"
            f"<tg-emoji emoji-id=\"6059654836918423763\">📉</tg-emoji> Giảm: {discount}%\n"
            f"<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> Giá combo: {format_money(combo_price)}"
        )
        return


async def send_upsell_suggestion(context, user_id: int, purchased_prod_id: str):
    """Send upsell suggestion after successful purchase"""
    try:
        upsell = get_upsell_products(purchased_prod_id, limit=2)
        if not upsell:
            return

        msg = lt(user_id, '<tg-emoji emoji-id="5226711870492126219">🎯</tg-emoji> <b>GỢI Ý CHO BẠN</b>\n\n', '<tg-emoji emoji-id="5226711870492126219">🎯</tg-emoji> <b>RECOMMENDED FOR YOU</b>\n\n', '<tg-emoji emoji-id="5226711870492126219">🎯</tg-emoji> <b>为您推荐</b>\n\n')
        btns = []
        for pid, p in upsell:
            price = p['price']
            flash_price, flash_info = get_flash_sale_price(pid, price)
            if flash_info:
                msg += f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>{html.escape(p["name"])}</b>\n<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <s>{format_money(price, user_id=user_id)}</s> → <b>{format_money(flash_price, user_id=user_id)}</b> <tg-emoji emoji-id="5303290914041505430">⚡</tg-emoji>\n\n'
            else:
                msg += f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>{html.escape(p["name"])}</b>\n<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>{format_money(price, user_id=user_id)}</b>\n\n'
            btns.append([InlineKeyboardButton(lt(user_id, "Mua {name}", "Buy {name}", "购买 {name}", name=p['name']), callback_data=f"view_prod_{pid}")])
        btns.append([InlineKeyboardButton(lt(user_id, "Menu chính", "Main Menu", "主菜单"), callback_data="back_to_main")])
        await context.bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.debug(f"Upsell suggestion error: {e}")


async def send_post_purchase_followups(context, user_id: int, purchased_prod_id: str, delay_seconds: float = 4.0):
    """Delay upsell/wheel follow-ups so the delivery file is easier to notice."""
    try:
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        await send_upsell_suggestion(context, user_id, purchased_prod_id)
        await asyncio.sleep(0.8)
        await context.bot.send_message(
            user_id,
            lt(user_id, '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> Bạn có <b>1 lượt quay</b> Vòng Quay May Mắn từ đơn hàng này! Bấm /wheel để quay.', '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> This order earned you <b>1 Lucky Wheel spin</b>! Use /wheel to spin.', '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> 此订单为您赢得 <b>1 次幸运转盘机会</b>！使用 /wheel 开始。'),
            parse_mode=ParseMode.HTML,
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.debug(f"Post-purchase follow-up error: {e}")


# ===================== LUCKY WHEEL =====================
async def wheel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Show wheel spin menu"""
    from app.services.games_withdrawals_db import check_if_banned
    if await check_if_banned(update): return
    user_id = update.effective_user.id
    user_orders = [o for o in order_history if o.get('user_id') == user_id and 'Hoàn thành' in status_text(o.get('status', ''))]
    if not user_orders:
        no_order_msg = lt(user_id, '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> <b>VÒNG QUAY MAY MẮN</b>\n\nBạn cần có <b>ít nhất 1 đơn hàng</b> thành công để chơi.\n\nHãy mua hàng để mở khóa!', '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> <b>LUCKY WHEEL</b>\n\nYou need <b>at least one completed order</b> to play.\n\nMake a purchase to unlock it!', '<tg-emoji emoji-id="5226711870492126219">🎡</tg-emoji> <b>幸运转盘</b>\n\n您需要<b>至少一个已完成订单</b>才能参与。\n\n购买商品即可解锁！')
        markup = InlineKeyboardMarkup([[_btn(lt(user_id, "Cửa hàng", "Store", "商店"), callback_data="store_main")], [_btn(lt(user_id, "Quay lại", "Back", "返回"), callback_data="back_to_main")]])
        if is_callback:
            try:
                await safe_edit_message(update.callback_query, text=no_order_msg, parse_mode=ParseMode.HTML, reply_markup=markup)
            except (TelegramError, ValueError, KeyError, AttributeError):
                await context.bot.send_message(chat_id=user_id, text=no_order_msg, parse_mode=ParseMode.HTML, reply_markup=markup)
        else:
            await update.message.reply_text(no_order_msg, parse_mode=ParseMode.HTML, reply_markup=markup)
        return
    wd = get_user_wheel_data(user_id)
    total_orders = len(user_orders)
    spins_used = wd.get('spins_used', 0)
    remaining_spins = max(0, total_orders - spins_used)
    total_won = wd.get('total_won', 0)
    msg = lt(
        user_id,
        '🎡 <b>VÒNG QUAY MAY MẮN</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>Giải thưởng:</b>\n💎 {p50} | 💵 {p20}\n🎁 Giảm 50% | 🎟 Giảm 20%\n💰 {p5} | 🎟 Giảm 10%\n🪙 {p2} | 😢 Chúc may mắn\n\n📦 Tổng đơn hàng: <b>{orders}</b>\n🎟 Lượt quay còn: <b>{spins}</b>\n💰 Tổng đã thắng: <b>{won}</b>\n\n<i>Mỗi đơn hàng = 1 lượt quay!</i>',
        '🎡 <b>LUCKY WHEEL</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>Prizes:</b>\n💎 {p50} | 💵 {p20}\n🎁 50% off | 🎟 20% off\n💰 {p5} | 🎟 10% off\n🪙 {p2} | 😢 Better luck next time\n\n📦 Total orders: <b>{orders}</b>\n🎟 Spins remaining: <b>{spins}</b>\n💰 Total won: <b>{won}</b>\n\n<i>Each order earns one spin!</i>',
        '🎡 <b>幸运转盘</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>奖品：</b>\n💎 {p50} | 💵 {p20}\n🎁 五折 | 🎟 八折\n💰 {p5} | 🎟 九折\n🪙 {p2} | 😢 祝下次好运\n\n📦 订单总数：<b>{orders}</b>\n🎟 剩余次数：<b>{spins}</b>\n💰 累计中奖：<b>{won}</b>\n\n<i>每个订单可获得一次机会！</i>',
        orders=total_orders,
        spins=remaining_spins,
        won=format_money(total_won, user_id=user_id),
        p50=format_money(50000, user_id=user_id),
        p20=format_money(20000, user_id=user_id),
        p5=format_money(5000, user_id=user_id),
        p2=format_money(2000, user_id=user_id),
    )
    btns = [[_btn(lt(user_id, "QUAY NGAY!", "SPIN NOW!", "立即转盘！"), callback_data="do_spin_wheel")]] if remaining_spins > 0 else [[_btn(lt(user_id, "Hết lượt — Mua thêm để quay!", "No spins — Buy to earn more!", "次数已用完 — 购买后再转！"), callback_data="store_main")]]
    btns.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), callback_data="back_to_main")])
    if is_callback:
        try:
            await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
        except (TelegramError, ValueError, KeyError, AttributeError):
            await context.bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))


async def handle_spin_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the actual wheel spin with animation"""

    query = update.callback_query
    user_id = update.effective_user.id
    user_orders = [o for o in order_history if o.get('user_id') == user_id and 'Hoàn thành' in status_text(o.get('status', ''))]
    if not user_orders:
        await safe_answer(query, lt(user_id, "Bạn cần ít nhất 1 đơn hàng để quay!", "You need at least one order to spin!", "您需要至少一个订单才能转盘！"), show_alert=True)
        return
    wd = get_user_wheel_data(user_id)
    total_orders = len(user_orders)
    spins_used = wd.get('spins_used', 0)
    remaining_spins = max(0, total_orders - spins_used)
    if remaining_spins <= 0:
        await safe_answer(query, lt(user_id, "Bạn đã hết lượt quay! Mua hàng để nhận thêm lượt.", "No spins left! Make a purchase to earn more.", "转盘次数已用完！购买商品可获得更多次数。"), show_alert=True)
        return
    now = time.time()
    wd['spins_used'] = spins_used + 1
    spin_emojis = ["🎡", "🎰", "🎲"]
    try:
        for emoji in spin_emojis:
            await safe_edit_message(query, text=f"{emoji} <b>{lt(user_id, 'Đang quay...', 'Spinning...', '转盘中...')}</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.7)
    except (TelegramError, ValueError, KeyError, AttributeError):
        logger.debug("Suppressed error while animating wheel spin")
    prize = spin_the_wheel()
    unlucky = lt(user_id, "Chúc bạn may mắn lần sau!", "Better luck next time!", "祝您下次好运！")
    reward_msg = ""
    if prize['type'] == 'balance':
        amount = prize['value']
        if not can_spend_promo(amount):
            prize = next((p for p in WHEEL_PRIZES if p['type'] == 'nothing'), prize)
            reward_msg = f"😢 {unlucky}"
            amount = 0
        else:
            user_info = db_get_user(user_id)
            if user_info:
                db_update_balance(user_id, user_info.get('balance', 0) + amount, reason=f"Lucky Wheel: +{amount}")
            wd['total_won'] = wd.get('total_won', 0) + amount
            record_promo_cost(amount, "wheel_balance")
            reward_msg = lt(user_id, "Bạn nhận được <b>{amount}</b> vào số dư!", "You received <b>{amount}</b> in your wallet!", "您的钱包已获得 <b>{amount}</b>！", amount=format_money(amount, user_id=user_id))
    elif prize['type'] == 'coupon':
        import random, string
        estimated_cost = int(35000 * prize['value'] / 100)
        if not can_spend_promo(estimated_cost):
            prize = next((p for p in WHEEL_PRIZES if p['type'] == 'nothing'), prize)
            reward_msg = f"😢 {unlucky}"
        else:
            record_promo_cost(estimated_cost, "wheel_coupon")
            coupon_code = f"SPIN{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
            coupons[coupon_code] = {'discount': prize['value'], 'quantity': 1, 'expires': (datetime.now() + timedelta(days=7)).strftime('%d-%m-%Y'), 'used': 0, 'is_percent': True}
            await save_data(tables=[COUPONS_FILE])
            reward_msg = lt(user_id, "Bạn nhận mã giảm <b>{value}%</b>!\nMã: <code>{code}</code>\n(Hết hạn sau 7 ngày)", "You won a <b>{value}% off</b> coupon!\nCode: <code>{code}</code>\n(Expires in 7 days)", "您获得 <b>{value}% 折扣</b>优惠码！\n代码：<code>{code}</code>\n（7 天后过期）", value=prize['value'], code=coupon_code)
    else:
        reward_msg = f"😢 {unlucky}"
    wd.setdefault('history', []).append({'prize': prize['name'], 'time': now})
    wd['history'] = wd['history'][-20:]
    wheel_data[str(user_id)] = wd
    await save_data(tables=[WHEEL_DATA_FILE])
    new_remaining = max(0, total_orders - wd.get('spins_used', 0))
    result_msg = lt(user_id, "🎡 <b>KẾT QUẢ VÒNG QUAY</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>{prize}</b>\n\n{reward}\n\n🎟 Lượt quay còn: {remaining}", "🎡 <b>LUCKY WHEEL RESULT</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>{prize}</b>\n\n{reward}\n\n🎟 Spins remaining: {remaining}", "🎡 <b>幸运转盘结果</b>\n━━━━━━━━━━━━━━━━━━\n\n🎁 <b>{prize}</b>\n\n{reward}\n\n🎟 剩余次数：{remaining}", prize=prize['name'], reward=reward_msg, remaining=new_remaining)
    btns = [[InlineKeyboardButton(lt(user_id, "Quay tiếp", "Spin Again", "继续转盘"), callback_data="lucky_wheel_menu")], [InlineKeyboardButton(lt(user_id, "Menu chính", "Main Menu", "主菜单"), callback_data="back_to_main")]]
    try:
        edited = await safe_edit_message(query, text=result_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
        if edited:
            return
    except (TelegramError, ValueError, KeyError, AttributeError):
        pass
    await context.bot.send_message(chat_id=user_id, text=result_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))


async def wheel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command handler for /wheel"""
    from app.services.games_withdrawals_db import check_if_banned
    if await check_if_banned(update): return
    await wheel_menu(update, context, is_callback=False)


async def testing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_USER_ID: return
    """
    [NEW] Auto-Testing Command for Admin
    Checks: AI, Database, Order System, Notifications
    """

    status_msg = await update.message.reply_text("<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>Đang chạy kiểm tra hệ thống...</b>\n\n<i>Vui lòng chờ 5-10 giây...</i>", parse_mode=ParseMode.HTML)

    results = []

    # 1. TEST DATABASE (Write/Read)
    try:
        test_key = "TEST_DB_KEY"
        user_data_db[test_key] = {"status": "ok", "time": time.time()}
        await save_data(force=True)
        if test_key in user_data_db:
            results.append("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Database:</b> Ghi/Đọc OK")
            del user_data_db[test_key] # Cleanup
            await save_data(force=True)
        else:
            results.append("❌ <b>Database:</b> Lỗi ghi dữ liệu")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        results.append(f"❌ <b>Database:</b> Exception ({str(e)})")

    # 2. TEST ORDER SYSTEM (Mock Order)
    try:
        test_code = "TEST-ORDER-123"
        mock_order = {
            "order_code": test_code,
            "user_id": ADMIN_USER_ID,
            "amount": 1000,
            "status": "TESTING",
            "timestamp": time.time()
        }
        db_add_order(mock_order)
        if order_index.get(test_code):
            results.append("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Order System:</b> Tạo đơn test OK")
            # Cleanup
            if test_code in order_index: del order_index[test_code]
            admin_uid = str(ADMIN_USER_ID)
            if admin_uid in user_order_index:
                user_order_index[admin_uid] = [o for o in user_order_index[admin_uid] if o.get("order_code") != test_code]
            # Sua tai cho: gan lai bien global chi doi ban ghi cua module nay, don
            # mock van con nguyen trong order_history that ma moi cho khac doc.
            order_history[:] = [o for o in order_history if o.get("order_code") != test_code]
        else:
            results.append("❌ <b>Order System:</b> Không tìm thấy đơn sau khi tạo")
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        results.append(f"❌ <b>Order System:</b> Exception ({str(e)})")

    # 3. TEST AI CONNECTION
    try:
        # Use a very short prompt to test connectivity
        ai_reply = await ask_ai("Chào, đây là test.", user_id=ADMIN_USER_ID)
        if ai_reply:
            results.append(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Gemini AI:</b> Phản hồi OK ({len(ai_reply)} chars)")
        else:
            results.append("❌ <b>Gemini AI:</b> Không có phản hồi")
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        results.append(f"❌ <b>Gemini AI:</b> Lỗi kết nối ({str(e)})")

    # 4. REPORT/NOTIFICATION
    results.append("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Notification:</b> Đã gửi test log này")

    # FINAL REPORT
    final_report = "<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>KẾT QUẢ KIỂM TRA HỆ THỐNG</b> <tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji>\n\n" + "\n".join(results)
    await context.bot.edit_message_text(chat_id=status_msg.chat_id, message_id=status_msg.message_id, text=final_report, parse_mode=ParseMode.HTML)



async def huongdan_baoloi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gửi hướng dẫn báo lỗi đơn hàng (Download ảnh để tránh lỗi region)"""
    if await check_if_banned(update): return
    user_id = update.effective_user.id
    caption = lt(
        user_id,
        '<tg-emoji emoji-id="5215392879320505675">🛠</tg-emoji> <b>HƯỚNG DẪN BÁO LỖI ĐƠN HÀNG</b>\n\n<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> <b>Bước 1:</b> Chọn /lichsu (Lịch sử đơn hàng).\n<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> <b>Bước 2:</b> Chọn đơn hàng gặp vấn đề.\n<tg-emoji emoji-id="5381879959335738545">3️⃣</tg-emoji> <b>Bước 3:</b> Bấm <b>\'Báo lỗi đơn này\'</b>.\n\n<tg-emoji emoji-id="6231107453178611892">📸</tg-emoji> <i>Xem ảnh để dễ hình dung hơn nhé!</i>',
        '<tg-emoji emoji-id="5215392879320505675">🛠</tg-emoji> <b>HOW TO REPORT AN ORDER ISSUE</b>\n\n<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> <b>Step 1:</b> Open /lichsu (Order History).\n<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> <b>Step 2:</b> Select the affected order.\n<tg-emoji emoji-id="5381879959335738545">3️⃣</tg-emoji> <b>Step 3:</b> Tap <b>\'Report this order\'</b>.\n\n<tg-emoji emoji-id="6231107453178611892">📸</tg-emoji> <i>See the image for a visual guide.</i>',
        '<tg-emoji emoji-id="5215392879320505675">🛠</tg-emoji> <b>订单问题报告指南</b>\n\n<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> <b>步骤 1：</b> 打开 /lichsu（订单历史）。\n<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> <b>步骤 2：</b> 选择有问题的订单。\n<tg-emoji emoji-id="5381879959335738545">3️⃣</tg-emoji> <b>步骤 3：</b> 点击<b>“报告此订单”</b>。\n\n<tg-emoji emoji-id="6231107453178611892">📸</tg-emoji> <i>请查看图片指南。</i>',
    )
    try:
        client = http_client if http_client else httpx.AsyncClient(timeout=10.0)
        response = await client.get(REPORT_INSTRUCTION_IMAGE_URL)
        photo_data = response.content if response.status_code == 200 else REPORT_INSTRUCTION_IMAGE_URL
        target_msg = update.callback_query.message if update.callback_query else update.message
        if update.callback_query:
            await safe_answer(update.callback_query)
        await target_msg.reply_photo(photo=photo_data, caption=caption, parse_mode=ParseMode.HTML)
        if not http_client and hasattr(client, 'aclose'):
            await client.aclose()
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error(f"Error sending guide photo: {e}")
        target_msg = update.callback_query.message if update.callback_query else update.message
        note = lt(user_id, "Ảnh không hiển thị được do lỗi mạng; vui lòng xem hướng dẫn chữ.", "The image could not load due to a network error; use the text guide.", "图片因网络错误无法加载；请查看文字指南。")
        await target_msg.reply_text(f'{caption}\n\n<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <i>{note}</i>', parse_mode=ParseMode.HTML)


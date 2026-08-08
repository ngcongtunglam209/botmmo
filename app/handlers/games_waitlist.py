# ==============================================================================
#  CÁC TRÌNH XỬ LÝ LỆNH VÀ TIN NHẮN
# ==============================================================================

# ==============================================================================
#  DICE GAME - GAME XÚC XẮC MAY MẮN
# ==============================================================================
DICE_COOLDOWN_SECONDS = 86400  # 24 giờ
DICE_PRIZE_MAX_PRICE = 20000   # Sản phẩm dưới 20k

async def dice_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> Game Xúc Xắc May Mắn
    - Quay 3 xúc xắc
    - Chỉ 111 hoặc 222 = CHIẾN THẮNG (nhận 1 sản phẩm miễn phí)
    - Cooldown: 24 giờ/lần chơi
    - Phần thưởng: Sản phẩm auto trong mức giá thưởng
    """
    if await check_if_banned(update):
        return
    
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    
    # 1. Check cooldown (24h)
    last_play = dice_game_data.get(str(user_id), 0)
    if time.time() - last_play < DICE_COOLDOWN_SECONDS:
        remaining = DICE_COOLDOWN_SECONDS - (time.time() - last_play)
        hours = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        await context.bot.send_message(
            chat_id,
            f"{E_LOADING} <b>CHƯA ĐẾN LƯỢT!</b>\n\n"
            f"Bạn cần chờ <b>{hours}h {mins}m</b> nữa mới được chơi tiếp!\n\n"
            f"{E_TIP} <i>Mỗi người chỉ được chơi 1 lần/24 giờ.</i>",
            parse_mode='HTML',
            reply_markup=create_back_button_menu(user_id=user_id)
        )
        return
    
    # 2. Update last play time TRƯỚC khi quay (tránh spam)
    dice_game_data[str(user_id)] = time.time()
    await save_data()
    
    # 3. Send intro message
    await context.bot.send_message(
        chat_id,
        "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>GAME XÚC XẮC MAY MẮN</b> <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji>\n\n"
        f"{E_TIP} <b>Luật chơi:</b> Chỉ ra 111 hoặc 222 mới THẮNG!\n"
        f"{E_TAG} <b>Phần thưởng:</b> 1 sản phẩm miễn phí\n"
        f"{E_TIP} <b>Tip:</b> Chỉ 111, 222 mới thắng\n\n"
        f"{E_LOADING} Đang quay xúc xắc...",
        parse_mode='HTML'
    )
    
    # 4. Roll 3 dice với delay animation
    results = []
    for i in range(3):
        dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji='<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji>')
        results.append(dice_msg.dice.value)
        await asyncio.sleep(3)  # Wait for dice animation (Telegram dice ~4s)
    
    # 5. Check win condition - hard lock: only 111/222 are winners
    result_tuple = tuple(results)
    is_win = result_tuple in WINNING_TRIPLES and is_dice_winning_combination(result_tuple)
    if len(set(results)) == 1 and not is_win:
        logger.warning(f"DICE non-winning triple blocked: user={user_id}, result={result_tuple}")
    
    if is_win and not can_spend_promo(DICE_PRIZE_MAX_PRICE):
        is_win = False
        logger.info(f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> DICE: Budget exceeded, blocking win for user {user_id}")
    result_str = f"{results[0]} - {results[1]} - {results[2]}"
    
    if is_win:
        # === CHIẾN THẮNG! ===
        context.user_data['dice_winner'] = True
        # FIX: Lưu winner vào persistent data (context.user_data bị mất khi restart)
        dice_game_data[f"winner_{user_id}"] = time.time()
        await save_data()
        
        # Lọc sản phẩm phù hợp theo DICE_PRIZE_MAX_PRICE
        available_prizes = []
        
        # Thêm các sản phẩm auto trong mức giá thưởng
        for pid, p in products.items():
            if not p.get('requires_gmail'):  # Chỉ auto products
                if p['price'] <= DICE_PRIZE_MAX_PRICE:  # Giá <= mức thưởng
                    stock = len(p.get('stock', []))
                    if stock > 0:  # Còn hàng
                        available_prizes.append({
                            'id': pid,
                            'name': f"{p['name']} ({p['price']:,}đ)",
                            'type': 'product'
                        })
        
        if not available_prizes:
            # Hết hàng - thông báo admin
            await context.bot.send_message(
                chat_id,
                f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result_str}</b>\n"
                f"{E_SUCCESS} {E_SUCCESS} <b>CHIẾN THẮNG!!!</b> {E_SUCCESS} {E_SUCCESS}\n\n"
                f"<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Rất tiếc, kho đang hết hàng phù hợp.\n"
                f"Admin sẽ liên hệ bạn để gửi phần thưởng!",
                parse_mode='HTML',
                reply_markup=create_back_button_menu(user_id=user_id)
            )
            # Notify admin
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>DICE WINNER - CẦN XỬ LÝ THỦ CÔNG</b>\n\n"
                f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>User:</b> {format_user_name_html(user=user)} (ID: <code>{user_id}</code>)\n"
                f"<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> <b>Kết quả:</b> {result_str}\n"
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Lý do:</b> Kho hết hàng trong mức thưởng\n\n"
                f"Vui lòng liên hệ user để gửi thưởng!",
                parse_mode='HTML'
            )
            return
        
        # Build prize selection keyboard
        keyboard = []
        for prize in available_prizes[:5]:  # Max 5 options
            btn_text = f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> {prize['name']}"
            callback = f"dice_prize_{prize['type']}_{prize['id']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])
        
        keyboard.append([_btn(lt(user_id, "Không nhận (Bỏ qua)", "Skip the prize", "放弃奖励"), icon_id="6147646987257782307", callback_data="dice_skip")])
        
        await context.bot.send_message(
            chat_id,
            f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result_str}</b>\n"
            f"{E_SUCCESS} {E_SUCCESS} <b>CHIẾN THẮNG!!!</b> {E_SUCCESS} {E_SUCCESS}\n\n"
            f"Chúc mừng bạn! Bạn được nhận <b>1 sản phẩm MIỄN PHÍ</b>!\n\n"
            f"{E_TIP} <b>Chọn phần thưởng của bạn:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Log win for admin
        logger.info(f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> DICE WIN: User {user_id} ({user.full_name}) - Result: {result_str}")
        
    else:
        # === THUA ===
        await context.bot.send_message(
            chat_id,
            f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result_str}</b>\n\n"
            f"<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Rất tiếc, bạn chưa thắng lần này!\n\n"
            f"{E_TIP} <b>Tip:</b> Chỉ 111 hoặc 222 mới thắng\n"
            f"{E_LOADING} Thử lại sau 24 giờ nhé!",
            reply_markup=create_back_button_menu(user_id=user_id),
            parse_mode='HTML'
        )


# ===================== STOCK WAITLIST =====================
async def handle_waitlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, prod_id: str):
    """Handle user clicking 'Notify when back in stock' button"""

    user_id = update.effective_user.id
    
    p = products.get(prod_id)
    if not p:
        await safe_answer(update.callback_query, "Sản phẩm không tồn tại", show_alert=True)
        return
    
    if prod_id not in stock_waitlist:
        stock_waitlist[prod_id] = []
    
    if user_id in stock_waitlist[prod_id]:
        await safe_answer(update.callback_query, "Bạn đã đăng ký nhận thông báo cho sản phẩm này rồi!", show_alert=True)
        return
    
    stock_waitlist[prod_id].append(user_id)
    await save_data(tables=[STOCK_WAITLIST_FILE])
    
    waitlist_count = len(stock_waitlist[prod_id])
    await safe_answer(update.callback_query, f"Đã đăng ký! Bạn sẽ được thông báo khi {p['name']} có hàng trở lại. ({waitlist_count} người đang chờ)", show_alert=True)


async def notify_waitlist_users(context, product_id: str, product_name: str, stock_count: int):
    """Notify waitlisted users when product is back in stock"""

    
    waitlist = stock_waitlist.get(product_id, [])
    if not waitlist:
        return 0
    
    message = (
        f"<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>SẢN PHẨM BẠN CHỜ ĐÃ CÓ HÀNG!</b>\n\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{html.escape(product_name)}</b>\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Số lượng:</b> {stock_count} sản phẩm\n\n"
        f"<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Mua ngay trước khi hết!</b> /start"
    )
    
    success = 0
    for user_id in list(waitlist):
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.05)
        except (TelegramError, ValueError, KeyError, AttributeError):
            logger.debug("Suppressed error at L7886")
    
    stock_waitlist[product_id] = []
    await save_data(tables=[STOCK_WAITLIST_FILE])
    logger.info(f"Waitlist: Notified {success}/{len(waitlist)} users for {product_name}")
    return success



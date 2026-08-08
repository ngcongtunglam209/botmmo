async def handle_games_callbacks(update, context, command):
    query = update.callback_query
    user_id = update.effective_user.id
    if command == 'games_menu':
        await safe_edit_message(
            query,
            text=t("games_title", user_id=user_id),
            parse_mode='HTML',
            reply_markup=create_games_menu(user_id=user_id),
        )
        return True
    elif command == 'play_dice_game':
        try:
            await query.message.delete()
        except (Forbidden, BadRequest) as e:
            logger.debug(f"Cannot delete callback message before dice game: {e}")
        # Call dice game function directly
        await dice_game_command(update, context)
        return True
    elif command.startswith('dice_prize_'):
        # Verify user actually won (anti-cheat) - check BOTH ephemeral AND persistent
        winner_key = f"winner_{user_id}"
        is_winner = context.user_data.get('dice_winner') or dice_game_data.get(winner_key)
        if not is_winner:
            try:
                await safe_answer(query, lt(user_id, "Bạn chưa thắng game!", "You have not won the game!", "您尚未赢得游戏！"), show_alert=True)
            except BadRequest:
                pass
            return
        parts = command.replace('dice_prize_', '').split('_', 1)
        if len(parts) < 2:
            await safe_answer(query, lt(user_id, "Lỗi dữ liệu!", "Invalid data!", "数据错误！"), show_alert=True)
            return
        prize_type, prize_id = parts[0], parts[1]
        user = update.effective_user
        try:
            if prize_type == 'product':
                p = products.get(prize_id)
                if not p:
                    await safe_answer(query, lt(user_id, "Sản phẩm không tồn tại!", "Product not found!", "商品不存在！"), show_alert=True)
                    return
                stock = p.get('stock', [])
                if not stock:
                    await safe_answer(query, lt(user_id, "Sản phẩm đã hết hàng!", "Product is out of stock!", "商品已售罄！"), show_alert=True)
                    return
                lock = await get_product_lock(prize_id)
                async with lock:
                    current_stock = products[prize_id].get('stock', [])
                    if not current_stock:
                        await safe_answer(query, lt(user_id, "Sản phẩm vừa hết hàng!", "The product just sold out!", "商品刚刚售罄！"), show_alert=True)
                        return
                    item = current_stock.pop(0)
                    products[prize_id]['stock'] = current_stock
                    await save_data(force=True)
                
                # Clear winner flag (both ephemeral and persistent)
                context.user_data.pop('dice_winner', None)
                dice_game_data.pop(f"winner_{user.id}", None)
                record_promo_cost(p.get('price', 0), 'dice_product')
                await save_data()
                
                order_code = f"DICE{int(time.time())}"
                item_raw = str(item)
                delivered_at = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                txt_content = (
                    "========================================\n"
                    "           DICE PRIZE DELIVERY\n"
                    "========================================\n\n"
                    f"Order Code : {order_code}\n"
                    f"Prize      : {p['name']}\n"
                    f"Delivered  : {delivered_at}\n\n"
                    "----------------------------------------\n"
                    "ACCOUNT INFO\n"
                    "----------------------------------------\n"
                    f"{item_raw}\n"
                )
                delivery_result = await deliver_items_as_txt(
                    context,
                    user.id,
                    order_code,
                    [item_raw],
                    file_content=txt_content,
                    file_prefix="DicePrize",
                    caption_html=lt(
                        user_id,
                        '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>CHÚC MỪNG!</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Phần thưởng:</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>Mã:</b> <code>{code}</code>',
                        '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>CONGRATULATIONS!</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Prize:</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>Code:</b> <code>{code}</code>',
                        '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>恭喜！</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>奖品：</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>编号：</b> <code>{code}</code>',
                        product=p['name'], code=order_code,
                    ),
                    reply_markup=create_back_button_menu(text=lt(user_id, "Quay lại", "Back", "返回"), user_id=user_id),
                )
                delivery_success = delivery_result.get("delivered")

                if not delivery_success:
                    # Keep record as pending manual delivery instead of false "delivered".
                    db_add_order({
                        "order_code": order_code,
                        "user_id": user.id,
                        "email": "N/A (Dice Prize)",
                        "amount": 0,
                        "status": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chờ gửi thủ công (Dice Game)",
                        "link": f"Dice Prize: {p['name']}",
                        "timestamp": time.time(),
                        "full_name": user.full_name,
                        "username": user.username,
                        "product_name": p['name'],
                        "quantity": 1,
                        "items": [str(item)],
                    })

                    try:
                        await query.edit_message_text(
                            lt(
                                user_id,
                                '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>Chưa thể gửi phần thưởng tự động</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Phần thưởng:</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>Mã xử lý:</b> <code>{code}</code>\n\nAdmin đã được báo và sẽ gửi thủ công cho bạn sớm nhất.',
                                '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>Automatic prize delivery failed</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Prize:</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>Reference:</b> <code>{code}</code>\n\nAdmin has been notified and will deliver it manually as soon as possible.',
                                '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>奖品自动发放失败</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>奖品：</b> {product}\n<tg-emoji emoji-id="5350481781306958339">🧾</tg-emoji> <b>处理编号：</b> <code>{code}</code>\n\n管理员已收到通知，将尽快手动发放。',
                                product=p['name'], code=order_code,
                            ), parse_mode='HTML',
                            reply_markup=create_back_button_menu(text=lt(user_id, "Quay lại", "Back", "返回"), user_id=user_id)
                        )
                    except BadRequest:
                        pass

                    await safe_send_admin(
                        context.bot,
                        f"<tg-emoji emoji-id=\"5447644880824181073\">🚨</tg-emoji> <b>DICE PRIZE DELIVERY FAILED</b>\n\n"
                        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>User:</b> {html.escape(user.full_name or 'N/A')} (<code>{user.id}</code>)\n"
                        f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Prize:</b> {html.escape(p['name'])}\n"
                        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Item:</b> <code>{html.escape(str(item))}</code>\n"
                        f"<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> <b>Mã:</b> <code>{order_code}</code>\n"
                        f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Fallback gửi:</b> {delivery_result.get('sent_items', 0)}/1\n"
                        f"❌ <b>Errors:</b> <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>\n\n"
                        f"Vui lòng gửi thủ công cho user.",
                    )

                    logger.warning(f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> DICE PRIZE delivery failed: user={user.id}, prize={p['name']}, order={order_code}")
                    return

                try:
                    await query.edit_message_text(
                        lt(
                            user_id,
                            '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>CHÚC MỪNG!</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Phần thưởng:</b> {product}\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <b>Thông tin tài khoản đã được gửi cho bạn.</b>',
                            '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>CONGRATULATIONS!</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Prize:</b> {product}\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <b>Your account details have been delivered.</b>',
                            '<tg-emoji emoji-id="5449800250032143374">🎉</tg-emoji> <b>恭喜！</b>\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>奖品：</b> {product}\n\n<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> <b>账户信息已发送给您。</b>',
                            product=p['name'],
                        ), parse_mode='HTML'
                    )
                except BadRequest as edit_err:
                    logger.debug(f"Dice prize success message edit skipped: {edit_err}")

                # Log order as completed only after successful delivery.
                db_add_order({
                    "order_code": order_code,
                    "user_id": user.id,
                    "email": "N/A (Dice Prize)",
                    "amount": 0,
                    "status": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Hoàn thành (Dice Game)",
                    "link": f"Dice Prize: {p['name']}",
                    "timestamp": time.time(),
                    "full_name": user.full_name,
                    "username": user.username,
                    "product_name": p['name'],
                    "quantity": 1,
                    "items": [str(item)],
                })

                await safe_send_admin(
                    context.bot,
                    f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>DICE PRIZE DELIVERED</b>\n\n"
                    f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>User:</b> {html.escape(user.full_name or 'N/A')} (<code>{user.id}</code>)\n"
                    f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Prize:</b> {html.escape(p['name'])}\n"
                    f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Item:</b> <code>{html.escape(str(item)[:50])}...</code>",
                )

                logger.info(f"<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> DICE PRIZE delivered: user={user.id}, prize={p['name']}, order={order_code}")
                
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Error delivering dice prize: {e}")
            try:
                await safe_answer(query, lt(user_id, "Lỗi giao phần thưởng: {error}", "Prize delivery error: {error}", "奖品发放错误：{error}", error=str(e)[:50]), show_alert=True)
            except BadRequest:
                pass
        return True
    elif command == 'dice_skip':
        context.user_data.pop('dice_winner', None)
        dice_game_data.pop(f"winner_{user_id}", None)
        try:
            await query.edit_message_text(
                lt(
                    user_id,
                    "❌ <b>Đã bỏ qua phần thưởng</b>\n\nBạn đã từ chối nhận phần thưởng.\nThử vận may lần sau nhé!",
                    "❌ <b>Prize skipped</b>\n\nYou declined the prize.\nGood luck next time!",
                    "❌ <b>已跳过奖品</b>\n\n您已放弃领取奖品。\n下次好运！",
                ), parse_mode='HTML',
                reply_markup=create_back_button_menu(text=lt(user_id, "Quay lại", "Back", "返回"), user_id=user_id)
            )
        except BadRequest:
            pass
        return True
    elif command == 'lucky_wheel_menu':
        await wheel_menu(update, context, is_callback=True)
        return True
    elif command == 'do_spin_wheel':
        await handle_spin_wheel(update, context)
        return True
    else:
        return False
    return True
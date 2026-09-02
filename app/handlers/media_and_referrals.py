async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_if_banned(update): return

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: SKIP channel posts/edited posts - context.user_data is None!
    if update.channel_post or update.edited_channel_post:
        return  # Ignore channel posts, chỉ xử lý user messages

    # <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> FIX: SKIP khi không có user_data (edge case)
    if context.user_data is None:
        return  # Không có user context, skip

    # Kiểm tra chế độ bảo trì
    if MAINTENANCE_MODE and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text(t("maintenance", user_id=update.effective_user.id), parse_mode=ParseMode.HTML)
        return

    user_state = context.user_data.get('state')

    if user_state == 'awaiting_report_photo':
        if not update.message or not update.message.photo:
             await update.message.reply_text(lt(update.effective_user.id, "❌ Vui lòng gửi ảnh hợp lệ.", "❌ Please send a valid photo.", "❌ 请发送有效的图片。"))
             return
        order_code = context.user_data.get('report_order_code')
        found_order = order_index.get(order_code) if order_code else None
        if found_order and found_order.get('refunded_at'):
            await update.message.reply_text(
                lt(
                    update.effective_user.id,
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa.",
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> This order was refunded, so it can no longer be reported.",
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 该订单已退款，无法再提交问题报告。",
                )
            )
            await clear_user_state(context)
            return
        if found_order and await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        photo_id = update.message.photo[-1].file_id
        try:
            # Validate file_id early to reduce Document_invalid at admin forwarding step.
            await context.bot.get_file(photo_id)
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"[REPORT] ảnh báo lỗi không hợp lệ ở bước nhận ({e})")
            await update.message.reply_text(
                lt(
                    update.effective_user.id,
                    "❌ Ảnh không hợp lệ. Vui lòng gửi lại ảnh dạng <b>Photo</b> (không phải file/document).",
                    "❌ That photo is not valid. Send it as a <b>Photo</b>, not as a file.",
                    "❌ 图片无效。请以<b>图片</b>形式发送，而不是文件。",
                ),
                parse_mode=ParseMode.HTML
            )
            return

        context.user_data['report_photo_id'] = photo_id
        context.user_data['report_photo_chat_id'] = update.message.chat_id
        context.user_data['report_photo_message_id'] = update.message.message_id
        context.user_data['state'] = 'awaiting_report_description'

        await update.message.reply_text(
            lt(
                update.effective_user.id,
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã nhận ảnh. Cuối cùng, vui lòng <b>mô tả ngắn gọn</b> vấn đề của bạn.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Photo received. Last step: <b>describe the problem briefly</b>.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> 已收到图片。最后请<b>简要描述问题</b>。",
            ),
            parse_mode=ParseMode.HTML,
        )

    elif user_state == 'awaiting_warranty_photo':
        order_code = context.user_data.get('warranty_claim_order')
        found_order = order_index.get(order_code) if order_code else None
        if found_order and await _auto_reject_expired_support_message(update.message, context, found_order, order_code):
            return
        photo_id = update.message.photo[-1].file_id
        desc = context.user_data.get('warranty_description', 'No description')

        # Save claim
        claim_id = f"CLM-{int(time.time())}"
        warranty_claims[claim_id] = {
            'user_id': update.effective_user.id,
            'order_code': order_code,
            'description': desc,
            'photo_id': photo_id,
            'status': 'pending',
            'timestamp': time.time()
        }
        await save_data()

        # Notify Admin
        admin_msg = (
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>YÊU CẦU BẢO HÀNH MỚI</b>\n"
            f"User: {format_user_mention_html(update.effective_user)}\n"
            f"Order: {order_code}\n"
            f"Lý do: {desc}"
        )
        btns = [
            [_btn("Duyệt", icon_id="5021905410089550576", callback_data=f"approve_warranty:{claim_id}")],
            [_btn("Từ chối", icon_id="6114086705512321034", callback_data=f"reject_warranty:{claim_id}")]
        ]
        try:
            await context.bot.send_photo(ADMIN_USER_ID, photo_id, caption=admin_msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Cannot notify admin about warranty claim {claim_id}: {e}")

        await update.message.reply_text(
            lt(
                update.effective_user.id,
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã gửi yêu cầu bảo hành. Admin sẽ xem xét sớm.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Your warranty request was sent. The admin will review it shortly.",
                "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> 保修申请已提交，管理员会尽快处理。",
            ),
            reply_markup=create_main_menu(user_id=update.effective_user.id),
        )
        await clear_user_state(context)

async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    if await check_if_banned(update): return
    user_id = update.effective_user.id
    stats = calculate_user_stats(user_id)
    badges = calculate_badges(user_id)
    rank_info = get_user_rank(user_id)
    current_rank = rank_info.get('rank') or {}
    next_rank = rank_info.get('next_rank')
    user_info = db_get_user(user_id)
    balance = user_info.get('balance', 0) if user_info else 0
    current_rank_name = format_rank_entry_premium(current_rank, user_id=user_id)
    next_rank_name = format_rank_entry_premium(next_rank, user_id=user_id) if next_rank else ""

    achievements_block = ""
    if badges:
        achievements_block = lt(
            user_id,
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Thành tựu</b>\n<blockquote>{badges}</blockquote>',
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>Achievements</b>\n<blockquote>{badges}</blockquote>',
            '\n\n<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> <b>成就</b>\n<blockquote>{badges}</blockquote>',
            badges="\n".join(f"• {badge}" for badge in badges),
        )

    rank_block = lt(
        user_id,
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Hạng VIP</b>\n<blockquote>• Hiện tại: <b>{rank}</b>\n',
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>VIP Rank</b>\n<blockquote>• Current: <b>{rank}</b>\n',
        '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>VIP 等级</b>\n<blockquote>• 当前：<b>{rank}</b>\n', rank=current_rank_name,
    )
    remaining = rank_info.get("remaining_to_next", 0)
    window_days = rank_info.get("window_days", 0)
    rank_block += lt(
        user_id,
        '• Chi tiêu {window} ngày qua: <b>{spent}</b>\n',
        '• Spent in last {window} days: <b>{spent}</b>\n',
        '• 近 {window} 天消费：<b>{spent}</b>\n',
        window=window_days, spent=format_money(rank_info.get("total_spent", 0), user_id),
    )
    if next_rank:
        rank_block += lt(
            user_id,
            '• Cần thêm <b>{amount}</b> để lên <b>{rank}</b>\n',
            '• Spend <b>{amount}</b> more to reach <b>{rank}</b>\n',
            '• 再消费 <b>{amount}</b> 即可升级至 <b>{rank}</b>\n',
            amount=format_money(remaining, user_id), rank=next_rank_name,
        )
    drop_timestamp = rank_info.get("drop_timestamp") or 0
    if drop_timestamp:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        drop_date = datetime.fromtimestamp(drop_timestamp, ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y")
        rank_block += lt(
            user_id,
            '• Không mua thêm thì <b>{date}</b> sẽ tuột hạng\n',
            '• Without a new order you drop a rank on <b>{date}</b>\n',
            '• 若不再下单，将于 <b>{date}</b> 掉级\n',
            date=drop_date,
        )
    rank_block += '</blockquote>'

    msg = lt(
        user_id,
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>THỐNG KÊ CÁ NHÂN</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>Tài khoản</b>\n<blockquote>• Tên: <b>{name}</b>\n• Số dư: <b>{balance}</b>\n• ID: <code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>Mua sắm</b>\n<blockquote>• Tổng chi tiêu: <b>{spent}</b>\n• Đơn hoàn thành: <b>{orders}</b>\n• Tiết kiệm mã giảm: <b>{saved}</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>Giới thiệu ({percent}% hoa hồng)</b>\n<blockquote>• Đã giới thiệu: <b>{refs}</b> người\n• Hoa hồng thực nhận: <b>{earned}</b></blockquote>{achievements}',
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>PERSONAL STATISTICS</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>Account</b>\n<blockquote>• Name: <b>{name}</b>\n• Balance: <b>{balance}</b>\n• ID: <code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>Purchases</b>\n<blockquote>• Total spent: <b>{spent}</b>\n• Completed orders: <b>{orders}</b>\n• Coupon savings: <b>{saved}</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>Referrals ({percent}% commission)</b>\n<blockquote>• Referred: <b>{refs}</b> people\n• Commission earned: <b>{earned}</b></blockquote>{achievements}',
        '<tg-emoji emoji-id="6059654836918423763">📊</tg-emoji> <b>个人统计</b>\n━━━━━━━━━━━━━━━━━━\n\n<tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> <b>账户</b>\n<blockquote>• 姓名：<b>{name}</b>\n• 余额：<b>{balance}</b>\n• ID：<code>{id}</code></blockquote>\n\n{rank}\n\n<tg-emoji emoji-id="5247134066322447995">🛒</tg-emoji> <b>购物</b>\n<blockquote>• 总消费：<b>{spent}</b>\n• 已完成订单：<b>{orders}</b>\n• 优惠码节省：<b>{saved}</b></blockquote>\n\n<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>推荐（{percent}% 佣金）</b>\n<blockquote>• 已推荐：<b>{refs}</b> 人\n• 已获佣金：<b>{earned}</b></blockquote>{achievements}',
        name=format_user_name_html(user=update.effective_user), balance=format_money(balance, user_id), id=user_id,
        spent=format_money(stats["total_spent"], user_id), orders=stats["order_count"], saved=format_money(stats["coupon_savings"], user_id),
        percent=REFERRAL_COMMISSION_PERCENT, refs=stats["referral_count"], earned=format_money(stats["commission_earned"], user_id),
        achievements=achievements_block, rank=rank_block,
    )
    btns = [
        [_btn(lt(user_id, "Nạp tiền vào ví", "Top up wallet", "钱包充值"), icon_id="5278467510604160626", callback_data='topup_start', style="primary")],
        [_btn(lt(user_id, "Link giới thiệu", "Referral Link", "推荐链接"), icon_id="5193085063998224234", callback_data='my_referral')],
    ]
    msg = upgrade_text_to_premium_emoji(msg)
    if is_callback:
        btns.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='back_to_main')])
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))


async def show_my_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.effective_user.id
    stats = calculate_user_stats(user_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    balance = user_data_db.get(str(user_id), {}).get('balance', 0)
    msg = lt(
        user_id,
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>CHƯƠNG TRÌNH ĐỐI TÁC MMO</b>\n━━━━━━━━━━━━━━━━━━\nGiới thiệu bạn bè để nhận <b>{percent}%</b> hoa hồng cho tất cả giao dịch của họ. Hoa hồng được cộng vào số dư để mua sản phẩm tại Lâm Shop.\n\n<b>Link Giới Thiệu Của Bạn:</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>Thống Kê Nhanh:</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> Đã mời: <b>{count}</b> người\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> Đã kiếm: <b>{earned}</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> Số dư mua hàng: <b>{balance}</b>\n',
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>MMO PARTNER PROGRAM</b>\n━━━━━━━━━━━━━━━━━━\nRefer friends and earn <b>{percent}%</b> commission on their transactions. Commission is added to your balance for purchases at Lâm Shop.\n\n<b>Your Referral Link:</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>Quick Stats:</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> Invited: <b>{count}</b> people\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> Earned: <b>{earned}</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> Purchase balance: <b>{balance}</b>\n',
        '<tg-emoji emoji-id="6293853394910057834">🤝</tg-emoji> <b>MMO 合作伙伴计划</b>\n━━━━━━━━━━━━━━━━━━\n邀请好友，获得其交易的 <b>{percent}%</b> 佣金。佣金将计入 Lâm Shop 的购物余额。\n\n<b>您的推荐链接：</b>\n<code>{link}</code>\n\n<tg-emoji emoji-id="5190806721286657692">📊</tg-emoji> <b>快速统计：</b>\n<tg-emoji emoji-id="5453957997418004470">👥</tg-emoji> 已邀请：<b>{count}</b> 人\n<tg-emoji emoji-id="5863724849851011383">💵</tg-emoji> 已赚取：<b>{earned}</b>\n<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji> 购物余额：<b>{balance}</b>\n',
        percent=REFERRAL_COMMISSION_PERCENT, link=ref_link, count=stats["referral_count"], earned=format_money(stats["commission_earned"], user_id), balance=format_money(balance, user_id),
    )
    keyboard = [[_btn(lt(user_id, "Top giới thiệu", "Top Referrers", "推荐排行"), icon_id="6129805886383723340", callback_data='top_referrers')]]
    if is_callback:
        keyboard.append([_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='back_to_main')])
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_top_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_id = update.effective_user.id
    top_list = get_top_referrers(limit=10)
    msg = lt(user_id, "⭐️ <b>TOP 10 NGƯỜI GIỚI THIỆU</b>\n\n", "⭐️ <b>TOP 10 REFERRERS</b>\n\n", "⭐️ <b>推荐排行榜前 10 名</b>\n\n")
    if not top_list:
        msg += lt(user_id, "<i>Chưa có dữ liệu</i>", "<i>No data yet</i>", "<i>暂无数据</i>")
    else:
        for item in top_list:
            rank = item['rank']
            medal = "⭐️" if rank <= 3 else f"{rank}."
            name = item['full_name'] if item.get('is_fake') else mask_name(item['full_name'])
            msg += f"{medal} <b>{name}</b>\n"
            msg += lt(user_id, '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} người · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission}\n\n', '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} people · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission}\n\n', '   <tg-emoji emoji-id="5350778980158956492">👥</tg-emoji> {count} 人 · <tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> {commission}\n\n', count=item['referral_count'], commission=format_money(item['total_commission'], user_id))
    btns = [[_btn(lt(user_id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data='my_referral')]]
    if is_callback:
        await safe_edit_message(update.callback_query, text=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

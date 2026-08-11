# ==============================================================================
async def create_ga_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    """Bắt đầu tạo Giveaway"""

    await update.message.reply_text(
        f"{E_SUCCESS} <b>TẠO SỰ KIỆN GIVEAWAY MỚI</b>\n\n"
        "<b>Bước 1/5:</b> Nhập <b>Mô tả sự kiện (Tiêu đề)</b>\n"
        "<i>VD: Tri ân khách hàng tháng 10</i>",
        parse_mode='HTML'
    )
    return GA_TITLE

async def receive_ga_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ga_title'] = update.message.text
    await update.message.reply_text(
        f"{E_TAG} <b>Bước 2/5:</b> Nhập <b>Số lượng giải</b> và <b>Tên phần thưởng</b>\n\n"
        "Dạng: <code>Số lượng - Tên phần thưởng</code>\n"
        "<i>VD: 5 - Tài khoản Netflix 1 tháng</i>",
        parse_mode='HTML'
    )
    return GA_PRIZE

async def receive_ga_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        if '-' not in text: raise ValueError
        qty_str, name = text.split('-', 1)
        qty = int(qty_str.strip())
        name = name.strip()
        context.user_data['ga_prize_qty'] = qty
        context.user_data['ga_prize_name'] = name
    except (TypeError, ValueError):
        await update.message.reply_text("❌ Sai cú pháp. Vui lòng nhập lại (VD: 5 - Netflix):")
        return GA_PRIZE

    # Create Mode Selection Keyboard
    keyboard = [
        [_btn("Random (Nút Bấm)", icon_id="6147646987257782307", callback_data="ga_mode_button")],
        [_btn("Dự Đoán (Comment)", icon_id="5443038326535759644", callback_data="ga_mode_comment")]
    ]
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã lưu giải thưởng.\n\n"
        "<b>Bước 3/6: Chọn loại Giveaway</b>\n"
        "• <b>Random (Nút Bấm):</b> User bấm nút tham gia, bot chọn ngẫu nhiên.\n"
        "• <b>Dự Đoán (Comment):</b> User bình luận kết quả, bot lọc comment đúng + nhanh nhất (VD: Tỉ số bóng đá).",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    return GA_MODE

async def receive_ga_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    mode = query.data.replace("ga_mode_", "")
    context.user_data['ga_mode'] = mode

    mode_text = "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> Random (Nút bấm)" if mode == "button" else "<tg-emoji emoji-id=\"5240228673738527951\">🔮</tg-emoji> Dự đoán (Comment)"

    await query.edit_message_text(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã chọn chế độ: <b>{mode_text}</b>\n\n"
        f"<b>Bước 4/6: Thời gian kết thúc?</b>\n"
        f"Nhập số phút (VD: 30) hoặc '0' để kết thúc thủ công.",
        parse_mode='HTML'
    )
    return GA_TIME

async def receive_ga_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    seconds = parse_ga_time(text)

    if seconds is None:
        await update.message.reply_text("❌ Định dạng thời gian không hợp lệ. Thử lại (VD: 30, 60, 1h).")
        return GA_TIME

    context.user_data['ga_seconds'] = seconds
    context.user_data['ga_duration_text'] = text

    await update.message.reply_text(
        "<tg-emoji emoji-id=\"6231107453178611892\">🖼️</tg-emoji> <b>Bước 5/6:</b> Gửi <b>Ảnh/Video banner</b> (hoặc gõ 'skip' để bỏ qua)\n\n"
        "<i>Sẽ hiển thị cùng bài post Giveaway</i>",
        parse_mode='HTML'
    )
    return GA_BANNER

async def receive_ga_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['ga_banner_id'] = update.message.photo[-1].file_id
        context.user_data['ga_banner_type'] = 'photo'
    elif update.message.video:
        context.user_data['ga_banner_id'] = update.message.video.file_id
        context.user_data['ga_banner_type'] = 'video'
    else:
        context.user_data['ga_banner_id'] = None
        context.user_data['ga_banner_type'] = None

    await update.message.reply_text(
        "<tg-emoji emoji-id=\"6129860303619363484\">📢</tg-emoji> <b>Bước 6/6:</b> Nhập <b>ID Kênh/Nhóm</b> để đăng (hoặc gõ 'me' để đăng tại đây)\n\n"
        "<i>VD: -100123456789 hoặc @channelname</i>\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Lưu ý: Bot phải là Admin trong kênh đó!",
        parse_mode='HTML'
    )
    return GA_CHANNEL

async def receive_ga_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.lower() == 'me':
        chat_id = update.effective_chat.id
    else:
        try:
            if text.startswith('@'):
                # Resolve username if needed, or usually bot api handles @username
                chat_id = text
            else:
                chat_id = int(text)
        except ValueError:
             await update.message.reply_text("❌ ID không hợp lệ. Vui lòng nhập lại số ID hoặc @username.")
             return GA_CHANNEL

    # FINAL: Post Giveaway
    try:
        ud = context.user_data
        mode = ud.get('ga_mode', 'button')
        end_time_ts = time.time() + ud['ga_seconds'] if ud['ga_seconds'] > 0 else 0
        end_str = datetime.fromtimestamp(end_time_ts).strftime('%H:%M %d/%m') if end_time_ts > 0 else "Khi Admin kết thúc"

        # Build Message
        msg_text = (
            f"{E_SUCCESS} <b>SỰ KIỆN GIVEAWAY: {ud['ga_title'].upper()}</b> {E_SUCCESS}\n\n"
            f"{E_TAG} <b>Phần thưởng:</b> {ud['ga_prize_qty']}x {ud['ga_prize_name']}\n"
            f"{E_LOADING} <b>Kết thúc:</b> {end_str}\n"
            f"{E_USER} <b>Người tham gia:</b> 0\n\n"
        )

        markup = None
        if mode == 'button':
            msg_text += "<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> <i>Bấm nút bên dưới để thử vận may!</i>"
            markup = InlineKeyboardMarkup([[_btn("THAM GIA NGAY", icon_id="5469744063815102906", callback_data="join_ga_action")]])
        else:
            msg_text += (
                "<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> <b>CÁCH THAM GIA:</b>\n"
                "• Reply (Trả lời) bài viết này với kết quả dự đoán (VD: 2-1).\n"
                "• <b>KHÔNG CHỈNH SỬA</b> (Sửa là bị loại).\n"
                "• Ai chính xác và nhanh nhất sẽ thắng!"
            )
            markup = None # No button for comment mode

        sent_msg = None
        if ud.get('ga_banner_id'):
            if ud['ga_banner_type'] == 'photo':
                sent_msg = await context.bot.send_photo(chat_id, ud['ga_banner_id'], caption=msg_text, parse_mode='HTML', reply_markup=markup)
            elif ud['ga_banner_type'] == 'video':
                sent_msg = await context.bot.send_video(chat_id, ud['ga_banner_id'], caption=msg_text, parse_mode='HTML', reply_markup=markup)
        else:
            sent_msg = await context.bot.send_message(chat_id, msg_text, parse_mode='HTML', reply_markup=markup)

        # Save to DB
        _ga_id = str(sent_msg.message_id)
        ga_key = f"{chat_id}_{sent_msg.message_id}"

        active_giveaways[ga_key] = {
            'title': ud['ga_title'],
            'prize_name': ud['ga_prize_name'],
            'prize_qty': ud['ga_prize_qty'],
            'start_time': time.time(),
            'end_time': end_time_ts,
            'channel_id': chat_id, # Can be int or str
            'message_id': sent_msg.message_id,
            'participants': [],
            'status': 'active',
            'mode': mode, # NEW
            'comments': [] # NEW: Store comments for prediction
        }
        await save_data()

        await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã đăng Giveaway ({mode}) thành công!\n<tg-emoji emoji-id=\"5231489647946768652\">🔗</tg-emoji> ID: {ga_key}")

    except Exception as e:
        logger.error(f"Lỗi khi đăng bài GA: {e}")
        await update.message.reply_text("❌ Lỗi khi đăng bài, vui lòng kiểm tra bot logs.")
        return ConversationHandler.END

    return ConversationHandler.END

async def list_ga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Liệt kê GA đang chạy"""
    if not active_giveaways:
        await update.message.reply_text("<tg-emoji emoji-id=\"5854908544712707500\">📭</tg-emoji> Không có Giveaway nào đang chạy.")
        return

    msg = "<b><tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> DANH SÁCH GIVEAWAY</b>\n\n"
    for ga_id, ga in active_giveaways.items():
        end_status = "Đang chạy" if ga.get('status') == 'active' else "Đã kết thúc"
        title = ga.get('title') or ga.get('desc') or "Giveaway"
        prize_name = ga.get('prize_name') or ga.get('prize') or "N/A"
        msg += (
            f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> <code>{ga_id}</code>\n"
            f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> {title} ({prize_name})\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👥</tg-emoji> Tham gia: {len(ga.get('participants', []))}\n"
            f"<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> Trạng thái: {end_status}\n\n"
        )
    await update.message.reply_html(msg)

async def endga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    """Kết thúc GA thủ công"""

    args = context.args
    ga_key = None

    # CASE 1: Reply to message (in Channel/Group or forwarded)
    if update.message.reply_to_message:
        # Construct key from current chat + replied message
        # Note: If admin replies in the channel, effective_chat is the channel.
        ga_key = f"{update.effective_chat.id}_{update.message.reply_to_message.message_id}"

    # CASE 2: Argument provided
    elif args:
        ga_key = args[0].strip()

    if not ga_key:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cách dùng:\n1. Reply vào tin nhắn Giveaway và gõ /endga\n2. Hoặc gõ /endga <GA_ID_CODE>")
        return

    # Check exact match first
    # If not found, try to assume user passed just message_id and try to find matching key
    if ga_key not in active_giveaways:
         # Try flexible search if argument is just digits (message_id)
         found = False
         for key in active_giveaways:
             if key.endswith(f"_{ga_key}"):
                 ga_key = key
                 found = True
                 break

         if not found:
            await update.message.reply_text("❌ Không tìm thấy Giveaway này (hoặc đã kết thúc).")
            return

    ga = active_giveaways[ga_key]
    if ga['status'] != 'active':
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Giveaway này đã kết thúc rồi.")
        return

    # NEW: Prediction Logic Check
    winning_result = None
    if ga.get('mode') == 'comment':
        # Result is required (e.g. /endga <ID> <RESULT>) or just reply with result
        # If replied, maybe the text of command contains result?
        # Let's simplify: /endga <ID> <RESULT> OR reply + /endga <RESULT>

        # Parse result from args
        # If accessed via reply: args[0] might be result
        # If accessed via arg: args[0] is ID, args[1] is result

        user_input_result = None
        if update.message.reply_to_message:
             if args: user_input_result = " ".join(args)
        else:
             if len(args) >= 2: user_input_result = " ".join(args[1:])

        if not user_input_result:
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> GA này là Dự Đoán. Cần nhập kết quả!\nVD: <code>/endga 2-1</code> (Reply) hoặc <code>/endga {ga_key} 2-1</code>", parse_mode='HTML')
            return

        winning_result = user_input_result.strip()

    await update.message.reply_text(f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang chốt thưởng cho GA: {ga['title']}...")
    await draw_ga_winners(context, ga_key, winning_result)

async def draw_ga_winners(context, ga_id, winning_result=None):
    """Chọn người thắng GA (Random hoặc Prediction)"""
    if ga_id not in active_giveaways: return
    ga = active_giveaways[ga_id]

    chat_id = ga.get('channel_id', ga.get('chat_id'))
    message_id = ga.get('message_id')
    qty = int(ga.get('prize_qty', ga.get('qty', 1)) or 1)
    prize = ga.get('prize_name', ga.get('prize', 'Món quà'))
    mode = ga.get('mode', 'button')
    if chat_id is None or message_id is None:
        logger.error(f"Giveaway data invalid for {ga_id}: missing chat_id/message_id")
        return

    winners_text = ""
    _winners = []

    if mode == 'comment' and winning_result:
        # --- PREDICTION LOGIC ---
        comments = ga.get('comments', [])
        valid_entries = []
        seen_users = set()

        target = winning_result.lower()

        # Filter entries
        for c in comments:
            if c['user_id'] in seen_users: continue # One entry per user? Or allow multiple? Let's take first valid per user?
            # Actually, normally allow spam but only earliest valid counts.
            # Let's simple: Filter correct first, then distinct users?
            # Better: if user spams 100 times, and 101st is correct, does it accept?
            # Standard prediction: One guess per user? Or free spam?
            # With "earliest wins", usually implies first correct guess.

            if c['edited']: continue # Disqualify edited

            if c['text'].lower() == target:
                valid_entries.append(c)
                seen_users.add(c['user_id'])

        # Sort by time (Earliest first)
        valid_entries.sort(key=lambda x: x['timestamp'])

        # Select Winners (Distinct users)
        final_winners = []
        final_users = set()
        for entry in valid_entries:
            if entry['user_id'] not in final_users:
                final_winners.append(entry)
                final_users.add(entry['user_id'])
                if len(final_winners) >= qty: break

        if not final_winners:
            winners_text = f"<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Không có ai đoán đúng kết quả: <b>{winning_result}</b>"
        else:
            winners_list_str = "\n".join([f"⭐️ {w['full_name']} (@{w.get('username','N/A')})" for w in final_winners])
            winners_text = (
                f"{E_SUCCESS} <b>KẾT QUẢ: {winning_result.upper()}</b>\n\n"
                f"Chúc mừng các nhà tiên tri nhanh nhất:\n"
                f"{winners_list_str}\n\n"
                f"{E_TAG} Phần thưởng: {prize}"
            )

    else:
        # --- RANDOM LOGIC ---
        participants = ga.get('participants', [])
        normalized_participants = []
        for participant in participants:
            pid = participant.get('id') if isinstance(participant, dict) else participant
            try:
                normalized_participants.append(int(pid))
            except (TypeError, ValueError):
                continue
        participants = list(dict.fromkeys(normalized_participants))
        ga['participants'] = participants

        if not participants:
            winners_text = "<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Không có người tham gia, GA bị hủy."
        else:
            # Pick unique winners
            unique_participants = participants

            if len(unique_participants) <= qty:
                chosen = unique_participants
            else:
                chosen = random.sample(unique_participants, qty)

            winners_list_str = []
            for uid in chosen:
                # Try fetch name
                try:
                    chat_member = await context.bot.get_chat_member(chat_id, uid)
                    name = chat_member.user.full_name
                    username = f"(@{chat_member.user.username})" if chat_member.user.username else ""
                    winners_list_str.append(f"<tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji> {name} {username}")
                except (ValueError, TypeError, KeyError, IndexError) as e:
                    logger.debug(f"Cannot resolve giveaway winner name for user {uid}: {e}")
                    winners_list_str.append(f"<tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji> User ID: {uid}")

            winners_text = (
                f"{E_SUCCESS} <b>KẾT QUẢ GIVEAWAY</b>\n\n"
                f"Chúc mừng {len(chosen)} người may mắn:\n"
                + "\n".join(winners_list_str) + "\n\n"
                f"{E_TAG} Phần thưởng: {prize}"
            )

    # 1. Update Post (Close GA)
    try:
        current_text = (
            f"<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> <b>GIVEAWAY ĐÃ KẾT THÚC</b> <tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji>\n\n"
            f"{E_TAG} <b>Phần thưởng:</b> {qty}x {prize}\n"
            f"⭐️ <b>Người thắng:</b> Xem bên dưới <tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji>"
        )
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=current_text,
            parse_mode='HTML',
            reply_markup=None # Remove buttons
            # Note: edit_message_caption might fail if original was text message not photo/video
            # Need check? No, button handler context implies message type somewhat?
            # Actually create_ga uses send_message OR send_photo.
            # edit_message_caption works for media messages. edit_message_text for text.
        )
    except BadRequest:
        # Try edit_message_text if caption fails
        try:
             await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=current_text,
                parse_mode='HTML',
                reply_markup=None
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.debug(f"Cannot edit giveaway post text: {e}")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error closing GA: {e}")

    # 2. Announce Winners (Reply to post)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=winners_text,
            reply_to_message_id=message_id,
            parse_mode='HTML'
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error announcing GA: {e}")

    # 3. Cleanup
    ga['status'] = 'ended'
    active_giveaways.pop(ga_id, None)
    try:
        os.remove("data_giveaways.json")
        await save_data() # Force save
    except OSError as e:
        logger.debug(f"Cannot remove data_giveaways.json during cleanup: {e}")


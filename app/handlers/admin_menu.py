def build_admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            _btn("Kho & Sản phẩm", icon_id="5854908544712707500", callback_data="adm:kho"),
            _btn("Đơn hàng & DT", icon_id="6271437775908639096", callback_data="adm:don"),
        ],
        [
            _btn("Người dùng", icon_id="5453957997418004470", callback_data="adm:users"),
            _btn("Marketing", icon_id="6143344362035090821", callback_data="adm:mk"),
        ],
        [
            _btn("API Partners", icon_id="5436359785534466562", callback_data="adm:api"),
        ],
        [
            _btn("Hệ thống & Tools", icon_id="5341715473882955310", callback_data="adm:sys"),
        ],
    ])

def build_admin_back_row() -> list:
    return [_btn("Quay lại", icon_id="6206032691075223572", callback_data="adm:home")]

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    text = (
        "<tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji> <b>BẢNG ĐIỀU KHIỂN ADMIN</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Chọn mục cần quản lý:"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=build_admin_main_menu())

async def handle_admin_menu_callback(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = query.data
    if not data.startswith("adm:"):
        return False

    action = data[4:]
    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await safe_answer(query, "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> Bạn không có quyền!", show_alert=True)
        return True

    await query.answer()

    async def _admin_edit(text: str, kb: InlineKeyboardMarkup) -> None:
        """Edit admin menu safely; fallback to new message if original cannot be edited."""
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except BadRequest as e:
            err = str(e).lower()
            if "message is not modified" in err:
                return
            if "there is no text in the message to edit" in err or "message can't be edited" in err:
                sent = await safe_send_message(
                    context,
                    query.message.chat_id,
                    text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
                if sent is not None:
                    try:
                        await query.message.delete()
                    except (Forbidden, BadRequest):
                        pass
                return
            raise

    if action == "home":
        text = (
            "<tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji> <b>BẢNG ĐIỀU KHIỂN ADMIN</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Chọn mục cần quản lý:"
        )
        await _admin_edit(text, build_admin_main_menu())
        return True

    if action == "kho":
        kb = InlineKeyboardMarkup([
            [_btn("DS sản phẩm", icon_id="5854908544712707500", callback_data="adm:x:products"),
             _btn("Xem kho Stock", icon_id="6271698656517165534", callback_data="adm:x:viewstock")],
            [_btn("Thêm SP mới", icon_id="5397916757333654639", callback_data="adm:h:newproduct"),
             _btn("Sửa sản phẩm", icon_id="5828072695694102691", callback_data="adm:h:editproduct")],
            [_btn("Thêm hàng vào kho", icon_id="5443127283898405358", callback_data="adm:h:addstock"),
             _btn("Giới hạn đơn chờ", icon_id="5212985021870123409", callback_data="adm:h:setlimit")],
            [_btn("Xóa sản phẩm", icon_id="6114086705512321034", callback_data="adm:h:delproduct")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>KHO & SẢN PHẨM</b>\nChọn thao tác:", kb)
        return True

    if action == "don":
        kb = InlineKeyboardMarkup([
            [_btn("Duyệt", icon_id="5021905410089550576", callback_data="adm:x:duyet"),
             _btn("Đơn manual chờ", icon_id="5215327832040811010", callback_data="adm:x:pending")],
            [_btn("Tìm đơn hàng", icon_id="5355252098403412825", callback_data="adm:h:find"),
             _btn("Hoàn tiền đơn", icon_id="6271636667254182477", callback_data="adm:h:refund")],
            [_btn("Xóa đơn stuck", icon_id="6183912183571682758", callback_data="adm:h:clearpending"),
             _btn("Báo cáo doanh thu", icon_id="5244837092042750681", callback_data="adm:x:doanhthu")],
            [_btn("Ngân sách KM", icon_id="5287231198098117669", callback_data="adm:x:promobudget"),
             _btn("Phân tích chi tiết", icon_id="5231200819986047254", callback_data="adm:x:analytics")],
            [_btn("Đổi email backup", icon_id="4967770306555937780", callback_data="adm:h:setemail")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>ĐƠN HÀNG & DOANH THU</b>\nChọn thao tác:", kb)
        return True

    if action == "users":
        kb = InlineKeyboardMarkup([
            [_btn("Danh sách user", icon_id="5256143829672672750", callback_data="adm:x:users"),
             _btn("Info chi tiết", icon_id="5309965701241379366", callback_data="adm:h:info")],
            [_btn("Cấm user", icon_id="5240241223632954241", callback_data="adm:h:ban", style="danger"),
             _btn("Mở cấm user", icon_id="5021905410089550576", callback_data="adm:h:unban", style="success")],
            [_btn("Cộng tiền user", icon_id="5397916757333654639", callback_data="adm:h:addmoney", style="success"),
             _btn("Trừ tiền user", icon_id="5406745771280187626", callback_data="adm:h:submoney", style="danger")],
            [_btn("Đơn rút tiền chờ", icon_id="5212985021870123409", callback_data="adm:x:pending_withdrawals"),
             _btn("DS chat hỗ trợ", icon_id="5443038326535759644", callback_data="adm:x:chats")],
            [_btn("Chat với user", icon_id="5443038326535759644", callback_data="adm:h:chat", style="primary"),
             _btn("Broadcast", icon_id="6143344362035090821", callback_data="adm:h:bc")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>QUẢN LÝ NGƯỜI DÙNG</b>\nChọn thao tác:", kb)
        return True

    if action == "mk":
        kb = InlineKeyboardMarkup([
            [_btn("Thêm coupon", icon_id="5377624166436445368", callback_data="adm:h:addcoupon")],
            [_btn("Xóa coupon", icon_id="5445267414562389170", callback_data="adm:h:delcoupon"),
             _btn("DS coupon", icon_id="5197269100878907942", callback_data="adm:x:listcoupons")],
            [_btn("Tạo Flash Sale", icon_id="5303290914041505430", callback_data="adm:h:flashsale"),
             _btn("DS Flash Sale", icon_id="5197269100878907942", callback_data="adm:h:flashsale_list")],
            [_btn("Dừng Flash Sale", icon_id="6271674836628541366", callback_data="adm:h:flashsale_stop"),
             _btn("Tạo Combo Deal", icon_id="5854908544712707500", callback_data="adm:h:combo_create")],
            [_btn("DS Combo", icon_id="5197269100878907942", callback_data="adm:h:combo_list"),
             _btn("Xóa Combo", icon_id="5445267414562389170", callback_data="adm:h:combo_delete")],
            [_btn("Thưởng top user", icon_id="6206032691075223572", callback_data="adm:x:rewardtop"),
             _btn("Tạo Giveaway", icon_id="5193209274452425995", callback_data="adm:h:create_ga")],
            [_btn("DS Giveaway", icon_id="5197269100878907942", callback_data="adm:x:list_ga"),
             _btn("Kết thúc GA", icon_id="6271674836628541366", callback_data="adm:h:end_ga")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5377624166436445368\">🎟</tg-emoji> <b>MARKETING & KHUYẾN MÃI</b>\nChọn thao tác:", kb)
        return True

    if action == "api":
        kb = InlineKeyboardMarkup([
            [_btn("API Partners", icon_id="5436359785534466562", callback_data="adm:x:api"),
             _btn("Thêm Partner", icon_id="5397916757333654639", callback_data="adm:h:addapi")],
            [_btn("Xóa Partner", icon_id="5445267414562389170", callback_data="adm:h:delapi"),
             _btn("Nạp tiền API", icon_id="5278467510604160626", callback_data="adm:h:napi")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>API PARTNERS</b>\nChọn thao tác:", kb)
        return True

    if action == "sys":
        _maintenance_icon = "<tg-emoji emoji-id=\"6269163801178804220\">🟢</tg-emoji>" if not MAINTENANCE_MODE else "<tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji>"
        _ai_icon = "<tg-emoji emoji-id=\"6269163801178804220\">🟢</tg-emoji>" if AI_AUTO_REPLY else "<tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji>"
        kb = InlineKeyboardMarkup([
            [_btn("Bảo trì ON/OFF", icon_id="5462921117423384478", callback_data="adm:h:baotri"),
             _btn("AI ON/OFF", icon_id="5287684458881756303", callback_data="adm:h:aimode")],
            [_btn("Test AI", icon_id="5443038326535759644", callback_data="adm:h:ask"),
             _btn("Backup thủ công", icon_id="5462956611033117422", callback_data="adm:x:backup")],
            [InlineKeyboardButton("<tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> Import dữ liệu", callback_data="adm:x:nhapdata"),
             _btn("Chế độ test", icon_id="5411512278740640309", callback_data="adm:x:testing")],
            [_btn("Thông báo hết hàng", icon_id="5458603043203327669", callback_data="adm:x:notify"),
             _btn("Reset thông báo", icon_id="5370715282044100355", callback_data="adm:x:resetnotify")],
            build_admin_back_row(),
        ])
        await _admin_edit("<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>HỆ THỐNG & TOOLS</b>\nChọn thao tác:", kb)
        return True

    if action.startswith("h:"):
        cmd = action[2:]
        hints = {
            "newproduct":     "<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> Thêm sản phẩm mới (Wizard):\n<code>/newproduct</code>",
            "editproduct":   "<tg-emoji emoji-id=\"5350752364246606166\">✏️</tg-emoji> Sửa sản phẩm:\n<code>/editproduct</code>",
            "addstock":       "<tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> Thêm hàng vào kho:\n<code>/addstock</code>",
            "setlimit":       "<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Giới hạn đơn chờ:\n<code>/setlimit [product_id] [số]</code>",
            "delproduct":     "❌ Xóa sản phẩm:\n<code>/delproduct [product_id]</code>",
            "find":           "<tg-emoji emoji-id=\"5429571366384842791\">🔍</tg-emoji> Tìm đơn hàng:\n<code>/find [mã_đơn]</code>",
            "refund":         "<tg-emoji emoji-id=\"5863724849851011383\">💸</tg-emoji> Hoàn tiền đơn:\n<code>/refund [mã_đơn]</code>",
            "clearpending":   "<tg-emoji emoji-id=\"5462956611033117422\">🧹</tg-emoji> Xóa đơn stuck:\n<code>/clearpending [mã/all]</code>",
            "setemail":       "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Đổi email backup:\n<code>/setemail [email]</code>",
            "info":           "ℹ️ Xem info user:\n<code>/info [user_id]</code>\nHoặc: <code>/info @username</code>",
            "ban":            "<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Cấm user:\n<code>/ban [user_id]</code>",
            "unban":          "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Mở cấm user:\n<code>/unban [user_id]</code>",
            "addmoney":       "<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> Cộng tiền user:\n<code>/addmoney [user_id] [số_tiền]</code>",
            "submoney":       "<tg-emoji emoji-id=\"5406745771280187626\">➖</tg-emoji> Trừ tiền user:\n<code>/submoney [user_id] [số_tiền]</code>",
            "chat":           "<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Chat với user:\n<code>/chat [user_id]</code>",
            "bc":             "<tg-emoji emoji-id=\"6129860303619363484\">📢</tg-emoji> Broadcast (Reply vào tin nhắn):\n<code>/bc</code>",
            "addcoupon":      "<tg-emoji emoji-id=\"5377624166436445368\">🎟</tg-emoji> Thêm coupon:\n<code>/addcoupon [Mã] [Sl] [Tiền] [Ngày]</code>",
            "delcoupon":      "<tg-emoji emoji-id=\"5424857974784925603\">🗑</tg-emoji> Xóa coupon:\n<code>/delcoupon [Mã]</code>",
            "flashsale":      "<tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> Tạo Flash Sale:\n<code>/flashsale [%_giảm] [số_phút] [product_id / all]</code>\n\nVí dụ:\n<code>/flashsale 30 60 all</code> — Giảm 30% tất cả trong 60 phút\n<code>/flashsale 50 30 netflix_1</code> — Giảm 50% SP cụ thể trong 30 phút",
            "flashsale_list": "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> Xem Flash Sale đang chạy:\n<code>/flashsale list</code>",
            "flashsale_stop": "<tg-emoji emoji-id=\"5447644880824181073\">⏹</tg-emoji> Dừng Flash Sale:\n<code>/flashsale stop [flash_sale_id]</code>",
            "combo_create":   "<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Tạo Combo Deal:\n<code>/combo create</code>",
            "combo_list":     "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> Xem Combo đang chạy:\n<code>/combo list</code>",
            "combo_delete":   "<tg-emoji emoji-id=\"5424857974784925603\">🗑</tg-emoji> Xóa Combo:\n<code>/combo delete [combo_id]</code>",
            "addapi":         "<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> Thêm Partner API:\n<code>/addapi [Tên_đối_tác]</code>",
            "delapi":         "<tg-emoji emoji-id=\"5424857974784925603\">🗑</tg-emoji> Xóa Partner:\n<code>/delapi [API_Key]</code>",
            "napi":           "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Nạp tiền API:\n<code>/napi [Key/Tên] [Số_tiền]</code>\nHoặc tạo QR:\n<code>/napi qr [Key/Tên] [Số_tiền]</code>",
            "create_ga":      "<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> Tạo Giveaway mới:\n<code>/create_ga</code>",
            "end_ga":         "<tg-emoji emoji-id=\"5424857974784925603\">🔚</tg-emoji> Kết thúc Giveaway:\n1. Reply vào tin nhắn GA và gõ <code>/endga</code>\n2. Hoặc: <code>/endga [GA_ID]</code>",
            "baotri":         "<tg-emoji emoji-id=\"5215392879320505675\">🛠</tg-emoji> Bật/Tắt bảo trì:\n<code>/baotri on</code> hoặc <code>/baotri off</code>",
            "aimode":         "<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Bật/Tắt AI reply:\n<code>/aimode on</code> hoặc <code>/aimode off</code>",
            "ask":            "<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Test AI assistant:\n<code>/ask [câu hỏi]</code>",
        }
        hint = hints.get(cmd, f"Dùng lệnh: <code>/{cmd}</code>")
        back_category = {
            "newproduct": "kho", "editproduct": "kho", "addstock": "kho",
            "find": "don", "refund": "don", "clearpending": "don", "setemail": "don",
            "info": "users", "ban": "users", "unban": "users", "addmoney": "users",
            "submoney": "users", "chat": "users", "bc": "users",
            "addcoupon": "mk", "delcoupon": "mk", "create_ga": "mk", "end_ga": "mk",
            "flashsale": "mk", "flashsale_list": "mk", "flashsale_stop": "mk",
            "combo_create": "mk", "combo_list": "mk", "combo_delete": "mk",
            "addapi": "api", "delapi": "api", "napi": "api",
            "baotri": "sys", "aimode": "sys", "ask": "sys",
        }
        cat = back_category.get(cmd, "home")
        kb = InlineKeyboardMarkup([
            [_btn("Quay lại", icon_id="6206032691075223572", callback_data=f"adm:{cat}")]
        ])
        await _admin_edit(f"<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>HƯỚNG DẪN SỬ DỤNG</b>\n\n{hint}", kb)
        return True

    if action.startswith("x:"):
        cmd = action[2:]
        if cmd == "nhapdata":
            kb = InlineKeyboardMarkup([
                [_btn("Quay lại", icon_id="6206032691075223572", callback_data="adm:sys")]
            ])
            await _admin_edit(
                "<tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> <b>IMPORT DỮ LIỆU TỪ BACKUP</b>\n\n"
                "Cách dùng:\n"
                "1. Dùng <code>/backup</code> hoặc lấy file ZIP backup sẵn có.\n"
                "2. Reply vào file ZIP đó và gõ <code>/nhapdata</code>.\n"
                "3. Hoặc gửi trực tiếp file .zip kèm caption <code>/nhapdata</code>.\n\n"
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chỉ nhận file <code>.zip</code> backup hợp lệ.",
                kb,
            )
            return True

        cmd_map = {
            "products":             listproducts_command,
            "duyet":                duyet_command,
            "pending":              pending_manual_command,
            "doanhthu":             doanhthu_command,
            "promobudget":          promobudget_command,
            "analytics":            analytics_command,
            "users":                listusers_command,
            "pending_withdrawals":  pending_withdrawals_command,
            "chats":                chats_command,
            "listcoupons":          listcoupons_command,
            "rewardtop":            rewardtop_command,
            "list_ga":              list_ga_command,
            "api":                  listapi_command,
            "backup":               backup_command,
            "testing":              testing_command,
            "notify":               notify_command,
            "resetnotify":          resetnotify_command,
        }
        handler_fn = cmd_map.get(cmd)
        if handler_fn:
            fake_update = update_from_callback(query)
            if fake_update:
                try:
                    await handler_fn(fake_update, context)
                except Exception as e:
                    logger.error(f"Admin menu exec error ({cmd}): {e}")
                    await context.bot.send_message(
                        ADMIN_USER_ID,
                        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Lỗi khi thực thi <code>/{cmd}</code>: {html.escape(str(e))}",
                        parse_mode=ParseMode.HTML
                    )
        else:
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chức năng <code>{cmd}</code> chưa được liên kết với menu.",
                parse_mode=ParseMode.HTML
            )
        return True

    return False

def update_from_callback(query) -> object:
    class FakeMessage:
        def __init__(self, q):
            self.chat = q.message.chat
            self.chat_id = q.message.chat_id
            self.from_user = q.from_user
            self.text = ""
            self.reply_to_message = None
            self.photo = None
            self.document = None
            self.message_id = q.message.message_id
            self._query = q
        async def reply_text(self, *args, **kwargs):
            return await self._query.message.reply_text(*args, **kwargs)
        async def reply_html(self, *args, **kwargs):
            return await self._query.message.reply_html(*args, **kwargs)
        async def reply_photo(self, *args, **kwargs):
            return await self._query.message.reply_photo(*args, **kwargs)
        async def reply_document(self, *args, **kwargs):
            return await self._query.message.reply_document(*args, **kwargs)

    class FakeUpdate:
        def __init__(self, q):
            self.effective_user = q.from_user
            self.effective_chat = q.message.chat
            self.message = FakeMessage(q)
            self.callback_query = q
            self._bot = q.get_bot()

        def get_bot(self):
            return self._bot

    return FakeUpdate(query)

async def handle_admin_quick_action(query, context: ContextTypes.DEFAULT_TYPE):
    parts = query.data.split(":")
    if len(parts) < 3:
        await safe_answer(query, "Dữ liệu không hợp lệ", show_alert=True)
        return

    action = parts[1]
    target_id_str = parts[2]

    try:
        target_id = int(target_id_str)
    except ValueError:
        await safe_answer(query, "ID không hợp lệ", show_alert=True)
        return

    await query.answer()

    if action == "toggleban":
        if target_id == ADMIN_USER_ID:
            await query.message.reply_text("❌ Không thể cấm chính mình.")
            return
        if target_id in banned_users:
            banned_users.discard(target_id)
            await save_data()
            await query.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã mở cấm user ID: <code>{target_id}</code>", parse_mode=ParseMode.HTML)
        else:
            banned_users.add(target_id)
            await save_data()
            await query.message.reply_text(f"<tg-emoji emoji-id=\"5424857974784925603\">🚫</tg-emoji> Đã cấm user ID: <code>{target_id}</code>", parse_mode=ParseMode.HTML)

    elif action == "addmoney":
        context.user_data['quick_action'] = f"addmoney:{target_id}"
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>CỘNG TIỀN CHO USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: {user_info.get('balance', 0):,} VNĐ\n\n"
            f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Nhập số tiền cần cộng:\n"
            f"<i>(Gõ /cancel để hủy)</i>",
            parse_mode=ParseMode.HTML
        )

    elif action == "submoney":
        context.user_data['quick_action'] = f"submoney:{target_id}"
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"5406745771280187626\">➖</tg-emoji> <b>TRỪ TIỀN USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: {user_info.get('balance', 0):,} VNĐ\n\n"
            f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> Nhập số tiền cần trừ:\n"
            f"<i>(Gõ /cancel để hủy)</i>",
            parse_mode=ParseMode.HTML
        )

    elif action == "chat":
        context.user_data['admin_chat_target'] = target_id
        user_info = user_data_db.get(target_id_str, {})
        name = user_info.get('first_name', 'N/A')
        await query.message.reply_text(
            f"<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> <b>CHAT VỚI USER</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> {name} (ID: <code>{target_id}</code>)\n\n"
            f"Gõ tin nhắn để gửi cho user.\n"
            f"<i>Gõ /cancel để thoát.</i>",
            parse_mode=ParseMode.HTML
        )

async def warranty_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state = context.user_data.get('state')
    
    if user_state == 'awaiting_warranty_photo':
        order_code = context.user_data.get('warranty_claim_order')
        description = context.user_data.get('warranty_description')
        if not update.message.photo: return
        
        photo = update.message.photo[-1].file_id
        
        # Create warranty claim
        claim_id = f"WRC{int(time.time())}"
        warranty_claims[claim_id] = {
            'order_code': order_code,
            'user_id': update.effective_user.id,
            'product_id': order_index[order_code].get('product_id'),
            'description': description,
            'photos': [photo],
            'status': 'pending',
            'timestamp': time.time(),
            'admin_notes': ''
        }
        
        await save_data()
        await clear_user_state(context)
        
        # Notify user
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ GỬI YÊU CẦU BẢO HÀNH</b>\n\n"
            f"Mã yêu cầu: <code>{claim_id}</code>\n"
            f"Admin sẽ xem xét trong 24h",
            parse_mode=ParseMode.HTML,
            reply_markup=create_main_menu(user_id=update.effective_user.id)
        )
        
        # Notify admin
        try:
            await context.bot.send_photo(
                ADMIN_USER_ID,
                photo=photo,
                caption=(
                    f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>YÊU CẦU BẢO HÀNH MỚI</b>\n\n"
                    f"Mã: <code>{claim_id}</code>\n"
                    f"Đơn: <code>{order_code}</code>\n"
                    f"User: {format_user_mention_html(update.effective_user)}\n\n"
                    f"Mô tả:\n<i>{description}</i>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    _btn("Duyệt", icon_id="5021905410089550576", callback_data=f"approve_warranty:{claim_id}"),
                    _btn("Từ chối", icon_id="6114086705512321034", callback_data=f"reject_warranty:{claim_id}")
                ]])
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Cannot notify admin of warranty claim: {e}")



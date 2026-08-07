# --- QUẢN LÝ API KEYS ---
async def addapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tạo API key mới cho đối tác. Cú pháp: /addapi <tên_đối_tác>"""
    if not context.args:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp: `/addapi <tên_đối_tác>`", parse_mode=ParseMode.HTML)
        return

    partner_name = context.args[0]
    # Tạo key ngẫu nhiên
    new_key = "DINO-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    
    # Lưu dưới dạng Dict để chứa cả số dư
    api_keys[new_key] = {
        "name": partner_name,
        "balance": 0  # Số dư ví dùng chung
    }
    await save_data(force=True)
    
    await update.message.reply_html(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ TẠO API KEY MỚI</b>\n\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Đối tác:</b> {partner_name}\n"
        f"🔐 <b>Key:</b> <code>{new_key}</code>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư:</b> 0 VNĐ\n\n"
        f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Hãy yêu cầu đối tác nạp tiền trước khi gọi API."
    )

async def helpapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiện hướng dẫn tích hợp API cho CTV"""
    # Restrict API documentation (contains sensitive info) to admin only
    if update.effective_user and update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Ban khong co quyen xem tai lieu API. Vui long lien he Admin.")
        return
    
    # Lấy Public URL hiện tại (nếu có)
    base_url = get_public_api_base_url()
    base_url_note = (
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Lưu ý:</b> Base URL hiện tại đang dùng Cloudflare Quick Tunnel, "
        "có thể thay đổi sau mỗi lần restart <code>cloudflared</code>. "
        "Nếu link đổi, hãy cập nhật lại cho đối tác ngay.\n\n"
        if "trycloudflare.com" in base_url
        else "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Lưu ý:</b> Base URL hiện tại lấy từ <code>PUBLIC_API_URL</code> đang cấu hình trong hệ thống.\n\n"
    )
    msg = (
        "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> <b>HƯỚNG DẪN ĐĂNG KÝ & TÍCH HỢP API (FULL)</b>\n"
        "================================================\n\n"
        "<b>A) Quy trình đăng ký Partner API</b>\n"
        "1. Gửi lệnh <code>/dkyapi</code> để tạo yêu cầu.\n"
        "2. Chờ Admin duyệt (nhận tin nhắn chứa API key).\n"
        "3. Nạp ví chung bằng <code>/napapi [số_tiền]</code>.\n"
        "4. Sau khi có số dư, bắt đầu gọi API để bán hàng.\n\n"
        "<b>B) Lệnh vận hành</b>\n"
        "• Partner: <code>/dkyapi</code>, <code>/napapi 500000</code>\n"
        "• Admin: <code>/addapi</code>, <code>/napi</code>, <code>/listapi</code>, <code>/delapi</code>\n\n"
        f"<b>C) Cấu hình tích hợp</b>\n"
        f"<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>BASE URL:</b> <code>{base_url}</code>\n"
        f"{base_url_note}"
        "🔐 <b>Header bắt buộc:</b> <code>x-api-key: KEY_PARTNER_CUA_BAN</code>\n"
        "<tg-emoji emoji-id=\"5350481781306958339\">🧾</tg-emoji> <b>Header khuyến nghị:</b> <code>x-idempotency-key: MA_DON_DOI_TAC</code>\n\n"
        "<b>D) API sản phẩm thường (V2)</b>\n"
        "• <code>GET /api/v2/me</code> - kiểm tra key/số dư dùng chung\n"
        "• <code>GET /api/v2/catalog</code> - chỉ sản phẩm thường\n"
        "• <code>POST /api/v2/orders</code> - tạo đơn sản phẩm thường\n"
        "• <code>GET /api/v2/orders</code> - lịch sử đơn thường\n"
        "• <code>GET /api/v2/orders/{order_code}</code> - chi tiết đơn thường\n\n"
        "<b>E) Social Media API</b>\n"
        "• <code>GET /api/social/catalog</code> - chỉ dịch vụ social\n"
        "• <code>POST /api/social/orders</code> - tạo đơn social\n"
        "• <code>GET /api/social/orders</code> - lịch sử đơn social\n"
        "• <code>GET /api/social/orders/{order_code}</code> - refresh trạng thái nguồn\n"
        "• <code>GET /api/social/orders/by-ref/{partner_ref}</code> - tra theo mã đối tác\n\n"
        "<b>F) Body mẫu đơn thường</b>\n"
        "<pre>{\n"
        '  "partner_ref": "ORDER_12345",\n'
        '  "product_id": "p_1700000000",\n'
        '  "quantity": 1,\n'
        '  "customer_email": "khach@example.com",\n'
        '  "customer_id": "telegram_9988",\n'
        '  "send_email": false\n'
        "}</pre>\n"
        "<b>Body mẫu đơn social</b>\n"
        "<pre>{\n"
        '  "partner_ref": "SOCIAL_12345",\n'
        '  "product_id": "ctt_8786",\n'
        '  "quantity": 100,\n'
        '  "target_link": "https://facebook.com/example"\n'
        "}</pre>\n"
        "<i>partner_ref phải duy nhất; retry phải giữ nguyên mã.</i>\n\n"
        "<b>G) Nhận kết quả</b>\n"
        "• Sản phẩm thường giao ngay nằm trong <code>data.items</code>.\n"
        "• Social đọc <code>supplier_status</code>, <code>supplier_remains</code> và poll endpoint social.\n\n"
        "<b>H) Lỗi thường gặp</b>\n"
        "• <code>400</code>: thiếu field hoặc dùng nhầm nhóm endpoint\n"
        "• <code>401</code>: sai/thiếu API key\n"
        "• <code>402</code>: không đủ số dư ví chung\n"
        "• <code>404</code>: không tìm thấy sản phẩm/đơn\n"
        "• <code>409</code>: partner_ref đang xử lý\n\n"
        "<b>I) Test nhanh</b>\n"
        "<pre>"
        f"curl -H \"x-api-key: KEY_PARTNER_CUA_BAN\" \"{base_url}/api/v2/catalog\"\n"
        f"curl -H \"x-api-key: KEY_PARTNER_CUA_BAN\" \"{base_url}/api/social/catalog\""
        "</pre>\n"
        "<b>J) API cũ (tương thích ngược)</b>\n"
        "• <code>GET /api/status</code>\n"
        "• <code>POST /api/buy</code>"
    )
    
    await update.message.reply_html(msg)

async def napi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Nạp tiền cho Key API.
    Cách 1: Nạp thủ công (Admin): /napi <Key_hoặc_Tên> <Số_tiền>
    Cách 2: Tạo QR nạp tự động: /napi qr <Key_hoặc_Tên> <Số_tiền>
    """
    if len(context.args) < 2:
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>HƯỚNG DẪN NẠP VÍ CHUNG</b>\n\n"
            "<tg-emoji emoji-id=\"5382322671679708881\">1️⃣</tg-emoji> <b>Nạp thủ công (Cộng ngay):</b>\n"
            "<code>/napi <Key/Tên> <Số_Tiền></code>\n"
            "VD: <code>/napi ShopMinh 500000</code>\n\n"
            "<tg-emoji emoji-id=\"5381990043642502553\">2️⃣</tg-emoji> <b>Tạo QR nạp tự động (Gửi cho khách):</b>\n"
            "<code>/napi qr <Key/Tên> <Số_Tiền></code>\n"
            "VD: <code>/napi qr ShopMinh 500000</code>"
        )
        return

    mode = "manual"
    if context.args[0].lower() == "qr":
        if len(context.args) != 3:
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp tạo QR: /napi qr <Key/Tên> <Số_Tiền>")
            return
        mode = "qr"
        target = context.args[1]
        amount_str = context.args[2]
    else:
        target = context.args[0]
        amount_str = context.args[1]

    try:
        amount = int(amount_str)
        if amount <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Số tiền phải là số nguyên dương.")
        return

    # Tìm key tương ứng
    found_key = None
    if target in api_keys:
        found_key = target
    else:
        for k, v in api_keys.items():
            name = v if isinstance(v, str) else v.get("name")
            if name == target:
                found_key = k
                break
    
    if not found_key:
        await update.message.reply_text("❌ Không tìm thấy Partner/Key này.")
        return

    found_data = _api_normalize_partner_key(found_key)
    if not isinstance(found_data, dict):
        await update.message.reply_text("❌ Dữ liệu API key không hợp lệ.")
        return
    partner_name = str(found_data.get("name") or found_key)

    # Xử lý theo Mode
    if mode == "manual":
        adjusted, new_balance, _ = await safe_api_adjust_balance(
            found_key,
            amount,
            save=True,
            reason=f"Admin top-up {partner_name}",
        )
        if not adjusted:
            await update.message.reply_text("❌ Không thể cộng tiền vào API key này.")
            return
        
        await update.message.reply_html(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ CỘNG TIỀN THỦ CÔNG!</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner_name}\n"
            f"<tg-emoji emoji-id=\"5397916757333654639\">➕</tg-emoji> <b>Nạp thêm:</b> {amount:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư mới:</b> {int(new_balance):,} VNĐ"
        )
    
    else: # mode == "qr"
        # Tạo mã memo nạp tiền duy nhất
        deposit_code = f"NAPI{int(time.time())}{random.randint(10,99)}"
        
        # Lưu vào danh sách chờ nạp
        pending_api_deposits[deposit_code] = {
            "api_key": found_key,
            "partner_name": partner_name,
            "amount": amount,
            "time": time.time(),
            "user_id": update.effective_user.id  # Lưu lại user_id để gửi thông báo
        }
        await save_data(force=True)
        
        # Tạo link QR VietQR
        _encoded_partner = quote(f"Nap {partner_name}")
        qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NUMBER}-print.png?amount={amount}&addInfo={deposit_code}&accountName={quote(ACCOUNT_NAME)}"
        
        caption = (
            f"<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>QR Code Nạp Ví Chung</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner_name}\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung:</b> <code>{deposit_code}</code>\n\n"
            f"<i><tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Hệ thống sẽ tự động cộng tiền khi nhận được chuyển khoản có nội dung <b>{deposit_code}</b>.</i>"
        )
        
        await update.message.reply_photo(photo=qr_url, caption=caption, parse_mode=ParseMode.HTML)

def build_partner_api_topup_qr_url(transfer_content: str, amount: int | None = None) -> str:
    safe_content = quote(str(transfer_content or "").strip())
    qr_params = [
        f"addInfo={safe_content}",
        f"accountName={quote(ACCOUNT_NAME)}",
    ]
    try:
        safe_amount = int(amount or 0)
    except (TypeError, ValueError):
        safe_amount = 0
    if safe_amount > 0:
        qr_params.insert(0, f"amount={safe_amount}")
    return f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NUMBER}-print.png?{'&'.join(qr_params)}"


async def create_partner_api_topup_request(
    api_key: str,
    partner_name: str,
    user_id: int,
    amount: int | None = None,
):
    transfer_content = str(int(user_id))
    pending_api_deposits[transfer_content] = {
        "api_key": api_key,
        "partner_name": partner_name,
        "amount": int(amount or 0),
        "time": time.time(),
        "user_id": int(user_id),
        "reference_type": "telegram_id",
        "transfer_content": transfer_content,
    }
    await save_data(force=True)
    return build_partner_api_topup_qr_url(transfer_content, amount), transfer_content


async def napapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Khách hàng (CTV) tự lấy QR nạp tiền cho API Key.
    Cú pháp: /napapi <Số_tiền> (Tự động nhận diện User)
    """
    user_id = update.effective_user.id
    
    # 1. Tự động tìm API Key của user
    found_key = None
    partner_name = "Unknown"
    
    for k, v in api_keys.items():
        if isinstance(v, dict) and v.get("user_id") == user_id:
            found_key = k
            partner_name = v.get("name")
            break
            
    if not found_key:
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>BẠN CHƯA CÓ TÀI KHOẢN ĐẠI LÝ (API)</b>\n\n"
            "Vui lòng đăng ký theo quy trình:\n"
            "1. Gửi <code>/dkyapi</code>\n"
            "2. Chờ Admin duyệt\n"
            "3. Nhận API Key và nạp ví bằng <code>/napapi</code>"
        )
        return

    # 2. Xử lý số tiền
    if not context.args:
        await update.message.reply_html(
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>HƯỚNG DẪN NẠP VÍ CHUNG</b>\n\n"
            "Cú pháp: <code>/napapi [số_tiền]</code>\n"
            "Ví dụ: <code>/napapi 500000</code>"
        )
        return

    try:
        # Xử lý input (bỏ dấu phẩy, chấm nếu có)
        amount_str = context.args[0].replace(',', '').replace('.', '')
        amount = int(amount_str)
        if amount < 10000:
             await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Số tiền nạp tối thiểu là 10,000đ.")
             return
    except ValueError:
        await update.message.reply_text("❌ Số tiền không hợp lệ. Vui lòng nhập số.")
        return

    # 3. Tạo yêu cầu nạp ví và QR theo Telegram ID của user
    qr_url, transfer_content = await create_partner_api_topup_request(
        found_key,
        partner_name,
        update.effective_user.id,
        amount=amount,
    )
    
    caption = (
        f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>YÊU CẦU NẠP VÍ CHUNG</b>\n\n"
        f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner_name}\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung CK:</b> <code>{transfer_content}</code>\n\n"
        f"<i>Vui lòng quét QR hoặc chuyển khoản đúng nội dung <b>{transfer_content}</b> (Telegram ID của bạn). Hệ thống sẽ tự động duyệt và cộng tiền sau 1-3 phút.</i>"
    )

    await update.message.reply_photo(photo=qr_url, caption=caption, parse_mode=ParseMode.HTML)

async def delapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xóa API key. Cú pháp: /delapi <key>"""
    if not context.args:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp: `/delapi <key>`", parse_mode=ParseMode.HTML)
        return

    key = context.args[0]
    if key in api_keys:
        api_keys.pop(key, None)
        await save_data(force=True)
        await update.message.reply_text(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã xóa API Key: {key}")
    else:
        await update.message.reply_text(f"❌ Không tìm thấy Key: {key}")

async def listapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Liệt kê danh sách API key"""
    if not api_keys:
        await update.message.reply_text("<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> Hiện chưa có API Key nào.")
        return

    header = (
        f"<b><tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> "
        f"DANH SÁCH API KEYS ({len(api_keys)})</b>\n\n"
    )
    message_parts = []
    current_part = header
    for key, data in api_keys.items():
        # Xử lý tương thích ngược (nếu dữ liệu cũ là string)
        if isinstance(data, str):
            name = data
            balance = 0
            # Tự động cập nhật lên format mới
            api_keys[key] = {"name": name, "balance": 0}
        else:
            name = data.get("name")
            balance = _api_get_partner_display_balance(key, data)

        entry = (
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>{html.escape(str(name or 'Unknown'))}</b> | "
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {balance:,} đ\n"
            f"🔐 <code>{key}</code>\n\n"
        )
        if len(current_part) + len(entry) > 3900:
            message_parts.append(current_part)
            current_part = ""
        current_part += entry

    if current_part:
        message_parts.append(current_part)
    
    await save_data() # Lưu lại nếu có migrate data
    for part in message_parts:
        await update.message.reply_html(part)
        await asyncio.sleep(0.2)


async def addmoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: Cộng tiền cho user. Cú pháp: /addmoney <user_id> <amount>"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp: `/addmoney <user_id> <amount>`", parse_mode=ParseMode.HTML)
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1].replace(',', '').replace('.', ''))
        
        if amount <= 0:
            await update.message.reply_text("❌ Số tiền phải lớn hơn 0.")
            return

        user_info = db_get_user(target_id)
        if not user_info:
            await update.message.reply_text(f"❌ Không tìm thấy user ID: {target_id}")
            return
            
        current_balance = user_info.get('balance', 0)
        new_balance = current_balance + amount
        db_update_balance(target_id, new_balance, reason=f"Admin Add: {amount:,} VNĐ")
        
        # Notify Admin
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ CỘNG TIỀN THÀNH CÔNG</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: {user_info.get('full_name', 'Unknown')} (`{target_id}`)\n"
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Cộng: +{amount:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư mới: {new_balance:,} VNĐ",
            parse_mode=ParseMode.HTML
        )
        
        # Notify User
        try:
            await context.bot.send_message(
                target_id,
                f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>THÔNG BÁO SỐ DƯ</b>\n\n"
                f"Admin đã cộng <b>+{amount:,} VNĐ</b> vào ví của bạn.\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: <b>{new_balance:,} VNĐ</b>",
                parse_mode=ParseMode.HTML
            )
        except (Forbidden, BadRequest) as e:
            logger.warning(f"Cannot notify user {target_id} after addmoney: {e}")
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể gửi thông báo cho user (Block bot?)")
            
    except ValueError:
        await update.message.reply_text("❌ ID hoặc số tiền không hợp lệ.")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Add money error: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra.")

async def submoney_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command: Trừ tiền user. Cú pháp: /submoney <user_id> <amount>"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Cú pháp: `/submoney <user_id> <amount>`", parse_mode=ParseMode.HTML)
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1].replace(',', '').replace('.', ''))
        
        if amount <= 0:
            await update.message.reply_text("❌ Số tiền phải lớn hơn 0.")
            return

        user_info = db_get_user(target_id)
        if not user_info:
            await update.message.reply_text(f"❌ Không tìm thấy user ID: {target_id}")
            return
            
        current_balance = user_info.get('balance', 0)
        new_balance = current_balance - amount
        
        # Cho phép âm tiền nếu admin muốn phạt, hoặc chặn âm tùy policy. Ở đây cho phép.
        # Nhưng thường ví không nên âm. Warning nếu âm.
        if new_balance < 0:
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Lưu ý: Sau khi trừ, số dư user sẽ bị âm.")
            
        db_update_balance(target_id, new_balance, reason=f"Admin Subtract: {amount:,} VNĐ")
        
        # Notify Admin
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ TRỪ TIỀN THÀNH CÔNG</b>\n\n"
            f"<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> User: {user_info.get('full_name', 'Unknown')} (`{target_id}`)\n"
            f"<tg-emoji emoji-id=\"5863724849851011383\">💸</tg-emoji> Trừ: -{amount:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư mới: {new_balance:,} VNĐ",
            parse_mode=ParseMode.HTML
        )
        
        # Notify User
        try:
            await context.bot.send_message(
                target_id,
                f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>THÔNG BÁO TRỪ TIỀN</b>\n\n"
                f"Admin đã trừ <b>-{amount:,} VNĐ</b> từ ví của bạn.\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: <b>{new_balance:,} VNĐ</b>",
                parse_mode=ParseMode.HTML
            )
        except (Forbidden, BadRequest) as e:
            logger.warning(f"Cannot notify user {target_id} after submoney: {e}")
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không thể gửi thông báo cho user (Block bot?)")
            
    except ValueError:
        await update.message.reply_text("❌ ID hoặc số tiền không hợp lệ.")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Sub money error: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra.")


def _mask_bank_account(account_no: str) -> str:
    digits = str(account_no or "").strip()
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def _mbbank_model_to_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(getattr(value, "__dict__", {}) or {})


def _parse_mbbank_amount(value) -> int:
    from decimal import Decimal, InvalidOperation

    normalized = str(value or "0").strip().replace(",", "")
    try:
        return int(Decimal(normalized))
    except (InvalidOperation, ValueError, TypeError):
        return 0


def _extract_mbbank_account_balance(balance_response, account_no: str) -> dict | None:
    payload = _mbbank_model_to_dict(balance_response)
    accounts = payload.get("acct_list") or payload.get("acctList") or []
    expected_account = str(account_no or "").strip()
    for raw_account in accounts:
        account = _mbbank_model_to_dict(raw_account)
        current_account = str(account.get("acctNo") or account.get("accountNo") or "").strip()
        if current_account == expected_account:
            return {
                "account_no": current_account,
                "account_name": str(account.get("acctNm") or account.get("accountName") or "").strip(),
                "currency": str(account.get("ccyCd") or account.get("currency") or "VND").strip() or "VND",
                "current_balance": _parse_mbbank_amount(account.get("currentBalance")),
            }
    return None


def _fetch_mbbank_account_balance(login_username: str, password: str, account_no: str) -> dict | None:
    import mbbank

    client = mbbank.MBBank(
        username=login_username,
        password=password,
        retry_times=3,
        timeout=BANK_API_TIMEOUT_SECONDS,
    )
    return _extract_mbbank_account_balance(client.getBalance(), account_no)


async def sodumb_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin-only command: display the configured MBBank account balance."""
    import asyncio
    import datetime
    import html as html_lib
    import os

    user = getattr(update, "effective_user", None)
    if not user or user.id != ADMIN_USER_ID:
        return

    account_no = str(BANK_ACCOUNT_NUMBER or "").strip()
    password = str(API_PASSWORD or "").strip()
    login_username = os.getenv("BANK_LOGIN_USERNAME", account_no).strip()
    if not account_no or not password or not login_username:
        await update.message.reply_text("❌ Chưa cấu hình đầy đủ tài khoản MBBank.")
        return

    status_message = await update.message.reply_text("⏳ Đang kiểm tra số dư MBBank...")
    try:
        balance = await asyncio.wait_for(
            asyncio.to_thread(
                _fetch_mbbank_account_balance,
                login_username,
                password,
                account_no,
            ),
            timeout=max(10.0, float(BANK_API_TIMEOUT_SECONDS) + 5.0),
        )
        if not balance:
            result_text = (
                "❌ <b>KHÔNG TÌM THẤY TÀI KHOẢN</b>\n\n"
                f"Tài khoản cấu hình: <code>{_mask_bank_account(account_no)}</code>"
            )
        else:
            checked_at = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            account_name = html_lib.escape(balance.get("account_name") or "MBBank")
            currency = html_lib.escape(balance.get("currency") or "VND")
            result_text = (
                "🏦 <b>SỐ DƯ TÀI KHOẢN MBBANK</b>\n\n"
                f"👤 Chủ tài khoản: <b>{account_name}</b>\n"
                f"💳 Số tài khoản: <code>{_mask_bank_account(balance['account_no'])}</code>\n"
                f"💰 Số dư hiện tại: <b>{int(balance['current_balance']):,} {currency}</b>\n"
                f"🕒 Kiểm tra lúc: <code>{checked_at}</code>"
            )
        await status_message.edit_text(result_text, parse_mode=ParseMode.HTML)
    except Exception as exc:
        # Never include the exception body: upstream errors may contain account data.
        logger.warning("MBBank balance check failed (%s)", type(exc).__name__)
        await status_message.edit_text(
            "❌ Không kiểm tra được số dư MBBank. Vui lòng kiểm tra đăng nhập hoặc thử lại sau."
        )






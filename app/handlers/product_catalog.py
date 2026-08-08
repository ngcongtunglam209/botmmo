

# ==============================================================================
#  QUẢN LÝ SẢN PHẨM KHÁC (STORE)
# ==============================================================================

# States for Add Product (UPDATED: Thêm nhiều states cho thông tin chi tiết)
import html

ADD_PROD_NAME, ADD_PROD_PRICE, ADD_PROD_DESC, ADD_PROD_DURATION, ADD_PROD_GMAIL, ADD_PROD_WARRANTY, ADD_PROD_CONFIRM = range(100, 107)
ADD_PROD_DESC_CHOICE, ADD_PROD_AI_DESC = 107, 108  # NEW: AI description states
ADD_PROD_NAME_SUGGEST = 109  # NEW: Name suggestion state
# States for Add Stock
STOCK_SELECT, STOCK_INPUT = range(120, 122)
EDIT_PROD_SELECT, EDIT_PROD_FIELD, EDIT_PROD_VALUE = range(110, 113)
EDIT_PROD_AI_DESC = 113  # NEW: AI description state for edit product # NEW: Edit Product
STOCK_VIEW, STOCK_DELETE_SELECT = range(114, 116) # NEW: Market Stock
# NEW: State cho nhập email sau thanh toán (manual products)
AWAITING_MANUAL_EMAIL = 200
# NEW: States cho Giveaway
GA_TITLE, GA_PRIZE, GA_MODE, GA_TIME, GA_BANNER, GA_CHANNEL = range(300, 306)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{E_LIMIT} Đã hủy thao tác.")
    return ConversationHandler.END

def _truncate_admin_product_button_text(text: str, limit: int = 56):
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."

EDIT_PRODUCT_PAGE_SIZE = 12

def _get_edit_product_entries():
    return [
        (pid, product)
        for pid, product in products.items()
        if isinstance(product, dict)
    ]

def _build_edit_product_select_payload(page: int = 0):
    entries = _get_edit_product_entries()
    total = len(entries)
    total_pages = max(1, (total + EDIT_PRODUCT_PAGE_SIZE - 1) // EDIT_PRODUCT_PAGE_SIZE)
    page = max(0, min(int(page or 0), total_pages - 1))
    start = page * EDIT_PRODUCT_PAGE_SIZE
    page_entries = entries[start:start + EDIT_PRODUCT_PAGE_SIZE]

    keyboard = []
    for pid, p in page_entries:
        btn_text = _truncate_admin_product_button_text(p.get('name', pid))
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"edit_sel_{pid}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("<<", callback_data=f"edit_page_{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=f"edit_page_{page}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(">>", callback_data=f"edit_page_{page + 1}"))
    if nav:
        keyboard.append(nav)

    text = (
        "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> "
        "<b>CHỌN SẢN PHẨM CẦN SỬA</b>\n"
        f"<i>Trang {page + 1}/{total_pages} - {total} sản phẩm</i>"
    )
    return text, InlineKeyboardMarkup(keyboard)

# --- ADD PRODUCT (UPDATED: Thêm nhiều thông tin chi tiết) ---
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    await update.message.reply_text(
        f"{E_TAG} <b>THÊM SẢN PHẨM MỚI</b>\n\n"
        "Bước 1/6: Nhập <b>Tên sản phẩm</b>\n\n"
        "<i>VD: Netflix Premium, Spotify Family, v.v</i>",
        parse_mode='HTML'
    )
    return ADD_PROD_NAME

def find_similar_product_name(input_name: str, threshold: float = 0.80) -> str | None:
    """Find an existing product name similar to input_name.
    Priority: 1) Exact normalized match (same chars, diff caps/spaces)
              2) Prefix match (input is prefix of existing name, >= 6 chars)
              3) Fuzzy similarity >= threshold
    """
    norm_in = re.sub(r'[^a-z0-9]', '', input_name.lower())
    if len(norm_in) < 4:
        return None  # Too short, skip
    best_ratio = 0.0
    best_match = None
    prefix_matches = []
    for p in products.values():
        existing = p['name']
        if existing == input_name:
            return None  # Already exact match
        norm_ex = re.sub(r'[^a-z0-9]', '', existing.lower())
        # Priority 1: Exact normalized match (same letters, diff formatting)
        if norm_in == norm_ex:
            return existing
        # Priority 2: Input is a prefix of existing (>= 6 chars)
        if len(norm_in) >= 6 and norm_ex.startswith(norm_in):
            prefix_matches.append(existing)
        # Priority 3: Fuzzy similarity
        ratio = difflib.SequenceMatcher(None, norm_in, norm_ex).ratio()
        if ratio >= threshold and ratio > best_ratio:
            best_ratio = ratio
            best_match = existing
    # Return prefix match only if unique (avoid ambiguity)
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    return best_match

async def receive_prod_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    typed_name = update.message.text.strip()
    context.user_data['new_prod_name'] = typed_name
    similar = find_similar_product_name(typed_name)
    if similar:
        keyboard = [
            [_btn("Dùng tên chuẩn", icon_id="5021905410089550576", callback_data="name_suggest_use")],
            [InlineKeyboardButton("<tg-emoji emoji-id=\"5350752364246606166\">✍️</tg-emoji> Giữ tên tôi nhập", callback_data="name_suggest_keep")]
        ]
        context.user_data['suggested_prod_name'] = similar
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5429571366384842791\">🔍</tg-emoji> <b>Phát hiện tên tương tự!</b>\n\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Bạn nhập: <code>{typed_name}</code>\n"
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Tên chuẩn đề cử: <b>{similar}</b>\n\n"
            "Dùng tên nào?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ADD_PROD_NAME_SUGGEST
    await update.message.reply_text(
        f"{E_TAG} Bước 2/6: Nhập <b>Giá bán (VNĐ)</b>\n\n"
        "<i>Chỉ nhập số, VD: 75000</i>",
        parse_mode='HTML'
    )
    return ADD_PROD_PRICE

async def receive_prod_name_suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name suggestion: use standard or keep typed name"""
    query = update.callback_query
    await safe_answer(query)
    if query.data == 'name_suggest_use':
        context.user_data['new_prod_name'] = context.user_data.pop('suggested_prod_name', context.user_data['new_prod_name'])
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã dùng tên chuẩn: <b>{context.user_data['new_prod_name']}</b>",
            parse_mode='HTML')
    else:
        context.user_data.pop('suggested_prod_name', None)
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5350752364246606166\">✍️</tg-emoji> Giữ tên: <b>{context.user_data['new_prod_name']}</b>",
            parse_mode='HTML')
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"{E_TAG} Bước 2/6: Nhập <b>Giá bán (VNĐ)</b>\n\n<i>Chỉ nhập số, VD: 75000</i>",
        parse_mode='HTML')
    return ADD_PROD_PRICE

async def receive_prod_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(',', '').replace('.', ''))
        if price <= 0:
            await update.message.reply_text("❌ Giá phải lớn hơn 0. Vui lòng nhập lại.")
            return ADD_PROD_PRICE
        context.user_data['new_prod_price'] = price
        keyboard = [
            [_btn("Tạo mô tả bằng AI", icon_id="5287684458881756303", callback_data="desc_choice_ai")],
            [_btn("Tự nhập tay", icon_id="5828072695694102691", callback_data="desc_choice_manual")]
        ]
        await update.message.reply_text(
            "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Bước 3/6: <b>Mô tả sản phẩm</b>\n\n"
            "Bạn muốn tạo mô tả thế nào?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ADD_PROD_DESC_CHOICE
    except ValueError:
        await update.message.reply_text("❌ Giá không hợp lệ. Vui lòng nhập lại số.")
        return ADD_PROD_PRICE

async def receive_prod_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_desc'] = update.message.text
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Bước 4/6: Nhập <b>Thời hạn sử dụng</b>\n\n"
        "<i>VD: 1 tháng, 3 tháng, Vĩnh viễn, v.v</i>",
        parse_mode='HTML'
    )
    return ADD_PROD_DURATION

async def receive_prod_desc_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI vs manual choice for product description"""
    query = update.callback_query
    await safe_answer(query)
    if query.data == 'desc_choice_manual':
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">✍️</tg-emoji> Nhập <b>MÔ TẢ SẢN PHẨM</b>:\n\n<i>VD: Tài khoản Netflix Premium 4K, xem không giới hạn</i>", parse_mode='HTML')
        return ADD_PROD_DESC
    name = context.user_data.get('new_prod_name', '')
    price = context.user_data.get('new_prod_price', 0)
    await query.edit_message_text("<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Đang tạo mô tả bằng AI... Vui lòng chờ")
    prompt = (f"Viết mô tả sản phẩm ngắn gọn 2-3 câu cho shop bán hàng Telegram tiếng Việt.\n"
             f"Tên sản phẩm: {name}\nGiá: {price:,} VNĐ\n"
             f"Yêu cầu: ngắn gọn, hấp dẫn, thế hiện rõ lợi ích, không quá 150 ký tự. Chỉ viết mô tả, không thêm bất kỳ tiêu đề nào khác.")
    desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
    if not desc: desc = f"{name} - Chất lượng cao, giao hàng tự động qua Telegram."
    context.user_data['ai_generated_desc'] = desc
    keyboard = [
        [_btn("Dùng mô tả này", icon_id="5021905410089550576", callback_data="ai_desc_use")],
        [_btn("Tạo lại", icon_id="5370715282044100355", callback_data="ai_desc_regen")],
        [_btn("Tự viết", icon_id="5828072695694102691", callback_data="ai_desc_manual")]
    ]
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>AI đề xuất:</b>\n\n{desc}\n\n<i>Bạn muốn dùng mô tả này không?</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ADD_PROD_AI_DESC

async def receive_prod_ai_desc_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle accept/regenerate/manual after AI desc generation"""
    query = update.callback_query
    await safe_answer(query)
    if query.data == 'ai_desc_use':
        context.user_data['new_prod_desc'] = context.user_data.get('ai_generated_desc', '')
        await query.edit_message_text("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Đã dùng mô tả AI!\n\n<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Bước 4/6: Nhập <b>Thời hạn sử dụng</b>\n<i>VD: 1 tháng, 3 tháng, Vĩnh viễn</i>", parse_mode='HTML')
        return ADD_PROD_DURATION
    elif query.data == 'ai_desc_regen':
        name = context.user_data.get('new_prod_name', '')
        price = context.user_data.get('new_prod_price', 0)
        await query.edit_message_text("<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> Đang tạo lại...")
        prompt = (f"Viết mô tả sản phẩm ngắn gọn 2-3 câu cho shop bán hàng Telegram tiếng Việt.\n"
                 f"Tên sản phẩm: {name}\nGiá: {price:,} VNĐ\n"
                 f"Yêu cầu: ngắn gọn, hấp dẫn. Viết KHÁC với lần trước. Chỉ mô tả, tối đa 150 ký tự.")
        desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
        if not desc: desc = f"{name} - Sản phẩm chính hãng, giao hàng nhanh."
        context.user_data['ai_generated_desc'] = desc
        keyboard = [
            [_btn("Dùng mô tả này", icon_id="5021905410089550576", callback_data="ai_desc_use")],
            [_btn("Tạo lại", icon_id="5370715282044100355", callback_data="ai_desc_regen")],
            [_btn("Tự viết", icon_id="5828072695694102691", callback_data="ai_desc_manual")]
        ]
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>AI đề xuất:</b>\n\n{desc}\n\n<i>Bạn muốn dùng mô tả này không?</i>",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return ADD_PROD_AI_DESC
    else:  # ai_desc_manual
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">✍️</tg-emoji> Nhập <b>MÔ TẢ SẢN PHẨM</b>:", parse_mode='HTML')
        return ADD_PROD_DESC

async def receive_prod_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_duration'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> CÓ - Yêu cầu Gmail", callback_data='prod_gmail_yes')],
        [_btn("Không", icon_id="5273914604752216432", callback_data='prod_gmail_no')]
    ]
    
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Bước 5/6: Sản phẩm này có <b>yêu cầu Gmail</b> không?\n\n"
        "<i>Nếu CÓ: Bot sẽ hỏi email khách khi mua\n"
        "Nếu KHÔNG: Gửi trực tiếp tài khoản qua Telegram</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    return ADD_PROD_GMAIL

async def receive_prod_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    requires_gmail = query.data == 'prod_gmail_yes'
    context.user_data['new_prod_gmail'] = requires_gmail
    
    await query.edit_message_text(
        "<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> Bước 6/6: Nhập <b>Thời gian bảo hành</b>\n\n"
        "<i>VD: 7 ngày, 30 ngày, Trọn đời, v.v</i>",
        parse_mode='HTML'
    )
    return ADD_PROD_WARRANTY

async def receive_prod_warranty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_warranty'] = update.message.text
    
    # Show preview
    name = context.user_data['new_prod_name']
    price = context.user_data['new_prod_price']
    desc = context.user_data['new_prod_desc']
    duration = context.user_data['new_prod_duration']
    requires_gmail = context.user_data['new_prod_gmail']
    warranty = context.user_data['new_prod_warranty']
    
    preview = (
        f"{E_TAG} <b>XÁC NHẬN THÔNG TIN SẢN PHẨM</b>\n\n"
        f"{E_TAG} <b>Tên:</b> {name}\n"
        f"{E_TAG} <b>Giá:</b> {price:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Mô tả:</b> {desc}\n"
        f"{E_LOADING} <b>Thời hạn:</b> {duration}\n"
        f"{E_GLOBE} <b>Yêu cầu Gmail:</b> {f'{E_SUCCESS} Có' if requires_gmail else f'{E_LIMIT} Không'}\n"
        f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo hành:</b> {warranty}\n\n"
        f"{E_ERROR} Bạn có chắc chắn muốn tạo sản phẩm này?"
    )
    
    keyboard = [
        [_btn("Xác nhận tạo", icon_id="6269163801178804220", callback_data='prod_confirm_yes')],
        [_btn("Hủy bỏ", icon_id="5273914604752216432", callback_data='prod_confirm_no')]
    ]
    
    await update.message.reply_text(preview, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ADD_PROD_CONFIRM

async def receive_prod_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    if query.data == 'prod_confirm_no':
        await query.edit_message_text("❌ Đã hủy tạo sản phẩm.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Lấy tất cả thông tin
    name = context.user_data['new_prod_name']
    price = context.user_data['new_prod_price']
    desc = context.user_data['new_prod_desc']
    duration = context.user_data['new_prod_duration']
    requires_gmail = context.user_data['new_prod_gmail']
    warranty = context.user_data['new_prod_warranty']
    
    # Generate ID
    prod_id = f"p_{int(time.time())}"
    
    # Lưu sản phẩm với đầy đủ thông tin
    products[prod_id] = {
        "name": name,
        "price": price,
        "description": desc,
        "duration": duration,               # NEW
        "requires_gmail": requires_gmail,   # NEW
        "warranty": warranty,               # NEW
        "stock": [],
        "created_at": time.time()
    }
    await save_data(force=True)
    
    await query.edit_message_text(
        f"{E_SUCCESS} <b>ĐÃ THÊM SẢN PHẨM THÀNH CÔNG!</b>\n\n"
        f"{E_ID} <b>ID:</b> <code>{prod_id}</code>\n"
        f"{E_TAG} <b>Tên:</b> {name}\n"
        f"{E_TAG} <b>Giá:</b> {price:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Mô tả:</b> {desc}\n"
        f"{E_LOADING} <b>Thời hạn:</b> {duration}\n"
        f"{E_GLOBE} <b>Gmail:</b> {f'{E_SUCCESS} Bắt buộc' if requires_gmail else f'{E_LIMIT} Không cần'}\n"
        f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo hành:</b> {warranty}\n\n"
        f"{E_TAG} <b>Tồn kho:</b> 0 (Dùng /addstock để thêm hàng)",
        parse_mode='HTML'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# --- ADD STOCK ---
ADD_STOCK_PAGE_SIZE = 20


def _is_add_stock_local_product(product: dict | None) -> bool:
    if not isinstance(product, dict):
        return False
    if product.get('requires_gmail', False):
        return False
    return isinstance(product.get('stock', []), list)


def _get_add_stock_auto_product_entries():
    entries = [
        (pid, product)
        for pid, product in products.items()
        if _is_add_stock_local_product(product)
    ]
    entries.sort(key=lambda item: str(item[1].get('name') or item[0]).casefold())
    return entries


def _build_add_stock_product_menu(page: int = 0):
    entries = _get_add_stock_auto_product_entries()
    total_pages = max(1, (len(entries) + ADD_STOCK_PAGE_SIZE - 1) // ADD_STOCK_PAGE_SIZE)
    safe_page = min(max(0, int(page or 0)), total_pages - 1)
    start_index = safe_page * ADD_STOCK_PAGE_SIZE
    visible_entries = entries[start_index:start_index + ADD_STOCK_PAGE_SIZE]

    keyboard = []
    for pid, product in visible_entries:
        stock_count = len(product.get('stock', []))
        btn_text = _truncate_admin_product_button_text(f"{product.get('name', pid)} ({stock_count} items)")
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"sel_stock_{pid}")])

    if total_pages > 1:
        nav_row = []
        if safe_page > 0:
            nav_row.append(InlineKeyboardButton("Trang truoc", callback_data=f"stock_page_{safe_page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{safe_page + 1}/{total_pages}", callback_data="stock_page_ignore"))
        if safe_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Trang sau", callback_data=f"stock_page_{safe_page + 1}"))
        keyboard.append(nav_row)

    text = (
        "<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>CHON SAN PHAM LOCAL DE THEM KHO</b>\n\n"
        "<i>Chi hien thi san pham co kho nhap tay</i>"
    )
    if total_pages > 1:
        text += f"\n\n<b>Trang:</b> {safe_page + 1}/{total_pages} | <b>Tong:</b> {len(entries)} san pham"

    return text, InlineKeyboardMarkup(keyboard)


async def add_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    
    if not products:
        await update.message.reply_text("❌ Chưa có sản phẩm nào. Dùng /newproduct để tạo trước.")
        return ConversationHandler.END
    
    # NEW: Lọc chỉ hiển thị products KHÔNG yêu cầu Gmail
    auto_products = dict(_get_add_stock_auto_product_entries())
    
    if not auto_products:
        await update.message.reply_text(
            "ℹ️ <b>KHÔNG CÓ SẢN PHẨM NÀO CẦN STOCK</b>\n\n"
            "Tất cả sản phẩm hiện tại đều là <b>dịch vụ manual</b> (yêu cầu Gmail).\n"
            "Admin sẽ xử lý từng đơn khi có khách mua.\n\n"
            "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Để tạo sản phẩm cần stock, chọn <b>❌ KHÔNG</b> ở bước Gmail khi /newproduct",
            parse_mode='HTML'
        )
        return ConversationHandler.END
        
    msg, reply_markup = _build_add_stock_product_menu(page=0)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    return STOCK_SELECT

async def stock_select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if query.data == "stock_page_ignore":
        return STOCK_SELECT
    if query.data.startswith("stock_page_"):
        try:
            page = int(query.data.replace("stock_page_", "", 1))
        except ValueError:
            page = 0
        msg, reply_markup = _build_add_stock_product_menu(page=page)
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        return STOCK_SELECT

    prod_id = query.data.replace("sel_stock_", "")
    if prod_id not in products:
        await query.edit_message_text("❌ Sản phẩm không tồn tại.")
        return ConversationHandler.END
    
    p = products[prod_id]
    
    # NEW: Check nếu là manual product
    if p.get('requires_gmail', False):
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>SẢN PHẨM DỊCH VỤ MANUAL</b>\n\n"
            f"Sản phẩm <b>{p['name']}</b> là dịch vụ yêu cầu Gmail.\n"
            f"Admin sẽ xử lý thủ công từng đơn, <b>không cần thêm stock trước</b>.\n\n"
            f"<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Khi có khách mua:\n"
            f"1. Khách thanh toán\n"
            f"2. Khách nhập email\n"
            f"3. Bot báo Admin\n"
            f"4. Admin setup/gửi cho khách\n"
            f"5. Admin bấm 'Đã hoàn thành'",
            parse_mode='HTML'
        )
        return ConversationHandler.END
        
    context.user_data['stock_prod_id'] = prod_id
    await query.edit_message_text(
        f"<tg-emoji emoji-id=\"5854908544712707500\">📥</tg-emoji> <b>THÊM KHO CHO: {p['name']}</b>\n\n"
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Loại:</b> Sản phẩm AUTO (giao hàng tự động)\n\n"
        f"<b>Cách nhập tài khoản:</b>\n"
        f"1. Gửi file <b>.txt</b> (Mỗi dòng 1 tài khoản)\n"
        f"2. Hoặc nhắn tin trực tiếp (Mỗi dòng 1 tài khoản)\n\n"
        f"<b>VD format trong file:</b>\n"
        f"<code>KHANG13@IKHNG12345</code>\n"
        f"<code>KHANG14@IKHNG12346</code>\n"
        f"<code>KHANG15@IKHNG12347</code>\n\n"
        f"<i>Gõ /cancel để hủy.</i>",
        parse_mode='HTML'
    )
    return STOCK_INPUT

async def receive_stock_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prod_id = context.user_data.get('stock_prod_id')
        new_items = []
        
        # Handle File
        if update.message.document:
            doc = update.message.document
            # Cho phép cả file .txt và không có extension nếu nội dung là text
            if not doc.file_name.lower().endswith('.txt'):
                await update.message.reply_text("❌ Chỉ chấp nhận file .txt")
                return STOCK_INPUT
                
            file = await doc.get_file()
            content = await file.download_as_bytearray()
            
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                # FIX BUG #4: Không fallback, yêu cầu UTF-8
                await update.message.reply_text(
                    "❌ <b>FILE KHÔNG ĐÚNG ĐỊNH DẠNG!</b>\n\n"
                    "Vui lòng lưu file với encoding <b>UTF-8</b>:\n"
                    "1. Mở Notepad\n"
                    "2. File → Save As\n"
                    "3. Encoding: UTF-8\n"
                    "4. Save và upload lại",
                    parse_mode='HTML'
                )
                return STOCK_INPUT
                
            new_items = [line.strip() for line in text_content.splitlines() if line.strip()]
            
        # Handle Text
        elif update.message.text:
            new_items = [line.strip() for line in update.message.text.splitlines() if line.strip()]
            
        if new_items:
            current_stock = products[prod_id].get('stock', [])
            was_out_of_stock = len(current_stock) == 0  # Track trạng thái trước khi thêm
            
            products[prod_id]['stock'] = current_stock + new_items
            await save_data(force=True)
            
            new_total = len(products[prod_id]['stock'])
            product_name = products[prod_id]['name']
            
            await update.message.reply_text(
                f"{E_SUCCESS} <b>ĐÃ THÊM {len(new_items)} ITEMS!</b>\n\n"
                f"{E_TAG} Sản phẩm: {product_name}\n"
                f"{E_STAT} Tổng tồn kho: {new_total}",
                parse_mode='HTML'
            )
            
            create_background_task(notify_stock_added(
                context,
                product_name,
                len(new_items),
                new_total,
                price=int(products[prod_id].get('price', 0) or 0),
            ))

            # NEW: Auto-broadcast nếu từ hết hàng → có hàng
            if was_out_of_stock and new_total > 0:
                create_background_task(broadcast_back_in_stock(context, product_name, prod_id, new_total))
            
            return ConversationHandler.END
        else:
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không đọc được dữ liệu nào từ file hoặc tin nhắn. Vui lòng thử lại.")
            return STOCK_INPUT
            
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error in receive_stock_input: {e}", exc_info=True)
        logger.error(f"Error in product catalog message update: {e}"); await update.message.reply_text("❌ Có lỗi xảy ra khi cập nhật catalog, vui lòng kiểm tra logs.")
        return ConversationHandler.END

# --- EDIT PRODUCT ---
async def edit_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        if update.message:
            await update.message.reply_text("❌ Bạn không có quyền truy cập lệnh này.")
        return ConversationHandler.END
    
    if not products:
        await update.message.reply_text("❌ Chưa có sản phẩm nào.")
        return ConversationHandler.END
        
    text, reply_markup = _build_edit_product_select_payload(0)
        
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return EDIT_PROD_SELECT

async def edit_prod_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)

    if query.data.startswith("edit_page_"):
        try:
            page = int(query.data.replace("edit_page_", "", 1))
        except ValueError:
            page = 0
        text, reply_markup = _build_edit_product_select_payload(page)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return EDIT_PROD_SELECT
    
    prod_id = query.data.replace("edit_sel_", "")
    if prod_id not in products:
        await query.edit_message_text("❌ Sản phẩm không tồn tại or đã bị xóa.")
        return ConversationHandler.END
        
    context.user_data['edit_prod_id'] = prod_id
    p = products[prod_id]
    product_name = html.escape(str(p.get('name', prod_id)))
    product_price = int(p.get('price', 0) or 0)
    product_description = html.escape(str(p.get('description', 'N/A')))
    product_duration = html.escape(str(p.get('duration', 'N/A')))
    product_warranty = html.escape(str(p.get('warranty', 'N/A')))
    
    msg = (
        f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>ĐANG SỬA: {product_name}</b>\n\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Giá hiện tại:</b> {product_price:,} VNĐ\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mô tả:</b> {product_description}\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Thời hạn:</b> {product_duration}\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Bảo hành:</b> {product_warranty}\n\n"
        f"<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> <i>Chọn thông tin cần sửa:</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("Tên sản phẩm", callback_data="edit_field_name")],
        [InlineKeyboardButton("Giá bán", callback_data="edit_field_price")],
        [InlineKeyboardButton("Mô tả", callback_data="edit_field_desc")],
        [InlineKeyboardButton("Thời hạn", callback_data="edit_field_duration")],
        [InlineKeyboardButton("Bảo hành", callback_data="edit_field_warranty")],
        [_btn("Hủy bỏ", icon_id="5273914604752216432", callback_data="cancel_edit")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return EDIT_PROD_FIELD

async def edit_prod_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    data = query.data
    if data == "cancel_edit":
        await query.edit_message_text("❌ Đã hủy sửa sản phẩm.")
        context.user_data.pop('edit_prod_id', None)
        return ConversationHandler.END
        
    field_map = {
        "edit_field_name": ("name", "Nhập TÊN MỚI cho sản phẩm:"),
        "edit_field_price": ("price", "Nhập GIÁ MỚI (VNĐ):"),
        "edit_field_desc": None,  # Handled separately with AI/manual choice
        "edit_field_duration": ("duration", "Nhập THỜI HẠN MỚI:"),
        "edit_field_warranty": ("warranty", "Nhập BẢO HÀNH MỚI:")
    }
    
    if data == "edit_field_desc":
        keyboard = [
            [_btn("AI tạo mô tả", icon_id="5287684458881756303", callback_data="ai_edit_desc_gen")],
            [_btn("Tự nhập tay", icon_id="5828072695694102691", callback_data="ai_edit_desc_manual")]
        ]
        await query.edit_message_text("<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Sửa MÔ TẢ</b>\n\nBạn muốn:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return EDIT_PROD_FIELD
    
    field_key, prompt = field_map.get(data)
    context.user_data['edit_field'] = field_key
    
    await query.edit_message_text(f"<tg-emoji emoji-id=\"5350752364246606166\">✏️</tg-emoji> <b>{prompt}</b>", parse_mode='HTML')
    return EDIT_PROD_VALUE

async def receive_edit_ai_desc_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI or manual choice for editing product description"""
    query = update.callback_query
    await safe_answer(query)
    prod_id = context.user_data.get('edit_prod_id')
    if not prod_id or prod_id not in products:
        await query.edit_message_text("❌ Lỗi dữ liệu. Vui lòng thử lại.")
        return ConversationHandler.END
    if query.data == 'ai_edit_desc_manual':
        context.user_data['edit_field'] = 'description'
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">✍️</tg-emoji> Nhập <b>MÔ TẢ MỚI</b>:", parse_mode='HTML')
        return EDIT_PROD_VALUE
    elif query.data == 'ai_edit_desc_gen':
        p = products[prod_id]
        await query.edit_message_text("<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> Đang tạo mô tả bằng AI...")
        prompt = (f"Viết mô tả sản phẩm ngắn gọn 2-3 câu cho shop Telegram tiếng Việt.\n"
                 f"Tên: {p['name']}\nGiá: {p['price']:,} VNĐ\n"
                 f"Yêu cầu: ngắn gọn, hấp dẫn, không quá 150 ký tự. Chỉ viết mô tả.")
        desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
        if not desc: desc = f"{p['name']} - Chất lượng cao, giao hàng tự động."
        context.user_data['ai_edit_desc'] = desc
        safe_desc = html.escape(str(desc))
        keyboard = [
            [_btn("Dùng mô tả này", icon_id="5021905410089550576", callback_data="ai_edit_desc_accept")],
            [_btn("Tạo lại", icon_id="5370715282044100355", callback_data="ai_edit_desc_gen")],
            [_btn("Tự viết", icon_id="5828072695694102691", callback_data="ai_edit_desc_manual")]
        ]
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>AI đề xuất:</b>\n\n{safe_desc}\n\n<i>Dùng mô tả này không?</i>",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return EDIT_PROD_AI_DESC
    elif query.data == 'ai_edit_desc_accept':
        desc = context.user_data.get('ai_edit_desc', '')
        products[prod_id]['description'] = desc
        await save_data(force=True, tables=[PRODUCTS_FILE])
        safe_desc = html.escape(str(desc))
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Đã cập nhật mô tả bằng AI!</b>\n\n{safe_desc}",
            parse_mode='HTML')
        context.user_data.pop('edit_prod_id', None)
        return ConversationHandler.END

async def edit_prod_receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    prod_id = context.user_data.get('edit_prod_id')
    field = context.user_data.get('edit_field')
    
    if not prod_id or prod_id not in products:
        await update.message.reply_text("❌ Lỗi dữ liệu. Vui lòng thử lại.")
        return ConversationHandler.END
    
    # Validate Price
    if field == 'price':
        try:
            full_price = int(text.replace('.', '').replace(',', ''))
            if full_price < 0: raise ValueError
            products[prod_id]['price'] = full_price
        except ValueError:
            await update.message.reply_text("❌ Giá không hợp lệ. Vui lòng nhập số.")
            return EDIT_PROD_VALUE
    else:
        products[prod_id][field] = text
        
    await save_data(force=True, tables=[PRODUCTS_FILE])
    safe_product_name = html.escape(str(products[prod_id].get('name', prod_id)))
    safe_text = html.escape(str(text))
    
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>CẬP NHẬT THÀNH CÔNG!</b>\n\n"
        f"Sản phẩm: {safe_product_name}\n"
        f"{field.capitalize()}: {safe_text}",
        parse_mode='HTML'
    )
    
    # Clear state
    context.user_data.pop('edit_prod_id', None)
    context.user_data.pop('edit_field', None)
    return ConversationHandler.END


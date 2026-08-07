

# ==============================================================================
#  QUáº¢N LÃ Sáº¢N PHáº¨M KHÃC (STORE)
# ==============================================================================

# States for Add Product (UPDATED: ThÃªm nhiá»u states cho thÃ´ng tin chi tiáº¿t)
import html

ADD_PROD_NAME, ADD_PROD_PRICE, ADD_PROD_DESC, ADD_PROD_DURATION, ADD_PROD_GMAIL, ADD_PROD_WARRANTY, ADD_PROD_CONFIRM = range(100, 107)
ADD_PROD_DESC_CHOICE, ADD_PROD_AI_DESC = 107, 108  # NEW: AI description states
ADD_PROD_NAME_SUGGEST = 109  # NEW: Name suggestion state
# States for Add Stock
STOCK_SELECT, STOCK_INPUT = range(120, 122)
EDIT_PROD_SELECT, EDIT_PROD_FIELD, EDIT_PROD_VALUE = range(110, 113)
EDIT_PROD_AI_DESC = 113  # NEW: AI description state for edit product # NEW: Edit Product
STOCK_VIEW, STOCK_DELETE_SELECT = range(114, 116) # NEW: Market Stock
# NEW: State cho nháº­p email sau thanh toÃ¡n (manual products)
AWAITING_MANUAL_EMAIL = 200
# NEW: States cho Giveaway
GA_TITLE, GA_PRIZE, GA_MODE, GA_TIME, GA_BANNER, GA_CHANNEL = range(300, 306)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{E_LIMIT} ÄÃ£ há»§y thao tÃ¡c.")
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
        if not (isinstance(product, dict) and product.get("is_social_source_service"))
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
        "<tg-emoji emoji-id=\"5215392879320505675\">ðŸ› ï¸</tg-emoji> "
        "<b>CHá»ŒN Sáº¢N PHáº¨M Cáº¦N Sá»¬A</b>\n"
        f"<i>Trang {page + 1}/{total_pages} - {total} sáº£n pháº©m</i>"
    )
    return text, InlineKeyboardMarkup(keyboard)

# --- ADD PRODUCT (UPDATED: ThÃªm nhiá»u thÃ´ng tin chi tiáº¿t) ---
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    await update.message.reply_text(
        f"{E_TAG} <b>THÃŠM Sáº¢N PHáº¨M Má»šI</b>\n\n"
        "BÆ°á»›c 1/6: Nháº­p <b>TÃªn sáº£n pháº©m</b>\n\n"
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
            [_btn("DÃ¹ng tÃªn chuáº©n", icon_id="5021905410089550576", callback_data="name_suggest_use")],
            [InlineKeyboardButton("<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Giá»¯ tÃªn tÃ´i nháº­p", callback_data="name_suggest_keep")]
        ]
        context.user_data['suggested_prod_name'] = similar
        await update.message.reply_text(
            f"<tg-emoji emoji-id=\"5429571366384842791\">ðŸ”</tg-emoji> <b>PhÃ¡t hiá»‡n tÃªn tÆ°Æ¡ng tá»±!</b>\n\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> Báº¡n nháº­p: <code>{typed_name}</code>\n"
            f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> TÃªn chuáº©n Ä‘á» cá»­: <b>{similar}</b>\n\n"
            "DÃ¹ng tÃªn nÃ o?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ADD_PROD_NAME_SUGGEST
    await update.message.reply_text(
        f"{E_TAG} BÆ°á»›c 2/6: Nháº­p <b>GiÃ¡ bÃ¡n (VNÄ)</b>\n\n"
        "<i>Chá»‰ nháº­p sá»‘, VD: 75000</i>",
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
            f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ dÃ¹ng tÃªn chuáº©n: <b>{context.user_data['new_prod_name']}</b>",
            parse_mode='HTML')
    else:
        context.user_data.pop('suggested_prod_name', None)
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Giá»¯ tÃªn: <b>{context.user_data['new_prod_name']}</b>",
            parse_mode='HTML')
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"{E_TAG} BÆ°á»›c 2/6: Nháº­p <b>GiÃ¡ bÃ¡n (VNÄ)</b>\n\n<i>Chá»‰ nháº­p sá»‘, VD: 75000</i>",
        parse_mode='HTML')
    return ADD_PROD_PRICE

async def receive_prod_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.replace(',', '').replace('.', ''))
        if price <= 0:
            await update.message.reply_text("âŒ GiÃ¡ pháº£i lá»›n hÆ¡n 0. Vui lÃ²ng nháº­p láº¡i.")
            return ADD_PROD_PRICE
        context.user_data['new_prod_price'] = price
        keyboard = [
            [_btn("Táº¡o mÃ´ táº£ báº±ng AI", icon_id="5287684458881756303", callback_data="desc_choice_ai")],
            [_btn("Tá»± nháº­p tay", icon_id="5828072695694102691", callback_data="desc_choice_manual")]
        ]
        await update.message.reply_text(
            "<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> BÆ°á»›c 3/6: <b>MÃ´ táº£ sáº£n pháº©m</b>\n\n"
            "Báº¡n muá»‘n táº¡o mÃ´ táº£ tháº¿ nÃ o?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return ADD_PROD_DESC_CHOICE
    except ValueError:
        await update.message.reply_text("âŒ GiÃ¡ khÃ´ng há»£p lá»‡. Vui lÃ²ng nháº­p láº¡i sá»‘.")
        return ADD_PROD_PRICE

async def receive_prod_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_desc'] = update.message.text
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> BÆ°á»›c 4/6: Nháº­p <b>Thá»i háº¡n sá»­ dá»¥ng</b>\n\n"
        "<i>VD: 1 thÃ¡ng, 3 thÃ¡ng, VÄ©nh viá»…n, v.v</i>",
        parse_mode='HTML'
    )
    return ADD_PROD_DURATION

async def receive_prod_desc_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI vs manual choice for product description"""
    query = update.callback_query
    await safe_answer(query)
    if query.data == 'desc_choice_manual':
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Nháº­p <b>MÃ” Táº¢ Sáº¢N PHáº¨M</b>:\n\n<i>VD: TÃ i khoáº£n Netflix Premium 4K, xem khÃ´ng giá»›i háº¡n</i>", parse_mode='HTML')
        return ADD_PROD_DESC
    name = context.user_data.get('new_prod_name', '')
    price = context.user_data.get('new_prod_price', 0)
    await query.edit_message_text("<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> Äang táº¡o mÃ´ táº£ báº±ng AI... Vui lÃ²ng chá»")
    prompt = (f"Viáº¿t mÃ´ táº£ sáº£n pháº©m ngáº¯n gá»n 2-3 cÃ¢u cho shop bÃ¡n hÃ ng Telegram tiáº¿ng Viá»‡t.\n"
             f"TÃªn sáº£n pháº©m: {name}\nGiÃ¡: {price:,} VNÄ\n"
             f"YÃªu cáº§u: ngáº¯n gá»n, háº¥p dáº«n, tháº¿ hiá»‡n rÃµ lá»£i Ã­ch, khÃ´ng quÃ¡ 150 kÃ½ tá»±. Chá»‰ viáº¿t mÃ´ táº£, khÃ´ng thÃªm báº¥t ká»³ tiÃªu Ä‘á» nÃ o khÃ¡c.")
    desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
    if not desc: desc = f"{name} - Cháº¥t lÆ°á»£ng cao, giao hÃ ng tá»± Ä‘á»™ng qua Telegram."
    context.user_data['ai_generated_desc'] = desc
    keyboard = [
        [_btn("DÃ¹ng mÃ´ táº£ nÃ y", icon_id="5021905410089550576", callback_data="ai_desc_use")],
        [_btn("Táº¡o láº¡i", icon_id="5370715282044100355", callback_data="ai_desc_regen")],
        [_btn("Tá»± viáº¿t", icon_id="5828072695694102691", callback_data="ai_desc_manual")]
    ]
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> <b>AI Ä‘á» xuáº¥t:</b>\n\n{desc}\n\n<i>Báº¡n muá»‘n dÃ¹ng mÃ´ táº£ nÃ y khÃ´ng?</i>",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ADD_PROD_AI_DESC

async def receive_prod_ai_desc_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle accept/regenerate/manual after AI desc generation"""
    query = update.callback_query
    await safe_answer(query)
    if query.data == 'ai_desc_use':
        context.user_data['new_prod_desc'] = context.user_data.get('ai_generated_desc', '')
        await query.edit_message_text("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> ÄÃ£ dÃ¹ng mÃ´ táº£ AI!\n\n<tg-emoji emoji-id=\"5213349767672769194\">â°</tg-emoji> BÆ°á»›c 4/6: Nháº­p <b>Thá»i háº¡n sá»­ dá»¥ng</b>\n<i>VD: 1 thÃ¡ng, 3 thÃ¡ng, VÄ©nh viá»…n</i>", parse_mode='HTML')
        return ADD_PROD_DURATION
    elif query.data == 'ai_desc_regen':
        name = context.user_data.get('new_prod_name', '')
        price = context.user_data.get('new_prod_price', 0)
        await query.edit_message_text("<tg-emoji emoji-id=\"5462956611033117422\">ðŸ”„</tg-emoji> Äang táº¡o láº¡i...")
        prompt = (f"Viáº¿t mÃ´ táº£ sáº£n pháº©m ngáº¯n gá»n 2-3 cÃ¢u cho shop bÃ¡n hÃ ng Telegram tiáº¿ng Viá»‡t.\n"
                 f"TÃªn sáº£n pháº©m: {name}\nGiÃ¡: {price:,} VNÄ\n"
                 f"YÃªu cáº§u: ngáº¯n gá»n, háº¥p dáº«n. Viáº¿t KHÃC vá»›i láº§n trÆ°á»›c. Chá»‰ mÃ´ táº£, tá»‘i Ä‘a 150 kÃ½ tá»±.")
        desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
        if not desc: desc = f"{name} - Sáº£n pháº©m chÃ­nh hÃ£ng, giao hÃ ng nhanh."
        context.user_data['ai_generated_desc'] = desc
        keyboard = [
            [_btn("DÃ¹ng mÃ´ táº£ nÃ y", icon_id="5021905410089550576", callback_data="ai_desc_use")],
            [_btn("Táº¡o láº¡i", icon_id="5370715282044100355", callback_data="ai_desc_regen")],
            [_btn("Tá»± viáº¿t", icon_id="5828072695694102691", callback_data="ai_desc_manual")]
        ]
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> <b>AI Ä‘á» xuáº¥t:</b>\n\n{desc}\n\n<i>Báº¡n muá»‘n dÃ¹ng mÃ´ táº£ nÃ y khÃ´ng?</i>",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return ADD_PROD_AI_DESC
    else:  # ai_desc_manual
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Nháº­p <b>MÃ” Táº¢ Sáº¢N PHáº¨M</b>:", parse_mode='HTML')
        return ADD_PROD_DESC

async def receive_prod_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_prod_duration'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> CÃ“ - YÃªu cáº§u Gmail", callback_data='prod_gmail_yes')],
        [_btn("KhÃ´ng", icon_id="5273914604752216432", callback_data='prod_gmail_no')]
    ]
    
    await update.message.reply_text(
        "<tg-emoji emoji-id=\"6129860303619363484\">ðŸ“§</tg-emoji> BÆ°á»›c 5/6: Sáº£n pháº©m nÃ y cÃ³ <b>yÃªu cáº§u Gmail</b> khÃ´ng?\n\n"
        "<i>Náº¿u CÃ“: Bot sáº½ há»i email khÃ¡ch khi mua\n"
        "Náº¿u KHÃ”NG: Gá»­i trá»±c tiáº¿p tÃ i khoáº£n qua Telegram</i>",
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
        "<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> BÆ°á»›c 6/6: Nháº­p <b>Thá»i gian báº£o hÃ nh</b>\n\n"
        "<i>VD: 7 ngÃ y, 30 ngÃ y, Trá»n Ä‘á»i, v.v</i>",
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
        f"{E_TAG} <b>XÃC NHáº¬N THÃ”NG TIN Sáº¢N PHáº¨M</b>\n\n"
        f"{E_TAG} <b>TÃªn:</b> {name}\n"
        f"{E_TAG} <b>GiÃ¡:</b> {price:,} VNÄ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>MÃ´ táº£:</b> {desc}\n"
        f"{E_LOADING} <b>Thá»i háº¡n:</b> {duration}\n"
        f"{E_GLOBE} <b>YÃªu cáº§u Gmail:</b> {f'{E_SUCCESS} CÃ³' if requires_gmail else f'{E_LIMIT} KhÃ´ng'}\n"
        f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>Báº£o hÃ nh:</b> {warranty}\n\n"
        f"{E_ERROR} Báº¡n cÃ³ cháº¯c cháº¯n muá»‘n táº¡o sáº£n pháº©m nÃ y?"
    )
    
    keyboard = [
        [_btn("XÃ¡c nháº­n táº¡o", icon_id="6269163801178804220", callback_data='prod_confirm_yes')],
        [_btn("Há»§y bá»", icon_id="5273914604752216432", callback_data='prod_confirm_no')]
    ]
    
    await update.message.reply_text(preview, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return ADD_PROD_CONFIRM

async def receive_prod_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    if query.data == 'prod_confirm_no':
        await query.edit_message_text("âŒ ÄÃ£ há»§y táº¡o sáº£n pháº©m.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Láº¥y táº¥t cáº£ thÃ´ng tin
    name = context.user_data['new_prod_name']
    price = context.user_data['new_prod_price']
    desc = context.user_data['new_prod_desc']
    duration = context.user_data['new_prod_duration']
    requires_gmail = context.user_data['new_prod_gmail']
    warranty = context.user_data['new_prod_warranty']
    
    # Generate ID
    prod_id = f"p_{int(time.time())}"
    
    # LÆ°u sáº£n pháº©m vá»›i Ä‘áº§y Ä‘á»§ thÃ´ng tin
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
        f"{E_SUCCESS} <b>ÄÃƒ THÃŠM Sáº¢N PHáº¨M THÃ€NH CÃ”NG!</b>\n\n"
        f"{E_ID} <b>ID:</b> <code>{prod_id}</code>\n"
        f"{E_TAG} <b>TÃªn:</b> {name}\n"
        f"{E_TAG} <b>GiÃ¡:</b> {price:,} VNÄ\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>MÃ´ táº£:</b> {desc}\n"
        f"{E_LOADING} <b>Thá»i háº¡n:</b> {duration}\n"
        f"{E_GLOBE} <b>Gmail:</b> {f'{E_SUCCESS} Báº¯t buá»™c' if requires_gmail else f'{E_LIMIT} KhÃ´ng cáº§n'}\n"
        f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>Báº£o hÃ nh:</b> {warranty}\n\n"
        f"{E_TAG} <b>Tá»“n kho:</b> 0 (DÃ¹ng /addstock Ä‘á»ƒ thÃªm hÃ ng)",
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
    if product.get('is_supplier_source_resell') or product.get('supplier_source_product_id') or product.get('supplier_source_variant_id'):
        return False
    if (
        product.get('is_social_source_service')
        or product.get('ctt_auto_managed')
        or product.get('ctt_service_id')
        or product.get('ctt_source_category')
    ):
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
        "<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>CHON SAN PHAM LOCAL DE THEM KHO</b>\n\n"
        "<i>Chi hien thi san pham co kho nhap tay, khong hien hang API/social/resell</i>"
    )
    if total_pages > 1:
        text += f"\n\n<b>Trang:</b> {safe_page + 1}/{total_pages} | <b>Tong:</b> {len(entries)} san pham"

    return text, InlineKeyboardMarkup(keyboard)


async def add_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    
    if not products:
        await update.message.reply_text("âŒ ChÆ°a cÃ³ sáº£n pháº©m nÃ o. DÃ¹ng /newproduct Ä‘á»ƒ táº¡o trÆ°á»›c.")
        return ConversationHandler.END
    
    # NEW: Lá»c chá»‰ hiá»ƒn thá»‹ products KHÃ”NG yÃªu cáº§u Gmail
    auto_products = dict(_get_add_stock_auto_product_entries())
    
    if not auto_products:
        await update.message.reply_text(
            "â„¹ï¸ <b>KHÃ”NG CÃ“ Sáº¢N PHáº¨M NÃ€O Cáº¦N STOCK</b>\n\n"
            "Táº¥t cáº£ sáº£n pháº©m hiá»‡n táº¡i Ä‘á»u lÃ  <b>dá»‹ch vá»¥ manual</b> (yÃªu cáº§u Gmail).\n"
            "Admin sáº½ xá»­ lÃ½ tá»«ng Ä‘Æ¡n khi cÃ³ khÃ¡ch mua.\n\n"
            "<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> Äá»ƒ táº¡o sáº£n pháº©m cáº§n stock, chá»n <b>âŒ KHÃ”NG</b> á»Ÿ bÆ°á»›c Gmail khi /newproduct",
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
        await query.edit_message_text("âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i.")
        return ConversationHandler.END
    
    p = products[prod_id]
    
    # NEW: Check náº¿u lÃ  manual product
    if p.get('requires_gmail', False):
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> <b>Sáº¢N PHáº¨M Dá»ŠCH Vá»¤ MANUAL</b>\n\n"
            f"Sáº£n pháº©m <b>{p['name']}</b> lÃ  dá»‹ch vá»¥ yÃªu cáº§u Gmail.\n"
            f"Admin sáº½ xá»­ lÃ½ thá»§ cÃ´ng tá»«ng Ä‘Æ¡n, <b>khÃ´ng cáº§n thÃªm stock trÆ°á»›c</b>.\n\n"
            f"<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> Khi cÃ³ khÃ¡ch mua:\n"
            f"1. KhÃ¡ch thanh toÃ¡n\n"
            f"2. KhÃ¡ch nháº­p email\n"
            f"3. Bot bÃ¡o Admin\n"
            f"4. Admin setup/gá»­i cho khÃ¡ch\n"
            f"5. Admin báº¥m 'ÄÃ£ hoÃ n thÃ nh'",
            parse_mode='HTML'
        )
        return ConversationHandler.END
        
    context.user_data['stock_prod_id'] = prod_id
    await query.edit_message_text(
        f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¥</tg-emoji> <b>THÃŠM KHO CHO: {p['name']}</b>\n\n"
        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>Loáº¡i:</b> Sáº£n pháº©m AUTO (giao hÃ ng tá»± Ä‘á»™ng)\n\n"
        f"<b>CÃ¡ch nháº­p tÃ i khoáº£n:</b>\n"
        f"1. Gá»­i file <b>.txt</b> (Má»—i dÃ²ng 1 tÃ i khoáº£n)\n"
        f"2. Hoáº·c nháº¯n tin trá»±c tiáº¿p (Má»—i dÃ²ng 1 tÃ i khoáº£n)\n\n"
        f"<b>VD format trong file:</b>\n"
        f"<code>KHANG13@IKHNG12345</code>\n"
        f"<code>KHANG14@IKHNG12346</code>\n"
        f"<code>KHANG15@IKHNG12347</code>\n\n"
        f"<i>GÃµ /cancel Ä‘á»ƒ há»§y.</i>",
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
            # Cho phÃ©p cáº£ file .txt vÃ  khÃ´ng cÃ³ extension náº¿u ná»™i dung lÃ  text
            if not doc.file_name.lower().endswith('.txt'):
                await update.message.reply_text("âŒ Chá»‰ cháº¥p nháº­n file .txt")
                return STOCK_INPUT
                
            file = await doc.get_file()
            content = await file.download_as_bytearray()
            
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                # FIX BUG #4: KhÃ´ng fallback, yÃªu cáº§u UTF-8
                await update.message.reply_text(
                    "âŒ <b>FILE KHÃ”NG ÄÃšNG Äá»ŠNH Dáº NG!</b>\n\n"
                    "Vui lÃ²ng lÆ°u file vá»›i encoding <b>UTF-8</b>:\n"
                    "1. Má»Ÿ Notepad\n"
                    "2. File â†’ Save As\n"
                    "3. Encoding: UTF-8\n"
                    "4. Save vÃ  upload láº¡i",
                    parse_mode='HTML'
                )
                return STOCK_INPUT
                
            new_items = [line.strip() for line in text_content.splitlines() if line.strip()]
            
        # Handle Text
        elif update.message.text:
            new_items = [line.strip() for line in update.message.text.splitlines() if line.strip()]
            
        if new_items:
            current_stock = products[prod_id].get('stock', [])
            was_out_of_stock = len(current_stock) == 0  # Track tráº¡ng thÃ¡i trÆ°á»›c khi thÃªm
            
            products[prod_id]['stock'] = current_stock + new_items
            await save_data(force=True)
            
            new_total = len(products[prod_id]['stock'])
            product_name = products[prod_id]['name']
            
            await update.message.reply_text(
                f"{E_SUCCESS} <b>ÄÃƒ THÃŠM {len(new_items)} ITEMS!</b>\n\n"
                f"{E_TAG} Sáº£n pháº©m: {product_name}\n"
                f"{E_STAT} Tá»•ng tá»“n kho: {new_total}",
                parse_mode='HTML'
            )
            
            # NEW: Auto-broadcast náº¿u tá»« háº¿t hÃ ng â†’ cÃ³ hÃ ng
            if was_out_of_stock and new_total > 0:
                create_background_task(broadcast_back_in_stock(context, product_name, prod_id, new_total))
            
            return ConversationHandler.END
        else:
            await update.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> KhÃ´ng Ä‘á»c Ä‘Æ°á»£c dá»¯ liá»‡u nÃ o tá»« file hoáº·c tin nháº¯n. Vui lÃ²ng thá»­ láº¡i.")
            return STOCK_INPUT
            
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error in receive_stock_input: {e}", exc_info=True)
        logger.error(f"Error in product catalog message update: {e}"); await update.message.reply_text("âŒ CÃ³ lá»—i xáº£y ra khi cáº­p nháº­t catalog, vui lÃ²ng kiá»ƒm tra logs.")
        return ConversationHandler.END

# --- EDIT PRODUCT ---
async def edit_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        if update.message:
            await update.message.reply_text("âŒ Báº¡n khÃ´ng cÃ³ quyá»n truy cáº­p lá»‡nh nÃ y.")
        return ConversationHandler.END
    
    if not products:
        await update.message.reply_text("âŒ ChÆ°a cÃ³ sáº£n pháº©m nÃ o.")
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
        await query.edit_message_text("âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i or Ä‘Ã£ bá»‹ xÃ³a.")
        return ConversationHandler.END
        
    context.user_data['edit_prod_id'] = prod_id
    p = products[prod_id]
    product_name = html.escape(str(p.get('name', prod_id)))
    product_price = int(p.get('price', 0) or 0)
    product_description = html.escape(str(p.get('description', 'N/A')))
    product_duration = html.escape(str(p.get('duration', 'N/A')))
    product_warranty = html.escape(str(p.get('warranty', 'N/A')))
    
    msg = (
        f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>ÄANG Sá»¬A: {product_name}</b>\n\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>GiÃ¡ hiá»‡n táº¡i:</b> {product_price:,} VNÄ\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>MÃ´ táº£:</b> {product_description}\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>Thá»i háº¡n:</b> {product_duration}\n"
        f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> <b>Báº£o hÃ nh:</b> {product_warranty}\n\n"
        f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> <i>Chá»n thÃ´ng tin cáº§n sá»­a:</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("TÃªn sáº£n pháº©m", callback_data="edit_field_name")],
        [InlineKeyboardButton("GiÃ¡ bÃ¡n", callback_data="edit_field_price")],
        [InlineKeyboardButton("MÃ´ táº£", callback_data="edit_field_desc")],
        [InlineKeyboardButton("Thá»i háº¡n", callback_data="edit_field_duration")],
        [InlineKeyboardButton("Báº£o hÃ nh", callback_data="edit_field_warranty")],
        [_btn("Há»§y bá»", icon_id="5273914604752216432", callback_data="cancel_edit")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return EDIT_PROD_FIELD

async def edit_prod_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    data = query.data
    if data == "cancel_edit":
        await query.edit_message_text("âŒ ÄÃ£ há»§y sá»­a sáº£n pháº©m.")
        context.user_data.pop('edit_prod_id', None)
        return ConversationHandler.END
        
    field_map = {
        "edit_field_name": ("name", "Nháº­p TÃŠN Má»šI cho sáº£n pháº©m:"),
        "edit_field_price": ("price", "Nháº­p GIÃ Má»šI (VNÄ):"),
        "edit_field_desc": None,  # Handled separately with AI/manual choice
        "edit_field_duration": ("duration", "Nháº­p THá»œI Háº N Má»šI:"),
        "edit_field_warranty": ("warranty", "Nháº­p Báº¢O HÃ€NH Má»šI:")
    }
    
    if data == "edit_field_desc":
        keyboard = [
            [_btn("AI táº¡o mÃ´ táº£", icon_id="5287684458881756303", callback_data="ai_edit_desc_gen")],
            [_btn("Tá»± nháº­p tay", icon_id="5828072695694102691", callback_data="ai_edit_desc_manual")]
        ]
        await query.edit_message_text("<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>Sá»­a MÃ” Táº¢</b>\n\nBáº¡n muá»‘n:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return EDIT_PROD_FIELD
    
    field_key, prompt = field_map.get(data)
    context.user_data['edit_field'] = field_key
    
    await query.edit_message_text(f"<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> <b>{prompt}</b>", parse_mode='HTML')
    return EDIT_PROD_VALUE

async def receive_edit_ai_desc_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle AI or manual choice for editing product description"""
    query = update.callback_query
    await safe_answer(query)
    prod_id = context.user_data.get('edit_prod_id')
    if not prod_id or prod_id not in products:
        await query.edit_message_text("âŒ Lá»—i dá»¯ liá»‡u. Vui lÃ²ng thá»­ láº¡i.")
        return ConversationHandler.END
    if query.data == 'ai_edit_desc_manual':
        context.user_data['edit_field'] = 'description'
        await query.edit_message_text("<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> Nháº­p <b>MÃ” Táº¢ Má»šI</b>:", parse_mode='HTML')
        return EDIT_PROD_VALUE
    elif query.data == 'ai_edit_desc_gen':
        p = products[prod_id]
        await query.edit_message_text("<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> Äang táº¡o mÃ´ táº£ báº±ng AI...")
        prompt = (f"Viáº¿t mÃ´ táº£ sáº£n pháº©m ngáº¯n gá»n 2-3 cÃ¢u cho shop Telegram tiáº¿ng Viá»‡t.\n"
                 f"TÃªn: {p['name']}\nGiÃ¡: {p['price']:,} VNÄ\n"
                 f"YÃªu cáº§u: ngáº¯n gá»n, háº¥p dáº«n, khÃ´ng quÃ¡ 150 kÃ½ tá»±. Chá»‰ viáº¿t mÃ´ táº£.")
        desc = await ask_ai(prompt, user_id=ADMIN_USER_ID)
        if not desc: desc = f"{p['name']} - Cháº¥t lÆ°á»£ng cao, giao hÃ ng tá»± Ä‘á»™ng."
        context.user_data['ai_edit_desc'] = desc
        safe_desc = html.escape(str(desc))
        keyboard = [
            [_btn("DÃ¹ng mÃ´ táº£ nÃ y", icon_id="5021905410089550576", callback_data="ai_edit_desc_accept")],
            [_btn("Táº¡o láº¡i", icon_id="5370715282044100355", callback_data="ai_edit_desc_gen")],
            [_btn("Tá»± viáº¿t", icon_id="5828072695694102691", callback_data="ai_edit_desc_manual")]
        ]
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"5303145396254563405\">ðŸ¤–</tg-emoji> <b>AI Ä‘á» xuáº¥t:</b>\n\n{safe_desc}\n\n<i>DÃ¹ng mÃ´ táº£ nÃ y khÃ´ng?</i>",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return EDIT_PROD_AI_DESC
    elif query.data == 'ai_edit_desc_accept':
        desc = context.user_data.get('ai_edit_desc', '')
        products[prod_id]['description'] = desc
        await save_data(force=True, tables=[PRODUCTS_FILE])
        safe_desc = html.escape(str(desc))
        await query.edit_message_text(
            f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>ÄÃ£ cáº­p nháº­t mÃ´ táº£ báº±ng AI!</b>\n\n{safe_desc}",
            parse_mode='HTML')
        context.user_data.pop('edit_prod_id', None)
        return ConversationHandler.END

async def edit_prod_receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    prod_id = context.user_data.get('edit_prod_id')
    field = context.user_data.get('edit_field')
    
    if not prod_id or prod_id not in products:
        await update.message.reply_text("âŒ Lá»—i dá»¯ liá»‡u. Vui lÃ²ng thá»­ láº¡i.")
        return ConversationHandler.END
    
    # Validate Price
    if field == 'price':
        try:
            full_price = int(text.replace('.', '').replace(',', ''))
            if full_price < 0: raise ValueError
            products[prod_id]['price'] = full_price
        except ValueError:
            await update.message.reply_text("âŒ GiÃ¡ khÃ´ng há»£p lá»‡. Vui lÃ²ng nháº­p sá»‘.")
            return EDIT_PROD_VALUE
    else:
        products[prod_id][field] = text
        
    await save_data(force=True, tables=[PRODUCTS_FILE])
    safe_product_name = html.escape(str(products[prod_id].get('name', prod_id)))
    safe_text = html.escape(str(text))
    
    await update.message.reply_text(
        f"<tg-emoji emoji-id=\"6269163801178804220\">âœ…</tg-emoji> <b>Cáº¬P NHáº¬T THÃ€NH CÃ”NG!</b>\n\n"
        f"Sáº£n pháº©m: {safe_product_name}\n"
        f"{field.capitalize()}: {safe_text}",
        parse_mode='HTML'
    )
    
    # Clear state
    context.user_data.pop('edit_prod_id', None)
    context.user_data.pop('edit_field', None)
    return ConversationHandler.END


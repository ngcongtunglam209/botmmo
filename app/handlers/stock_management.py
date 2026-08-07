# --- STOCK MANAGEMENT ---
async def view_stock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID: return
    
    query = update.callback_query
    if query:
        await query.answer()

    if not products:
        msg = "❌ Chưa có sản phẩm nào."
        if query: await query.edit_message_text(msg)
        else: await update.message.reply_text(msg)
        return ConversationHandler.END
        
    # Filter only local-stock products; source API/resell products do not have manual stock to manage.
    auto_products = {pid: p for pid, p in products.items() if _is_add_stock_local_product(p)}
    
    if not auto_products:
        msg = "❌ Không có sản phẩm Auto (Stock) nào."
        if query: await query.edit_message_text(msg)
        else: await update.message.reply_text(msg)
        return ConversationHandler.END
        
    keyboard = []
    for pid, p in auto_products.items():
        count = len(p.get('stock', []))
        keyboard.append([InlineKeyboardButton(f"{p['name']} ({count})", callback_data=f"view_stock_{pid}")])
        
    text = "<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>QUẢN LÝ KHO (STOCK)</b>\n<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> <i>Chọn sản phẩm để xem/xóa acc:</i>"
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    return STOCK_VIEW

async def view_stock_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    
    data = query.data
    
    # Handle Deletion Selection (from previous view)
    if data.startswith("del_stock_sel_"):
        # Ask which index to delete
        prod_id = data.replace("del_stock_sel_", "")
        context.user_data['del_stock_pid'] = prod_id
        await query.edit_message_text(
            "<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>XÓA STOCK</b>\n\n"
            "Vui lòng nhập <b>SỐ THỨ TỰ (Index)</b> của acc muốn xóa.\n"
            "(Số nằm trong ngoặc vuông [] ở danh sách trên)\n"
            "<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Hoặc gõ <b>all</b> để <b>XÓA TOÀN BỘ KHO</b>.\n\n"
            "<i>Gõ /cancel để hủy.</i>",
            parse_mode='HTML'
        )
        return STOCK_DELETE_SELECT

    prod_id = data.replace("view_stock_", "")
    if prod_id not in products:
        await query.edit_message_text("❌ Sản phẩm không tồn tại.")
        return ConversationHandler.END
        
    p = products[prod_id]
    stock = p.get('stock', [])
    
    if not stock:
        await query.edit_message_text(f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{p['name']}</b>: Kho trống!")
        return ConversationHandler.END
        
    # Show items (Limit 15 newest/top)
    msg = f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>KHO: {p['name']}</b> ({len(stock)} items)\n\n"
    limit = 15
    for i, item in enumerate(stock[:limit]):
        # Mask password or show full? user is admin so show full but truncated if too long
        display_item = item[:50] + "..." if len(item) > 50 else item
        msg += f"<b>[{i}]</b> <code>{display_item}</code>\n"
        
    if len(stock) > limit:
        msg += f"\n<i>... và {len(stock) - limit} items khác.</i>"
        
    keyboard = [
        [_btn("Xóa Account", icon_id="5217464097234241939", callback_data=f"del_stock_sel_{prod_id}")],
        [_btn("Quay lại", icon_id="6206032691075223572", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    return STOCK_VIEW

async def stock_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    prod_id = context.user_data.get('del_stock_pid')
    
    if not prod_id or prod_id not in products:
        await update.message.reply_text("❌ Lỗi phiên làm việc.")
        return ConversationHandler.END
        
    try:
        if text.lower() == 'all':
            async with global_stock_lock:
                stock_count = len(products[prod_id].get('stock', []))
                products[prod_id]['stock'] = []
                await save_data(force=True, tables=[PRODUCTS_FILE])
                
            await update.message.reply_text(
                f"{E_SUCCESS} <b>ĐÃ XÓA TOÀN BỘ STOCK</b>\n\n"
                f"{E_TAG} SP: {products[prod_id]['name']}\n"
                f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> Số lượng xóa: <b>{stock_count}</b> acc\n"
                f"{E_STAT} Còn lại: 0",
                parse_mode='HTML'
            )
            context.user_data.pop('del_stock_pid', None)
            return ConversationHandler.END

        index = int(text)
        
        async with global_stock_lock:
            stock = products[prod_id].get('stock', [])
            if index < 0 or index >= len(stock):
                await update.message.reply_text(f"❌ Index {index} không hợp lệ (0 - {len(stock)-1}).")
                return STOCK_DELETE_SELECT
                
            # Delete
            removed_item = stock.pop(index)
            products[prod_id]['stock'] = stock
            left_count = len(stock)
            await save_data(force=True, tables=[PRODUCTS_FILE])
        
        await update.message.reply_text(
            f"{E_SUCCESS} <b>ĐÃ XÓA THÀNH CÔNG</b>\n\n"
            f"{E_TAG} SP: {products[prod_id]['name']}\n"
            f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> Item: <code>{removed_item}</code>\n"
            f"{E_STAT} Còn lại: {left_count}",
            parse_mode='HTML'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập số nguyên hoặc 'all'.")
        return STOCK_DELETE_SELECT
        
    context.user_data.pop('del_stock_pid', None)
    return ConversationHandler.END

# ==============================================================================
#  GIVEAWAY WIZARD (CREATE GA)

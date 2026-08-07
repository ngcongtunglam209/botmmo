async def get_user_pending_order(user_id: int):
    for code, order in await pending_items_snapshot():
        if order.get('user_id') == user_id and order.get('status') == 'pending_payment':
            return code, order
    return None, None


def prepare_icloud_checkout_quote(user_id: int, coupon_code: str = None) -> dict:
    final_price = ICLOUD_PACKAGE_PRICE
    coupon_applied_text = ""
    coupon_notice_text = ""
    normalized_coupon = None

    raw_coupon = str(coupon_code or "").strip().upper()
    if raw_coupon:
        coupon_details = coupons.get(raw_coupon)
        if coupon_details:
            try:
                expires_at = datetime.strptime(
                    coupon_details.get('expires', '01-01-1970'),
                    '%d-%m-%Y'
                ).replace(hour=23, minute=59, second=59)
                is_expired = datetime.now() > expires_at
            except (ValueError, TypeError):
                is_expired = True

            is_used_up = (
                isinstance(coupon_details.get('quantity'), int)
                and coupon_details.get('used', 0) >= coupon_details.get('quantity')
            )

            if is_used_up or is_expired:
                coupon_notice_text = (
                    f"{E_LIMIT} Mã <b>{html.escape(raw_coupon)}</b> đã hết hạn hoặc hết lượt sử dụng.\n\n"
                )
            else:
                normalized_coupon = raw_coupon
                discount = coupon_details.get('discount', 0)
                if coupon_details.get('is_percent', False):
                    discount_amount = int(ICLOUD_PACKAGE_PRICE * discount / 100)
                    final_price = max(0, ICLOUD_PACKAGE_PRICE - discount_amount)
                    coupon_applied_text = (
                        f"{E_SUCCESS} Đã áp dụng coupon <b>{normalized_coupon}</b> "
                        f"(Giảm {discount}% = {discount_amount:,} VNĐ)\n\n"
                    )
                else:
                    final_price = max(0, ICLOUD_PACKAGE_PRICE - discount)
                    coupon_applied_text = (
                        f"{E_SUCCESS} Đã áp dụng coupon <b>{normalized_coupon}</b> "
                        f"(Giảm {discount:,} VNĐ)\n\n"
                    )
        else:
            coupon_notice_text = f"{E_LIMIT} Mã <b>{html.escape(raw_coupon)}</b> không hợp lệ.\n\n"

    user_record = user_data_db.setdefault(str(user_id), {})
    user_balance = int(user_record.get("balance", 0) or 0)
    balance_used = min(user_balance, final_price)
    amount_due = final_price - balance_used

    return {
        "base_price": ICLOUD_PACKAGE_PRICE,
        "final_price": final_price,
        "balance_used": balance_used,
        "amount_due": amount_due,
        "coupon_code": normalized_coupon,
        "coupon_applied_text": coupon_applied_text,
        "coupon_notice_text": coupon_notice_text,
        "user_balance": user_balance,
    }


async def show_icloud_payment_method_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email: str,
    coupon_code: str = None,
):
    quote = prepare_icloud_checkout_quote(update.effective_user.id, coupon_code)
    context.user_data['purchase_email'] = email
    context.user_data['purchase_coupon_code'] = quote.get("coupon_code")
    context.user_data['state'] = 'awaiting_icloud_payment_method'

    if quote["amount_due"] <= 0:
        await clear_user_state(context)
        await generate_icloud_payment_checkout(update, context, email, quote.get("coupon_code"), payment_provider="bank")
        return

    buttons = [
        [_btn("Ngân hàng (QR)", icon_id=BANK_BUTTON_ICON_ID, callback_data="icloud_pay_bank", style="success")]
    ]
    buttons.append([_btn("Hủy", icon_id="5273914604752216432", callback_data="back_to_main", style="danger")])

    balance_line = (
        f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Tự động trừ ví:</b> -{quote['balance_used']:,} VNĐ\n"
        if quote["balance_used"] > 0 else ""
    )
    method_text = (
        f"{quote['coupon_notice_text']}"
        f"{quote['coupon_applied_text']}"
        f"<b>Chọn phương thức thanh toán</b>\n\n"
        f"<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>Email:</b> <code>{html.escape(email)}</code>\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Gói:</b> iCloud 2TB\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Giá niêm yết:</b> {quote['base_price']:,} VNĐ\n"
        f"{balance_line}"
        f"<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> <b>Cần thanh toán:</b> {quote['amount_due']:,} VNĐ\n\n"
        "Bot sẽ tạo hóa đơn chuyển khoản QR cho phần thanh toán còn lại."
    )

    query = update.callback_query
    if query:
        await query.edit_message_text(
            method_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await context.bot.send_message(
            update.effective_user.id,
            method_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )


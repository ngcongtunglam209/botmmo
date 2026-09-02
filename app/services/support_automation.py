def handle_email_not_found(user_id: int | None = None) -> dict:
    """Auto-resolve: Can't find the order email -> spam check guide"""
    return {
        "message": t(
            "support_email_not_found_guide",
            user_id=user_id,
            globe=E_GLOBE,
            tip=E_TIP,
            loading=E_LOADING,
            limit=E_LIMIT,
        ),
        "action": "spam_check_guide"
    }

def handle_billing_questions(query: str, user_id: int | None = None) -> dict:
    """Auto-resolve: Billing questions → smart FAQ"""
    query_lower = query.lower()

    if any(word in query_lower for word in ["giá", "cost", "price", "bao nhiêu"]):
        message = t("support_billing_price", user_id=user_id, tag=E_TAG, loading=E_LOADING)
    elif any(word in query_lower for word in ["hoàn tiền", "refund", "trả lại"]):
        message = t("support_billing_refund", user_id=user_id, success=E_SUCCESS, limit=E_LIMIT)
    elif any(word in query_lower for word in ["chuyển khoản", "thanh toán", "payment"]):
        message = t(
            "support_billing_payment",
            user_id=user_id,
            tag=E_TAG,
            loading=E_LOADING,
            tip=E_TIP,
        )
    else:
        message = t("support_billing_general", user_id=user_id)

    return {"message": message, "action": "billing_faq"}

def automated_support_handler(query: str) -> str | None:
    """FIX BUG #23: Mở rộng knowledge base để cover nhiều câu hỏi hơn"""
    query_lower = query.lower()

    current_time = datetime.now()

    # Count active coupons
    active_coupons_count = 0
    active_coupons_list = []
    for code, details in list(coupons.items())[:5]:  # Top 5
        try:
            expires_str = details.get('expires')
            if expires_str:
                expiry_date = datetime.strptime(expires_str, '%d-%m-%Y')
                if expiry_date.date() >= current_time.date():
                    used = details.get('used', 0)
                    quantity = details.get('quantity', 999)
                    if used < quantity:
                        active_coupons_count += 1
                        discount = details.get('discount', 0)
                        active_coupons_list.append(f"• <code>{code}</code>: Giảm {discount:,}đ")
        except (TypeError, ValueError) as e:
            logger.debug(f"Skip invalid active coupon entry '{code}': {e}")

    NL = "\n"
    coupons_text = NL.join(active_coupons_list[:3])
    store_count = len([p for p in products.values() if len(p.get('stock', [])) > 0 or p.get('requires_gmail')])

    # Dynamic knowledge base với real-time data
    knowledge_base = {
        ("mã giảm giá", "giảm giá", "coupon", "khuyến mãi", "sale"):
            f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>MÃ GIẢM GIÁ HIỆN TẠI</b> ({current_time.strftime('%H:%M %d/%m/%Y')})\n\n" +
            (f"Hiện có <b>{active_coupons_count} mã</b> đang active:\n{coupons_text}"
             f"\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <i>Dùng /start để mua hàng và nhập mã khi thanh toán!</i>" if active_coupons_count > 0
             else "Hiện tại chưa có mã giảm giá nào. <tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji>\n\nNhưng giá đã rẻ lắm rồi! Gõ /start để mua ngay nhé! <tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji>"),

        ("không nhận được mail", "chưa nhận mail", "kiểm tra mail", "không có mail"):
            "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>VỀ EMAIL ĐƠN HÀNG:</b>\n\nThông tin tài khoản được gửi <b>ngay trong Telegram</b> sau khi thanh toán thành công (< 3 phút).\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Nếu đơn cần email, vui lòng kiểm tra:\n• Hộp thư đến\n• Thư mục <b>Spam/Thư rác</b> (rất quan trọng!)\n• Tìm từ khóa 'Lâm Shop'\n\nNếu vẫn không thấy sau 10 phút, dùng /start → Báo lỗi để được hỗ trợ!",

        ("thanh toán", "chuyển khoản", "chuyển sai", "bank", "qr"):
            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>VỀ THANH TOÁN:</b> ({current_time.strftime('%H:%M %d/%m')})\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Tự động duyệt nếu:\n• Chuyển khoản ĐÚNG SỐ TIỀN\n• Nội dung ĐÚNG MÃ ĐƠN\n• Trong vòng 30 phút\n\n<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Thời gian xử lý:\n• Bot scan bank mỗi {BANK_CHECK_INTERVAL_SECONDS} giây\n• Tự động gửi hàng sau 1-3 phút\n\n❌ Nếu chuyển sai:\n• QR hết hạn sau 30 phút\n• Liên hệ Admin với mã đơn để xử lý thủ công",

        ("giá", "bao nhiêu", "giá cả", "price"):
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>BẢNG GIÁ:</b> ({current_time.strftime('%d/%m/%Y')})\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> Mỗi sản phẩm có giá riêng.\nGõ /start → 'Cửa hàng' để xem toàn bộ giá!\n\n<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> Có mã giảm giá không? Dùng được luôn khi thanh toán! ⭐️",

        ("bao lâu", "mất bao lâu", "thời gian", "nhanh không"):
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>THỜI GIAN XỬ LÝ:</b>\n\n<b>Sản phẩm AUTO:</b>\n• Thanh toán → Nhận ngay trong Telegram (< 1 phút) <tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji>\n\n<b>Sản phẩm MANUAL:</b>\n• Thanh toán → Admin xử lý trong 1-30 phút\n• Tùy thuộc vào số đơn đang chờ\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Hiện tại ({current_time.strftime('%H:%M')}): {len(pending_manual_orders)} đơn manual đang chờ",

        ("còn hàng", "stock", "hết hàng", "available"):
            f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>TÌNH TRẠNG KHO:</b> ({current_time.strftime('%H:%M %d/%m')})\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> Đang bán: {store_count} sản phẩm\n\nGõ /start để xem chi tiết và mua ngay! <tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji>"
    }

    for keywords, answer in knowledge_base.items():
        if any(keyword in query_lower for keyword in keywords):
            return answer
    return None

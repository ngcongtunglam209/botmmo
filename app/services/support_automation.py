def handle_email_not_found() -> dict:
    """Auto-resolve: Can't find the order email -> spam check guide"""
    return {
        "message": (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN TÌM EMAIL ĐƠN HÀNG</b>\n\n"
            f"{E_GLOBE} <b>Bước 1:</b> Kiểm tra hộp thư đến chính\n"
            f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>Bước 2:</b> Kiểm tra thư mục <b>Spam/Thư rác</b>\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Bước 3:</b> Kiểm tra các thư mục khác: Promotions, Social\n"
            f"{E_TIP} <b>Bước 4:</b> Tìm kiếm với từ khóa <code>Lâm Shop</code>\n\n"
            f"<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>Trên Gmail Mobile:</b>\n"
            f"• Mở Gmail → Chạm 3 gạch ngang → Spam\n"
            f"• Nếu tìm thấy → Đánh dấu 'Không phải spam'\n\n"
            f"{E_LOADING} <b>Thông tin tài khoản cũng luôn được gửi ngay trong Telegram</b>\n\n"
            f"{E_LIMIT} <b>Nếu vẫn không tìm thấy:</b> Bấm nút bên dưới để được hỗ trợ"
        ),
        "action": "spam_check_guide"
    }

def handle_billing_questions(query: str) -> dict:
    """Auto-resolve: Billing questions → smart FAQ"""
    query_lower = query.lower()

    if any(word in query_lower for word in ["giá", "cost", "price", "bao nhiêu"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>THÔNG TIN GIÁ CẢ</b>\n\n"
            f"{E_TAG} Mỗi sản phẩm có giá riêng, xem trực tiếp trong cửa hàng.\n"
            f"{E_LOADING} Gõ /start → <b>Cửa hàng</b> để xem giá mới nhất.\n\n"
            f"{E_TAG} <b>Ưu đãi hiện tại:</b>\n"
            f"• Giao hàng tự động 24/7\n"
            f"• Bảo hành theo từng sản phẩm\n"
            f"• Hỗ trợ 24/7"
        )
    elif any(word in query_lower for word in ["hoàn tiền", "refund", "trả lại"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>CHÍNH SÁCH HOÀN TIỀN</b>\n\n"
            f"{E_SUCCESS} <b>Điều kiện hoàn tiền:</b>\n"
            f"• Trong thời hạn bảo hành của sản phẩm\n"
            f"• Lỗi từ phía chúng tôi\n"
            f"• Tài khoản không dùng được sau nhiều lần khắc phục\n\n"
            f"{E_LIMIT} <b>Không hoàn tiền nếu:</b>\n"
            f"• Tự ý đổi mật khẩu hoặc email khôi phục\n"
            f"• Chia sẻ tài khoản cho nhiều người\n"
            f"• Vi phạm điều khoản của nền tảng\n\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Quy trình hoàn tiền:</b>\n"
            f"1. Liên hệ Admin với mã đơn hàng\n"
            f"2. Admin kiểm tra và xác nhận\n"
            f"3. Hoàn tiền trong 1-3 ngày làm việc"
        )
    elif any(word in query_lower for word in ["chuyển khoản", "thanh toán", "payment"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN THANH TOÁN</b>\n\n"
            f"{E_TAG} <b>Phương thức hiện tại:</b>\n"
            f"• Chuyển khoản ngân hàng\n"
            f"• Quét mã QR (nhanh nhất)\n"
            f"• Số dư ví trong bot\n\n"
            f"{E_LOADING} <b>Quy trình:</b>\n"
            f"1. Gõ /start → Cửa hàng → chọn sản phẩm\n"
            f"2. Chọn số lượng và phương thức thanh toán\n"
            f"3. Quét QR hoặc chuyển khoản thủ công\n"
            f"4. Bot tự động giao hàng sau 1-3 phút\n\n"
            f"{E_TIP} <b>Lưu ý quan trọng:</b>\n"
            f"• Chuyển đúng số tiền và nội dung\n"
            f"• Đơn hàng tự hủy sau 10 phút nếu không thanh toán"
        )
    else:
        message = (
            "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HỖ TRỢ BILLING TỔNG QUÁT</b>\n\n"
            '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Giá:</b> Xem trực tiếp từng sản phẩm trong cửa hàng\n'
            '<tg-emoji emoji-id="5458774648621643551">💳</tg-emoji> <b>Thanh toán:</b> Chuyển khoản, QR hoặc số dư ví\n'
            "<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>Hoàn tiền:</b> Trong thời hạn bảo hành nếu lỗi từ chúng tôi\n"
            "<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> <b>Hỗ trợ:</b> 24/7 qua bot và admin\n\n"
            "<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> <b>Câu hỏi cụ thể khác?</b>\n"
            "Hãy mô tả chi tiết vấn đề của bạn để được hỗ trợ tốt nhất!"
        )

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

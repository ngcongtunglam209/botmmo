
async def handle_link_not_working(user_id: int) -> dict:
    """Auto-resolve: Link not working → auto resend"""
    # Tìm đơn hàng gần nhất của user
    user_orders = [o for o in reversed(user_order_index.get(str(user_id), [])) if "Hoàn thành" in status_text(o.get("status"))]
    
    if user_orders:
        latest_order = user_orders[0]
        email = latest_order.get("email")
        order_code = latest_order.get("order_code")
        
        if available_links:
            new_link = next(iter(available_links))
            
            # Gửi lại email
            try:
                # Kiểm tra link trước khi gửi
                if not await validate_activation_link(new_link):
                    logger.warning(f"Link không hợp lệ: {new_link}")
                    # Bỏ qua link không hợp lệ
                    async with global_stock_lock:
                        if new_link in available_links:
                            available_links.remove(new_link)
                    return None

                # Gửi email với link mới
                await send_activation_email_async(
                    email, f"[Auto-Support] Link kích hoạt mới - {order_code}", 
                    latest_order.get("full_name", "bạn"), new_link
                )
                
                # Update order history
                latest_order.update({'link': new_link, 'status': OrderStatus.COMPLETED_RESENT.value})
                await save_data()
                
                return {
                    "message": (
                        f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>ĐÃ TỰ ĐỘNG XỬ LÝ!</b>\n\n"
                        f"{E_SUCCESS} Đã gửi lại link kích hoạt mới đến email <b>{email}</b>\n\n"
                        f"{E_GLOBE} Vui lòng kiểm tra hộp thư (kể cả thư mục spam)\n"
                        f"{E_LOADING} Link mới sẽ có trong vòng 2-3 phút\n\n"
                        f"{E_TIP} <b>Nếu vẫn gặp vấn đề:</b> Vui lòng liên hệ Admin để được hỗ trợ thủ công."
                    ),
                    "action": "auto_resend_link"
                }
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Lỗi auto-resend link: {e}")
                return None
        else:
            return {
                "message": (
                    f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>ĐÃ PHÁT HIỆN VẤN ĐỀ!</b>\n\n"
                    f"{E_LIMIT} Hệ thống hiện đang tạm hết link thay thế\n"
                    f"<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> Đã tự động thông báo Admin để bổ sung link\n"
                    f"{E_LOADING} Admin sẽ xử lý trong vòng 30 phút\n\n"
                    f"{E_TAG} <b>Bồi thường:</b> Bạn sẽ được ưu tiên và nhận thêm 1 tháng miễn phí"
                ),
                "action": "auto_escalate_no_links"
            }
    else:
        return {
            "message": (
                "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>CẦN THÊM THÔNG TIN!</b>\n\n"
                "<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> Không tìm thấy đơn hàng của bạn trong hệ thống\n"
                "<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> Vui lòng cung cấp <b>mã đơn hàng</b> (VD: ICLD123456) để được hỗ trợ nhanh chóng\n\n"
                "<tg-emoji emoji-id=\"6129860303619363484\">💬</tg-emoji> Hoặc liên hệ Admin với thông tin:\n"
                "• Email đã dùng để mua\n"
                "• Thời gian mua gần đúng"
            ),
            "action": "request_order_info"
        }

def handle_email_not_found() -> dict:
    """Auto-resolve: Can't find email → spam check guide"""
    return {
        "message": (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN TÌM EMAIL KÍCH HOẠT</b>\n\n"
            f"{E_GLOBE} <b>Bước 1:</b> Kiểm tra hộp thư đến chính\n"
            f"<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>Bước 2:</b> Kiểm tra thư mục <b>Spam/Thư rác</b>\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Bước 3:</b> Kiểm tra các thư mục khác: Promotions, Social\n"
            f"{E_TIP} <b>Bước 4:</b> Tìm kiếm với từ khóa <code>DinoTools</code> hoặc <code>iCloud</code>\n\n"
            f"<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>Trên Gmail Mobile:</b>\n"
            f"• Mở Gmail → Chạm 3 gạch ngang → Spam\n"
            f"• Nếu tìm thấy → Đánh dấu 'Không phải spam'\n\n"
            f"{E_LOADING} <b>Email thường đến trong vòng 1-5 phút sau thanh toán</b>\n\n"
            f"{E_LIMIT} <b>Nếu vẫn không tìm thấy:</b> Bấm nút bên dưới để được hỗ trợ"
        ),
        "action": "spam_check_guide"
    }

def handle_icloud_tutorial() -> dict:
    """Auto-resolve: How to use iCloud → interactive tutorial"""
    return {
        "message": (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN SỬ DỤNG ICLOUD 2TB</b>\n\n"
            f"<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>BƯỚC 1: KÍCH HOẠT (SAU KHI NHẬN EMAIL)</b>\n"
            f"• Bấm vào link trong email\n"
            f"• Chọn <b>'Accept'</b> hoặc <b>'Chấp nhận'</b>\n"
            f"• Đăng nhập Apple ID của bạn\n\n"
            f"{E_STAT} <b>BƯỚC 2: KIỂM TRA DUNG LƯỢNG</b>\n"
            f"• iPhone: Cài đặt → Tên của bạn → iCloud\n"
            f"• Mac: Apple Menu → System Settings → Apple ID → iCloud\n"
            f"• Sẽ hiển thị <b>2TB available</b>\n\n"
            f"<tg-emoji emoji-id=\"5231489647946768652\">☁️</tg-emoji> <b>BƯỚC 3: BẬT ĐỒNG BỘ</b>\n"
            f"• Photos (Ảnh)\n"
            f"• iCloud Drive\n"
            f"• Backup\n"
            f"• Contacts, Calendar, Notes\n\n"
            f"{E_TIP} <b>MẸO HAY:</b>\n"
            f"• Bật 'Optimize iPhone Storage' để tiết kiệm bộ nhớ\n"
            f"• Thiết lập Auto Backup hàng đêm\n"
            f"• Chia sẻ folder với gia đình qua iCloud Drive"
        ),
        "action": "icloud_tutorial"
    }

def handle_billing_questions(query: str) -> dict:
    """Auto-resolve: Billing questions → smart FAQ"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["giá", "cost", "price", "bao nhiêu"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>THÔNG TIN GIÁ CẢ</b>\n\n"
            f"{E_TAG} <b>Gói iCloud 2TB:</b> {ICLOUD_PACKAGE_PRICE:,} VNĐ\n"
            f"{E_LOADING} <b>Thời gian:</b> Vĩnh viễn (không hết hạn)\n"
            f"{E_TAG} <b>So sánh Apple chính hãng:</b>\n"
            f"• Apple: 70,000 VNĐ/tháng = 840,000 VNĐ/năm\n"
            f"• DinoTools: {ICLOUD_PACKAGE_PRICE:,} VNĐ một lần\n"
            f"• <b>Tiết kiệm: {840000 - ICLOUD_PACKAGE_PRICE:,} VNĐ/năm</b>\n\n"
            f"{E_TAG} <b>Ưu đãi hiện tại:</b>\n"
            f"• Miễn phí setup\n"
            f"• Bảo hành 20 ngày\n"
            f"• Hỗ trợ 24/7"
        )
    elif any(word in query_lower for word in ["hoàn tiền", "refund", "trả lại"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>CHÍNH SÁCH HOÀN TIỀN</b>\n\n"
            f"{E_SUCCESS} <b>Điều kiện hoàn tiền:</b>\n"
            f"• Trong vòng 20 ngày từ khi mua\n"
            f"• Lỗi từ phía chúng tôi\n"
            f"• Link không hoạt động sau nhiều lần khắc phục\n\n"
            f"{E_LIMIT} <b>Không hoàn tiền nếu:</b>\n"
            f"• Tự ý rời khỏi Family Sharing\n"
            f"• Apple ID bị khóa/vô hiệu hóa\n"
            f"• Đã sử dụng thành công > 20 ngày\n\n"
            f"<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Quy trình hoàn tiền:</b>\n"
            f"1. Liên hệ Admin với mã đơn hàng\n"
            f"2. Admin kiểm tra và xác nhận\n"
            f"3. Hoàn tiền trong 1-3 ngày làm việc"
        )
    elif any(word in query_lower for word in ["chuyển khoản", "thanh toán", "payment"]):
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN THANH TOÁN</b>\n\n"
            f"{E_TAG} <b>Phương thức hiện tại:</b>\n"
            f"• Chuyển khoản ngân hàng (VCB)\n"
            f"• Quét mã QR (nhanh nhất)\n\n"
            f"{E_LOADING} <b>Quy trình:</b>\n"
            f"1. Chọn 'Mua gói iCloud'\n"
            f"2. Nhập email nhận link\n"
            f"3. Quét QR hoặc chuyển khoản thủ công\n"
            f"4. Bấm 'Đã chuyển khoản'\n"
            f"5. Nhận link qua email trong 1-3 phút\n\n"
            f"{E_TIP} <b>Lưu ý quan trọng:</b>\n"
            f"• Chuyển đúng số tiền và nội dung\n"
            f"• Đơn hàng tự hủy sau 15 phút nếu không thanh toán"
        )
    else:
        message = (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HỖ TRỢ BILLING TỔNG QUÁT</b>\n\n"
            f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> <b>Giá:</b> {ICLOUD_PACKAGE_PRICE:,} VNĐ một lần, vĩnh viễn\n'
            f'<tg-emoji emoji-id="5458774648621643551">💳</tg-emoji> <b>Thanh toán:</b> Chuyển khoản VCB hoặc QR\n'
            f"<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>Hoàn tiền:</b> Trong 20 ngày nếu lỗi từ chúng tôi\n"
            f"<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> <b>Hỗ trợ:</b> 24/7 qua bot và admin\n\n"
            f"<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> <b>Câu hỏi cụ thể khác?</b>\n"
            f"Hãy mô tả chi tiết vấn đề của bạn để được hỗ trợ tốt nhất!"
        )
    
    return {"message": message, "action": "billing_faq"}

def handle_privacy_concerns() -> dict:
    """Auto-resolve: Privacy concerns"""
    return {
        "message": (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>BẢO MẬT & QUYỀN RIÊNG TƯ</b>\n\n"
            f"{E_LOCK} <b>Apple Family Sharing hoàn toàn riêng tư:</b>\n"
            f"• Chỉ chia sẻ dung lượng lưu trữ\n"
            f"• KHÔNG chia sẻ nội dung, ảnh, tệp\n"
            f"• KHÔNG ai có thể xem dữ liệu của bạn\n"
            f"• Mỗi thành viên có iCloud riêng biệt\n\n"
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo mật Apple:</b>\n"
            f"• End-to-end encryption\n"
            f"• Two-factor authentication\n"
            f"• Zero-knowledge architecture\n"
            f"• Tuân thủ GDPR và các chuẩn bảo mật quốc tế\n\n"
            f"{E_SUCCESS} <b>Điều chúng tôi có thể thấy:</b>\n"
            f"• Email bạn đăng ký\n"
            f"• Thống kê dung lượng sử dụng\n"
            f"• Trạng thái kích hoạt\n\n"
            f"{E_LIMIT} <b>Điều chúng tôi KHÔNG thể thấy:</b>\n"
            f"• Ảnh, video, tài liệu của bạn\n"
            f"• Contacts, lịch, ghi chú\n"
            f"• Mật khẩu, thông tin cá nhân\n"
            f"• Vị trí hoặc hoạt động của bạn"
        ),
        "action": "privacy_explanation"
    }

def handle_family_sharing() -> dict:
    """Auto-resolve: Family sharing issues"""
    return {
        "message": (
            f"<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>FAMILY SHARING - HƯỚNG DẪN QUAN TRỌNG</b>\n\n"
            f"{E_ERROR} <b>CẢNH BÁO:</b> KHÔNG TỰ Ý THOÁT KHỎI NHÓM!\n\n"
            f"{E_LIMIT} <b>Nếu bạn rời Family Sharing:</b>\n"
            f"• Dung lượng 2TB sẽ mất ngay lập tức\n"
            f"• Trở về 5GB miễn phí của Apple\n"
            f"• Dữ liệu không mất nhưng không sync được\n"
            f"• Phải mua lại để tiếp tục sử dụng\n\n"
            f"{E_SUCCESS} <b>Cách sử dụng an toàn:</b>\n"
            f"• Chỉ sử dụng, KHÔNG tùy chỉnh cài đặt Family\n"
            f"• KHÔNG mời thêm người vào nhóm\n"
            f"• KHÔNG thay đổi payment method\n"
            f"• KHÔNG rời khỏi nhóm vì bất kỳ lý do gì\n\n"
            f"<tg-emoji emoji-id=\"6301027265899661025\">🆘</tg-emoji> <b>Nếu đã thoát nhầm:</b>\n"
            f"• Liên hệ Admin ngay lập tức\n"
            f"• Cung cấp email và mã đơn hàng\n"
            f"• Admin sẽ mời lại (nếu còn slot)\n"
            f"• Có thể mất phí tái kích hoạt\n\n"
            f"{E_TIP} <b>Lưu ý:</b> Family Sharing chỉ là cách Apple chia sẻ dung lượng, hoàn toàn an toàn!"
        ),
        "action": "family_sharing_guide"
    }

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
    icloud_status = '<tg-emoji emoji-id="6269163801178804220">✅</tg-emoji> Còn link' if available_links else '❌ Tạm hết'
    store_count = len([p for p in products.values() if len(p.get('stock', [])) > 0 or p.get('requires_gmail')])
    
    # Dynamic knowledge base với real-time data
    knowledge_base = {
        ("mã giảm giá", "giảm giá", "coupon", "khuyến mãi", "sale"):
            f"<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> <b>MÃ GIẢM GIÁ HIỆN TẠI</b> ({current_time.strftime('%H:%M %d/%m/%Y')})\n\n" + 
            (f"Hiện có <b>{active_coupons_count} mã</b> đang active:\n{coupons_text}"
             f"\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <i>Dùng /start để mua hàng và nhập mã khi thanh toán!</i>" if active_coupons_count > 0 
             else "Hiện tại chưa có mã giảm giá nào. <tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji>\n\nNhưng giá đã rẻ lắm rồi! Gõ /start để mua ngay nhé! <tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji>"),
        
        ("không nhận được mail", "chưa nhận mail", "kiểm tra mail", "không có mail"):
            "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> <b>VỀ EMAIL KÍCH HOẠT:</b>\n\nLink kích hoạt được gửi <b>ngay lập tức</b> sau khi thanh toán thành công (< 3 phút).\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Vui lòng kiểm tra:\n• Hộp thư đến\n• Thư mục <b>Spam/Thư rác</b> (rất quan trọng!)\n• Tìm từ khóa 'iCloud' hoặc 'DinoTools'\n\nNếu vẫn không thấy sau 10 phút, dùng /start → Báo lỗi để được hỗ trợ!",
        
        ("riêng tư", "thấy ảnh", "xem dữ liệu", "bảo mật", "an toàn"):
            "🔐 <b>VỀ BẢO MẬT & RIÊNG TƯ:</b>\n\nFamily Sharing <b>HOÀN TOÀN RIÊNG TƯ</b>! <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>\n\n• Không ai xem được ảnh của bạn\n• Không ai xem được file của bạn\n• Không ai truy cập được iCloud của bạn\n• Apple bảo mật tuyệt đối\n\nFamily Sharing chỉ chia sẻ <b>DUNG LƯỢNG</b>, không chia sẻ dữ liệu!",
        
        ("rời nhóm", "tự thoát", "out group", "leave"):
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>CẢNH BÁO: KHÔNG THOÁT FAMILY!</b>\n\n❌ Nếu rời nhóm:\n• Mất 2TB ngay lập tức\n• Trở về 5GB miễn phí\n• Dữ liệu không mất nhưng không sync\n• Phải mua lại để dùng tiếp\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Cách dùng đúng:\n• Cứ để yên, đừng động gì\n• Không tùy chỉnh Family settings\n• Không mời người khác\n\nĐã thoát nhầm? Liên hệ Admin ngay!",
        
        ("thanh toán", "chuyển khoản", "chuyển sai", "bank", "qr"):
            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>VỀ THANH TOÁN:</b> ({current_time.strftime('%H:%M %d/%m')})\n\n<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Tự động duyệt nếu:\n• Chuyển khoản ĐÚNG SỐ TIỀN\n• Nội dung ĐÚNG MÃ ĐƠN (VD: ICLD123456)\n• Trong vòng 30 phút\n\n<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Thời gian xử lý:\n• Bot scan bank mỗi {BANK_CHECK_INTERVAL_SECONDS} giây\n• Tự động gửi hàng sau 1-3 phút\n\n❌ Nếu chuyển sai:\n• QR hết hạn sau 30 phút\n• Liên hệ Admin với mã đơn để xử lý thủ công",
        
        ("giá", "bao nhiêu", "giá cả", "price"):
            f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>BẢNG GIÁ:</b> ({current_time.strftime('%d/%m/%Y')})\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Gói iCloud 2TB:</b> {ICLOUD_PACKAGE_PRICE:,}đ (vĩnh viễn)\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> <b>Sản phẩm khác:</b>\nGõ /start → 'Cửa hàng khác' để xem!\n\n<tg-emoji emoji-id=\"5377624166436445368\">🎟️</tg-emoji> Có mã giảm giá không? Dùng được luôn khi thanh toán! ⭐️",
        
        ("bao lâu", "mất bao lâu", "thời gian", "nhanh không"):
            f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>THỜI GIAN XỬ LÝ:</b>\n\n<b>Gói iCloud 2TB (AUTO):</b>\n• Thanh toán → 1-3 phút → Nhận link qua email <tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji>\n\n<b>Sản phẩm AUTO khác:</b>\n• Thanh toán → Nhận ngay trong Telegram (< 1 phút) <tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji>\n\n<b>Sản phẩm MANUAL:</b>\n• Thanh toán → Admin xử lý trong 1-30 phút\n• Tùy thuộc vào số đơn đang chờ\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Hiện tại ({current_time.strftime('%H:%M')}): {len(pending_manual_orders)} đơn manual đang chờ",
        
        ("còn hàng", "stock", "hết hàng", "available"):
            f"<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>TÌNH TRẠNG KHO:</b> ({current_time.strftime('%H:%M %d/%m')})\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> iCloud 2TB: {icloud_status}\n<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> Sản phẩm khác: {store_count} sản phẩm đang bán\n\nGõ /start để xem chi tiết và mua ngay! <tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji>"
    }
    
    for keywords, answer in knowledge_base.items():
        if any(keyword in query_lower for keyword in keywords):
            return answer
    return None


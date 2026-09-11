SUPPORTED_LANGS = ("vi", "en", "zh")
DEFAULT_LANG = "vi"

_LANG_ALIASES = {
    "vi": "vi",
    "vn": "vi",
    "vie": "vi",
    "vietnamese": "vi",
    "en": "en",
    "eng": "en",
    "english": "en",
    "zh": "zh",
    "cn": "zh",
    "zh-cn": "zh",
    "zh_cn": "zh",
    "chinese": "zh",
    "中文": "zh",
}

STRINGS = {
    "vi": {
        "main_menu_title": (
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> <b>HỆ THỐNG DỊCH VỤ MMO CAO CẤP</b> '
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji>\n'
            "━━━━━━━━━━━━━━━━━━\n"
            '<blockquote><tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Uy tín - Nhanh gọn - Chuyên nghiệp</b>\n'
            '<tg-emoji emoji-id="5303290914041505430">⚡️</tg-emoji> Hệ thống giao hàng tự động 24/7.</blockquote>\n\n'
            "{success} <i>Lựa chọn dịch vụ bên dưới để bắt đầu:</i>"
        ),
        "hello": "Xin chào {name}!",
        "rank_balance": "Hạng: {rank} | Số dư: {balance}",
        "rank_label": "Đồng",
        "rank_name_bronze": "Đồng",
        "rank_name_silver": "Bạc",
        "rank_name_gold": "Vàng",
        "rank_name_diamond": "Kim Cương",
        "rank_name_master": "Cao Thủ",
        "btn_shop": "Mua Hàng",
        "btn_purchased": "Đã Mua",
        "btn_game": "Game",
        "btn_earn": "Kiếm Tiền",
        "btn_wallet": "Tài Khoản & Số Dư",
        "btn_guide": "HD & CS",
        "btn_support": "Hỗ Trợ & Liên Hệ",
        "btn_report": "Báo Lỗi",
        "btn_community": "Nhóm Cộng Đồng",
        "btn_api_partner": "API Partner",
        "btn_api_topup": "Nạp Ví",
        "btn_api_register": "Đăng Ký API",
        "btn_api_guide": "HD API",
        "btn_admin": "Bảng Điều Khiển Admin",
        "btn_admin_web": "WebApp API Admin",
        "btn_language": "Ngôn ngữ / Language",
        "btn_wheel": "Vòng Quay",
        "btn_dice": "Xúc Xắc",
        "btn_back_main": "Quay Lại Menu Chính",
        "games_title": (
            '<tg-emoji emoji-id="5226711870492126219">🎮</tg-emoji> <b>TRUNG TÂM GAME</b>\n'
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Chọn game bạn muốn chơi bên dưới:"
        ),
        "lang_menu_title": (
            "🌐 <b>CHỌN NGÔN NGỮ / LANGUAGE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Ngôn ngữ hiện tại: <b>{current}</b>\n"
            "Chọn ngôn ngữ bên dưới:"
        ),
        "btn_back": "Quay lại",
        "lang_changed": "✅ Đã đổi ngôn ngữ sang <b>{lang}</b>.",
        "lang_name_vi": "Tiếng Việt",
        "lang_name_en": "English",
        "lang_name_zh": "中文",
        "maintenance": "🛠️ <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n\nHệ thống đang được nâng cấp. Vui lòng quay lại sau ít phút.\n\nXin lỗi vì sự bất tiện này!",
        "sys_unexpected_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.",
        "sys_rate_limited": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Vui lòng chờ {seconds}s trước khi dùng lại lệnh này.",
        "sys_banned": "{limit} Bạn đã bị cấm sử dụng bot này. Vui lòng liên hệ Admin.",
        "verify_title": "XÁC MINH NHANH",
        "verify_prompt": "Trả lời phép tính đơn giản này để bắt đầu dùng bot:",
        "verify_example": "Ví dụ: nếu là <code>1 + 2</code> thì gửi <code>3</code>.",
        "verify_number_only": "Vui lòng chỉ gửi đáp án bằng số.",
        "verify_wrong": "Sai rồi, thử lại nhé.",
        "verify_success": "XÁC MINH THÀNH CÔNG!",
        "verify_referral_saved": "Đã ghi nhận mã giới thiệu.",
        "opening_main_menu": "Đang mở menu chính...",
        "already_verified": "BẠN ĐÃ XÁC MINH RỒI.",
        "use_start": "Dùng <code>/start</code> để mở bot.",
        "cancelled": "Đã hủy hành động. Quay về menu chính.",
        "ai_fallback": "Xin lỗi, mình đang hơi bận! 🤖\n\nBạn có thể:\n• Gõ /start để xem menu\n• Hoặc liên hệ admin để được hỗ trợ ngay",
        "live_chat_title": "LIVE CHAT VỚI ADMIN",
        "live_chat_you": "Bạn",
        "live_chat_admin": "Admin",
        "live_chat_empty": "Chưa có tin nhắn. Hãy gửi câu hỏi của bạn!",
        "live_chat_prompt": "Gửi tin nhắn để chat với Admin...",
        "live_chat_close": "Đóng chat",
        "live_chat_closed": "Chat đã đóng. Cảm ơn bạn!",
        "value_none": "Không",
        "value_customer": "Khách hàng",
        "btn_new_order": "Tạo đơn mới",
        "order_expired_refund_note": "\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>Đã hoàn lại:</b> +{amount} vào ví (do đơn hết hạn).",
        "order_expired_store": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\nĐơn hàng này đã hết hạn thanh toán.\nVui lòng tạo đơn mới nếu bạn vẫn muốn mua.{refund}",
        "order_expired_email": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\nĐơn hàng cho email <b>{email}</b> đã hết hạn thanh toán.\nVui lòng tạo đơn mới nếu bạn vẫn muốn mua.{refund}",
        "order_product_unavailable": "{error} <b>XIN LỖI - SẢN PHẨM KHÔNG KHẢ DỤNG</b>\n\nSản phẩm bạn đặt (Mã: <code>{prod_id}</code>) hiện không còn khả dụng.\n\n{tag} <b>Số tiền CK:</b> {paid}\n{tag} <b>Đã hoàn ví:</b> +{refunded}\n{tag} <b>Mã đơn:</b> <code>{order_code}</code>\n\nToàn bộ tiền đã được hoàn vào Ví Bot.\nKhoản hoàn từ {min_bank} sẽ có thêm lựa chọn nhận qua ngân hàng.",
        "order_paid_manual": "{success} <b>THANH TOÁN THÀNH CÔNG!</b>\n\n{tag} <b>Sản phẩm:</b> {product}\n<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Số lượng:</b> {qty}\n{tag} <b>Đã thanh toán:</b> {amount}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n{globe} <b>Vui lòng nhập email nhận dịch vụ:</b>\n<i>Email này sẽ được dùng để Admin setup/gửi thông tin cho bạn</i>\n\n<b>Cách gửi email:</b>\n• Reply tin nhắn này với email của bạn\n• Hoặc dùng lệnh: <code>/guimail email@abc.com</code>",
        "order_soldout_refunded": "❌ <b>RẤT TIẾC!</b>\n\nSản phẩm <b>{product}</b> vừa được mua hết bởi khách khác.\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Đơn hàng đã được hoàn tiền tự động: <b>+{refund}</b>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư mới: <b>{balance}</b>",
        "order_paid_auto": "{success} <b>THANH TOÁN THÀNH CÔNG</b>\n\n{tag} <b>Sản phẩm:</b> {product}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Số lượng:</b> {qty}\n{tag} <b>Thanh toán:</b> {amount}\n{loading} <b>Thời hạn:</b> {duration}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo hành:</b> {warranty}\n\n{tip} <b>Hệ thống đang gửi thông tin tài khoản ngay sau tin nhắn này...</b>",
        "reward_period_weekly": "TUẦN QUA",
        "reward_period_monthly": "THÁNG QUA",
        "reward_top_buyer": "⭐️ <b>CHÚC MỪNG TOP 1 NGƯỜI MUA HÀNG {period}!</b> ⭐️\n<i>({range})</i>\n\nXin chào <b>{name}</b>,\nBạn là người mua hàng nhiều nhất kỳ vừa qua với <b>{count} đơn hàng</b>.\n\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Phần thưởng của bạn:</b>\n<b>{quantity}x Mã giảm giá {percent}%</b>\n\n",
        "reward_coupon_footer": "\n<i>(Hạn sử dụng: 30 ngày. Áp dụng cho đơn hàng tiếp theo)</i>",
        "order_manual_completed": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐƠN HÀNG ĐÃ HOÀN THÀNH!</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\nCảm ơn bạn đã sử dụng dịch vụ! <tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>",
        "order_cancelled_refunded": "❌ <b>ĐƠN HÀNG ĐÃ BỊ HỦY</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Sản phẩm:</b> {product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Đã hoàn tiền:</b> {refund}\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Số dư mới:</b> {balance}",
        "order_refunded_by_admin": "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>ĐƠN HÀNG ĐÃ ĐƯỢC HOÀN TIỀN</b>\n\n<tg-emoji emoji-id=\"6260059243605398502\">🔖</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n{tag} <b>Hoàn lại:</b> {refund}\n{tag} <b>Số dư mới:</b> {balance}\n\n<i>Admin đã hoàn tiền do gặp vấn đề kỹ thuật.</i>",
        "order_approved_out_of_stock": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ DUYỆT ĐƠN HÀNG</b>\n\nTuy nhiên, KHO KHÔNG ĐỦ HÀNG. Admin sẽ liên hệ xử lý sau.",
        "refund_target_wallet_bot": "Ví Bot",
        "refund_target_wallet_shared": "Ví chung",
        "btn_refund_to_bank": "Yêu cầu hoàn về ngân hàng",
        "refund_done_partner": "💸 <b>ĐƠN HÀNG ĐƯỢC HOÀN TIỀN</b>\n\nMã đơn: <code>{order_code}</code>\nSản phẩm: {product}\nSố tiền hoàn: <b>{amount}</b> ({reason})\nNơi hoàn: <b>{target}</b>\nSố dư ví chung mới: <b>{balance}</b>",
        "refund_done_wallet": "💸 <b>ĐƠN HÀNG ĐƯỢC HOÀN TIỀN</b>\n\nMã đơn: <code>{order_code}</code>\nSản phẩm: {product}\nSố tiền hoàn: <b>{amount}</b> ({reason})\nNơi hoàn: <b>{target}</b>\n\n<i>Tiền đã được cộng vào số dư của bạn.</i>{note}",
        "refund_bank_note_eligible": "\n\nKhoản hoàn từ <b>{min}</b> có thể yêu cầu chuyển về ngân hàng.",
        "refund_bank_note_below_min": "\n\nKhoản hoàn dưới <b>{min}</b> chỉ hoàn vào Ví Bot.",
        "refund_bank_request_processing": "⚠️ Yêu cầu hoàn ngân hàng đã được gửi hoặc xử lý.",
        "refund_bank_info_prompt": "🏦 <b>NHẬP THÔNG TIN NHẬN TIỀN</b>\n\nMã đơn: <code>{order_code}</code>\nSố tiền: <b>{amount}</b>\n\nNhập theo mẫu:\n<code>Tên ngân hàng - Số tài khoản - Tên chủ tài khoản</code>\n\nVí dụ: <code>MB Bank - 0123456789 - NGUYEN VAN A</code>\nGõ <code>/cancel</code> để hủy.",
        "refund_bank_cancelled": "Đã hủy yêu cầu hoàn về ngân hàng.",
        "refund_bank_info_invalid": "❌ {error}\nVui lòng nhập: <code>Tên ngân hàng - Số tài khoản - Tên chủ tài khoản</code>",
        "refund_not_found": "❌ Không tìm thấy đơn hoàn tiền hợp lệ.",
        "refund_below_bank_minimum": "❌ Khoản hoàn dưới {min} chỉ nhận qua Ví Bot.",
        "refund_bank_request_exists": "⚠️ Yêu cầu hoàn ngân hàng đã tồn tại.",
        "refund_insufficient_wallet": "❌ Số dư Ví Bot không còn đủ khoản tiền hoàn để chuyển sang ngân hàng. Vui lòng liên hệ Admin.",
        "refund_bank_request_sent": "✅ <b>ĐÃ GỬI YÊU CẦU HOÀN NGÂN HÀNG</b>\n\nMã yêu cầu: <code>{request_id}</code>\nMã đơn: <code>{order_code}</code>\nSố tiền: <b>{amount}</b>\nThông tin: <code>{bank_info}</code>\n\nAdmin sẽ kiểm tra và xác nhận sau khi chuyển khoản.",
        "order_manual_done_email": "{success} <b>ĐƠN HÀNG ĐÃ HOÀN THÀNH!</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n{tag} <b>Sản phẩm:</b> {product}\n{globe} <b>Email:</b> <code>{email}</code>\n\n<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Vui lòng kiểm tra email của bạn!</b>\n(Nếu không thấy, kiểm tra thư mục Spam/Junk)\n\n{globe} Nếu có vấn đề, liên hệ Admin để được hỗ trợ.",
        "order_manual_cancelled_refund": "{limit} <b>ĐƠN HÀNG ĐÃ BỊ HỦY</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n{tag} <b>Sản phẩm:</b> {product}\n\n{tag} <b>Số tiền đã hoàn:</b> {refund}\n{tag} <b>Số dư mới:</b> {balance}\n\n{globe} Nếu có thắc mắc, vui lòng liên hệ Admin.",
        "refund_not_approved_yet": "❌ Đơn chưa được duyệt hoàn tiền.",
        "checkout_pending_order_exists": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn <b>{order_code}</b> chưa hoàn thành!\nVui lòng hoàn tất hoặc hủy đơn cũ trước khi tạo đơn mới.",
        "checkout_qr_failed_refunded": "❌ Không thể tạo mã QR. Đã hoàn lại {amount} vào ví.\nVui lòng thử lại sau.",
        "checkout_qr_failed": "❌ Không thể tạo mã QR. Vui lòng thử lại sau.",
        "checkout_awaiting_email": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>CHỜ NHẬP EMAIL...</b>",
        "product_combo_invalid": "Combo không hợp lệ",
        "product_combo_offer": "<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> <b>COMBO ƯU ĐÃI</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {first}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {second}\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Giá gốc: <s>{full_price}</s>\n<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> Giá combo: <b>{combo_price}</b> (-{percent}%)\n\n<i>Bấm vào từng sản phẩm để mua riêng:</i>",
        "warranty_claim_approved": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Yêu cầu bảo hành {claim_id} của bạn đã được DUYỆT! Admin sẽ liên hệ sớm.",
        "warranty_claim_rejected": "❌ Yêu cầu bảo hành {claim_id} của bạn đã bị TỪ CHỐI.",
        "support_request_rejected": "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>THÔNG BÁO TỪ ADMIN</b>\n\nYêu cầu hỗ trợ cho đơn hàng <code>{order_code}</code> đã bị <b>TỪ CHỐI</b>.\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Lý do:</b> {reason}\n\n<i>Vui lòng không tiếp tục gửi yêu cầu cho đơn hàng này.</i>",
        "warranty_done_notice": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>THÔNG BÁO BẢO HÀNH</b>\n\nBáo cáo lỗi cho đơn <code>{order_code}</code> đã được admin xử lý và đánh dấu <b>đã bảo hành</b>.\n\nVui lòng kiểm tra lại sản phẩm/tài khoản. Nếu vẫn còn lỗi, bạn có thể gửi lại báo cáo hoặc liên hệ hỗ trợ.",
        "warranty_replacement_issued": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>BẢO HÀNH ĐƠN HÀNG {order_code}</b>\n\nAdmin đã cấp lại sản phẩm mới cho bạn:\n━━━━━━━━━━━━━━━━━━\n<code>{item}</code>\n━━━━━━━━━━━━━━━━━━\n\nXin lỗi vì sự bất tiện này!",
        "withdraw_approved": "{success} <b>YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC DUYỆT!</b>\n\n{tag} Số tiền: {amount}\n<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> Đã chuyển về: <code>{bank_info}</code>\n{tag} Số dư còn lại: {balance}\n\nCảm ơn bạn đã đồng hành cùng Lâm Shop! {menu}",
        "withdraw_rejected": "{limit} <b>YÊU CẦU RÚT TIỀN BỊ TỪ CHỐI</b>\n\n{tag} Số tiền: {amount}\nTiền đã được trả lại Ví Bot. Vui lòng liên hệ Admin để biết thêm chi tiết.",
        "partner_api_registered": "<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>ĐĂNG KÝ API THÀNH CÔNG!</b>\n\n🔐 <b>API Key của bạn:</b> <code>{api_key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số dư:</b> {balance}\n\n<b>Hướng dẫn bắt đầu nhanh:</b>\n1. Nạp tiền: <code>/napapi 500000</code>\n2. Tạo đơn: <code>GET /api/v2/catalog</code> → <code>POST /api/v2/orders</code>\n3. Tra đơn: <code>GET /api/v2/orders/{{order_code}}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vào <code>/start</code> để mở tài liệu API đầy đủ.",
        "partner_api_rejected": "❌ Yêu cầu đăng ký API của bạn đã bị từ chối.",
        "partner_no_account": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>BẠN CHƯA CÓ TÀI KHOẢN ĐẠI LÝ (API)</b>\n\nVui lòng đăng ký theo quy trình:\n1. Gửi <code>/dkyapi</code>\n2. Chờ Admin duyệt\n3. Nhận API Key và nạp ví bằng <code>/napapi</code>",
        "partner_topup_guide": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>HƯỚNG DẪN NẠP VÍ CHUNG</b>\n\nCú pháp: <code>/napapi [số_tiền]</code>\nVí dụ: <code>/napapi 500000</code>",
        "partner_topup_min_amount": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Số tiền nạp tối thiểu là {min}.",
        "partner_topup_invalid_amount": "❌ Số tiền không hợp lệ. Vui lòng nhập số.",
        "partner_topup_request": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>YÊU CẦU NẠP VÍ CHUNG</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Số tiền:</b> {amount}\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Nội dung CK:</b> <code>{content}</code>\n\n<i>Vui lòng quét QR hoặc chuyển khoản đúng nội dung <b>{content}</b> (Telegram ID của bạn). Hệ thống sẽ tự động duyệt và cộng tiền sau 1-3 phút.</i>",
        "wallet_credited_by_admin": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>THÔNG BÁO SỐ DƯ</b>\n\nAdmin đã cộng <b>+{amount}</b> vào ví của bạn.\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: <b>{balance}</b>",
        "wallet_debited_by_admin": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>THÔNG BÁO TRỪ TIỀN</b>\n\nAdmin đã trừ <b>-{amount}</b> từ ví của bạn.\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số dư hiện tại: <b>{balance}</b>",
        "warranty_claim_sent": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ĐÃ GỬI YÊU CẦU BẢO HÀNH</b>\n\nMã yêu cầu: <code>{claim_id}</code>\nAdmin sẽ xem xét trong 24h",
        "admin_only_command": "❌ Bạn không có quyền truy cập lệnh này.",
        "giveaway_message_edited": "{error} <b>CẢNH BÁO:</b> Bạn đã sửa tin nhắn! Kết quả này sẽ KHÔNG được tính.",
        "referral_commission_received": "{tag} <b>BẠN VỪA NHẬN HOA HỒNG!</b>\n\n{tag} <b>Số tiền:</b> +{amount}\n{user} <b>Từ:</b> Người bạn giới thiệu vừa mua hàng\n{tag} <b>Số dư mới:</b> {balance}",
        "referral_signup_success": "{success} <b>BẠN VỪA GIỚI THIỆU THÀNH CÔNG!</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Người mới:</b> {name}\n{id} <b>ID:</b> <code>{member_id}</code>\n\n{tag} Bạn sẽ nhận {percent}% hoa hồng khi người này mua hàng!",
        "game_dice_cooldown": "{loading} <b>CHƯA ĐẾN LƯỢT!</b>\n\nBạn cần chờ <b>{hours}h {mins}m</b> nữa mới được chơi tiếp!\n\n{tip} <i>Mỗi người chỉ được chơi 1 lần/24 giờ.</i>",
        "game_dice_intro": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>GAME XÚC XẮC MAY MẮN</b> <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji>\n\n{tip} <b>Luật chơi:</b> Chỉ ra 111 hoặc 222 mới THẮNG!\n{tag} <b>Phần thưởng:</b> 1 sản phẩm miễn phí\n{tip} <b>Tip:</b> Chỉ 111, 222 mới thắng\n\n{loading} Đang quay xúc xắc...",
        "game_dice_win_no_stock": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result}</b>\n{success} {success} <b>CHIẾN THẮNG!!!</b> {success} {success}\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Rất tiếc, kho đang hết hàng phù hợp.\nAdmin sẽ liên hệ bạn để gửi phần thưởng!",
        "game_dice_win_choose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result}</b>\n{success} {success} <b>CHIẾN THẮNG!!!</b> {success} {success}\n\nChúc mừng bạn! Bạn được nhận <b>1 sản phẩm MIỄN PHÍ</b>!\n\n{tip} <b>Chọn phần thưởng của bạn:</b>",
        "game_dice_lose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>KẾT QUẢ: {result}</b>\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Rất tiếc, bạn chưa thắng lần này!\n\n{tip} <b>Tip:</b> Chỉ 111 hoặc 222 mới thắng\n{loading} Thử lại sau 24 giờ nhé!",
        "order_email_reminder": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>THÔNG BÁO TỪ BOT</b>\n\nBạn ơi, mình thấy bạn vừa mua <b>{product}</b> nhưng chưa nhập Email nhận hàng nè.\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vui lòng <b>nhập địa chỉ Email</b> của bạn vào đây ngay nhé!\n\n<b>Cách gửi email:</b>\n• Reply tin nhắn này với email của bạn\n• Hoặc dùng lệnh: <code>/guimail email@abc.com</code>",
        "payment_reminder": "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>NHẮC NHỞ THANH TOÁN</b>\n\n<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã đơn: <code>{order_code}</code>\n<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> Sản phẩm: {product}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số tiền: <b>{amount}</b>\n\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn chưa thanh toán đơn hàng này.\nĐơn sẽ tự hủy sau <b>{minutes} phút</b> nếu không nhận được thanh toán.\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Nếu đã chuyển khoản, vui lòng đợi 1-2 phút để hệ thống xác nhận.",
        "rank_panel_header": "⭐️ <b>HẠNG THÀNH VIÊN CỦA BẠN</b>\n{divider}\n\n⭐️ Rank: <b>{rank}</b>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Đơn {window} ngày qua: <b>{orders}</b>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Chi tiêu {window} ngày qua: <b>{spent}</b>\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Ưu đãi: <b>giảm {discount}% mọi đơn</b>\n",
        "rank_next_target": "\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Rank tiếp theo: {rank}</b>\n└ Cần chi thêm: <b>{spent_need}</b>\n",
        "rank_highest_reached": "\n<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>Bạn đã đạt hạng cao nhất!</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n",
        "rank_tier_list_header": "\n{divider}\n<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>CÁC CẤP BẬC:</b>\n",
        "rank_tier_row": "  {rank} — từ {min_spent}{marker}\n",
        "rank_you_marker": " ← Bạn",
        "rank_drop_warning": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Không mua thêm thì <b>{date}</b> bạn sẽ tuột khỏi hạng <b>{rank}</b>.\n",
        "rank_window_rule": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Hạng tính theo chi tiêu <b>{window} ngày gần nhất</b>. Đơn cũ hơn sẽ không còn được tính. Nạp tiền không tính, chỉ đơn mua thành công mới tính.",
        "order_save_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Có lỗi xảy ra khi lưu đơn hàng. Vui lòng thử lại hoặc liên hệ Admin.",
        "partner_key_rotate_cancelled_title": "{stop} <b>ĐÃ HỦY ĐỔI API KEY</b>",
        "partner_key_rotate_cancelled": "{stop} Đã hủy đổi API key.",
        "partner_key_rotate_confirm_hint": "{warn} Để xác nhận đổi API key, hãy nhập đúng <code>sure</code>.\nNếu đổi ý, bạn có thể gõ <code>/cancel</code>.",
        "partner_key_rotate_confirmed": "{ok} <b>ĐÃ XÁC NHẬN ĐỔI API KEY</b>\n\nHệ thống đang tạo key mới...",
        "partner_key_not_found": "{warn} Không tìm thấy API key đang hoạt động. Vui lòng thử lại từ menu API.",
        "partner_key_rotate_expired": "{warn} Yêu cầu xác nhận đã hết hiệu lực. Hãy bấm lại nút đổi API key nếu bạn vẫn muốn tiếp tục.",
        "email_invalid_detailed": "❌ Email không hợp lệ!\n\n<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Vui lòng nhập email đúng định dạng.\n<i>Ví dụ: example@gmail.com</i>",
        "email_invalid_short": "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Email không hợp lệ. Vui lòng nhập lại email chính xác.",
        "order_not_found_retry": "❌ Lỗi: Không tìm thấy đơn hàng. Vui lòng thử lại.",
        "checkout_email_received": "{success} <b>ĐÃ NHẬN EMAIL!</b>\n\n{globe} <b>Email:</b> <code>{email}</code>\n{tag} <b>Sản phẩm:</b> {product} x{qty}\n{amount_line}\n{loading} <b>Admin đang xử lý đơn hàng...</b>\n{sos} Bạn sẽ nhận thông báo khi hoàn tất!\n\n{tip} <b>Mã đơn:</b> <code>{order_code}</code>",
        "checkout_amount_line": "{tag} <b>Số tiền:</b> {amount}\n",
        "support_order_refunded": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Đơn hàng này đã được hoàn tiền nên không thể báo lỗi nữa.",
        "admin_reply_header": "<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Bạn có phản hồi từ Admin:</b>",
        "partner_key_old_invalidated": "{warn} <b>QR/API KEY CŨ ĐÃ HẾT HIỆU LỰC</b>\n━━━━━━━━━━━━━━━━━━\n{shield} <b>Key cũ:</b> <code>{old_key}</code>\n{lock} <b>Key mới:</b> <code>{new_key}</code>\n\n<i>Vui lòng dùng key hoặc QR ở tin nhắn mới nhất bên dưới. Không dùng lại ảnh QR cũ này.</i>",
        "partner_key_changed": "{lock} <b>ĐÃ ĐỔI API KEY</b>\n━━━━━━━━━━━━━━━━━━\n{user} <b>Partner:</b> {partner}\n{note} <b>API Key mới:</b> <code>{new_key}</code>\n{money} <b>Số dư ví chung:</b> {balance}\n\n<i>{warn} API key cũ đã bị vô hiệu hóa để bảo mật. Hãy cập nhật key mới trong hệ thống của bạn.</i>",
        "private_chat_required": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Không thể nhắn riêng cho bạn.</b>\n\nVui lòng mở chat riêng với bot và gửi <code>/start</code> trước,\nsau đó quay lại thao tác này.",
        "btn_open_bot_chat": "Mở chat bot",
        "partner_register_guide": "<tg-emoji emoji-id=\"5350481781306958339\">📘</tg-emoji> <b>HƯỚNG DẪN ĐĂNG KÝ API PARTNER</b>\n━━━━━━━━━━━━━━━━━━\n1. Nhấn nút <b>Gửi yêu cầu đăng ký</b> bên dưới.\n2. Chờ Admin duyệt tài khoản.\n3. Bot gửi API Key cho bạn qua tin nhắn.\n4. Nạp ví bằng lệnh <code>/napapi [số_tiền]</code>.\n5. Vào lại <code>/start</code> để thấy menu <b>API Partner</b>.\n\n<i>Menu API chỉ hiện sau khi được Admin duyệt.</i>",
        "partner_topup_menu_guide": "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>HƯỚNG DẪN NẠP VÍ CHUNG</b>\n━━━━━━━━━━━━━━━━━━\n1. Gõ lệnh: <code>/napapi [số_tiền]</code>\n2. Bot trả về QR + nội dung chuyển khoản (NAPI...)\n3. Chuyển đúng số tiền và đúng nội dung\n4. Chờ 1-3 phút hệ thống tự cộng vào ví chung\n\n<b>Ví dụ:</b>\n• <code>/napapi 200000</code>\n• <code>/napapi 500000</code>",
        "broadcast_out_of_stock": "{error} <b>THÔNG BÁO HẾT HÀNG</b>\n\n{tag} Sản phẩm vừa hết hàng:\n<b>{product}</b>\n\n{sos} Chúng tôi sẽ thông báo khi có lại hàng.\n{globe} Liên hệ Admin để đặt trước: @{admin}",
        "broadcast_back_in_stock": "{success} <b>ĐÃ CÓ HÀNG TRỞ LẠI!</b>\n\n{tag} <b>Sản phẩm:</b> {product}\n{stat} <b>Số lượng:</b> {count} sản phẩm\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Đặt hàng ngay:</b> /start\n{loading} <b>Nhanh tay kẻo hết!</b>",
        "partner_low_balance_alert": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>CẢNH BÁO SỐ DƯ API THẤP</b>\n\nPartner: <b>{partner}</b>\nSố dư: <b>{balance}</b>\nNgưỡng: {threshold}",
        "broadcast_product_promo": "<b>{tag} SẢN PHẨM ĐANG MỞ BÁN</b>\n\n<b>{product}</b>\n{tag} Giá: <b>{price}</b>\n{tag} Thời hạn: <b>{duration}</b>\n{shield} Bảo hành: <b>{warranty}</b>\n\n<blockquote>{description}</blockquote>\nBấm nút bên dưới để mua ngay.",
        "value_unlimited": "Không giới hạn",
        "btn_buy_now": "Mua ngay",
        "btn_view_product": "Xem sản phẩm",
        "waitlist_back_in_stock": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>SẢN PHẨM BẠN CHỜ ĐÃ CÓ HÀNG!</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{product}</b>\n<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Số lượng:</b> {count} sản phẩm\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Mua ngay trước khi hết!</b> /start",
        "waitlist_already_registered": "Bạn đã đăng ký nhận thông báo cho sản phẩm này rồi!",
        "waitlist_registered": "Đã đăng ký! Bạn sẽ được thông báo khi {product} có hàng trở lại. ({count} người đang chờ)",
        "support_email_not_found_guide": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN TÌM EMAIL ĐƠN HÀNG</b>\n\n{globe} <b>Bước 1:</b> Kiểm tra hộp thư đến chính\n<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>Bước 2:</b> Kiểm tra thư mục <b>Spam/Thư rác</b>\n<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Bước 3:</b> Kiểm tra các thư mục khác: Promotions, Social\n{tip} <b>Bước 4:</b> Tìm kiếm với từ khóa <code>Lâm Shop</code>\n\n<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>Trên Gmail Mobile:</b>\n• Mở Gmail → Chạm 3 gạch ngang → Spam\n• Nếu tìm thấy → Đánh dấu 'Không phải spam'\n\n{loading} <b>Thông tin tài khoản cũng luôn được gửi ngay trong Telegram</b>\n\n{limit} <b>Nếu vẫn không tìm thấy:</b> Bấm nút bên dưới để được hỗ trợ",
        "support_billing_price": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>THÔNG TIN GIÁ CẢ</b>\n\n{tag} Mỗi sản phẩm có giá riêng, xem trực tiếp trong cửa hàng.\n{loading} Gõ /start → <b>Cửa hàng</b> để xem giá mới nhất.\n\n{tag} <b>Ưu đãi hiện tại:</b>\n• Giao hàng tự động 24/7\n• Bảo hành theo từng sản phẩm\n• Hỗ trợ 24/7",
        "support_billing_refund": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>CHÍNH SÁCH HOÀN TIỀN</b>\n\n{success} <b>Điều kiện hoàn tiền:</b>\n• Trong thời hạn bảo hành của sản phẩm\n• Lỗi từ phía chúng tôi\n• Tài khoản không dùng được sau nhiều lần khắc phục\n\n{limit} <b>Không hoàn tiền nếu:</b>\n• Tự ý đổi mật khẩu hoặc email khôi phục\n• Chia sẻ tài khoản cho nhiều người\n• Vi phạm điều khoản của nền tảng\n\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Quy trình hoàn tiền:</b>\n1. Liên hệ Admin với mã đơn hàng\n2. Admin kiểm tra và xác nhận\n3. Hoàn tiền trong 1-3 ngày làm việc",
        "support_billing_payment": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HƯỚNG DẪN THANH TOÁN</b>\n\n{tag} <b>Phương thức hiện tại:</b>\n• Chuyển khoản ngân hàng\n• Quét mã QR (nhanh nhất)\n• Số dư ví trong bot\n\n{loading} <b>Quy trình:</b>\n1. Gõ /start → Cửa hàng → chọn sản phẩm\n2. Chọn số lượng và phương thức thanh toán\n3. Quét QR hoặc chuyển khoản thủ công\n4. Bot tự động giao hàng sau 1-3 phút\n\n{tip} <b>Lưu ý quan trọng:</b>\n• Chuyển đúng số tiền và nội dung\n• Đơn hàng tự hủy sau 10 phút nếu không thanh toán",
        "support_billing_general": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HỖ TRỢ BILLING TỔNG QUÁT</b>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Giá:</b> Xem trực tiếp từng sản phẩm trong cửa hàng\n<tg-emoji emoji-id=\"5458774648621643551\">💳</tg-emoji> <b>Thanh toán:</b> Chuyển khoản, QR hoặc số dư ví\n<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>Hoàn tiền:</b> Trong thời hạn bảo hành nếu lỗi từ chúng tôi\n<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> <b>Hỗ trợ:</b> 24/7 qua bot và admin\n\n<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> <b>Câu hỏi cụ thể khác?</b>\nHãy mô tả chi tiết vấn đề của bạn để được hỗ trợ tốt nhất!",
        "partner_base_url_tunnel_note": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Link hiện tại là Cloudflare Quick Tunnel.</b> Nếu server restart hoặc mở lại cloudflared thì URL sẽ đổi.\n\n",
        "partner_base_url_config_note": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>Link này đang lấy từ cấu hình PUBLIC_API_URL hiện tại.</b>\n\n",
        "partner_endpoints_doc": "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> <b>DANH SÁCH ENDPOINT PARTNER</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Tài liệu Web:</b> <a href=\"{docs_url}\">{docs_url}</a>\n\n<b>Sản phẩm thường:</b>\n• <code>GET /api/v2/me</code>\n• <code>GET /api/v2/catalog</code>\n• <code>POST /api/v2/orders</code>\n• <code>GET /api/v2/orders/{{order_code}}</code>\n\n<b>Headers dùng chung:</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: MA_DON_DOI_TAC</code>\n\n<b>Mã phản hồi:</b> <code>200</code> OK · <code>400</code> sai endpoint/field · <code>401</code> sai key · <code>402</code> thiếu tiền · <code>404</code> không tìm thấy",
        "partner_docs_summary": "<tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji> <b>TÀI LIỆU API DÀNH CHO THÀNH VIÊN</b>\n━━━━━━━━━━━━━━━━━━\n{status}<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Tài liệu Web:</b> <a href=\"{docs_url}\">{docs_url}</a>\n\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>API Key của bạn:</b> <code>{api_key}</code>\n\n<b>Gọi API cần các header:</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: MA_DON_DOI_TAC</code> (khuyến nghị)\n\n<b>Luồng tích hợp:</b>\n1. <code>GET /api/v2/catalog</code>\n2. <code>POST /api/v2/orders</code>\n3. Poll đơn tại <code>/api/v2/orders/{{order_code}}</code>\n4. Retry phải giữ nguyên partner_ref\n\n<b>Ghi nhớ:</b>\n• Sản phẩm thường giao ngay nằm trong <code>data.items</code>\n• Retry phải giữ nguyên <code>partner_ref</code> và <code>x-idempotency-key</code>\n• Gặp <code>402</code>: nạp ví bằng <code>/napapi [số_tiền]</code>",
        "partner_guide_file_sent": "<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>Mình đã gửi file tài liệu chi tiết ở tin nhắn bên dưới.</b>\n\n",
        "partner_guide_file_failed": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>Chưa gửi được file tài liệu.</b> Bạn vẫn có thể xem bản tóm tắt bên dưới.\n\n",
        "partner_guide_file_caption": "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> <b>Tài liệu API Partner chi tiết</b>\n<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <a href=\"{docs_url}\">{docs_url}</a>\n<i>File này có ví dụ tạo đơn, poll đơn, nhận sản phẩm, quantity và các response mẫu.</i>",
    },
    "en": {
        "main_menu_title": (
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> <b>PREMIUM MMO SERVICE SYSTEM</b> '
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji>\n'
            "━━━━━━━━━━━━━━━━━━\n"
            '<blockquote><tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Trusted - Fast - Professional</b>\n'
            '<tg-emoji emoji-id="5303290914041505430">⚡️</tg-emoji> Auto delivery 24/7.</blockquote>\n\n'
            "{success} <i>Choose a service below to start:</i>"
        ),
        "hello": "Hello {name}!",
        "rank_balance": "Rank: {rank} | Balance: {balance}",
        "rank_label": "Bronze",
        "rank_name_bronze": "Bronze",
        "rank_name_silver": "Silver",
        "rank_name_gold": "Gold",
        "rank_name_diamond": "Diamond",
        "rank_name_master": "Master",
        "btn_shop": "Shop",
        "btn_purchased": "Purchased",
        "btn_game": "Games",
        "btn_earn": "Earn",
        "btn_wallet": "Account & Balance",
        "btn_guide": "Guide & Policy",
        "btn_support": "Support & Contact",
        "btn_report": "Report Issue",
        "btn_community": "Community Group",
        "btn_api_partner": "API Partner",
        "btn_api_topup": "Top Up Wallet",
        "btn_api_register": "Register API",
        "btn_api_guide": "API Guide",
        "btn_admin": "Admin Panel",
        "btn_admin_web": "WebApp API Admin",
        "btn_language": "Language / 语言",
        "btn_wheel": "Lucky Wheel",
        "btn_dice": "Dice",
        "btn_back_main": "Back to Main Menu",
        "games_title": (
            '<tg-emoji emoji-id="5226711870492126219">🎮</tg-emoji> <b>GAME CENTER</b>\n'
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Pick a game below:"
        ),
        "lang_menu_title": (
            "🌐 <b>SELECT LANGUAGE</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Current language: <b>{current}</b>\n"
            "Choose a language below:"
        ),
        "btn_back": "Back",
        "lang_changed": "✅ Language changed to <b>{lang}</b>.",
        "lang_name_vi": "Tiếng Việt",
        "lang_name_en": "English",
        "lang_name_zh": "中文",
        "maintenance": "🛠️ <b>SYSTEM UNDER MAINTENANCE</b>\n\nThe system is being upgraded. Please try again in a few minutes.\n\nSorry for the inconvenience!",
        "sys_unexpected_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Something went wrong while handling your request. Please try again later.",
        "sys_rate_limited": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Please wait {seconds}s before using this command again.",
        "sys_banned": "{limit} You are banned from using this bot. Please contact the admin.",
        "verify_title": "QUICK VERIFICATION",
        "verify_prompt": "Answer this simple calculation to start using the bot:",
        "verify_example": "Example: if it is <code>1 + 2</code>, send <code>3</code>.",
        "verify_number_only": "Please send numbers only.",
        "verify_wrong": "Incorrect. Please try again.",
        "verify_success": "VERIFICATION SUCCESSFUL!",
        "verify_referral_saved": "Referral code recorded.",
        "opening_main_menu": "Opening the main menu...",
        "already_verified": "YOU ARE ALREADY VERIFIED.",
        "use_start": "Use <code>/start</code> to open the bot.",
        "cancelled": "Action cancelled. Returning to the main menu.",
        "ai_fallback": "Sorry, I'm a little busy right now! 🤖\n\nYou can:\n• Type /start to view the menu\n• Contact admin for immediate support",
        "live_chat_title": "LIVE CHAT WITH ADMIN",
        "live_chat_you": "You",
        "live_chat_admin": "Admin",
        "live_chat_empty": "No messages yet. Send your question!",
        "live_chat_prompt": "Send a message to chat with Admin...",
        "live_chat_close": "Close chat",
        "live_chat_closed": "Chat closed. Thank you!",
        "value_none": "None",
        "value_customer": "Customer",
        "btn_new_order": "New order",
        "order_expired_refund_note": "\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>Refunded:</b> +{amount} to your wallet (the order expired).",
        "order_expired_store": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ORDER EXPIRED</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\nThe payment window for this order has closed.\nPlease create a new order if you still want to buy.{refund}",
        "order_expired_email": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>ORDER EXPIRED</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\nThe payment window for the order tied to <b>{email}</b> has closed.\nPlease create a new order if you still want to buy.{refund}",
        "order_product_unavailable": "{error} <b>SORRY - PRODUCT UNAVAILABLE</b>\n\nThe product you ordered (code: <code>{prod_id}</code>) is no longer available.\n\n{tag} <b>Transferred:</b> {paid}\n{tag} <b>Refunded to wallet:</b> +{refunded}\n{tag} <b>Order code:</b> <code>{order_code}</code>\n\nThe full amount has been returned to your Bot Wallet.\nRefunds of {min_bank} or more can also be paid out to a bank account.",
        "order_paid_manual": "{success} <b>PAYMENT SUCCESSFUL!</b>\n\n{tag} <b>Product:</b> {product}\n<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>Quantity:</b> {qty}\n{tag} <b>Paid:</b> {amount}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n\n{globe} <b>Please send the email address for this service:</b>\n<i>The admin will use it to set up and deliver your order.</i>\n\n<b>How to send it:</b>\n• Reply to this message with your email\n• Or use the command: <code>/guimail email@abc.com</code>",
        "order_soldout_refunded": "❌ <b>SORRY!</b>\n\n<b>{product}</b> has just sold out to another customer.\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Your order was refunded automatically: <b>+{refund}</b>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> New balance: <b>{balance}</b>",
        "order_paid_auto": "{success} <b>PAYMENT SUCCESSFUL</b>\n\n{tag} <b>Product:</b> {product}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Quantity:</b> {qty}\n{tag} <b>Paid:</b> {amount}\n{loading} <b>Duration:</b> {duration}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Warranty:</b> {warranty}\n\n{tip} <b>Your account details are being sent right after this message...</b>",
        "reward_period_weekly": "LAST WEEK",
        "reward_period_monthly": "LAST MONTH",
        "reward_top_buyer": "⭐️ <b>CONGRATULATIONS — TOP BUYER OF {period}!</b> ⭐️\n<i>({range})</i>\n\nHello <b>{name}</b>,\nYou bought the most of anyone this period, with <b>{count} orders</b>.\n\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>Your reward:</b>\n<b>{quantity}x {percent}% discount code</b>\n\n",
        "reward_coupon_footer": "\n<i>(Valid for 30 days. Applies to your next order.)</i>",
        "order_manual_completed": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ORDER COMPLETED!</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Product:</b> {product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n\nThank you for using our service! <tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>",
        "order_cancelled_refunded": "❌ <b>ORDER CANCELLED</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Product:</b> {product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Refunded:</b> {refund}\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>New balance:</b> {balance}",
        "order_refunded_by_admin": "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>ORDER REFUNDED</b>\n\n<tg-emoji emoji-id=\"6260059243605398502\">🔖</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n{tag} <b>Refunded:</b> {refund}\n{tag} <b>New balance:</b> {balance}\n\n<i>The admin issued this refund after a technical problem.</i>",
        "order_approved_out_of_stock": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>ORDER APPROVED</b>\n\nStock is short, however. The admin will contact you to sort it out.",
        "refund_target_wallet_bot": "Bot Wallet",
        "refund_target_wallet_shared": "Shared wallet",
        "btn_refund_to_bank": "Request a bank payout",
        "refund_done_partner": "💸 <b>ORDER REFUNDED</b>\n\nOrder code: <code>{order_code}</code>\nProduct: {product}\nRefund amount: <b>{amount}</b> ({reason})\nRefunded to: <b>{target}</b>\nNew shared wallet balance: <b>{balance}</b>",
        "refund_done_wallet": "💸 <b>ORDER REFUNDED</b>\n\nOrder code: <code>{order_code}</code>\nProduct: {product}\nRefund amount: <b>{amount}</b> ({reason})\nRefunded to: <b>{target}</b>\n\n<i>The money has been added to your balance.</i>{note}",
        "refund_bank_note_eligible": "\n\nRefunds of <b>{min}</b> or more can be paid out to a bank account on request.",
        "refund_bank_note_below_min": "\n\nRefunds below <b>{min}</b> go to the Bot Wallet only.",
        "refund_bank_request_processing": "⚠️ A bank payout request has already been sent or processed.",
        "refund_bank_info_prompt": "🏦 <b>ENTER YOUR PAYOUT DETAILS</b>\n\nOrder code: <code>{order_code}</code>\nAmount: <b>{amount}</b>\n\nUse this format:\n<code>Bank name - Account number - Account holder</code>\n\nExample: <code>MB Bank - 0123456789 - NGUYEN VAN A</code>\nSend <code>/cancel</code> to abort.",
        "refund_bank_cancelled": "The bank payout request has been cancelled.",
        "refund_bank_info_invalid": "❌ {error}\nPlease enter: <code>Bank name - Account number - Account holder</code>",
        "refund_not_found": "❌ No eligible refund order was found.",
        "refund_below_bank_minimum": "❌ Refunds below {min} can only be received in the Bot Wallet.",
        "refund_bank_request_exists": "⚠️ A bank payout request already exists.",
        "refund_insufficient_wallet": "❌ Your Bot Wallet no longer holds the refunded amount, so it cannot be moved to a bank account. Please contact the admin.",
        "refund_bank_request_sent": "✅ <b>BANK PAYOUT REQUEST SENT</b>\n\nRequest ID: <code>{request_id}</code>\nOrder code: <code>{order_code}</code>\nAmount: <b>{amount}</b>\nDetails: <code>{bank_info}</code>\n\nThe admin will review and confirm once the transfer is done.",
        "order_manual_done_email": "{success} <b>ORDER COMPLETED!</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n{tag} <b>Product:</b> {product}\n{globe} <b>Email:</b> <code>{email}</code>\n\n<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>Please check your inbox!</b>\n(If it is not there, check the Spam/Junk folder.)\n\n{globe} If anything looks wrong, contact the admin for help.",
        "order_manual_cancelled_refund": "{limit} <b>ORDER CANCELLED</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n{tag} <b>Product:</b> {product}\n\n{tag} <b>Refunded:</b> {refund}\n{tag} <b>New balance:</b> {balance}\n\n{globe} If you have any questions, please contact the admin.",
        "refund_not_approved_yet": "❌ This order has not been approved for a refund yet.",
        "checkout_pending_order_exists": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> You still have an unfinished order: <b>{order_code}</b>\nPlease complete or cancel it before creating a new one.",
        "checkout_qr_failed_refunded": "❌ The QR code could not be created. {amount} has been returned to your wallet.\nPlease try again later.",
        "checkout_qr_failed": "❌ The QR code could not be created. Please try again later.",
        "checkout_awaiting_email": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>WAITING FOR YOUR EMAIL...</b>",
        "product_combo_invalid": "This combo is not valid",
        "product_combo_offer": "<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> <b>COMBO DEAL</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {first}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {second}\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Regular price: <s>{full_price}</s>\n<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> Combo price: <b>{combo_price}</b> (-{percent}%)\n\n<i>Tap a product to buy it on its own:</i>",
        "warranty_claim_approved": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Your warranty claim {claim_id} has been APPROVED. The admin will contact you shortly.",
        "warranty_claim_rejected": "❌ Your warranty claim {claim_id} has been DECLINED.",
        "support_request_rejected": "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>MESSAGE FROM THE ADMIN</b>\n\nThe support request for order <code>{order_code}</code> has been <b>DECLINED</b>.\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>Reason:</b> {reason}\n\n<i>Please do not send further requests for this order.</i>",
        "warranty_done_notice": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>WARRANTY NOTICE</b>\n\nThe issue report for order <code>{order_code}</code> has been handled by the admin and marked <b>covered under warranty</b>.\n\nPlease check the product/account again. If the problem persists, send another report or contact support.",
        "warranty_replacement_issued": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>WARRANTY FOR ORDER {order_code}</b>\n\nThe admin has issued a replacement for you:\n━━━━━━━━━━━━━━━━━━\n<code>{item}</code>\n━━━━━━━━━━━━━━━━━━\n\nSorry for the inconvenience!",
        "withdraw_approved": "{success} <b>WITHDRAWAL APPROVED!</b>\n\n{tag} Amount: {amount}\n<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> Sent to: <code>{bank_info}</code>\n{tag} Remaining balance: {balance}\n\nThank you for being with Lâm Shop! {menu}",
        "withdraw_rejected": "{limit} <b>WITHDRAWAL DECLINED</b>\n\n{tag} Amount: {amount}\nThe money has been returned to your Bot Wallet. Please contact the admin for details.",
        "partner_api_registered": "<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>API REGISTRATION COMPLETE!</b>\n\n🔐 <b>Your API key:</b> <code>{api_key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Balance:</b> {balance}\n\n<b>Quick start:</b>\n1. Top up: <code>/napapi 500000</code>\n2. Create an order: <code>GET /api/v2/catalog</code> → <code>POST /api/v2/orders</code>\n3. Check an order: <code>GET /api/v2/orders/{{order_code}}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Open <code>/start</code> for the full API documentation.",
        "partner_api_rejected": "❌ Your API registration request has been declined.",
        "partner_no_account": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>YOU DO NOT HAVE A PARTNER (API) ACCOUNT YET</b>\n\nTo register:\n1. Send <code>/dkyapi</code>\n2. Wait for admin approval\n3. Receive your API key and top up with <code>/napapi</code>",
        "partner_topup_guide": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>HOW TO TOP UP THE SHARED WALLET</b>\n\nSyntax: <code>/napapi [amount]</code>\nExample: <code>/napapi 500000</code>",
        "partner_topup_min_amount": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> The minimum top-up is {min}.",
        "partner_topup_invalid_amount": "❌ Invalid amount. Please enter a number.",
        "partner_topup_request": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>SHARED WALLET TOP-UP REQUEST</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>Partner:</b> {partner}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Amount:</b> {amount}\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>Transfer reference:</b> <code>{content}</code>\n\n<i>Scan the QR code or transfer with exactly the reference <b>{content}</b> (your Telegram ID). The system approves and credits it automatically within 1-3 minutes.</i>",
        "wallet_credited_by_admin": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>BALANCE UPDATE</b>\n\nThe admin added <b>+{amount}</b> to your wallet.\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Current balance: <b>{balance}</b>",
        "wallet_debited_by_admin": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>DEDUCTION NOTICE</b>\n\nThe admin deducted <b>-{amount}</b> from your wallet.\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Current balance: <b>{balance}</b>",
        "warranty_claim_sent": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>WARRANTY CLAIM SENT</b>\n\nClaim ID: <code>{claim_id}</code>\nThe admin will review it within 24 hours.",
        "admin_only_command": "❌ You do not have permission to use this command.",
        "giveaway_message_edited": "{error} <b>WARNING:</b> You edited your message, so this entry will NOT be counted.",
        "referral_commission_received": "{tag} <b>YOU JUST EARNED A COMMISSION!</b>\n\n{tag} <b>Amount:</b> +{amount}\n{user} <b>From:</b> someone you referred just made a purchase\n{tag} <b>New balance:</b> {balance}",
        "referral_signup_success": "{success} <b>REFERRAL REGISTERED!</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>New member:</b> {name}\n{id} <b>ID:</b> <code>{member_id}</code>\n\n{tag} You will earn {percent}% commission when they make a purchase.",
        "game_dice_cooldown": "{loading} <b>NOT YET!</b>\n\nYou need to wait <b>{hours}h {mins}m</b> before playing again.\n\n{tip} <i>One play per person every 24 hours.</i>",
        "game_dice_intro": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>LUCKY DICE GAME</b> <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji>\n\n{tip} <b>Rules:</b> only 111 or 222 wins!\n{tag} <b>Prize:</b> one free product\n{tip} <b>Tip:</b> only 111 and 222 win\n\n{loading} Rolling the dice...",
        "game_dice_win_no_stock": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>RESULT: {result}</b>\n{success} {success} <b>YOU WIN!!!</b> {success} {success}\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> Unfortunately nothing suitable is in stock right now.\nThe admin will contact you to hand over your prize.",
        "game_dice_win_choose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>RESULT: {result}</b>\n{success} {success} <b>YOU WIN!!!</b> {success} {success}\n\nCongratulations! You get <b>one FREE product</b>.\n\n{tip} <b>Pick your prize:</b>",
        "game_dice_lose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>RESULT: {result}</b>\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> No luck this time!\n\n{tip} <b>Tip:</b> only 111 or 222 wins\n{loading} Try again in 24 hours.",
        "order_email_reminder": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>A NOTE FROM THE BOT</b>\n\nYou bought <b>{product}</b> but have not sent the email address for delivery yet.\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Order code:</b> <code>{order_code}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Please <b>send your email address</b> here.\n\n<b>How to send it:</b>\n• Reply to this message with your email\n• Or use the command: <code>/guimail email@abc.com</code>",
        "payment_reminder": "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>PAYMENT REMINDER</b>\n\n<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Order code: <code>{order_code}</code>\n<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> Product: {product}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Amount: <b>{amount}</b>\n\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> This order has not been paid.\nIt will be cancelled automatically in <b>{minutes} minutes</b> if no payment arrives.\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> If you have already transferred, please allow 1-2 minutes for confirmation.",
        "rank_panel_header": "⭐️ <b>YOUR MEMBERSHIP RANK</b>\n{divider}\n\n⭐️ Rank: <b>{rank}</b>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Orders in last {window} days: <b>{orders}</b>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Spent in last {window} days: <b>{spent}</b>\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Perks: <b>{discount}% off every order</b>\n",
        "rank_next_target": "\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Next rank: {rank}</b>\n└ Still to spend: <b>{spent_need}</b>\n",
        "rank_highest_reached": "\n<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>You have reached the highest rank!</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n",
        "rank_tier_list_header": "\n{divider}\n<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>TIERS:</b>\n",
        "rank_tier_row": "  {rank} — from {min_spent}{marker}\n",
        "rank_you_marker": " ← You",
        "rank_drop_warning": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Without a new order you drop out of <b>{rank}</b> on <b>{date}</b>.\n",
        "rank_window_rule": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Rank is based on spending over the <b>last {window} days</b>. Older orders stop counting. Wallet top-ups do not count — only completed orders do.",
        "order_save_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Something went wrong while saving your order. Please try again or contact the admin.",
        "partner_key_rotate_cancelled_title": "{stop} <b>API KEY ROTATION CANCELLED</b>",
        "partner_key_rotate_cancelled": "{stop} The API key rotation has been cancelled.",
        "partner_key_rotate_confirm_hint": "{warn} To confirm the API key rotation, type exactly <code>sure</code>.\nIf you changed your mind, send <code>/cancel</code>.",
        "partner_key_rotate_confirmed": "{ok} <b>API KEY ROTATION CONFIRMED</b>\n\nA new key is being generated...",
        "partner_key_not_found": "{warn} No active API key was found. Please start again from the API menu.",
        "partner_key_rotate_expired": "{warn} The confirmation request has expired. Press the rotate API key button again if you still want to continue.",
        "email_invalid_detailed": "❌ That email is not valid.\n\n<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Please enter a correctly formatted email address.\n<i>Example: example@gmail.com</i>",
        "email_invalid_short": "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> That email is not valid. Please send a correct address.",
        "order_not_found_retry": "❌ Error: the order could not be found. Please try again.",
        "checkout_email_received": "{success} <b>EMAIL RECEIVED!</b>\n\n{globe} <b>Email:</b> <code>{email}</code>\n{tag} <b>Product:</b> {product} x{qty}\n{amount_line}\n{loading} <b>The admin is processing your order...</b>\n{sos} You will be notified once it is done.\n\n{tip} <b>Order code:</b> <code>{order_code}</code>",
        "checkout_amount_line": "{tag} <b>Amount:</b> {amount}\n",
        "support_order_refunded": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> This order has already been refunded, so it can no longer be reported.",
        "admin_reply_header": "<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>You have a reply from the admin:</b>",
        "partner_key_old_invalidated": "{warn} <b>THE OLD QR / API KEY IS NO LONGER VALID</b>\n━━━━━━━━━━━━━━━━━━\n{shield} <b>Old key:</b> <code>{old_key}</code>\n{lock} <b>New key:</b> <code>{new_key}</code>\n\n<i>Use the key or QR code in the newest message below. Do not reuse this old QR image.</i>",
        "partner_key_changed": "{lock} <b>API KEY ROTATED</b>\n━━━━━━━━━━━━━━━━━━\n{user} <b>Partner:</b> {partner}\n{note} <b>New API key:</b> <code>{new_key}</code>\n{money} <b>Shared wallet balance:</b> {balance}\n\n<i>{warn} The old API key has been disabled for security. Update your system with the new key.</i>",
        "private_chat_required": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>The bot cannot message you privately.</b>\n\nOpen a private chat with the bot and send <code>/start</code> first,\nthen come back and try again.",
        "btn_open_bot_chat": "Open the bot chat",
        "partner_register_guide": "<tg-emoji emoji-id=\"5350481781306958339\">📘</tg-emoji> <b>HOW TO REGISTER FOR THE PARTNER API</b>\n━━━━━━━━━━━━━━━━━━\n1. Press <b>Send a registration request</b> below.\n2. Wait for the admin to approve your account.\n3. The bot sends your API key by message.\n4. Top up with <code>/napapi [amount]</code>.\n5. Open <code>/start</code> again to see the <b>API Partner</b> menu.\n\n<i>The API menu only appears after admin approval.</i>",
        "partner_topup_menu_guide": "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>HOW TO TOP UP THE SHARED WALLET</b>\n━━━━━━━━━━━━━━━━━━\n1. Send: <code>/napapi [amount]</code>\n2. The bot returns a QR code and a transfer reference (NAPI...)\n3. Transfer exactly that amount with exactly that reference\n4. Wait 1-3 minutes for the system to credit the shared wallet\n\n<b>Examples:</b>\n• <code>/napapi 200000</code>\n• <code>/napapi 500000</code>",
        "broadcast_out_of_stock": "{error} <b>OUT OF STOCK</b>\n\n{tag} This product has just sold out:\n<b>{product}</b>\n\n{sos} We will let you know when it is back.\n{globe} Contact the admin to pre-order: @{admin}",
        "broadcast_back_in_stock": "{success} <b>BACK IN STOCK!</b>\n\n{tag} <b>Product:</b> {product}\n{stat} <b>Quantity:</b> {count} in stock\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Order now:</b> /start\n{loading} <b>Be quick before it sells out.</b>",
        "partner_low_balance_alert": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>LOW API BALANCE</b>\n\nPartner: <b>{partner}</b>\nBalance: <b>{balance}</b>\nThreshold: {threshold}",
        "broadcast_product_promo": "<b>{tag} NOW ON SALE</b>\n\n<b>{product}</b>\n{tag} Price: <b>{price}</b>\n{tag} Duration: <b>{duration}</b>\n{shield} Warranty: <b>{warranty}</b>\n\n<blockquote>{description}</blockquote>\nUse the button below to buy it now.",
        "value_unlimited": "Unlimited",
        "btn_buy_now": "Buy now",
        "btn_view_product": "View the product",
        "waitlist_back_in_stock": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>THE PRODUCT YOU WAITED FOR IS BACK!</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{product}</b>\n<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>Quantity:</b> {count} in stock\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>Buy it before it sells out!</b> /start",
        "waitlist_already_registered": "You are already on the notification list for this product.",
        "waitlist_registered": "Done. You will be notified when {product} is back in stock. ({count} people waiting)",
        "support_email_not_found_guide": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HOW TO FIND YOUR ORDER EMAIL</b>\n\n{globe} <b>Step 1:</b> Check your main inbox\n<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>Step 2:</b> Check the <b>Spam/Junk</b> folder\n<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>Step 3:</b> Check other tabs: Promotions, Social\n{tip} <b>Step 4:</b> Search for the keyword <code>Lâm Shop</code>\n\n<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>On Gmail mobile:</b>\n• Open Gmail → tap the three lines → Spam\n• If you find it → mark it 'Not spam'\n\n{loading} <b>Account details are always sent inside Telegram as well.</b>\n\n{limit} <b>Still cannot find it?</b> Press the button below for help.",
        "support_billing_price": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>PRICING</b>\n\n{tag} Each product is priced individually — see the store for details.\n{loading} Send /start → <b>Store</b> for the current prices.\n\n{tag} <b>What you get:</b>\n• Automatic delivery, 24/7\n• Warranty per product\n• Support 24/7",
        "support_billing_refund": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>REFUND POLICY</b>\n\n{success} <b>Refunds are possible when:</b>\n• The product is still within its warranty period\n• The fault is on our side\n• The account still does not work after repeated fixes\n\n{limit} <b>No refund if:</b>\n• You changed the password or recovery email yourself\n• The account was shared with several people\n• The platform's terms were broken\n\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>How a refund works:</b>\n1. Contact the admin with your order code\n2. The admin checks and confirms\n3. The refund lands within 1-3 business days",
        "support_billing_payment": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>HOW TO PAY</b>\n\n{tag} <b>Available methods:</b>\n• Bank transfer\n• QR code scan (fastest)\n• Your wallet balance in the bot\n\n{loading} <b>The steps:</b>\n1. Send /start → Store → pick a product\n2. Choose the quantity and a payment method\n3. Scan the QR code or transfer manually\n4. The bot delivers automatically within 1-3 minutes\n\n{tip} <b>Important:</b>\n• Transfer the exact amount with the exact reference\n• Unpaid orders cancel themselves after 10 minutes",
        "support_billing_general": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>BILLING HELP</b>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>Prices:</b> shown on each product in the store\n<tg-emoji emoji-id=\"5458774648621643551\">💳</tg-emoji> <b>Payment:</b> bank transfer, QR code, or wallet balance\n<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>Refunds:</b> within the warranty period if the fault is ours\n<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> <b>Support:</b> 24/7 through the bot and the admin\n\n<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> <b>Something more specific?</b>\nDescribe your problem in detail and we will help.",
        "partner_base_url_tunnel_note": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>This link is a Cloudflare Quick Tunnel.</b> The URL changes whenever the server restarts or cloudflared is reopened.\n\n",
        "partner_base_url_config_note": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>This link comes from the current PUBLIC_API_URL setting.</b>\n\n",
        "partner_endpoints_doc": "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> <b>PARTNER ENDPOINTS</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Web documentation:</b> <a href=\"{docs_url}\">{docs_url}</a>\n\n<b>Standard products:</b>\n• <code>GET /api/v2/me</code>\n• <code>GET /api/v2/catalog</code>\n• <code>POST /api/v2/orders</code>\n• <code>GET /api/v2/orders/{{order_code}}</code>\n\n<b>Shared headers:</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: YOUR_ORDER_REF</code>\n\n<b>Response codes:</b> <code>200</code> OK · <code>400</code> wrong endpoint/field · <code>401</code> bad key · <code>402</code> insufficient funds · <code>404</code> order not found",
        "partner_docs_summary": "<tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji> <b>PARTNER API DOCUMENTATION</b>\n━━━━━━━━━━━━━━━━━━\n{status}<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL:</b> <code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>Web documentation:</b> <a href=\"{docs_url}\">{docs_url}</a>\n\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>Your API key:</b> <code>{api_key}</code>\n\n<b>Every call needs these headers:</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: YOUR_ORDER_REF</code> (recommended)\n\n<b>Integration flow:</b>\n1. <code>GET /api/v2/catalog</code>\n2. <code>POST /api/v2/orders</code>\n3. Poll the order at <code>/api/v2/orders/{{order_code}}</code>\n4. A retry must keep the same partner_ref\n\n<b>Keep in mind:</b>\n• Instantly delivered products arrive in <code>data.items</code>\n• A retry must keep the same <code>partner_ref</code> and <code>x-idempotency-key</code>\n• On <code>402</code>: top up with <code>/napapi [amount]</code>",
        "partner_guide_file_sent": "<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>The full documentation file is in the message below.</b>\n\n",
        "partner_guide_file_failed": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>The documentation file could not be sent.</b> The summary below still applies.\n\n",
        "partner_guide_file_caption": "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> <b>Full partner API documentation</b>\n<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <a href=\"{docs_url}\">{docs_url}</a>\n<i>It covers creating an order, polling it, receiving the product, quantity, and sample responses.</i>",
    },
    "zh": {
        "main_menu_title": (
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> <b>高端 MMO 服务系统</b> '
            '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji>\n'
            "━━━━━━━━━━━━━━━━━━\n"
            '<blockquote><tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>可靠 · 快速 · 专业</b>\n'
            '<tg-emoji emoji-id="5303290914041505430">⚡️</tg-emoji> 全自动发货 24/7。</blockquote>\n\n'
            "{success} <i>请选择下方服务开始：</i>"
        ),
        "hello": "你好 {name}!",
        "rank_balance": "等级: {rank} | 余额: {balance}",
        "rank_label": "青铜",
        "rank_name_bronze": "青铜",
        "rank_name_silver": "白银",
        "rank_name_gold": "黄金",
        "rank_name_diamond": "钻石",
        "rank_name_master": "王者",
        "btn_shop": "购买",
        "btn_purchased": "已购",
        "btn_game": "游戏",
        "btn_earn": "赚钱",
        "btn_wallet": "账户与余额",
        "btn_guide": "指南与政策",
        "btn_support": "客服与联系",
        "btn_report": "报错",
        "btn_community": "社群",
        "btn_api_partner": "API 合作",
        "btn_api_topup": "充值钱包",
        "btn_api_register": "注册 API",
        "btn_api_guide": "API 指南",
        "btn_admin": "管理面板",
        "btn_admin_web": "WebApp 管理",
        "btn_language": "语言 / Language",
        "btn_wheel": "幸运转盘",
        "btn_dice": "骰子",
        "btn_back_main": "返回主菜单",
        "games_title": (
            '<tg-emoji emoji-id="5226711870492126219">🎮</tg-emoji> <b>游戏中心</b>\n'
            "━━━━━━━━━━━━━━━━━━\n\n"
            "请选择下方游戏："
        ),
        "lang_menu_title": (
            "🌐 <b>选择语言</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "当前语言: <b>{current}</b>\n"
            "请选择下方语言："
        ),
        "btn_back": "返回",
        "lang_changed": "✅ 语言已切换为 <b>{lang}</b>。",
        "lang_name_vi": "Tiếng Việt",
        "lang_name_en": "English",
        "lang_name_zh": "中文",
        "maintenance": "🛠️ <b>系统维护中</b>\n\n系统正在升级，请几分钟后重试。\n\n给您带来不便，敬请谅解！",
        "sys_unexpected_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 处理您的请求时发生错误，请稍后重试。",
        "sys_rate_limited": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> 请等待 {seconds} 秒后再次使用此命令。",
        "sys_banned": "{limit} 您已被禁止使用此机器人，请联系管理员。",
        "verify_title": "快速验证",
        "verify_prompt": "请回答这道简单算术题以开始使用机器人：",
        "verify_example": "示例：如果题目是 <code>1 + 2</code>，请发送 <code>3</code>。",
        "verify_number_only": "请仅发送数字答案。",
        "verify_wrong": "答案错误，请重试。",
        "verify_success": "验证成功！",
        "verify_referral_saved": "推荐码已记录。",
        "opening_main_menu": "正在打开主菜单...",
        "already_verified": "您已完成验证。",
        "use_start": "使用 <code>/start</code> 打开机器人。",
        "cancelled": "操作已取消，正在返回主菜单。",
        "ai_fallback": "抱歉，我现在有点忙！🤖\n\n您可以：\n• 输入 /start 查看菜单\n• 联系管理员获取即时帮助",
        "live_chat_title": "与管理员在线聊天",
        "live_chat_you": "您",
        "live_chat_admin": "管理员",
        "live_chat_empty": "暂无消息，请发送您的问题！",
        "live_chat_prompt": "发送消息与管理员聊天...",
        "live_chat_close": "关闭聊天",
        "live_chat_closed": "聊天已关闭，谢谢！",
        "value_none": "无",
        "value_customer": "顾客",
        "btn_new_order": "重新下单",
        "order_expired_refund_note": "\n\n<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>已退款：</b>+{amount} 至钱包（订单已过期）。",
        "order_expired_store": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>订单已过期</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n该订单的付款时限已过。\n如仍需购买，请重新下单。{refund}",
        "order_expired_email": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>订单已过期</b> <tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>\n\n邮箱 <b>{email}</b> 对应订单的付款时限已过。\n如仍需购买，请重新下单。{refund}",
        "order_product_unavailable": "{error} <b>抱歉 — 商品不可用</b>\n\n您下单的商品（代码：<code>{prod_id}</code>）已不再供应。\n\n{tag} <b>转账金额：</b>{paid}\n{tag} <b>已退至钱包：</b>+{refunded}\n{tag} <b>订单号：</b><code>{order_code}</code>\n\n全部款项已退回机器人钱包。\n退款金额达到 {min_bank} 时，还可选择退回银行账户。",
        "order_paid_manual": "{success} <b>付款成功！</b>\n\n{tag} <b>商品：</b>{product}\n<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>数量：</b>{qty}\n{tag} <b>已付金额：</b>{amount}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n\n{globe} <b>请提供接收服务的邮箱：</b>\n<i>管理员将使用该邮箱为您设置并发送订单信息。</i>\n\n<b>发送方式：</b>\n• 直接回复本条消息并附上邮箱\n• 或使用命令：<code>/guimail email@abc.com</code>",
        "order_soldout_refunded": "❌ <b>非常抱歉！</b>\n\n商品 <b>{product}</b> 刚刚被其他顾客买完了。\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 订单已自动退款：<b>+{refund}</b>\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> 新余额：<b>{balance}</b>",
        "order_paid_auto": "{success} <b>付款成功</b>\n\n{tag} <b>商品：</b>{product}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>数量：</b>{qty}\n{tag} <b>已付金额：</b>{amount}\n{loading} <b>有效期：</b>{duration}\n<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>保修：</b>{warranty}\n\n{tip} <b>账号信息将紧随本条消息发送……</b>",
        "reward_period_weekly": "上周",
        "reward_period_monthly": "上月",
        "reward_top_buyer": "⭐️ <b>恭喜您成为{period}购买冠军！</b> ⭐️\n<i>（{range}）</i>\n\n您好 <b>{name}</b>，\n本期您的下单量最高，共 <b>{count} 笔订单</b>。\n\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> <b>您的奖励：</b>\n<b>{quantity} 张 {percent}% 折扣码</b>\n\n",
        "reward_coupon_footer": "\n<i>（有效期 30 天，适用于下一笔订单。）</i>",
        "order_manual_completed": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>订单已完成！</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>商品：</b>{product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n\n感谢您的惠顾！<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji>",
        "order_cancelled_refunded": "❌ <b>订单已取消</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>商品：</b>{product}\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>已退款：</b>{refund}\n<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>新余额：</b>{balance}",
        "order_refunded_by_admin": "<tg-emoji emoji-id=\"5462956611033117422\">♻️</tg-emoji> <b>订单已退款</b>\n\n<tg-emoji emoji-id=\"6260059243605398502\">🔖</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n{tag} <b>退款金额：</b>{refund}\n{tag} <b>新余额：</b>{balance}\n\n<i>因技术问题，管理员已为您办理退款。</i>",
        "order_approved_out_of_stock": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>订单已批准</b>\n\n但目前库存不足，管理员稍后会联系您处理。",
        "refund_target_wallet_bot": "机器人钱包",
        "refund_target_wallet_shared": "共享钱包",
        "btn_refund_to_bank": "申请退回银行账户",
        "refund_done_partner": "💸 <b>订单已退款</b>\n\n订单号：<code>{order_code}</code>\n商品：{product}\n退款金额：<b>{amount}</b>（{reason}）\n退款至：<b>{target}</b>\n共享钱包新余额：<b>{balance}</b>",
        "refund_done_wallet": "💸 <b>订单已退款</b>\n\n订单号：<code>{order_code}</code>\n商品：{product}\n退款金额：<b>{amount}</b>（{reason}）\n退款至：<b>{target}</b>\n\n<i>款项已计入您的余额。</i>{note}",
        "refund_bank_note_eligible": "\n\n退款金额达到 <b>{min}</b> 时，可申请转回银行账户。",
        "refund_bank_note_below_min": "\n\n低于 <b>{min}</b> 的退款只能退回机器人钱包。",
        "refund_bank_request_processing": "⚠️ 银行退款申请已提交或已处理。",
        "refund_bank_info_prompt": "🏦 <b>请填写收款信息</b>\n\n订单号：<code>{order_code}</code>\n金额：<b>{amount}</b>\n\n请按以下格式填写：\n<code>银行名称 - 账号 - 开户人姓名</code>\n\n示例：<code>MB Bank - 0123456789 - NGUYEN VAN A</code>\n发送 <code>/cancel</code> 可取消。",
        "refund_bank_cancelled": "已取消银行退款申请。",
        "refund_bank_info_invalid": "❌ {error}\n请填写：<code>银行名称 - 账号 - 开户人姓名</code>",
        "refund_not_found": "❌ 未找到符合条件的退款订单。",
        "refund_below_bank_minimum": "❌ 低于 {min} 的退款只能通过机器人钱包接收。",
        "refund_bank_request_exists": "⚠️ 银行退款申请已存在。",
        "refund_insufficient_wallet": "❌ 机器人钱包余额已不足退款金额，无法转至银行账户，请联系管理员。",
        "refund_bank_request_sent": "✅ <b>银行退款申请已提交</b>\n\n申请编号：<code>{request_id}</code>\n订单号：<code>{order_code}</code>\n金额：<b>{amount}</b>\n收款信息：<code>{bank_info}</code>\n\n管理员将在转账后核对并确认。",
        "order_manual_done_email": "{success} <b>订单已完成！</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n{tag} <b>商品：</b>{product}\n{globe} <b>邮箱：</b><code>{email}</code>\n\n<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>请查收您的邮件！</b>\n（如未收到，请检查垃圾邮件文件夹。）\n\n{globe} 如有问题，请联系管理员。",
        "order_manual_cancelled_refund": "{limit} <b>订单已取消</b>\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n{tag} <b>商品：</b>{product}\n\n{tag} <b>已退金额：</b>{refund}\n{tag} <b>新余额：</b>{balance}\n\n{globe} 如有疑问，请联系管理员。",
        "refund_not_approved_yet": "❌ 该订单尚未通过退款审核。",
        "checkout_pending_order_exists": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 您还有一笔未完成的订单：<b>{order_code}</b>\n请先完成或取消该订单，再重新下单。",
        "checkout_qr_failed_refunded": "❌ 无法生成二维码，{amount} 已退回您的钱包。\n请稍后重试。",
        "checkout_qr_failed": "❌ 无法生成二维码，请稍后重试。",
        "checkout_awaiting_email": "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>等待输入邮箱……</b>",
        "product_combo_invalid": "该套餐无效",
        "product_combo_offer": "<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> <b>套餐优惠</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {first}\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {second}\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 原价：<s>{full_price}</s>\n<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> 套餐价：<b>{combo_price}</b>（-{percent}%）\n\n<i>点击单个商品可单独购买：</i>",
        "warranty_claim_approved": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> 您的保修申请 {claim_id} 已通过审核！管理员将尽快与您联系。",
        "warranty_claim_rejected": "❌ 您的保修申请 {claim_id} 已被拒绝。",
        "support_request_rejected": "<tg-emoji emoji-id=\"5424857974784925603\">⛔</tg-emoji> <b>管理员通知</b>\n\n订单 <code>{order_code}</code> 的支持请求已被<b>拒绝</b>。\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <b>原因：</b>{reason}\n\n<i>请不要再为该订单提交请求。</i>",
        "warranty_done_notice": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>保修通知</b>\n\n订单 <code>{order_code}</code> 的故障报告已由管理员处理，并标记为<b>已保修</b>。\n\n请重新检查商品／账号。如问题仍未解决，可再次提交报告或联系客服。",
        "warranty_replacement_issued": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>订单 {order_code} 保修处理</b>\n\n管理员已为您补发新的商品：\n━━━━━━━━━━━━━━━━━━\n<code>{item}</code>\n━━━━━━━━━━━━━━━━━━\n\n给您带来不便，敬请谅解！",
        "withdraw_approved": "{success} <b>提现申请已通过！</b>\n\n{tag} 金额：{amount}\n<tg-emoji emoji-id=\"5278467510604160626\">🏦</tg-emoji> 已转至：<code>{bank_info}</code>\n{tag} 剩余余额：{balance}\n\n感谢您一直支持 Lâm Shop！{menu}",
        "withdraw_rejected": "{limit} <b>提现申请被拒绝</b>\n\n{tag} 金额：{amount}\n款项已退回机器人钱包。详情请联系管理员。",
        "partner_api_registered": "<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>API 注册成功！</b>\n\n🔐 <b>您的 API 密钥：</b><code>{api_key}</code>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>余额：</b>{balance}\n\n<b>快速上手：</b>\n1. 充值：<code>/napapi 500000</code>\n2. 下单：<code>GET /api/v2/catalog</code> → <code>POST /api/v2/orders</code>\n3. 查单：<code>GET /api/v2/orders/{{order_code}}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> 进入 <code>/start</code> 查看完整 API 文档。",
        "partner_api_rejected": "❌ 您的 API 注册申请已被拒绝。",
        "partner_no_account": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>您还没有代理（API）账户</b>\n\n注册流程：\n1. 发送 <code>/dkyapi</code>\n2. 等待管理员审核\n3. 获取 API 密钥并使用 <code>/napapi</code> 充值",
        "partner_topup_guide": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>共享钱包充值说明</b>\n\n格式：<code>/napapi [金额]</code>\n示例：<code>/napapi 500000</code>",
        "partner_topup_min_amount": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 最低充值金额为 {min}。",
        "partner_topup_invalid_amount": "❌ 金额无效，请输入数字。",
        "partner_topup_request": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>共享钱包充值申请</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>合作方：</b>{partner}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>金额：</b>{amount}\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>转账备注：</b><code>{content}</code>\n\n<i>请扫描二维码，或转账时填写备注 <b>{content}</b>（您的 Telegram ID）。系统将在 1-3 分钟内自动审核并入账。</i>",
        "wallet_credited_by_admin": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>余额通知</b>\n\n管理员已为您的钱包充值 <b>+{amount}</b>。\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 当前余额：<b>{balance}</b>",
        "wallet_debited_by_admin": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>扣款通知</b>\n\n管理员已从您的钱包扣除 <b>-{amount}</b>。\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 当前余额：<b>{balance}</b>",
        "warranty_claim_sent": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>保修申请已提交</b>\n\n申请编号：<code>{claim_id}</code>\n管理员将在 24 小时内审核。",
        "admin_only_command": "❌ 您没有使用该命令的权限。",
        "giveaway_message_edited": "{error} <b>警告：</b>您修改了消息，本次结果将不计入。",
        "referral_commission_received": "{tag} <b>您获得了一笔佣金！</b>\n\n{tag} <b>金额：</b>+{amount}\n{user} <b>来源：</b>您推荐的用户刚刚下单\n{tag} <b>新余额：</b>{balance}",
        "referral_signup_success": "{success} <b>推荐成功！</b>\n\n<tg-emoji emoji-id=\"5350778980158956492\">👤</tg-emoji> <b>新成员：</b>{name}\n{id} <b>ID：</b><code>{member_id}</code>\n\n{tag} 该用户下单后，您将获得 {percent}% 佣金。",
        "game_dice_cooldown": "{loading} <b>还没轮到您！</b>\n\n还需等待 <b>{hours} 小时 {mins} 分</b>才能再玩一次。\n\n{tip} <i>每人每 24 小时只能玩一次。</i>",
        "game_dice_intro": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>幸运骰子游戏</b> <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji>\n\n{tip} <b>规则：</b>只有掷出 111 或 222 才算赢！\n{tag} <b>奖励：</b>一件免费商品\n{tip} <b>提示：</b>只有 111 和 222 能获胜\n\n{loading} 正在掷骰子……",
        "game_dice_win_no_stock": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>结果：{result}</b>\n{success} {success} <b>您赢了！！！</b>{success} {success}\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> 很抱歉，目前没有合适的库存。\n管理员会联系您发放奖励！",
        "game_dice_win_choose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>结果：{result}</b>\n{success} {success} <b>您赢了！！！</b>{success} {success}\n\n恭喜！您获得 <b>一件免费商品</b>！\n\n{tip} <b>请选择您的奖励：</b>",
        "game_dice_lose": "<tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> <b>结果：{result}</b>\n\n<tg-emoji emoji-id=\"5386856460632201117\">😢</tg-emoji> 很遗憾，这次没有中奖！\n\n{tip} <b>提示：</b>只有 111 或 222 才算赢\n{loading} 24 小时后再来试试吧！",
        "order_email_reminder": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>机器人提醒</b>\n\n您购买了 <b>{product}</b>，但还没有提供收货邮箱。\n\n<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>订单号：</b><code>{order_code}</code>\n\n<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> 请在此<b>填写您的邮箱地址</b>。\n\n<b>发送方式：</b>\n• 直接回复本条消息并附上邮箱\n• 或使用命令：<code>/guimail email@abc.com</code>",
        "payment_reminder": "<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>付款提醒</b>\n\n<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> 订单号：<code>{order_code}</code>\n<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> 商品：{product}\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 金额：<b>{amount}</b>\n\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 该订单尚未付款。\n若在 <b>{minutes} 分钟</b>内未收到款项，订单将自动取消。\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> 如已转账，请等待 1-2 分钟由系统确认。",
        "rank_panel_header": "⭐️ <b>您的会员等级</b>\n{divider}\n\n⭐️ 等级：<b>{rank}</b>\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> 近 {window} 天订单：<b>{orders}</b>\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> 近 {window} 天消费：<b>{spent}</b>\n<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> 优惠：<b>全单折扣 {discount}%</b>\n",
        "rank_next_target": "\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>下一等级：{rank}</b>\n└ 还需消费：<b>{spent_need}</b>\n",
        "rank_highest_reached": "\n<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>您已达到最高等级！</b><tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n",
        "rank_tier_list_header": "\n{divider}\n<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>等级列表：</b>\n",
        "rank_tier_row": "  {rank} — {min_spent} 起{marker}\n",
        "rank_you_marker": " ← 您",
        "rank_drop_warning": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 若不再下单，您将在 <b>{date}</b> 跌出 <b>{rank}</b> 等级。\n",
        "rank_window_rule": "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 等级按<b>近 {window} 天</b>消费额计算，更早的订单不再计入。充值不计，仅统计已完成订单。",
        "order_save_error": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 保存订单时出错，请重试或联系管理员。",
        "partner_key_rotate_cancelled_title": "{stop} <b>已取消更换 API 密钥</b>",
        "partner_key_rotate_cancelled": "{stop} 已取消更换 API 密钥。",
        "partner_key_rotate_confirm_hint": "{warn} 如需确认更换 API 密钥，请准确输入 <code>sure</code>。\n若改变主意，可发送 <code>/cancel</code>。",
        "partner_key_rotate_confirmed": "{ok} <b>已确认更换 API 密钥</b>\n\n系统正在生成新密钥……",
        "partner_key_not_found": "{warn} 未找到有效的 API 密钥，请从 API 菜单重新开始。",
        "partner_key_rotate_expired": "{warn} 确认请求已失效。如仍需继续，请重新点击更换 API 密钥按钮。",
        "email_invalid_detailed": "❌ 邮箱格式无效！\n\n<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> 请输入格式正确的邮箱地址。\n<i>示例：example@gmail.com</i>",
        "email_invalid_short": "<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> 邮箱无效，请重新输入正确的邮箱地址。",
        "order_not_found_retry": "❌ 错误：未找到该订单，请重试。",
        "checkout_email_received": "{success} <b>已收到邮箱！</b>\n\n{globe} <b>邮箱：</b><code>{email}</code>\n{tag} <b>商品：</b>{product} x{qty}\n{amount_line}\n{loading} <b>管理员正在处理您的订单……</b>\n{sos} 处理完成后将通知您。\n\n{tip} <b>订单号：</b><code>{order_code}</code>",
        "checkout_amount_line": "{tag} <b>金额：</b>{amount}\n",
        "support_order_refunded": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> 该订单已完成退款，无法再提交故障报告。",
        "admin_reply_header": "<tg-emoji emoji-id=\"5314638736462966754\">📬</tg-emoji> <b>您收到管理员的回复：</b>",
        "partner_key_old_invalidated": "{warn} <b>旧二维码／API 密钥已失效</b>\n━━━━━━━━━━━━━━━━━━\n{shield} <b>旧密钥：</b><code>{old_key}</code>\n{lock} <b>新密钥：</b><code>{new_key}</code>\n\n<i>请使用下方最新消息中的密钥或二维码，勿再使用这张旧二维码。</i>",
        "partner_key_changed": "{lock} <b>API 密钥已更换</b>\n━━━━━━━━━━━━━━━━━━\n{user} <b>合作方：</b>{partner}\n{note} <b>新 API 密钥：</b><code>{new_key}</code>\n{money} <b>共享钱包余额：</b>{balance}\n\n<i>{warn} 出于安全考虑，旧密钥已停用。请在您的系统中更新为新密钥。</i>",
        "private_chat_required": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>机器人无法私信您。</b>\n\n请先与机器人开启私聊并发送 <code>/start</code>，\n然后返回重新操作。",
        "btn_open_bot_chat": "打开机器人对话",
        "partner_register_guide": "<tg-emoji emoji-id=\"5350481781306958339\">📘</tg-emoji> <b>合作方 API 注册指南</b>\n━━━━━━━━━━━━━━━━━━\n1. 点击下方<b>提交注册申请</b>按钮。\n2. 等待管理员审核账户。\n3. 机器人将通过消息发送 API 密钥。\n4. 使用 <code>/napapi [金额]</code> 充值。\n5. 重新打开 <code>/start</code> 即可看到 <b>API Partner</b> 菜单。\n\n<i>API 菜单需管理员审核通过后才会显示。</i>",
        "partner_topup_menu_guide": "<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>共享钱包充值指南</b>\n━━━━━━━━━━━━━━━━━━\n1. 发送命令：<code>/napapi [金额]</code>\n2. 机器人返回二维码和转账备注（NAPI…）\n3. 按照给出的金额和备注准确转账\n4. 等待 1-3 分钟，系统自动计入共享钱包\n\n<b>示例：</b>\n• <code>/napapi 200000</code>\n• <code>/napapi 500000</code>",
        "broadcast_out_of_stock": "{error} <b>缺货通知</b>\n\n{tag} 该商品刚刚售罄：\n<b>{product}</b>\n\n{sos} 补货后我们会通知您。\n{globe} 如需预订请联系管理员：@{admin}",
        "broadcast_back_in_stock": "{success} <b>补货到了！</b>\n\n{tag} <b>商品：</b>{product}\n{stat} <b>数量：</b>{count} 件\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>立即下单：</b>/start\n{loading} <b>手快有，手慢无！</b>",
        "partner_low_balance_alert": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>API 余额不足提醒</b>\n\n合作方：<b>{partner}</b>\n余额：<b>{balance}</b>\n阈值：{threshold}",
        "broadcast_product_promo": "<b>{tag} 正在发售</b>\n\n<b>{product}</b>\n{tag} 价格：<b>{price}</b>\n{tag} 有效期：<b>{duration}</b>\n{shield} 保修：<b>{warranty}</b>\n\n<blockquote>{description}</blockquote>\n点击下方按钮立即购买。",
        "value_unlimited": "不限",
        "btn_buy_now": "立即购买",
        "btn_view_product": "查看商品",
        "waitlist_back_in_stock": "<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>您等待的商品已到货！</b>\n\n<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>{product}</b>\n<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>数量：</b>{count} 件\n\n<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> <b>手快下单，售完为止！</b>/start",
        "waitlist_already_registered": "您已订阅该商品的到货通知。",
        "waitlist_registered": "已订阅！{product} 到货后将通知您。（当前 {count} 人等待）",
        "support_email_not_found_guide": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>如何找到订单邮件</b>\n\n{globe} <b>第 1 步：</b>检查主收件箱\n<tg-emoji emoji-id=\"5424857974784925603\">🗑️</tg-emoji> <b>第 2 步：</b>检查<b>垃圾邮件</b>文件夹\n<tg-emoji emoji-id=\"5854908544712707500\">📁</tg-emoji> <b>第 3 步：</b>检查其他标签：促销、社交\n{tip} <b>第 4 步：</b>搜索关键词 <code>Lâm Shop</code>\n\n<tg-emoji emoji-id=\"5426991207731437507\">📱</tg-emoji> <b>Gmail 手机端：</b>\n• 打开 Gmail → 点击三横线 → 垃圾邮件\n• 找到后 → 标记为「不是垃圾邮件」\n\n{loading} <b>账号信息同样会直接发送到 Telegram。</b>\n\n{limit} <b>仍然找不到？</b>请点击下方按钮联系客服。",
        "support_billing_price": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>价格信息</b>\n\n{tag} 每件商品价格不同，请在商店中查看。\n{loading} 发送 /start → <b>商店</b>查看最新价格。\n\n{tag} <b>当前优惠：</b>\n• 24/7 自动发货\n• 每件商品均有保修\n• 24/7 客服支持",
        "support_billing_refund": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>退款政策</b>\n\n{success} <b>可以退款的情形：</b>\n• 商品仍在保修期内\n• 问题出在我方\n• 多次修复后账号仍无法使用\n\n{limit} <b>不予退款的情形：</b>\n• 自行更改密码或找回邮箱\n• 账号被多人共用\n• 违反平台条款\n\n<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> <b>退款流程：</b>\n1. 携订单号联系管理员\n2. 管理员核实并确认\n3. 1-3 个工作日内完成退款",
        "support_billing_payment": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>付款指南</b>\n\n{tag} <b>目前支持的方式：</b>\n• 银行转账\n• 扫描二维码（最快）\n• 机器人钱包余额\n\n{loading} <b>操作流程：</b>\n1. 发送 /start → 商店 → 选择商品\n2. 选择数量和付款方式\n3. 扫码或手动转账\n4. 机器人将在 1-3 分钟内自动发货\n\n{tip} <b>重要提示：</b>\n• 请按给出的金额和备注准确转账\n• 未付款的订单将在 10 分钟后自动取消",
        "support_billing_general": "<tg-emoji emoji-id=\"6271362510901747485\">🤖</tg-emoji> <b>账单与付款帮助</b>\n\n<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> <b>价格：</b>在商店中查看每件商品\n<tg-emoji emoji-id=\"5458774648621643551\">💳</tg-emoji> <b>付款：</b>银行转账、二维码或钱包余额\n<tg-emoji emoji-id=\"5462956611033117422\">🔄</tg-emoji> <b>退款：</b>保修期内且属我方问题时可退\n<tg-emoji emoji-id=\"6129860303619363484\">📞</tg-emoji> <b>客服：</b>机器人与管理员 24/7 在线\n\n<tg-emoji emoji-id=\"5264919878082509254\">❓</tg-emoji> <b>还有其他具体问题？</b>\n请详细描述您的问题，我们将尽力协助。",
        "partner_base_url_tunnel_note": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>当前链接为 Cloudflare Quick Tunnel。</b>服务器重启或重新启动 cloudflared 后，该地址会改变。\n\n",
        "partner_base_url_config_note": "<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> <b>该链接取自当前的 PUBLIC_API_URL 配置。</b>\n\n",
        "partner_endpoints_doc": "<tg-emoji emoji-id=\"5215392879320505675\">🛠️</tg-emoji> <b>合作方接口列表</b>\n━━━━━━━━━━━━━━━━━━\n<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL：</b><code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>网页文档：</b><a href=\"{docs_url}\">{docs_url}</a>\n\n<b>普通商品：</b>\n• <code>GET /api/v2/me</code>\n• <code>GET /api/v2/catalog</code>\n• <code>POST /api/v2/orders</code>\n• <code>GET /api/v2/orders/{{order_code}}</code>\n\n<b>通用请求头：</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: 您的订单号</code>\n\n<b>响应码：</b><code>200</code> 成功 · <code>400</code> 接口或字段错误 · <code>401</code> 密钥错误 · <code>402</code> 余额不足 · <code>404</code> 订单不存在",
        "partner_docs_summary": "<tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji> <b>合作方 API 文档</b>\n━━━━━━━━━━━━━━━━━━\n{status}<tg-emoji emoji-id=\"5447410659077661506\">🌐</tg-emoji> <b>Base URL：</b><code>{base_url}</code>\n{note}<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <b>网页文档：</b><a href=\"{docs_url}\">{docs_url}</a>\n\n<tg-emoji emoji-id=\"5197288647275071607\">🛡</tg-emoji> <b>您的 API 密钥：</b><code>{api_key}</code>\n\n<b>调用接口所需请求头：</b>\n• <code>x-api-key: {api_key}</code>\n• <code>x-idempotency-key: 您的订单号</code>（建议）\n\n<b>对接流程：</b>\n1. <code>GET /api/v2/catalog</code>\n2. <code>POST /api/v2/orders</code>\n3. 通过 <code>/api/v2/orders/{{order_code}}</code> 轮询订单\n4. 重试时必须保持相同的 partner_ref\n\n<b>注意事项：</b>\n• 即时发货商品在 <code>data.items</code> 中返回\n• 重试时必须保持相同的 <code>partner_ref</code> 与 <code>x-idempotency-key</code>\n• 遇到 <code>402</code>：使用 <code>/napapi [金额]</code> 充值",
        "partner_guide_file_sent": "<tg-emoji emoji-id=\"5303290914041505430\">⚡️</tg-emoji> <b>完整文档文件已在下方消息中发送。</b>\n\n",
        "partner_guide_file_failed": "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <b>文档文件发送失败。</b>您仍可查看下方的摘要。\n\n",
        "partner_guide_file_caption": "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> <b>合作方 API 完整文档</b>\n<tg-emoji emoji-id=\"5350481781306958339\">📖</tg-emoji> <a href=\"{docs_url}\">{docs_url}</a>\n<i>内含下单、轮询订单、接收商品、数量以及示例响应。</i>",
    },
}


def normalize_lang(lang) -> str:
    key = str(lang or "").strip().lower().replace(" ", "")
    if key in _LANG_ALIASES:
        return _LANG_ALIASES[key]
    # Telegram gửi IETF tag như "en-US", "zh-Hans", "vi-VN": lấy phần gốc.
    base = key.replace("_", "-").split("-", 1)[0]
    return _LANG_ALIASES.get(base, DEFAULT_LANG)


def resolve_lang(user) -> str:
    """Ngôn ngữ đã lưu trong profile, nếu chưa có thì lấy theo client Telegram."""
    try:
        uid = int(getattr(user, "id", 0) or 0)
    except (TypeError, ValueError):
        uid = 0
    if uid > 0:
        try:
            profile = user_data_db.get(str(uid)) if isinstance(user_data_db, dict) else None
        except NameError:
            profile = None
        if isinstance(profile, dict) and profile.get("lang"):
            return normalize_lang(profile.get("lang"))
    return normalize_lang(getattr(user, "language_code", None))


def get_user_lang(user_id=None) -> str:
    try:
        uid = int(user_id or 0)
    except (TypeError, ValueError):
        return DEFAULT_LANG
    if uid <= 0:
        return DEFAULT_LANG
    try:
        profile = user_data_db.get(str(uid)) if isinstance(user_data_db, dict) else None
    except NameError:
        profile = None
    if not isinstance(profile, dict):
        return DEFAULT_LANG
    return normalize_lang(profile.get("lang"))


def set_user_lang(user_id, lang) -> str:
    code = normalize_lang(lang)
    try:
        uid = int(user_id or 0)
    except (TypeError, ValueError):
        return code
    if uid <= 0:
        return code
    try:
        if not isinstance(user_data_db, dict):
            return code
        profile = user_data_db.get(str(uid))
        if not isinstance(profile, dict):
            user_data_db[str(uid)] = {"lang": code, "balance": 0}
        else:
            profile["lang"] = code
    except NameError:
        pass
    return code


def t(key: str, user_id=None, lang=None, **kwargs) -> str:
    code = normalize_lang(lang) if lang is not None else get_user_lang(user_id)
    table = STRINGS.get(code) or STRINGS[DEFAULT_LANG]
    text = table.get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


def lang_display_name(code, user_id=None, lang=None) -> str:
    code = normalize_lang(code)
    return t(f"lang_name_{code}", user_id=user_id, lang=lang)


def pick_locale(table, code):
    """Chon ban dich theo locale, roi ve tieng Viet neu locale la.

    Moi dict theo locale trong repo deu duoc index bang mot ma ngon ngu; neu ma
    do khong co trong bang thi phep index tran nem KeyError giua luong gui tin
    cho khach. Bao qua day de luon con duong lui ve DEFAULT_LANG.
    """
    if not isinstance(table, dict):
        return table
    if code in table:
        return table[code]
    return table.get(DEFAULT_LANG)


def render_all_locales(key: str, **kwargs) -> dict:
    """Dung san mot ban dich cho moi locale, de broadcast khong format N lan.

    Vong lap broadcast truoc day dung text MOT lan roi gui cho tat ca, nen khach
    en/zh luon nhan tieng Viet. Goi t() trong vong lap thi dung ngon ngu nhung
    doi so lan format tu 1 thanh N. Ham nay format dung ba lan, roi moi nguoi
    nhan chi con mot phep tra dict qua pick_locale().
    """
    return {code: t(key, lang=code, **kwargs) for code in SUPPORTED_LANGS}


def lt(user_id, vi: str, en: str, zh: str, **kwargs) -> str:
    """Select and format one inline user-facing translation."""
    text = pick_locale({"vi": vi, "en": en, "zh": zh}, get_user_lang(user_id))
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, ValueError, IndexError):
        return text


def get_main_menu_text(user_id=None, lang=None) -> str:
    success = E_SUCCESS if "E_SUCCESS" in globals() else "✅"
    return t("main_menu_title", user_id=user_id, lang=lang, success=success)


def create_language_menu(user_id=None):
    current = get_user_lang(user_id)
    # Nhan ngon ngu dung endonym (`Tiếng Việt` / `English` / `中文`) tu STRINGS,
    # khong dung ten tieng Viet ("Anh", "China") vi khach en/zh cung doc man nay.
    flags = {"vi": "🇻🇳", "zh": "🇨🇳", "en": "🇬🇧"}
    icons = {
        "vi": "6296529082226054237",
        "zh": "6118278546348575756",
        "en": "6118484374066302696",
    }
    rows = [
        [_btn(
            f'{lang_display_name(code, user_id=user_id)} {flags[code]}',
            icon_id=icons[code],
            callback_data=f"set_lang:{code}",
            style="primary" if current != code else "success",
        )]
        for code in ("vi", "zh", "en")
    ]
    rows.append(
        [_btn(t("btn_back", user_id=user_id), icon_id="6206032691075223572", callback_data="back_to_main")]
    )
    return InlineKeyboardMarkup(rows)

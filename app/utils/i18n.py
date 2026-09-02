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
    rows = [
        [_btn("Việt Nam 🇻🇳", icon_id="6296529082226054237", callback_data="set_lang:vi", style="primary" if current != "vi" else "success")],
        [_btn("China 🇨🇳", icon_id="6118278546348575756", callback_data="set_lang:zh", style="primary" if current != "zh" else "success")],
        [_btn("Anh 🇬🇧", icon_id="6118484374066302696", callback_data="set_lang:en", style="primary" if current != "en" else "success")],
        [_btn(t("btn_back", user_id=user_id), icon_id="6206032691075223572", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(rows)

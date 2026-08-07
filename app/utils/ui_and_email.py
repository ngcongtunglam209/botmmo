MAIN_MENU_TEXT = get_main_menu_text()


def build_main_menu_account_summary(user_id=None):
    import re
    try:
        target_user_id = int(user_id or 0)
    except (TypeError, ValueError):
        return ""
    if target_user_id <= 0:
        return ""
    try:
        from app.services.games_withdrawals_db import db_get_user
        balance = int((db_get_user(target_user_id) or {}).get("balance", 0) or 0)
    except (TypeError, ValueError, KeyError, AttributeError, ImportError):
        balance = 0
    rank_name = t("rank_label", user_id=target_user_id)
    try:
        from app.services.referrals_stats import get_user_rank
        rank_info = get_user_rank(target_user_id)
        raw = str((rank_info.get("rank") or {}).get("name", "") or "")
        rank_name = re.sub(r"<[^>]+>", "", raw).strip() or rank_name
    except Exception:
        pass
    return f"🏅 <b>Hạng hiện tại:</b> {rank_name}\n💰 <b>Số dư:</b> <b>{balance:,} VNĐ</b>\n\n"


def build_main_menu_status_button_text(user_id=None):
    import re
    try:
        target_user_id = int(user_id or 0)
    except (TypeError, ValueError):
        return None
    if target_user_id <= 0:
        return None
    try:
        from app.services.games_withdrawals_db import db_get_user
        balance = int((db_get_user(target_user_id) or {}).get("balance", 0) or 0)
    except (TypeError, ValueError, KeyError, AttributeError, ImportError):
        balance = 0
    rank_name = t("rank_label", user_id=target_user_id)
    try:
        from app.services.referrals_stats import get_user_rank
        rank_info = get_user_rank(target_user_id)
        raw = str((rank_info.get("rank") or {}).get("name", "") or "")
        rank_name = re.sub(r"<[^>]+>", "", raw).strip() or rank_name
    except Exception:
        pass
    return t("rank_balance", user_id=target_user_id, rank=rank_name, balance=balance)


HUONGDAN_TEXT = (
    '<tg-emoji emoji-id="5321466670177330155">📖</tg-emoji> <b>HƯỚNG DẪN SỬ DỤNG DINO STORE</b>\n'
    '<i>Cập nhật: 06/08/2026</i>\n\n'
    '<b>1. Chọn sản phẩm</b>\n'
    '• Vào <b>Mua Hàng</b> → chọn danh mục → chọn sản phẩm.\n'
    '• Đọc kỹ mô tả, giá hiện tại, tồn kho, thời hạn và điều kiện bảo hành.\n'
    '• Với sản phẩm resell, bấm <b>Làm mới giá &amp; tồn kho</b> trước khi đặt.\n\n'
    '<b>2. Chọn số lượng và thanh toán</b>\n'
    '• Chọn số lượng → kiểm tra tổng tiền → chọn Ví, QR ngân hàng, Binance Pay hoặc USDT nếu đang được hỗ trợ.\n'
    '• Với QR: chuyển <b>đúng số tiền</b> và <b>đúng nội dung</b> trước giờ hết hạn.\n'
    '• Không sửa nội dung chuyển khoản và không dùng lại QR của đơn cũ.\n'
    '• Nếu chuyển sai, giữ biên lai và liên hệ hỗ trợ để đối soát; không tự chuyển thêm lần nữa.\n\n'
    '<b>3. Nhận sản phẩm</b>\n'
    '• Đơn tự động: sản phẩm được giao ngay trong Telegram sau khi hệ thống xác nhận thanh toán.\n'
    '• Đơn manual: làm theo yêu cầu nhập email/thông tin và chờ Admin xử lý.\n'
    '• Xem lại nội dung tại <b>Đã Mua</b> → chọn đơn → <b>Lấy lại thông tin đơn hàng</b>.\n'
    '• Có thể dùng <b>Mua lại sản phẩm này</b>; hệ thống luôn áp dụng giá và tồn kho hiện tại.\n\n'
    '<b>4. Dịch vụ Social Media</b>\n'
    '• Chọn đúng dịch vụ, nhập số lượng trong giới hạn và dán đúng link cần chạy.\n'
    '• Không đổi username, xóa bài, khóa tài khoản hoặc sửa link khi đơn đang chạy.\n'
    '• Trạng thái, số lượng còn lại và tiến độ phụ thuộc dữ liệu từ nhà cung cấp.\n\n'
    '<b>5. Báo lỗi và bảo hành</b>\n'
    '• Vào <b>Đã Mua</b> → chọn đơn → <b>Báo lỗi đơn này</b>.\n'
    '• Gửi mã đơn, ảnh/video lỗi và mô tả thao tác đã thử.\n'
    '• Không thay đổi mật khẩu, email khôi phục hoặc chia sẻ tài khoản trước khi được kiểm tra.\n\n'
    '<b>6. An toàn tài khoản</b>\n'
    '• Dino Store không yêu cầu gửi mật khẩu ngân hàng, OTP hoặc mã xác thực ví.\n'
    '• Không chia sẻ API key, mã đơn hoặc nội dung sản phẩm tại nơi công khai.\n\n'
    '<b>Cần hỗ trợ?</b> Chọn <b>Hỗ Trợ &amp; Liên Hệ</b> trong menu chính và gửi đầy đủ mã đơn cùng bằng chứng.'
)

CHINHSACH_TEXT = (
    '<tg-emoji emoji-id="5321466670177330155">📜</tg-emoji> <b>CHÍNH SÁCH DINO STORE</b>\n'
    '<i>Cập nhật: 06/08/2026</i>\n\n'
    '<b>1. Phạm vi áp dụng</b>\n'
    'Khi tạo đơn, người mua xác nhận đã đọc mô tả sản phẩm, giá, số lượng, phương thức giao và chính sách liên quan hiển thị tại thời điểm đặt hàng.\n\n'
    '<b>2. Giá và thanh toán</b>\n'
    '• Giá có thể thay đổi theo nguồn cung; đơn được tính theo mức giá hiển thị tại bước xác nhận cuối.\n'
    '• Chỉ thanh toán bằng phương thức do bot cung cấp và dùng đúng mã/nội dung của đơn.\n'
    '• Giao dịch sai số tiền, sai nội dung hoặc sau thời hạn có thể cần đối soát thủ công.\n'
    '• QR chỉ dùng cho đơn hàng hợp pháp. Nghiêm cấm gian lận, rửa tiền, chiếm đoạt tài sản và mọi hành vi trái pháp luật.\n\n'
    '<b>3. Giao hàng</b>\n'
    '• Thời gian giao phụ thuộc loại sản phẩm: tự động, manual, resell hoặc Social Media.\n'
    '• Người mua phải kiểm tra sản phẩm ngay sau khi nhận và bảo quản thông tin an toàn.\n'
    '• Không công khai hoặc bán lại nội dung nếu sản phẩm/nhà cung cấp không cho phép.\n\n'
    '<b>4. Bảo hành</b>\n'
    '• Chỉ áp dụng trong thời hạn và phạm vi ghi tại sản phẩm hoặc đơn hàng.\n'
    '• Cần cung cấp mã đơn và bằng chứng lỗi để kiểm tra.\n'
    '• Không bảo hành lỗi do đổi mật khẩu/email khôi phục, chia sẻ nhiều người, sử dụng sai hướng dẫn, vi phạm điều khoản nền tảng hoặc tự ý can thiệp sản phẩm.\n'
    '• Dịch vụ Social Media chỉ được refill/bù tụt khi dịch vụ có ghi rõ hỗ trợ và người mua giữ nguyên điều kiện cần thiết.\n\n'
    '<b>5. Hủy đơn và hoàn tiền</b>\n'
    '• Đơn chưa thanh toán có thể hủy trước khi hết hạn. Phần tiền ví đã giữ sẽ được hoàn theo trạng thái hệ thống.\n'
    '• Xem xét hoàn tiền khi hệ thống trừ tiền nhưng không tạo được đơn, giao trùng hoặc nhà cung cấp xác nhận hủy/hoàn một phần.\n'
    '• Sản phẩm số đã giao đúng và đã sử dụng thường không được hoàn, trừ trường hợp thuộc phạm vi bảo hành hoặc có lỗi được xác minh.\n'
    '• Đơn lỗi đã sử dụng một phần được hoàn theo số ngày nguyên còn lại chưa sử dụng; ngày đã bắt đầu được tính là một ngày đã dùng.\n'
    '• Khoản hoàn dưới 200.000 VNĐ được hoàn vào Ví Bot. Khoản hoàn từ 200.000 VNĐ trở lên có thể yêu cầu chuyển về ngân hàng sau khi cung cấp đúng thông tin và được Admin xác nhận.\n'
    '• Yêu cầu chuyển về ngân hàng sẽ tạm trừ đúng khoản hoàn khỏi Ví Bot; nếu bị từ chối, tiền được trả lại Ví Bot.\n'
    '• Thời gian xử lý phụ thuộc việc đối soát ngân hàng, ví và nhà cung cấp.\n\n'
    '<b>6. Dữ liệu và quyền riêng tư</b>\n'
    '• Bot chỉ sử dụng thông tin cần thiết để tạo đơn, giao hàng, hỗ trợ, chống gian lận và đối soát.\n'
    '• Không gửi mật khẩu ngân hàng, OTP, khóa ví hoặc dữ liệu không cần thiết.\n'
    '• Thông tin có thể được cung cấp cho đơn vị xử lý liên quan hoặc cơ quan có thẩm quyền khi pháp luật yêu cầu.\n\n'
    '<b>7. Hành vi bị cấm</b>\n'
    '• Dùng sản phẩm cho lừa đảo, spam, xâm nhập trái phép, phát tán mã độc, đánh cắp dữ liệu hoặc nội dung vi phạm pháp luật.\n'
    '• Lợi dụng lỗi hệ thống, tạo giao dịch giả, hoàn tiền gian lận hoặc cố tình tạo đơn trùng.\n'
    '• Dino Store có thể từ chối xử lý và yêu cầu xác minh khi phát hiện dấu hiệu bất thường.\n\n'
    '<b>8. Khiếu nại và hỗ trợ</b>\n'
    'Gửi yêu cầu qua <b>Hỗ Trợ &amp; Liên Hệ</b>, kèm mã đơn, thời gian, nội dung và bằng chứng. Hai bên ưu tiên kiểm tra dữ liệu hệ thống và trao đổi để giải quyết minh bạch.\n\n'
    '<i>Chính sách này là thông tin giao dịch của Dino Store và không thay thế quy định pháp luật hiện hành.</i>'
)


def _btn(text, icon_id=None, **kwargs):
    api_kwargs = dict(kwargs.pop('api_kwargs', {}) or {})
    style = kwargs.pop('style', None)
    if icon_id:
        api_kwargs['icon_custom_emoji_id'] = icon_id
    if style:
        api_kwargs['style'] = style
    if api_kwargs:
        kwargs['api_kwargs'] = api_kwargs
    return InlineKeyboardButton(text, **kwargs)


def _normalize_public_api_url(value: str) -> str:
    url = str(value or "").strip().rstrip("/")
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        scheme = "https" if PUBLIC_API_SCHEME == "https" else "http"
        url = f"{scheme}://{url}"
    return url


def get_public_api_base_url() -> str:
    normalized = _normalize_public_api_url(PUBLIC_API_URL)
    if normalized:
        return normalized
    return f"http://YOUR_VPS_IP:{API_SERVER_PORT}"


def _sanitize_public_endpoint_error(error_obj) -> str:
    """Hide sensitive token data in public endpoint error logs."""
    return _redact_sensitive_text(error_obj)


def get_query_message_html(query) -> str:
    message = getattr(query, "message", None)
    if not message:
        return ""
    for attr in ("text_html", "caption_html", "text", "caption"):
        value = getattr(message, attr, None)
        if value:
            return value
    return ""


def get_partner_api_entry_by_user(user_id: int):
    try:
        target_uid = int(user_id)
    except (TypeError, ValueError):
        return None, None
    for key, data in api_keys.items():
        if not isinstance(data, dict) or data.get("enabled") is False:
            continue
        try:
            if int(data.get("user_id", 0)) == target_uid:
                return key, data
        except (TypeError, ValueError):
            continue
    return None, None
def _legacy_create_main_menu_v1(user_id=None):
    keyboard = [
        [_btn("Mua Hàng", icon_id="5247134066322447995", callback_data='store_main'), _btn("Đã Mua", icon_id="5444856076954520455", callback_data='lichsu_entry')],
        [_btn("Vòng Quay", icon_id="5226711870492126219", callback_data='lucky_wheel_menu'), _btn("Xúc Xắc", icon_id="6201668110949291585", callback_data='play_dice_game'), _btn("Kiếm Tiền", icon_id="5193085063998224234", callback_data='my_referral')],
        [_btn("Tài Khoản & Số Dư", icon_id="4967667085606912536", callback_data='my_stats'), _btn("HD & CS", icon_id="5321466670177330155", callback_data='huongdan')],
        [_btn("Hỗ Trợ & Liên Hệ", icon_id="5462921117423384478", callback_data='lienhe_admin'), _btn("Báo Lỗi", icon_id="5273914604752216432", callback_data='guide_baoloi_menu')],
        [_btn("Nhóm Cộng đồng", icon_id="5443038326535759644", url=SUPPORT_GROUP_LINK)]
    ]

    partner_api_key = None
    if user_id:
        partner_api_key, _ = get_partner_api_entry_by_user(user_id)
    if partner_api_key:
        keyboard.insert(
            3,
            [
                _btn("API Partner", icon_id="5436359785534466562", callback_data='api_member_menu'),
                _btn("Nạp Ví", icon_id="5278467510604160626", callback_data='api_member_wallet'),
            ]
        )
    elif user_id and user_id != ADMIN_USER_ID:
        keyboard.insert(
            3,
            [
                _btn("Đăng Ký API", icon_id="5436359785534466562", callback_data='api_register_request'),
                _btn("HD API", icon_id="5350481781306958339", callback_data='api_register_guide')
            ]
        )

    if user_id == ADMIN_USER_ID:
        keyboard.append([_btn("Bảng Điều Khiển Admin", icon_id="6129805886383723340", callback_data='adm:home')])
    return InlineKeyboardMarkup(keyboard)

def _legacy_create_main_menu_v2(user_id=None):
    keyboard = [
        [_btn("Mua Hàng", icon_id="5247134066322447995", callback_data='store_main'), _btn("Đã Mua", icon_id="5444856076954520455", callback_data='lichsu_entry')],
        [_btn("Game", icon_id="5226711870492126219", callback_data='games_menu'), _btn("Kiếm Tiền", icon_id="5193085063998224234", callback_data='my_referral')],
        [_btn("Tài Khoản & Số Dư", icon_id="4967667085606912536", callback_data='my_stats'), _btn("HD & CS", icon_id="5321466670177330155", callback_data='huongdan')],
        [_btn("Hỗ Trợ & Liên Hệ", icon_id="5462921117423384478", callback_data='lienhe_admin'), _btn("Báo Lỗi", icon_id="5273914604752216432", callback_data='guide_baoloi_menu')],
        [_btn("Nhóm Cộng Đồng", icon_id="5443038326535759644", url=SUPPORT_GROUP_LINK)]
    ]

    partner_api_key = None
    if user_id:
        partner_api_key, _ = get_partner_api_entry_by_user(user_id)
    if partner_api_key:
        keyboard.insert(
            3,
            [
                _btn("API Partner", icon_id="5436359785534466562", callback_data='api_member_menu'),
                _btn("Nạp Ví", icon_id="5278467510604160626", callback_data='api_member_wallet'),
            ]
        )
    elif user_id and user_id != ADMIN_USER_ID:
        keyboard.insert(
            3,
            [
                _btn("Đăng Ký API", icon_id="5436359785534466562", callback_data='api_register_request'),
                _btn("HD API", icon_id="5350481781306958339", callback_data='api_register_guide')
            ]
        )

    if user_id == ADMIN_USER_ID:
        keyboard.append([_btn("Bảng Điều Khiển Admin", icon_id="6129805886383723340", callback_data='adm:home')])
    return InlineKeyboardMarkup(keyboard)


def create_main_menu(user_id=None):
    keyboard = [
        [
            _btn(t("btn_shop", user_id=user_id), icon_id="5247134066322447995", callback_data='store_main', style="primary"),
            _btn(t("btn_purchased", user_id=user_id), icon_id="5444856076954520455", callback_data='lichsu_entry', style="primary"),
        ],
        [
            _btn(t("btn_game", user_id=user_id), icon_id="5226711870492126219", callback_data='games_menu', style="primary"),
            _btn(t("btn_earn", user_id=user_id), icon_id="5193085063998224234", callback_data='my_referral', style="primary"),
        ],
        [
            _btn(t("btn_wallet", user_id=user_id), icon_id="4967667085606912536", callback_data='my_stats', style="primary"),
            _btn(t("btn_guide", user_id=user_id), icon_id="5321466670177330155", callback_data='huongdan', style="primary"),
        ],
        [
            _btn(t("btn_support", user_id=user_id), icon_id="5462921117423384478", callback_data='lienhe_admin', style="primary"),
            _btn(t("btn_report", user_id=user_id), icon_id="5273914604752216432", callback_data='guide_baoloi_menu', style="primary"),
        ],
        [
            _btn(t("btn_community", user_id=user_id), icon_id="5443038326535759644", url=SUPPORT_GROUP_LINK, style="primary"), _btn(t("btn_language", user_id=user_id), icon_id="5816436147525522455", callback_data='language_menu', style="primary"),
        ],
    ]

    status_button_text = build_main_menu_status_button_text(user_id)
    if status_button_text:
        keyboard.insert(
            0,
            [_btn(status_button_text, icon_id="6059654836918423763", callback_data='ignore', style="success")]
        )

    partner_api_key = None
    if user_id:
        partner_api_key, _ = get_partner_api_entry_by_user(user_id)
    if partner_api_key:
        keyboard.insert(
            3,
            [
                _btn(t("btn_api_partner", user_id=user_id), icon_id="5436359785534466562", callback_data='api_member_menu', style="primary"),
                _btn(t("btn_api_topup", user_id=user_id), icon_id="5278467510604160626", callback_data='api_member_wallet', style="primary"),
            ]
        )
    elif user_id and user_id != ADMIN_USER_ID:
        keyboard.insert(
            3,
            [
                _btn(t("btn_api_register", user_id=user_id), icon_id="5436359785534466562", callback_data='api_register_request', style="primary"),
                _btn(t("btn_api_guide", user_id=user_id), icon_id="5350481781306958339", callback_data='api_register_guide', style="primary"),
            ]
        )

    if user_id == ADMIN_USER_ID:
        from telegram import WebAppInfo

        admin_web_url = f"{get_public_api_base_url()}/admin"
        keyboard.append([
            _btn(t("btn_admin", user_id=user_id), icon_id="6129805886383723340", callback_data='adm:home', style="primary")
        ])
        keyboard.append([
            _btn(t("btn_admin_web", user_id=user_id), icon_id="5231489647946768652", web_app=WebAppInfo(url=admin_web_url), style="primary")
        ])
    return InlineKeyboardMarkup(keyboard)


def create_games_menu(user_id=None):
    return InlineKeyboardMarkup([
        [_btn(t("btn_wheel", user_id=user_id), icon_id="5226711870492126219", callback_data='lucky_wheel_menu')],
        [_btn(t("btn_dice", user_id=user_id), icon_id="6201668110949291585", callback_data='play_dice_game')],
        [_btn(t("btn_back_main", user_id=user_id), icon_id="5247134066322447995", callback_data='back_to_main')],
    ])


def create_guide_policy_menu(active: str = "guide"):
    guide_text = "• Hướng dẫn" if active == "guide" else "Hướng dẫn"
    policy_text = "• Chính sách" if active == "policy" else "Chính sách"
    return InlineKeyboardMarkup([
        [
            _btn(guide_text, icon_id="5321466670177330155", callback_data="huongdan", style="primary" if active == "guide" else None),
            _btn(policy_text, icon_id="6037266106832041274", callback_data="chinhsach", style="primary" if active == "policy" else None),
        ],
        [_btn("Quay Lại Menu Chính", icon_id="6206032691075223572", callback_data="back_to_main")],
    ])


def create_back_button_menu(text="⬅️ Quay Lại Menu Chính", callback="back_to_main"): return InlineKeyboardMarkup([[_btn(text, icon_id="6206032691075223572", callback_data=callback)]])
def create_success_menu(): return InlineKeyboardMarkup([ [_btn("Cần hỗ trợ / Báo lỗi đơn hàng", icon_id="5273914604752216432", callback_data='report_error')], [_btn("Quay Lại Menu Chính", icon_id="6206032691075223572", callback_data='back_to_main')] ])

# ===================== EMAIL HELPERS =====================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _send_email_sync(recipient_email: str, subject: str, full_name: str, activation_link: str):
    """
    FIX BUG #2: Thêm retry logic để đảm bảo email được gửi
    Retry 3 lần với exponential backoff
    """
    if not ENABLE_EMAIL_SENDING:
        logger.info("<tg-emoji emoji-id=\"6129860303619363484\">📧</tg-emoji> Tính năng gửi email đang tắt.")
        return False, "Disabled by config"
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        logger.error("❌ Missing SMTP credentials: SENDER_EMAIL/SENDER_APP_PASSWORD")
        return False, "Missing SMTP credentials"
    
    html_body = f'''<html><head><style>body{{font-family:Arial,sans-serif;line-height:1.6;color:#333}}.container{{max-width:600px;margin:20px auto;padding:20px;border:1px solid #ddd;border-radius:10px}}.button{{display:inline-block;background-color:#007aff;color:white!important;padding:15px 25px;text-align:center;text-decoration:none;border-radius:8px;font-size:18px;font-weight:700;margin:20px 0}}h2{{color:#0056b3}}hr{{border:0;border-top:1px solid #eee;margin:20px 0}}.guide{{background-color:#f9f9f9;padding:15px;border-radius:8px;margin-top:20px;border-left:4px solid #007aff}}</style></head><body><div class="container"><h2>{E_SUCCESS} Chúc Mừng Bạn Đã Đăng Ký Thành Công Gói iCloud 2TB!</h2><p>Xin chào <b>{full_name}</b>,</p><p>Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ của me. Link kích hoạt gói dung lượng của bạn đã sẵn sàng.</p><p style="text-align:center">Vui lòng nhấp vào nút bên dưới để kích hoạt ngay lập tức:</p><p style="text-align:center"><a href="{activation_link}" class="button">KÍCH HOẠT NGAY</a></p>
    
    <div class="guide">
        <h3>{E_TIP} HƯỚNG DẪN KIỂM TRA iCLOUD 2TB ĐÃ ĐƯỢC CHIA SẺ</h3>
        <p>{E_LOADING}{E_LOADING} <b>1.</b> Vào <b>Cài đặt</b> > Nhấn vào tên tài khoản Apple ở trên cùng.</p>
        <p>{E_LOADING}{E_LOADING} <b>2.</b> Chọn <b>Gia đình</b> > Kiểm tra có tên bạn trong danh sách thành viên.</p>
        <p>{E_LOADING}{E_LOADING} <b>3.</b> Vào mục <b>Đăng ký</b> > Xem có hiển thị <b>iCloud+ – Được chia sẻ</b>.</p>
        <p>{E_LOADING}{E_LOADING} <b>4.</b> Quay lại <b>Cài đặt</b> > <b>iCloud</b> > Chọn <b>Sử dụng dung lượng của Gia đình</b> để kiểm tra bạn đã dùng gói <tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji></p>
        
        <div style="text-align:center; margin-top:15px">
             <img src="{INSTRUCTION_IMAGE_URL}" alt="Hình ảnh hướng dẫn" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #ddd;">
        </div>
    </div>

    <hr><p>Nếu có bất kỳ câu hỏi nào, vui lòng liên hệ admin qua Telegram hoặc tham gia nhóm hỗ trợ của chúng tôi.</p><p>Trân trọng,<br><b>DinoTools Team</b></p></div></body></html>'''
    
    msg = MIMEText(html_body, 'html', 'utf-8')
    msg['Subject'], msg['From'], msg['To'] = subject, f"DinoTools iCloud Store <{SENDER_EMAIL}>", recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp_server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        logger.info(f"{E_SUCCESS} Đã gửi email thành công đến {recipient_email}")
        return True, "Success"
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Lỗi không xác định khi gửi email đến {recipient_email}: {e}")
        return False, str(e)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _send_api_email_sync(recipient_email: str, subject: str, link: str):
    """
    FIX BUG #2: Gửi email ẩn danh với retry logic
    """
    if not ENABLE_EMAIL_SENDING:
        return False, "Disabled by config"
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        logger.error("❌ Missing SMTP credentials: SENDER_EMAIL/SENDER_APP_PASSWORD")
        return False, "Missing SMTP credentials"

    html_body = f'''<html><head><style>body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;background-color:#f9f9f9;margin:0;padding:20px}}.container{{max-width:600px;margin:0 auto;padding:30px;background:#ffffff;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}}.button{{display:inline-block;background-color:#007aff;color:white!important;padding:15px 30px;text-align:center;text-decoration:none;border-radius:8px;font-size:16px;font-weight:bold;margin:20px 0}}.steps{{background-color:#f2f7ff;padding:20px;border-radius:8px;margin-top:20px}}h2{{color:#007aff;margin-top:0}}.note{{font-size:13px;color:#666;font-style:italic}}</style></head><body><div class="container"><h2>{E_SUCCESS} Kích hoạt gói dịch vụ</h2><p>Xin chào,</p><p>Cảm ơn bạn đã tin tưởng sử dụng dịch vụ. Gói dung lượng của bạn đã sẵn sàng.</p><p style="text-align:center"><a href="{link}" class="button">KÍCH HOẠT NGAY</a></p><div class="steps"><h3>{E_TAG} Hướng dẫn kích hoạt:</h3><ol><li>Bấm vào nút <b>KÍCH HOẠT NGAY</b> ở trên.</li><li>Đăng nhập vào tài khoản Icloud của bạn (nếu được yêu cầu).</li><li>Chọn <b>"Tham gia gia đình" (Join Family)</b> để hoàn tất.</li></ol><p class="note">{E_ERROR} Lưu ý: Mỗi link chỉ sử dụng được cho 1 tài khoản.</p></div><hr style="border:0;border-top:1px solid #eee;margin:30px 0"><p>Trân trọng,<br>Service Store</p></div></body></html>'''
    
    msg = MIMEText(html_body, 'html', 'utf-8')
    # Generic sender name
    msg['Subject'], msg['From'], msg['To'] = subject, f"Service Store <{SENDER_EMAIL}>", recipient_email
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            smtp_server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        logger.info(f"{E_SUCCESS} Đã gửi email API thành công đến {recipient_email}")
        return True, "Success"
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Lỗi gửi email API đến {recipient_email}: {e}")
        return False, str(e)

async def send_activation_email(recipient_email: str, subject: str, full_name: str, activation_link: str):
    """Wrapper bất đồng bộ để gửi email không chặn bot"""
    return await asyncio.to_thread(_send_email_sync, recipient_email, subject, full_name, activation_link)

async def send_api_email(recipient_email: str, link: str):
    """Wrapper gửi email API (Ẩn danh)"""
    return await asyncio.to_thread(_send_api_email_sync, recipient_email, "Thông tin đơn hàng - Kích hoạt ngay", link)

# ===================== QR CODE HELPERS =====================

def generate_secret_transfer_code(length: int = 6):
    digits = "0123456789"
    try:
        length = int(length or 0)
    except (TypeError, ValueError):
        length = 6
    if length <= 0:
        length = 6
    for _ in range(200):
        secret_code = ''.join(random.choices(digits, k=length))
        if not any(
            isinstance(order_data, dict) and str(order_data.get("secret_transfer_code") or "").strip().lower() == secret_code
            for order_data in pending_orders.values()
        ):
            return secret_code
    return ''.join(random.choices(digits, k=length))

def build_transfer_content(secret_code):
    return random.choice((
        "Em yeu anh xxx",
        "Chuc mung sinh nhat xxx",
        "Xin chao ban xxx",
        "Dem qua em tuyet lam xxx",
        "Hom nay an com chua xxx",
        "Ca phe sang nhe xxx",
        "Nho que qua troi xxx",
        "Tet nay ve nha xxx",
        "Di an pho nhe xxx",
        "Bun bo ngon qua xxx",
        "Com tam dinh qua xxx",
        "An lau khong ban xxx",
        "Hen nhau cuoi tuan xxx",
        "Troi oi nong qua xxx",
        "Mua roi do ban xxx",
        "Ra ngo uong tra da xxx",
        "Nho me nau canh chua xxx",
        "Nho mui lua dong xxx",
        "Qua nha choi nhe xxx",
        "Cho em xin gia tot xxx",
        "Chot don nhanh nhe xxx",
        "Lam an phat tai xxx",
        "Tien vao nhu nuoc xxx",
        "Mau hong phat nhe xxx",
        "Dau nam may man xxx",
        "Cuoi nam trung lon xxx",
        "Binh an va hanh phuc xxx",
        "Van su nhu y xxx",
        "Chuc ban phat loc xxx",
        "Chuc mung khai truong xxx",
        "Chuc mung tan gia xxx",
        "Mot doi an nhan xxx",
        "An khang thinh vuong xxx",
        "Vui nhu trung Tet xxx",
        "Chieu nay di bao xxx",
        "Cuoi tuan ve ben xxx",
        "Nho em nhieu lam xxx",
        "Thuong nhau den gia xxx",
        "Tinh nghia anh em xxx",
        "Song chan thanh nhe xxx",
        "Cho doi mot nguoi xxx",
        "Mong ngay gap lai xxx",
        "An no roi ha xxx",
        "Ngu ngon nhe xxx",
        "Day som an sang xxx",
        "Minh cung co gang xxx",
        "Co len nha minh xxx",
        "Thuong doi chut thoi xxx",
        "Song cham lai nhe xxx",
        "Chuyen nay de em lo xxx",
    )).replace("xxx", str(secret_code))

def create_vietqr_link(amount, add_info):
    """Tạo link QR qua API SePay.vn chuẩn hóa"""
    try:
        encoded_add_info = quote(add_info)
        # Sử dụng API SePay theo chuẩn tài liệu:
        # Template để trống sẽ lấy mặc định là "Khung VietQR" có logo Napas247 rất đẹp
        return f"https://qr.sepay.vn/img?acc={BANK_ACCOUNT_NUMBER}&bank={BANK_ID}&amount={amount}&des={encoded_add_info}"
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error creating SePay QR link: {e}")
        return None


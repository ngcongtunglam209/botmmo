MAIN_MENU_TEXT = get_main_menu_text()


def _localized_rank_name(target_user_id) -> str:
    """Ten hang cua khach, da dich va da bo the emoji (dung duoc trong nut)."""
    import re

    try:
        from app.services.referrals_stats import format_rank_entry_premium, get_user_rank
        rank_info = get_user_rank(target_user_id)
        name = format_rank_entry_premium(rank_info.get("rank") or {}, user_id=target_user_id)
        cleaned = re.sub(r"<[^>]+>", "", name).strip()
        if cleaned:
            return cleaned
    except Exception:
        pass
    return t("rank_label", user_id=target_user_id)


def build_main_menu_account_summary(user_id=None):
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
    rank_name = _localized_rank_name(target_user_id)
    return lt(
        target_user_id,
        "🏅 <b>Hạng hiện tại:</b> {rank}\n💰 <b>Số dư:</b> <b>{balance}</b>\n\n",
        "🏅 <b>Current rank:</b> {rank}\n💰 <b>Balance:</b> <b>{balance}</b>\n\n",
        "🏅 <b>当前等级：</b>{rank}\n💰 <b>余额：</b><b>{balance}</b>\n\n",
        rank=rank_name,
        balance=format_money(balance, target_user_id),
    )


def build_main_menu_status_button_text(user_id=None):
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
    return t(
        "rank_balance",
        user_id=target_user_id,
        rank=_localized_rank_name(target_user_id),
        balance=format_money(balance, target_user_id),
    )


HUONGDAN_TEXT_VI = (
    '<tg-emoji emoji-id="5321466670177330155">📖</tg-emoji> <b>HƯỚNG DẪN SỬ DỤNG LÂM SHOP</b>\n'
    '<i>Cập nhật: 06/08/2026</i>\n\n'
    '<b>1. Chọn sản phẩm</b>\n'
    '• Vào <b>Mua Hàng</b> → chọn danh mục → chọn sản phẩm.\n'
    '• Đọc kỹ mô tả, giá hiện tại, tồn kho, thời hạn và điều kiện bảo hành.\n'
    '<b>2. Chọn số lượng và thanh toán</b>\n'
    '• Chọn số lượng → kiểm tra tổng tiền → chọn Ví, QR ngân hàng, Crypto (NOWPayments) hoặc Binance Pay nếu đang được hỗ trợ.\n'
    '• Với QR: chuyển <b>đúng số tiền</b> và <b>đúng nội dung</b> trước giờ hết hạn.\n'
    '• Không sửa nội dung chuyển khoản và không dùng lại QR của đơn cũ.\n'
    '• Nếu chuyển sai, giữ biên lai và liên hệ hỗ trợ để đối soát; không tự chuyển thêm lần nữa.\n\n'
    '<b>3. Nhận sản phẩm</b>\n'
    '• Đơn tự động: sản phẩm được giao ngay trong Telegram sau khi hệ thống xác nhận thanh toán.\n'
    '• Đơn manual: làm theo yêu cầu nhập email/thông tin và chờ Admin xử lý.\n'
    '• Xem lại nội dung tại <b>Đã Mua</b> → chọn đơn → <b>Lấy lại thông tin đơn hàng</b>.\n'
    '• Có thể dùng <b>Mua lại sản phẩm này</b>; hệ thống luôn áp dụng giá và tồn kho hiện tại.\n\n'
    '<b>4. Báo lỗi và bảo hành</b>\n'
    '• Vào <b>Đã Mua</b> → chọn đơn → <b>Báo lỗi đơn này</b>.\n'
    '• Gửi mã đơn, ảnh/video lỗi và mô tả thao tác đã thử.\n'
    '• Không thay đổi mật khẩu, email khôi phục hoặc chia sẻ tài khoản trước khi được kiểm tra.\n\n'
    '<b>5. An toàn tài khoản</b>\n'
    '• Lâm Shop không yêu cầu gửi mật khẩu ngân hàng, OTP hoặc mã xác thực ví.\n'
    '• Không chia sẻ API key, mã đơn hoặc nội dung sản phẩm tại nơi công khai.\n\n'
    '<b>Cần hỗ trợ?</b> Chọn <b>Hỗ Trợ &amp; Liên Hệ</b> trong menu chính và gửi đầy đủ mã đơn cùng bằng chứng.'
)

HUONGDAN_TEXT_EN = (
    '<tg-emoji emoji-id="5321466670177330155">📖</tg-emoji> <b>HOW TO USE LÂM SHOP</b>\n'
    '<i>Updated: 06/08/2026</i>\n\n'
    '<b>1. Pick a product</b>\n'
    '• Open <b>Shop</b> → choose a category → choose a product.\n'
    '• Read the description, current price, stock, duration and warranty terms carefully.\n'
    '<b>2. Choose the quantity and pay</b>\n'
    '• Pick the quantity → check the total → pay with your wallet, bank QR, Crypto (NOWPayments) or Binance Pay where available.\n'
    '• With QR: transfer the <b>exact amount</b> with the <b>exact reference</b> before the deadline.\n'
    '• Do not edit the transfer reference and do not reuse the QR of an older order.\n'
    '• If you sent the wrong amount, keep the receipt and contact support so we can reconcile it. Do not send a second transfer.\n\n'
    '<b>3. Receive the product</b>\n'
    '• Automatic orders: delivered in Telegram as soon as the payment is confirmed.\n'
    '• Manual orders: follow the prompt for your email or details and wait for the admin.\n'
    '• You can read the details again under <b>Purchased</b> → pick the order → <b>Resend order details</b>.\n'
    '• <b>Buy this product again</b> is available too; it always uses the current price and stock.\n\n'
    '<b>4. Reporting a problem and warranty</b>\n'
    '• Go to <b>Purchased</b> → pick the order → <b>Report a problem</b>.\n'
    '• Send the order code, a screenshot or video of the problem, and what you already tried.\n'
    '• Do not change the password or recovery email, and do not share the account, before we have checked it.\n\n'
    '<b>5. Account safety</b>\n'
    '• Lâm Shop never asks for your banking password, an OTP or a wallet verification code.\n'
    '• Never post your API key, order code or product contents in public.\n\n'
    '<b>Need help?</b> Choose <b>Support &amp; Contact</b> in the main menu and include the order code and your evidence.'
)

HUONGDAN_TEXT_ZH = (
    '<tg-emoji emoji-id="5321466670177330155">📖</tg-emoji> <b>LÂM SHOP 使用指南</b>\n'
    '<i>更新时间：2026/08/06</i>\n\n'
    '<b>1. 选择商品</b>\n'
    '• 进入<b>购买</b> → 选择分类 → 选择商品。\n'
    '• 请仔细阅读商品说明、当前价格、库存、有效期与保修条件。\n'
    '<b>2. 选择数量并付款</b>\n'
    '• 选择数量 → 核对总金额 → 使用钱包、银行 QR、Crypto（NOWPayments）或 Binance Pay（如已开放）付款。\n'
    '• 使用 QR 时：请在超时前转账<b>准确金额</b>并填写<b>准确备注</b>。\n'
    '• 请勿修改转账备注，也不要重复使用旧订单的 QR。\n'
    '• 若转错金额，请保留凭证并联系客服核对，切勿再次转账。\n\n'
    '<b>3. 接收商品</b>\n'
    '• 自动订单：系统确认付款后立即在 Telegram 发货。\n'
    '• 人工订单：按提示提交邮箱或所需信息，等待管理员处理。\n'
    '• 可在<b>已购</b> → 选择订单 → <b>重新获取订单信息</b>中再次查看。\n'
    '• 也可使用<b>再次购买该商品</b>，系统始终按当前价格与库存计算。\n\n'
    '<b>4. 报错与保修</b>\n'
    '• 进入<b>已购</b> → 选择订单 → <b>报告订单问题</b>。\n'
    '• 请提供订单号、问题截图或录屏，以及已尝试的操作。\n'
    '• 在我们核查之前，请勿修改密码、找回邮箱，也不要共享账号。\n\n'
    '<b>5. 账号安全</b>\n'
    '• LÂM SHOP 绝不会索要银行密码、OTP 或钱包验证码。\n'
    '• 请勿在公开场合分享 API 密钥、订单号或商品内容。\n\n'
    '<b>需要帮助？</b>请在主菜单选择<b>客服与联系</b>，并附上订单号与相关凭证。'
)

CHINHSACH_TEXT_VI = (
    '<tg-emoji emoji-id="5321466670177330155">📜</tg-emoji> <b>CHÍNH SÁCH LÂM SHOP</b>\n'
    '<i>Cập nhật: 06/08/2026</i>\n\n'
    '<b>1. Phạm vi áp dụng</b>\n'
    'Khi tạo đơn, người mua xác nhận đã đọc mô tả sản phẩm, giá, số lượng, phương thức giao và chính sách liên quan hiển thị tại thời điểm đặt hàng.\n\n'
    '<b>2. Giá và thanh toán</b>\n'
    '• Giá có thể thay đổi theo nguồn cung; đơn được tính theo mức giá hiển thị tại bước xác nhận cuối.\n'
    '• Chỉ thanh toán bằng phương thức do bot cung cấp và dùng đúng mã/nội dung của đơn.\n'
    '• Giao dịch sai số tiền, sai nội dung hoặc sau thời hạn có thể cần đối soát thủ công.\n'
    '• QR chỉ dùng cho đơn hàng hợp pháp. Nghiêm cấm gian lận, rửa tiền, chiếm đoạt tài sản và mọi hành vi trái pháp luật.\n\n'
    '<b>3. Giao hàng</b>\n'
    '• Thời gian giao phụ thuộc loại sản phẩm: tự động hoặc manual.\n'
    '• Người mua phải kiểm tra sản phẩm ngay sau khi nhận và bảo quản thông tin an toàn.\n'
    '• Không công khai hoặc bán lại nội dung nếu sản phẩm/nhà cung cấp không cho phép.\n\n'
    '<b>4. Bảo hành</b>\n'
    '• Chỉ áp dụng trong thời hạn và phạm vi ghi tại sản phẩm hoặc đơn hàng.\n'
    '• Cần cung cấp mã đơn và bằng chứng lỗi để kiểm tra.\n'
    '• Không bảo hành lỗi do đổi mật khẩu/email khôi phục, chia sẻ nhiều người, sử dụng sai hướng dẫn, vi phạm điều khoản nền tảng hoặc tự ý can thiệp sản phẩm.\n'
    '\n'
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
    '• Lâm Shop có thể từ chối xử lý và yêu cầu xác minh khi phát hiện dấu hiệu bất thường.\n\n'
    '<b>8. Khiếu nại và hỗ trợ</b>\n'
    'Gửi yêu cầu qua <b>Hỗ Trợ &amp; Liên Hệ</b>, kèm mã đơn, thời gian, nội dung và bằng chứng. Hai bên ưu tiên kiểm tra dữ liệu hệ thống và trao đổi để giải quyết minh bạch.\n\n'
    '<i>Chính sách này là thông tin giao dịch của Lâm Shop và không thay thế quy định pháp luật hiện hành.</i>'
)

CHINHSACH_TEXT_EN = (
    '<tg-emoji emoji-id="5321466670177330155">📜</tg-emoji> <b>LÂM SHOP POLICY</b>\n'
    '<i>Updated: 06/08/2026</i>\n\n'
    '<b>1. Scope</b>\n'
    'By placing an order you confirm that you have read the product description, price, quantity, delivery method and the related policies shown at the time of ordering.\n\n'
    '<b>2. Price and payment</b>\n'
    '• Prices follow supply and may change; an order is charged at the price shown on the final confirmation step.\n'
    '• Pay only through the methods the bot offers, and use the reference belonging to your order.\n'
    '• A transfer with the wrong amount, the wrong reference or after the deadline may need manual reconciliation.\n'
    '• QR payments are for lawful orders only. Fraud, money laundering, misappropriation and any unlawful use are prohibited.\n\n'
    '<b>3. Delivery</b>\n'
    '• Delivery time depends on the product type: automatic or manual.\n'
    '• Check the product right after you receive it and keep the details safe.\n'
    '• Do not publish or resell the contents where the product or the supplier does not allow it.\n\n'
    '<b>4. Warranty</b>\n'
    '• Applies only within the period and scope stated on the product or the order.\n'
    '• The order code and evidence of the fault are required for us to check.\n'
    '• Faults caused by changing the password or recovery email, sharing the account, using it against the guide, breaching the platform terms or tampering with the product are not covered.\n'
    '\n'
    '<b>5. Cancellation and refunds</b>\n'
    '• An unpaid order can be cancelled before it expires. Wallet funds on hold are returned according to the system state.\n'
    '• Refunds are considered when the system charged you without creating an order, delivered a duplicate, or the supplier confirmed a cancellation or partial refund.\n'
    '• A digital product delivered correctly and already used is normally not refundable, unless it falls under the warranty or a verified fault.\n'
    '• A faulty order that was partly used is refunded for the whole unused days remaining; a day that has started counts as used.\n'
    '• Refunds below 200,000 VND go to your bot wallet. From 200,000 VND you may request a bank transfer once you provide correct details and the admin confirms it.\n'
    '• A bank transfer request holds the refund amount out of your bot wallet; if it is declined, the money returns to the wallet.\n'
    '• Processing time depends on reconciliation with the bank, the wallet and the supplier.\n\n'
    '<b>6. Data and privacy</b>\n'
    '• The bot uses only the information needed to create orders, deliver, support you, prevent fraud and reconcile payments.\n'
    '• Never send banking passwords, OTPs, wallet keys or any data that is not required.\n'
    '• Information may be shared with the relevant processors or with the authorities where the law requires it.\n\n'
    '<b>7. Prohibited use</b>\n'
    '• Using products for fraud, spam, unauthorised access, malware distribution, data theft or any unlawful content.\n'
    '• Exploiting system faults, faking transactions, claiming fraudulent refunds or deliberately creating duplicate orders.\n'
    '• Lâm Shop may decline to process an order and ask for verification when something looks irregular.\n\n'
    '<b>8. Complaints and support</b>\n'
    'Send your request through <b>Support &amp; Contact</b> with the order code, the time, what happened and your evidence. We check the system records first and work with you towards a transparent outcome.\n\n'
    '<i>This policy describes how Lâm Shop trades and does not replace applicable law.</i>'
)

CHINHSACH_TEXT_ZH = (
    '<tg-emoji emoji-id="5321466670177330155">📜</tg-emoji> <b>LÂM SHOP 服务条款</b>\n'
    '<i>更新时间：2026/08/06</i>\n\n'
    '<b>1. 适用范围</b>\n'
    '下单即表示买家已阅读下单时显示的商品说明、价格、数量、发货方式及相关条款。\n\n'
    '<b>2. 价格与付款</b>\n'
    '• 价格随供货情况变动；订单按最终确认步骤显示的价格计算。\n'
    '• 请仅使用机器人提供的付款方式，并填写本订单对应的备注。\n'
    '• 金额错误、备注错误或超时的转账可能需要人工核对。\n'
    '• QR 付款仅限合法订单。严禁欺诈、洗钱、侵占财产及任何违法行为。\n\n'
    '<b>3. 发货</b>\n'
    '• 发货时间取决于商品类型：自动或人工。\n'
    '• 买家须在收货后立即检查商品，并妥善保管相关信息。\n'
    '• 若商品或供应商不允许，请勿公开或转售其内容。\n\n'
    '<b>4. 保修</b>\n'
    '• 仅在商品或订单标明的期限与范围内适用。\n'
    '• 需提供订单号及故障凭证以便核查。\n'
    '• 因修改密码/找回邮箱、多人共享、未按指南使用、违反平台条款或自行改动商品造成的问题不在保修范围内。\n'
    '\n'
    '<b>5. 取消与退款</b>\n'
    '• 未付款订单可在超时前取消，钱包中冻结的金额按系统状态退回。\n'
    '• 出现系统已扣款但未生成订单、重复发货，或供应商确认取消/部分退款时，可申请退款。\n'
    '• 已正确发货且已使用的数字商品通常不予退款，除非属于保修范围或已核实存在故障。\n'
    '• 部分使用的问题订单按剩余整天数退款；已开始的当天计为已使用。\n'
    '• 低于 200,000 VND 的退款退入机器人钱包；达到 200,000 VND 及以上可在提供正确信息并经管理员确认后申请银行转账。\n'
    '• 申请银行转账会先从机器人钱包冻结相应金额；若被拒绝，款项将退回钱包。\n'
    '• 处理时间取决于与银行、钱包及供应商的对账。\n\n'
    '<b>6. 数据与隐私</b>\n'
    '• 机器人仅使用创建订单、发货、客服、反欺诈与对账所必需的信息。\n'
    '• 请勿发送银行密码、OTP、钱包密钥或其他非必要数据。\n'
    '• 在法律要求时，信息可能提供给相关处理方或有权机关。\n\n'
    '<b>7. 禁止行为</b>\n'
    '• 将商品用于诈骗、垃圾信息、非法入侵、传播恶意软件、窃取数据或任何违法内容。\n'
    '• 利用系统漏洞、伪造交易、恶意申请退款或故意重复下单。\n'
    '• 发现异常迹象时，LÂM SHOP 可拒绝处理并要求进行验证。\n\n'
    '<b>8. 投诉与支持</b>\n'
    '请通过<b>客服与联系</b>提交请求，并附订单号、时间、事情经过与凭证。双方优先核对系统数据，透明沟通解决。\n\n'
    '<i>本条款为 LÂM SHOP 的交易说明，不替代现行法律法规。</i>'
)


def get_guide_text(user_id=None) -> str:
    return pick_locale({"vi": HUONGDAN_TEXT_VI, "en": HUONGDAN_TEXT_EN, "zh": HUONGDAN_TEXT_ZH}, get_user_lang(user_id))


def get_policy_text(user_id=None) -> str:
    return pick_locale({"vi": CHINHSACH_TEXT_VI, "en": CHINHSACH_TEXT_EN, "zh": CHINHSACH_TEXT_ZH}, get_user_lang(user_id))


_BUTTON_ACTION_FIELDS = (
    'callback_data', 'url', 'copy_text', 'web_app', 'login_url', 'pay',
    'callback_game', 'switch_inline_query', 'switch_inline_query_current_chat',
    'switch_inline_query_chosen_chat',
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

    # Mot action rong (vi du url=SUPPORT_GROUP_LINK khi bien .env chua dien) van
    # duoc PTB gui len duoi dang {"url": ""}. Telegram doc do la nut chi co chu
    # va tu choi NGUYEN CA ban phim: "text buttons are unallowed in the inline
    # keyboard". Mot bien moi truong bo trong khong duoc phep lam sap ca menu,
    # nen bo action rong va rot ve nut vo hai.
    dropped = [name for name in _BUTTON_ACTION_FIELDS if name in kwargs and _is_blank_action(kwargs[name])]
    for name in dropped:
        kwargs.pop(name)
    if not any(name in kwargs for name in _BUTTON_ACTION_FIELDS):
        if dropped:
            logger.warning(
                "Nut '%s' bi bo action rong (%s) -> chuyen thanh nut tro. Kiem tra cau hinh.",
                text, ", ".join(dropped),
            )
        kwargs['callback_data'] = 'ignore'
    return InlineKeyboardButton(text, **kwargs)


def _is_blank_action(value) -> bool:
    """True khi gia tri action rong theo nghia Telegram se bo qua no."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    # WebAppInfo/LoginUrl rong url cung bi Telegram tu choi y het.
    url = getattr(value, 'url', None)
    if isinstance(url, str):
        return not url.strip()
    return False


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
    ]

    language_button = _btn(t("btn_language", user_id=user_id), icon_id="5816436147525522455", callback_data='language_menu', style="primary")
    if str(SUPPORT_GROUP_LINK or "").strip():
        keyboard.append([
            _btn(t("btn_community", user_id=user_id), icon_id="5443038326535759644", url=SUPPORT_GROUP_LINK, style="primary"),
            language_button,
        ])
    else:
        # Chua dat SUPPORT_GROUP_LINK: bo han nut thay vi hien mot nut bam khong
        # ra gi.
        keyboard.append([language_button])

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
        # Telegram chi mo web app qua HTTPS. Khi PUBLIC_API_URL chua dat,
        # get_public_api_base_url() tra ve placeholder http://YOUR_VPS_IP:...,
        # va Telegram tu choi ca ban phim chu khong rieng nut nay.
        if admin_web_url.startswith("https://"):
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


def create_guide_policy_menu(active: str = "guide", user_id=None):
    guide_text = lt(user_id, "Hướng dẫn", "Guide", "使用指南")
    policy_text = lt(user_id, "Chính sách", "Policy", "服务条款")
    return InlineKeyboardMarkup([
        [
            _btn(
                f"• {guide_text}" if active == "guide" else guide_text,
                icon_id="5321466670177330155",
                callback_data="huongdan",
                style="primary" if active == "guide" else None,
            ),
            _btn(
                f"• {policy_text}" if active == "policy" else policy_text,
                icon_id="6037266106832041274",
                callback_data="chinhsach",
                style="primary" if active == "policy" else None,
            ),
        ],
        [_btn(t("btn_back_main", user_id=user_id), icon_id="6206032691075223572", callback_data="back_to_main")],
    ])


def create_back_button_menu(text=None, callback="back_to_main", user_id=None):
    label = text or f"⬅️ {t('btn_back_main', user_id=user_id)}"
    return InlineKeyboardMarkup([[_btn(label, icon_id="6206032691075223572", callback_data=callback)]])


def create_success_menu(user_id=None):
    return InlineKeyboardMarkup([
        [
            _btn(
                lt(user_id, "Cần hỗ trợ / Báo lỗi đơn hàng", "Need help / report an issue", "需要帮助 / 报告订单问题"),
                icon_id="5273914604752216432",
                callback_data='report_error',
            )
        ],
        [_btn(t("btn_back_main", user_id=user_id), icon_id="6206032691075223572", callback_data='back_to_main')],
    ])

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
        secret_code = ''.join(secrets.choice(digits) for _ in range(length))
        if not any(
            isinstance(order_data, dict) and str(order_data.get("secret_transfer_code") or "").strip().lower() == secret_code
            for order_data in pending_orders.values()
        ):
            return secret_code
    return ''.join(secrets.choice(digits) for _ in range(length))

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

def create_vietqr_png(amount, add_info):
    """Ảnh QR chuyển khoản (PNG bytes) sinh tại chỗ theo chuẩn NAPAS VietQR,
    không gọi img.vietqr.io: không phụ thuộc bên thứ ba lúc khách thanh toán,
    mã đơn và số tiền không đi qua server lạ.

    Nội dung chuyển khoản chứa mã đơn, GPM Pay chỉ việc bắn webhook kèm nội
    dung đó. Trả None khi thiếu cấu hình ngân hàng (BANK_ID/BANK_BIN/số TK).
    """
    from app.utils.vietqr import make_vietqr_png

    try:
        return make_vietqr_png(BANK_ID, BANK_ACCOUNT_NUMBER, int(amount), str(add_info or ""), bank_bin=BANK_BIN)
    except Exception as e:
        logger.error(f"Error creating VietQR image: {e}")
        return None


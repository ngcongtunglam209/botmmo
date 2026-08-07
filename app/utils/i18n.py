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
            '<tg-emoji emoji-id="5413614600807528475">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5413770125868284686">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5411498324391902647">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5411600256850738882">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5420512812206143917">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5420291728764581871">🌷</tg-emoji>'
            '<tg-emoji emoji-id="5411600256850738882">🔤</tg-emoji>'
            '<tg-emoji emoji-id="5411096972582992980">🌹</tg-emoji>'
            '<tg-emoji emoji-id="5411209822848693977">🔤</tg-emoji>\n'
            '<blockquote><tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> <b>Uy tín - Nhanh gọn - Chuyên nghiệp</b>\n'
            '<tg-emoji emoji-id="5303290914041505430">⚡️</tg-emoji> Hệ thống giao hàng tự động 24/7.</blockquote>\n\n'
            "{success} <i>Lựa chọn dịch vụ bên dưới để bắt đầu:</i>"
        ),
        "hello": "Xin chào {name}!",
        "rank_balance": "Hạng: {rank} | Số dư: {balance:,}đ",
        "rank_label": "Đồng",
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
        "rank_balance": "Rank: {rank} | Balance: {balance:,}đ",
        "rank_label": "Bronze",
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
        "rank_balance": "等级: {rank} | 余额: {balance:,}đ",
        "rank_label": "青铜",
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
    },
}


def normalize_lang(lang) -> str:
    key = str(lang or "").strip().lower().replace(" ", "")
    return _LANG_ALIASES.get(key, DEFAULT_LANG)


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


def lt(user_id, vi: str, en: str, zh: str, **kwargs) -> str:
    """Select and format one inline user-facing translation."""
    text = {"vi": vi, "en": en, "zh": zh}[get_user_lang(user_id)]
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

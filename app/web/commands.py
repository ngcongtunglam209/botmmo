"""Danh mục lệnh admin của bot Telegram.

Dữ liệu tĩnh dùng cho trang /admin/commands và endpoint /api/admin/commands.
Cập nhật ở đây khi thêm/bớt lệnh trong handlers.
"""

from __future__ import annotations

from typing import Any

#: (tên, cú pháp, mô tả, mức rủi ro)
COMMAND_GROUPS: list[dict[str, Any]] = [
    {
        "group": "Tổng quan hệ thống",
        "commands": [
            ("admin", "/admin", "Mở bảng điều khiển admin trên Telegram.", "readonly"),
            ("helpadmin", "/helpadmin", "Alias của /admin.", "readonly"),
            ("uptime", "/uptime", "Xem uptime, thông tin hệ thống.", "readonly"),
            ("status", "/status", "Alias của /uptime.", "readonly"),
            ("backup", "/backup", "Tạo và gửi backup dữ liệu.", "danger"),
            ("nhapdata", "/nhapdata", "Restore dữ liệu từ file backup zip.", "danger"),
            ("testing", "/testing", "Lệnh test nội bộ.", "danger"),
        ],
    },
    {
        "group": "Sản phẩm và tồn kho",
        "commands": [
            ("products", "/products", "Danh sách sản phẩm store.", "readonly"),
            ("newproduct", "/newproduct", "Conversation tạo sản phẩm mới.", "conversation"),
            ("editproduct", "/editproduct", "Conversation sửa sản phẩm.", "conversation"),
            ("delproduct", "/delproduct <product_id>", "Xóa sản phẩm.", "danger"),
            ("addstock", "/addstock", "Conversation thêm stock local.", "conversation"),
            ("viewstock", "/viewstock", "Xem stock local.", "readonly"),
            ("delstock", "/delstock", "Conversation xóa stock local.", "conversation"),
            ("setlimit", "/setlimit <product_id> <so_luong>", "Đặt giới hạn pending/manual.", "write"),
            ("setstockchannel", "/setstockchannel <chat_id|off>", "Đặt kênh nhận thông báo nhập kho (hoặc forward tin từ kênh).", "write"),
            ("stockchannel", "/stockchannel", "Xem kênh nhận thông báo nhập kho.", "readonly"),
        ],
    },
    {
        "group": "Đơn hàng và thanh toán",
        "commands": [
            ("duyet", "/duyet <ma_don>", "Duyệt đơn thủ công/manual.", "write"),
            ("pending", "/pending", "Xem đơn manual đang chờ.", "readonly"),
            ("clearpending", "/clearpending", "Xóa pending manual.", "danger"),
            ("refund", "/refund <ma_don>", "Hoàn tiền đơn hàng user/API partner.", "danger"),
            ("find", "/find <ma_don|user_id>", "Tìm đơn hàng.", "readonly"),
            ("doanhthu", "/doanhthu", "Thống kê doanh thu.", "readonly"),
            ("setemail", "/setemail <ma_don> <email>", "Gắn email nhận hàng cho đơn.", "write"),
            ("transactions", "/transactions", "Xem lịch sử giao dịch ví.", "readonly"),
            ("lichsugiaodich", "/lichsugiaodich", "Alias của /transactions.", "readonly"),
        ],
    },
    {
        "group": "User và ví",
        "commands": [
            ("users", "/users", "Danh sách user.", "readonly"),
            ("info", "/info <user_id>", "Xem thông tin user.", "readonly"),
            ("ban", "/ban <user_id>", "Cấm user.", "danger"),
            ("unban", "/unban <user_id>", "Gỡ cấm user.", "write"),
            ("bc", "/bc <noi_dung>", "Broadcast tin nhắn.", "danger"),
            ("addmoney", "/addmoney <user_id> <so_tien>", "Cộng tiền vào ví user/API.", "danger"),
            ("submoney", "/submoney <user_id> <so_tien>", "Trừ tiền ví user/API.", "danger"),
            ("pending_withdrawals", "/pending_withdrawals", "Xem yêu cầu rút tiền.", "readonly"),
        ],
    },
    {
        "group": "Coupon, khuyến mãi, game",
        "commands": [
            ("sale", "/sale <noi_dung>", "Gửi thông báo sale.", "danger"),
            ("addcoupon", "/addcoupon ...", "Thêm coupon.", "write"),
            ("delcoupon", "/delcoupon <code>", "Xóa coupon.", "write"),
            ("listcoupons", "/listcoupons", "Danh sách coupon.", "readonly"),
            ("rewardtop", "/rewardtop", "Thưởng top buyer/referral.", "danger"),
            ("promobudget", "/promobudget", "Xem ngân sách khuyến mãi.", "readonly"),
            ("ngansachkm", "/ngansachkm", "Alias của /promobudget.", "readonly"),
            ("flashsale", "/flashsale ...", "Quản lý flash sale.", "write"),
            ("combo", "/combo ...", "Quản lý combo deal.", "write"),
            ("create_ga", "/create_ga", "Conversation tạo giveaway.", "conversation"),
            ("list_ga", "/list_ga", "Danh sách giveaway.", "readonly"),
            ("listga", "/listga", "Alias của /list_ga.", "readonly"),
            ("endga", "/endga <ga_id>", "Kết thúc giveaway.", "write"),
            ("end_ga", "/end_ga <ga_id>", "Alias của /endga.", "write"),
        ],
    },
    {
        "group": "API partner",
        "commands": [
            ("api", "/api", "Danh sách API key partner.", "readonly"),
            ("addapi", "/addapi <ten> <so_du>", "Tạo API key partner.", "danger"),
            ("delapi", "/delapi <key>", "Xóa/vô hiệu API key.", "danger"),
            ("napi", "/napi ...", "Nạp ví API partner.", "write"),
            ("helpapi", "/helpapi", "Hướng dẫn API.", "readonly"),
            ("dkyapi", "/dkyapi", "User đăng ký API partner.", "user"),
            ("dkapi", "/dkapi", "Alias đăng ký API.", "user"),
            ("dangkyapi", "/dangkyapi", "Alias đăng ký API.", "user"),
            ("regapi", "/regapi", "Alias đăng ký API.", "user"),
            ("napapi", "/napapi", "User nạp ví API.", "user"),
            ("topupapi", "/topupapi", "Alias nạp ví API.", "user"),
        ],
    },
    {
        "group": "Hỗ trợ, thông báo, vận hành",
        "commands": [
            ("notify", "/notify <product_id> <out|back>", "Thông báo hết/có hàng.", "write"),
            ("resetnotify", "/resetnotify", "Reset cờ thông báo stock.", "write"),
            ("analytics", "/analytics", "Thống kê nâng cao.", "readonly"),
            ("chats", "/chats", "Danh sách live chat.", "readonly"),
            ("chat", "/chat <user_id>", "Mở chat admin với user.", "conversation"),
            ("closechat", "/closechat", "Đóng chat admin.", "write"),
            ("baotri", "/baotri", "Bật/tắt maintenance mode.", "danger"),
            ("aimode", "/aimode", "Bật/tắt AI auto reply.", "write"),
        ],
    },
]

RISK_TONES = {
    "readonly": "info",
    "write": "warn",
    "danger": "danger",
    "conversation": "neutral",
    "user": "ok",
}


def flat_commands() -> list[dict[str, str]]:
    """Danh sách phẳng dùng cho API và tìm kiếm."""
    return [
        {
            "group": group["group"],
            "name": name,
            "syntax": syntax,
            "description": description,
            "risk": risk,
        }
        for group in COMMAND_GROUPS
        for name, syntax, description, risk in group["commands"]
    ]


def grouped_commands() -> list[dict[str, Any]]:
    """Nhóm lệnh kèm tone màu để template khỏi tính lại."""
    return [
        {
            "group": group["group"],
            "commands": [
                {
                    "name": name,
                    "syntax": syntax,
                    "description": description,
                    "risk": risk,
                    "tone": RISK_TONES.get(risk, "neutral"),
                }
                for name, syntax, description, risk in group["commands"]
            ],
        }
        for group in COMMAND_GROUPS
    ]

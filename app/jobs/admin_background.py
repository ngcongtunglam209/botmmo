# ==============================================================================
#  ADMIN BACKGROUND JOBS
# ==============================================================================
async def admin_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, func) -> None:
    """Wrapper để bảo vệ các lệnh Admin"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        # Không phản hồi hoặc báo lỗi
        return

    try:
        await func(update, context)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        command_name = getattr(func, "__name__", "?")
        logger.error(f"Lỗi khi thực thi lệnh Admin {command_name}: {e}", exc_info=True)
        # Truoc day cau nay luon noi "khi backup" du lenh nao hong cung vay.
        message = getattr(update, "message", None)
        if message is not None:
            await message.reply_text("❌ Lệnh gặp lỗi, vui lòng kiểm tra logs.")



# ==============================================================================
#  HELPER: Batch Error Reporting (Job Queue)
# ==============================================================================
# ==============================================================================
#  HELPER: Unresolved Error Reminder (Job Queue)
# ==============================================================================
async def send_batched_error_reports(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Nhắc nhở Admin về các đơn báo lỗi CHƯA XỬ LÝ (Unresolved)
    """
    # Khong khai bao `global`: ca hai cho ben duoi deu sua TAI CHO. Gan lai bien
    # global trong section module chi doi ban ghi cua module nay, cac module khac
    # van giu alias toi list cu.

    # Filter unresolved reports
    unresolved = [r for r in pending_error_reports if not r.get('resolved', False)]

    if not unresolved:
        # Cleanup resolved ones to save memory
        pending_error_reports.clear()
        return

    # Gửi thông báo nhắc nhở
    count = len(unresolved)
    summary_msg = f"{E_TIP} <b>SẾP ƠI! CÒN {count} ĐƠN LỖI CHƯA XỬ LÝ:</b>\n\n"

    for i, report in enumerate(unresolved, 1):
        waiting_time_min = int((time.time() - report['timestamp']) / 60)
        time_str = f"{waiting_time_min}p trước" if waiting_time_min < 60 else f"{int(waiting_time_min/60)}h trước"

        summary_msg += (
            f"{i}. <code>{report['order_code']}</code> - {html.escape(report['product_name'])}\n"
            f"   {E_USER} {html.escape(report['username'] or 'N/A')} (Báo lần {report.get('report_count', 1)})\n"
            f"   {E_CALENDAR} Mua: {report.get('purchase_date', 'N/A')} - <tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> {time_str}\n"
        )

    summary_msg += "\n<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> Vui lòng check tin nhắn trên để xử lý!"

    try:
        await safe_send_admin(context.bot, summary_msg)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        logger.error(f"Cannot send reminder summary: {e}")

    # Sua TAI CHO chu khong gan lai: cac section module dung chung namespace va
    # giu alias toi chinh list nay. Gan lai se tach vinh vien ban ghi cua module
    # nay khoi list ma moi cho khac dang append vao.
    pending_error_reports[:] = unresolved

async def auto_remind_email_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Cron Job: Tự động nhắc user nhập email nếu quên (Mỗi 5 phút)
    """
    current_time = time.time()

    # Iterate copy to avoid runtime error if dict changes
    for order_code, order in list(pending_manual_orders.items()):

        # Chỉ check đơn đang chờ email
        if order.get('status') == 'awaiting_email' and not order.get('email'):

            user_id = order.get('user_id')
            start_time = order.get('timestamp', 0)
            last_reminded = order.get('last_reminded', 0)

            # Điều kiện nhắc:
            # 1. Đã qua 2 phút kể từ lúc mua (để họ kịp nhập)
            # 2. Đã qua 15 phút kể từ lần nhắc cuối (tránh spam)
            # 3. Tổng thời gian chờ < 24h (sau 24h thôi nhắc)

            minutes_waiting = (current_time - start_time) / 60
            minutes_since_last = (current_time - last_reminded) / 60

            if minutes_waiting > 2 and minutes_since_last > 15 and minutes_waiting < 1440:
                try:
                    product_name = order.get('product_name', 'Sản phẩm')

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> <b>THÔNG BÁO TỪ BOT</b>\n\n"
                            f"Bạn ơi, mình thấy bạn vừa mua <b>{product_name}</b> nhưng chưa nhập Email nhận hàng nè.\n\n"
                            f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> <b>Mã đơn:</b> <code>{order_code}</code>\n\n"
                            f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vui lòng <b>nhập địa chỉ Email</b> của bạn vào đây ngay nhé!\n\n"
                            f"<b>Cách gửi email:</b>\n"
                            f"• Reply tin nhắn này với email của bạn\n"
                            f"• Hoặc dùng lệnh: <code>/guimail email@abc.com</code>"
                        ),
                        parse_mode=ParseMode.HTML
                    )

                    # Update status
                    pending_manual_orders[order_code]['last_reminded'] = current_time
                    await save_data()
                    logger.info(f"<tg-emoji emoji-id=\"5447644880824181073\">🔔</tg-emoji> Đã nhắc user {user_id} nhập email cho đơn {order_code}")

                except (TelegramError, ValueError, KeyError, AttributeError) as e:
                    logger.warning(f"Không thể nhắc user {user_id}: {e}")
                    # Có thể đánh dấu failed để không nhắc lại ngay
                    pending_manual_orders[order_code]['last_reminded'] = current_time # Skip this turn

# ==============================================================================
#  VIP/RANK SYSTEM — Hệ thống cấp bậc theo số đơn hoàn thành
# ==============================================================================

VIP_RANKS = [
    {"name": "⭐️ Đồng",         "min_orders": 0,  "min_spent": 0,        "discount": 0},
    {"name": "⭐️ Bạc",          "min_orders": 0,  "min_spent": 500000,   "discount": 0},
    {"name": "⭐️ Vàng",         "min_orders": 0,  "min_spent": 1000000,  "discount": 0},
    {"name": "<tg-emoji emoji-id=\"5240228673738527951\">💎</tg-emoji> Kim Cương",    "min_orders": 0,  "min_spent": 5000000,  "discount": 0},
    {"name": "⭐️ Cao Thủ",      "min_orders": 0,  "min_spent": 10000000, "discount": 0},
]


def _get_previous_month_maintenance_window(reference_dt=None):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = reference_dt.astimezone(tz) if reference_dt else datetime.now(tz)
    current_month_start = datetime(now.year, now.month, 1, tzinfo=tz)
    last_day_previous_month = current_month_start.date() - timedelta(days=1)
    previous_month_start = datetime(
        last_day_previous_month.year,
        last_day_previous_month.month,
        1,
        tzinfo=tz,
    )
    return previous_month_start, current_month_start, previous_month_start.strftime("%m/%Y")


def _calculate_orders_spent_in_period(orders, start_ts: float, end_ts: float) -> int:
    total_spent = 0
    for order in orders:
        if not is_completed_order(order):
            continue
        try:
            order_ts = float(order.get("timestamp", 0) or 0)
            if start_ts <= order_ts < end_ts:
                total_spent += int(order.get("amount", 0) or 0)
        except (ValueError, TypeError):
            continue
    return total_spent


def get_user_vip_rank(user_id) -> dict:
    """Tính rank VIP dựa trên tổng đơn hoàn thành và tổng chi tiêu."""
    merged_orders = {}
    for order in user_order_index.get(str(user_id), []):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    for order in _api_get_orders_for_user(user_id):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    user_orders = list(merged_orders.values())
    completed = [o for o in user_orders if is_completed_order(o)]
    total_orders = len(completed)
    total_spent = sum(o.get('amount', 0) for o in completed)

    base_rank_index = 0
    next_lifetime_rank = None
    for i, rank in enumerate(VIP_RANKS):
        if total_orders >= rank["min_orders"] and total_spent >= rank["min_spent"]:
            base_rank_index = i
            next_lifetime_rank = VIP_RANKS[i + 1] if i + 1 < len(VIP_RANKS) else None
        else:
            next_lifetime_rank = rank
            break

    previous_month_start, current_month_start, period_label = _get_previous_month_maintenance_window()
    monthly_spend = _calculate_orders_spent_in_period(
        user_orders,
        previous_month_start.timestamp(),
        current_month_start.timestamp(),
    )
    maintenance_status = {
        "period_label": period_label,
        "monthly_spend": monthly_spend,
        "minimum_required": VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "met_requirement": monthly_spend >= VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "remaining_to_maintain": max(0, VIP_MONTHLY_MAINTENANCE_MIN_SPEND - monthly_spend),
    }
    demoted_by_maintenance = base_rank_index > 0 and not maintenance_status["met_requirement"]
    effective_rank_index = max(0, base_rank_index - 1) if demoted_by_maintenance else base_rank_index
    current_rank = VIP_RANKS[effective_rank_index]
    base_rank = VIP_RANKS[base_rank_index]

    if demoted_by_maintenance:
        next_rank = base_rank
    else:
        next_rank = next_lifetime_rank

    return {
        "rank": current_rank,
        "base_rank": base_rank,
        "next_rank": next_rank,
        "total_orders": total_orders,
        "total_spent": total_spent,
        "discount_percent": 0,
        "demoted_by_maintenance": demoted_by_maintenance,
        "maintenance_status": maintenance_status,
    }

def apply_vip_discount(user_id, original_price: int) -> tuple:
    """Trả về (giá_sau_giảm, phần_trăm_giảm, tên_rank)."""
    vip = get_user_vip_rank(user_id)
    return original_price, 0, vip["rank"]["name"]


# ==============================================================================
#  /UPTIME — Bot uptime + system stats
# ==============================================================================

async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiển thị thời gian bot đã chạy và thông tin hệ thống."""
    now = datetime.now()
    delta = now - BOT_START_TIME
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_str = ""
    if days > 0:
        uptime_str += f"{days} ngày "
    uptime_str += f"{hours}h {minutes}m {seconds}s"

    # System info
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Process info
        proc = psutil.Process()
        proc_mem = proc.memory_info().rss / (1024 * 1024)  # MB

        sys_info = (
            f"\n<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> <b>HỆ THỐNG</b>\n"
            f"├ CPU: <b>{cpu_percent}%</b>\n"
            f"├ RAM: <b>{mem.percent}%</b> ({mem.used // (1024**2):,}/{mem.total // (1024**2):,} MB)\n"
            f"├ Disk: <b>{disk.percent}%</b> ({disk.used // (1024**3):,}/{disk.total // (1024**3):,} GB)\n"
            f"└ Bot RAM: <b>{proc_mem:.1f} MB</b>\n"
        )
    except ImportError:
        sys_info = "\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Cài psutil để xem thông tin hệ thống: pip install psutil</i>\n"
    except Exception as e:
        logger.exception(f"Loi doc system info: {e}", exc_info=e)
        sys_info = f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> <i>Lỗi đọc system info: {e}</i>\n"

    # Bot stats
    total_users = len(user_data_db)
    total_orders = len(order_history)
    total_products = len(products)

    msg = (
        f"<tg-emoji emoji-id=\"5303145396254563405\">🤖</tg-emoji> <b>BOT STATUS</b>\n"
        f"{'━' * 28}\n\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">⏱️</tg-emoji> Uptime: <b>{uptime_str}</b>\n"
        f"<tg-emoji emoji-id=\"5213349767672769194\">🕐</tg-emoji> Khởi chạy: {BOT_START_TIME.strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"{sys_info}\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">📈</tg-emoji> <b>THỐNG KÊ</b>\n"
        f"├ Users: <b>{total_users:,}</b>\n"
        f"├ Đơn hàng: <b>{total_orders:,}</b>\n"
        f"├ Sản phẩm: <b>{total_products}</b>\n"
        f"└ Pending: <b>{len(pending_orders)}</b>\n"
    )

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  PAYMENT REMINDER JOB — Nhắc thanh toán đơn pending > 15 phút
# ==============================================================================

_payment_reminded = set()  # Track đã nhắc để không spam

async def payment_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cron job: Nhắc user thanh toán nếu đơn pending > 15 phút."""
    if not pending_orders:
        return

    current_time = time.time()
    REMIND_AFTER_SECONDS = 15 * 60  # 15 phút
    MAX_PENDING_SECONDS = 60 * 60   # 1 giờ — auto hủy

    orders_to_remove = []

    for order_code, order_details in list(pending_orders.items()):
        start_time = order_details.get('timestamp', 0)
        if not start_time:
            continue

        elapsed = current_time - start_time
        user_id = order_details.get('user_id')
        if not user_id:
            continue

        reminder_key = f"{order_code}_{user_id}"

        # Quá 1 giờ → tự hủy
        if elapsed > MAX_PENDING_SECONDS:
            orders_to_remove.append(order_code)
            _payment_reminded.discard(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sản phẩm')
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>ĐƠN HÀNG ĐÃ HẾT HẠN</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> SP: {html.escape(str(product_name))}\n\n"
                    "Đơn hàng đã bị hủy do quá thời gian thanh toán (60 phút).\n"
                    "Vui lòng đặt lại nếu cần.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass  # User có thể đã block bot
            except Exception as e:
                logger.exception(f"Payment reminder send_message cancelled order failed for user {user_id}: {e}", exc_info=e)
            continue

        # Quá 15 phút + chưa nhắc → gửi nhắc nhở
        if elapsed > REMIND_AFTER_SECONDS and reminder_key not in _payment_reminded:
            _payment_reminded.add(reminder_key)
            try:
                product_name = order_details.get('product_name') or order_details.get('product', 'Sản phẩm')
                amount = order_details.get('amount', 0)
                minutes_left = max(1, int((MAX_PENDING_SECONDS - elapsed) / 60))
                await context.bot.send_message(
                    user_id,
                    f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> <b>NHẮC NHỞ THANH TOÁN</b>\n\n"
                    f"<tg-emoji emoji-id=\"5334890573281114250\">🆔</tg-emoji> Mã đơn: <code>{html.escape(str(order_code))}</code>\n"
                    f"<tg-emoji emoji-id=\"6260059243605398502\">📌</tg-emoji> Sản phẩm: {html.escape(str(product_name))}\n"
                    f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Số tiền: <b>{amount:,} VNĐ</b>\n\n"
                    f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn chưa thanh toán đơn hàng này.\n"
                    f"Đơn sẽ tự hủy sau <b>{minutes_left} phút</b> nếu không nhận được thanh toán.\n\n"
                    "<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> Nếu đã chuyển khoản, vui lòng đợi 1-2 phút để hệ thống xác nhận.",
                    parse_mode=ParseMode.HTML
                )
            except TelegramError:
                pass
            except Exception as e:
                logger.exception(f"Payment reminder send_message remind order failed for user {user_id}: {e}", exc_info=e)

    # Xóa các đơn hết hạn.
    # Qua pending_pop() chu khong pop truc tiep: pending_pop tra lai suat ma giam
    # gia ma don dang giu. Pop thang dict lam suat do ket vinh vien.
    # LUU Y: duong nay het han o MAX_PENDING_SECONDS (1h) va KHONG hoan
    # balance_used, khac voi _cleanup_expired_pending_orders (600s, co hoan).
    # Thuc te don chet o 600s truoc nen nhanh nay hau nhu khong chay toi.
    for code in orders_to_remove:
        await pending_pop(code)

    if orders_to_remove:
        create_background_task(save_data())
        logger.info(f"<tg-emoji emoji-id=\"5213349767672769194\">⏰</tg-emoji> Payment reminder: Đã hủy {len(orders_to_remove)} đơn hết hạn.")

# ==============================================================================
#  /RANK — Xem VIP rank cá nhân
# ==============================================================================

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hiển thị VIP rank của user."""
    from app.services.games_withdrawals_db import check_if_banned
    if await check_if_banned(update): return

    user_id = update.effective_user.id
    vip = get_user_vip_rank(user_id)

    rank = vip["rank"]
    base_rank = vip.get("base_rank") or rank
    next_rank = vip["next_rank"]
    maintenance_status = vip.get("maintenance_status") or {}

    msg = (
        f"⭐️ <b>HẠNG THÀNH VIÊN CỦA BẠN</b>\n"
        f"{'━' * 28}\n\n"
        f"⭐️ Rank: <b>{rank['name']}</b>\n"
        f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> Tổng đơn: <b>{vip['total_orders']}</b>\n"
        f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Tổng chi: <b>{vip['total_spent']:,} VNĐ</b>\n"
        f"<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Ưu đãi: <b>Không còn giảm giá theo rank</b>\n"
    )

    if vip.get("demoted_by_maintenance"):
        msg += (
            f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
            f"Tháng {maintenance_status.get('period_label', 'trước')} bạn chỉ chi "
            f"<b>{maintenance_status.get('monthly_spend', 0):,} VNĐ</b>, dưới mức duy trì "
            f"<b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b> nên đang bị tụt 1 bậc.\n"
            f"<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> "
            f"Cần chi tối thiểu <b>{maintenance_status.get('remaining_to_maintain', 0):,} VNĐ</b> "
            f"trong tháng này để lấy lại <b>{base_rank['name']}</b> vào tháng sau.\n"
        )
    if next_rank:
        if vip.get("demoted_by_maintenance"):
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Rank cần lấy lại: {next_rank['name']}</b>\n"
                f"└ Điều kiện: tháng này chi tối thiểu <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b>\n"
            )
        else:
            orders_need = max(0, next_rank["min_orders"] - vip["total_orders"])
            spent_need = max(0, next_rank["min_spent"] - vip["total_spent"])
            msg += (
                f"\n<tg-emoji emoji-id=\"5972022360025336988\">⬆️</tg-emoji> <b>Rank tiếp theo: {next_rank['name']}</b>\n"
                f"├ Cần thêm: <b>{orders_need}</b> đơn hàng\n"
                f"└ Cần chi thêm: <b>{spent_need:,} VNĐ</b>\n"
            )
    else:
        msg += "\n<tg-emoji emoji-id=\"5449800250032143374\">🎉</tg-emoji> <b>Bạn đã đạt hạng cao nhất!</b> <tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji>\n"

    # Bảng xếp hạng
    msg += (
        f"\n{'━' * 28}\n"
        "<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>CÁC CẤP BẬC:</b>\n"
    )
    for r in VIP_RANKS:
        marker = " ← Bạn" if r["name"] == rank["name"] else ""
        msg += f"  {r['name']} — {r['min_orders']}+ đơn{marker}\n"
    msg += f"\n<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Quy tắc duy trì: nếu tháng trước chi dưới <b>{VIP_MONTHLY_MAINTENANCE_MIN_SPEND:,} VNĐ</b> thì sẽ tụt 1 bậc trong tháng này."

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# ==============================================================================
#  HÀM MAIN (KHỞI CHẠY BOT)
# ==============================================================================


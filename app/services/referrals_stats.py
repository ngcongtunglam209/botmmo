# ==============================================================================
#  ADVANCED FEATURES HELPER FUNCTIONS
# ==============================================================================

def generate_progress_bar(current, total, length=15):
    """Tạo thanh progress bar: [████░░░░░░] 40%"""
    if total == 0: return f"[{'░' * length}] 0%"
    percent = min(current / total, 1.0)
    filled_length = int(length * percent)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"[{bar}] {int(percent * 100)}%"

async def process_referral_commission(context, user_id: int, amount: int, order_code: str = None):
    """
    Xử lý hoa hồng referral khi có người mua hàng
    Returns: commission amount nếu có, 0 nếu không
    """
    user_id_str = str(user_id)
    
    # Check if user was referred by someone
    if user_id_str not in referral_data:
        return 0
    
    ref_info = referral_data[user_id_str]
    if 'referrer_id' not in ref_info:
        return 0
    
    referrer_id = ref_info['referrer_id']
    referrer_id_str = str(referrer_id)
    
    if order_code and referrer_id_str in referral_data:
        history = referral_data[referrer_id_str].get('commission_history', [])
        if any(h.get('order_code') == order_code for h in history):
            logger.info(f'[COMMISSION] Skipping duplicate commission for order {order_code}')
            return 0
    
    # Calculate commission
    commission = int(amount * REFERRAL_COMMISSION_PERCENT / 100)
    
    # Add to referrer's balance
    referrer_user = db_get_user(referrer_id)
    if referrer_user:
        new_balance = referrer_user.get('balance', 0) + commission
        db_update_balance(referrer_id, new_balance, reason=f"Commission: {commission:,} VNĐ verified user")
        
        # Track commission in referral_data
        if referrer_id_str not in referral_data:
            referral_data[referrer_id_str] = {
                'referred_users': [],
                'total_commission': 0,
                'commission_history': []
            }
        
        referral_data[referrer_id_str]['total_commission'] += commission
        referral_data[referrer_id_str]['commission_history'].append({
            'from_user_id': user_id,
            'amount': commission,
            'order_code': order_code,
            'timestamp': time.time()
        })
        
        await save_data()
        
        # Notify referrer
        try:
            await context.bot.send_message(
                referrer_id,
                f"{E_TAG} <b>BẠN VỪA NHẬN HOA HỒNG!</b>\n\n"
                f"{E_TAG} <b>Số tiền:</b> +{commission:,} VNĐ\n"
                f"{E_USER} <b>Từ:</b> Người bạn giới thiệu vừa mua hàng\n"
                f"{E_TAG} <b>Số dư mới:</b> {new_balance:,} VNĐ",
                parse_mode=ParseMode.HTML
            )
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.error(f"Cannot notify referrer {referrer_id}: {e}")
        
        return commission
    
    return 0


def _get_user_merged_orders(user_id: int):
    merged_orders = {}
    for order in db_get_user_orders(user_id, limit=None):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    for order in _api_get_orders_for_user(user_id):
        order_code = str(order.get("order_code") or "")
        if order_code:
            merged_orders[order_code] = order
    return list(merged_orders.values())


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


def calculate_user_period_spent(user_id: int, start_ts: float, end_ts: float) -> int:
    total_spent = 0
    for order in _get_user_merged_orders(user_id):
        if not is_completed_order(order):
            continue
        try:
            order_ts = float(order.get("timestamp", 0) or 0)
            if start_ts <= order_ts < end_ts:
                total_spent += int(order.get("amount", 0) or 0)
        except (ValueError, TypeError):
            continue
    return total_spent


def get_rank_maintenance_status(user_id: int, reference_dt=None):
    previous_month_start, current_month_start, period_label = _get_previous_month_maintenance_window(reference_dt)
    monthly_spend = calculate_user_period_spent(
        user_id,
        previous_month_start.timestamp(),
        current_month_start.timestamp(),
    )
    remaining_to_maintain = max(0, VIP_MONTHLY_MAINTENANCE_MIN_SPEND - monthly_spend)
    return {
        "period_label": period_label,
        "monthly_spend": monthly_spend,
        "minimum_required": VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "met_requirement": monthly_spend >= VIP_MONTHLY_MAINTENANCE_MIN_SPEND,
        "remaining_to_maintain": remaining_to_maintain,
    }


def calculate_user_stats(user_id: int):
    """Tính toán thống kê user"""
    orders = _get_user_merged_orders(user_id)
    
    total_spent = 0
    order_count = 0
    for o in orders:
        if is_completed_order(o):
            order_count += 1
            try:
                total_spent += int(o.get('amount', 0))
            except (ValueError, TypeError):
                pass

    # Coupon savings
    coupon_savings = 0
    for o in orders:
        if o.get('coupon_used'):
            code = o['coupon_used']
            if code in coupons:
                try:
                    coupon_savings += int(coupons[code].get('discount', 0))
                except (ValueError, TypeError):
                    pass
    
    # Referral stats
    user_id_str = str(user_id)
    referral_count = len(referral_data.get(user_id_str, {}).get('referred_users', []))
    total_commission = referral_data.get(user_id_str, {}).get('total_commission', 0)
    
    return {
        'total_spent': total_spent,
        'order_count': order_count,
        'coupon_savings': coupon_savings,
        'referral_count': referral_count,
        'commission_earned': total_commission
    }

def _legacy_calculate_badges(user_id: int):
    """Tính toán badges cho user"""
    stats = calculate_user_stats(user_id)
    badges = []
    
    # Order-based badges
    if stats['order_count'] >= 1:
        badges.append('<tg-emoji emoji-id=\"5334890573281114250\">🆕</tg-emoji> Newbie')
    if stats['order_count'] >= 5:
        badges.append('<tg-emoji emoji-id=\"5247134066322447995\">🛒</tg-emoji> Khách quen')
    if stats['order_count'] >= 20 or stats['total_spent'] >= 1000000:
        badges.append('<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> VIP')
    if stats['order_count'] >= 50 or stats['total_spent'] >= 5000000:
        badges.append('<tg-emoji emoji-id=\"6124902618574625426\">👑</tg-emoji> Legend')
    
    # Referral badges
    if stats['referral_count'] >= 5:
        badges.append('<tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Influencer')
    if stats['referral_count'] >= 20:
        badges.append('<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> Super Influencer')
    
    # Deal hunter
    if stats['coupon_savings'] >= 100000:
        badges.append('<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> Deal Hunter')
    
    return badges

def calculate_badges(user_id: int):
    """Tính toán badges cho user với premium emoji cố định."""
    stats = calculate_user_stats(user_id)
    badges = []

    if stats['order_count'] >= 1:
        badges.append('<tg-emoji emoji-id="5334890573281114250">🆔</tg-emoji> Newbie')
    if stats['order_count'] >= 5:
        badges.append('<tg-emoji emoji-id="5247134066322447995">🛍</tg-emoji> Khách quen')
    if stats['order_count'] >= 20 or stats['total_spent'] >= 1000000:
        badges.append('<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> VIP')
    if stats['order_count'] >= 50 or stats['total_spent'] >= 5000000:
        badges.append('<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> Legend')

    if stats['referral_count'] >= 5:
        badges.append('<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> Influencer')
    if stats['referral_count'] >= 20:
        badges.append('<tg-emoji emoji-id="5449800250032143374">🎁</tg-emoji> Super Influencer')

    if stats['coupon_savings'] >= 100000:
        badges.append('<tg-emoji emoji-id="6260059243605398502">🏷️</tg-emoji> Deal Hunter')

    return badges


def _legacy_format_rank_name_premium(rank_name: str) -> str:
    clean_name = re.sub(r'<[^>]+>', '', str(rank_name or '')).strip()
    if 'Cao Thủ' in clean_name:
        return '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> Cao Thủ'
    if 'Kim Cương' in clean_name:
        return '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương'
    if 'Vàng' in clean_name:
        return '⭐️ Vàng'
    if 'Bạc' in clean_name:
        return '⭐️ Bạc'
    return '⭐️ Đồng'


def format_rank_name_premium(rank_name: str) -> str:
    import unicodedata

    clean_name = re.sub(r'<[^>]+>', '', str(rank_name or '')).strip()
    lower_name = clean_name.lower()
    ascii_name = ''.join(
        ch for ch in unicodedata.normalize('NFD', lower_name)
        if not unicodedata.combining(ch)
    )

    if chr(0x1F451) in clean_name or chr(0x1F3C6) in clean_name or "cao thu" in ascii_name:
        return '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> Cao Thủ'
    if chr(0x1F48E) in clean_name or "kim cuong" in ascii_name or "kim" in ascii_name:
        return '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương'
    if chr(0x1F947) in clean_name or "vang" in ascii_name:
        return '⭐️ Vàng'
    if chr(0x1F948) in clean_name or "bac" in ascii_name:
        return '⭐️ Bạc'
    return '⭐️ Đồng'


def format_rank_entry_premium(rank: dict) -> str:
    if not isinstance(rank, dict):
        return '⭐️ Đồng'

    min_spent = int(rank.get('min_spent', rank.get('min_spend', 0)) or 0)
    discount = int(rank.get('discount', 0) or 0)
    raw_name = re.sub(r'<[^>]+>', '', str(rank.get('name', '') or '')).strip().lower()

    if min_spent >= 10000000 or 'cao' in raw_name or chr(0x1F451) in raw_name or chr(0x1F3C6) in raw_name:
        return '<tg-emoji emoji-id="6124902618574625426">👑</tg-emoji> Cao Thủ'
    if min_spent >= 5000000 or discount >= 8 or chr(0x1F48E) in raw_name or 'kim' in raw_name:
        return '<tg-emoji emoji-id="5240228673738527951">💎</tg-emoji> Kim Cương'
    if min_spent >= 1000000 or discount >= 5 or chr(0x1F947) in raw_name:
        return '⭐️ Vàng'
    if min_spent >= 500000 or discount >= 2 or chr(0x1F948) in raw_name:
        return '⭐️ Bạc'
    return '⭐️ Đồng'


def get_user_rank(user_id: int):
    """Get VIP rank info for a user based on total spending"""
    stats = calculate_user_stats(user_id)
    total_spent = stats['total_spent']
    base_rank_index = 0
    next_lifetime_rank = None
    for i, rank in enumerate(VIP_RANKS):
        if total_spent >= rank['min_spent']:
            base_rank_index = i
            next_lifetime_rank = VIP_RANKS[i + 1] if i + 1 < len(VIP_RANKS) else None

    maintenance_status = get_rank_maintenance_status(user_id)
    demoted_by_maintenance = base_rank_index > 0 and not maintenance_status['met_requirement']
    effective_rank_index = max(0, base_rank_index - 1) if demoted_by_maintenance else base_rank_index

    current_rank = VIP_RANKS[effective_rank_index]
    base_rank = VIP_RANKS[base_rank_index]

    if demoted_by_maintenance:
        next_rank = base_rank
        remaining = maintenance_status['remaining_to_maintain']
    else:
        next_rank = next_lifetime_rank
        if next_rank:
            next_rank_min_spent = int(next_rank.get('min_spend', next_rank.get('min_spent', 0)) or 0)
            remaining = max(0, next_rank_min_spent - total_spent)
        else:
            remaining = 0

    return {
        'rank': current_rank,
        'base_rank': base_rank,
        'next_rank': next_rank,
        'total_spent': total_spent,
        'remaining_to_next': remaining,
        'demoted_by_maintenance': demoted_by_maintenance,
        'maintenance_status': maintenance_status,
    }

def get_rank_discount(user_id: int):
    """Get discount percent based on VIP rank"""
    return 0

def get_flash_sale_price(prod_id: str, original_price: int):
    """Check if product has active flash sale, return (discounted_price, sale_info) or (original_price, None)"""
    now = time.time()
    for sale_id, sale in flash_sales.items():
        if sale.get('active', True) and sale['start_time'] <= now <= sale['end_time']:
            if prod_id in sale.get('product_ids', []) or sale.get('all_products', False):
                discount = sale['discount_percent']
                discounted = int(original_price * (100 - discount) / 100)
                remaining_secs = int(sale['end_time'] - now)
                mins = remaining_secs // 60
                secs = remaining_secs % 60
                return discounted, {
                    'original': original_price,
                    'discount_percent': discount,
                    'countdown': f"{mins}:{secs:02d}",
                    'sale_name': sale.get('name', 'Flash Sale'),
                    'sale_id': sale_id
                }
    return original_price, None

def get_best_discount(user_id: int, prod_id: str, base_price: int):
    """Get best discount between VIP rank and flash sale (not stacked)"""
    flash_price, flash_info = get_flash_sale_price(prod_id, base_price)
    if flash_info and flash_price < base_price:
        return flash_price, 'flash', flash_info
    return base_price, None, None

def get_upsell_products(purchased_prod_id: str, limit: int = 2):
    """Find related products for upsell suggestion"""
    purchased = products.get(purchased_prod_id)
    if not purchased:
        return []
    purchased_cat = get_product_category(purchased['name'])
    candidates = []
    for pid, p in products.items():
        if pid == purchased_prod_id:
            continue
        cat = get_product_category(p['name'])
        if cat == purchased_cat:
            stock_count = len(p.get('stock', [])) if not p.get('is_supplier_source_resell') else p.get('supplier_source_stock', 0)
            has_stock = stock_count > 0 or p.get('requires_gmail', False)
            if has_stock:
                candidates.append((pid, p))
    candidates.sort(key=lambda x: x[1]['price'])
    return candidates[:limit]

def _get_discount_display_line(user_id: int, prod_id: str, base_price: int):
    """Generate discount info line for product detail view"""
    best_price, discount_type, info = get_best_discount(user_id, prod_id, base_price)
    if discount_type == 'flash':
        return f"\n<tg-emoji emoji-id=\"5303290914041505430\">⚡</tg-emoji> <b>FLASH SALE -{info['discount_percent']}%:</b> <s>{base_price:,}đ</s> → <b>{best_price:,}đ</b> (Còn {info['countdown']})\n"
    return ""

def get_user_wheel_data(user_id: int):
    """Get or create wheel data for user"""
    uid_str = str(user_id)
    if uid_str not in wheel_data:
        wheel_data[uid_str] = {'spins': 0, 'last_free_spin': 0, 'total_won': 0, 'history': []}
    return wheel_data[uid_str]

def spin_the_wheel():
    """Spin the wheel and return a prize based on weights - respects promo budget"""
    budget_remaining = get_daily_promo_budget() - get_daily_promo_spent()
    if budget_remaining <= 0:
        nothing_prize = next((p for p in WHEEL_PRIZES if p['type'] == 'nothing'), WHEEL_PRIZES[2])
        return nothing_prize
    total_weight = sum(p['weight'] for p in WHEEL_PRIZES)
    r = random.randint(1, total_weight)
    cumulative = 0
    for prize in WHEEL_PRIZES:
        cumulative += prize['weight']
        if r <= cumulative:
            return prize
    return WHEEL_PRIZES[-1]

def calculate_warranty_expiry(purchase_timestamp: float, warranty_text: str):
    """
    Tính thời gian hết hạn bảo hành
    Returns: timestamp khi hết hạn hoặc None nếu không có bảo hành
    """
    if not warranty_text or warranty_text.lower() in ['không', 'none', 'n/a']:
        return None
    
    # Parse warranty text (e.g., "30 ngày", "1 tháng", "6 tháng")
    warranty_lower = warranty_text.lower()
    days = 0
    
    if 'ngày' in warranty_lower:
        try:
            days = int(''.join(filter(str.isdigit, warranty_lower)))
        except (TypeError, ValueError):
            pass
    elif 'tháng' in warranty_lower:
        try:
            months = int(''.join(filter(str.isdigit, warranty_lower)))
            days = months * 30
        except (TypeError, ValueError):
            pass
    elif 'năm' in warranty_lower:
        try:
            years = int(''.join(filter(str.isdigit, warranty_lower)))
            days = years * 365
        except (TypeError, ValueError):
            pass
    
    if days > 0:
        return purchase_timestamp + (days * 24 * 60 * 60)
    
    return None


def get_top_referrers(limit=10):
    """
    Lấy top người giới thiệu theo hoa hồng
    Returns: List of {user_id, full_name, referral_count, total_commission, rank}
    """
    top_list = []
    
    for user_id_str, data in referral_data.items():
        total_commission = data.get('total_commission', 0)
        
        # Skip users with 0 commission
        if total_commission <= 0:
            continue
        
        # Get user info
        user_info = user_data_db.get(user_id_str, {})
        full_name = user_info.get('first_name', 'Unknown User')
        
        top_list.append({
            'user_id': user_id_str,
            'full_name': full_name,
            'referral_count': len(data.get('referred_users', [])),
            'total_commission': total_commission
        })
    
    # Sort by commission descending
    top_list.sort(key=lambda x: x['total_commission'], reverse=True)
    
    
    # Add rank
    for idx, item in enumerate(top_list[:limit], 1):
        item['rank'] = idx
    
    return top_list[:limit]



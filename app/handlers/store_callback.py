from __future__ import annotations

try:
    from app.state import app_state
    app_state.bridge_from_globals(globals())
except ImportError:
    pass


def _format_store_description_text(value) -> str:
    cleaned = _plain_text_preserve_emoji(str(value or ""))
    return html.escape(cleaned)


def _checkout_labels(user_id):
    return {
        "vi": {"choose_qty": "CHỌN SỐ LƯỢNG MUỐN MUA", "product": "Sản phẩm", "unit_price": "Đơn giá", "stock": "Tồn kho khả dụng", "quantity": "Số lượng", "enter_qty": "Nhập số lượng", "back": "Quay lại", "confirm": "XÁC NHẬN MUA HÀNG", "total": "Tổng tiền", "choose_payment": "Vui lòng chọn phương thức thanh toán", "balance": "Số dư", "insufficient": "Không đủ", "bank": "Chuyển khoản (QR)", "coupon": "Nhập mã giảm giá", "use_combo": "Dùng {balance:,}đ + QR {remaining:,}đ", "out": "Sản phẩm hiện đang hết hàng!", "missing": "Sản phẩm không tồn tại!"},
        "en": {"choose_qty": "CHOOSE QUANTITY", "product": "Product", "unit_price": "Unit price", "stock": "Available stock", "quantity": "Quantity", "enter_qty": "Enter quantity", "back": "Back", "confirm": "CONFIRM PURCHASE", "total": "Total", "choose_payment": "Choose a payment method", "balance": "Balance", "insufficient": "Insufficient", "bank": "Bank transfer (QR)", "coupon": "Enter coupon", "use_combo": "Use {balance:,}đ + QR {remaining:,}đ", "out": "This product is out of stock!", "missing": "Product not found!"},
        "zh": {"choose_qty": "选择购买数量", "product": "商品", "unit_price": "单价", "stock": "可用库存", "quantity": "数量", "enter_qty": "输入数量", "back": "返回", "confirm": "确认购买", "total": "总计", "choose_payment": "请选择付款方式", "balance": "余额", "insufficient": "余额不足", "bank": "银行转账（QR）", "coupon": "输入优惠码", "use_combo": "使用 {balance:,}đ + QR {remaining:,}đ", "out": "该商品已缺货！", "missing": "商品不存在！"},
    }[get_user_lang(user_id)]


def _render_text_with_custom_emoji_entities(value):
    import re
    from telegram import MessageEntity

    def _utf16_len(text: str) -> int:
        return len((text or "").encode("utf-16-le")) // 2

    def _safe_placeholder_glyph(raw_glyph: str) -> str:
        cleaned = html.unescape(re.sub(r"<[^>]+>", "", str(raw_glyph or ""))).strip()
        return cleaned[:1] or "\u2B50"

    # Map HTML tag names to MessageEntity types
    _TAG_ENTITY_MAP = {
        "b": MessageEntity.BOLD,
        "strong": MessageEntity.BOLD,
        "i": MessageEntity.ITALIC,
        "em": MessageEntity.ITALIC,
        "u": MessageEntity.UNDERLINE,
        "ins": MessageEntity.UNDERLINE,
        "s": MessageEntity.STRIKETHROUGH,
        "strike": MessageEntity.STRIKETHROUGH,
        "del": MessageEntity.STRIKETHROUGH,
        "code": MessageEntity.CODE,
        "pre": MessageEntity.PRE,
        "blockquote": MessageEntity.BLOCKQUOTE,
    }
    # Tags that produce a newline when opened/closed (block-level)
    _BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "blockquote", "pre"}

    source = str(value or "")
    token_regex = re.compile(
        r'<tg-emoji\s+emoji-id=(?:"|\')?(\d+)(?:"|\')?[^>]*>(.*?)</tg-emoji>'
        r'|<br\s*/?>'
        r'|</?\w+(?:\s[^>]*)?>',
        re.IGNORECASE | re.DOTALL,
    )

    parts = []
    entities = []
    cursor = 0
    # Stack: list of (tag_name, entity_type, offset_at_open)
    format_stack = []

    def _append_plain(text: str):
        if text:
            parts.append(html.unescape(text))

    for match in token_regex.finditer(source):
        _append_plain(source[cursor:match.start()])

        emoji_id = match.group(1)
        if emoji_id:
            glyph = _safe_placeholder_glyph(match.group(2))
            if glyph:
                offset = _utf16_len("".join(parts))
                parts.append(glyph)
                entities.append(
                    MessageEntity(
                        type=MessageEntity.CUSTOM_EMOJI,
                        offset=offset,
                        length=_utf16_len(glyph),
                        custom_emoji_id=str(emoji_id),
                    )
                )
        else:
            tag_str = match.group(0)
            # Parse the tag name and whether it's closing
            tag_match = re.match(r'<(/?)(\w+)(\s[^>]*)?\s*/?>', tag_str, re.IGNORECASE)
            if tag_match:
                is_closing = tag_match.group(1) == "/"
                tag_name = tag_match.group(2).lower()
                tag_attrs = tag_match.group(3) or ""

                if tag_name == "br":
                    parts.append("\n")
                elif is_closing:
                    # Closing tag: find matching open tag on stack
                    entity_type = _TAG_ENTITY_MAP.get(tag_name)
                    if entity_type:
                        # Pop from stack (find last matching)
                        for idx in range(len(format_stack) - 1, -1, -1):
                            if format_stack[idx][0] == tag_name:
                                _, etype, open_offset = format_stack.pop(idx)
                                current_offset = _utf16_len("".join(parts))
                                length = current_offset - open_offset
                                if length > 0:
                                    entities.append(
                                        MessageEntity(
                                            type=etype,
                                            offset=open_offset,
                                            length=length,
                                        )
                                    )
                                break
                    if tag_name in _BLOCK_TAGS:
                        parts.append("\n")
                else:
                    # Opening tag: add block newline BEFORE recording offset
                    if tag_name in _BLOCK_TAGS:
                        parts.append("\n")
                    entity_type = _TAG_ENTITY_MAP.get(tag_name)
                    if entity_type:
                        # Check for expandable blockquote
                        if tag_name == "blockquote" and "expandable" in tag_attrs.lower():
                            entity_type = MessageEntity.EXPANDABLE_BLOCKQUOTE
                        open_offset = _utf16_len("".join(parts))
                        format_stack.append((tag_name, entity_type, open_offset))
                    # (block newline already added above)

        cursor = match.end()

    _append_plain(source[cursor:])

    plain_text = "".join(parts)
    return plain_text, entities


def _store_product_image_path(product: dict):
    """Return absolute Path to product image file on disk, or None."""
    if not isinstance(product, dict):
        return None
    try:
        from pathlib import Path as _Path
        base = _Path(__file__).resolve().parent.parent / "api" / "static" / "products"

        name = str(product.get("image_local") or "").strip()
        if name:
            candidate = base / name
            if candidate.is_file():
                return candidate

        product_id = str(product.get("_product_id") or "").strip()
        if product_id:
            for ext in ("jpg", "jpeg", "png", "webp"):
                candidate = base / f"{product_id}.{ext}"
                if candidate.is_file():
                    return candidate
    except Exception:
        return None
    return None


def _store_category_slug(name: str) -> str:
    import unicodedata as _ud, re as _re
    s = _ud.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    s = _re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "uncategorized"


def _store_category_image_path(product: dict):
    """Return absolute Path to category image file shared by all products in same category."""
    if not isinstance(product, dict):
        return None
    get_effective_category = globals().get("get_effective_store_category")
    if callable(get_effective_category):
        cat = str(get_effective_category(product) or "").strip()
    else:
        cat = ""
    if not cat:
        cat = str(product.get("store_category") or "").strip()
    if not cat:
        try:
            get_cat = globals().get("get_product_category")
            if callable(get_cat):
                cat = str(get_cat(product.get("name") or "") or "")
        except Exception:
            cat = ""
    if not cat:
        return None
    slug = _store_category_slug(cat)
    if not slug:
        return None
    try:
        from pathlib import Path as _Path
        base = _Path(__file__).resolve().parent.parent / "api" / "static" / "categories"
        for ext in ("jpg", "jpeg", "png", "webp"):
            candidate = base / f"{slug}.{ext}"
            if candidate.is_file():
                return candidate
    except Exception:
        return None
    return None


def _telegram_utf16_len(text: str) -> int:
    return len(str(text or "").encode("utf-16-le")) // 2


def _telegram_trim_utf16(text: str, limit: int) -> str:
    value = str(text or "")
    if _telegram_utf16_len(value) <= limit:
        return value
    out = []
    used = 0
    for ch in value:
        size = _telegram_utf16_len(ch)
        if used + size > limit:
            break
        out.append(ch)
        used += size
    return "".join(out)


def _filter_entities_to_text(entities, text: str):
    text_len = _telegram_utf16_len(text)
    safe = []
    for entity in entities or []:
        try:
            start = int(getattr(entity, "offset", 0) or 0)
            length = int(getattr(entity, "length", 0) or 0)
        except (TypeError, ValueError):
            continue
        if start >= 0 and length > 0 and start + length <= text_len:
            safe.append(entity)
    return safe


def _trim_caption_with_entities(text: str, entities, limit: int = 1024):
    if _telegram_utf16_len(text) <= limit:
        return text, _filter_entities_to_text(entities, text)
    trimmed = _telegram_trim_utf16(text, limit - 1).rstrip() + "…"
    return trimmed, _filter_entities_to_text(entities, trimmed)


def _trim_product_description_for_caption(description: str, reserve_utf16: int, limit: int = 1024) -> str:
    available = max(80, int(limit) - int(reserve_utf16) - 1)
    if _telegram_utf16_len(description) <= available:
        return description
    return _telegram_trim_utf16(description, available).rstrip() + "..."


async def _persist_product_media_cache():
    try:
        save_data_fn = globals().get("save_data")
        products_file = globals().get("PRODUCTS_FILE")
        if save_data_fn is not None and products_file is not None:
            await save_data_fn(force=True, tables=[products_file])
    except Exception:
        pass


async def _show_store_product_panel(query, context, product, html_text, reply_markup):
    """Send product as photo+caption using product image (preferred) or category image (fallback)."""
    if not isinstance(product, dict):
        return await _show_store_panel(query, context, html_text, reply_markup)

    rendered_text, rendered_entities = _render_text_with_custom_emoji_entities(html_text)
    if _telegram_utf16_len(rendered_text) > 1024:
        return await _show_store_panel(query, context, html_text, reply_markup)

    source_message = getattr(query, "message", None)
    chat_id = getattr(source_message, "chat_id", None)
    if chat_id is None:
        return await _show_store_panel(query, context, html_text, reply_markup)

    async def _send_photo_payload(payload, caption_entities=rendered_entities):
        return await context.bot.send_photo(
            chat_id=chat_id,
            photo=payload,
            caption=rendered_text,
            caption_entities=caption_entities,
            reply_markup=reply_markup,
        )

    async def _try_local(path, caption_entities=rendered_entities):
        if path is None:
            return None
        file_handle = None
        try:
            file_handle = open(path, "rb")
            return await _send_photo_payload(file_handle, caption_entities=caption_entities)
        finally:
            if file_handle is not None:
                try:
                    file_handle.close()
                except Exception:
                    pass

    def _looks_like_entity_media_error(error):
        text = str(error or "").lower()
        return "document_invalid" in text or "entity" in text or "parse" in text

    attempts = []
    product_file_id = str(product.get("image_file_id") or "").strip()
    category_file_id = str(product.get("category_image_file_id") or "").strip()
    product_path = _store_product_image_path(product)
    category_path = _store_category_image_path(product)

    if product_file_id:
        attempts.append(("product_id", product_file_id))
    if product_path is not None:
        attempts.append(("product_path", product_path))
    if category_file_id:
        attempts.append(("category_id", category_file_id))
    if category_path is not None:
        attempts.append(("category_path", category_path))

    sent = None
    used_source = None
    dirty_cache = False
    for source, payload in attempts:
        try:
            sent = await (_try_local(payload) if source.endswith("_path") else _send_photo_payload(payload))
            used_source = source
            break
        except (BadRequest, TelegramError) as send_error:
            logger.warning(f"[store_panel] send_photo failed ({source}): {send_error}")
            if rendered_entities and _looks_like_entity_media_error(send_error):
                try:
                    sent = await (
                        _try_local(payload, caption_entities=None)
                        if source.endswith("_path")
                        else _send_photo_payload(payload, caption_entities=None)
                    )
                    used_source = source
                    break
                except (BadRequest, TelegramError) as plain_error:
                    logger.warning(f"[store_panel] send_photo plain failed ({source}): {plain_error}")
            if source == "product_id":
                product.pop("image_file_id", None)
                dirty_cache = True
            elif source == "category_id":
                product.pop("category_image_file_id", None)
                dirty_cache = True

    if dirty_cache:
        await _persist_product_media_cache()

    if sent is None:
        return await _show_store_panel(query, context, html_text, reply_markup)

    try:
        photos = getattr(sent, "photo", None) or []
        if photos and used_source and used_source.endswith("_path"):
            best = photos[-1]
            new_file_id = getattr(best, "file_id", None)
            if new_file_id:
                product["category_image_file_id" if used_source == "category_path" else "image_file_id"] = str(new_file_id)
                await _persist_product_media_cache()
    except Exception:
        pass

    if source_message is not None:
        try:
            await source_message.delete()
        except (BadRequest, TelegramError):
            pass
    return sent


async def _show_store_panel(query, context, html_text, reply_markup):
    rendered_text, rendered_entities = _render_text_with_custom_emoji_entities(html_text)
    rendered_text = _telegram_trim_utf16(rendered_text, 4096)
    rendered_entities = _filter_entities_to_text(rendered_entities, rendered_text)
    source_message = getattr(query, "message", None)
    chat_id = getattr(source_message, "chat_id", None)

    if chat_id is not None:
        try:
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=rendered_text,
                entities=rendered_entities,
                reply_markup=reply_markup,
            )
            if source_message is not None:
                try:
                    await source_message.delete()
                except (BadRequest, TelegramError):
                    pass
            return sent
        except (BadRequest, TelegramError) as send_error:
            logger.warning(f"[store_panel] entity send failed: {send_error}")

        plain_text = _plain_text_preserve_emoji(html_text)
        sent = await safe_send_message(
            context,
            chat_id,
            plain_text,
            reply_markup=reply_markup,
        )
        if sent is not None:
            if source_message is not None:
                try:
                    await source_message.delete()
                except (BadRequest, TelegramError):
                    pass
            return sent

    try:
        await query.edit_message_text(
            rendered_text,
            entities=rendered_entities,
            reply_markup=reply_markup,
        )
        return True
    except (BadRequest, TelegramError) as edit_error:
        logger.warning(f"[store_panel] entity edit failed: {edit_error}")
        return await safe_edit_message(
            query,
            text=_plain_text_preserve_emoji(html_text),
            reply_markup=reply_markup,
            parse_mode=None,
        )


async def _show_store_product_detail(
    query,
    context,
    prod_id: str,
    back_callback_data: str | None = None,
    back_button_text: str | None = None,
    already_answered: bool = False,
):
    if not already_answered:
        await safe_answer(query)
    lang = get_user_lang(query.from_user.id)
    curr = "đ" if lang == "vi" else " VND"

    def _fmt_price(price_vnd: int) -> str:
        if not price_vnd: return "0đ" if lang == "vi" else "0 USDT"
        if lang == "vi": return f"{price_vnd:,}đ"
        try:
            rate = float(globals().get("_cached_live_usdt_rate") or USDT_TRC20_RATE_VND_PER_USDT)
            return f"{price_vnd / rate:.2f} USDT"
        except (TypeError, ValueError, ZeroDivisionError):
            return f"{price_vnd:,} VND"


    labels = {
        "vi": {
            "description": "Mô tả", "price": "Giá", "duration": "Thời hạn", "warranty": "Bảo hành",
            "auto": "Giao tự động", "status": "Trạng thái", "available": "Còn {count} sản phẩm",
            "out": "Hết hàng", "how_email": "Thanh toán → nhập email → admin xử lý → nhận hàng.",
            "how_auto": "Thanh toán → nhận tài khoản ngay trên Telegram.", "how": "Cách mua",
            "buy": "Mua ngay", "busy": "Admin đang bận", "notify": "Thông báo khi có hàng", "back": "Quay lại Danh Mục",
            "manual": "Dịch vụ xử lý thủ công", "manual_avail": "Còn {count} lượt đặt",
            "manual_full": "Tạm ngừng nhận đơn", "suspended": "Tạm ngừng bán"
        },
        "en": {
            "description": "Description", "price": "Price", "duration": "Duration", "warranty": "Warranty",
            "auto": "Automatic delivery", "status": "Status", "available": "{count} products available",
            "out": "Out of stock", "how_email": "Pay → enter email → admin processes → receive your order.",
            "how_auto": "Pay → receive the account instantly on Telegram.", "how": "How to buy",
            "buy": "Buy now", "busy": "Admin is busy", "notify": "Notify me when available", "back": "Back to Categories",
            "manual": "Manual processing service", "manual_avail": "{count} slots remaining",
            "manual_full": "Temporarily stopped taking orders", "suspended": "Suspended"
        },
        "zh": {
            "description": "描述", "price": "价格", "duration": "有效期", "warranty": "保修",
            "auto": "自动发货", "status": "状态", "available": "剩余 {count} 件",
            "out": "缺货", "how_email": "付款 → 输入邮箱 → 管理员处理 → 收货。",
            "how_auto": "付款 → 立即在 Telegram 接收账号。", "how": "购买方式",
            "buy": "立即购买", "busy": "管理员忙碌中", "notify": "到货通知", "back": "返回分类",
            "manual": "人工处理服务", "manual_avail": "剩余 {count} 个名额",
            "manual_full": "暂停接单", "suspended": "暂停销售"
        },
    }.get(lang, {})

    p = products.get(prod_id)
    if isinstance(p, dict):
        p["_product_id"] = str(prod_id)
    if not p or not isinstance(p, dict):
        await safe_answer(query, lt(query.from_user.id, "Sản phẩm không tồn tại", "This product no longer exists", "该商品不存在"), show_alert=True)
        return True

    requires_gmail = p.get('requires_gmail', False)
    
    raw_name = str(p.get("name") or prod_id)
    get_effective_category = globals().get("get_effective_store_category")
    effective_category = get_effective_category(p) if callable(get_effective_category) else (p.get("store_category") or get_product_category(raw_name))
    product_icon_id = get_store_icon_id(raw_name, get_store_icon_id(effective_category, "5854908544712707500"))
    product_icon_fallback = {
        "Netflix": "🎬",
        "YouTube Premium": "▶️",
        "Spotify & Music": "🎵",
        "Google Drive & One": "☁️",
        "CapCut & Edit Video": "🎞️",
        "Adobe Creative Cloud": "🎨",
        "TikTok": "🎵",
        "Proxy": "🛡️",
        "AI Tools (GPT, Copilot...)": "🤖",
    }.get(str(effective_category or ""), "📦")
    product_icon_markup = f'<tg-emoji emoji-id="{product_icon_id}">{product_icon_fallback}</tg-emoji>'
    can_buy = False
    display_price_text = _fmt_price(p.get("price", 0) or 0)
    discount_line = _get_discount_display_line(query.from_user.id, prod_id, p["price"])

    if requires_gmail:
        pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
        max_pending = p.get('max_pending_orders', 10)
        slots_left = max_pending - pending_count

        if slots_left > 0:
            stock_info = f'{E_LOADING} {labels["manual"]}\n{E_SUCCESS} {labels["status"]}: {labels["manual_avail"].format(count=slots_left)}'
            can_buy = True
        else:
            stock_info = f'{E_LOADING} {labels["manual"]}\n{E_LIMIT} {labels["status"]}: {labels["manual_full"]}'
            can_buy = False
    else:
        stock_count = int(get_local_stock_available_count(p) or 0)

        if stock_count > 0:
            stock_info = f'{E_ANDROID} {labels["auto"]}\n{E_SUCCESS} {labels["status"]}: {labels["available"].format(count=stock_count)}'
            can_buy = True
        else:
            stock_info = f'{E_ANDROID} {labels["auto"]}\n{E_ERROR} {labels["status"]}: {labels["out"]}'
            can_buy = False

    localized_name = str(p.get(f"name_{lang}") or p.get("name") or prod_id)
    localized_description = p.get(f"description_{lang}") or p.get("description") or ""
    desc_text = _format_store_description_text(localized_description)
    
    default_duration = "Không giới hạn" if lang == "vi" else ("Unlimited" if lang == "en" else "无限制")
    default_warranty = "Không" if lang == "vi" else ("No" if lang == "en" else "无")
    
    def_dur_val = p.get("duration", default_duration)
    if def_dur_val == "Theo thông tin sản phẩm":
        def_dur_val = "Theo thông tin sản phẩm" if lang == "vi" else ("See product info" if lang == "en" else "查看产品信息")
    
    def_war_val = p.get("warranty", default_warranty)
    if def_war_val == "Bảo hành theo quy định":
        def_war_val = "Bảo hành theo quy định" if lang == "vi" else ("Standard warranty" if lang == "en" else "标准保修")
        
    duration_text = html.escape(p.get(f"duration_{lang}") or def_dur_val)
    warranty_text = html.escape(p.get(f"warranty_{lang}") or def_war_val)

    # labels already built at the top

    msg = (
        f'{E_TAG} <b>{html.escape(localized_name)}</b>\n'
        f'<blockquote expandable>📝 <b>{labels["description"]}:</b>\n{desc_text}</blockquote>\n'
        f'{E_TAG} {labels["price"]}: <b>{display_price_text}</b>\n'
        f'{E_LOADING} {labels["duration"]}: <b>{duration_text}</b>\n'
        f'{E_SHIELD} {labels["warranty"]}: <b>{warranty_text}</b>\n'
        f'{discount_line}'
        f'{stock_info}\n'
        f'<blockquote><b>{labels["how"]}:</b> {labels["how_email"] if requires_gmail else labels["how_auto"]}</blockquote>\n'
    )

    btns = []
    detail_labels = locals().get("labels", {})
    if can_buy:
        btns.append([_btn(detail_labels.get("buy", "Mua ngay"), icon_id="5402186569006210455", callback_data=f"sel_qty_{prod_id}", style="success")])
    else:
        if requires_gmail:
            btns.append([_btn(detail_labels.get("busy", "Admin đang bận"), icon_id="5197288647275071607", callback_data="ignore", style="danger")])
        else:
            btns.append([_btn(detail_labels.get("out", "Hết hàng"), icon_id="5273914604752216432", callback_data="ignore", style="danger")])
            btns.append([_btn(detail_labels.get("notify", "Thông báo khi có hàng"), icon_id="5447364299200678034", callback_data=f"waitlist_{prod_id}")])

    from app.core.emoji_runtime import upgrade_text_to_premium_emoji

    msg = upgrade_text_to_premium_emoji(
        msg.replace(E_TAG, product_icon_markup)
        .replace(E_LOADING, '<tg-emoji emoji-id="5373251851074415873">📄</tg-emoji>')
        .replace(E_LIMIT, '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji>')
        .replace(E_ERROR, '<tg-emoji emoji-id="5273914604752216432">❌</tg-emoji>')
    )

    get_effective_category = globals().get("get_effective_store_category")
    cat = get_effective_category(p) if callable(get_effective_category) else (p.get('store_category') or get_product_category(p['name']))
    btns.append([_btn(back_button_text or detail_labels.get("back", "Quay lại Danh Mục"), icon_id="6206032691075223572", callback_data=back_callback_data or f"view_cat_{cat}")])
    reply_markup = InlineKeyboardMarkup(btns)
    await _show_store_product_panel(query, context, p, msg, reply_markup)
    return True


def _get_store_effective_unit_price(user_id: int, context: ContextTypes.DEFAULT_TYPE, prod_id: str, product: dict, qty: int) -> int:
    unit_price, _discount_type, _discount_info = get_best_discount(user_id, prod_id, product['price'])
    store_coupon_discount = 0
    if getattr(context, "user_data", None) is not None:
        _store_coupon_code, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
    if store_coupon_discount > 0:
        coupon_unit_price = max(0, product['price'] - store_coupon_discount)
        unit_price = min(unit_price, coupon_unit_price)
    return int(unit_price or 0)


def _get_store_category_panel_text(category_name: str, user_id: int, refresh_summary: str = "") -> str:
    lang = get_user_lang(user_id)
    category_copy = {
        "vi": ("DANH MỤC", "Chọn sản phẩm chi tiết:"),
        "en": ("CATEGORY", "Choose a product:"),
        "zh": ("分类", "请选择商品："),
    }[lang]
    category_icon_id = get_store_icon_id(category_name, "5854908544712707500")
    summary = f"\n\n{refresh_summary}" if refresh_summary else ""
    return (
        f"<tg-emoji emoji-id=\"{category_icon_id}\">🎬</tg-emoji> "
        f"<b>{category_copy[0]}: {html.escape(category_name)}</b>\n\n"
        f"{category_copy[1]}{summary}"
    )


async def handle_store_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "store_main":
        # Acknowledge early to stop Telegram spinner immediately.
        await safe_answer(query)

        lang = get_user_lang(query.from_user.id)
        store_copy = {
            "vi": ("CỬA HÀNG DỊCH VỤ", "Chọn danh mục sản phẩm bạn quan tâm:"),
            "en": ("SERVICE STORE", "Choose a product category:"),
            "zh": ("服务商店", "请选择商品分类："),
        }[lang]
        store_text = (
            "<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> "
            f"<b>{store_copy[0]}</b>\n\n{store_copy[1]}"
        )
        store_markup = create_store_menu(selected_category=None, user_id=query.from_user.id)
        src_msg = query.message
        is_media_message = bool(
            getattr(src_msg, "video", None)
            or getattr(src_msg, "photo", None)
            or getattr(src_msg, "animation", None)
            or getattr(src_msg, "document", None)
            or getattr(src_msg, "audio", None)
            or getattr(src_msg, "voice", None)
        )

        if is_media_message:
            sent = await safe_send_message(
                context,
                src_msg.chat_id,
                store_text,
                parse_mode=ParseMode.HTML,
                reply_markup=store_markup,
            )
            if sent is not None:
                try:
                    await src_msg.delete()
                except (Forbidden, BadRequest) as e:
                    logger.debug(f"Cannot delete old media menu message: {e}")
                return True

            # Fallback if send_message unexpectedly fails.
            try:
                await query.edit_message_caption(
                    caption=store_text,
                    reply_markup=store_markup,
                    parse_mode=ParseMode.HTML,
                )
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"store_main media fallback failed: {e}")
            return True

        # Text message path
        await safe_edit_message(
            query,
            text=store_text,
            reply_markup=store_markup,
            parse_mode='HTML',
        )
        return True
        
    elif data.startswith("waitlist_"):
        wl_prod_id = data.replace("waitlist_", "")
        await handle_waitlist_callback(update, context, wl_prod_id)
        return True

    elif data.startswith("view_combo_"):
        await safe_answer(query)
        combo_id = data.replace("view_combo_", "")
        combo = combo_deals.get(combo_id)
        if not combo:
            await safe_answer(query, "Combo không tồn tại", show_alert=True)
            return True
        combo_prods = [products.get(pid) for pid in combo.get('products', []) if pid in products]
        if len(combo_prods) != 2:
            await safe_answer(query, "Combo không hợp lệ", show_alert=True)
            return True
        total = sum(p['price'] for p in combo_prods)
        combo_price = int(total * (100 - combo['discount_percent']) / 100)
        msg = (
            f"<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> <b>COMBO ƯU ĐÃI</b>\n\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {html.escape(combo_prods[0]['name'])}\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> {html.escape(combo_prods[1]['name'])}\n\n"
            f'<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji> Giá gốc: <s>{total:,}đ</s>\n'
            f"<tg-emoji emoji-id=\"5863724849851011383\">💵</tg-emoji> Giá combo: <b>{combo_price:,}đ</b> (-{combo['discount_percent']}%)\n\n"
            f"<i>Bấm vào từng sản phẩm để mua riêng:</i>"
        )
        btns = []
        pids = combo['products'] # Assuming combo['products'] is a list of product IDs
        # Build product buttons
        for pid in pids:
            p = products.get(pid)
            if p:
                btns.append([
                    _btn(
                        p['name'],
                        icon_id=get_store_icon_id(p['name'], "5431492767249342908"),
                        callback_data=f"view_prod_{pid}",
                        style="success" if is_store_product_available(pid, p) else "danger",
                    )
                ])
        btns.append([_btn(lt(query.from_user.id, "Quay lại", "Back", "返回"), icon_id="6206032691075223572", callback_data="store_main")])
        await _show_store_panel(query, context, msg, InlineKeyboardMarkup(btns))
        return True

    elif data.startswith("view_cat_"):
        await safe_answer(query)
        # Show Products in Category
        cat_name = data.replace("view_cat_", "")
        await safe_edit_message(
            query,
            text=_get_store_category_panel_text(cat_name, query.from_user.id),
            reply_markup=create_store_menu(selected_category=cat_name, user_id=query.from_user.id),
            parse_mode='HTML'
        )
        return True
        
    elif data.startswith("view_prod_"):
        await safe_answer(query)
        prod_id = data.replace("view_prod_", "")
        return await _show_store_product_detail(query, context, prod_id, already_answered=True)

    elif data.startswith("sel_qty_"):
        prod_id = data.replace("sel_qty_", "")
        p = products.get(prod_id)
        if not p: return True
        
        requires_gmail = p.get('requires_gmail', False)

        if requires_gmail:
            pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
            max_pending = p.get('max_pending_orders', 10)
            labels = _checkout_labels(query.from_user.id)
            lang = get_user_lang(query.from_user.id)
            manual = {
                "vi": {"busy": "ADMIN ĐANG BẬN!", "processing": "Đang xử lý", "return": "Vui lòng quay lại sau 10-30 phút", "title": "XÁC NHẬN ĐẶT DỊCH VỤ", "manual": "Dịch vụ manual", "original": "Giá gốc", "payment": "Thanh toán", "after": "Sau khi thanh toán", "steps": ("Bạn sẽ nhập email", "Admin setup trong 1-30 phút", "Nhận thông báo check mail"), "none": "Không"},
                "en": {"busy": "ADMIN IS BUSY!", "processing": "Processing", "return": "Please return in 10-30 minutes", "title": "CONFIRM SERVICE ORDER", "manual": "Manual service", "original": "Original price", "payment": "Payment", "after": "After payment", "steps": ("Enter your email", "Admin sets it up within 1-30 minutes", "Receive an email-check notification"), "none": "Unavailable"},
                "zh": {"busy": "管理员忙碌中！", "processing": "正在处理", "return": "请在 10-30 分钟后重试", "title": "确认服务订单", "manual": "人工服务", "original": "原价", "payment": "付款", "after": "付款后", "steps": ("输入邮箱", "管理员将在 1-30 分钟内设置", "收到查收邮件通知"), "none": "不可用"},
            }[lang]

            if pending_count >= max_pending:
                await safe_answer(query, f"⚠️ {manual['busy']}\n\n{manual['processing']}: {pending_count}/{max_pending}\n{manual['return']}", show_alert=True)
                return True

            user = update.effective_user
            user_info = db_get_user(user.id)
            balance = user_info.get('balance', 0) if user_info else 0
            unit_price, discount_type, discount_info = get_best_discount(user.id, prod_id, p['price'])
            total_price = unit_price
            product_name = p.get(f"name_{lang}") or p.get("name") or prod_id

            price_line = f"{E_TAG} <b>{labels['total']}:</b> {total_price:,} VNĐ\n"
            if total_price < p['price']:
                price_line = f"{E_TAG} <b>{manual['original']}:</b> <s>{p['price']:,} VNĐ</s>\n{E_TAG} <b>{manual['payment']}:</b> <b>{total_price:,} VNĐ</b>"
                if discount_type == 'flash_sale':
                    price_line += " (Flash Sale)"
                price_line += "\n"

            msg_text = (
                f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>{manual['title']}</b>\n\n"
                f"{E_TAG} <b>{labels['product']}:</b> {product_name}\n"
                f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>{labels['quantity']}:</b> 1 ({manual['manual']})\n"
                f"{price_line}\n"
                f"<tg-emoji emoji-id=\"5264919878082509254\">ℹ️</tg-emoji> <b>{manual['after']}:</b>\n"
                f"1. {manual['steps'][0]}\n2. {manual['steps'][1]}\n3. {manual['steps'][2]}\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> {labels['choose_payment']}:"
            )

            btns = []
            bal_text = f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> {labels['balance']} ({balance:,}đ)"
            if balance >= total_price:
                btns.append([_btn(bal_text, callback_data=f"pay_prod_bal_{prod_id}_1", style="success")])
            elif balance > 0:
                remaining = total_price - balance
                btns.append([_btn(labels["use_combo"].format(balance=balance, remaining=remaining), icon_id="5213403875670765022", callback_data=f"pay_prod_combo_{prod_id}_1", style="success")])
            else:
                btns.append([_btn(manual["none"], icon_id="5273914604752216432", callback_data="ignore", style="danger")])

            from app.integrations.payments_core import is_usdt_trc20_enabled, is_binance_pay_id_enabled
            if is_usdt_trc20_enabled() or is_binance_pay_id_enabled():
                btns.append([_btn("USDT (Binance ID / BEP20)", icon_id="5281029063459234079", callback_data=f"pay_prod_usdt_trc20_{prod_id}_1", style="success")])
            from app.integrations.payments_core import is_bank_transfer_enabled
            if is_bank_transfer_enabled():
                btns.append([_btn(labels["bank"], icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_1", style="success")])
            btns.append([_btn(labels["coupon"], icon_id="5377624166436445368", callback_data=f"store_coupon_{prod_id}_1")])
            btns.append([_btn(labels["back"], icon_id="6206032691075223572", callback_data=f"view_prod_{prod_id}")])

            await _show_store_panel(query, context, msg_text, InlineKeyboardMarkup(btns))
            return True
        
        # AUTO PRODUCTS - Cho chọn số lượng
        stock_count = int(get_local_stock_available_count(p) or 0)
        effective_stock = stock_count

        labels = _checkout_labels(query.from_user.id)
        if effective_stock <= 0:
            await safe_answer(query, f"❌ {labels['out']}", show_alert=True)
            return True

        _max_buy = min(effective_stock, 100) if effective_stock > 0 else 100
        
        btns = []
        row = []
        
        # Tạo nút 1-5
        for q in [1, 2, 3, 4, 5]:
            if q <= effective_stock:
                row.append(_btn(f"{q}", callback_data=f"buy_prod_confirm_{prod_id}_{q}", style="success"))
            
            if len(row) == 3:
                btns.append(row)
                row = []
                
        if row:
            btns.append(row)
            
        # Nút lớn hơn
        large_qty = []
        for q in [10, 20]:
            if q <= effective_stock and q > 5:
                large_qty.append(_btn(f"{q}", callback_data=f"buy_prod_confirm_{prod_id}_{q}", style="success"))
        if large_qty:
            btns.append(large_qty)
        
        btns.append([_btn(labels["enter_qty"], icon_id="5364075889669718872", callback_data=f"custom_qty_{prod_id}")])
        btns.append([_btn(labels["back"], icon_id="6206032691075223572", callback_data=f"view_prod_{prod_id}")])

        stock_display = str(stock_count)
        lang = get_user_lang(query.from_user.id)
        product_name = p.get(f"name_{lang}") or p.get("name") or prod_id

        msg_text = (
            f"<tg-emoji emoji-id=\"5334890573281114250\">🔢</tg-emoji> <b>{labels['choose_qty']}</b>\n\n"
            f"{E_TAG} {labels['product']}: {product_name}\n"
            f"{E_TAG} {labels['unit_price']}: {p['price']:,} VNĐ\n"
            f"{E_STAT} {labels['stock']}: {stock_display}\n\n"
            f"<tg-emoji emoji-id=\"6186252635805323641\">👇</tg-emoji> {labels['quantity']}:"
        )

        await _show_store_panel(query, context, msg_text, InlineKeyboardMarkup(btns))
        return True

    elif data.startswith("buy_prod_confirm_"):
        # Fix: Use rsplit to handle product IDs with underscores
        clean_data = data.replace("buy_prod_confirm_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                prod_id = clean_data; qty = 1
        else:
            prod_id = clean_data; qty = 1
        
        labels = _checkout_labels(query.from_user.id)
        p = products.get(prod_id)
        if not p:
            await safe_answer(query, f"❌ {labels['missing']}", show_alert=True)
            return True

        unit_price, discount_type, discount_info = get_best_discount(update.effective_user.id, prod_id, p['price'])
        total_price = unit_price * qty
        
        user_id = update.effective_user.id
        user_info = db_get_user(user_id)
        balance = user_info.get('balance', 0) if user_info else 0
        
        btns = []
        
        bal_text = f"{labels['balance']} ({balance:,}đ)"
        if balance >= total_price:
            btns.append([_btn(bal_text, icon_id="5458774648621643551", callback_data=f"pay_prod_bal_{prod_id}_{qty}", style="success")])
        elif balance > 0:
            remaining = total_price - balance
            btns.append([_btn(
                labels["use_combo"].format(balance=balance, remaining=remaining),
                icon_id="5458774648621643551",
                callback_data=f"pay_prod_combo_{prod_id}_{qty}",
                style="success",
            )])
        else:
            btns.append([_btn(f"{bal_text} - {labels['insufficient']}", icon_id="5273914604752216432", callback_data="ignore", style="danger")])

        from app.integrations.payments_core import is_usdt_trc20_enabled, is_binance_pay_id_enabled
        if is_usdt_trc20_enabled() or is_binance_pay_id_enabled():
            btns.append([_btn("USDT (Binance ID / BEP20)", icon_id="5281029063459234079", callback_data=f"pay_prod_usdt_trc20_{prod_id}_{qty}", style="success")])
        from app.integrations.payments_core import is_bank_transfer_enabled
        if is_bank_transfer_enabled():
            btns.append([_btn(labels["bank"], icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}", style="success")])
        btns.append([_btn(labels["coupon"], icon_id="5447364299200678034", callback_data=f"store_coupon_{prod_id}_{qty}")])
        btns.append([_btn(labels["back"], icon_id="6206032691075223572", callback_data=f"sel_qty_{prod_id}")])

        combo_note = ""
        if 0 < balance < total_price:
            combo_note = f"\n\n<tg-emoji emoji-id=\"5460753627817723162\">💡</tg-emoji> <i>Bạn có thể kết hợp ví ({balance:,}đ) + chuyển khoản ({total_price - balance:,}đ)</i>"

        lang = get_user_lang(user_id)
        product_name = p.get(f"name_{lang}") or p.get("name") or prod_id
        await _show_store_panel(
            query,
            context,
            f'<tg-emoji emoji-id="5247134066322447995">🛍</tg-emoji> <b>{labels["confirm"]}</b>\n\n'
            f'<tg-emoji emoji-id="5240228673738527951">🏷</tg-emoji> {labels["product"]}: {product_name}\n'
            f'<tg-emoji emoji-id="5305749482170758709">0️⃣</tg-emoji> {labels["quantity"]}: {qty}\n'
            f'<tg-emoji emoji-id="5240228673738527951">🏷</tg-emoji> {labels["total"]}: {total_price:,} VNĐ{" (-" + str(discount_info["discount_percent"]) + "%)" if discount_type else ""}'
            f'{combo_note}\n\n'
            f'<tg-emoji emoji-id="6186252635805323641">👇</tg-emoji> {labels["choose_payment"]}:',
            InlineKeyboardMarkup(btns),
        )
        return True
    
    elif data.startswith("custom_qty_"):
        # Handle custom quantity input
        prod_id = data.replace("custom_qty_", "")
        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "❌ Sản phẩm không tồn tại!", show_alert=True)
            return True

        else:
            stock_count = int(get_local_stock_available_count(p) or 0)
            _max_text = str(stock_count)

        # Set state for text input only after stock validation passes
        context.user_data['state'] = f'awaiting_custom_qty:{prod_id}'
        await _show_store_panel(
            query,
            context,
            f"<tg-emoji emoji-id=\"5350752364246606166\">✏️</tg-emoji> <b>NHẬP SỐ LƯỢNG TỰ CHỌN</b>\n\n"
            f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
            f"{E_TAG} <b>Đơn giá:</b> {p['price']:,} VNĐ\n"
            f"{E_STAT} <b>Tồn kho:</b> {stock_count}\n"
            f"<tg-emoji emoji-id=\"6186252635805323641\">👉</tg-emoji> Vui lòng <b>nhập số lượng</b> muốn mua:\n\n"
            f"<i>Ví dụ: Nhập 1000 nếu muốn server chạy đúng 1000 đơn vị</i>",
            InlineKeyboardMarkup([[_btn(lt(query.from_user.id, "Hủy", "Cancel", "取消"), icon_id="5273914604752216432", callback_data=f"sel_qty_{prod_id}", style="danger")]]),
        )
        return True

    elif data.startswith("pay_prod_bal_"):
        # Fix: Use rsplit to handle product IDs with underscores
        clean_data = data.replace("pay_prod_bal_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                 prod_id = clean_data; qty = 1
        else:
             prod_id = clean_data; qty = 1
        
        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "❌ Sản phẩm không tồn tại!", show_alert=True)
            return True

        unit_price, disc_type, _ = get_best_discount(update.effective_user.id, prod_id, p['price'])
        store_coupon_code, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
        if store_coupon_discount > 0:
            coupon_unit_price = max(0, p['price'] - store_coupon_discount)
            unit_price = min(unit_price, coupon_unit_price)
        total_price = unit_price * qty
    
        user_id = update.effective_user.id
        user_info = db_get_user(user_id)
        balance = user_info.get('balance', 0) if user_info else 0
        
        if balance < total_price:
            await safe_answer(query, "❌ Số dư không đủ!", show_alert=True)
            return True

        # FIX: Check requires_gmail TRƯỚC để bỏ qua stock check nếu manual
        requires_gmail = p.get('requires_gmail', False)
        
        if not requires_gmail:
            available_count = int(get_local_stock_available_count(p) or 0)
            if available_count < qty:
                await safe_answer(query, f"❌ Chỉ còn {available_count} sản phẩm, không đủ số lượng {qty}!", show_alert=True)
                return True
    
        if requires_gmail:
            # FLOW MỚI: Hỏi email → Báo Admin → Admin xử lý
            
            # Trừ tiền trước
            new_balance = balance - total_price
            db_update_balance(user_id, new_balance)
            
            # Lưu thông tin tạm thời & GLOBAL (Persistent)
            order_code = await generate_unique_order_code(
                prefix="MANUAL",
                length=8,
                charset=string.ascii_uppercase + string.digits,
                extra_reserved=pending_manual_orders,
            )
            
            # Save to global storage immediately
            pending_manual_orders[order_code] = {
                'order_code': order_code,
                'user_id': user_id,
                'email': None, # Chưa có email
                'product_id': prod_id,
                'product_name': p['name'],
                'quantity': qty,
                'amount': total_price,
                'status': 'awaiting_email', # Trạng thái chờ email
                'timestamp': time.time(),
                'full_name': update.effective_user.full_name,
                'coupon_code': store_coupon_code,
                'last_reminded': 0 # Track reminder
            }
            if store_coupon_code and store_coupon_code in coupons:
                coupons[store_coupon_code]['used'] = coupons[store_coupon_code].get('used', 0) + 1
            await save_data(force=True)
            clear_store_coupon_context(context)
            
            context.user_data['pending_manual_order'] = pending_manual_orders[order_code]
            context.user_data['state'] = 'awaiting_manual_email'
            
            await query.message.reply_text(
                lt(
                    user_id,
                    f"{E_SUCCESS} <b>ĐÃ TRỪ TIỀN THÀNH CÔNG</b>\n\n"
                    f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
                    f"{E_TAG} <b>Đã trừ:</b> {total_price:,} VNĐ\n"
                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Số dư còn:</b> {new_balance:,} VNĐ\n\n"
                    f"{E_GLOBE} <b>Vui lòng nhập email nhận dịch vụ:</b>\n"
                    f"<i>(Email này sẽ được dùng để setup và gửi thông tin)</i>",
                    f"{E_SUCCESS} <b>PAYMENT TAKEN FROM YOUR WALLET</b>\n\n"
                    f"{E_TAG} <b>Product:</b> {p['name']}\n"
                    f"{E_TAG} <b>Charged:</b> {total_price:,} VND\n"
                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Remaining balance:</b> {new_balance:,} VND\n\n"
                    f"{E_GLOBE} <b>Send the email address for this service:</b>\n"
                    f"<i>(We use it to set the service up and send you the details)</i>",
                    f"{E_SUCCESS} <b>已从钱包扣款</b>\n\n"
                    f"{E_TAG} <b>商品：</b>{p['name']}\n"
                    f"{E_TAG} <b>扣款：</b>{total_price:,} VND\n"
                    f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>剩余余额：</b>{new_balance:,} VND\n\n"
                    f"{E_GLOBE} <b>请输入接收服务的邮箱：</b>\n"
                    f"<i>（该邮箱用于开通服务并发送信息）</i>",
                ),
                parse_mode='HTML'
            )
            
            # Edit message và lưu message_id để xóa sau
            waiting_msg = await query.edit_message_text(
                "<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> <b>CHỜ NHẬP EMAIL...</b>",
                reply_markup=None
            )
            context.user_data['waiting_message_id'] = waiting_msg.message_id
            context.user_data['waiting_chat_id'] = waiting_msg.chat_id
            
            # Gửi thông báo cho admin rằng đang chờ email
            admin_notif = await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>ĐÃ NHẬN THANH TOÁN - ĐƠN MANUAL</b>\n"
                f"<tg-emoji emoji-id=\"5972022360025336988\">🔸</tg-emoji> Mã: {order_code}\n"
                f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> SP: {p['name']}\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> {total_price:,} VNĐ\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">⏳</tg-emoji> Đang chờ khách nhập email...",
                parse_mode='HTML'
            )
            # Lưu message_id của thông báo admin để update sau
            context.user_data['admin_waiting_message_id'] = admin_notif.message_id
            return True
        
        # FLOW CŨ: Giao hàng tự động
        items_bought = []
        actual_qty = qty
        refunded_qty = 0
        refund_amount = 0
        charged_amount = total_price
        
        # === REGULAR LOCAL STOCK FLOW ===
        stock_result = await consume_local_stock_items(
            prod_id,
            qty,
            order_state={
                "user_id": user_id,
                "product_id": prod_id,
            },
            persist_tables=(PRODUCTS_FILE,),
            notify_bot=context.bot,
            source="store_balance",
        )
        if stock_result.get("items") is None:
            await safe_answer(query, f"Het hang! Chi con {int(stock_result.get('available', 0) or 0)} san pham.", show_alert=True)
            return True

        items_bought = list(stock_result.get("items") or [])
        actual_qty = int(stock_result.get("actual_delivered") or len(items_bought))
        refunded_qty = int(stock_result.get("refunded_qty") or 0)
        unit_price = int(p.get("price", 0) or 0)
        refund_amount = refunded_qty * unit_price
        charged_amount = total_price - refund_amount
        new_balance = balance - charged_amount
        db_update_balance(user_id, new_balance, reason=f"Purchase: {p['name']} x{actual_qty} (refunded {refunded_qty} duplicates)")

    
        # === CHUNG CHO CẢ 2 FLOW (Delivery & Logging) ===
        # Log Order
        order_code = await generate_unique_order_code(
            prefix="PROD",
            length=8,
            charset=string.ascii_uppercase + string.digits,
        )
        order_data = {
            "order_code": order_code,
            "user_id": user_id,
            "email": "N/A",
            "amount": charged_amount,
            "status": "Hoàn thành",
            "type": "store_product",
            "link": "Sản phẩm khác",
            "timestamp": time.time(),
            "coupon_used": store_coupon_code or "",
            "refunded_at": 0,
            "full_name": update.effective_user.full_name,
            "username": update.effective_user.username,
            "product_name": p['name'],
            "quantity": actual_qty,
            "original_quantity": qty,
            "refunded_qty": refunded_qty,
            "refund_amount": refund_amount,
            "items": items_bought, # Save items into order history too
        }
        order_data["delivery_method"] = "pending"
        db_add_order(order_data)
        if store_coupon_code and store_coupon_code in coupons:
            coupons[store_coupon_code]['used'] = coupons[store_coupon_code].get('used', 0) + 1
        clear_store_coupon_context(context)
        total_discount = (p['price'] * qty) - total_price
        if total_discount > 0:
            record_promo_cost(total_discount, 'order_discount')
        await save_data() # Save orders

        # Delivery Message - Luôn gửi file .txt
        delivery_notice = (
            f"{E_TIP} <b>Hệ thống đang gửi thông tin tài khoản ngay sau tin nhắn này...</b>"
            if items_bought
            else f"{E_TIP} <b>Đơn này đang chờ giao hàng. Admin sẽ hỗ trợ sớm nhất.</b>"
        )
        refund_notice = ""
        if refunded_qty > 0:
            refund_notice = f"\n<tg-emoji emoji-id=\"5863724849851011383\">💸</tg-emoji> <b>Thiếu sản phẩm:</b> Không tính tiền {refunded_qty} sản phẩm ({refund_amount:,} VNĐ)\n"
        info_msg = (
            f"{E_SUCCESS} <b>MUA HÀNG THÀNH CÔNG!</b>\n\n"
            f"{E_TAG} <b>Sản phẩm:</b> {p['name']}\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">📦</tg-emoji> <b>Số lượng:</b> {actual_qty}"
            f"{' (Thiếu ' + str(refunded_qty) + ' sản phẩm)' if refunded_qty > 0 else ''}\n"
            f"{E_LOADING} <b>Thời hạn:</b> {p.get('duration', 'N/A')}\n"
            f"<tg-emoji emoji-id=\"5197288647275071607\">🛡️</tg-emoji> <b>Bảo hành:</b> {p.get('warranty', 'Không')}\n"
            f"{E_TAG} <b>Thanh toán thực tế:</b> {charged_amount:,} VNĐ\n"
            f"<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> <b>Số dư còn lại:</b> {new_balance:,} VNĐ"
            f"{refund_notice}\n\n"
            f"{delivery_notice}"
        )
        
        await query.message.reply_text(info_msg, parse_mode='HTML')
        delivery_result = {"delivered": False, "method": "failed"}

        if items_bought:
            purchase_date = datetime.fromtimestamp(time.time()).strftime('%d/%m/%Y %H:%M:%S')
            product_description_txt = format_product_description_for_txt(p)
            file_content = "="*60 + "\n"
            file_content += "           THÔNG TIN ĐƠN HÀNG\n"
            file_content += "="*60 + "\n\n"
            file_content += f"Mã đơn hàng    : {order_code}\n"
            file_content += f"Ngày mua       : {purchase_date}\n"
            file_content += f"Sản phẩm       : {p['name']}\n"
            file_content += f"Số lượng       : {actual_qty}\n"
            if refunded_qty > 0:
                file_content += f"Thiếu sản phẩm : {refunded_qty}\n"
                file_content += f"Không tính tiền: {refund_amount:,} VND\n"
            file_content += f"Thanh toán     : {charged_amount:,} VND\n"
            if product_description_txt:
                file_content += f"\nMô tả sản phẩm:\n{product_description_txt}\n\n"
            file_content += f"Thời hạn       : {p.get('duration', 'N/A')}\n"
            file_content += f"Bảo hành       : {p.get('warranty', 'Không')}\n"
            file_content += "\n" + "="*60 + "\n"
            file_content += "           DANH SÁCH TÀI KHOẢN\n"
            file_content += "="*60 + "\n\n"
            for idx_f, item_f in enumerate(items_bought, 1):
                file_content += f"Tài khoản {idx_f}:\n{item_f}\n\n"
            file_content += "Cảm ơn quý khách đã mua hàng. Chúc quý khách sử dụng dịch vụ vui vẻ!\n"
            file_content += "\n" + "="*60 + "\n"
            
            delivery_result = await deliver_items_as_txt(
                context,
                user_id,
                order_code,
                items_bought,
                file_content=file_content,
                file_prefix="DonHang",
                caption_html=f"<tg-emoji emoji-id=\"5373251851074415873\">📋</tg-emoji> <b>File tài khoản</b>\nMã đơn: <code>{order_code}</code>",
                reply_markup=create_success_menu(user_id=user_id),
            )
            order_data["delivery_method"] = delivery_result.get("method", "failed")
            await save_data(force=True, tables=[HISTORY_FILE])
            if not delivery_result.get("delivered"):
                order_data["status"] = "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Chờ gửi thủ công (Store Balance)"
                await safe_send_admin(
                    context.bot,
                    f"{E_SOS} <b>DELIVERY FAILED (STORE BALANCE)</b>\n"
                    f"{E_ID} Đơn: <code>{order_code}</code>\n"
                    f"{E_USER} User: <code>{user_id}</code>\n"
                    f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                    f"{E_STAT} Fallback gửi: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                    f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                )
                await safe_send_message(
                    context,
                    user_id,
                    f"❌ Có lỗi khi gửi file tài khoản cho đơn <code>{order_code}</code>.\n"
                    "Admin đã nhận cảnh báo và sẽ gửi thủ công sớm nhất.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(user_id=user_id),
                )
                await save_data(force=True, tables=[HISTORY_FILE])
        else:
            await query.message.reply_text(lt(user_id, "<i>Liên hệ Admin để nhận hàng</i>", "<i>Contact the admin to receive your order</i>", "<i>请联系管理员领取订单</i>"), parse_mode='HTML')
            await safe_send_admin(
                context.bot,
                f"{E_TIP} <b>ĐƠN CHỜ GIAO TỪ NGUỒN</b>\n"
                f"{E_ID} Đơn: <code>{order_code}</code>\n"
                f"{E_USER} User: <code>{user_id}</code>\n"
                f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                f"{E_STAT} Trạng thái: {html.escape(order_data.get('status', 'pending'))}",
            )
        
        await query.edit_message_text(
            lt(
                user_id,
                f"{E_SUCCESS} <b>ĐÃ THANH TOÁN THÀNH CÔNG</b>\n\nCảm ơn bạn đã mua hàng.",
                f"{E_SUCCESS} <b>PAYMENT COMPLETED</b>\n\nThank you for your purchase.",
                f"{E_SUCCESS} <b>支付成功</b>\n\n感谢您的购买。",
            ),
            reply_markup=create_back_button_menu(user_id=user_id)
        )
        
        # Post-purchase follow-ups are delayed so they do not visually drown out the delivery file.
        if delivery_result.get("delivered"):
            await send_live_order_notification(
                context,
                update.effective_user.full_name,
                total_price,
                product_name=p['name'],
                quantity=qty,
                order_code=order_code,
            )
            await notify_admin_store_order(
                context,
                order_code=order_code,
                user_id=user_id,
                full_name=update.effective_user.full_name,
                username=update.effective_user.username,
                product_name=p['name'],
                quantity=qty,
                amount=total_price,
                payment_method="balance",
                items=items_bought,
                delivery_method=delivery_result.get("method", "failed"),
            )
            create_background_task(send_post_purchase_followups(context, user_id, prod_id))
        
        return True
        
    elif data.startswith("store_coupon_"):
        clean_data = data.replace("store_coupon_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                prod_id = clean_data; qty = 1
        else:
            prod_id = clean_data; qty = 1
        context.user_data['store_coupon_prod_id'] = prod_id
        context.user_data['store_coupon_qty'] = qty
        context.user_data['state'] = 'awaiting_store_coupon'
        await query.edit_message_text(
            lt(
                query.from_user.id,
                "🎫 <b>NHẬP MÃ GIẢM GIÁ</b>\n\n"
                "Vui lòng nhập mã coupon của bạn:\n"
                "<i>(Gõ /cancel để hủy)</i>",
                "🎫 <b>ENTER A DISCOUNT CODE</b>\n\n"
                "Send your coupon code:\n"
                "<i>(Type /cancel to abort)</i>",
                "🎫 <b>输入优惠码</b>\n\n"
                "请发送您的优惠码：\n"
                "<i>（输入 /cancel 取消）</i>",
            ),
            parse_mode=ParseMode.HTML
        )
        return True

    elif data.startswith("pay_prod_combo_"):
        clean_data = data.replace("pay_prod_combo_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                prod_id = clean_data; qty = 1
        else:
            prod_id = clean_data; qty = 1

        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "❌ Sản phẩm không tồn tại!", show_alert=True)
            return True
        user_id = update.effective_user.id
        pending_code, pending_detail = await get_user_pending_order(user_id)
        if pending_code:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn {pending_code} chưa hoàn thành! Vui lòng hoàn tất hoặc hủy đơn cũ trước.", show_alert=True)
            return True
        user_info = db_get_user(user_id)
        balance = user_info.get('balance', 0) if user_info else 0

        if balance <= 0:
            await safe_answer(query, "❌ Số dư ví bằng 0!", show_alert=True)
            return True

        unit_price, _, _ = get_best_discount(user_id, prod_id, p['price'])
        _, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
        if store_coupon_discount > 0:
            coupon_unit_price = max(0, p['price'] - store_coupon_discount)
            unit_price = min(unit_price, coupon_unit_price)
        total_price = unit_price * qty

        if balance >= total_price:
            await safe_answer(query, "<tg-emoji emoji-id=\"5213403875670765022\">💳</tg-emoji> Số dư đủ! Hãy chọn thanh toán bằng số dư.", show_alert=True)
            return True

        balance_used = balance
        _qr_amount = total_price - balance_used

        requires_gmail = p.get('requires_gmail', False)
        if not requires_gmail:
            lock = await get_product_lock(prod_id)
            async with lock:
                available_count = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                if available_count < qty:
                    await safe_answer(query, "❌ Số lượng yêu cầu vượt quá tồn kho!", show_alert=True)
                    return True
        db_update_balance(user_id, 0, reason=f"Combo payment: -{balance_used:,} for {prod_id}")

        qr_sent = await generate_product_payment_qr(update, context, prod_id, qty, balance_used=balance_used)
        if qr_sent is False:
            return True
        try:
            await query.delete_message()
        except BadRequest:
            pass
        return True

    elif data.startswith("pay_prod_usdt_trc20_"):
        clean_data = data.replace("pay_prod_usdt_trc20_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                 prod_id = clean_data; qty = 1
        else:
             prod_id = clean_data; qty = 1

        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "❌ Sản phẩm không tồn tại!", show_alert=True)
            return True
        from app.handlers.payment_generation import generate_product_payment_usdt_trc20
        # Delete old message to avoid duplicate buttons
        try:
            await query.delete_message()
        except Exception:
            pass
        await generate_product_payment_usdt_trc20(update, context, prod_id, qty)
        return True

    elif data.startswith("pay_prod_binance_"):
        await safe_answer(
            query,
            "Binance Pay đã được thay thế bằng USDT. Vui lòng chọn USDT (Binance ID / BEP20).",
            show_alert=True,
        )
        return True

    elif data.startswith("pay_prod_qr_"):
        clean_data = data.replace("pay_prod_qr_", "")
        if "_" in clean_data:
            prod_id, qty_str = clean_data.rsplit("_", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                 prod_id = clean_data; qty = 1
        else:
             prod_id = clean_data; qty = 1

        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "❌ Sản phẩm không tồn tại!", show_alert=True)
            return True
        pending_code, pending_detail = await get_user_pending_order(update.effective_user.id)
        if pending_code:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Bạn đang có đơn {pending_code} chưa hoàn thành! Vui lòng hoàn tất hoặc hủy đơn cũ trước.", show_alert=True)
            return True

        requires_gmail = p.get('requires_gmail', False)
        
        if not requires_gmail:
            # Auto product - phải có stock với lock protection
            lock = await get_product_lock(prod_id)
            async with lock:
                available_count = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                if available_count < qty:
                    await safe_answer(query, "❌ Số lượng yêu cầu vượt quá tồn kho!", show_alert=True)
                    return True
                # Stock check passed - proceed to create QR (stock will be reserved in pending_orders)
        else:
            # Manual product - check pending limit
            pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
            max_pending = p.get('max_pending_orders', 10)
            
            if pending_count >= max_pending:
                await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Admin đang bận ({pending_count}/{max_pending})!", show_alert=True)
                return True
             
        qr_sent = await generate_product_payment_qr(update, context, prod_id, qty)
        if qr_sent is False:
            return True
        # Clean up the previous message if needed or let generate_product_payment_qr handle it
        try:
            await query.delete_message()
        except BadRequest:
            pass
        return True
    
    return False


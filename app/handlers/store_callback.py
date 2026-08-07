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
        "vi": {"choose_qty": "CHá»ŒN Sá» LÆ¯á»¢NG MUá»N MUA", "product": "Sáº£n pháº©m", "unit_price": "ÄÆ¡n giÃ¡", "stock": "Tá»“n kho kháº£ dá»¥ng", "quantity": "Sá»‘ lÆ°á»£ng", "enter_qty": "Nháº­p sá»‘ lÆ°á»£ng", "back": "Quay láº¡i", "confirm": "XÃC NHáº¬N MUA HÃ€NG", "total": "Tá»•ng tiá»n", "choose_payment": "Vui lÃ²ng chá»n phÆ°Æ¡ng thá»©c thanh toÃ¡n", "balance": "Sá»‘ dÆ°", "insufficient": "KhÃ´ng Ä‘á»§", "bank": "Chuyá»ƒn khoáº£n (QR)", "coupon": "Nháº­p mÃ£ giáº£m giÃ¡", "use_combo": "DÃ¹ng {balance:,}Ä‘ + QR {remaining:,}Ä‘", "out": "Sáº£n pháº©m hiá»‡n Ä‘ang háº¿t hÃ ng!", "missing": "Sáº£n pháº©m khÃ´ng tá»“n táº¡i!"},
        "en": {"choose_qty": "CHOOSE QUANTITY", "product": "Product", "unit_price": "Unit price", "stock": "Available stock", "quantity": "Quantity", "enter_qty": "Enter quantity", "back": "Back", "confirm": "CONFIRM PURCHASE", "total": "Total", "choose_payment": "Choose a payment method", "balance": "Balance", "insufficient": "Insufficient", "bank": "Bank transfer (QR)", "coupon": "Enter coupon", "use_combo": "Use {balance:,}Ä‘ + QR {remaining:,}Ä‘", "out": "This product is out of stock!", "missing": "Product not found!"},
        "zh": {"choose_qty": "é€‰æ‹©è´­ä¹°æ•°é‡", "product": "å•†å“", "unit_price": "å•ä»·", "stock": "å¯ç”¨åº“å­˜", "quantity": "æ•°é‡", "enter_qty": "è¾“å…¥æ•°é‡", "back": "è¿”å›ž", "confirm": "ç¡®è®¤è´­ä¹°", "total": "æ€»è®¡", "choose_payment": "è¯·é€‰æ‹©ä»˜æ¬¾æ–¹å¼", "balance": "ä½™é¢", "insufficient": "ä½™é¢ä¸è¶³", "bank": "é“¶è¡Œè½¬è´¦ï¼ˆQRï¼‰", "coupon": "è¾“å…¥ä¼˜æƒ ç ", "use_combo": "ä½¿ç”¨ {balance:,}Ä‘ + QR {remaining:,}Ä‘", "out": "è¯¥å•†å“å·²ç¼ºè´§ï¼", "missing": "å•†å“ä¸å­˜åœ¨ï¼"},
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
    trimmed = _telegram_trim_utf16(text, limit - 1).rstrip() + "â€¦"
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
    curr = "Ä‘" if lang == "vi" else " VND"

    def _fmt_price(price_vnd: int) -> str:
        if not price_vnd: return "0Ä‘" if lang == "vi" else "0 USDT"
        if lang == "vi": return f"{price_vnd:,}Ä‘"
        try:
            rate = float(globals().get("_cached_live_usdt_rate") or USDT_TRC20_RATE_VND_PER_USDT)
            return f"{price_vnd / rate:.2f} USDT"
        except (TypeError, ValueError, ZeroDivisionError):
            return f"{price_vnd:,} VND"


    labels = {
        "vi": {
            "description": "MÃ´ táº£", "price": "GiÃ¡", "duration": "Thá»i háº¡n", "warranty": "Báº£o hÃ nh",
            "auto": "Giao tá»± Ä‘á»™ng", "status": "Tráº¡ng thÃ¡i", "available": "CÃ²n {count} sáº£n pháº©m",
            "out": "Háº¿t hÃ ng", "how_email": "Thanh toÃ¡n â†’ nháº­p email â†’ admin xá»­ lÃ½ â†’ nháº­n hÃ ng.",
            "how_auto": "Thanh toÃ¡n â†’ nháº­n tÃ i khoáº£n ngay trÃªn Telegram.", "how": "CÃ¡ch mua",
            "buy": "Mua ngay", "busy": "Admin Ä‘ang báº­n", "notify": "ThÃ´ng bÃ¡o khi cÃ³ hÃ ng", "back": "Quay láº¡i Danh Má»¥c",
            "manual": "Dá»‹ch vá»¥ xá»­ lÃ½ thá»§ cÃ´ng", "manual_avail": "CÃ²n {count} lÆ°á»£t Ä‘áº·t",
            "manual_full": "Táº¡m ngá»«ng nháº­n Ä‘Æ¡n", "suspended": "Táº¡m ngá»«ng bÃ¡n"
        },
        "en": {
            "description": "Description", "price": "Price", "duration": "Duration", "warranty": "Warranty",
            "auto": "Automatic delivery", "status": "Status", "available": "{count} products available",
            "out": "Out of stock", "how_email": "Pay â†’ enter email â†’ admin processes â†’ receive your order.",
            "how_auto": "Pay â†’ receive the account instantly on Telegram.", "how": "How to buy",
            "buy": "Buy now", "busy": "Admin is busy", "notify": "Notify me when available", "back": "Back to Categories",
            "manual": "Manual processing service", "manual_avail": "{count} slots remaining",
            "manual_full": "Temporarily stopped taking orders", "suspended": "Suspended"
        },
        "zh": {
            "description": "æè¿°", "price": "ä»·æ ¼", "duration": "æœ‰æ•ˆæœŸ", "warranty": "ä¿ä¿®",
            "auto": "è‡ªåŠ¨å‘è´§", "status": "çŠ¶æ€", "available": "å‰©ä½™ {count} ä»¶",
            "out": "ç¼ºè´§", "how_email": "ä»˜æ¬¾ â†’ è¾“å…¥é‚®ç®± â†’ ç®¡ç†å‘˜å¤„ç† â†’ æ”¶è´§ã€‚",
            "how_auto": "ä»˜æ¬¾ â†’ ç«‹å³åœ¨ Telegram æŽ¥æ”¶è´¦å·ã€‚", "how": "è´­ä¹°æ–¹å¼",
            "buy": "ç«‹å³è´­ä¹°", "busy": "ç®¡ç†å‘˜å¿™ç¢Œä¸­", "notify": "åˆ°è´§é€šçŸ¥", "back": "è¿”å›žåˆ†ç±»",
            "manual": "äººå·¥å¤„ç†æœåŠ¡", "manual_avail": "å‰©ä½™ {count} ä¸ªåé¢",
            "manual_full": "æš‚åœæŽ¥å•", "suspended": "æš‚åœé”€å”®"
        },
    }.get(lang, {})

    p = products.get(prod_id)
    if isinstance(p, dict):
        p["_product_id"] = str(prod_id)
    if not p or not _ctt_is_catalog_visible(p):
        await safe_answer(query, "Sáº£n pháº©m khÃ´ng tá»“n táº¡i", show_alert=True)
        return True

    requires_gmail = p.get('requires_gmail', False)
    is_ctt_product = _is_ctt_store_product(p)
    
    raw_name = str(p.get("name") or prod_id)
    get_effective_category = globals().get("get_effective_store_category")
    effective_category = get_effective_category(p) if callable(get_effective_category) else (p.get("store_category") or get_product_category(raw_name))
    product_icon_id = get_store_icon_id(raw_name, get_store_icon_id(effective_category, "5854908544712707500"))
    product_icon_fallback = {
        "Netflix": "ðŸŽ¬",
        "YouTube Premium": "â–¶ï¸",
        "Spotify & Music": "ðŸŽµ",
        "Google Drive & One": "â˜ï¸",
        "CapCut & Edit Video": "ðŸŽžï¸",
        "Adobe Creative Cloud": "ðŸŽ¨",
        "TikTok": "ðŸŽµ",
        "Proxy": "ðŸ›¡ï¸",
        "AI Tools (GPT, Copilot...)": "ðŸ¤–",
    }.get(str(effective_category or ""), "ðŸ“¦")
    product_icon_markup = f'<tg-emoji emoji-id="{product_icon_id}">{product_icon_fallback}</tg-emoji>'
    can_buy = False
    display_price_text = _fmt_price(p.get("price", 0) or 0)
    discount_line = _get_discount_display_line(query.from_user.id, prod_id, p["price"])

    if is_ctt_product:
        minimum_quantity = _ctt_get_package_quantity(p)
        maximum_quantity = int(p.get("ctt_max_quantity", 0) or 0)
        quantity_error = _ctt_validate_purchase_quantity(p, minimum_quantity)
        required_inputs = _ctt_required_input_fields(p)
        input_labels = {
            "link": "Link livestream TikTok" if "tiktok" in str(p.get("name") or "").lower() else "Link sáº£n pháº©m",
            "comments": "Ná»™i dung bÃ¬nh luáº­n",
            "comment": "Ná»™i dung bÃ¬nh luáº­n",
            "username": "Username",
            "user": "Username",
            "uid": "UID",
            "phone": "Sá»‘ Ä‘iá»‡n thoáº¡i",
            "email": "Email",
        }
        input_text = ", ".join(input_labels.get(str(field).lower(), str(field)) for field in required_inputs) if required_inputs else "Link sáº£n pháº©m"
        pricing_preview = _get_ctt_store_pricing_preview(query.from_user.id, context, prod_id, p, minimum_quantity)
        base_unit_text = _ctt_format_vnd_decimal(pricing_preview.get("base_unit_price", 0))
        effective_unit_text = _ctt_format_vnd_decimal(pricing_preview.get("chosen_unit_price", 0))
        display_price_text = f'~{_fmt_price(float(pricing_preview.get("base_unit_price", 0) or 0))} / 1 Ä‘Æ¡n vá»‹'
        if pricing_preview.get("discount_percent", 0) > 0:
            discount_line = (
                f'\n{E_TAG} <b>Giáº£m {int(pricing_preview.get("discount_percent", 0) or 0)}%:</b> '
                f'<s>{base_unit_text}Ä‘</s> â†’ <b>{effective_unit_text}Ä‘</b> / Ä‘Æ¡n vá»‹\n'
            )
        elif pricing_preview.get("coupon_unit_discount", 0) > 0:
            discount_line = (
                f'\n{E_TAG} <b>Coupon:</b> '
                f'<s>{base_unit_text}Ä‘</s> â†’ <b>{effective_unit_text}Ä‘</b> / Ä‘Æ¡n vá»‹\n'
            )
        else:
            discount_line = ""

        if not SOCIAL_SOURCE_API_KEY:
            stock_info = (
                f'{E_LOADING} Loáº¡i: Dá»‹ch vá»¥ máº¡ng xÃ£ há»™i\n'
                f'{E_LIMIT} Tráº¡ng thÃ¡i: Táº¡m ngá»«ng bÃ¡n'
            )
            can_buy = False
        elif quantity_error:
            stock_info = (
                f'{E_LOADING} Loáº¡i: Dá»‹ch vá»¥ máº¡ng xÃ£ há»™i\n'
                f'{E_LIMIT} Tráº¡ng thÃ¡i: Táº¡m ngá»«ng bÃ¡n\n'
                f'{E_LIMIT} {html.escape(quantity_error)}'
            )
            can_buy = False
        else:
            max_text = f"{maximum_quantity:,}" if maximum_quantity > 0 else "KhÃ´ng giá»›i háº¡n"
            stock_info = (
                f'{E_LOADING} Loáº¡i: Dá»‹ch vá»¥ máº¡ng xÃ£ há»™i\n'
                f'{E_SUCCESS} Tráº¡ng thÃ¡i: Sáºµn sÃ ng\n'
                f'{E_STAT} Mua tá»‘i thiá»ƒu: {minimum_quantity:,} Ä‘Æ¡n vá»‹\n'
                f'{E_STAT} Mua tá»‘i Ä‘a: {max_text}\n'
                f'{E_STAT} Cáº§n nháº­p: {html.escape(input_text)}'
            )
            can_buy = True
    elif requires_gmail:
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
        if p.get('is_supplier_source_resell'):
            supplier_source_stock = _get_supplier_source_stock_count(p)

            if _is_supplier_source_purchase_blocked(p):
                block_reason = html.escape(str(p.get("supplier_source_purchase_blocked_reason") or ("Nguá»“n Ä‘ang táº¡m ngá»«ng bÃ¡n" if lang == "vi" else "Source suspended")))
                stock_info = f'{E_ANDROID} {labels["auto"]}\n{E_LIMIT} {labels["status"]}: {labels["suspended"]}\n<i>{block_reason}</i>'
                can_buy = False
            elif supplier_source_stock > 0:
                stock_info = f'{E_ANDROID} {labels["auto"]}\n{E_SUCCESS} {labels["status"]}: {labels["available"].format(count=supplier_source_stock)}'
                can_buy = True
            else:
                stock_info = f'{E_ANDROID} {labels["auto"]}\n{E_ERROR} {labels["status"]}: {labels["out"]}'
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
    
    default_duration = "KhÃ´ng giá»›i háº¡n" if lang == "vi" else ("Unlimited" if lang == "en" else "æ— é™åˆ¶")
    default_warranty = "KhÃ´ng" if lang == "vi" else ("No" if lang == "en" else "æ— ")
    
    def_dur_val = p.get("duration", default_duration)
    if def_dur_val == "Theo thÃ´ng tin sáº£n pháº©m":
        def_dur_val = "Theo thÃ´ng tin sáº£n pháº©m" if lang == "vi" else ("See product info" if lang == "en" else "æŸ¥çœ‹äº§å“ä¿¡æ¯")
    
    def_war_val = p.get("warranty", default_warranty)
    if def_war_val == "Báº£o hÃ nh theo quy Ä‘á»‹nh":
        def_war_val = "Báº£o hÃ nh theo quy Ä‘á»‹nh" if lang == "vi" else ("Standard warranty" if lang == "en" else "æ ‡å‡†ä¿ä¿®")
        
    duration_text = html.escape(p.get(f"duration_{lang}") or def_dur_val)
    warranty_text = html.escape(p.get(f"warranty_{lang}") or def_war_val)

    if is_ctt_product:
        raw_search = raw_name.lower()
        if "tiktok" in raw_search or "tik tok" in raw_search:
            platform_text = "TikTok"
        elif "facebook" in raw_search or raw_search.startswith("fb ") or " fb " in raw_search:
            platform_text = "Facebook"
        elif "instagram" in raw_search or " ig " in raw_search:
            platform_text = "Instagram"
        elif "youtube" in raw_search:
            platform_text = "YouTube"
        elif "telegram" in raw_search:
            platform_text = "Telegram"
        else:
            platform_text = html.escape(str(p.get("store_category") or "Social"))
        if "livestream" in raw_search or "live stream" in raw_search or "live" in raw_search:
            service_text = "TÄƒng tÆ°Æ¡ng tÃ¡c livestream"
        elif "like" in raw_search and ("share" in raw_search or "comment" in raw_search):
            service_text = "TÄƒng tÆ°Æ¡ng tÃ¡c"
        elif "like" in raw_search:
            service_text = "TÄƒng lÆ°á»£t thÃ­ch"
        elif "follow" in raw_search or "follower" in raw_search:
            service_text = "TÄƒng ngÆ°á»i theo dÃµi"
        elif "comment" in raw_search:
            service_text = "TÄƒng bÃ¬nh luáº­n"
        elif "share" in raw_search:
            service_text = "TÄƒng chia sáº»"
        elif "view" in raw_search:
            service_text = "TÄƒng lÆ°á»£t xem"
        else:
            service_text = "Dá»‹ch vá»¥ máº¡ng xÃ£ há»™i"

        included_parts = []
        if "like" in raw_search:
            included_parts.append("Likes")
        if "share" in raw_search:
            included_parts.append("Shares")
        if "comment" in raw_search:
            included_parts.append("Comments")
        included_text = " + ".join(included_parts) if included_parts else service_text
        max_text = f"{maximum_quantity:,}" if maximum_quantity > 0 else "KhÃ´ng giá»›i háº¡n theo há»‡ thá»‘ng"
        refill_text = "CÃ³ báº£o hÃ nh" if bool(p.get("ctt_refill")) else "KhÃ´ng báº£o hÃ nh / KhÃ´ng bÃ¹ tá»¥t"

        msg = (
            f'{E_TAG} <b>{html.escape(raw_name)}</b>\n'
            f'<blockquote expandable><b>MÃ´ táº£:</b>\n\n'
            f'{E_LOADING} <b>ThÃ´ng tin dá»‹ch vá»¥</b>\n'
            f'{E_TAG} Ná»n táº£ng: {platform_text}\n'
            f'{E_TAG} Dá»‹ch vá»¥: {service_text}\n'
            f'{E_TAG} Bao gá»“m: {html.escape(included_text)}\n'
            f'{E_STAT} Tá»‘i thiá»ƒu: {minimum_quantity:,}\n'
            f'{E_STAT} Tá»‘i Ä‘a: {max_text}\n'
            f'{E_TAG} Nháº­p: {html.escape(input_text)}\n'
            f'{E_SHIELD} Báº£o hÃ nh: {refill_text}\n\n'
            f'<tg-emoji emoji-id="5278467510604160626">ðŸ’°</tg-emoji> GiÃ¡: <b>{display_price_text}</b>\n'
            f'{E_TAG} GÃ³i tá»‘i thiá»ƒu: <b>{minimum_quantity:,} Ä‘Æ¡n vá»‹</b>\n'
            f'{E_SUCCESS} Tá»‘c Ä‘á»™: Tá»± Ä‘á»™ng xá»­ lÃ½ sau khi thanh toÃ¡n\n\n'
            f'{E_LOADING} <b>Quy trÃ¬nh:</b>\n'
            f'Nháº­p sá»‘ lÆ°á»£ng â†’ DÃ¡n link cáº§n cháº¡y â†’ Thanh toÃ¡n â†’ Bot táº¡o Ä‘Æ¡n tá»± Ä‘á»™ng</blockquote>\n'
        )
    else:
        # labels already built at the top

        msg = (
            f'{E_TAG} <b>{html.escape(localized_name)}</b>\n'
            f'<blockquote expandable>ðŸ“ <b>{labels["description"]}:</b>\n{desc_text}</blockquote>\n'
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
            btns.append([_btn(detail_labels.get("busy", "Admin Ä‘ang báº­n"), icon_id="5197288647275071607", callback_data="ignore", style="danger")])
        else:
            btns.append([_btn(detail_labels.get("out", "Háº¿t hÃ ng"), icon_id="5273914604752216432", callback_data="ignore", style="danger")])
            if not is_ctt_product:
                btns.append([_btn(detail_labels.get("notify", "ThÃ´ng bÃ¡o khi cÃ³ hÃ ng"), icon_id="5447364299200678034", callback_data=f"waitlist_{prod_id}")])

    from app.core.emoji_runtime import upgrade_text_to_premium_emoji

    msg = upgrade_text_to_premium_emoji(
        msg.replace(E_TAG, product_icon_markup)
        .replace(E_LOADING, '<tg-emoji emoji-id="5373251851074415873">ðŸ“„</tg-emoji>')
        .replace(E_LIMIT, '<tg-emoji emoji-id="5447644880824181073">âš ï¸</tg-emoji>')
        .replace(E_ERROR, '<tg-emoji emoji-id="5273914604752216432">âŒ</tg-emoji>')
    )

    get_effective_category = globals().get("get_effective_store_category")
    cat = get_effective_category(p) if callable(get_effective_category) else (p.get('store_category') or get_product_category(p['name']))
    btns.append([_btn(back_button_text or detail_labels.get("back", "Quay láº¡i Danh Má»¥c"), icon_id="6206032691075223572", callback_data=back_callback_data or f"view_cat_{cat}")])
    reply_markup = InlineKeyboardMarkup(btns)
    await _show_store_product_panel(query, context, p, msg, reply_markup)
    return True


def _is_supplier_source_purchase_blocked(product) -> bool:
    return bool(isinstance(product, dict) and product.get("supplier_source_purchase_blocked"))


def _get_supplier_source_stock_count(product) -> int:
    if _is_supplier_source_purchase_blocked(product):
        return 0
    try:
        return int((product or {}).get('supplier_source_stock', 0) or 0)
    except (TypeError, ValueError, KeyError, AttributeError):
        return 0


def _is_ctt_store_product(product) -> bool:
    return _ctt_is_service_product(product)


def _get_store_effective_unit_price(user_id: int, context: ContextTypes.DEFAULT_TYPE, prod_id: str, product: dict, qty: int) -> int:
    unit_price, _discount_type, _discount_info = get_best_discount(user_id, prod_id, product['price'])
    store_coupon_discount = 0
    if getattr(context, "user_data", None) is not None:
        _store_coupon_code, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
    if store_coupon_discount > 0:
        coupon_unit_price = max(0, product['price'] - store_coupon_discount)
        unit_price = min(unit_price, coupon_unit_price)
    return int(unit_price or 0)


def _get_ctt_store_pricing_preview(user_id: int, context: ContextTypes.DEFAULT_TYPE, prod_id: str, product: dict, qty: int = 1) -> dict:
    from decimal import Decimal

    base_unit = _ctt_get_base_unit_price_decimal(product)
    base_total = _ctt_calculate_total_price(product, qty)
    scenarios = [
        {
            "kind": "base",
            "unit_price": base_unit,
            "total_price": base_total,
            "discount_type": None,
            "discount_percent": 0,
            "coupon_unit_discount": 0,
        }
    ]

    _best_price, discount_type, discount_info = get_best_discount(user_id, prod_id, int(product.get("price", 0) or 0))
    discount_percent = 0
    if isinstance(discount_info, dict):
        try:
            discount_percent = int(discount_info.get("discount_percent", 0) or 0)
        except (TypeError, ValueError, KeyError, AttributeError):
            discount_percent = 0
    if discount_percent > 0:
        scenarios.append(
            {
                "kind": "discount",
                "unit_price": base_unit * (Decimal("100") - Decimal(discount_percent)) / Decimal("100"),
                "total_price": _ctt_calculate_total_price(product, qty, discount_percent=discount_percent),
                "discount_type": discount_type,
                "discount_percent": discount_percent,
                "coupon_unit_discount": 0,
            }
        )

    store_coupon_discount = 0
    if getattr(context, "user_data", None) is not None:
        _store_coupon_code, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
    if store_coupon_discount > 0:
        scenarios.append(
            {
                "kind": "coupon",
                "unit_price": max(Decimal("0"), base_unit - Decimal(str(store_coupon_discount))),
                "total_price": _ctt_calculate_total_price(product, qty, coupon_unit_discount=store_coupon_discount),
                "discount_type": "coupon",
                "discount_percent": 0,
                "coupon_unit_discount": int(store_coupon_discount or 0),
            }
        )

    chosen = min(scenarios, key=lambda item: int(item.get("total_price", 0) or 0))
    return {
        "base_unit_price": base_unit,
        "base_total_price": base_total,
        "chosen_unit_price": chosen.get("unit_price", base_unit),
        "chosen_total_price": int(chosen.get("total_price", base_total) or 0),
        "discount_type": chosen.get("discount_type"),
        "discount_percent": int(chosen.get("discount_percent", 0) or 0),
        "coupon_unit_discount": int(chosen.get("coupon_unit_discount", 0) or 0),
    }


def _get_ctt_store_total_price(user_id: int, context: ContextTypes.DEFAULT_TYPE, prod_id: str, product: dict, qty: int) -> int:
    preview = _get_ctt_store_pricing_preview(user_id, context, prod_id, product, qty)
    return int(preview.get("chosen_total_price", 0) or 0)


async def _begin_ctt_checkout_collection(query, context: ContextTypes.DEFAULT_TYPE, prod_id: str, qty: int, payment_flow: str, *, balance_used: int = 0):
    product = products.get(prod_id)
    if not _is_ctt_store_product(product):
        await safe_answer(query, "San pham nay khong phai dich vu social.", show_alert=True)
        return True

    quantity_error = _ctt_validate_purchase_quantity(product, qty)
    if quantity_error:
        await safe_answer(query, quantity_error, show_alert=True)
        return True

    fields = _ctt_required_input_fields(product)
    first_field = fields[0]
    context.user_data['pending_ctt_checkout'] = {
        "prod_id": prod_id,
        "qty": int(qty or 1),
        "payment_flow": str(payment_flow or "balance"),
        "balance_used": int(balance_used or 0),
        "fields": list(fields),
        "collected_inputs": {},
    }
    context.user_data['pending_ctt_payment_balance_used'] = int(balance_used or 0)
    context.user_data['state'] = f'awaiting_ctt_{first_field}'

    await _show_store_panel(
        query,
        context,
        _ctt_build_checkout_prompt(product, int(qty or 1), first_field),
        InlineKeyboardMarkup([[_btn("Huy", icon_id="5273914604752216432", callback_data=f"buy_prod_confirm_{prod_id}_{qty}", style="danger")]]),
    )
    return True


async def _complete_ctt_balance_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, draft: dict):
    prod_id = str((draft or {}).get("prod_id") or "").strip()
    qty = int((draft or {}).get("qty", 1) or 1)
    product = products.get(prod_id)
    if not _is_ctt_store_product(product):
        await update.message.reply_text("San pham social khong con ton tai. Vui long thu lai.")
        return

    user = update.effective_user
    user_info = db_get_user(user.id)
    balance = int((user_info or {}).get('balance', 0) or 0)
    total_price = _get_ctt_store_total_price(user.id, context, prod_id, product, qty)
    if balance < total_price:
        await update.message.reply_text("So du hien tai khong du de tao don social nay.")
        return

    collected_inputs = dict((draft or {}).get("collected_inputs") or {})
    supplier_result = await ctt_submit_local_service_order(product, qty, collected_inputs)
    if not supplier_result.get("success"):
        await update.message.reply_text(
            f"Khong the tao don social tu nguon.\nLoi: <code>{html.escape(str(supplier_result.get('error') or 'unknown_error'))}</code>",
            parse_mode=ParseMode.HTML,
        )
        await safe_send_admin(
            context.bot,
            f"{E_SOS} <b>SOCIAL_SOURCE BALANCE ORDER FAILED</b>\n"
            f"{E_USER} User: <code>{user.id}</code>\n"
            f"{E_TAG} SP: {html.escape(str(product.get('name') or prod_id))} x{qty}\n"
            f"{E_ERROR} Loi: <code>{html.escape(str(supplier_result.get('error') or 'unknown_error'))}</code>",
        )
        return

    new_balance = balance - total_price
    db_update_balance(user.id, new_balance, reason=f"Purchase Social: {product['name']} x{qty}")

    payment_reference_code = await generate_unique_order_code(
        prefix="PROD",
        length=8,
        charset=string.ascii_uppercase + string.digits,
    )
    order_code = _ctt_customer_order_code(payment_reference_code, supplier_result)
    await release_reserved_order_code(payment_reference_code)
    order_data = {
        "order_code": order_code,
        "payment_reference_code": payment_reference_code,
        "user_id": user.id,
        "email": "N/A",
        "amount": total_price,
        "status": ctt_build_local_order_status(supplier_result.get("supplier_status") or "Pending"),
        "type": "store_product",
        "link": supplier_result.get("target_link") or "",
        "timestamp": time.time(),
        "coupon_used": (get_active_store_coupon_context(context, prod_id, qty)[0] or ""),
        "refunded_at": 0,
        "full_name": user.full_name,
        "username": user.username,
        "product_id": prod_id,
        "product_name": product['name'],
        "quantity": qty,
        "items": [],
        "delivery_method": "social_service",
        "is_social_source_service": True,
        "ctt_supplier_order_id": supplier_result.get("supplier_order_id") or "",
        "ctt_supplier_status": supplier_result.get("supplier_status") or "Pending",
        "ctt_supplier_quantity": int(supplier_result.get("supplier_quantity", 0) or 0),
        "ctt_target_link": supplier_result.get("target_link") or "",
        "ctt_comments": supplier_result.get("comments") or "",
    }
    if supplier_result.get("supplier_charge"):
        order_data["ctt_supplier_charge"] = supplier_result.get("supplier_charge")
    if supplier_result.get("supplier_remains"):
        order_data["ctt_supplier_remains"] = supplier_result.get("supplier_remains")
    if supplier_result.get("supplier_start_count"):
        order_data["ctt_supplier_start_count"] = supplier_result.get("supplier_start_count")

    coupon_code_used = order_data.get("coupon_used")
    if coupon_code_used and coupon_code_used in coupons:
        coupons[coupon_code_used]['used'] = coupons[coupon_code_used].get('used', 0) + 1
    clear_store_coupon_context(context)

    db_add_order(order_data)
    await save_data(force=True, tables=[HISTORY_FILE, USERS_FILE])

    target_link = html.escape(str(supplier_result.get("target_link") or "N/A"))
    supplier_order_id = html.escape(str(supplier_result.get("supplier_order_id") or ""))
    supplier_status = html.escape(str(supplier_result.get("supplier_status") or "Pending"))
    supplier_progress = ctt_build_supplier_progress_text(order_data)
    supplier_progress_line = (
        f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>{html.escape(supplier_progress)}</b>\n"
        if supplier_progress
        else ""
    )
    await update.message.reply_text(
        f"{E_SUCCESS} <b>ÄÆ N SOCIAL ÄÃƒ ÄÆ¯á»¢C Táº O THÃ€NH CÃ”NG</b>\n\n"
        f"{E_TAG} <b>Sáº£n pháº©m:</b> {html.escape(str(product['name']))}\n"
        f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>Sá»‘ lÆ°á»£ng:</b> {qty}\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>MÃ£ Ä‘Æ¡n:</b> <code>{html.escape(str(order_code))}</code>\n"
        f"<tg-emoji emoji-id=\"6059654836918423763\">ðŸ“Š</tg-emoji> <b>Tá»•ng Ä‘Æ¡n vá»‹ nguá»“n:</b> {int(supplier_result.get('supplier_quantity', 0) or 0):,}\n"
        f"<tg-emoji emoji-id=\"5231489647946768652\">ðŸ”—</tg-emoji> <b>Target:</b> <code>{target_link}</code>\n"
        f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“</tg-emoji> <b>MÃ£ supplier:</b> <code>{supplier_order_id}</code>\n"
        f"{E_STAT} <b>Tráº¡ng thÃ¡i nguá»“n:</b> {supplier_status}\n"
        f"{supplier_progress_line}"
        f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> <b>ÄÃ£ trá»«:</b> {total_price:,} VNÄ\n"
        f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>Sá»‘ dÆ° cÃ²n láº¡i:</b> {new_balance:,} VNÄ",
        parse_mode=ParseMode.HTML,
        reply_markup=create_success_menu(),
    )

    await send_live_order_notification(
        context,
        user.full_name,
        total_price,
        product_name=product['name'],
        quantity=qty,
        order_code=order_code,
    )
    await notify_admin_store_order(
        context,
        order_code=order_code,
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        product_name=product['name'],
        quantity=qty,
        amount=total_price,
        payment_method="balance",
        items=[],
        delivery_method="social_service",
        is_resell=False,
    )


def _ctt_has_source_entries() -> bool:
    category_name, category_products = get_ctt_source_category_by_index(0)
    return bool(category_name and category_products)


async def _ensure_ctt_catalog_ready():
    refresh_ctt_runtime_config()

    if _ctt_has_source_entries():
        return True

    try:
        load_data()
    except (OSError, ValueError, KeyError, AttributeError):
        pass

    if _ctt_has_source_entries():
        return True

    if not SOCIAL_SOURCE_API_KEY:
        return False

    sync_result = await ctt_sync_catalog(force_refresh=True, log_error=False)
    return bool(sync_result.get("success") and _ctt_has_source_entries())


def _get_ctt_root_panel_text() -> str:
    if not SOCIAL_SOURCE_API_KEY:
        return (
            f"<b>{html.escape(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY)}</b>\n\n"
            "Nguon social chua duoc cau hinh."
        )
    if not _ctt_has_source_entries():
        return (
            f"<b>{html.escape(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY)}</b>\n\n"
            "Catalog social dang rong hoac chua sync xong."
        )
    return (
        f"<b>DANH MUC: {html.escape(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY)}</b>\n\n"
        "Chon nhom dich vu social:"
    )


def _clear_ctt_search_state(context: ContextTypes.DEFAULT_TYPE, *, clear_query: bool = True):
    if getattr(context, "user_data", None) is None:
        return
    if context.user_data.get("state") == "awaiting_ctt_catalog_search":
        context.user_data.pop("state", None)
    if clear_query:
        context.user_data.pop("ctt_search_query", None)


def _get_ctt_search_prompt_text() -> str:
    return (
        "<b>TIM KIEM DICH VU SOCIAL</b>\n\n"
        "Nhap tu khoa de loc dich vu.\n"
        "Vi du: <code>facebook</code>, <code>tiktok like</code>, <code>instagram</code>\n\n"
        "Go <code>huy</code> neu muon quay lai danh muc social."
    )


def _get_ctt_search_result_panel_text(search_query: str) -> str:
    result_count = len(_get_ctt_search_result_entries(search_query))
    return (
        "<b>KET QUA TIM KIEM SOCIAL</b>\n\n"
        f"Tu khoa: <code>{html.escape(str(search_query or ''))}</code>\n"
        f"So ket qua: <b>{result_count}</b>\n\n"
        "Chon dich vu chi tiet:"
    )


def _get_store_category_panel_text(category_name: str, user_id: int, refresh_summary: str = "") -> str:
    lang = get_user_lang(user_id)
    category_copy = {
        "vi": ("DANH Má»¤C", "Chá»n sáº£n pháº©m chi tiáº¿t:"),
        "en": ("CATEGORY", "Choose a product:"),
        "zh": ("åˆ†ç±»", "è¯·é€‰æ‹©å•†å“ï¼š"),
    }[lang]
    category_icon_id = get_store_icon_id(category_name, "5854908544712707500")
    summary = f"\n\n{refresh_summary}" if refresh_summary else ""
    return (
        f"<tg-emoji emoji-id=\"{category_icon_id}\">ðŸŽ¬</tg-emoji> "
        f"<b>{category_copy[0]}: {html.escape(category_name)}</b>\n\n"
        f"{category_copy[1]}{summary}"
    )


async def _refresh_resell_product_entries(product_entries) -> dict:
    summary = {"updated": 0, "errors": 0, "total": 0}
    for prod_id, product in list(product_entries or []):
        if not isinstance(product, dict) or not product.get("is_supplier_source_resell"):
            continue
        summary["total"] += 1
        variant_id = str(product.get("supplier_source_variant_id") or "").strip()
        if not variant_id:
            summary["errors"] += 1
            continue

        result = await supplier_get_variant_info(product)
        if not result.get("success"):
            error_text = str(result.get("error") or "supplier_refresh_failed")
            if _supplier_source_is_purchase_unavailable_error(error_text, int(result.get("status_code", 0) or 0)):
                _supplier_source_update_purchase_block_state(
                    product_id=product.get("supplier_source_product_id"),
                    variant_id=variant_id,
                    blocked=True,
                    reason=error_text,
                    force_stock_zero=True,
                    persist=False,
                )
            summary["errors"] += 1
            continue

        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        try:
            source_price = int(float(data.get("price", 0) or 0))
        except (TypeError, ValueError):
            source_price = 0
        try:
            source_stock = max(0, int(float(data.get("stock", 0) or 0)))
        except (TypeError, ValueError):
            source_stock = 0
        try:
            markup_percent = float(product.get("markup_percent", 0) or 0)
        except (TypeError, ValueError):
            markup_percent = 0

        if source_price > 0:
            products[prod_id]["supplier_source_price"] = source_price
            products[prod_id]["price"] = int(source_price * (1 + markup_percent / 100))
        products[prod_id]["supplier_source_stock"] = source_stock
        _supplier_source_update_purchase_block_state(
            product_id=product.get("supplier_source_product_id"),
            variant_id=variant_id,
            blocked=False,
            persist=False,
        )
        summary["updated"] += 1

    if summary["total"]:
        await save_data(force=True)
    return summary


async def handle_store_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "store_main":
        # Acknowledge early to stop Telegram spinner immediately.
        await safe_answer(query)
        _clear_ctt_search_state(context)

        lang = get_user_lang(query.from_user.id)
        store_copy = {
            "vi": ("Cá»¬A HÃ€NG Dá»ŠCH Vá»¤", "Chá»n danh má»¥c sáº£n pháº©m báº¡n quan tÃ¢m:"),
            "en": ("SERVICE STORE", "Choose a product category:"),
            "zh": ("æœåŠ¡å•†åº—", "è¯·é€‰æ‹©å•†å“åˆ†ç±»ï¼š"),
        }[lang]
        store_text = (
            "<tg-emoji emoji-id=\"5247134066322447995\">ðŸ›ï¸</tg-emoji> "
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
            await safe_answer(query, "Combo khÃ´ng tá»“n táº¡i", show_alert=True)
            return True
        combo_prods = [products.get(pid) for pid in combo.get('products', []) if pid in products]
        if len(combo_prods) != 2:
            await safe_answer(query, "Combo khÃ´ng há»£p lá»‡", show_alert=True)
            return True
        total = sum(p['price'] for p in combo_prods)
        combo_price = int(total * (100 - combo['discount_percent']) / 100)
        msg = (
            f"<tg-emoji emoji-id=\"5226711870492126219\">ðŸŽ¯</tg-emoji> <b>COMBO Æ¯U ÄÃƒI</b>\n\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> {html.escape(combo_prods[0]['name'])}\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> {html.escape(combo_prods[1]['name'])}\n\n"
            f'<tg-emoji emoji-id="5278467510604160626">ðŸ’°</tg-emoji> GiÃ¡ gá»‘c: <s>{total:,}Ä‘</s>\n'
            f"<tg-emoji emoji-id=\"5863724849851011383\">ðŸ’µ</tg-emoji> GiÃ¡ combo: <b>{combo_price:,}Ä‘</b> (-{combo['discount_percent']}%)\n\n"
            f"<i>Báº¥m vÃ o tá»«ng sáº£n pháº©m Ä‘á»ƒ mua riÃªng:</i>"
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
        btns.append([_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="store_main")])
        await _show_store_panel(query, context, msg, InlineKeyboardMarkup(btns))
        return True

    elif data == f"view_cat_{SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY}":
        await safe_answer(query)
        _clear_ctt_search_state(context)
        await _ensure_ctt_catalog_ready()
        await safe_edit_message(
            query,
            text=_get_ctt_root_panel_text(),
            reply_markup=create_ctt_source_category_menu(page=0),
            parse_mode='HTML'
        )
        return True

    elif data.startswith("view_ctt_root_"):
        await safe_answer(query)
        _clear_ctt_search_state(context)
        await _ensure_ctt_catalog_ready()
        try:
            page = int(data.replace("view_ctt_root_", ""))
        except (TypeError, ValueError):
            page = 0
        await safe_edit_message(
            query,
            text=_get_ctt_root_panel_text(),
            reply_markup=create_ctt_source_category_menu(page=page),
            parse_mode='HTML'
        )
        return True

    elif data == "ctt_search_prompt":
        await safe_answer(query)
        _clear_ctt_search_state(context)
        await _ensure_ctt_catalog_ready()
        context.user_data["state"] = "awaiting_ctt_catalog_search"
        await safe_edit_message(
            query,
            text=_get_ctt_search_prompt_text(),
            reply_markup=InlineKeyboardMarkup([
                [_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data="view_ctt_root_0")],
            ]),
            parse_mode='HTML',
        )
        return True

    elif data == "ctt_search_cancel":
        await safe_answer(query)
        _clear_ctt_search_state(context)
        await safe_edit_message(
            query,
            text=_get_ctt_root_panel_text(),
            reply_markup=create_ctt_source_category_menu(page=0),
            parse_mode='HTML',
        )
        return True

    elif data.startswith("view_ctt_search_"):
        await safe_answer(query)
        search_query = str(context.user_data.get("ctt_search_query") or "").strip()
        if not search_query:
            await safe_answer(query, "Khong tim thay tu khoa dang tim.", show_alert=True)
            return True
        try:
            page = int(data.replace("view_ctt_search_", ""))
        except (TypeError, ValueError):
            page = 0
        await safe_edit_message(
            query,
            text=_get_ctt_search_result_panel_text(search_query),
            reply_markup=create_ctt_search_result_menu(search_query, page=page),
            parse_mode='HTML',
        )
        return True

    elif data.startswith("view_ctt_source_"):
        await safe_answer(query)
        _clear_ctt_search_state(context)
        payload = data.replace("view_ctt_source_", "")
        try:
            source_index_raw, page_raw = payload.split("_", 1)
            source_index = int(source_index_raw)
            page = int(page_raw)
        except (AttributeError, TypeError, ValueError):
            await safe_answer(query, "Danh muc social khong hop le", show_alert=True)
            return True

        category_name, _ = get_ctt_source_category_by_index(source_index)
        if not category_name:
            await safe_answer(query, "Danh muc social khong ton tai", show_alert=True)
            return True

        await safe_edit_message(
            query,
            text=f"<b>DANH MUC SOCIAL: {html.escape(category_name)}</b>\n\nChon dich vu chi tiet:",
            reply_markup=create_ctt_source_product_menu(source_index, page=page),
            parse_mode='HTML'
        )
        return True

    elif data.startswith("view_prod_search_"):
        try:
            page_payload, prod_id = data.replace("view_prod_search_", "", 1).split("|", 1)
            page = int(page_payload)
        except (AttributeError, TypeError, ValueError):
            await safe_answer(query, "San pham khong ton tai", show_alert=True)
            return True
        return await _show_store_product_detail(
            query,
            context,
            prod_id,
            back_callback_data=f"view_ctt_search_{page}",
        )

    elif data.startswith("view_prod_ctx_"):
        try:
            context_payload, prod_id = data.replace("view_prod_ctx_", "", 1).split("|", 1)
            source_index_raw, page_raw = context_payload.split("_", 1)
            source_index = int(source_index_raw)
            page = int(page_raw)
        except (AttributeError, TypeError, ValueError):
            await safe_answer(query, "San pham khong ton tai", show_alert=True)
            return True
        return await _show_store_product_detail(
            query,
            context,
            prod_id,
            back_callback_data=f"view_ctt_source_{source_index}_{page}",
        )

    elif data.startswith("refresh_resell_cat:"):
        now = time.time()
        last_refresh = float(context.user_data.get("_last_resell_store_refresh", 0) or 0)
        if now - last_refresh < 3:
            await safe_answer(query, "Vui lÃ²ng chá» vÃ i giÃ¢y trÆ°á»›c khi lÃ m má»›i láº¡i.", show_alert=True)
            return True
        context.user_data["_last_resell_store_refresh"] = now

        category_token = data.split(":", 1)[1]
        category_name = get_store_resell_category_by_token(category_token)
        if not category_name:
            await safe_answer(query, "Danh má»¥c resell khÃ´ng cÃ²n tá»“n táº¡i.", show_alert=True)
            return True

        await safe_answer(query, "Äang cáº­p nháº­t giÃ¡ vÃ  tá»“n kho...")
        category_products = _group_visible_products_by_category().get(category_name, [])
        summary = await _refresh_resell_product_entries(category_products)
        lang = get_user_lang(query.from_user.id)
        error_suffix_vi = f" Â· Lá»—i: {summary['errors']}" if summary["errors"] else ""
        error_suffix_en = f" Â· Errors: {summary['errors']}" if summary["errors"] else ""
        error_suffix_zh = f" Â· é”™è¯¯ï¼š{summary['errors']}" if summary["errors"] else ""
        refresh_summary = {
            "vi": f"ðŸ”„ <i>ÄÃ£ lÃ m má»›i: {summary['updated']}/{summary['total']} sáº£n pháº©m"
                  f"{error_suffix_vi}</i>",
            "en": f"ðŸ”„ <i>Refreshed: {summary['updated']}/{summary['total']} products"
                  f"{error_suffix_en}</i>",
            "zh": f"ðŸ”„ <i>å·²åˆ·æ–°ï¼š{summary['updated']}/{summary['total']} ä¸ªå•†å“"
                  f"{error_suffix_zh}</i>",
        }.get(lang)
        await safe_edit_message(
            query,
            text=_get_store_category_panel_text(category_name, query.from_user.id, refresh_summary),
            reply_markup=create_store_menu(selected_category=category_name, user_id=query.from_user.id),
            parse_mode="HTML",
        )
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

        if _is_ctt_store_product(p):
            if not SOCIAL_SOURCE_API_KEY:
                await safe_answer(query, "âŒ Nguá»“n social chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh.", show_alert=True)
                return True

            minimum_quantity = _ctt_get_package_quantity(p)
            quantity_error = _ctt_validate_purchase_quantity(p, minimum_quantity)
            if quantity_error:
                await safe_answer(query, quantity_error, show_alert=True)
                return True

            max_quantity = _ctt_get_max_package_purchase(p)
            quick_quantities = _ctt_get_quick_quantity_options(p)

            btns = []
            row = []
            for q in quick_quantities:
                if q <= max_quantity:
                    row.append(_btn(f"{q}", callback_data=f"buy_prod_confirm_{prod_id}_{q}", style="success"))
                if len(row) == 3:
                    btns.append(row)
                    row = []

            if row:
                btns.append(row)

            btns.append([_btn("Nháº­p sá»‘ lÆ°á»£ng", icon_id="5364075889669718872", callback_data=f"custom_qty_{prod_id}")])
            btns.append([_btn("Quay láº¡i", icon_id="6206032691075223572", callback_data=f"view_prod_{prod_id}")])

            msg_text = (
                f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>CHá»ŒN Sá» LÆ¯á»¢NG MUá»N MUA</b>\n\n"
                f"{E_TAG} Sáº£n pháº©m: {p['name']}\n"
                f"{E_TAG} ÄÆ¡n giÃ¡: {p['price']:,} VNÄ / Ä‘Æ¡n vá»‹\n"
                f"{E_STAT} Tá»‘i thiá»ƒu: {minimum_quantity:,} Ä‘Æ¡n vá»‹\n"
                f"{E_STAT} Tá»‘i Ä‘a: {max_quantity:,} Ä‘Æ¡n vá»‹\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> Chá»n sá»‘ lÆ°á»£ng:"
            )
            await _show_store_panel(query, context, msg_text, InlineKeyboardMarkup(btns))
            return True
        
        if requires_gmail:
            pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
            max_pending = p.get('max_pending_orders', 10)
            labels = _checkout_labels(query.from_user.id)
            lang = get_user_lang(query.from_user.id)
            manual = {
                "vi": {"busy": "ADMIN ÄANG Báº¬N!", "processing": "Äang xá»­ lÃ½", "return": "Vui lÃ²ng quay láº¡i sau 10-30 phÃºt", "title": "XÃC NHáº¬N Äáº¶T Dá»ŠCH Vá»¤", "manual": "Dá»‹ch vá»¥ manual", "original": "GiÃ¡ gá»‘c", "payment": "Thanh toÃ¡n", "after": "Sau khi thanh toÃ¡n", "steps": ("Báº¡n sáº½ nháº­p email", "Admin setup trong 1-30 phÃºt", "Nháº­n thÃ´ng bÃ¡o check mail"), "none": "KhÃ´ng"},
                "en": {"busy": "ADMIN IS BUSY!", "processing": "Processing", "return": "Please return in 10-30 minutes", "title": "CONFIRM SERVICE ORDER", "manual": "Manual service", "original": "Original price", "payment": "Payment", "after": "After payment", "steps": ("Enter your email", "Admin sets it up within 1-30 minutes", "Receive an email-check notification"), "none": "Unavailable"},
                "zh": {"busy": "ç®¡ç†å‘˜å¿™ç¢Œä¸­ï¼", "processing": "æ­£åœ¨å¤„ç†", "return": "è¯·åœ¨ 10-30 åˆ†é’ŸåŽé‡è¯•", "title": "ç¡®è®¤æœåŠ¡è®¢å•", "manual": "äººå·¥æœåŠ¡", "original": "åŽŸä»·", "payment": "ä»˜æ¬¾", "after": "ä»˜æ¬¾åŽ", "steps": ("è¾“å…¥é‚®ç®±", "ç®¡ç†å‘˜å°†åœ¨ 1-30 åˆ†é’Ÿå†…è®¾ç½®", "æ”¶åˆ°æŸ¥æ”¶é‚®ä»¶é€šçŸ¥"), "none": "ä¸å¯ç”¨"},
            }[lang]

            if pending_count >= max_pending:
                await safe_answer(query, f"âš ï¸ {manual['busy']}\n\n{manual['processing']}: {pending_count}/{max_pending}\n{manual['return']}", show_alert=True)
                return True

            user = update.effective_user
            user_info = db_get_user(user.id)
            balance = user_info.get('balance', 0) if user_info else 0
            unit_price, discount_type, discount_info = get_best_discount(user.id, prod_id, p['price'])
            total_price = unit_price
            product_name = p.get(f"name_{lang}") or p.get("name") or prod_id

            price_line = f"{E_TAG} <b>{labels['total']}:</b> {total_price:,} VNÄ\n"
            if total_price < p['price']:
                price_line = f"{E_TAG} <b>{manual['original']}:</b> <s>{p['price']:,} VNÄ</s>\n{E_TAG} <b>{manual['payment']}:</b> <b>{total_price:,} VNÄ</b>"
                if discount_type == 'flash_sale':
                    price_line += " (Flash Sale)"
                price_line += "\n"

            msg_text = (
                f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>{manual['title']}</b>\n\n"
                f"{E_TAG} <b>{labels['product']}:</b> {product_name}\n"
                f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>{labels['quantity']}:</b> 1 ({manual['manual']})\n"
                f"{price_line}\n"
                f"<tg-emoji emoji-id=\"5264919878082509254\">â„¹ï¸</tg-emoji> <b>{manual['after']}:</b>\n"
                f"1. {manual['steps'][0]}\n2. {manual['steps'][1]}\n3. {manual['steps'][2]}\n\n"
                f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> {labels['choose_payment']}:"
            )

            btns = []
            bal_text = f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> {labels['balance']} ({balance:,}Ä‘)"
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
            from app.core.config_env import ENABLE_PAYMENT_MBBANK
            if ENABLE_PAYMENT_MBBANK:
                btns.append([_btn(labels["bank"], icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_1", style="success")])
            btns.append([_btn(labels["coupon"], icon_id="5377624166436445368", callback_data=f"store_coupon_{prod_id}_1")])
            btns.append([_btn(labels["back"], icon_id="6206032691075223572", callback_data=f"view_prod_{prod_id}")])

            await _show_store_panel(query, context, msg_text, InlineKeyboardMarkup(btns))
            return True
        
        # AUTO PRODUCTS - Cho chá»n sá»‘ lÆ°á»£ng
        # BUG FIX: Sáº£n pháº©m resell dÃ¹ng supplier_source_stock thay vÃ¬ stock local
        is_resell = p.get('is_supplier_source_resell', False)
        if is_resell:
            stock_count = _get_supplier_source_stock_count(p)
            effective_stock = stock_count
        else:
            stock_count = int(get_local_stock_available_count(p) or 0)
            effective_stock = stock_count

        labels = _checkout_labels(query.from_user.id)
        if effective_stock <= 0:
            await safe_answer(query, f"âŒ {labels['out']}", show_alert=True)
            return True

        _max_buy = min(effective_stock, 100) if effective_stock > 0 else 100
        
        btns = []
        row = []
        
        # Táº¡o nÃºt 1-5 (dÃ¹ng effective_stock Ä‘á»ƒ resell luÃ´n cÃ³ nÃºt)
        for q in [1, 2, 3, 4, 5]:
            if q <= effective_stock:
                row.append(_btn(f"{q}", callback_data=f"buy_prod_confirm_{prod_id}_{q}", style="success"))
            
            if len(row) == 3:
                btns.append(row)
                row = []
                
        if row:
            btns.append(row)
            
        # NÃºt lá»›n hÆ¡n
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
            f"<tg-emoji emoji-id=\"5334890573281114250\">ðŸ”¢</tg-emoji> <b>{labels['choose_qty']}</b>\n\n"
            f"{E_TAG} {labels['product']}: {product_name}\n"
            f"{E_TAG} {labels['unit_price']}: {p['price']:,} VNÄ\n"
            f"{E_STAT} {labels['stock']}: {stock_display}\n\n"
            f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‡</tg-emoji> {labels['quantity']}:"
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
            await safe_answer(query, f"âŒ {labels['missing']}", show_alert=True)
            return True

        if _is_ctt_store_product(p):
            if not SOCIAL_SOURCE_API_KEY:
                await safe_answer(query, "âŒ Nguá»“n social chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh.", show_alert=True)
                return True
            quantity_error = _ctt_validate_purchase_quantity(p, qty)
            if quantity_error:
                await safe_answer(query, quantity_error, show_alert=True)
                return True

        if p.get('is_supplier_source_resell'):
            available_count = _get_supplier_source_stock_count(p)
            if available_count < qty:
                await safe_answer(
                    query,
                    f"âŒ Nguá»“n SupplierSource chá»‰ cÃ²n {available_count} sáº£n pháº©m!",
                    show_alert=True,
                )
                return True

        unit_price, discount_type, discount_info = get_best_discount(update.effective_user.id, prod_id, p['price'])
        total_price = _get_ctt_store_total_price(update.effective_user.id, context, prod_id, p, qty) if _is_ctt_store_product(p) else unit_price * qty
        
        user_id = update.effective_user.id
        user_info = db_get_user(user_id)
        balance = user_info.get('balance', 0) if user_info else 0
        
        btns = []
        
        bal_text = f"{labels['balance']} ({balance:,}Ä‘)"
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
        from app.core.config_env import ENABLE_PAYMENT_MBBANK
        if ENABLE_PAYMENT_MBBANK:
            btns.append([_btn(labels["bank"], icon_id=BANK_BUTTON_ICON_ID, callback_data=f"pay_prod_qr_{prod_id}_{qty}", style="success")])
        btns.append([_btn(labels["coupon"], icon_id="5447364299200678034", callback_data=f"store_coupon_{prod_id}_{qty}")])
        btns.append([_btn(labels["back"], icon_id="6206032691075223572", callback_data=f"sel_qty_{prod_id}")])

        combo_note = ""
        if 0 < balance < total_price:
            combo_note = f"\n\n<tg-emoji emoji-id=\"5460753627817723162\">ðŸ’¡</tg-emoji> <i>Báº¡n cÃ³ thá»ƒ káº¿t há»£p vÃ­ ({balance:,}Ä‘) + chuyá»ƒn khoáº£n ({total_price - balance:,}Ä‘)</i>"

        supplier_note = ""
        if _is_ctt_store_product(p):
            minimum_quantity = _ctt_get_package_quantity(p)
            supplier_units = _ctt_get_total_supplier_quantity(p, qty)
            supplier_note = (
                f'\n{E_STAT} ÄÆ¡n vá»‹ nguá»“n: {supplier_units:,}'
                f'\n{E_STAT} Tá»‘i thiá»ƒu: {minimum_quantity:,} Ä‘Æ¡n vá»‹'
            )

        lang = get_user_lang(user_id)
        product_name = p.get(f"name_{lang}") or p.get("name") or prod_id
        await _show_store_panel(
            query,
            context,
            f'<tg-emoji emoji-id="5247134066322447995">ðŸ›</tg-emoji> <b>{labels["confirm"]}</b>\n\n'
            f'<tg-emoji emoji-id="5240228673738527951">ðŸ·</tg-emoji> {labels["product"]}: {product_name}\n'
            f'<tg-emoji emoji-id="5305749482170758709">0ï¸âƒ£</tg-emoji> {labels["quantity"]}: {qty}{supplier_note}\n'
            f'<tg-emoji emoji-id="5240228673738527951">ðŸ·</tg-emoji> {labels["total"]}: {total_price:,} VNÄ{" (-" + str(discount_info["discount_percent"]) + "%)" if discount_type else ""}'
            f'{combo_note}\n\n'
            f'<tg-emoji emoji-id="6186252635805323641">ðŸ‘‡</tg-emoji> {labels["choose_payment"]}:',
            InlineKeyboardMarkup(btns),
        )
        return True
    
    elif data.startswith("custom_qty_"):
        # Handle custom quantity input
        prod_id = data.replace("custom_qty_", "")
        p = products.get(prod_id)
        if not p:
            await safe_answer(query, "âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!", show_alert=True)
            return True

        if _is_ctt_store_product(p):
            if not SOCIAL_SOURCE_API_KEY:
                await safe_answer(query, "âŒ Nguá»“n social chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh.", show_alert=True)
                return True
            minimum_quantity = _ctt_get_package_quantity(p)
            max_quantity = _ctt_get_max_package_purchase(p)
            quantity_error = _ctt_validate_purchase_quantity(p, minimum_quantity)
            if max_quantity <= 0 or quantity_error:
                await safe_answer(query, quantity_error or "âŒ Dá»‹ch vá»¥ social hiá»‡n chÆ°a sáºµn sÃ ng.", show_alert=True)
                return True
            stock_count = max_quantity
            _max_text = str(max_quantity)
        # BUG FIX: Sáº£n pháº©m resell dÃ¹ng supplier_source_stock
        elif p.get('is_supplier_source_resell'):
            stock_count = _get_supplier_source_stock_count(p)
            if stock_count <= 0:
                await safe_answer(query, "âŒ Sáº£n pháº©m hiá»‡n Ä‘ang háº¿t hÃ ng!", show_alert=True)
                return True
            _max_text = str(stock_count)
        else:
            stock_count = int(get_local_stock_available_count(p) or 0)
            _max_text = str(stock_count)

        # Set state for text input only after stock validation passes
        context.user_data['state'] = f'awaiting_custom_qty:{prod_id}'
        social_min_line = ""
        if _is_ctt_store_product(p):
            social_min_line = f"{E_STAT} <b>Tá»‘i thiá»ƒu:</b> {minimum_quantity:,}\n"
        
        await _show_store_panel(
            query,
            context,
            f"<tg-emoji emoji-id=\"5350752364246606166\">âœï¸</tg-emoji> <b>NHáº¬P Sá» LÆ¯á»¢NG Tá»° CHá»ŒN</b>\n\n"
            f"{E_TAG} <b>Sáº£n pháº©m:</b> {p['name']}\n"
            f"{E_TAG} <b>ÄÆ¡n giÃ¡:</b> {p['price']:,} VNÄ{' / Ä‘Æ¡n vá»‹' if _is_ctt_store_product(p) else ''}\n"
            f"{E_STAT} <b>{'Giá»›i háº¡n sá»‘ lÆ°á»£ng' if _is_ctt_store_product(p) else 'Tá»“n kho'}:</b> {stock_count}\n"
            f"{social_min_line}"
            f"<tg-emoji emoji-id=\"6186252635805323641\">ðŸ‘‰</tg-emoji> Vui lÃ²ng <b>nháº­p sá»‘ lÆ°á»£ng</b> muá»‘n mua:\n\n"
            f"<i>VÃ­ dá»¥: Nháº­p 1000 náº¿u muá»‘n server cháº¡y Ä‘Ãºng 1000 Ä‘Æ¡n vá»‹</i>",
            InlineKeyboardMarkup([[_btn("Há»§y", icon_id="5273914604752216432", callback_data=f"sel_qty_{prod_id}", style="danger")]]),
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
            await safe_answer(query, "âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!", show_alert=True)
            return True

        if p.get('is_supplier_source_resell'):
            available_count = _get_supplier_source_stock_count(p)
            if available_count < qty:
                await safe_answer(
                    query,
                    f"âŒ Nguá»“n SupplierSource chá»‰ cÃ²n {available_count} sáº£n pháº©m!",
                    show_alert=True,
                )
                return True

        if _is_ctt_store_product(p):
            total_price = _get_ctt_store_total_price(update.effective_user.id, context, prod_id, p, qty)
        else:
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
            await safe_answer(query, "âŒ Sá»‘ dÆ° khÃ´ng Ä‘á»§!", show_alert=True)
            return True

        if _is_ctt_store_product(p):
            return await _begin_ctt_checkout_collection(query, context, prod_id, qty, "balance")

        # FIX: Check requires_gmail TRÆ¯á»šC Ä‘á»ƒ bá» qua stock check náº¿u manual
        requires_gmail = p.get('requires_gmail', False)
        
        if not requires_gmail:
            # Chá»‰ check stock cho AUTO products (KHÃ”NG pháº£i resell)
            # Resell products mua real-time tá»« API, khÃ´ng cáº§n check local stock
            if not p.get('is_supplier_source_resell'):
                available_count = int(get_local_stock_available_count(p) or 0)
                if available_count < qty:
                    await safe_answer(query, f"âŒ Chá»‰ cÃ²n {available_count} sáº£n pháº©m, khÃ´ng Ä‘á»§ sá»‘ lÆ°á»£ng {qty}!", show_alert=True)
                    return True
        
        if requires_gmail:
            # FLOW Má»šI: Há»i email â†’ BÃ¡o Admin â†’ Admin xá»­ lÃ½
            
            # Trá»« tiá»n trÆ°á»›c
            new_balance = balance - total_price
            db_update_balance(user_id, new_balance)
            
            # LÆ°u thÃ´ng tin táº¡m thá»i & GLOBAL (Persistent)
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
                'email': None, # ChÆ°a cÃ³ email
                'product_id': prod_id,
                'product_name': p['name'],
                'quantity': qty,
                'amount': total_price,
                'status': 'awaiting_email', # Tráº¡ng thÃ¡i chá» email
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
                f"{E_SUCCESS} <b>ÄÃƒ TRá»ª TIá»€N THÃ€NH CÃ”NG!</b>\n\n"
                f"{E_TAG} <b>Sáº£n pháº©m:</b> {p['name']}\n"
                f"{E_TAG} <b>ÄÃ£ trá»«:</b> {total_price:,} VNÄ\n"
                f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>Sá»‘ dÆ° cÃ²n:</b> {new_balance:,} VNÄ\n\n"
                f"{E_GLOBE} <b>Vui lÃ²ng nháº­p email nháº­n dá»‹ch vá»¥:</b>\n"
                f"<i>(Email nÃ y sáº½ Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ setup/gá»­i thÃ´ng tin)</i>",
                parse_mode='HTML'
            )
            
            # Edit message vÃ  lÆ°u message_id Ä‘á»ƒ xÃ³a sau
            waiting_msg = await query.edit_message_text(
                "<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> <b>CHá»œ NHáº¬P EMAIL...</b>",
                reply_markup=None
            )
            context.user_data['waiting_message_id'] = waiting_msg.message_id
            context.user_data['waiting_chat_id'] = waiting_msg.chat_id
            
            # Gá»­i thÃ´ng bÃ¡o cho admin ráº±ng Ä‘ang chá» email
            admin_notif = await context.bot.send_message(
                ADMIN_USER_ID,
                f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>ÄÃƒ NHáº¬N THANH TOÃN - ÄÆ N MANUAL</b>\n"
                f"<tg-emoji emoji-id=\"5972022360025336988\">ðŸ”¸</tg-emoji> MÃ£: {order_code}\n"
                f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> SP: {p['name']}\n"
                f"<tg-emoji emoji-id=\"5278467510604160626\">ðŸ’°</tg-emoji> {total_price:,} VNÄ\n"
                f"<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Äang chá» khÃ¡ch nháº­p email...",
                parse_mode='HTML'
            )
            # LÆ°u message_id cá»§a thÃ´ng bÃ¡o admin Ä‘á»ƒ update sau
            context.user_data['admin_waiting_message_id'] = admin_notif.message_id
            return True
        
        # FLOW CÅ¨: Giao hÃ ng tá»± Ä‘á»™ng & AUTO RESELL
        # Check Auto Resell first
        is_resell = p.get('is_supplier_source_resell', False)
        items_bought = []
        actual_qty = qty
        refunded_qty = 0
        refund_amount = 0
        charged_amount = total_price
        
        if is_resell:
            # === AUTO RESELL FLOW ===
            # 1. Trá»« tiá»n trÆ°á»›c (Ä‘á»ƒ trÃ¡nh spam)
            new_balance = balance - total_price
            db_update_balance(user_id, new_balance, reason=f"Purchase Resell: {p['name']} x{qty}")
            
            # 2. Gá»i API nguá»“n qua dispatcher (SupplierSource / SupplierCatalog)
            supplier_source_product_id = p.get('supplier_source_product_id')
            supplier_source_variant_id = p.get('supplier_source_variant_id')
            
            # ThÃ´ng bÃ¡o user Ä‘ang xá»­ lÃ½
            processing_msg = await query.message.reply_text("<tg-emoji emoji-id=\"5213349767672769194\">â³</tg-emoji> Äang káº¿t ná»‘i Ä‘áº¿n kho hÃ ng Ä‘á»‘i tÃ¡c...")
            
            supplier_source_result = await supplier_create_order(p, qty)
            
            # XÃ³a tin nháº¯n waiting
            try:
                await context.bot.delete_message(chat_id=processing_msg.chat_id, message_id=processing_msg.message_id)
            except (Forbidden, BadRequest) as e:
                logger.debug(f"Cannot delete supplier processing message: {e}")

            if not supplier_source_result.get("success"):
                # Lá»—i API -> HoÃ n tiá»n ngay láº­p tá»©c
                db_update_balance(user_id, balance, reason=f"Refund: Supplier API Error {p['name']}")
                error = supplier_source_result.get("error", "Unknown")
                failed_order_code = await generate_unique_order_code(
                    prefix="PROD",
                    length=8,
                    charset=string.ascii_uppercase + string.digits,
                )
                await record_wallet_refund(
                    context,
                    order_code=failed_order_code,
                    user_id=user_id,
                    amount=total_price,
                    product_name=p.get("name", "Sáº£n pháº©m"),
                    reason=f"Lá»—i nguá»“n cung cáº¥p: {error}",
                    order_data={
                        "product_id": prod_id,
                        "quantity": qty,
                        "full_name": getattr(update.effective_user, "full_name", "") or "Unknown",
                        "username": getattr(update.effective_user, "username", "") or "",
                        "is_supplier_source_resell": True,
                        "delivery_method": "supplier_failed",
                    },
                )
                await safe_answer(query, "âŒ Sáº£n pháº©m nguá»“n táº¡m thá»i khÃ´ng thá»ƒ giao dá»‹ch. ÄÃ£ hoÃ n tiá»n vÃ o vÃ­!", show_alert=True)
                
                # Notify Admin
                await safe_send_admin(
                    context.bot,
                    f"<tg-emoji emoji-id=\"5447644880824181073\">ðŸš¨</tg-emoji> <b>Lá»–I NGUá»’N CUNG Cáº¤P KHI MUA Báº°NG Sá» DÆ¯</b>\n"
                    f"User: <code>{user_id}</code>\n"
                    f"ÄÆ¡n: <code>{failed_order_code}</code>\n"
                    f"SP: {html.escape(p['name'])}\n"
                    f"Lá»—i: <code>{html.escape(str(error))}</code>",
                )
                return True
            
            # ThÃ nh cÃ´ng -> Parse content
            supplier_source_orders = supplier_source_result.get("data", [])
            for dm_order in supplier_source_orders:
                delivered = dm_order.get("deliveredContent")
                if delivered:
                    items_bought.extend(normalize_delivered_items(delivered))
            
            # Náº¿u khÃ´ng cÃ³ content (API tráº£ vá» success nhÆ°ng chÆ°a giao hÃ ng) -> Thá»­ láº¥y detail
            if not items_bought:
                 # Retry logic or wait logic similar to check_payment_job if needed
                 # For simplicity in balance payment (synchronous feel), we try one more fetch
                 for dm_order in supplier_source_orders:
                    dm_id = dm_order.get("id")
                    if dm_id:
                        det = await supplier_get_order_details(p, dm_id)
                        if det.get("success"):
                            d_content = det.get("data", {}).get("deliveredContent")
                            if d_content:
                                items_bought.extend(normalize_delivered_items(d_content))
        
        else:
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

        
        # === CHUNG CHO Cáº¢ 2 FLOW (Delivery & Logging) ===
        if not items_bought and is_resell:
             # TrÆ°á»ng há»£p SupplierSource success mÃ  chÆ°a cÃ³ hÃ ng ngay -> BÃ¡o user chá»
             # Log order vá»›i status pending? 
             # Here let's assume worst case handled or manual check needed
             await query.message.reply_text("<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> ÄÆ¡n hÃ ng Ä‘Ã£ táº¡o nhÆ°ng há»‡ thá»‘ng nguá»“n chÆ°a tráº£ hÃ ng. Vui lÃ²ng liÃªn há»‡ Admin Ä‘á»c MÃ£ ÄÆ¡n HÃ ng.")

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
            "status": "HoÃ n thÃ nh",
            "type": "store_product",
            "link": "Resell Product" if is_resell else "Sáº£n pháº©m khÃ¡c",
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
            "is_supplier_source_resell": is_resell
        }
        order_data["delivery_method"] = "pending"
        if not items_bought and is_resell:
            order_data["status"] = "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá» giao tá»« nguá»“n (Resell)"
            order_data["delivery_method"] = "pending_source"
        db_add_order(order_data)
        if store_coupon_code and store_coupon_code in coupons:
            coupons[store_coupon_code]['used'] = coupons[store_coupon_code].get('used', 0) + 1
        clear_store_coupon_context(context)
        total_discount = (p['price'] * qty) - total_price
        if total_discount > 0:
            record_promo_cost(total_discount, 'order_discount')
        await save_data() # Save orders

        # Delivery Message - LuÃ´n gá»­i file .txt
        delivery_notice = (
            f"{E_TIP} <b>Há»‡ thá»‘ng Ä‘ang gá»­i thÃ´ng tin tÃ i khoáº£n ngay sau tin nháº¯n nÃ y...</b>"
            if items_bought
            else f"{E_TIP} <b>ÄÆ¡n nÃ y Ä‘ang chá» giao hÃ ng. Admin sáº½ há»— trá»£ sá»›m nháº¥t.</b>"
        )
        refund_notice = ""
        if refunded_qty > 0:
            refund_notice = f"\n<tg-emoji emoji-id=\"5863724849851011383\">ðŸ’¸</tg-emoji> <b>Thiáº¿u sáº£n pháº©m:</b> KhÃ´ng tÃ­nh tiá»n {refunded_qty} sáº£n pháº©m ({refund_amount:,} VNÄ)\n"
        info_msg = (
            f"{E_SUCCESS} <b>MUA HÃ€NG THÃ€NH CÃ”NG!</b>\n\n"
            f"{E_TAG} <b>Sáº£n pháº©m:</b> {p['name']}\n"
            f"<tg-emoji emoji-id=\"5854908544712707500\">ðŸ“¦</tg-emoji> <b>Sá»‘ lÆ°á»£ng:</b> {actual_qty}"
            f"{' (Thiáº¿u ' + str(refunded_qty) + ' sáº£n pháº©m)' if refunded_qty > 0 else ''}\n"
            f"{E_LOADING} <b>Thá»i háº¡n:</b> {p.get('duration', 'N/A')}\n"
            f"<tg-emoji emoji-id=\"5197288647275071607\">ðŸ›¡ï¸</tg-emoji> <b>Báº£o hÃ nh:</b> {p.get('warranty', 'KhÃ´ng')}\n"
            f"{E_TAG} <b>Thanh toÃ¡n thá»±c táº¿:</b> {charged_amount:,} VNÄ\n"
            f"<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> <b>Sá»‘ dÆ° cÃ²n láº¡i:</b> {new_balance:,} VNÄ"
            f"{refund_notice}\n\n"
            f"{delivery_notice}"
        )
        
        await query.message.reply_text(info_msg, parse_mode='HTML')
        delivery_result = {"delivered": False, "method": "failed"}

        if items_bought:
            purchase_date = datetime.fromtimestamp(time.time()).strftime('%d/%m/%Y %H:%M:%S')
            product_description_txt = format_product_description_for_txt(p)
            file_content = "="*60 + "\n"
            file_content += "           THÃ”NG TIN ÄÆ N HÃ€NG\n"
            file_content += "="*60 + "\n\n"
            file_content += f"MÃ£ Ä‘Æ¡n hÃ ng    : {order_code}\n"
            file_content += f"NgÃ y mua       : {purchase_date}\n"
            file_content += f"Sáº£n pháº©m       : {p['name']}\n"
            file_content += f"Sá»‘ lÆ°á»£ng       : {actual_qty}\n"
            if refunded_qty > 0:
                file_content += f"Thiáº¿u sáº£n pháº©m : {refunded_qty}\n"
                file_content += f"KhÃ´ng tÃ­nh tiá»n: {refund_amount:,} VND\n"
            file_content += f"Thanh toÃ¡n     : {charged_amount:,} VND\n"
            if product_description_txt:
                file_content += f"\nMÃ´ táº£ sáº£n pháº©m:\n{product_description_txt}\n\n"
            file_content += f"Thá»i háº¡n       : {p.get('duration', 'N/A')}\n"
            file_content += f"Báº£o hÃ nh       : {p.get('warranty', 'KhÃ´ng')}\n"
            file_content += "\n" + "="*60 + "\n"
            file_content += "           DANH SÃCH TÃ€I KHOáº¢N\n"
            file_content += "="*60 + "\n\n"
            for idx_f, item_f in enumerate(items_bought, 1):
                file_content += f"TÃ i khoáº£n {idx_f}:\n{item_f}\n\n"
            file_content += "Cáº£m Æ¡n quÃ½ khÃ¡ch Ä‘Ã£ mua hÃ ng. ChÃºc quÃ½ khÃ¡ch sá»­ dá»¥ng dá»‹ch vá»¥ vui váº»!\n"
            file_content += "\n" + "="*60 + "\n"
            
            delivery_result = await deliver_items_as_txt(
                context,
                user_id,
                order_code,
                items_bought,
                file_content=file_content,
                file_prefix="DonHang",
                caption_html=f"<tg-emoji emoji-id=\"5373251851074415873\">ðŸ“‹</tg-emoji> <b>File tÃ i khoáº£n</b>\nMÃ£ Ä‘Æ¡n: <code>{order_code}</code>",
                reply_markup=create_success_menu(),
            )
            order_data["delivery_method"] = delivery_result.get("method", "failed")
            await save_data(force=True, tables=[HISTORY_FILE])
            if not delivery_result.get("delivered"):
                order_data["status"] = "<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Chá» gá»­i thá»§ cÃ´ng (Store Balance)"
                await safe_send_admin(
                    context.bot,
                    f"{E_SOS} <b>DELIVERY FAILED (STORE BALANCE)</b>\n"
                    f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                    f"{E_USER} User: <code>{user_id}</code>\n"
                    f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                    f"{E_STAT} Fallback gá»­i: {delivery_result.get('sent_items', 0)}/{len(items_bought)} items\n"
                    f"{E_ERROR} Errors: <code>{html.escape(' | '.join(delivery_result.get('errors', [])[-3:]) or 'n/a')}</code>",
                )
                await safe_send_message(
                    context,
                    user_id,
                    f"âŒ CÃ³ lá»—i khi gá»­i file tÃ i khoáº£n cho Ä‘Æ¡n <code>{order_code}</code>.\n"
                    "Admin Ä‘Ã£ nháº­n cáº£nh bÃ¡o vÃ  sáº½ gá»­i thá»§ cÃ´ng sá»›m nháº¥t.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=create_success_menu(),
                )
                await save_data(force=True, tables=[HISTORY_FILE])
        else:
            await query.message.reply_text("<i>LiÃªn há»‡ Admin Ä‘á»ƒ nháº­n hÃ ng</i>", parse_mode='HTML')
            await safe_send_admin(
                context.bot,
                f"{E_TIP} <b>ÄÆ N CHá»œ GIAO Tá»ª NGUá»’N</b>\n"
                f"{E_ID} ÄÆ¡n: <code>{order_code}</code>\n"
                f"{E_USER} User: <code>{user_id}</code>\n"
                f"{E_TAG} SP: {html.escape(p['name'])} x{qty}\n"
                f"{E_STAT} Tráº¡ng thÃ¡i: {html.escape(order_data.get('status', 'pending'))}",
            )
        
        await query.edit_message_text(
            f"{E_SUCCESS} <b>ÄÃƒ THANH TOÃN THÃ€NH CÃ”NG</b>\n\nCáº£m Æ¡n báº¡n Ä‘Ã£ mua hÃ ng!",
            reply_markup=create_back_button_menu()
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
                is_resell=is_resell,
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
            "\U0001f3ab <b>NH\u1eacP M\xc3 GI\u1ea2M GI\xc1</b>\n\n"
            "Vui l\xf2ng nh\u1eadp m\xe3 coupon c\u1ee7a b\u1ea1n:\n"
            "<i>(G\xf5 /cancel \u0111\u1ec3 h\u1ee7y)</i>",
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
            await safe_answer(query, "âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!", show_alert=True)
            return True
        if p.get('is_supplier_source_resell'):
            available_count = _get_supplier_source_stock_count(p)
            if available_count < qty:
                await safe_answer(
                    query,
                    f"âŒ Nguá»“n SupplierSource chá»‰ cÃ²n {available_count} sáº£n pháº©m!",
                    show_alert=True,
                )
                return True

        user_id = update.effective_user.id
        pending_code, pending_detail = await get_user_pending_order(user_id)
        if pending_code:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Báº¡n Ä‘ang cÃ³ Ä‘Æ¡n {pending_code} chÆ°a hoÃ n thÃ nh! Vui lÃ²ng hoÃ n táº¥t hoáº·c há»§y Ä‘Æ¡n cÅ© trÆ°á»›c.", show_alert=True)
            return True
        user_info = db_get_user(user_id)
        balance = user_info.get('balance', 0) if user_info else 0

        if balance <= 0:
            await safe_answer(query, "âŒ Sá»‘ dÆ° vÃ­ báº±ng 0!", show_alert=True)
            return True

        if _is_ctt_store_product(p):
            total_price = _get_ctt_store_total_price(user_id, context, prod_id, p, qty)
        else:
            unit_price, _, _ = get_best_discount(user_id, prod_id, p['price'])
            _, store_coupon_discount = get_active_store_coupon_context(context, prod_id, qty)
            if store_coupon_discount > 0:
                coupon_unit_price = max(0, p['price'] - store_coupon_discount)
                unit_price = min(unit_price, coupon_unit_price)
            total_price = unit_price * qty

        if balance >= total_price:
            await safe_answer(query, "<tg-emoji emoji-id=\"5213403875670765022\">ðŸ’³</tg-emoji> Sá»‘ dÆ° Ä‘á»§! HÃ£y chá»n thanh toÃ¡n báº±ng sá»‘ dÆ°.", show_alert=True)
            return True

        balance_used = balance
        _qr_amount = total_price - balance_used

        if _is_ctt_store_product(p):
            return await _begin_ctt_checkout_collection(query, context, prod_id, qty, "qr", balance_used=balance_used)

        requires_gmail = p.get('requires_gmail', False)
        if not requires_gmail:
            if not p.get('is_supplier_source_resell'):
                lock = await get_product_lock(prod_id)
                async with lock:
                    available_count = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                    if available_count < qty:
                        await safe_answer(query, "âŒ Sá»‘ lÆ°á»£ng yÃªu cáº§u vÆ°á»£t quÃ¡ tá»“n kho!", show_alert=True)
                        return True
        else:
            pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
            max_pending = p.get('max_pending_orders', 10)
            if pending_count >= max_pending:
                await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Admin Ä‘ang báº­n ({pending_count}/{max_pending})!", show_alert=True)
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
            await safe_answer(query, "âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!", show_alert=True)
            return True
        if p.get('is_supplier_source_resell'):
            available_count = _get_supplier_source_stock_count(p)
            if available_count < qty:
                await safe_answer(query, f"âŒ Nguá»“n SupplierSource chá»‰ cÃ²n {available_count} sáº£n pháº©m!", show_alert=True)
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
            "Binance Pay Ä‘Ã£ Ä‘Æ°á»£c thay tháº¿ báº±ng USDT. Vui lÃ²ng chá»n USDT (Binance ID / BEP20).",
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
            await safe_answer(query, "âŒ Sáº£n pháº©m khÃ´ng tá»“n táº¡i!", show_alert=True)
            return True
        if p.get('is_supplier_source_resell'):
            available_count = _get_supplier_source_stock_count(p)
            if available_count < qty:
                await safe_answer(
                    query,
                    f"âŒ Nguá»“n SupplierSource chá»‰ cÃ²n {available_count} sáº£n pháº©m!",
                    show_alert=True,
                )
                return True

        pending_code, pending_detail = await get_user_pending_order(update.effective_user.id)
        if pending_code:
            await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Báº¡n Ä‘ang cÃ³ Ä‘Æ¡n {pending_code} chÆ°a hoÃ n thÃ nh! Vui lÃ²ng hoÃ n táº¥t hoáº·c há»§y Ä‘Æ¡n cÅ© trÆ°á»›c.", show_alert=True)
            return True

        if _is_ctt_store_product(p):
            return await _begin_ctt_checkout_collection(query, context, prod_id, qty, "qr")
        
        requires_gmail = p.get('requires_gmail', False)
        
        if not requires_gmail:
            # Auto product - pháº£i cÃ³ stock vá»›i lock protection
            # NHÆ¯NG skip cho resell products (mua real-time tá»« API)
            if not p.get('is_supplier_source_resell'):
                lock = await get_product_lock(prod_id)
                async with lock:
                    available_count = int(get_local_stock_available_count(products.get(prod_id)) or 0)
                    if available_count < qty:
                        await safe_answer(query, "âŒ Sá»‘ lÆ°á»£ng yÃªu cáº§u vÆ°á»£t quÃ¡ tá»“n kho!", show_alert=True)
                        return True
                    # Stock check passed - proceed to create QR (stock will be reserved in pending_orders)
            # Resell products: Skip local stock check, sáº½ mua tá»« SupplierSource khi thanh toÃ¡n
        else:
            # Manual product - check pending limit
            pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == prod_id)
            max_pending = p.get('max_pending_orders', 10)
            
            if pending_count >= max_pending:
                await safe_answer(query, f"<tg-emoji emoji-id=\"5447644880824181073\">âš ï¸</tg-emoji> Admin Ä‘ang báº­n ({pending_count}/{max_pending})!", show_alert=True)
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


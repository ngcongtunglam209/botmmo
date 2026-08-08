
# ==============================================================================
#  HELPER FUNCTIONS MỚI (FIX LỖI THIẾU HÀM)
# ==============================================================================

TELEGRAM_CALLBACK_ANSWER_LIMIT = 200
TELEGRAM_COMMAND_DESCRIPTION_LIMIT = 256


_MOJIBAKE_CP1252_REVERSE = {
    "\u20ac": 0x80,
    "\u201a": 0x82,
    "\u0192": 0x83,
    "\u201e": 0x84,
    "\u2026": 0x85,
    "\u2020": 0x86,
    "\u2021": 0x87,
    "\u02c6": 0x88,
    "\u2030": 0x89,
    "\u0160": 0x8A,
    "\u2039": 0x8B,
    "\u0152": 0x8C,
    "\u017d": 0x8E,
    "\u2018": 0x91,
    "\u2019": 0x92,
    "\u201c": 0x93,
    "\u201d": 0x94,
    "\u2022": 0x95,
    "\u2013": 0x96,
    "\u2014": 0x97,
    "\u02dc": 0x98,
    "\u2122": 0x99,
    "\u0161": 0x9A,
    "\u203a": 0x9B,
    "\u0153": 0x9C,
    "\u017e": 0x9E,
    "\u0178": 0x9F,
}

_MOJIBAKE_SUSPICIOUS_CHARS = set(
    "\u00a1\u00a2\u00a3\u00a4\u00a5\u00a6\u00a7\u00a8\u00a9\u00aa\u00ab\u00ac\u00ae\u00af"
    "\u00b0\u00b1\u00b2\u00b3\u00b4\u00b5\u00b6\u00b7\u00b8\u00b9\u00ba\u00bb\u00bc\u00bd\u00be\u00bf"
    "\u00c2\u00c3\u00c4\u00c5\u00c6\u00d0\u00d1\u00d7\u00d8\u00de\u00df"
    "\u00e2\u00e3\u00e4\u00e5\u00e6\u00f0\u00fe"
    "\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192"
    "\u2013\u2014\u2018\u2019\u201a\u201c\u201d\u201e\u2020\u2021\u2022\u2026\u2030\u2039\u203a"
    "\u20ac\u2122\ufffd"
)


def _mojibake_score(text: str) -> int:
    score = 0
    for ch in str(text or ""):
        codepoint = ord(ch)
        if 0x80 <= codepoint <= 0x9F:
            score += 3
        elif ch in _MOJIBAKE_SUSPICIOUS_CHARS:
            score += 2
    return score


def _repair_mojibake_once(text: str):
    raw_bytes = bytearray()
    for ch in str(text or ""):
        codepoint = ord(ch)
        if codepoint <= 0xFF:
            raw_bytes.append(codepoint)
            continue

        recovered_byte = _MOJIBAKE_CP1252_REVERSE.get(ch)
        if recovered_byte is None:
            return None
        raw_bytes.append(recovered_byte)

    try:
        return bytes(raw_bytes).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _repair_mojibake_token(token: str) -> str:
    best = str(token or "")
    best_score = _mojibake_score(best)
    if best_score <= 0:
        return best

    for _ in range(4):
        candidate = _repair_mojibake_once(best)
        if not candidate:
            break

        candidate_score = _mojibake_score(candidate)
        if candidate_score > best_score or candidate == best:
            break

        best = candidate
        best_score = candidate_score
        if candidate_score == 0:
            break

    return best


def _repair_mojibake_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text

    if _mojibake_score(text) <= 0:
        return text

    return re.sub(r"\S+", lambda match: _repair_mojibake_token(match.group(0)), text)


def _sanitize_plain_telegram_text(text: str, max_length: int | None = None, strip_emojis: bool = True):
    if text is None:
        return None

    cleaned = _repair_mojibake_text(str(text))
    cleaned = strip_tg_emoji(cleaned)
    cleaned = re.sub(r"</?[^>]+>", "", cleaned)
    cleaned = html.unescape(cleaned).strip()
    if strip_emojis:
        cleaned = _strip_generic_emojis(cleaned)
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned or None


def _normalize_bot_command_specs(commands):
    try:
        from telegram import BotCommand
    except (TelegramError, ValueError, KeyError, AttributeError, ImportError):
        BotCommand = None

    if not isinstance(commands, (list, tuple)):
        return commands, False

    changed = False
    normalized = []

    for item in commands:
        if BotCommand is not None and isinstance(item, BotCommand):
            clean_description = _sanitize_plain_telegram_text(
                getattr(item, "description", ""),
                max_length=TELEGRAM_COMMAND_DESCRIPTION_LIMIT,
                strip_emojis=True,
            )
            if clean_description != getattr(item, "description", ""):
                changed = True
                normalized.append(BotCommand(item.command, clean_description or "Command"))
            else:
                normalized.append(item)
            continue

        if isinstance(item, tuple) and len(item) == 2:
            command, description = item
            clean_description = _sanitize_plain_telegram_text(
                description,
                max_length=TELEGRAM_COMMAND_DESCRIPTION_LIMIT,
                strip_emojis=True,
            )
            if clean_description != description:
                changed = True
            normalized.append((command, clean_description or "Command"))
            continue

        if isinstance(item, list) and len(item) == 2:
            command, description = item
            clean_description = _sanitize_plain_telegram_text(
                description,
                max_length=TELEGRAM_COMMAND_DESCRIPTION_LIMIT,
                strip_emojis=True,
            )
            if clean_description != description:
                changed = True
            normalized.append([command, clean_description or "Command"])
            continue

        if isinstance(item, dict) and "command" in item and "description" in item:
            clean_description = _sanitize_plain_telegram_text(
                item.get("description"),
                max_length=TELEGRAM_COMMAND_DESCRIPTION_LIMIT,
                strip_emojis=True,
            )
            if clean_description != item.get("description"):
                changed = True
                updated = dict(item)
                updated["description"] = clean_description or "Command"
                normalized.append(updated)
            else:
                normalized.append(item)
            continue

        normalized.append(item)

    if not changed:
        return commands, False
    if isinstance(commands, tuple):
        return tuple(normalized), True
    return normalized, True


async def safe_answer(query, text=None, show_alert=False):
    """
    FIX BUG: Safe wrapper for callback queries to prevent 'Query is too old' crashes
    """
    try:
        cb_text = _sanitize_plain_telegram_text(
            text,
            max_length=TELEGRAM_CALLBACK_ANSWER_LIMIT,
            strip_emojis=True,
        )
        await query.answer(text=cb_text, show_alert=show_alert)
    except BadRequest as e:
        msg = str(e).lower()
        if (
            "query is too old" in msg
            or "response timeout expired" in msg
            or "query id is invalid" in msg
        ):
            return  # Ignore expired/invalid callback queries
        # Instead of raising we should just log the error and allow code to continue
        logger.warning(f"safe_answer BadRequest: {e}")
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"safe_answer Exception: {e}")

async def safe_edit_message(query, text=None, caption=None, reply_markup=None, parse_mode='HTML', alert_text=None):
    """
    FIX BUG: Safe wrapper để edit message và tự động bắt lỗi "Message is not modified"
    Hỗ trợ cả CallbackQuery và Message object (từ send_message)
    """
    try:
        if caption is not None:
            # Edit caption
            if hasattr(query, 'edit_message_caption'):
                await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await query.edit_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                
        elif text is not None:
            # Edit text
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                await query.edit_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                
        else:
            # Chỉ edit reply_markup
            if hasattr(query, 'edit_message_reply_markup'):
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            else:
                await query.edit_reply_markup(reply_markup=reply_markup)
                
        return True
    except BadRequest as e:
        err = str(e or "")
        err_low = err.lower()

        if "message is not modified" in err_low:
            # Message không thay đổi - Không cần log lỗi, chỉ cần answer query nếu là CallbackQuery
            if alert_text and hasattr(query, 'answer'):
                await safe_answer(query, alert_text, show_alert=False)
            return False

        if text is not None and _is_message_too_long_error(err_low):
            return await _handle_long_edit_fallback(
                query,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )

        # Fallback 1: Message gốc là media + caption, nhưng code đang edit text.
        if text is not None and "there is no text in the message to edit" in err_low:
            try:
                if hasattr(query, 'edit_message_caption'):
                    await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    return True
            except BadRequest as e2:
                err2 = str(e2 or "").lower()
                # Nếu không edit caption được thì gửi message mới để user luôn thấy phản hồi
                if "caption" in err2 or "message to edit not found" in err2:
                    if getattr(query, "message", None):
                        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                        return True
                raise

        # Fallback 2: Message gốc là text, nhưng code đang edit caption.
        if caption is not None and ("there is no caption in the message to edit" in err_low or "message has no caption" in err_low):
            try:
                if hasattr(query, 'edit_message_text'):
                    await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    return True
            except BadRequest as e2:
                err2 = str(e2 or "").lower()
                if "text" in err2 or "message to edit not found" in err2:
                    if getattr(query, "message", None):
                        await query.message.reply_text(caption, reply_markup=reply_markup, parse_mode=parse_mode)
                        return True
                raise

        if any(marker in err_low for marker in ("document_invalid", "entity", "parse")):
            fallback_text = text if text is not None else caption
            plain_fallback = html.escape(_plain_text_preserve_emoji(fallback_text), quote=False)
            if plain_fallback:
                try:
                    if text is not None:
                        if hasattr(query, 'edit_message_text'):
                            await query.edit_message_text(text=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                        else:
                            await query.edit_text(text=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                    elif caption is not None:
                        if hasattr(query, 'edit_message_caption'):
                            await query.edit_message_caption(caption=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                        else:
                            await query.edit_caption(caption=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                    return True
                except (BadRequest, TelegramError):
                    if getattr(query, "message", None):
                        await query.message.reply_text(plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                        return True

        # Lỗi khác - raise để xử lý
        raise
    except TelegramError as e:
        err_low = str(e or "").lower()
        if text is not None and _is_message_too_long_error(err_low):
            return await _handle_long_edit_fallback(
                query,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        if any(marker in err_low for marker in ("document_invalid", "entity", "parse")):
            fallback_text = text if text is not None else caption
            plain_fallback = html.escape(_plain_text_preserve_emoji(fallback_text), quote=False)
            if plain_fallback:
                if text is not None:
                    if hasattr(query, 'edit_message_text'):
                        await query.edit_message_text(text=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                    else:
                        await query.edit_text(text=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                elif caption is not None:
                    if hasattr(query, 'edit_message_caption'):
                        await query.edit_message_caption(caption=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                    else:
                        await query.edit_caption(caption=plain_fallback, reply_markup=reply_markup, parse_mode=parse_mode)
                return True
        raise

async def safe_send_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
    """
    Send message safely to avoid crashing handler when user never started private chat.
    Returns sent message object or None on send failure.
    """
    text = _repair_mojibake_text(text) if isinstance(text, str) else text
    kwargs = dict(kwargs)
    kwargs["reply_markup"] = _upgrade_reply_markup_to_premium(kwargs.get("reply_markup"))
    try:
        return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except (Forbidden, BadRequest) as e:
        err_low = str(e or "").lower()
        if any(marker in err_low for marker in ("document_invalid", "entity", "parse")):
            plain_text = _plain_text_preserve_emoji(text)
            if plain_text:
                retry_kwargs = dict(kwargs)
                retry_kwargs.pop("entities", None)
                retry_kwargs.pop("caption_entities", None)
                if "parse_mode" in retry_kwargs:
                    plain_text = html.escape(plain_text, quote=False)
                    retry_kwargs["parse_mode"] = ParseMode.HTML
                try:
                    return await context.bot.send_message(chat_id=chat_id, text=plain_text, **retry_kwargs)
                except (Forbidden, BadRequest):
                    retry_kwargs.pop("parse_mode", None)
                    try:
                        return await context.bot.send_message(chat_id=chat_id, text=_plain_text_preserve_emoji(text), **retry_kwargs)
                    except (Forbidden, BadRequest):
                        pass
        logger.warning(f"Cannot send message to chat_id={chat_id}: {e}")
        return None

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_TEXT_LIMIT = 4096

def _is_caption_too_long_error(err_text: str) -> bool:
    text = str(err_text or "").lower()
    return (
        "media_caption_too_long" in text
        or "caption_too_long" in text
        or "caption is too long" in text
        or "message caption is too long" in text
    )

def _is_message_too_long_error(err_text: str) -> bool:
    text = str(err_text or "").lower()
    return (
        "message is too long" in text
        or "message_too_long" in text
        or "text is too long" in text
        or "message text is too long" in text
    )

def _is_entity_parse_error(err_text: str) -> bool:
    text = str(err_text or "").lower()
    return (
        "entity_text_invalid" in text
        or "can't parse entities" in text
        or "unsupported start tag" in text
        or "entity begins" in text
        or "parse entities" in text
        or ("entity" in text and "invalid" in text)
        or ("parse" in text and "entity" in text)
    )

async def _handle_long_edit_fallback(query, payload_text, reply_markup=None, parse_mode='HTML'):
    target_message = getattr(query, "message", None) or query
    bot = getattr(target_message, "get_bot", lambda: None)()
    chat_id = getattr(target_message, "chat_id", None)
    reply_to_message_id = getattr(target_message, "message_id", None)

    if bot is None or chat_id is None or not isinstance(payload_text, str) or not payload_text.strip():
        return False

    notice_text = (
        "<tg-emoji emoji-id=\"5350481781306958339\">📚</tg-emoji> "
        "<b>Nội dung hơi dài nên mình đã gửi chi tiết ở các tin nhắn bên dưới.</b>"
    )
    payload_text = _repair_mojibake_text(payload_text)
    reply_markup = _upgrade_reply_markup_to_premium(reply_markup)
    try:
        if hasattr(query, 'edit_message_text'):
            await query.edit_message_text(text=notice_text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif hasattr(query, 'edit_text'):
            await query.edit_text(text=notice_text, reply_markup=reply_markup, parse_mode=parse_mode)
    except (TelegramError, ValueError, KeyError, AttributeError):
        pass

    await _send_caption_overflow_as_messages(
        bot,
        chat_id,
        payload_text,
        parse_mode=parse_mode,
        reply_to_message_id=reply_to_message_id,
    )
    return True

def _plain_text_chunks(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    plain = str(text or "").strip()
    if not plain:
        return []
    chunks = []
    remaining = plain
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        chunk = remaining[:split_at].strip()
        if not chunk:
            chunk = remaining[:limit]
            split_at = limit
        chunks.append(chunk)
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks

async def _send_caption_overflow_as_messages(bot, chat_id, caption_text, parse_mode=None, reply_to_message_id=None):
    if chat_id is None or not isinstance(caption_text, str) or not caption_text.strip():
        return

    send_kwargs = {"chat_id": chat_id, "text": caption_text}
    if parse_mode is not None:
        send_kwargs["parse_mode"] = parse_mode
    if reply_to_message_id:
        send_kwargs["reply_to_message_id"] = reply_to_message_id

    try:
        await bot.send_message(**send_kwargs)
        return
    except (BadRequest, TelegramError, ValueError, KeyError, AttributeError) as e:
        logger.warning(f"[caption_overflow] rich-text follow-up failed, applying chunk validation: {e}")

    # FIX BUG Mảng 4: Áp dụng html.escape để chống lỗi cắt tag giữa chừng
    # Thay vì strip toàn bộ tag bằng _plain_text_preserve_emoji, ta giữ nguyên và escape nó
    # Hoặc nếu là text thường, escape để ngăn telegram parser bắt lỗi.
    for idx, chunk in enumerate(_plain_text_chunks(caption_text)):
        if parse_mode in ('HTML', getattr(ParseMode, 'HTML', 'HTML')):
            # Ngăn lỗi bằng cách escape toàn bộ HTML ở chế độ fallback
            final_chunk = html.escape(chunk)
        else:
            final_chunk = chunk
            
        chunk_kwargs = {"chat_id": chat_id, "text": final_chunk}
        if parse_mode is not None:
            chunk_kwargs["parse_mode"] = parse_mode
        if idx == 0 and reply_to_message_id:
            chunk_kwargs["reply_to_message_id"] = reply_to_message_id
            
        try:
            await bot.send_message(**chunk_kwargs)
        except (BadRequest, TelegramError, ValueError, KeyError, AttributeError) as chunk_error:
            logger.warning(f"[caption_overflow] escaped follow-up failed on chunk {idx}: {chunk_error}")
            # Fallback level 2: remove parse_mode
            chunk_kwargs.pop("parse_mode", None)
            try:
                await bot.send_message(**chunk_kwargs)
            except Exception as e2:
                logger.warning(f"[caption_overflow] absolute fallback failed: {e2}")
            break

def _strip_generic_emojis(text: str, replacement: str = " ") -> str:
    if not isinstance(text, str) or not text:
        return text
    keycap_regex = re.compile(r'([0-9#*])\ufe0f?\u20e3')
    normalized = keycap_regex.sub(lambda match: match.group(1), text)
    normalized = GENERIC_EMOJI_REGEX.sub(replacement, normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()

def _plain_text_preserve_emoji(text: str) -> str:
    plain = _repair_mojibake_text(str(text or ""))
    plain = strip_tg_emoji(plain)
    plain = re.sub(r"(?i)<br\s*/?>", "\n", plain)
    plain = re.sub(r"(?i)</?(?:p|div|li|ul|ol|blockquote|pre)\b[^>]*>", "\n", plain)
    plain = re.sub(r"</?[^>]+>", "", plain)
    plain = html.unescape(plain)
    plain = re.sub(r"[ \t]+\n", "\n", plain)
    plain = re.sub(r"\n[ \t]+", "\n", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()

def _plain_no_emoji_text(text: str) -> str:
    plain = _plain_text_preserve_emoji(text)
    return _strip_generic_emojis(plain)

def _find_first_premium_emoji(text: str):
    if not isinstance(text, str) or not text:
        return None, None

    text = _repair_mojibake_text(text)

    # Check if there's already an explicit <tg-emoji> tag in the text
    explicit_match = re.search(r'<tg-emoji[^>]*emoji-id=["\']?(\d+)["\']?[^>]*>(.*?)</tg-emoji>', text)
    if explicit_match:
        emoji_id = explicit_match.group(1)
        return "", emoji_id

    for match in GENERIC_EMOJI_REGEX.finditer(text):
        glyph = match.group(0)
        emoji_id = _resolve_premium_emoji_id(glyph)
        if emoji_id:
            return glyph, emoji_id
    return None, None

def _clean_inline_keyboard_button_text(text: str) -> str:
    repaired_text = _repair_mojibake_text(str(text or ""))
    cleaned = _strip_generic_emojis(strip_tg_emoji(repaired_text))
    if cleaned:
        return cleaned
    fallback = _plain_no_emoji_text(repaired_text)
    if fallback:
        return fallback
    return "Chon"

def _infer_inline_keyboard_button_icon_id(button_text: str, payload: dict | None = None):
    payload = payload or {}
    normalized_text = _clean_inline_keyboard_button_text(button_text).lower()
    callback_data = str(payload.get("callback_data") or "").lower()
    url = str(payload.get("url") or "").lower()
    combined = " ".join(part for part in (normalized_text, callback_data, url) if part)

    if normalized_text.isdigit():
        return _resolve_premium_emoji_id("🔢")

    keyword_rules = [
        (r"\b(quay lai|back|menu chinh|main menu|menu)\b", "⬅️"),
        (r"\b(xem them|cu hon|moi hon|lich su|history|danh sach|list|ds)\b", "📜"),
        (r"\b(huy|khong|no|dong|xoa|delete|refund|reject|close|stop|ignore)\b", "❌"),
        (r"\b(duyet|co|yes|xac nhan|done|accept|approve|keep|use)\b", "✅"),
        (r"\b(chat|support|reply|phan hoi|lien he|message|hoi)\b", "💬"),
        (r"\b(mua|order|cart|store|shop|checkout)\b", "🛒"),
        (r"\b(stock|kho|product|prod|san pham|hang)\b", "📦"),
        (r"\b(qr|usdt|binance|wallet|balance|bal|money|price|gia|nap|rut|pay|thanh toan)\b", "💰"),
        (r"\b(add|them|tao|create|new|register|dang ky)\b", "➕"),
        (r"\b(edit|sua|viet|nhap|name|ten|mo ta|field)\b", "✍️"),
        (r"\b(email|gmail|mail)\b", "📧"),
        (r"\b(api|docs|endpoint|link|url|open)\b", "🌐"),
        (r"\b(ai|bot)\b", "🤖"),
    ]

    for pattern, glyph in keyword_rules:
        if re.search(pattern, combined):
            return _resolve_premium_emoji_id(glyph)

    if url:
        return _resolve_premium_emoji_id("🌐")
    return _resolve_premium_emoji_id("ℹ️")

def _upgrade_inline_keyboard_button(button):
    try:
        from telegram import InlineKeyboardButton
    except (TelegramError, ValueError, KeyError, AttributeError, ImportError):
        return button

    if not isinstance(button, InlineKeyboardButton):
        return button

    payload = button.to_dict()
    current_api_kwargs = dict(getattr(button, "api_kwargs", {}) or {})
    existing_icon_id = current_api_kwargs.get("icon_custom_emoji_id") or payload.get("icon_custom_emoji_id")
    button_text = _repair_mojibake_text(str(payload.get("text", "") or getattr(button, "text", "") or ""))
    _glyph, detected_icon_id = _find_first_premium_emoji(button_text)
    emoji_id = existing_icon_id or detected_icon_id or _infer_inline_keyboard_button_icon_id(button_text, payload)
    cleaned_text = _clean_inline_keyboard_button_text(button_text)

    if cleaned_text == button_text and emoji_id == existing_icon_id:
        return button

    payload["text"] = cleaned_text
    if emoji_id:
        payload["icon_custom_emoji_id"] = emoji_id
    return InlineKeyboardButton.de_json(payload, bot=None)

def _upgrade_reply_markup_to_premium(reply_markup):
    try:
        from telegram import InlineKeyboardMarkup
    except (TelegramError, ValueError, KeyError, AttributeError, ImportError):
        return reply_markup

    if not isinstance(reply_markup, InlineKeyboardMarkup):
        return reply_markup

    changed = False
    upgraded_rows = []
    for row in reply_markup.inline_keyboard:
        upgraded_row = []
        for button in row:
            upgraded_button = _upgrade_inline_keyboard_button(button)
            if upgraded_button is not button:
                changed = True
            upgraded_row.append(upgraded_button)
        upgraded_rows.append(upgraded_row)

    if not changed:
        return reply_markup
    return InlineKeyboardMarkup(upgraded_rows)

def _patch_bot_send_message():
    from telegram import Bot, CallbackQuery, Message
    try:
        from telegram.ext import ExtBot
    except (TelegramError, ValueError, KeyError, AttributeError):
        ExtBot = None

    def _extract_field(args, kwargs, field_name, arg_index):
        if field_name in kwargs:
            return kwargs.get(field_name)
        if len(args) > arg_index:
            return args[arg_index]
        return None

    def _inject_field(args, kwargs, field_name, arg_index, value):
        args_list = list(args)
        kwargs_copy = dict(kwargs)
        if field_name in kwargs_copy:
            kwargs_copy[field_name] = value
        elif len(args_list) > arg_index:
            args_list[arg_index] = value
        else:
            kwargs_copy[field_name] = value
        return tuple(args_list), kwargs_copy

    def _strip_tg_payload(args, kwargs, field_name, arg_index):
        text = _extract_field(args, kwargs, field_name, arg_index)
        if not isinstance(text, str):
            return args, kwargs
        plain = _plain_text_preserve_emoji(text)
        return _inject_field(args, kwargs, field_name, arg_index, plain)

    def _is_unset_parse_mode(parse_mode) -> bool:
        # PTB often passes parse_mode as DefaultValue(None), not literal None.
        return parse_mode is None or str(parse_mode) == "DefaultValue(None)"

    def _prepare_reply_markup(kwargs):
        reply_markup = kwargs.get("reply_markup")
        if reply_markup is None:
            return kwargs, False
        upgraded_markup = _upgrade_reply_markup_to_premium(reply_markup)
        if upgraded_markup is reply_markup:
            return kwargs, False
        new_kwargs = dict(kwargs)
        new_kwargs["reply_markup"] = upgraded_markup
        return new_kwargs, True

    def _prepare_payload(args, kwargs, field_name, arg_index):
        if not field_name:
            return args, kwargs, False

        text = _extract_field(args, kwargs, field_name, arg_index)
        if not isinstance(text, str) or not text:
            return args, kwargs, False

        repaired_text = _repair_mojibake_text(text)
        new_args, new_kwargs = args, dict(kwargs)
        changed = repaired_text != text
        if changed:
            new_args, new_kwargs = _inject_field(args, kwargs, field_name, arg_index, repaired_text)

        entity_field_name = "caption_entities" if field_name == "caption" else "entities"
        if new_kwargs.get(entity_field_name):
            return new_args, new_kwargs, changed

        parse_mode = new_kwargs.get("parse_mode")
        effective_parse_mode = None if _is_unset_parse_mode(parse_mode) else parse_mode
        if _is_markdown_mode(effective_parse_mode):
            return new_args, new_kwargs, changed

        allow_auto_html = _allow_auto_html_for_text(effective_parse_mode, repaired_text)
        source_text = repaired_text
        if effective_parse_mode is None and not allow_auto_html:
            # Raw text has special chars like < or &. Escape first so we can safely
            # switch to HTML parse mode when adding premium emoji tags.
            if not GENERIC_EMOJI_REGEX.search(source_text):
                return new_args, new_kwargs, changed
            source_text = html.escape(source_text, quote=False)

        upgraded = upgrade_text_to_premium_emoji(source_text)
        if upgraded != repaired_text:
            new_args, new_kwargs = _inject_field(new_args, new_kwargs, field_name, arg_index, upgraded)
            changed = True

        if _is_unset_parse_mode(new_kwargs.get("parse_mode")):
            final_text = _extract_field(new_args, new_kwargs, field_name, arg_index)
            if isinstance(final_text, str) and HTML_INTENT_REGEX.search(final_text):
                new_kwargs["parse_mode"] = ParseMode.HTML
                changed = True

        return new_args, new_kwargs, changed

    async def _call_with_fallback(original_func, method_name, field_name, arg_index, bot_self, *args, **kwargs):
        original_args = args
        original_kwargs = dict(kwargs)
        call_kwargs, markup_transformed = _prepare_reply_markup(kwargs)
        call_args, call_kwargs, payload_transformed = _prepare_payload(args, call_kwargs, field_name, arg_index)
        transformed = markup_transformed or payload_transformed
        
        if method_name and method_name.endswith("reply_html") and "parse_mode" in call_kwargs:
            del call_kwargs["parse_mode"]
            
        try:
            return await original_func(bot_self, *call_args, **call_kwargs)
        except TypeError as e:
            if "unexpected keyword argument 'parse_mode'" in str(e) and "parse_mode" in call_kwargs:
                del call_kwargs["parse_mode"]
                return await original_func(bot_self, *call_args, **call_kwargs)
            raise e
        except TelegramError as e:
            err_str = str(e)
            err_low = err_str.lower()

            # Retry with original payload if auto-html transform caused parse issues.
            if transformed and _is_entity_parse_error(err_low):
                try:
                    return await original_func(bot_self, *original_args, **original_kwargs)
                except TelegramError:
                    pass

            if markup_transformed and any(marker in err_low for marker in ("button", "reply markup", "custom emoji", "icon_custom_emoji_id")):
                try:
                    return await original_func(bot_self, *original_args, **original_kwargs)
                except TelegramError:
                    pass

            # Retry with stripped tg-emoji if custom emoji payload fails.
            field_text = _extract_field(call_args, call_kwargs, field_name, arg_index)
            if field_text and "<tg-emoji" in str(field_text):
                stripped_args, stripped_kwargs = _strip_tg_payload(call_args, call_kwargs, field_name, arg_index)
                try:
                    return await original_func(bot_self, *stripped_args, **stripped_kwargs)
                except TelegramError:
                    pass

            # Retry media sends without caption, then send the full caption as
            # a follow-up text message so the flow continues instead of failing.
            if field_name == "caption" and _is_caption_too_long_error(err_low) and method_name.split(".")[-1].startswith("send_"):
                caption_text = _extract_field(call_args, call_kwargs, field_name, arg_index)
                no_caption_args, no_caption_kwargs = _inject_field(call_args, call_kwargs, field_name, arg_index, None)
                try:
                    sent_media = await original_func(bot_self, *no_caption_args, **no_caption_kwargs)
                    chat_id = _extract_field(call_args, call_kwargs, "chat_id", 0)
                    reply_to_message_id = getattr(sent_media, "message_id", None)
                    await _send_caption_overflow_as_messages(
                        bot_self,
                        chat_id,
                        caption_text,
                        parse_mode=call_kwargs.get("parse_mode"),
                        reply_to_message_id=reply_to_message_id,
                    )
                    return sent_media
                except TelegramError:
                    pass

            # Last-resort fallback for malformed HTML/Markdown payloads:
            # send an escaped version instead of crashing the caller.
            if _is_entity_parse_error(err_low):
                plain_text = _extract_field(call_args, call_kwargs, field_name, arg_index)
                if isinstance(plain_text, str) and plain_text:
                    sanitized = strip_tg_emoji(plain_text)
                    sanitized = re.sub(r"(?is)<script.*?</script>", "", sanitized)
                    sanitized = re.sub(r"(?is)<style.*?</style>", "", sanitized)
                    
                    # FIX BUG Mảng 4: Áp dụng html.escape để chống lỗi tag
                    # Nếu parse entity lỗi (có thể do chunk cắt trúng thẻ HTML), 
                    # ta dùng html.escape để hiện nguyên mẫu chứ không xóa đi
                    sanitized = html.escape(sanitized)
                    
                    if not sanitized:
                        sanitized = "[message omitted due to parse error]"
                    if len(sanitized) > TELEGRAM_TEXT_LIMIT:
                        sanitized = sanitized[:TELEGRAM_TEXT_LIMIT - 1] + "…"
                    safe_args, safe_kwargs = _inject_field(call_args, call_kwargs, field_name, arg_index, sanitized)
                    
                    safe_kwargs["parse_mode"] = getattr(ParseMode, 'HTML', 'HTML')
                    safe_kwargs.pop("entities", None)
                    safe_kwargs.pop("caption_entities", None)
                    try:
                        return await original_func(bot_self, *safe_args, **safe_kwargs)
                    except TelegramError as try2_e:
                        logger.warning(f"Fallback with html.escape failed: {try2_e}, sending as plain text.")
                        safe_kwargs.pop("parse_mode", None)
                        try:
                            return await original_func(bot_self, *safe_args, **safe_kwargs)
                        except TelegramError:
                            pass

            logger.debug(f"[{method_name}] send failed after fallback: {err_str}")
            raise

    def _patch_one_class(target_cls):
        if target_cls is None or getattr(target_cls, "_premium_emoji_patch_applied", False):
            return

        specs = [
            ("send_message", "text", 1),
            ("edit_message_text", "text", 0),
            ("edit_message_reply_markup", None, 0),
            ("send_photo", "caption", 2),
            ("edit_message_caption", "caption", 0),
            ("send_document", "caption", 2),
            ("send_video", "caption", 2),
            ("send_animation", "caption", 2),
            ("send_audio", "caption", 2),
            ("send_voice", "caption", 2),
        ]

        for method_name, field_name, arg_index in specs:
            # Patch only methods defined on this class to avoid double-wrapping
            # inherited methods (e.g. ExtBot inheriting already patched Bot methods).
            original = target_cls.__dict__.get(method_name)
            if original is None:
                continue

            async def _wrapped(self, *args, __orig=original, __m=method_name, __f=field_name, __i=arg_index, **kwargs):
                return await _call_with_fallback(__orig, f"{target_cls.__name__}.{__m}", __f, __i, self, *args, **kwargs)

            setattr(target_cls, method_name, _wrapped)

        target_cls._premium_emoji_patch_applied = True

    def _patch_message_surface_methods():
        if Message is None or getattr(Message, "_premium_emoji_surface_patch_applied", False):
            return

        specs = [
            ("reply_text", "text", 0),
            ("reply_html", "text", 0),
            ("reply_photo", "caption", 1),
            ("reply_document", "caption", 1),
            ("reply_video", "caption", 2),
            ("reply_animation", "caption", 4),
            ("reply_audio", "caption", 1),
            ("reply_voice", "caption", 1),
            ("edit_text", "text", 0),
            ("edit_caption", "caption", 0),
            ("edit_reply_markup", None, 0),
        ]

        for method_name, field_name, arg_index in specs:
            original = Message.__dict__.get(method_name)
            if original is None:
                continue

            async def _wrapped(self, *args, __orig=original, __m=method_name, __f=field_name, __i=arg_index, **kwargs):
                return await _call_with_fallback(__orig, f"Message.{__m}", __f, __i, self, *args, **kwargs)

            setattr(Message, method_name, _wrapped)

        Message._premium_emoji_surface_patch_applied = True

    def _patch_callback_query_methods():
        if CallbackQuery is None or getattr(CallbackQuery, "_premium_emoji_patch_applied", False):
            return

        specs = [
            ("edit_message_text", "text", 0),
            ("edit_message_caption", "caption", 0),
            ("edit_message_reply_markup", None, 0),
        ]

        for method_name, field_name, arg_index in specs:
            original = CallbackQuery.__dict__.get(method_name)
            if original is None:
                continue

            async def _wrapped(self, *args, __orig=original, __m=method_name, __f=field_name, __i=arg_index, **kwargs):
                return await _call_with_fallback(__orig, f"CallbackQuery.{__m}", __f, __i, self, *args, **kwargs)

            setattr(CallbackQuery, method_name, _wrapped)

        CallbackQuery._premium_emoji_patch_applied = True

    _patch_one_class(Bot)
    _patch_one_class(ExtBot)
    _patch_message_surface_methods()
    _patch_callback_query_methods()

_patch_bot_send_message()


def _patch_plain_surface_methods():
    from telegram import Bot
    try:
        from telegram.ext import ExtBot
    except (TelegramError, ValueError, KeyError, AttributeError):
        ExtBot = None

    def _extract_field(args, kwargs, field_name, arg_index):
        if field_name in kwargs:
            return kwargs.get(field_name)
        if len(args) > arg_index:
            return args[arg_index]
        return None

    def _inject_field(args, kwargs, field_name, arg_index, value):
        args_list = list(args)
        kwargs_copy = dict(kwargs)
        if field_name in kwargs_copy:
            kwargs_copy[field_name] = value
        elif len(args_list) > arg_index:
            args_list[arg_index] = value
        else:
            kwargs_copy[field_name] = value
        return tuple(args_list), kwargs_copy

    def _patch_one_class(target_cls):
        if target_cls is None or getattr(target_cls, "_plain_surface_patch_applied", False):
            return

        original_answer = target_cls.__dict__.get("answer_callback_query")
        if original_answer is not None:
            async def _answer_wrapped(self, *args, __orig=original_answer, **kwargs):
                raw_text = _extract_field(args, kwargs, "text", 1)
                normalized = _sanitize_plain_telegram_text(
                    raw_text,
                    max_length=TELEGRAM_CALLBACK_ANSWER_LIMIT,
                    strip_emojis=True,
                )
                call_args, call_kwargs = _inject_field(args, kwargs, "text", 1, normalized)
                return await __orig(self, *call_args, **call_kwargs)

            setattr(target_cls, "answer_callback_query", _answer_wrapped)

        original_set_commands = target_cls.__dict__.get("set_my_commands")
        if original_set_commands is not None:
            async def _set_commands_wrapped(self, *args, __orig=original_set_commands, **kwargs):
                raw_commands = _extract_field(args, kwargs, "commands", 0)
                normalized_commands, changed = _normalize_bot_command_specs(raw_commands)
                call_args, call_kwargs = args, kwargs
                if changed:
                    call_args, call_kwargs = _inject_field(args, kwargs, "commands", 0, normalized_commands)
                return await __orig(self, *call_args, **call_kwargs)

            setattr(target_cls, "set_my_commands", _set_commands_wrapped)

        target_cls._plain_surface_patch_applied = True

    _patch_one_class(Bot)
    _patch_one_class(ExtBot)


_patch_plain_surface_methods()


def _patch_message_edit_methods():
    try:
        from telegram import CallbackQuery, Message
    except (TelegramError, ValueError, KeyError, AttributeError):
        return

    def _extract_primary(args, kwargs, key):
        if key in kwargs:
            return kwargs.get(key)
        if args:
            return args[0]
        return None

    def _text_to_caption_kwargs(args, kwargs):
        payload = dict(kwargs)
        payload.pop("text", None)
        payload.pop("entities", None)
        payload.pop("link_preview_options", None)
        payload.pop("disable_web_page_preview", None)
        payload["caption"] = _extract_primary(args, kwargs, "text")
        return payload

    def _caption_to_text_kwargs(args, kwargs):
        payload = dict(kwargs)
        payload.pop("caption", None)
        payload.pop("caption_entities", None)
        payload.pop("show_caption_above_media", None)
        payload["text"] = _extract_primary(args, kwargs, "caption")
        return payload

    if not getattr(CallbackQuery, "_edit_fallback_patch_applied", False):
        original_cq_edit_text = CallbackQuery.edit_message_text
        original_cq_edit_caption = CallbackQuery.edit_message_caption

        async def _cq_edit_text(self, *args, **kwargs):
            try:
                return await original_cq_edit_text(self, *args, **kwargs)
            except TelegramError as e:
                err_low = str(e or "").lower()
                if "there is no text in the message to edit" not in err_low:
                    raise
                return await original_cq_edit_caption(self, **_text_to_caption_kwargs(args, kwargs))

        async def _cq_edit_caption(self, *args, **kwargs):
            try:
                return await original_cq_edit_caption(self, *args, **kwargs)
            except TelegramError as e:
                err_low = str(e or "").lower()
                if _is_caption_too_long_error(err_low):
                    caption_text = _extract_primary(args, kwargs, "caption")
                    payload = dict(kwargs)
                    payload["caption"] = None
                    sent = await original_cq_edit_caption(self, **payload)
                    if getattr(self, "message", None):
                        await _send_caption_overflow_as_messages(
                            self.message.get_bot(),
                            getattr(getattr(self, "message", None), "chat_id", None),
                            caption_text,
                            parse_mode=kwargs.get("parse_mode"),
                            reply_to_message_id=getattr(self.message, "message_id", None),
                        )
                    return sent
                if (
                    "there is no caption in the message to edit" not in err_low
                    and "message has no caption" not in err_low
                ):
                    raise
                return await original_cq_edit_text(self, **_caption_to_text_kwargs(args, kwargs))

        CallbackQuery.edit_message_text = _cq_edit_text
        CallbackQuery.edit_message_caption = _cq_edit_caption
        CallbackQuery._edit_fallback_patch_applied = True

    if not getattr(Message, "_edit_fallback_patch_applied", False):
        original_msg_edit_text = Message.edit_text
        original_msg_edit_caption = Message.edit_caption

        async def _msg_edit_text(self, *args, **kwargs):
            try:
                return await original_msg_edit_text(self, *args, **kwargs)
            except TelegramError as e:
                err_low = str(e or "").lower()
                if "there is no text in the message to edit" not in err_low:
                    raise
                return await original_msg_edit_caption(self, **_text_to_caption_kwargs(args, kwargs))

        async def _msg_edit_caption(self, *args, **kwargs):
            try:
                return await original_msg_edit_caption(self, *args, **kwargs)
            except TelegramError as e:
                err_low = str(e or "").lower()
                if _is_caption_too_long_error(err_low):
                    caption_text = _extract_primary(args, kwargs, "caption")
                    payload = dict(kwargs)
                    payload["caption"] = None
                    sent = await original_msg_edit_caption(self, **payload)
                    await _send_caption_overflow_as_messages(
                        self.get_bot(),
                        getattr(self, "chat_id", None),
                        caption_text,
                        parse_mode=kwargs.get("parse_mode"),
                        reply_to_message_id=getattr(self, "message_id", None),
                    )
                    return sent
                if (
                    "there is no caption in the message to edit" not in err_low
                    and "message has no caption" not in err_low
                ):
                    raise
                return await original_msg_edit_text(self, **_caption_to_text_kwargs(args, kwargs))

        Message.edit_text = _msg_edit_text
        Message.edit_caption = _msg_edit_caption
        Message._edit_fallback_patch_applied = True


_patch_message_edit_methods()


async def broadcast_send_message(bot, chat_id, text, **kwargs) -> str:
    """Gui mot tin trong vong broadcast. KHONG BAO GIO raise.

    Tra ve:
      "ok"      - da gui
      "blocked" - user chan bot (Forbidden), nen don khoi danh sach
      "invalid" - chat khong con ton tai (tai khoan da xoa), nen don
      "failed"  - loi khac, giu lai de lan sau thu tiep

    Cac vong broadcast truoc day chi bat Forbidden va vai loi kieu du lieu.
    BadRequest("Chat not found") - tai khoan da xoa - khong nam trong so do, nen
    dung mot nguoi nhan hong la ca task chet va TAT CA nguoi con lai khong nhan
    duoc gi. Mot nguoi nhan hong khong duoc phep dung ca dot gui.

    RetryAfter duoc ngu roi thu lai mot lan: coi flood-control la that bai se
    lam mat dung nhung user o giua dot gui, khi Telegram bat dau chan toc do.
    """
    for attempt in (1, 2):
        try:
            await bot.send_message(chat_id=chat_id, text=text, **kwargs)
            return "ok"
        except Forbidden:
            return "blocked"
        except RetryAfter as e:
            if attempt == 1:
                await asyncio.sleep(float(getattr(e, "retry_after", 1) or 1) + 0.5)
                continue
            return "failed"
        except BadRequest as e:
            reason = str(e).lower().replace("_", " ")
            if (
                "chat not found" in reason
                or "user is deactivated" in reason
                or "peer id invalid" in reason
                or "bot was blocked" in reason
            ):
                return "invalid"
            return "failed"
        except TelegramError:
            return "failed"
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            return "failed"
    return "failed"


def _is_tg_emoji_parse_error(error) -> bool:
    """True chi khi loi that su den tu the tg-emoji trong NOI DUNG tin nhan.

    Truoc day dieu kien la `'parse' in str(e).lower()`, ma Telegram cung dung
    tu "parse" cho loi ban phim: "Can't parse InlineKeyboardButton: text buttons
    are unallowed in the inline keyboard". Loi do bi doi thanh loi tg-emoji, roi
    gui lai y het ban phim hong -> lan hai that bai giong lan mot, va log chi ro
    vao tg-emoji nen khong ai nghi den ban phim. Loai han cac loi ban phim ra.
    """
    text = str(error).lower()
    if 'inlinekeyboard' in text or 'button' in text or 'reply_markup' in text:
        return False
    return 'document_invalid' in text or 'entity' in text or 'parse' in text


async def safe_reply_html(message, text, **kwargs):
    try:
        return await message.reply_html(text, **kwargs)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        if _is_tg_emoji_parse_error(e):
            logger.warning(f'[safe_reply_html] tg-emoji fallback: {e}')
            return await message.reply_html(_plain_text_preserve_emoji(text), **kwargs)
        raise

async def safe_reply_video_html(message, video, caption, **kwargs):
    try:
        return await message.reply_video(
            video=video,
            caption=caption,
            parse_mode=ParseMode.HTML,
            **kwargs,
        )
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        if _is_tg_emoji_parse_error(e):
            logger.warning(f'[safe_reply_video_html] tg-emoji fallback: {e}')
            return await message.reply_video(
                video=video,
                caption=_plain_text_preserve_emoji(caption),
                parse_mode=ParseMode.HTML,
                **kwargs,
            )
        raise

async def safe_bot_send_html(bot, chat_id, text, **kwargs):
    try:
        return await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, **kwargs)
    except (TelegramError, ValueError, KeyError, AttributeError) as e:
        if _is_tg_emoji_parse_error(e):
            logger.warning(f'[safe_bot_send_html] tg-emoji fallback: {e}')
            return await bot.send_message(chat_id, _plain_text_preserve_emoji(text), parse_mode=ParseMode.HTML, **kwargs)
        raise

def _normalize_github_video_url(url: str) -> str:
    if not url:
        return ""
    if "github.com/" in url and "/blob/" in url:
        return url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace("/blob/", "/")
    return url

async def send_start_welcome_with_video(update: Update, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    global WELCOME_VIDEO_FILE_ID

    menu_text = f"{t('hello', user_id=user.id, name=format_user_mention_html(user))}\n\n{get_main_menu_text(user_id=user.id)}"
    menu_kb = create_main_menu(user_id=user.id)
    msg = update.message
    if not msg:
        return

    if WELCOME_VIDEO_ENABLED and WELCOME_VIDEO_URL:
        try:
            video_source = WELCOME_VIDEO_FILE_ID or _normalize_github_video_url(WELCOME_VIDEO_URL)
            sent_video = await asyncio.wait_for(
                safe_reply_video_html(
                    msg,
                    video_source,
                    menu_text,
                    supports_streaming=True,
                    reply_markup=menu_kb,
                ),
                timeout=max(1.0, WELCOME_VIDEO_SEND_TIMEOUT),
            )
            if not WELCOME_VIDEO_FILE_ID and sent_video and getattr(sent_video, "video", None):
                WELCOME_VIDEO_FILE_ID = sent_video.video.file_id
            return
        except asyncio.TimeoutError:
            logger.warning(f"Welcome video send timeout after {WELCOME_VIDEO_SEND_TIMEOUT}s. Fallback to text menu.")
        except (TelegramError, ValueError, KeyError, AttributeError) as e:
            logger.warning(f"Welcome video send failed: {e}")

    await safe_reply_html(
        msg,
        menu_text,
        reply_markup=menu_kb,
    )

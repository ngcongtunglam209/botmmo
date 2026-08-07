import html
import os
import re

from telegram.constants import ParseMode
from telegram.error import TelegramError

def strip_tg_emoji(text: str) -> str:
    return re.sub(r'<tg-emoji[^>]*>([^<]*)</tg-emoji>', r'\1', text)


def _load_premium_emoji_map():
    """
    Build a glyph -> premium emoji-id map from all <tg-emoji> tags in project source.
    Supports both plain quotes and escaped quotes inside Python string literals.
    """
    mapping = {}
    try:
        from pathlib import Path

        source_path = Path(os.path.abspath(__file__)).resolve()
        project_root = source_path.parents[2] if len(source_path.parents) > 2 else Path.cwd()
        for py_file in project_root.rglob("*.py"):
            parts = {part.lower() for part in py_file.parts}
            if "__pycache__" in parts or ".venv" in parts or "venv" in parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            pairs = re.findall(r'<tg-emoji\s+emoji-id=\\?"(\d+)\\?">([^<]+)</tg-emoji>', source)
            for emoji_id, glyph in pairs:
                if not glyph:
                    continue
                mapping.setdefault(glyph, emoji_id)
                no_vs = glyph.replace("\ufe0f", "")
                mapping.setdefault(no_vs, emoji_id)
                mapping.setdefault(no_vs + "\ufe0f", emoji_id)
    except (OSError, ValueError):
        # If source scan fails we still keep bot running.
        return {}
    return mapping


PREMIUM_EMOJI_ID_BY_GLYPH = _load_premium_emoji_map()
DEFAULT_PREMIUM_EMOJI_ID = (
    PREMIUM_EMOJI_ID_BY_GLYPH.get("ℹ️")
    or PREMIUM_EMOJI_ID_BY_GLYPH.get("ℹ")
    or (next(iter(PREMIUM_EMOJI_ID_BY_GLYPH.values())) if PREMIUM_EMOJI_ID_BY_GLYPH else None)
)

# Semantic aliases for emojis that do not have a direct premium-id mapping in source.
# The value must be a glyph that already has a known premium-id.
PREMIUM_EMOJI_ALIAS = {
    "❌": "🚫",
    "⛔": "🚫",
    "⏳": "⏰",
    "⌛": "⏰",
    "⌚": "⏰",
    "⏱": "⏰",
    "⏭": "⏰",
    "⏸": "⚠️",
    "⏹": "⚠️",
    "📧": "💬",
    "✉": "💬",
    "✉️": "💬",
    "📩": "💬",
    "📨": "💬",
    "📭": "📦",
    "📥": "📦",
    "📤": "📦",
    "🎲": "🎡",
    "🎯": "🎡",
    "🎰": "🎡",
    "🎮": "🎡",
    "🎪": "🎡",
    "🎉": "🎁",
    "🏆": "⭐",
    "🥇": "⭐",
    "🥈": "⭐",
    "🥉": "⭐",
    "🏅": "⭐",
    "🎖": "⭐",
    "👉": "👇",
    "⬅": "👇",
    "⬅️": "👇",
    "⬆": "🔸",
    "⬆️": "🔸",
    "🗑": "🚫",
    "🗑️": "🚫",
    "🔢": "🆔",
    "🔥": "⚡️",
    "💥": "⚡️",
    "🚀": "⚡️",
    "🛒": "🛍",
    "♻": "⚙️",
    "♻️": "⚙️",
    "➕": "🔸",
    "➖": "🔸",
    "🏦": "💰",
    "🔗": "🌐",
    "🧾": "📜",
    "📋": "📝",
    "📑": "📜",
    "📄": "📜",
    "📘": "📚",
    "📁": "📦",
    "📂": "📦",
    "📈": "📊",
    "📉": "📊",
    "📌": "🏷️",
    "📍": "🏷️",
    "🔄": "⚙️",
    "🚨": "⚠️",
    "🧹": "⚙️",
    "✨": "⭐",
    "📢": "💬",
    "📣": "💬",
    "☁": "🌐",
    "☁️": "🌐",
    "✏": "✍️",
    "✏️": "✍️",
    "👨": "👤",
    "🧑": "👤",
    "👍": "✅",
    "💪": "🤝",
    "💼": "📦",
    "🔑": "🔒",
    "🔔": "⚠️",
    "🔕": "⚠️",
    "🔇": "⚠️",
    "❓": "ℹ️",
    "💾": "📜",
    "📞": "💬",
    "🔖": "🏷️",
    "😊": "🤝",
    "😅": "🫤",
    "😎": "⭐",
    "🟢": "✅",
    "☀": "⭐",
    "☀️": "⭐",
    "🆕": "🆔",
    "🌙": "🌚",
    "🏠": "🌐",
    "📖": "📚",
    "📛": "🏷️",
    "🔌": "⚙️",
    "🔚": "🚫",
    "🔧": "🛠",
    "🔍": "🔎",
    "🔮": "💎",
    "🔺": "🔸",
    "🔻": "🔸",
    "🖼": "📸",
    "🖼️": "📸",
    "🦕": "🤖",
    "🦖": "🤖",
    "🕐": "⏰",
    "🚚": "📦",
    "🌍": "🌐",
    "🧩": "🤝",
}

GENERIC_EMOJI_REGEX = re.compile(
    r'(?:[0-9#*]\ufe0f?\u20e3|[\U0001F000-\U0001FAFF](?:\ufe0f)?|[\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF](?:\ufe0f)?)'
)
HTML_INTENT_REGEX = re.compile(r"</?(?:b|i|u|s|code|pre|a|blockquote|tg-emoji)\b", re.IGNORECASE)


def _is_markdown_mode(parse_mode) -> bool:
    if parse_mode is None:
        return False
    return "MARKDOWN" in str(parse_mode).upper()


def _allow_auto_html_for_text(parse_mode, raw_text: str) -> bool:
    if parse_mode is not None:
        return "HTML" in str(parse_mode).upper()
    if not isinstance(raw_text, str):
        return False
    if HTML_INTENT_REGEX.search(raw_text):
        return True
    if "<" in raw_text or ">" in raw_text or "&" in raw_text:
        return False
    return True


def _resolve_premium_emoji_id(glyph: str, allow_default: bool = True):
    if not PREMIUM_EMOJI_ID_BY_GLYPH:
        return None
    direct = PREMIUM_EMOJI_ID_BY_GLYPH.get(glyph) or PREMIUM_EMOJI_ID_BY_GLYPH.get(glyph.replace("\ufe0f", ""))
    if direct:
        return direct
    alias_target = PREMIUM_EMOJI_ALIAS.get(glyph) or PREMIUM_EMOJI_ALIAS.get(glyph.replace("\ufe0f", ""))
    if alias_target:
        alias_id = PREMIUM_EMOJI_ID_BY_GLYPH.get(alias_target) or PREMIUM_EMOJI_ID_BY_GLYPH.get(alias_target.replace("\ufe0f", ""))
        if alias_id:
            return alias_id
    if allow_default and DEFAULT_PREMIUM_EMOJI_ID:
        return DEFAULT_PREMIUM_EMOJI_ID
    return None


def upgrade_text_to_premium_emoji(text: str) -> str:
    """
    Convert mapped emoji glyphs to premium tags while preserving unknown glyphs.
    Existing <tg-emoji> tags are preserved as-is.
    """
    if not isinstance(text, str) or not text or not PREMIUM_EMOJI_ID_BY_GLYPH:
        return text

    placeholders = []

    def _protect_tg(match):
        placeholders.append(match.group(0))
        return f"__TG_EMOJI_BLOCK_{len(placeholders) - 1}__"

    protected = re.sub(r"<tg-emoji[^>]*>[^<]*</tg-emoji>", _protect_tg, text)
    changed = False

    def _replace_emoji(match):
        nonlocal changed
        glyph = match.group(0)
        emoji_id = _resolve_premium_emoji_id(glyph, allow_default=False)
        if not emoji_id:
            return glyph
        changed = True
        return f'<tg-emoji emoji-id="{emoji_id}">{glyph}</tg-emoji>'

    upgraded = GENERIC_EMOJI_REGEX.sub(_replace_emoji, protected)

    for idx, original in enumerate(placeholders):
        upgraded = upgraded.replace(f"__TG_EMOJI_BLOCK_{idx}__", original)

    return upgraded if changed else text

def _plain_no_emoji_text(text: str) -> str:
    plain = strip_tg_emoji(str(text or ""))
    plain = re.sub(r"(?i)<br\s*/?>", "\n", plain)
    plain = re.sub(r"(?i)</?(?:p|div|li|ul|ol|blockquote|pre)\b[^>]*>", "\n", plain)
    plain = re.sub(r"</?[^>]+>", "", plain)
    plain = html.unescape(plain).strip()
    plain = re.sub(r'([0-9#*])\ufe0f?\u20e3', lambda match: match.group(1), plain)
    plain = GENERIC_EMOJI_REGEX.sub(" ", plain)
    plain = re.sub(r"[ \t]{2,}", " ", plain)
    plain = re.sub(r" *\n *", "\n", plain)
    return plain.strip()

def _plain_text_preserve_emoji(text: str) -> str:
    plain = strip_tg_emoji(str(text or ""))
    plain = re.sub(r"(?i)<br\s*/?>", "\n", plain)
    plain = re.sub(r"(?i)</?(?:p|div|li|ul|ol|blockquote|pre)\b[^>]*>", "\n", plain)
    plain = re.sub(r"</?[^>]+>", "", plain)
    plain = html.unescape(plain)
    plain = re.sub(r"[ \t]+\n", "\n", plain)
    plain = re.sub(r"\n[ \t]+", "\n", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()

async def safe_send_admin(bot, text, parse_mode=ParseMode.HTML, reply_markup=None, **kwargs):
    try:
        return await bot.send_message(chat_id=ADMIN_USER_ID, text=text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except (TelegramError, ValueError, KeyError, AttributeError):
        plain = _plain_text_preserve_emoji(text)
        try:
            return await bot.send_message(chat_id=ADMIN_USER_ID, text=plain, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
        except (TelegramError, ValueError, KeyError, AttributeError):
            try:
                return await bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=re.sub(r'<[^>]+>', '', plain),
                    reply_markup=reply_markup,
                    **kwargs
                )
            except (TelegramError, ValueError, KeyError, AttributeError) as e:
                logger.warning(f"safe_send_admin failed: {e}")
                return None


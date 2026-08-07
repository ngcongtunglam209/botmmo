# --- STORE USER INTERFACE ---

import time

from app.services.brand_matching import contains_any_search_term, contains_search_term


SOCIAL_SOURCE_STORE_PAGE_SIZE = 10
SOCIAL_SOURCE_MENU_CACHE_TTL_SECONDS = 30
_ctt_visible_category_cache = {
    "fingerprint": None,
    "expires_at": 0.0,
    "entries": [],
}

SOCIAL_SOURCE_PLATFORM_ICON_IDS = {
    "tiktok": "5327982530702359565",
    "facebook": "5323261730283863478",
    "instagram": "5319160079465857105",
    "telegram": "5330237710655306682",
    "twitter": "5255982126932439754",
}


def get_product_category(name):
    """Helper: Xác định category dựa trên tên sản phẩm."""
    import re

    name_lower = str(name or "").lower()
    if "capcut" in name_lower:
        return "CapCut & Edit Video"
    if "netflix" in name_lower:
        return "Netflix"
    if "drive" in name_lower or "google" in name_lower:
        return "Google Drive & One"
    if "youtube" in name_lower:
        return "YouTube Premium"
    if "spotify" in name_lower:
        return "Spotify & Music"
    if "kling" in name_lower:
        return "Kling"
    if "perplexity" in name_lower:
        return "Perplexity"
    if "tiktok" in name_lower or "tik tok" in name_lower:
        return "TikTok"
    if "proxy" in name_lower:
        return "Proxy"
    if (
        any(k in name_lower for k in ["gpt", "chatgpt", "openai", "copilot", "cursor", "claude", "gemini"])
        or re.search(r"\bai\b", name_lower)
    ):
        return "AI Tools (GPT, Copilot...)"
    if "adobe" in name_lower:
        return "Adobe Creative Cloud"
    if any(k in name_lower for k in ["elxa", "duolingo", "douligo", "doulingo"]):
        return "Học Tập"
    return "Sản Phẩm Khác"


def get_effective_store_category(product):
    explicit = str((product or {}).get("store_category") or "").strip()
    if explicit:
        return explicit
    """Infer a category only when the admin has not assigned one."""
    inferred = get_product_category((product or {}).get("name"))
    if inferred != "Sản Phẩm Khác":
        return inferred
    return (product or {}).get("store_category") or inferred


def get_store_category_config(category_name: str) -> dict:
    categories = globals().get("store_categories", {})
    config = categories.get(str(category_name or "").strip(), {}) if isinstance(categories, dict) else {}
    return config if isinstance(config, dict) else {}


def get_store_icon_id(label: str, fallback: str = "5854908544712707500") -> str:
    """Resolve custom emoji icon id by brand/category text."""
    if not label:
        return fallback

    value = str(label).strip().lower()
    configured_icon = str(get_store_category_config(label).get("emoji_id") or "").strip()
    if configured_icon:
        return configured_icon

    exact_map = {
        "capcut & edit video": "5364339557712020484",
        "netflix": "5318911503938634641",
        "google drive & one": "5796314805564346672",
        "youtube premium": "5334681713316479679",
        "spotify & music": "5346074681004801565",
        "kling": "6177161027558316737",
        "perplexity": "6174854857753631984",
        "tiktok": SOCIAL_SOURCE_PLATFORM_ICON_IDS["tiktok"],
        "facebook": SOCIAL_SOURCE_PLATFORM_ICON_IDS["facebook"],
        "instagram": SOCIAL_SOURCE_PLATFORM_ICON_IDS["instagram"],
        "telegram": SOCIAL_SOURCE_PLATFORM_ICON_IDS["telegram"],
        "twitter": SOCIAL_SOURCE_PLATFORM_ICON_IDS["twitter"],
        "x": SOCIAL_SOURCE_PLATFORM_ICON_IDS["twitter"],
        "proxy": "5447410659077661506",
        "ai tools (gpt, copilot...)": "5359726582447487916",
        "adobe creative cloud": "5359320531944358335",
        "học tập": "5796371348808799072",
        "sản phẩm khác": "5854908544712707500",
        str(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY).strip().lower(): "5397916757333654639",
    }
    if value in exact_map:
        return exact_map[value]

    # Platform names win over admin custom keywords. Prevents broad custom keys
    # like "post"/"like" from turning Facebook product buttons into X icons.
    platform_keyword_map = [
        (("tiktok", "tik tok", "douyin"), SOCIAL_SOURCE_PLATFORM_ICON_IDS["tiktok"]),
        (("facebook", "fb"), SOCIAL_SOURCE_PLATFORM_ICON_IDS["facebook"]),
        (("instagram", "ig"), SOCIAL_SOURCE_PLATFORM_ICON_IDS["instagram"]),
        (("telegram",), SOCIAL_SOURCE_PLATFORM_ICON_IDS["telegram"]),
        (("twitter", "x.com", "x"), SOCIAL_SOURCE_PLATFORM_ICON_IDS["twitter"]),
    ]
    for keywords, icon_id in platform_keyword_map:
        if contains_any_search_term(value, keywords):
            return icon_id

    dynamic_icons = globals().get("custom_store_icons", {})
    if isinstance(dynamic_icons, dict):
        for raw_keyword, raw_icon_id in sorted(dynamic_icons.items(), key=lambda item: len(str(item[0] or "")), reverse=True):
            keyword = str(raw_keyword or "").strip().lower()
            icon_id = str(raw_icon_id or "").strip()
            if keyword and icon_id and contains_search_term(value, keyword):
                return icon_id

    keyword_map = [
        (("youtube",), "5334681713316479679"),
        (("netflix",), "5318911503938634641"),
        (("capcut",), "5364339557712020484"),
        (("spotify",), "5346074681004801565"),
        (("adobe",), "5359320531944358335"),
        (("canva",), "5796214303329620386"),
        (("surfshark",), "5796592771552777710"),
        (("kling",), "6177161027558316737"),
        (("perplexity",), "6174854857753631984"),
        (("proxy", "residential proxy", "datacenter proxy", "ipv4", "ipv6"), "5447410659077661506"),
        (("gmail", "google one", "google drive", "gdrive", "google"), "5796314805564346672"),
        (("apple", "icloud", "ios"), "5334955749409834455"),
        (("github", "copilot"), "5346181118884331907"),
        (("banking", "bank", "momo", "vietcombank", "mbbank", "acb", "tpbank", "zalopay"), "5364075889669718872"),
        (("antigravity",), "6178962311072456422"),
        (("grok", "super grok", "supergrok"), "6179337489350663129"),
        (("claude",), "6174520215376763867"),
        (("chatgpt", "gpt", "openai", "gemini", "cursor", "ai tools"), "5359726582447487916"),
        (("duolingo", "douligo", "doulingo", "elxa", "hoc tap", "học tập"), "5796371348808799072"),
        (("hotmail", "outlook"), "5253742260054409879"),
        (("social",), "5397916757333654639"),
    ]

    for keywords, icon_id in keyword_map:
        if contains_any_search_term(value, keywords):
            return icon_id
    return fallback


def _is_supplier_source_purchase_blocked(product) -> bool:
    return bool(isinstance(product, dict) and product.get("supplier_source_purchase_blocked"))


def _collect_pending_manual_count_by_pid():
    counts = {}
    if pending_manual_orders:
        for order in pending_manual_orders.values():
            product_id = order.get("product_id")
            if product_id:
                counts[product_id] = counts.get(product_id, 0) + 1
    return counts


def _is_product_visible_in_store(product) -> bool:
    if not isinstance(product, dict) or not _ctt_is_catalog_visible(product):
        return False
    
    out_of_stock_since = product.get("out_of_stock_since")
    if out_of_stock_since:
        import time
        if time.time() - out_of_stock_since > 7 * 86400:
            return False
            
    return True


def _group_visible_products_by_category():
    grouped_products = {}
    for pid, product in products.items():
        if not _is_product_visible_in_store(product):
            continue
        if _ctt_is_service_product(product):
            continue
        category = get_effective_store_category(product)
        if get_store_category_config(category).get("hidden") is True:
            continue
        grouped_products.setdefault(category, []).append((pid, product))
    return grouped_products


def _paginate_items(items, page: int, page_size: int = SOCIAL_SOURCE_STORE_PAGE_SIZE):
    safe_items = list(items or [])
    safe_page_size = max(1, int(page_size or SOCIAL_SOURCE_STORE_PAGE_SIZE))
    total_pages = max(1, (len(safe_items) + safe_page_size - 1) // safe_page_size)
    safe_page = min(max(0, int(page or 0)), total_pages - 1)
    start_index = safe_page * safe_page_size
    end_index = start_index + safe_page_size
    return safe_items[start_index:end_index], safe_page, total_pages


def _build_pagination_row(previous_callback: str | None = None, next_callback: str | None = None):
    row = []
    if previous_callback:
        row.append(_btn("Trang trước", icon_id="6206032691075223572", callback_data=previous_callback))
    if next_callback:
        row.append(_btn("Trang sau", icon_id="6186252635805323641", callback_data=next_callback))
    return row


def _get_ctt_visible_source_category_entries():
    now = time.monotonic()
    service_count = 0
    visible_count = 0
    latest_synced_at = 0.0
    for product in products.values():
        if not _ctt_is_service_product(product):
            continue
        service_count += 1
        if not _ctt_is_catalog_visible(product):
            continue
        visible_count += 1
        try:
            latest_synced_at = max(
                latest_synced_at,
                float(product.get("ctt_last_synced_at") or 0),
            )
        except (TypeError, ValueError, AttributeError):
            pass

    fingerprint = (service_count, visible_count, latest_synced_at)
    if (
        _ctt_visible_category_cache.get("fingerprint") == fingerprint
        and float(_ctt_visible_category_cache.get("expires_at") or 0) > now
    ):
        return list(_ctt_visible_category_cache.get("entries") or [])

    category_map = {}
    for pid, product in products.items():
        if not _ctt_is_service_product(product):
            continue
        if not _ctt_is_catalog_visible(product):
            continue
        source_category = _ctt_get_grouped_source_category_label(product)
        category_map.setdefault(source_category, []).append((pid, product))

    entries = []
    for category_name, category_products in category_map.items():
        name_min = {}
        for pid, product in category_products:
            product_name = str(product.get("name") or pid)
            name_min[product_name] = min(name_min.get(product_name, float("inf")), int(product.get("price", 0) or 0))
        sorted_products = sorted(
            category_products,
            key=lambda item: (
                name_min[str(item[1].get("name") or item[0])],
                int(item[1].get("price", 0) or 0),
                str(item[1].get("name") or item[0]).casefold(),
            ),
        )
        entries.append((category_name, sorted_products))

    entries.sort(key=lambda item: _ctt_group_sort_key(item[0]))
    _ctt_visible_category_cache.update(
        {
            "fingerprint": fingerprint,
            "expires_at": now + SOCIAL_SOURCE_MENU_CACHE_TTL_SECONDS,
            "entries": entries,
        }
    )
    return entries


def _ctt_group_sort_key(category_name: str):
    parts = [part.strip() for part in str(category_name or "").split("|", 1)]
    platform = parts[0] if parts else ""
    group = parts[1] if len(parts) > 1 else ""
    platform_priority = {
        "TikTok": 0,
        "Facebook": 1,
        "Instagram": 2,
        "Telegram": 3,
        "YouTube": 4,
        "Twitter": 5,
        "Threads": 6,
        "Discord": 7,
        "Spotify": 8,
        "Shopee": 9,
        "Social": 99,
    }
    group_priority = {
        "Tang Like": 0,
        "Tang Follow": 1,
        "Tang Member": 2,
        "Tang View": 3,
        "Tang Comment": 4,
        "Tang Share": 5,
        "Tang Save": 6,
        "Live": 7,
        "Story": 8,
        "Dich vu khac": 99,
    }
    return (
        platform_priority.get(platform, 50),
        _normalize_ctt_search_text(platform),
        group_priority.get(group, 50),
        _normalize_ctt_search_text(group),
    )


def _ctt_get_platform_label(product: dict | None) -> str:
    raw_category = _ctt_get_source_category_label(product)
    first_part = str(raw_category or "").split("|", 1)[0].strip()
    normalized = _normalize_ctt_search_text(" | ".join([
        first_part,
        str((product or {}).get("name") or ""),
        str((product or {}).get("description") or ""),
    ]))
    for keywords, label in (
        (("facebook", "fb"), "Facebook"),
        (("tiktok", "tik tok"), "TikTok"),
        (("instagram", "ig"), "Instagram"),
        (("telegram",), "Telegram"),
        (("youtube",), "YouTube"),
        (("twitter", "x.com", "x"), "Twitter"),
        (("spotify",), "Spotify"),
        (("shopee",), "Shopee"),
        (("threads",), "Threads"),
        (("discord",), "Discord"),
    ):
        if contains_any_search_term(normalized, keywords):
            return label
    return first_part or "Social"


def _ctt_get_service_group_label(product: dict | None) -> str:
    haystack = _normalize_ctt_search_text(" | ".join([
        _ctt_get_source_category_label(product),
        str((product or {}).get("name") or ""),
        str((product or {}).get("description") or ""),
        str((product or {}).get("ctt_service_type") or ""),
    ]))
    group_rules = (
        (("member", "members", "group member", "telegram member", "join", "invite"), "Tang Member"),
        (("follow", "follower", "followers", "subscribers", "subscriber", "subscription", "sub "), "Tang Follow"),
        (("like", "likes", "reaction", "reactions", "favorites", "favorite", "heart"), "Tang Like"),
        (("view", "views", "watch", "impression", "impressions", "stream"), "Tang View"),
        (("comment", "comments", "reply", "reviews", "review"), "Tang Comment"),
        (("share", "shares", "repost", "retweet", "retweets"), "Tang Share"),
        (("save", "saves", "bookmark", "bookmarks"), "Tang Save"),
        (("live", "livestream", "live stream"), "Live"),
        (("story", "stories"), "Story"),
    )
    for keywords, label in group_rules:
        if any(keyword in haystack for keyword in keywords):
            return label
    raw_category = _ctt_get_source_category_label(product)
    parts = [part.strip() for part in str(raw_category or "").split("|") if part.strip()]
    return parts[1] if len(parts) > 1 else "Dich vu khac"


def _ctt_get_grouped_source_category_label(product: dict | None) -> str:
    return f"{_ctt_get_platform_label(product)} | {_ctt_get_service_group_label(product)}"


def _ctt_compact_service_name(product: dict | None, fallback: str = "") -> str:
    import html as html_lib
    import re

    raw_name = str((product or {}).get("name") or fallback or "").strip()
    raw_category = _ctt_get_source_category_label(product)
    platform = _ctt_get_platform_label(product)

    parts = [part.strip() for part in str(raw_category or "").split("|") if part.strip()]
    detail_parts = parts[1:] if parts and _normalize_ctt_search_text(parts[0]) == _normalize_ctt_search_text(platform) else parts
    cleaned = " - ".join(detail_parts) if detail_parts else raw_name
    cleaned = html_lib.unescape(str(cleaned or raw_name or fallback or "Service").strip())
    platform_pattern = re.compile(rf"^\s*{re.escape(platform)}\s*[-|:]*\s*", re.IGNORECASE)
    cleaned = platform_pattern.sub("", cleaned).strip()
    cleaned = re.sub(rf"(?i)\b{re.escape(platform)}\b\s*[-|:]*\s*", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or raw_name or fallback or "Service"


def _ctt_truncate_button_text(text: str, limit: int = 92) -> str:
    value = str(text or "").strip()
    safe_limit = max(24, int(limit or 92))
    if len(value) <= safe_limit:
        return value
    return value[: max(0, safe_limit - 3)].rstrip() + "..."


def _ctt_build_service_button_text(pid: str, product: dict | None) -> str:
    short_name = _ctt_compact_service_name(product, fallback=pid)
    minimum_quantity = int((product or {}).get("ctt_min_quantity", (product or {}).get("ctt_package_quantity", 1)) or 1)
    maximum_quantity = int((product or {}).get("ctt_max_quantity", 0) or 0)
    product_price = int((product or {}).get("price", 0) or 0)
    button_price_text = f"{product_price:,}d"
    if _ctt_is_service_product(product):
        button_price_text = f"~{_ctt_format_vnd_decimal(_ctt_get_base_unit_price_decimal(product))}d"

    badges = [button_price_text, f"Min {minimum_quantity:,}"]
    if maximum_quantity > 0:
        badges.append(f"Max {maximum_quantity:,}")
    badges.append("BH" if bool((product or {}).get("ctt_refill")) else "No BH")

    suffix = " | ".join(badges)
    name_limit = max(24, 92 - len(suffix) - 3)
    short_name = _ctt_truncate_button_text(short_name, name_limit)
    return _ctt_truncate_button_text(f"{short_name} | {suffix}", 92)


def get_ctt_source_category_by_index(source_index: int):
    entries = _get_ctt_visible_source_category_entries()
    if not entries:
        return None, []
    try:
        safe_index = int(source_index or 0)
    except (TypeError, ValueError):
        safe_index = 0
    if safe_index < 0 or safe_index >= len(entries):
        return None, []
    return entries[safe_index]


def refresh_ctt_runtime_config() -> None:
    """No-op: SOCIAL_SOURCE_API_KEY/BASE_URL la hang so tinh (hardcode rong)
    trong config_env.py, khong co runtime nao khac ghi de len - khong co gi
    de refresh. Giu ham nay lai vi nhieu noi khac van goi no."""
    return None


def _ctt_has_configured_source() -> bool:
    refresh_ctt_runtime_config()
    return bool(str(SOCIAL_SOURCE_API_KEY or "").strip())


def _get_ctt_visible_service_count() -> int:
    return sum(len(category_products) for _, category_products in _get_ctt_visible_source_category_entries())


def _get_ctt_empty_state_label() -> str:
    if not _ctt_has_configured_source():
        return "Nguon social chua cau hinh"
    return "Catalog social dang rong"


def _normalize_ctt_search_text(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _get_ctt_search_result_entries(search_query: str):
    normalized_query = _normalize_ctt_search_text(search_query)
    query_tokens = [token for token in normalized_query.split(" ") if token]
    if not query_tokens:
        return []

    matches = []
    for pid, product in products.items():
        if not _ctt_is_service_product(product):
            continue
        if not _ctt_is_catalog_visible(product):
            continue

        source_category = _ctt_get_source_category_label(product)
        haystack = " | ".join(
            [
                str(product.get("name") or pid),
                str(source_category or ""),
                str(product.get("description") or ""),
                str(product.get("ctt_service_id") or ""),
            ]
        )
        normalized_haystack = _normalize_ctt_search_text(haystack)
        if all(token in normalized_haystack for token in query_tokens):
            matches.append((pid, product))

    matches.sort(
        key=lambda item: (
            _normalize_ctt_search_text(_ctt_get_source_category_label(item[1])),
            int(item[1].get("price", 0) or 0),
            _normalize_ctt_search_text(str(item[1].get("name") or item[0])),
        )
    )
    return matches


def create_ctt_source_category_menu(page: int = 0):
    entries = _get_ctt_visible_source_category_entries()
    keyboard = []
    if not entries:
        keyboard.append([
            _btn(
                _get_ctt_empty_state_label(),
                icon_id="5447644880824181073",
                callback_data="ignore",
                style="danger",
            )
        ])
        keyboard.append([_btn("Quay lại Cửa hàng", icon_id="6206032691075223572", callback_data="store_main")])
        return InlineKeyboardMarkup(keyboard)

    keyboard.append([
        _btn("Tìm kiếm dịch vụ", icon_id="5429571366384842791", callback_data="ctt_search_prompt", style="primary")
    ])

    pending_manual_count_by_pid = _collect_pending_manual_count_by_pid()

    _, safe_page, total_pages = _paginate_items(entries, page)
    for global_index, (category_name, category_products) in enumerate(entries):
        if global_index < safe_page * SOCIAL_SOURCE_STORE_PAGE_SIZE:
            continue
        if global_index >= (safe_page + 1) * SOCIAL_SOURCE_STORE_PAGE_SIZE:
            break
        is_available = any(
            is_store_product_available(pid, product, pending_manual_count_by_pid)
            for pid, product in category_products
        )
        keyboard.append([
            _btn(
                f"{category_name} ({len(category_products)})",
                icon_id=get_store_icon_id(category_name, "5397916757333654639"),
                callback_data=f"view_ctt_source_{global_index}_0",
                style="success" if is_available else "danger",
            )
        ])

    if total_pages > 1:
        previous_callback = f"view_ctt_root_{safe_page - 1}" if safe_page > 0 else None
        next_callback = f"view_ctt_root_{safe_page + 1}" if safe_page < (total_pages - 1) else None
        pagination_row = _build_pagination_row(previous_callback, next_callback)
        if pagination_row:
            keyboard.append(pagination_row)

    keyboard.append([_btn("Quay lại Cửa hàng", icon_id="6206032691075223572", callback_data="store_main")])
    return InlineKeyboardMarkup(keyboard)


def create_ctt_source_product_menu(source_index: int, page: int = 0):
    category_name, category_products = get_ctt_source_category_by_index(source_index)
    if not category_name:
        return InlineKeyboardMarkup([
            [_btn("Danh mục social trống", icon_id="5447644880824181073", callback_data="ignore")],
            [_btn("Quay lại", icon_id="6206032691075223572", callback_data="view_ctt_root_0")],
        ])

    keyboard = []
    pending_manual_count_by_pid = _collect_pending_manual_count_by_pid()
    visible_products, safe_page, total_pages = _paginate_items(category_products, page)
    fallback_icon_id = get_store_icon_id(category_name, "5431492767249342908")

    for pid, product in visible_products:
        product_name = str(product.get("name") or pid)
        product_available = is_store_product_available(pid, product, pending_manual_count_by_pid)
        button_text = _ctt_build_service_button_text(pid, product)
        keyboard.append([
            _btn(
                button_text,
                icon_id=get_store_icon_id(product_name, fallback_icon_id),
                callback_data=f"view_prod_ctx_{int(source_index)}_{safe_page}|{pid}",
                style="success" if product_available else "danger",
            )
        ])

    if total_pages > 1:
        previous_callback = f"view_ctt_source_{int(source_index)}_{safe_page - 1}" if safe_page > 0 else None
        next_callback = f"view_ctt_source_{int(source_index)}_{safe_page + 1}" if safe_page < (total_pages - 1) else None
        pagination_row = _build_pagination_row(previous_callback, next_callback)
        if pagination_row:
            keyboard.append(pagination_row)

    root_page = max(0, int(source_index or 0) // SOCIAL_SOURCE_STORE_PAGE_SIZE)
    keyboard.append([_btn("Quay lại Nền tảng", icon_id="6206032691075223572", callback_data=f"view_ctt_root_{root_page}")])
    return InlineKeyboardMarkup(keyboard)


def create_ctt_search_result_menu(search_query: str, page: int = 0):
    matches = _get_ctt_search_result_entries(search_query)
    keyboard = []

    if not matches:
        return InlineKeyboardMarkup([
            [_btn("Không có kết quả phù hợp", icon_id="5447644880824181073", callback_data="ignore", style="danger")],
            [
                _btn("Tìm lại", icon_id="5429571366384842791", callback_data="ctt_search_prompt"),
                _btn("Quay lại Nền tảng", icon_id="6206032691075223572", callback_data="view_ctt_root_0"),
            ],
        ])

    pending_manual_count_by_pid = _collect_pending_manual_count_by_pid()
    visible_products, safe_page, total_pages = _paginate_items(matches, page)

    for pid, product in visible_products:
        product_name = str(product.get("name") or pid)
        product_available = is_store_product_available(pid, product, pending_manual_count_by_pid)
        button_text = _ctt_build_service_button_text(pid, product)
        keyboard.append([
            _btn(
                button_text,
                icon_id=get_store_icon_id(product_name, "5397916757333654639"),
                callback_data=f"view_prod_search_{safe_page}|{pid}",
                style="success" if product_available else "danger",
            )
        ])

    if total_pages > 1:
        previous_callback = f"view_ctt_search_{safe_page - 1}" if safe_page > 0 else None
        next_callback = f"view_ctt_search_{safe_page + 1}" if safe_page < (total_pages - 1) else None
        pagination_row = _build_pagination_row(previous_callback, next_callback)
        if pagination_row:
            keyboard.append(pagination_row)

    keyboard.append([
        _btn("Tìm lại", icon_id="5429571366384842791", callback_data="ctt_search_prompt"),
        _btn("Quay lại Nền tảng", icon_id="6206032691075223572", callback_data="view_ctt_root_0"),
    ])
    return InlineKeyboardMarkup(keyboard)


def is_store_product_available(pid, product, pending_manual_count_by_pid=None) -> bool:
    """Best-effort availability check used for store button styling."""
    if not _is_product_visible_in_store(product):
        return False

    if pending_manual_count_by_pid is None:
        pending_manual_count_by_pid = _collect_pending_manual_count_by_pid()

    if product.get("requires_gmail"):
        pending_count = pending_manual_count_by_pid.get(pid, 0)
        max_pending = product.get("max_pending_orders", 10)
        return pending_count < max_pending

    if _ctt_is_service_product(product):
        minimum_quantity = int(product.get("ctt_min_quantity", product.get("ctt_package_quantity", 1)) or 1)
        return bool(SOCIAL_SOURCE_API_KEY) and not _ctt_validate_purchase_quantity(product, minimum_quantity)

    if product.get("is_supplier_source_resell"):
        if _is_supplier_source_purchase_blocked(product):
            return False
        return int(product.get("supplier_source_stock", 0) or 0) > 0

    return len(product.get("stock", [])) > 0


def _store_resell_category_token(category_name: str) -> str:
    return hashlib.sha256(str(category_name or "").encode("utf-8")).hexdigest()[:12]


def get_store_resell_category_by_token(category_token: str) -> str:
    safe_token = str(category_token or "").strip().lower()
    if not safe_token:
        return ""
    for category_name, category_products in _group_visible_products_by_category().items():
        if not any(product.get("is_supplier_source_resell") for _, product in category_products):
            continue
        if hmac.compare_digest(_store_resell_category_token(category_name), safe_token):
            return category_name
    return ""


def create_store_menu(selected_category=None, user_id=None):
    lang = get_user_lang(user_id)
    labels = {
        "vi": {"back_main": "Quay lại Main Menu", "back_categories": "Quay lại Danh Mục", "empty": "Danh mục trống", "left": "Còn {count}", "out": "Hết hàng", "available": "Sẵn hàng", "paused": "Tạm ngừng"},
        "en": {"back_main": "Back to Main Menu", "back_categories": "Back to Categories", "empty": "Empty category", "left": "{count} left", "out": "Out of stock", "available": "Available", "paused": "Paused"},
        "zh": {"back_main": "返回主菜单", "back_categories": "返回分类", "empty": "分类为空", "left": "剩余 {count}", "out": "缺货", "available": "有货", "paused": "暂停销售"},
    }.get(lang)

    def _fmt_price(price_vnd: int) -> str:
        if not price_vnd: return "0đ" if lang == "vi" else "0 USDT"
        if lang == "vi": return f"{price_vnd:,}đ"
        try:
            rate = float(globals().get("_cached_live_usdt_rate") or USDT_TRC20_RATE_VND_PER_USDT)
            return f"{price_vnd / rate:.2f} USDT"
        except (TypeError, ValueError, ZeroDivisionError):
            return f"{price_vnd:,} VND"

    keyboard = []
    pending_manual_count_by_pid = _collect_pending_manual_count_by_pid()
    grouped_products = _group_visible_products_by_category()
    social_visible_count = _get_ctt_visible_service_count()
    if social_visible_count == 0 and _ctt_has_configured_source():
        try:
            load_data()
        except (OSError, ValueError, KeyError, AttributeError):
            pass
        grouped_products = _group_visible_products_by_category()
        social_visible_count = _get_ctt_visible_service_count()

    if selected_category is None:
        try:
            from app.core.config_env import ENABLE_ICLOUD_SALES
        except ImportError:
            ENABLE_ICLOUD_SALES = True
            
        icloud_btn = None
        if ENABLE_ICLOUD_SALES and available_links:
            icloud_btn = _btn(
                f"Gói iCloud 2TB (Auto) | {_fmt_price(ICLOUD_PACKAGE_PRICE)}",
                icon_id="5334955749409834455",
                callback_data="muahang_start",
                style="success",
            )
        elif ENABLE_ICLOUD_SALES:
            icloud_btn = _btn(
                "Gói iCloud 2TB - TẠM HẾT HÀNG",
                icon_id="5273914604752216432",
                callback_data="muahang_start",
                style="danger",
            )
        if icloud_btn is not None:
            keyboard.append([icloud_btn])

        for combo_id, combo in combo_deals.items():
            combo_products = [products.get(pid) for pid in combo.get("products", []) if pid in products]
            if len(combo_products) != 2:
                continue
            total_price = sum(int(product.get("price", 0) or 0) for product in combo_products)
            combo_price = int(total_price * (100 - combo["discount_percent"]) / 100)
            combo_name = (
                f"<tg-emoji emoji-id=\"5226711870492126219\">🎯</tg-emoji> "
                f"{combo_products[0]['name']} + {combo_products[1]['name']} | {_fmt_price(combo_price)} (-{combo['discount_percent']}%)"
            )
            combo_available = all(
                is_store_product_available(pid, products.get(pid), pending_manual_count_by_pid)
                for pid in combo.get("products", [])
            )
            keyboard.append([
                _btn(
                    combo_name,
                    callback_data=f"view_combo_{combo_id}",
                    style="success" if combo_available else "danger",
                )
            ])

        priority = [
            "Netflix",
            "YouTube Premium",
            "CapCut & Edit Video",
            "Google Drive & One",
            "Kling",
            "Perplexity",
            "AI Tools (GPT, Copilot...)",
            "TikTok",
            SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY,
            "Proxy",
            "Spotify & Music",
            "Adobe Creative Cloud",
        ]

        cat_icons = {
            "CapCut & Edit Video": "5364339557712020484",
            "Netflix": "5318911503938634641",
            "Google Drive & One": "5796314805564346672",
            "YouTube Premium": "5334681713316479679",
            "Spotify & Music": "5346074681004801565",
            "Kling": "6177161027558316737",
            "Perplexity": "6174854857753631984",
            "TikTok": "5327982530702359565",
            SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY: "5397916757333654639",
            "Proxy": "5447410659077661506",
            "AI Tools (GPT, Copilot...)": "5359726582447487916",
            "Adobe Creative Cloud": "5359320531944358335",
            "Học Tập": "5460966473512001416",
            "Sản Phẩm Khác": "5854908544712707500",
        }

        category_names = set(grouped_products.keys())
        if get_store_category_config(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY).get("hidden") is not True:
            category_names.add(SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY)

        sorted_categories = sorted(
            category_names,
            key=lambda category_name: (
                int(get_store_category_config(category_name).get(
                    "sort_order",
                    priority.index(category_name) if category_name in priority else 99,
                )),
                str(category_name).casefold(),
            ),
        )

        for category_name in sorted_categories:
            category_products = grouped_products.get(category_name, [])
            count = len(category_products)
            button_text = f"{category_name} ({count})"
            icon_id = get_store_icon_id(category_name, cat_icons.get(category_name, "5854908544712707500"))
            if category_name == SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY:
                count = social_visible_count
                button_text = f"{category_name} ({count})"
                category_available = _ctt_has_configured_source() and social_visible_count > 0
            else:
                category_available = any(
                    is_store_product_available(pid, product, pending_manual_count_by_pid)
                    for pid, product in category_products
                )
            keyboard.append([
                _btn(
                    button_text,
                    icon_id=icon_id,
                    callback_data=f"view_cat_{category_name}",
                    style="success" if category_available else "danger",
                )
            ])

        keyboard.append([_btn(labels["back_main"], icon_id="6206032691075223572", callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)

    if selected_category == SOCIAL_SOURCE_AUTO_MANAGED_ROOT_CATEGORY:
        return create_ctt_source_category_menu(page=0)

    if selected_category in grouped_products:
        category_products = grouped_products[selected_category]
        name_min = {}
        for pid, product in category_products:
            product_name = str(product.get("name") or pid)
            name_min[product_name] = min(name_min.get(product_name, float("inf")), int(product.get("price", 0) or 0))
        sorted_products = sorted(
            category_products,
            key=lambda item: (
                name_min[str(item[1].get("name") or item[0])],
                int(item[1].get("price", 0) or 0),
                str(item[1].get("name") or item[0]).casefold(),
            ),
        )
        product_fallback_icon_id = get_store_icon_id(selected_category, "5431492767249342908")

        for pid, product in sorted_products:
            name = str(product.get(f"name_{lang}") or product.get("name") or pid)
            price = int(product.get("price", 0) or 0)
            product_icon_id = get_store_icon_id(str(product.get("name") or name), product_fallback_icon_id)
            product_available = is_store_product_available(pid, product, pending_manual_count_by_pid)
            button_style = "success" if product_available else "danger"

            if product.get("requires_gmail"):
                pending_count = pending_manual_count_by_pid.get(pid, 0)
                max_pending = product.get("max_pending_orders", 10)
                slots_left = max_pending - pending_count
                state = labels["paused"] if pending_count >= max_pending else (labels["left"].format(count=slots_left) if slots_left <= 3 else labels["available"])
                button_text = f"{name} | {_fmt_price(price)} | {state}"
            elif product.get("is_supplier_source_resell"):
                stock = int(product.get("supplier_source_stock", 0) or 0)
                state = labels["paused"] if _is_supplier_source_purchase_blocked(product) else (labels["left"].format(count=stock) if stock else labels["out"])
                button_text = f"{name} | {_fmt_price(price)} | {state}"
            elif _ctt_is_service_product(product):
                minimum_quantity = int(product.get("ctt_min_quantity", product.get("ctt_package_quantity", 1)) or 1)
                unit_price = _ctt_get_base_unit_price_decimal(product)
                button_text = f"{name} | ~{_fmt_price(float(unit_price))} | Min {minimum_quantity:,}"
            else:
                stock = len(product.get("stock", []))
                button_text = f"{name} | {_fmt_price(price)} | {labels['left'].format(count=stock) if stock else labels['out']}"

            keyboard.append([
                _btn(
                    button_text,
                    icon_id=product_icon_id,
                    callback_data=f"view_prod_{pid}",
                    style=button_style,
                )
            ])
    else:
        keyboard.append([_btn(labels["empty"], icon_id="5447644880824181073", callback_data="ignore")])

    selected_products = grouped_products.get(selected_category, [])
    if any(product.get("is_supplier_source_resell") for _, product in selected_products):
        refresh_label = {
            "vi": "Làm mới giá & tồn kho",
            "en": "Refresh",
            "zh": "刷新",
        }.get(lang, "Làm mới giá & tồn kho")
        keyboard.append([
            _btn(
                refresh_label,
                icon_id="5370715282044100355",
                callback_data=f"refresh_resell_cat:{_store_resell_category_token(selected_category)}",
            )
        ])
    keyboard.append([_btn(labels["back_categories"], icon_id="6206032691075223572", callback_data="store_main")])
    return InlineKeyboardMarkup(keyboard)


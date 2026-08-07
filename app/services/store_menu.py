# --- STORE USER INTERFACE ---

import time

from app.services.brand_matching import contains_any_search_term, contains_search_term


STORE_PAGE_SIZE = 10

PLATFORM_ICON_IDS = {
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
        "tiktok": PLATFORM_ICON_IDS["tiktok"],
        "facebook": PLATFORM_ICON_IDS["facebook"],
        "instagram": PLATFORM_ICON_IDS["instagram"],
        "telegram": PLATFORM_ICON_IDS["telegram"],
        "twitter": PLATFORM_ICON_IDS["twitter"],
        "x": PLATFORM_ICON_IDS["twitter"],
        "proxy": "5447410659077661506",
        "ai tools (gpt, copilot...)": "5359726582447487916",
        "adobe creative cloud": "5359320531944358335",
        "học tập": "5796371348808799072",
        "sản phẩm khác": "5854908544712707500",
    }
    if value in exact_map:
        return exact_map[value]

    # Platform names win over admin custom keywords. Prevents broad custom keys
    # like "post"/"like" from turning Facebook product buttons into X icons.
    platform_keyword_map = [
        (("tiktok", "tik tok", "douyin"), PLATFORM_ICON_IDS["tiktok"]),
        (("facebook", "fb"), PLATFORM_ICON_IDS["facebook"]),
        (("instagram", "ig"), PLATFORM_ICON_IDS["instagram"]),
        (("telegram",), PLATFORM_ICON_IDS["telegram"]),
        (("twitter", "x.com", "x"), PLATFORM_ICON_IDS["twitter"]),
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
        (("github", "copilot"), "5346181118884331907"),
        (("banking", "bank", "momo", "vietcombank", "mbbank", "acb", "tpbank", "zalopay"), "5364075889669718872"),
        (("antigravity",), "6178962311072456422"),
        (("grok", "super grok", "supergrok"), "6179337489350663129"),
        (("claude",), "6174520215376763867"),
        (("chatgpt", "gpt", "openai", "gemini", "cursor", "ai tools"), "5359726582447487916"),
        (("duolingo", "douligo", "doulingo", "elxa", "hoc tap", "học tập"), "5796371348808799072"),
        (("hotmail", "outlook"), "5253742260054409879"),
    ]

    for keywords, icon_id in keyword_map:
        if contains_any_search_term(value, keywords):
            return icon_id
    return fallback


def _collect_pending_manual_count_by_pid():
    counts = {}
    if pending_manual_orders:
        for order in pending_manual_orders.values():
            product_id = order.get("product_id")
            if product_id:
                counts[product_id] = counts.get(product_id, 0) + 1
    return counts


def _is_product_visible_in_store(product) -> bool:
    if not isinstance(product, dict):
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
        category = get_effective_store_category(product)
        if get_store_category_config(category).get("hidden") is True:
            continue
        grouped_products.setdefault(category, []).append((pid, product))
    return grouped_products


def _paginate_items(items, page: int, page_size: int = STORE_PAGE_SIZE):
    safe_items = list(items or [])
    safe_page_size = max(1, int(page_size or STORE_PAGE_SIZE))
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

    return len(product.get("stock", [])) > 0


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
    if selected_category is None:
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
            "Proxy": "5447410659077661506",
            "AI Tools (GPT, Copilot...)": "5359726582447487916",
            "Adobe Creative Cloud": "5359320531944358335",
            "Học Tập": "5460966473512001416",
            "Sản Phẩm Khác": "5854908544712707500",
        }

        category_names = set(grouped_products.keys())

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

    keyboard.append([_btn(labels["back_categories"], icon_id="6206032691075223572", callback_data="store_main")])
    return InlineKeyboardMarkup(keyboard)


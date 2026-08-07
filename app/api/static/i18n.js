
<script>
(function () {
  const en = {
    "Dashboard": "Dashboard",
    "Lenh admin": "Admin commands",
    "OpenAPI": "OpenAPI",
    "control center": "control center",
    "Tong quan": "Overview",
    "Actions": "Actions",
    "San pham": "Products",
    "Don hang": "Orders",
    "Users": "Users",
    "API partner": "API partner",
    "Khuyen mai": "Promotions",
    "Ho tro": "Support",
    "Van hanh": "Operations",
    "Audit": "Audit",
    "admin app": "admin app",
    "Dino Control Center": "Dino Control Center",
    "Bang dieu khien tap trung cho san pham, kho, don hang, user, vi, API partner, coupon, support va van hanh.": "Central console for products, stock, orders, users, wallets, API partners, coupons, support, and operations.",
    "Chi so van hanh hien tai, cap nhat truc tiep tu runtime.": "Current operating metrics, rendered directly from runtime state.",
    "Doanh thu hom nay": "Today's revenue",
    "Tong doanh thu": "Total revenue",
    "Don thanh cong": "Completed orders",
    "Pending pay": "Pending payment",
    "Low stock": "Low stock",
    "Manual pending": "Manual pending",
    "API partner on": "API partners on",
    "So du API": "API balance",
    "Coupon": "Coupons",
    "Support open": "Open support",
    "Hang doi can xu ly": "Work queue",
    "Don moi gan day": "Recent orders",
    "Audit gan day": "Recent audit",
    "Khong co don manual pending.": "No manual pending orders.",
    "Chua co don hang gan day.": "No recent orders.",
    "Chua co audit log.": "No audit log yet.",
    "Thao tac ghi truc tiep vao database/runtime, co audit log.": "Write actions are applied directly to database/runtime and recorded in audit.",
    "San pham & ton kho": "Products & inventory",
    "Quan ly catalog local, manual, SupplierSource va SocialSource.": "Manage local, manual, SupplierSource, and SocialSource catalog.",
    "Tat ca loai": "All types",
    "Recent orders va trang thai thanh toan/giao hang.": "Recent orders and payment/delivery status.",
    "Users & vi": "Users & wallets",
    "Top users theo so du, don hang va trang thai ban.": "Top users by balance, orders, and ban status.",
    "Tat ca": "All",
    "Key partner, so du va trang thai kich hoat.": "Partner keys, balance, and enabled state.",
    "Khuyen mai": "Promotions",
    "Coupon hien co, flash sale va combo se mo rong o phase sau.": "Current coupons, with flash sale and combo expansion planned.",
    "Promo snapshot": "Promo snapshot",
    "Live chat, bao hanh va rut tien gom chung de admin khong bo sot ticket.": "Live chat, warranty, and withdrawals grouped so admins do not miss tickets.",
    "Manual pending, bao tri, AI va roadmap hoan thien admin web.": "Manual pending queue, maintenance, AI, and admin web roadmap.",
    "Lich su thao tac tu web admin.": "Action history from the admin web.",
    "Vi user": "User wallet",
    "Ban / unban": "Ban / unban",
    "Tao san pham": "Create product",
    "He thong": "System",
    "Pending manual": "Manual pending",
    "Thuc hien": "Run",
    "Cap nhat user": "Update user",
    "Luu san pham": "Save product",
    "Tao san pham": "Create product",
    "Cap nhat API": "Update API",
    "Cap nhat don": "Update order",
    "Luu coupon": "Save coupon",
    "Cap nhat he thong": "Update system",
    "Don dep pending": "Clean pending",
    "User ID": "User ID",
    "So tien": "Amount",
    "Kieu": "Mode",
    "Cong tien": "Add balance",
    "Tru tien": "Subtract balance",
    "Set so du": "Set balance",
    "Ly do": "Reason",
    "Trang thai": "Status",
    "Product ID": "Product ID",
    "Gia moi": "New price",
    "Ten moi": "New name",
    "Thoi han": "Duration",
    "Gioi han manual": "Manual limit",
    "Mo ta": "Description",
    "Them stock local": "Add local stock",
    "Gia": "Price",
    "Ten": "Name",
    "Loai": "Type",
    "Local stock": "Local stock",
    "Manual/Gmail": "Manual/Gmail",
    "Stock ban dau": "Initial stock",
    "Thao tac": "Action",
    "Nap tien key": "Top up key",
    "Tao key": "Create key",
    "Tat key": "Disable key",
    "Bat key": "Enable key",
    "Key hoac ten partner": "Key or partner name",
    "Ma don": "Order code",
    "Gan email": "Set email",
    "Ghi chu admin": "Admin note",
    "Gia tri": "Value",
    "Them / cap nhat": "Add / update",
    "Xoa coupon": "Delete coupon",
    "Ma coupon": "Coupon code",
    "So luong": "Quantity",
    "Giam tien": "Discount",
    "So ngay het han": "Days until expiry",
    "Bat bao tri": "Maintenance on",
    "Tat bao tri": "Maintenance off",
    "Bat AI auto reply": "AI auto reply on",
    "Tat AI auto reply": "AI auto reply off",
    "Xoa 1 don": "Clear one order",
    "Xoa tat ca": "Clear all",
    "ID": "ID",
    "Stock": "Stock",
    "Pending": "Pending",
    "Sold": "Sold",
    "Sync": "Sync",
    "Status": "Status",
    "Tien": "Amount",
    "Luc": "Time",
    "Ghi chu": "Note",
    "Partner": "Partner",
    "So du": "Balance",
    "Het han": "Expires",
    "Noi dung": "Content",
    "Module": "Module",
    "Action": "Action",
    "Target": "Target",
    "Message": "Message",
    "Ve dashboard": "Back to dashboard",
    "object detail": "object detail",
    "Raw data": "Raw data",
    "Sá»­a san pham": "Edit product",
    "Sua san pham": "Edit product",
    "editable": "editable",
    "Luu thay doi": "Save changes",
    "Stock local": "Local stock",
    "Xoa toan bo stock local": "Clear all local stock",
    "Ho so user": "User profile",
    "Luu ho so": "Save profile",
    "Vi & ban": "Wallet & ban",
    "Cap nhat vi": "Update wallet",
    "Don hang cua user": "User orders",
    "Cong cu don hang": "Order tools",
    "API partner": "API partner",
    "Cap nhat partner": "Update partner",
    "Coupon": "Coupons",
    "Cap nhat": "Update",
    "Xoa": "Delete",
    "Cap nhat ticket": "Update ticket",
    "All admin commands.": "All admin commands.",
    "command catalog": "command catalog",
    "Danh sach toan bo lenh admin dang co trong bot, loc theo tu khoa va muc rui ro de quan ly van hanh nhanh hon tren web.": "Full catalog of admin bot commands with keyword and risk filters for faster web operations.",
    "JSON catalog": "JSON catalog",
    "Tat ca risk": "All risks",
    "Tong quan he thong": "System overview",
    "Kho link legacy": "Legacy link vault",
    "San pham va ton kho": "Products and inventory",
    "Don hang va thanh toan": "Orders and payment",
    "User va vi": "Users and wallets",
    "Coupon, khuyen mai, game": "Coupons, promotions, games",
    "Supplier SupplierSource va SocialSource": "SupplierSource and SocialSource suppliers",
    "Ho tro, thong bao, van hanh": "Support, notifications, operations"
  };
  const placeholders = {
    "Tim trong module hien tai...": "Search current module...",
    "Tim trong cac bang...": "Search tables...",
    "123456789": "123456789",
    "100000": "100000",
    "bo trong neu khong doi": "leave blank to keep current",
    "vd: 30 ngay": "e.g. 30 days",
    "Moi dong 1 item, chi nen dung voi san pham local stock": "One item per line, only for local-stock products",
    "Ten san pham": "Product name",
    "30 ngay": "30 days",
    "Mo ta ngan": "Short description",
    "Moi dong 1 item, chi dung voi local stock": "One item per line, local stock only",
    "500000": "500000",
    "DINO... hoac ten": "DINO... or name",
    "ICLD123456": "ICLD123456",
    "email hoac ghi chu": "email or note",
    "SALE2026": "SALE2026",
    "bo trong neu xoa tat ca": "leave blank to clear all",
    "Tim lenh, nhom, mo ta...": "Search commands, groups, descriptions..."
  };
  Object.assign(en, {
    "MMO ops center": "MMO ops center",
    "Tá»•ng quan": "Overview",
    "Sáº£n pháº©m": "Products",
    "ÄÆ¡n hÃ ng": "Orders",
    "Khuyáº¿n mÃ£i": "Promotions",
    "Há»— trá»£": "Support",
    "Váº­n hÃ nh": "Operations",
    "Lá»‡nh admin": "Admin commands",
    "MMO admin app": "MMO admin app",
    "Báº£ng Ä‘iá»u khiá»ƒn táº­p trung cho sáº£n pháº©m, kho, Ä‘Æ¡n hÃ ng, user, vÃ­, API partner, coupon, support vÃ  váº­n hÃ nh.": "Central console for products, stock, orders, users, wallets, API partners, coupons, support, and operations.",
    "Chá»‰ sá»‘ váº­n hÃ nh hiá»‡n táº¡i, cáº­p nháº­t trá»±c tiáº¿p tá»« runtime.": "Current operating metrics, rendered directly from runtime state.",
    "Doanh thu hÃ´m nay": "Today's revenue",
    "Tá»•ng doanh thu": "Total revenue",
    "ÄÆ¡n thÃ nh cÃ´ng": "Completed orders",
    "Sá»‘ dÆ° API": "API balance",
    "HÃ ng Ä‘á»£i cáº§n xá»­ lÃ½": "Work queue",
    "ÄÆ¡n má»›i gáº§n Ä‘Ã¢y": "Recent orders",
    "Audit gáº§n Ä‘Ã¢y": "Recent audit",
    "KhÃ´ng cÃ³ Ä‘Æ¡n manual pending.": "No manual pending orders.",
    "ChÆ°a cÃ³ Ä‘Æ¡n hÃ ng gáº§n Ä‘Ã¢y.": "No recent orders.",
    "ChÆ°a cÃ³ audit log.": "No audit log yet.",
    "Thao tÃ¡c ghi trá»±c tiáº¿p vÃ o database/runtime, cÃ³ audit log báº¯t buá»™c.": "Write actions are applied directly to database/runtime and always recorded in audit.",
    "Sáº£n pháº©m & tá»“n kho": "Products & inventory",
    "Quáº£n lÃ½ catalog local, manual, SupplierSource vÃ  SocialSource.": "Manage local, manual, SupplierSource, and SocialSource catalog.",
    "Táº¥t cáº£ loáº¡i": "All types",
    "Recent orders vÃ  tráº¡ng thÃ¡i thanh toÃ¡n/giao hÃ ng.": "Recent orders and payment/delivery status.",
    "Users & vÃ­": "Users & wallets",
    "Top users theo sá»‘ dÆ°, Ä‘Æ¡n hÃ ng vÃ  tráº¡ng thÃ¡i ban.": "Top users by balance, orders, and ban status.",
    "Táº¥t cáº£": "All",
    "Key partner, sá»‘ dÆ° vÃ  tráº¡ng thÃ¡i kÃ­ch hoáº¡t.": "Partner keys, balance, and enabled state.",
    "Coupon hiá»‡n cÃ³, flash sale vÃ  combo sáº½ má»Ÿ rá»™ng á»Ÿ phase sau.": "Current coupons, with flash sale and combo expansion planned.",
    "Live chat, báº£o hÃ nh vÃ  rÃºt tiá»n gom chung Ä‘á»ƒ admin khÃ´ng bá» sÃ³t ticket.": "Live chat, warranty, and withdrawals grouped so admins do not miss tickets.",
    "Manual pending, báº£o trÃ¬, AI vÃ  roadmap hoÃ n thiá»‡n admin web.": "Manual pending queue, maintenance, AI, and admin web roadmap.",
    "Lá»‹ch sá»­ thao tÃ¡c tá»« web admin.": "Action history from the admin web.",
    "VÃ­ user": "User wallet",
    "Há»‡ thá»‘ng": "System",
    "Thá»±c hiá»‡n": "Run",
    "Cáº­p nháº­t user": "Update user",
    "LÆ°u sáº£n pháº©m": "Save product",
    "Táº¡o sáº£n pháº©m": "Create product",
    "Cáº­p nháº­t API": "Update API",
    "Cáº­p nháº­t Ä‘Æ¡n": "Update order",
    "Cáº­p nháº­t há»‡ thá»‘ng": "Update system",
    "Dá»n pending": "Clean pending",
    "Sá»‘ tiá»n": "Amount",
    "Kiá»ƒu": "Mode",
    "Cá»™ng tiá»n": "Add balance",
    "Trá»« tiá»n": "Subtract balance",
    "Set sá»‘ dÆ°": "Set balance",
    "LÃ½ do": "Reason",
    "GiÃ¡ má»›i": "New price",
    "TÃªn má»›i": "New name",
    "Thá»i háº¡n": "Duration",
    "Giá»›i háº¡n manual": "Manual limit",
    "MÃ´ táº£": "Description",
    "ThÃªm stock local": "Add local stock",
    "GiÃ¡": "Price",
    "TÃªn": "Name",
    "Loáº¡i": "Type",
    "Thao tÃ¡c": "Action",
    "Náº¡p tiá»n key": "Top up key",
    "Táº¡o key": "Create key",
    "Táº¯t key": "Disable key",
    "Báº­t key": "Enable key",
    "Key hoáº·c tÃªn partner": "Key or partner name",
    "MÃ£ Ä‘Æ¡n": "Order code",
    "Gáº¯n email": "Set email",
    "Ghi chÃº admin": "Admin note",
    "GiÃ¡ trá»‹": "Value",
    "ThÃªm / cáº­p nháº­t": "Add / update",
    "XÃ³a coupon": "Delete coupon",
    "Sá»‘ lÆ°á»£ng": "Quantity",
    "Giáº£m tiá»n": "Discount",
    "Sá»‘ ngÃ y háº¿t háº¡n": "Days until expiry",
    "Báº­t báº£o trÃ¬": "Maintenance on",
    "Táº¯t báº£o trÃ¬": "Maintenance off",
    "Báº­t AI auto reply": "AI auto reply on",
    "Táº¯t AI auto reply": "AI auto reply off",
    "XÃ³a 1 Ä‘Æ¡n": "Clear one order",
    "XÃ³a táº¥t cáº£": "Clear all",
    "Tiá»n": "Amount",
    "LÃºc": "Time",
    "Ghi chÃº": "Note",
    "Sá»‘ dÆ°": "Balance",
    "Háº¿t háº¡n": "Expires",
    "Ná»™i dung": "Content",
    "Vá» dashboard": "Back to dashboard",
    "Sá»­a sáº£n pháº©m": "Edit product",
    "LÆ°u thay Ä‘á»•i": "Save changes",
    "XÃ³a toÃ n bá»™ stock local": "Clear all local stock",
    "Há»“ sÆ¡ user": "User profile",
    "LÆ°u há»“ sÆ¡": "Save profile",
    "VÃ­ & ban": "Wallet & ban",
    "Cáº­p nháº­t vÃ­": "Update wallet",
    "ÄÆ¡n hÃ ng cá»§a user": "User orders",
    "CÃ´ng cá»¥ Ä‘Æ¡n hÃ ng": "Order tools",
    "Cáº­p nháº­t partner": "Update partner",
    "Cáº­p nháº­t": "Update",
    "XÃ³a": "Delete",
    "Cáº­p nháº­t ticket": "Update ticket",
    "Danh sÃ¡ch toÃ n bá»™ lá»‡nh admin Ä‘ang cÃ³ trong bot, lá»c theo tá»« khÃ³a vÃ  má»©c rá»§i ro Ä‘á»ƒ quáº£n lÃ½ váº­n hÃ nh nhanh hÆ¡n trÃªn web.": "Full catalog of admin bot commands with keyword and risk filters for faster web operations.",
    "Táº¥t cáº£ risk": "All risks"
  });
  Object.assign(placeholders, {
    "TÃ¬m trong module hiá»‡n táº¡i...": "Search current module...",
    "TÃ¬m trong cÃ¡c báº£ng...": "Search tables...",
    "bá» trá»‘ng náº¿u khÃ´ng Ä‘á»•i": "leave blank to keep current",
    "vd: 30 ngÃ y": "e.g. 30 days",
    "Má»—i dÃ²ng 1 item, chá»‰ nÃªn dÃ¹ng vá»›i sáº£n pháº©m local stock": "One item per line, only for local-stock products",
    "TÃªn sáº£n pháº©m": "Product name",
    "30 ngÃ y": "30 days",
    "MÃ´ táº£ ngáº¯n": "Short description",
    "Má»—i dÃ²ng 1 item, chá»‰ dÃ¹ng vá»›i local stock": "One item per line, local stock only",
    "DINO... hoáº·c tÃªn": "DINO... or name",
    "email hoáº·c ghi chÃº": "email or note",
    "bá» trá»‘ng náº¿u xÃ³a táº¥t cáº£": "leave blank to clear all",
    "TÃ¬m lá»‡nh, nhÃ³m, mÃ´ táº£...": "Search commands, groups, descriptions..."
  });
  const dictionaries = { vi: {}, en };
  const textSources = new WeakMap();
  const blockedTags = new Set(["SCRIPT", "STYLE", "CANVAS", "PRE", "CODE"]);
  function translateTextNode(node, lang) {
    if (!node || !node.parentElement || blockedTags.has(node.parentElement.tagName)) return;
    if (!textSources.has(node)) textSources.set(node, node.nodeValue);
    const source = textSources.get(node);
    const trimmed = source.trim();
    if (!trimmed) return;
    const translated = lang === "en" ? (dictionaries.en[trimmed] || trimmed) : trimmed;
    node.nodeValue = source.replace(trimmed, translated);
  }
  function translateAttributes(lang) {
    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach((el) => {
      if (!el.dataset.i18nPlaceholderSource) el.dataset.i18nPlaceholderSource = el.getAttribute("placeholder") || "";
      const source = el.dataset.i18nPlaceholderSource;
      el.setAttribute("placeholder", lang === "en" ? (placeholders[source] || source) : source);
    });
    document.querySelectorAll("[data-confirm]").forEach((el) => {
      if (!el.dataset.i18nConfirmSource) el.dataset.i18nConfirmSource = el.dataset.confirm || "";
      const source = el.dataset.i18nConfirmSource;
      const translated = lang === "en" ? (en[source] || source) : source;
      el.dataset.confirm = translated;
    });
  }
  function translatePage(lang) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        let parent = node.parentElement;
        while (parent) {
          if (blockedTags.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
          parent = parent.parentElement;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => translateTextNode(node, lang));
    translateAttributes(lang);
  }
  function setLanguage(lang) {
    const next = lang === "en" ? "en" : "vi";
    localStorage.setItem("admin_lang", next);
    document.documentElement.lang = next;
    document.documentElement.dataset.adminLang = next;
    translatePage(next);
    document.querySelectorAll("[data-lang-toggle]").forEach((button) => {
      button.classList.toggle("active", button.dataset.langToggle === next);
      button.setAttribute("aria-pressed", button.dataset.langToggle === next ? "true" : "false");
    });
  }
  function initialLanguage() {
    const param = new URLSearchParams(location.search).get("lang");
    if (param === "en" || param === "vi") return param;
    return localStorage.getItem("admin_lang") || "vi";
  }
  document.querySelectorAll("[data-lang-toggle]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.langToggle));
  });
  window.AdminI18n = { setLanguage };
  setLanguage(initialLanguage());
})();
</script>


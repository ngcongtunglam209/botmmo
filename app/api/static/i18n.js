
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
    "Lâm Shop Control Center": "Lâm Shop Control Center",
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
    "Sửa san pham": "Edit product",
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
    "LAMSHOP... hoac ten": "LAMSHOP... or name",
    "ICLD123456": "ICLD123456",
    "email hoac ghi chu": "email or note",
    "SALE2026": "SALE2026",
    "bo trong neu xoa tat ca": "leave blank to clear all",
    "Tim lenh, nhom, mo ta...": "Search commands, groups, descriptions..."
  };
  Object.assign(en, {
    "MMO ops center": "MMO ops center",
    "Tổng quan": "Overview",
    "Sản phẩm": "Products",
    "Đơn hàng": "Orders",
    "Khuyến mãi": "Promotions",
    "Hỗ trợ": "Support",
    "Vận hành": "Operations",
    "Lệnh admin": "Admin commands",
    "MMO admin app": "MMO admin app",
    "Bảng điều khiển tập trung cho sản phẩm, kho, đơn hàng, user, ví, API partner, coupon, support và vận hành.": "Central console for products, stock, orders, users, wallets, API partners, coupons, support, and operations.",
    "Chỉ số vận hành hiện tại, cập nhật trực tiếp từ runtime.": "Current operating metrics, rendered directly from runtime state.",
    "Doanh thu hôm nay": "Today's revenue",
    "Tổng doanh thu": "Total revenue",
    "Đơn thành công": "Completed orders",
    "Số dư API": "API balance",
    "Hàng đợi cần xử lý": "Work queue",
    "Đơn mới gần đây": "Recent orders",
    "Audit gần đây": "Recent audit",
    "Không có đơn manual pending.": "No manual pending orders.",
    "Chưa có đơn hàng gần đây.": "No recent orders.",
    "Chưa có audit log.": "No audit log yet.",
    "Thao tác ghi trực tiếp vào database/runtime, có audit log bắt buộc.": "Write actions are applied directly to database/runtime and always recorded in audit.",
    "Sản phẩm & tồn kho": "Products & inventory",
    "Quản lý catalog local, manual, SupplierSource và SocialSource.": "Manage local, manual, SupplierSource, and SocialSource catalog.",
    "Tất cả loại": "All types",
    "Recent orders và trạng thái thanh toán/giao hàng.": "Recent orders and payment/delivery status.",
    "Users & ví": "Users & wallets",
    "Top users theo số dư, đơn hàng và trạng thái ban.": "Top users by balance, orders, and ban status.",
    "Tất cả": "All",
    "Key partner, số dư và trạng thái kích hoạt.": "Partner keys, balance, and enabled state.",
    "Coupon hiện có, flash sale và combo sẽ mở rộng ở phase sau.": "Current coupons, with flash sale and combo expansion planned.",
    "Live chat, bảo hành và rút tiền gom chung để admin không bỏ sót ticket.": "Live chat, warranty, and withdrawals grouped so admins do not miss tickets.",
    "Manual pending, bảo trì, AI và roadmap hoàn thiện admin web.": "Manual pending queue, maintenance, AI, and admin web roadmap.",
    "Lịch sử thao tác từ web admin.": "Action history from the admin web.",
    "Ví user": "User wallet",
    "Hệ thống": "System",
    "Thực hiện": "Run",
    "Cập nhật user": "Update user",
    "Lưu sản phẩm": "Save product",
    "Tạo sản phẩm": "Create product",
    "Cập nhật API": "Update API",
    "Cập nhật đơn": "Update order",
    "Cập nhật hệ thống": "Update system",
    "Dọn pending": "Clean pending",
    "Số tiền": "Amount",
    "Kiểu": "Mode",
    "Cộng tiền": "Add balance",
    "Trừ tiền": "Subtract balance",
    "Set số dư": "Set balance",
    "Lý do": "Reason",
    "Giá mới": "New price",
    "Tên mới": "New name",
    "Thời hạn": "Duration",
    "Giới hạn manual": "Manual limit",
    "Mô tả": "Description",
    "Thêm stock local": "Add local stock",
    "Giá": "Price",
    "Tên": "Name",
    "Loại": "Type",
    "Thao tác": "Action",
    "Nạp tiền key": "Top up key",
    "Tạo key": "Create key",
    "Tắt key": "Disable key",
    "Bật key": "Enable key",
    "Key hoặc tên partner": "Key or partner name",
    "Mã đơn": "Order code",
    "Gắn email": "Set email",
    "Ghi chú admin": "Admin note",
    "Giá trị": "Value",
    "Thêm / cập nhật": "Add / update",
    "Xóa coupon": "Delete coupon",
    "Số lượng": "Quantity",
    "Giảm tiền": "Discount",
    "Số ngày hết hạn": "Days until expiry",
    "Bật bảo trì": "Maintenance on",
    "Tắt bảo trì": "Maintenance off",
    "Bật AI auto reply": "AI auto reply on",
    "Tắt AI auto reply": "AI auto reply off",
    "Xóa 1 đơn": "Clear one order",
    "Xóa tất cả": "Clear all",
    "Tiền": "Amount",
    "Lúc": "Time",
    "Ghi chú": "Note",
    "Số dư": "Balance",
    "Hết hạn": "Expires",
    "Nội dung": "Content",
    "Về dashboard": "Back to dashboard",
    "Sửa sản phẩm": "Edit product",
    "Lưu thay đổi": "Save changes",
    "Xóa toàn bộ stock local": "Clear all local stock",
    "Hồ sơ user": "User profile",
    "Lưu hồ sơ": "Save profile",
    "Ví & ban": "Wallet & ban",
    "Cập nhật ví": "Update wallet",
    "Đơn hàng của user": "User orders",
    "Công cụ đơn hàng": "Order tools",
    "Cập nhật partner": "Update partner",
    "Cập nhật": "Update",
    "Xóa": "Delete",
    "Cập nhật ticket": "Update ticket",
    "Danh sách toàn bộ lệnh admin đang có trong bot, lọc theo từ khóa và mức rủi ro để quản lý vận hành nhanh hơn trên web.": "Full catalog of admin bot commands with keyword and risk filters for faster web operations.",
    "Tất cả risk": "All risks"
  });
  Object.assign(placeholders, {
    "Tìm trong module hiện tại...": "Search current module...",
    "Tìm trong các bảng...": "Search tables...",
    "bỏ trống nếu không đổi": "leave blank to keep current",
    "vd: 30 ngày": "e.g. 30 days",
    "Mỗi dòng 1 item, chỉ nên dùng với sản phẩm local stock": "One item per line, only for local-stock products",
    "Tên sản phẩm": "Product name",
    "30 ngày": "30 days",
    "Mô tả ngắn": "Short description",
    "Mỗi dòng 1 item, chỉ dùng với local stock": "One item per line, local stock only",
    "LAMSHOP... hoặc tên": "LAMSHOP... or name",
    "email hoặc ghi chú": "email or note",
    "bỏ trống nếu xóa tất cả": "leave blank to clear all",
    "Tìm lệnh, nhóm, mô tả...": "Search commands, groups, descriptions..."
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


# Audit hệ thống i18n — Dino Store / Lâm Shop

**Ngày:** 2026-09-01 · **Commit:** `dc19970` · **Phạm vi:** toàn repo, chỉ đọc
**Phương pháp:** 4 track song song, mọi con số lấy từ AST-parse thật (`ast.parse` trên 116 file `.py` dưới `app/`), không ước đoán.
**Dữ liệu máy đọc:** [`docs/i18n-issues.json`](./i18n-issues.json) — 153 issue.

---

## 0. Kết luận trước

> ## VERDICT: **B — REFACTOR MỘT PHẦN**
>
> Giữ nguyên toàn bộ **runtime** (`normalize_lang` / `resolve_lang` / `get_user_lang` / `set_user_lang` / `t()` / `lt()` — `app/utils/i18n.py:243-332`). Lõi này đúng, có fallback, có test.
> Sửa phần **nội dung**: 101 chuỗi tiếng Việt hardcode đang bay thẳng tới khách hàng, và 1 lỗ hổng `KeyError` chặn việc thêm ngôn ngữ thứ 4.
>
> Không đủ điều kiện viết lại (C): **0/4** tiêu chí thỏa. Không đủ điều kiện giữ nguyên (A): **101 lỗi critical**.

Chi tiết định lượng ở [§6](#6-verdict).

---

## 1. Bản đồ hệ thống

Không có `locales/`, `lang/`, `i18n/`. Không có `.po` / `.mo` / JSON / YAML. Toàn bộ i18n là **Python dict trong source**.

| Nơi chứa chuỗi dịch | File | Đơn vị | Số lượng |
|---|---|---|---|
| Bảng trung tâm `STRINGS` | `app/utils/i18n.py:20-240` | key | **55 key × 3 locale = 165 chuỗi** |
| Helper inline `lt(user_id, vi, en, zh)` | định nghĩa `app/utils/i18n.py:324` | call site | **307 call × 3 = 921 chuỗi**, 22 file |
| 9 dict `{"vi","en","zh"}` rời rạc | 6 file (bảng dưới) | key | ~90 key × 3 |
| 2 tài liệu HD/Chính sách | `app/utils/ui_and_email.py:63-260` | hằng | 6 hằng `HUONGDAN_TEXT_*` / `CHINHSACH_TEXT_*` |
| Chuỗi hardcode 1 ngôn ngữ | 34 file | literal | **450** (349 admin-only, 101 tới khách) |

9 dict rời rạc:

| # | Vị trí | Tên | Key |
|---|---|---|---|
| 1 | `app/handlers/payment_generation.py:190-194` | `qr_text` | 15 |
| 2 | `app/handlers/store_callback.py:17-20` | `_checkout_labels` | 17 |
| 3 | `app/handlers/store_callback.py:456-483` | `labels` (chi tiết SP) | 19 |
| 4 | `app/handlers/store_callback.py:609-613`, `:632-636` | `category_copy` / `store_copy` | tuple |
| 5 | `app/handlers/store_callback.py:761-765` | `manual` | 10 |
| 6 | `app/services/orders_delivery.py:48-90` | `_DELIVERY_TXT_LABELS` | 10 |
| 7 | `app/services/store_menu.py:217-221` | `labels` | 7 |
| 8 | `app/handlers/priority_and_text.py:1206-1210` | `confirm_labels` | tuple |
| 9 | `app/utils/ui_and_email.py:63-260` | `HUONGDAN_TEXT_*` + `CHINHSACH_TEXT_*` | 2 tài liệu |

**Ngoài phạm vi bot:** `app/web/**` (admin panel + partner API) — 22 template Jinja2 + `docs.html`, **hardcode tiếng Việt 100%, 0 call i18n**. Đây là thiết kế có chủ đích (panel 1 admin), không tính là lỗi hiển thị.

---

## 2. Key parity — sạch tuyệt đối

`ast.parse` trên literal `STRINGS` (không exec module, nên bắt được cả key trùng bị dict ghi đè âm thầm):

| Locale | Số key | Thiếu | Thừa | Trùng | Rỗng | **Coverage** |
|---|---|---|---|---|---|---|
| `vi` | 55 | 0 | 0 | 0 | 0 | **100%** |
| `en` | 55 | 0 | 0 | 0 | 0 | **100%** |
| `zh` | 55 | 0 | 0 | 0 | 0 | **100%** |

- **Missing key gọi từ code: 0.** 68 call `t()` đều dùng key tồn tại ở cả 3 locale.
- **Giá trị y hệt `vi`:** 9 candidate thô, sau khi loại endonym hợp lệ (`lang_name_vi`="Tiếng Việt", `lang_name_zh`="中文" — cố ý giữ nguyên ở mọi locale) và thuật ngữ kỹ thuật (`API Partner`, `WebApp API Admin`, `Admin`) thì còn **0 ca rò rỉ chưa dịch thật sự**.
- 9 dict rời rạc: cũng parity đủ 3 locale, 0 key thiếu.

Test `tests/test_i18n.py:32-35` (`test_all_languages_have_the_same_translation_keys`) enforce parity này bằng `assert set(i18n.STRINGS[lang]) == expected`. Nó hoạt động — và đó là lý do parity 100%.

---

## 3. An toàn Telegram — 0 lỗi crash

Kiểm 165 chuỗi `STRINGS` + 307 call `lt()` + 9 dict:

| Kiểm tra | Kết quả |
|---|---|
| Placeholder lệch giữa locale | **0** |
| Placeholder không có kwarg tương ứng | **0** |
| HTML hỏng / tag Telegram không hỗ trợ | **0** (1 flag ở `media_and_referrals.py:143-148` đã truy vết ra false positive — dòng `:161` đóng `</blockquote>`) |
| Vượt 4096 (message) | **0** — dài nhất `CHINHSACH_TEXT_EN` = 3201 ký tự sau strip tag |
| Vượt 64 (button label) | **0** — dài nhất 29 ký tự, trên 94 call `lt()` đi vào `_btn()` |
| Xuống dòng trong button label | **0** |
| ZWJ / lệch UTF-16 | 15 chuỗi lệch 1-3 unit — đúng surrogate pair của 👑💎🎮, bình thường |
| `zh` sót tiếng Việt | **0** — không diacritic nào trong dict `zh` |

**Vì sao không crash được:** cả hai accessor đều bọc format.

```python
# app/utils/i18n.py:311-316 (t) và :327-332 (lt)
try:
    return text.format(**kwargs)
except (KeyError, ValueError, IndexError):
    return text
```

Placeholder sai chỉ khiến user thấy `{ten}` thô, không văng exception. Đây là điểm mạnh thật của thiết kế hiện tại.

**2 rủi ro cấu trúc (chưa vỡ, medium):** chuỗi ghép từ dữ liệu runtime rồi làm button label, không cap 64 ký tự:

- `app/utils/ui_and_email.py:55-60` → `:401` — `rank_balance` + `format_money()` (zh trả `¥X ($Y)`).
- `app/services/store_menu.py:217-220` → `:342-366` — nhúng **tên sản phẩm admin nhập, không giới hạn độ dài**.

---

## 4. Kiến trúc

| Hạng mục | Thực trạng | Đánh giá |
|---|---|---|
| **Detect** | `resolve_lang()` `i18n.py:252-265`: profile → `user.language_code` → `vi`. `normalize_lang()` `:243-249` parse IETF tag (`en-US`, `zh-Hans`). | Đúng |
| **Lưu** | `user_data_db[uid]['lang']`, ghi lúc đăng ký `user_entry.py:72`, đổi qua `set_user_lang()` `:284-302` + `save_data(force=True, tables=[USERS_FILE])` `callback_router.py:432-434` | Sống sót restart. Không có race riêng cho lang |
| **Fallback** | `t()` `:305-316`: locale → `vi` → **trả về chính tên key**. Không crash, nhưng **không log** | Có, an toàn |
| **Cache / hot-reload** | `STRINGS` là dict module-level, load 1 lần lúc `exec()` boot. Không cache per-user nên đổi ngôn ngữ hiệu lực ngay tin nhắn kế. Sửa bản dịch phải restart | Chấp nhận được |
| **Plural** | Không có. `"{count} left"` dùng chung cho 1 và nhiều (`store_menu.py:218`) | Thiếu, ảnh hưởng thấp (vi/zh không chia số nhiều) |
| **Tiền tệ** | **Có** locale-aware: `format_money()` / `get_user_display_currency()` `payments_core.py:366-401` (vi→VND, en→USD, zh→CNY+USD). Nhưng bị bypass ở `store_callback.py:18,20` và `flashsale_wheel.py:320-322` — hardcode `đ` trong cả chuỗi en/zh | Có, dùng chưa nhất quán |
| **Ngày giờ** | Không locale-aware. Định dạng ngày viết cứng trong chuỗi tĩnh (`ui_and_email.py:65` `06/08/2026` vs `:117` `2026/08/06`) | Thiếu |

### Lỗ hổng chặn mở rộng ngôn ngữ (HIGH)

```python
# app/utils/i18n.py:326
text = {"vi": vi, "en": en, "zh": zh}[get_user_lang(user_id)]
```

Index trực tiếp, không `.get()`. 9 dict rời rạc cũng vậy (`store_callback.py:18-20`, `payment_generation.py:192-193`, `priority_and_text.py:1208-1209`, `store_menu.py:218-219`, `ui_and_email.py:263,267`).

Hôm nay an toàn **chỉ vì** `normalize_lang()` ghim cứng đúng 3 giá trị. Thêm `"ru"` vào `SUPPORTED_LANGS` + `_LANG_ALIASES` trước khi migrate xong 307 call `lt()` sẽ khiến **mọi user chọn `ru` ăn `KeyError` ngay tin nhắn đầu tiên**. Đây là chi phí chi phối khi thêm ngôn ngữ, không phải 55 key `STRINGS`.

### Khoảng trống test (HIGH)

- `tests/test_i18n.py:32-35` gác parity — **chỉ cho 55 key `STRINGS`**.
- **0 test** phủ 307 call `lt()` và 9 dict rời rạc. Thêm một `lt()` mai này với 2 tham số giống nhau, hoặc thiếu bản `zh`, **cả suite 460 test vẫn xanh**.

---

## 5. Chuỗi hardcode

450 literal tiếng Việt (hoặc chứa `<tg-emoji>`) đi thẳng vào `reply_text` / `send_message` / `edit_message_text` / `InlineKeyboardButton`, không qua `t()`/`lt()`.

Phân loại theo **người nhận thật** (truy vết guard `admin_command_wrapper` / `ADMIN_USER_ID` / `admin_only_prefixes`, rồi truy vết `chat_id=` của từng lệnh gửi):

| Nhóm | Số lượng | Ý nghĩa |
|---|---|---|
| **CUSTOMER-FACING** | **101** | **CRITICAL** — khách chọn `en`/`zh` nhận tiếng Việt |
| ADMIN-ONLY | 349 | Medium — 1 `ADMIN_USER_ID` cố định, tiếng Việt là đúng chủ đích |
| UNCERTAIN | 0 | — |

**Bẫy quan trọng:** nhiều chuỗi nằm trong file `admin_*.py` nhưng là thông báo admin **gửi cho khách** (duyệt hoàn tiền, buyer nhận tin). Khoảng 30/101 thuộc loại này. File `app/services/admin_refund.py` có **cả 9/9** hit là customer-facing.

### 101 chuỗi tới khách — theo file

| File | Số chuỗi |
|---|---|
| `app/handlers/priority_and_text.py` | 14 |
| `app/handlers/callback_router.py` | 11 |
| `app/services/admin_refund.py` | 9 |
| `app/services/admin_support.py` | 9 |
| `app/jobs/payment_monitor.py` | 8 |
| `app/handlers/admin_api.py` | 7 |
| `app/handlers/games_waitlist.py` | 6 |
| `app/handlers/payment_generation.py` | 4 |
| `app/jobs/admin_background.py` | 4 |
| `app/services/admin_withdrawals.py` | 4 |
| `app/services/support_automation.py` | 4 |
| `app/services/admin_orders.py` | 3 |
| `app/services/notifications_async.py` | 3 |
| `app/core/runtime_state.py` | 2 |
| `app/handlers/store_callback.py` | 2 |
| `app/handlers/user_entry.py` | 2 |
| `app/core/lifecycle.py`, `admin_menu.py`, `admin_orders.py`, `admin_user_commands.py`, `flashsale_wheel.py`, `product_catalog.py`, `payments_core.py`, `games_withdrawals_db.py`, `referrals_stats.py` | 1 mỗi file |
| **Tổng** | **101** trên **25 file** |

### Bằng chứng — nặng nhất

| file:line | Nội dung | Ai nhận |
|---|---|---|
| `app/core/lifecycle.py:245` | `⚠️ Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.` | **Mọi user** gặp exception chưa bắt |
| `app/core/runtime_state.py:26` | `Bot đang bảo trì / Vui lòng quay lại sau ít phút.` | Mọi non-admin |
| `app/core/runtime_state.py:50` | `⏳ Vui lòng chờ {remaining}s trước khi dùng lại lệnh này.` | Mọi user bị rate-limit |
| `app/jobs/payment_monitor.py:197,204` | `⚠️ ĐƠN HÀNG ĐÃ HẾT HẠN` | Người mua |
| `app/jobs/payment_monitor.py:613` | `XIN LỖI - SẢN PHẨM KHÔNG KHẢ DỤNG` | Người mua |
| `app/services/admin_orders.py:226` | `✅ ĐƠN HÀNG ĐÃ HOÀN THÀNH!` | Người mua |
| `app/services/admin_orders.py:271` | `❌ ĐƠN HÀNG ĐÃ BỊ HỦY` | Người mua |
| `app/services/admin_refund.py:181` | `💸 ĐƠN HÀNG ĐƯỢC HOÀN TIỀN` | Người mua |
| `app/services/admin_support.py:25,39` | `Yêu cầu bảo hành {claim_id} ... DUYỆT / TỪ CHỐI` | Người mua |
| `app/services/admin_withdrawals.py:49,91` | `YÊU CẦU RÚT TIỀN ĐÃ ĐƯỢC DUYỆT / BỊ TỪ CHỐI` | Người rút |
| `app/services/admin_withdrawals.py:148` | `🎉 ĐĂNG KÝ API THÀNH CÔNG!` | Partner |
| `app/handlers/user_entry.py:372` | `BẠN VỪA GIỚI THIỆU THÀNH CÔNG!` | Người giới thiệu |

Danh sách đủ 101 mục kèm dòng chính xác và trích đoạn: `docs/i18n-issues.json`, lọc `type == "hardcoded_string_customer_facing"`.

### Tỉ lệ hardcode

| Cách tính | Công thức | Kết quả |
|---|---|---|
| Thô (toàn bộ) | 450 / (450 + 375) | **54.5%** |
| **Chỉ chuỗi hiển thị cho khách** | 101 / (101 + 375) | **21.2%** |

375 = 68 `t()` + 307 `lt()`, tất cả đều nằm trên đường khách/partner đi được (0 call i18n nào ở nhánh admin-only). Hai mẫu số cùng quần thể, so sánh được.

**Con số 21.2% là con số dùng cho verdict.** 349 chuỗi admin-only không phải "chuỗi hiển thị" theo nghĩa đa ngữ — bot chỉ có một admin, nói tiếng Việt.

---

## 6. Verdict

### Đối chiếu tiêu chí "viết lại toàn bộ (C)" — cần ≥2

| # | Điều kiện | Đo được | Thỏa? |
|---|---|---|---|
| 1 | Key parity < 70% | **100%** (55/55/55) | KHÔNG |
| 2 | Không có cơ chế fallback | `t()` fallback `vi` → key name (`i18n.py:313`); `lt()` bọc try/except (`:329-332`) | KHÔNG |
| 3 | > 30% chuỗi hiển thị hardcode | **21.2%** | KHÔNG |
| 4 | Không có loader tập trung | **1 loader duy nhất** `app/utils/i18n.py`; mọi dispatch qua `get_user_lang()` | KHÔNG |

**0/4 thỏa — loại C dứt khoát.**

### Loại A?

A chỉ hợp lệ khi chỉ còn lỗi low/medium. Thực tế: **101 critical** (khách nhận sai ngôn ngữ) + **2 high** (`KeyError` chặn mở rộng, test không phủ 82% bề mặt dịch). **Loại A.**

### Chọn B — REFACTOR MỘT PHẦN

Ranh giới rõ ràng:

**GIỮ NGUYÊN — không đụng một dòng nào:**

- Toàn bộ runtime `app/utils/i18n.py:243-332`: `normalize_lang`, `resolve_lang`, `get_user_lang`, `set_user_lang`, `t()`.
- Cơ chế lưu locale trong `user_data_db` + `save_data(force=True)`.
- Bảng `STRINGS` 55 key và test parity `tests/test_i18n.py`.
- `format_money()` / `get_user_display_currency()` `payments_core.py:366-401`.
- `app/web/**` (ngoài phạm vi — panel 1 admin).

**REFACTOR:**

1. **Nội dung** — 101 chuỗi customer-facing chuyển sang `t()`/`lt()`.
2. **Chống lỗi** — `lt()` và 9 dict đổi index trực tiếp thành `.get(code, vi)`.
3. **Rào test** — test AST gác `lt()` và các dict rời rạc.
4. **Nhất quán** — thuật ngữ `zh`, `đ` hardcode, menu ngôn ngữ.

---

## 7. Ước lượng công sức

| Phase | Nội dung | File sửa | Key/chuỗi migrate | Rủi ro |
|---|---|---|---|---|
| **0** | Fallback hardening: `lt()` + 9 dict index thành `.get(code, vi)` | **6** | 10 vị trí, ~12 dòng | Rất thấp |
| **1** | 101 chuỗi customer-facing chuyển vào `STRINGS` | **25** (+1 `i18n.py`) | **101 key mới × 3 = 303 giá trị**; `STRINGS` 55 → 156 key | Trung bình |
| **2** | Test gate cho `lt()` + dict rời rạc | **1** (test mới) | — | Rất thấp |
| **3** | Nhất quán thuật ngữ + tiền tệ + menu | **5** | ~14 chuỗi | Thấp |
| **4** | *(Tùy chọn — chỉ khi thêm ngôn ngữ thứ 4)* migrate 307 `lt()` sang key | **22** | **307 key × 3 = 921 giá trị**; `STRINGS` 156 → 463 key | Cao |

**Phase 0-3 (bắt buộc): 31 file, 101 key mới, 303 giá trị dịch.**
Phase 4 gấp 3 lần khối lượng còn lại — **chỉ làm khi thực sự thêm ngôn ngữ**, không làm vì "cho sạch".

Chi tiết Phase 3:

- `zh` — `保修` (`callback_router.py:1214`, `store_callback.py:477,550`) vs `质保` (`orders_delivery.py:40,70,82,752,759`): chọn 1.
- `zh` — `支付方式` (`priority_and_text.py:785`) vs `付款方式` (`:1209`): cùng file, chọn 1.
- `đ` hardcode trong chuỗi en/zh: `store_callback.py:18,20`; `flashsale_wheel.py:320-322` — dùng `format_money()`.
- Menu ngôn ngữ `i18n.py:343-345` — nhãn `"Việt Nam"` / `"China"` / `"Anh"` trộn tiếng Việt và tiếng Anh bất kể locale người xem.
- `store_menu.py:217-220` → `:342-366` — truncate tên sản phẩm trước khi làm button label (giới hạn 64).
- `zh` xưng hô: 49 lần `您` vs 1 lần `你` (`i18n.py:176`). `vi`: ~75 lần `bạn` vs 2 lần `quý khách` (`store_callback.py:1224`).
- `&` chưa escape trong `btn_guide` / `btn_support` / `btn_wallet` (low — python-telegram-bot không parse HTML nhãn button, không vỡ hôm nay).

---

## 8. Kế hoạch migration (mô tả — CHƯA thực thi)

> Mỗi bước là 1 PR riêng, chạy `pytest` và `ruff check app/ tests/` trước khi sang bước kế.
> **Lưu ý loader:** `app/utils/i18n.py` là section module trong `SECTION_FILES`. Thêm key vào `STRINGS` an toàn. **Không** thêm file section mới, **không** đổi thứ tự `SECTION_FILES`, **không** chạy `ruff check --fix` không giới hạn rule trên file section.

**Bước 1 — Rào an toàn trước (Phase 0 + 2).**
Đổi `lt()` `i18n.py:326` thành `.get(get_user_lang(user_id), vi)`; làm tương tự 9 dict. Thêm test AST duyệt mọi `ast.Call` tên `lt` trong `app/`, assert đủ 3 tham số literal và không có 2 tham số trùng nhau (loại trừ emoji/số/brand). Sau bước này mọi thay đổi kế tiếp có lưới đỡ. Zero rủi ro hành vi.

**Bước 2 — Nhóm "lỗi hệ thống", 5 chuỗi.**
`lifecycle.py:245`, `runtime_state.py:26,50`, `payments_core.py:82`. Đây là chuỗi mọi user đều có thể gặp, giá trị trên rủi ro tốt nhất. Chuyển sang `t()`, thêm 5 key.

**Bước 3 — Nhóm "vòng đời đơn hàng", ~35 chuỗi.**
`payment_monitor.py` (8), `admin_orders.py` services (3) và handlers (1), `admin_refund.py` (9), `payment_generation.py` (4), `notifications_async.py` (3), `store_callback.py` (2). Chuyển sang `t()`. Đây là nhóm khách nhìn thấy nhiều nhất và liên quan tiền, soi kỹ placeholder tiền tệ, dùng `format_money()` thay vì `{x:,}đ`.

**Bước 4 — Nhóm "bảo hành / rút tiền / partner", ~24 chuỗi.**
`admin_support.py` (9), `admin_withdrawals.py` (4), `admin_api.py` (7), `support_automation.py` (4).

**Bước 5 — Nhóm còn lại, ~37 chuỗi.**
`priority_and_text.py` (14), `callback_router.py` (11), `games_waitlist.py` (6), `admin_background.py` (4), và các file 1-2 hit.

**Bước 6 — Phase 3, nhất quán.**
Thống nhất thuật ngữ `zh`, thay `đ` hardcode bằng `format_money()`, dịch nhãn menu ngôn ngữ theo locale người xem, truncate tên sản phẩm ở button.

**Bước 7 — Chỉ khi có yêu cầu thêm ngôn ngữ thứ 4.**
Migrate 307 `lt()` sang key `STRINGS`, theo từng file (22 file = 22 PR nhỏ). Thứ tự an toàn bắt buộc: **migrate hết `lt()` trước, mới thêm mã ngôn ngữ vào `SUPPORTED_LANGS` / `_LANG_ALIASES` sau**. Làm ngược lại là `KeyError` production ngay lập tức (xem §4).

Không đề xuất chuyển sang `gettext` / `.po` hay thư viện i18n ngoài: bảng hiện tại parity 100%, có test gác, và convention `<tg-emoji emoji-id>` cùng cơ chế section-loader khiến chi phí đổi format lớn hơn lợi ích.

---

## 9. Tổng kết issue

| Severity | Số lượng | Nội dung |
|---|---|---|
| **Critical** | **101** | Chuỗi tiếng Việt hardcode gửi tới khách hàng (25 file) |
| **High** | **2** | `lt()`/dict index không fallback dẫn tới `KeyError` khi thêm ngôn ngữ; test không phủ 307 `lt()` + 9 dict |
| **Medium** | **36** | 27 file có chuỗi admin-only hardcode; 2 button label không cap 64 ký tự; drift thuật ngữ `zh`; thiếu plural; ngày giờ không locale-aware |
| **Low** | **14** | `&` chưa escape (6); `đ` hardcode trong en/zh; menu ngôn ngữ trộn ngôn ngữ; xưng hô lệch; key động không static-check được (2) |
| **Tổng** | **153** | |

### Số liệu nền

| Chỉ số | Giá trị |
|---|---|
| File `.py` dưới `app/` | 116 (162 kể cả `tests/`) |
| LOC `app/` | 35,584 |
| Locale hỗ trợ | `vi` (mặc định), `en`, `zh` |
| Key `STRINGS` | 55 × 3 = 165 chuỗi |
| Call `t()` | 68 |
| Call `lt()` | 307 (22 file) |
| Tổng call site i18n | 375 |
| Chuỗi hardcode | 450 (101 khách / 349 admin) |
| Missing key | 0 |
| Placeholder mismatch | 0 |
| Lỗi HTML | 0 |
| Vượt giới hạn Telegram | 0 |

### Chưa xác minh

- Có chuỗi hardcode nào **trùng nghĩa** với key `STRINGS` sẵn có không (lẽ ra phải dùng `t()`) — cần rà thủ công, không kiểm được bằng static analysis.
- Chuỗi tiếng Anh thuần không dấu tiếng Việt và không `<tg-emoji>` — heuristic bỏ sót, con số 450 là **cận dưới**.
- Template Jinja2 `app/web/**` chưa quét chuỗi (đã xác nhận đơn ngữ tiếng Việt, ngoài phạm vi bot).
- Chất lượng dịch nghĩa `en`/`zh` do người bản ngữ đánh giá — audit này chỉ bắt lỗi kỹ thuật và drift thuật ngữ, không phán xét văn phong.

# Kế hoạch sửa i18n — Dino Store

Nối tiếp [`docs/i18n-audit.md`](./i18n-audit.md) (verdict **B — refactor một phần**).
Tài liệu này là kế hoạch thi công. **Chưa có dòng code nào được sửa.**

---

## 1. Số liệu đã hiệu chỉnh so với audit

Hai đợt khảo sát chi tiết đã sửa lại vài con số của audit. Dùng bảng này, không dùng bảng cũ.

| Hạng mục | Audit nói | Thực tế | Ghi chú |
|---|---|---|---|
| Chuỗi customer-facing | 101 | 101 | Không đổi |
| **Key mới phải viết** | 101 | **90** | 4 báo động giả, 6 dùng lại key sẵn có, 1 gộp trùng |
| Dict theo locale cần vá | 9 | **8** | `orders_delivery.py:315` đã an toàn sẵn |
| Tổng dict theo locale trong repo | 9 | 14 | Quét tổng quát; 6 cái còn lại đã an toàn |
| `STRINGS` sau migration | 156 key | **145 key** | 55 + 90 |

### 11 mục không cần key mới

**Báo động giả — không phải hardcode (4):**

| file:line | Lý do |
|---|---|
| `app/handlers/payment_generation.py:207` | Đã đa ngữ qua dict `qr_text`; chỉ cần vá fallback |
| `app/handlers/callback_router.py:582` | Đã gọi `t("live_chat_title", ...)`; heuristic bắt nhầm phần markup bao quanh |
| `app/handlers/callback_router.py:611` | Như trên |
| `app/handlers/flashsale_wheel.py:509` | Text đã dựng bằng `lt()` ở dòng ngay trên |

**Dùng lại key sẵn có (6):**

| file:line | Key tái sử dụng |
|---|---|
| `app/core/runtime_state.py:26` | `maintenance` |
| `app/services/admin_support.py:462` | `live_chat_title` |
| `app/services/admin_support.py:470` | `live_chat_empty` |
| `app/services/admin_support.py:471` | `live_chat_prompt` |
| `app/services/admin_support.py:472` | `live_chat_close` |
| `app/handlers/user_entry.py:614` | `live_chat_admin` |

**Gộp trùng (1):** `callback_router.py:288` và `:764` byte-identical (một bên dùng hằng `API_PREM_*`, một bên dùng escape unicode của cùng glyph) — chung key `partner_key_changed`.

**Xung đột tên đã xử lý:** `admin_api.py:269` và `callback_router.py:841` cùng được đề xuất tên `partner_topup_guide` nhưng nội dung khác nhau (nhắc cú pháp ngắn vs menu hướng dẫn đầy đủ) — cái sau đổi thành `partner_topup_menu_guide`.

### Khối lượng dịch thật sự

90 key × 3 locale = 270 giá trị. Bản `vi` bê nguyên từ source hiện tại, nên **180 chuỗi `en` + `zh` phải viết mới**. Đây là phần tốn công nhất và không tự động hoá được — code chỉ là chỗ chứa.

---

## 2. Quy ước đặt key

Flat, snake_case, tiền tố theo miền, khớp phong cách 55 key hiện có (`btn_*`, `verify_*`, `lang_*`, `rank_name_*`).

Tiền tố dùng: `order_` `refund_` `warranty_` `withdraw_` `partner_` `sys_` `referral_` `wallet_` `support_` `game_` `email_` `checkout_` `reward_` `product_`, cộng mở rộng họ `rank_` sẵn có.

**Emoji.** Thẻ `<tg-emoji emoji-id="...">` viết thẳng trong chuỗi dịch — đúng convention của `main_menu_title`. Hằng module trần (`E_SUCCESS`, `E_ERROR`, `E_TAG`, `E_LIMIT`, `E_LOADING`, `E_TIP`, `E_STAT`, `E_GLOBE`, `E_SOS`, `E_ID`, `E_MENU`, `API_PREM_*`) truyền vào làm kwarg của `t()`, theo tiền lệ `get_main_menu_text()` với `success=E_SUCCESS`.

**Không xung đột** với 55 key hiện có, ngoài 6 ca tái sử dụng có chủ ý ở trên.

---

## 3. Bảy chỗ khó — đọc trước khi bắt đầu

Đây là phần duy nhất không phải thay-một-dòng. Chúng là thông báo admin gửi **cho khách**, nên ngôn ngữ phải resolve từ id **người nhận**, không phải id admin đang thao tác. Ở bảy chỗ này id người nhận không có sẵn trong scope.

**Vòng lặp broadcast — dựng text một lần rồi mới lặp (3):**

| file:line | Vấn đề |
|---|---|
| `app/services/notifications_async.py:286` | Text dựng trước vòng `for` người nhận |
| `app/services/notifications_async.py:580` | Như trên |
| `app/services/notifications_async.py:823` | Như trên |

Sửa: chuyển lời gọi `t()` vào **trong** vòng lặp, mỗi người nhận một lần. Không phải swap một dòng. Đổi số lần format từ 1 thành N — với broadcast lớn cần đo lại chi phí.

**Thiếu tham số — hàm không hề nhận `user_id` (4):**

| file:line | Hàm |
|---|---|
| `app/services/support_automation.py:24` | `handle_billing_questions()` |
| `app/services/support_automation.py:34` | như trên |
| `app/services/support_automation.py:50` | `handle_email_not_found()` |
| `app/services/support_automation.py:66` | như trên |

`user_id` tồn tại cách đó hai tầng gọi (`priority_and_text.py:1096`) nhưng không được truyền qua `auto_resolve_ticket()`. Sửa: đổi chữ ký hàm, luồn `user_id` xuống.

Bảy chỗ này gom riêng vào PR 6, không trộn vào các PR cơ học.

---

## 4. Vá chống lỗi — thiết kế

Thêm một helper vào `app/utils/i18n.py`:

```python
def pick_locale(table, code):
    """Chọn bản dịch theo locale, rơi về tiếng Việt nếu locale lạ."""
    return table.get(code, table[DEFAULT_LANG])
```

Mỗi chỗ hỏng chỉ bọc lại, không đụng nội dung dict:

```python
# truoc
return {"vi": ..., "en": ..., "zh": ...}[code]
# sau
return pick_locale({"vi": ..., "en": ..., "zh": ...}, code)
```

Áp cho `lt()` (`i18n.py:326`) và 8 dict còn lại.

**Đã kiểm chứng, không phải suy đoán:**

- **Thứ tự nạp section không thành vấn đề.** `i18n.py` là index 22 trong `SECTION_FILES`; `store_callback.py`=21, `store_menu.py`=19, `orders_delivery.py`=10 nạp *trước*. Vẫn chạy được vì `runtime_loader` đẩy lại namespace tích luỹ vào mọi module đã nạp sau mỗi vòng, và cả 10 chỗ dùng đều nằm trong thân hàm nên tra cứu bị hoãn tới lúc gọi. Đã xác nhận cùng một function object ở cả 6 file.
- **Không chỗ nào dựa vào việc nó nổ.** `grep -r "except KeyError" app/` ra 0 kết quả.
- **`vi` là fallback đúng** ở cả 10 chỗ — đó là `DEFAULT_LANG`.

**Hai chỗ hỏng theo kiểu khác, audit mô tả chưa đủ:**

| file:line | Kiểu lỗi |
|---|---|
| `app/handlers/store_callback.py:485` | `.get(lang, {})` rồi nổ `KeyError` ở câu lệnh kế |
| `app/services/store_menu.py:220` | `.get(lang)` không default, nổ `TypeError` ở dòng 323 |

**Không cần sửa:** `orders_delivery.py:315` và `payments_core.py:343` đã an toàn sẵn.

---

## 5. Rào test

File mới `tests/test_lt_call_sites.py`. Duyệt AST mọi `.py` dưới `app/`, không cần `load_modules()` — nhanh hơn và tránh hẳn loader.

Kiểm:

- Mọi `ast.Call` tên `lt` có đủ 4 tham số vị trí.
- Ba tham số vi/en/zh, khi là literal, không có hai cái byte-identical (trừ allowlist: emoji thuần, số, URL, brand token — lấy từ những gì thực sự có trong repo).
- Bộ placeholder giống hệt nhau giữa ba locale.
- Mỗi dict theo locale có đúng bộ key `{"vi","en","zh"}` và cùng bộ placeholder mỗi mục.

**Kết quả chạy thật trên repo hiện tại: 941 pass, 23 skip, 0 fail.** Thu được 307 call `lt()` và 14 dict literal. 23 skip là các `lt()` truyền f-string, không phân tích tĩnh được.

**Nói thẳng:** test này hôm nay không bắt được lỗi nào. Nó là rào chống hồi quy cho các PR sau, không phải máy dò bug. Giá trị của nó nằm ở PR 2-6.

Không ảnh hưởng `tests/test_lint_config.py` hay ruff per-file-ignores — cả hai chỉ liệt kê `SECTION_FILES`, file test mới không nằm trong đó.

---

## 6. Bảy PR

Mỗi PR chạy `pytest` và `ruff check app/ tests/` trước khi merge.

| PR | Nội dung | File | Key mới | Rủi ro |
|---|---|---|---|---|
| 1 | `pick_locale()` + 9 chỗ vá + `tests/test_lt_call_sites.py` | 7 | 0 | Rất thấp |
| 2 | Nhóm lỗi hệ thống | 3 | 4 | Thấp |
| 3 | Vòng đời đơn hàng | 6 | 30 | Trung bình |
| 4 | Bảo hành / rút tiền / partner | 4 | 24 | Trung bình |
| 5 | Phần còn lại (trừ 7 chỗ khó) | 10 | 36 | Thấp |
| 6 | 7 chỗ khó — đổi chữ ký, sửa vòng lặp | 3 | 7 | **Cao** |
| 7 | Nhất quán thuật ngữ, tiền tệ, menu | 5 | 0 | Thấp |

**PR 1 — rào an toàn.** Không đổi hành vi. Phải vào trước tiên, lý do ở §7.

**PR 2 — nhóm lỗi hệ thống.** `lifecycle.py:245`, `runtime_state.py:50`, `payments_core.py:82`. Chuỗi mọi user đều có thể gặp; `runtime_state.py:26` dùng lại key `maintenance` sẵn có. Giá trị trên rủi ro tốt nhất trong cả kế hoạch.

**PR 3 — vòng đời đơn hàng.** `payment_monitor.py`, `admin_orders.py` (services + handlers), `admin_refund.py`, `payment_generation.py`, `notifications_async.py`, `store_callback.py`. Nhóm khách thấy nhiều nhất và dính tiền. Soi kỹ placeholder tiền tệ — dùng `format_money()` thay cho `{x:,}đ`. Ba chỗ broadcast của `notifications_async.py` **để lại cho PR 6**.

**PR 4 — bảo hành, rút tiền, partner.** `admin_support.py`, `admin_withdrawals.py`, `admin_api.py`. Bốn chỗ của `support_automation.py` để lại cho PR 6.

**PR 5 — phần còn lại.** `priority_and_text.py`, `callback_router.py`, `games_waitlist.py`, `admin_background.py`, và các file 1-2 chuỗi.

**PR 6 — bảy chỗ khó.** Xem §3. Đây là PR duy nhất đổi chữ ký hàm và cấu trúc vòng lặp. Cần test riêng cho `auto_resolve_ticket()` và cho một broadcast, vì đây là chỗ dễ hồi quy nhất.

**PR 7 — nhất quán.** Từ §7 của audit: thống nhất `保修`/`质保`, `支付方式`/`付款方式`; bỏ `đ` hardcode ở `store_callback.py:18,20` và `flashsale_wheel.py:320-322`; dịch nhãn menu ngôn ngữ `i18n.py:343-345` theo locale người xem; truncate tên sản phẩm ở `store_menu.py` trước khi làm button label.

---

## 7. Vì sao PR 1 phải đi trước

1. PR 2-6 đụng đúng những hình dạng call-site mà test theo dõi. Có test trước thì mỗi PR tự kiểm, không phải soi lại sau.
2. Chưa có idiom chuẩn thì người viết PR sau sẽ copy pattern gần nhất — tức pattern đang hỏng — làm số chỗ dính `KeyError` **tăng lên**.
3. Hai thay đổi nằm ở nhánh code rời nhau (`lt()` và dict rời rạc, so với `STRINGS`/`t()` vốn đã `.get()`-safe), nên xếp PR 1 trước không làm chậm migration chút nào.

---

## 8. Không làm

- **Không** migrate 307 `lt()` sang key `STRINGS`. Đó là phase 4 của audit, chỉ đáng làm khi thực sự thêm ngôn ngữ thứ tư, và nó gấp ba khối lượng còn lại.
- **Không** đổi sang `gettext` / `.po` hay thư viện i18n ngoài. Bảng hiện tại parity 100%, có test gác; convention `<tg-emoji>` cộng cơ chế section-loader khiến chi phí đổi format lớn hơn lợi ích.
- **Không** đụng 349 chuỗi admin-only. Một `ADMIN_USER_ID` cố định, tiếng Việt là đúng chủ đích.
- **Không** đụng `app/web/**`. Panel một admin, đơn ngữ có chủ đích.

---

## 9. Ngoài phạm vi — đã thấy nhưng chưa tính

Khảo sát phát hiện thêm vài chuỗi customer-facing mà heuristic của audit bỏ sót. **Không** nằm trong con số 90/101:

- `app/services/admin_refund.py` quanh dòng 190 và 254/271 — các nhánh hoàn tiền qua ngân hàng.
- `app/jobs/admin_background.py` — lệnh `/rank` còn nhiều khối điều kiện chưa được gắn cờ, sau dòng 410.

Xử lý ở một đợt sau, hoặc gộp vào PR 5 nếu muốn quét sạch một lần. Ghi chú chi tiết nằm trong dữ liệu khảo sát, không phải trong repo.

Ngoài ra audit đã ghi hai điểm chưa xác minh vẫn còn nguyên: chuỗi tiếng Anh thuần không dấu và không `<tg-emoji>` bị heuristic bỏ sót, nên **450 là cận dưới**; và chất lượng dịch nghĩa `en`/`zh` cần người bản ngữ đọc.

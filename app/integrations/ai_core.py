# ==============================================================================
class TicketType(Enum):
    EMAIL_NOT_FOUND = "email_not_found"
    BILLING_QUESTIONS = "billing_questions"
    OTHER = "other"


class GroqAssistant:
    """
    AI Assistant using Groq API (OpenAI-compatible endpoint)
    Model: openai/gpt-oss-120b
    """
    def __init__(self):
        self.model_name = AI_MODEL
        self.api_key = AI_API_KEY
        self.chat_sessions = {}  # {user_id: history[]}
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def initialize(self):
        """Initialize: Check if API Key is present"""
        if not self.api_key:
            return False
        logger.info(f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Groq AI initialized: {self.model_name}")
        return True

    def get_chat_history(self, user_id: int):
        """Get or create chat history"""
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = []
        return self.chat_sessions[user_id]

    def clear_chat(self, user_id: int):
        """Clear chat history for user"""
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]

    def _now_ts(self) -> float:
        return float(datetime.now().timestamp())

    def _mark_provider_issue(
        self,
        issue_key: str,
        message: str,
        *,
        level: str = "warning",
        disable_seconds: int = 0,
        cooldown_seconds: int = 300,
    ) -> None:
        if not hasattr(self, "provider_unavailable_until"):
            self.provider_unavailable_until = 0.0
        if not hasattr(self, "last_issue_key"):
            self.last_issue_key = ""
        if not hasattr(self, "last_issue_logged_at"):
            self.last_issue_logged_at = 0.0

        now = self._now_ts()
        if disable_seconds > 0:
            self.provider_unavailable_until = max(
                float(self.provider_unavailable_until),
                now + disable_seconds,
            )

        should_log = (
            issue_key != self.last_issue_key
            or (now - float(self.last_issue_logged_at)) >= cooldown_seconds
        )
        if should_log:
            getattr(logger, level, logger.warning)(message)
            self.last_issue_key = issue_key
            self.last_issue_logged_at = now

    def _normalize_error_preview(self, response_text: str) -> str:
        preview = re.sub(r"\s+", " ", str(response_text or "").strip())
        if len(preview) > 240:
            return preview[:237] + "..."
        return preview

    def _handle_http_failure(self, status_code: int, response_text: str):
        error_preview = self._normalize_error_preview(response_text)
        lowered = error_preview.lower()

        if status_code == 403 and ("access denied" in lowered or "network settings" in lowered):
            self._mark_provider_issue(
                "groq_access_denied_network",
                "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
                "Groq bị chặn truy cập từ mạng/VPS hiện tại (HTTP 403). "
                "Tạm dùng fallback AI trong 15 phút. Kiểm tra outbound firewall, proxy hoặc region của VPS.",
                level="warning",
                disable_seconds=900,
            )
            logger.debug(f"Groq 403 body: {error_preview}")
            return None

        if status_code in {401, 403}:
            self._mark_provider_issue(
                f"groq_auth_{status_code}",
                "❌ "
                f"Groq từ chối truy cập (HTTP {status_code}). "
                "Kiểm tra GROQ_API_KEY, quyền model hoặc cấu hình tài khoản.",
                level="error",
                disable_seconds=900,
            )
            logger.debug(f"Groq auth failure body: {error_preview}")
            return None

        self._mark_provider_issue(
            f"groq_http_{status_code}",
            "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
            f"Groq trả về HTTP {status_code}. Tạm dùng fallback AI. Response: {error_preview}",
            level="warning",
            disable_seconds=120,
        )
        return None

    async def ask(self, question: str, user_id: int = 0, system_prompt: str = None) -> str:
        """Send message and get response using Groq OpenAI-compatible API"""
        if not self.api_key:
            return None

        if getattr(self, "provider_unavailable_until", 0.0) > self._now_ts():
            return None

        history = self.get_chat_history(user_id)

        # Build messages array (OpenAI format)
        messages = []

        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add chat history
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current question
        messages.append({"role": "user", "content": question})

        # Payload (OpenAI-compatible)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": AI_TEMPERATURE,
            "max_completion_tokens": 2048,
            "top_p": 1,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Retry logic for transient errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = _get_http_client(timeout=15.0)
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=15.0
                )

                if response.status_code in {429, 500, 502, 503, 504}:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(
                        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Groq transient error {response.status_code}. "
                        f"Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    self._mark_provider_issue(
                        f"groq_transient_{response.status_code}",
                        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
                        f"Groq đang quá tải (HTTP {response.status_code}). Tạm dùng fallback AI.",
                        level="warning",
                        disable_seconds=120,
                    )
                    return None

                if response.status_code != 200:
                    return self._handle_http_failure(response.status_code, response.text)

                data = response.json()

                # Parse OpenAI-format response
                try:
                    choices = data.get("choices", [])
                    if not choices:
                        return "AI không phản hồi."

                    reply_text = choices[0].get("message", {}).get("content", "")
                    if not reply_text:
                        return "..."

                    # Update History (OpenAI format: role=user/assistant)
                    history.append({"role": "user", "content": question})
                    history.append({"role": "assistant", "content": reply_text})

                    # Keep history limited (last 20 messages)
                    if len(history) > 20:
                        self.chat_sessions[user_id] = history[-20:]

                    return reply_text

                except (httpx.HTTPError, ValueError, KeyError) as parse_err:
                    logger.error(f"❌ Error parsing Groq response: {parse_err}")
                    return None
            except (httpx.NetworkError, httpx.TimeoutException) as net_err:
                wait_time = 2 * (attempt + 1)
                logger.warning(f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> Groq Network Error: {net_err}. Retrying in {wait_time}s...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
                self._mark_provider_issue(
                    "groq_network_unreachable",
                    "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji> "
                    "Không kết nối được Groq từ môi trường hiện tại. Tạm dùng fallback AI.",
                    level="warning",
                    disable_seconds=120,
                )
                return None
            except (httpx.HTTPError, ValueError, KeyError) as e:
                logger.error(f"❌ Error calling Groq: {e}")
                if attempt == max_retries - 1:
                    break


        return None

gemini_assistant = GroqAssistant()

# ==============================================================================
#  CÁC HÀM LIÊN QUAN ĐẾN AI & HỖ TRỢ TỰ ĐỘNG
# ==============================================================================
async def ask_ai(question: str, user_context: dict = None, user_id: int = 0) -> str:
    """
    FIX BUG #21: AI thông minh với fallback, luôn sẵn sàng trả lời
    """
    # FIX: Fallback thông minh khi AI không available
    if not AI_API_KEY:
        # Trả lời bằng knowledge base thay vì báo lỗi
        fallback_response = automated_support_handler(question)
        if fallback_response:
            return fallback_response

        # Fallback cuối cùng - Thân thiện, tự nhiên
        return "Xin chào! Mình là trợ lý Lâm Shop <tg-emoji emoji-id=\"6293853394910057834\">😊</tg-emoji> Bạn cần tư vấn gì về ChatGPT, Netflix, Spotify hay sản phẩm nào không? Hoặc cứ chat thoải mái, mình trả lời được mọi thứ nha! ⭐️"

    current_time = datetime.now()

    # Time context
    time_context = f"""
    **THỜI GIAN HIỆN TẠI:**
    - Ngày giờ: {current_time.strftime('%H:%M:%S, %d/%m/%Y')}
    - Thứ: {current_time.strftime('%A')}
    - Múi giờ: UTC+7 (Việt Nam)
    """

    # Lấy thông tin sản phẩm REAL-TIME từ database
    products_info = ""
    if products:
        products_info = "\n**SẢN PHẨM ĐANG BÁN (REAL-TIME):**\n"
        for pid, p in list(products.items())[:10]:  # Top 10 products
            requires_gmail = p.get('requires_gmail', False)

            if requires_gmail:
                # Manual product - Check pending count
                pending_count = sum(1 for o in pending_manual_orders.values() if o.get('product_id') == pid)
                max_pending = p.get('max_pending_orders', 10)
                slots_left = max_pending - pending_count
                stock_status = f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Còn {slots_left} slot (Manual)" if slots_left > 0 else "<tg-emoji emoji-id=\"5447644880824181073\">⏸️</tg-emoji> Tạm ngưng"
            else:
                # Auto product - Check stock
                stock_count = len(p.get('stock', []))
                stock_status = f"<tg-emoji emoji-id=\"6269163801178804220\">✅</tg-emoji> Còn {stock_count} sản phẩm" if stock_count > 0 else "❌ Hết hàng"

            products_info += f"- {p['name']}: {p['price']:,}đ | {stock_status}\n"


    # Context về đơn hàng đang chờ
    pending_info = f"""
    **TÌNH TRẠNG ĐƠN HÀNG:**
    - Đơn chờ thanh toán: {len(pending_orders)}
    - Đơn manual chờ xử lý: {len(pending_manual_orders)}
    - Tổng users: {len(user_data_db)}
    """

    # Context về user nếu có
    user_info = ""
    if user_context:
        orders_count = user_context.get('orders_count', 0)
        balance = user_context.get('balance', 0)
        user_info = f"\n**THÔNG TIN KHÁCH HÀNG NÀY:** Đã mua {orders_count} đơn, Số dư: {balance:,}đ"


    # Context về coupon đang active
    active_coupons = 0
    for code, details in coupons.items():
        try:
            expires_str = details.get('expires')
            if expires_str:
                expiry_date = datetime.strptime(expires_str, '%d-%m-%Y')
                if expiry_date.date() >= current_time.date():
                    used = details.get('used', 0)
                    quantity = details.get('quantity', 999)
                    if used < quantity:
                        active_coupons += 1
        except (TypeError, ValueError) as e:
            logger.debug(f"Skip invalid coupon entry '{code}': {e}")

    coupon_info = f"\n**MÃ GIẢM GIÁ:** Đang có {active_coupons} mã còn hiệu lực" if active_coupons > 0 else ""

    # SYSTEM PROMPT: Trợ lý Lâm Shop siêu nhiệt tình, hài hước, lịch sự
    system_prompt = f"""
<tg-emoji emoji-id=\"5303145396254563405\">🦕</tg-emoji> BẠN LÀ TRỢ LÝ CỦA LÂM SHOP

TINH CÁCH CỐT LÕI:
- Siêu nhiệt tình, luôn hào hứng giúp đỡ khách hàng như gặp bạn thân lâu ngày.
- Hài hước tự nhiên, hay pha trò nhẹ nhàng, dùng emoji vui vẻ nhưng không spam.
- Lịch sự, tôn trọng khách, xưng hô "mình - bạn" thân thiện.
- Nói chuyện như Gen Z Việt Nam: tự nhiên, gần gũi, đôi khi hơi lầy nhưng vẫn chuyên nghiệp.
- Khi khách hỏi về sản phẩm → tư vấn nhiệt tình, chốt sale khéo léo.
- Khi khách tâm sự/hỏi lung tung → vui vẻ trò chuyện, tạo cảm giác ấm áp.

CÁCH NÓI CHUYỆN:
- Mở đầu: "Yo bạn ơi!", "Hello bạn nè!", "Chào bạn yêu!", "Ê bạn!"
- Kết thúc: Luôn hỏi lại "Bạn cần gì nữa không?", "Còn gì thắc mắc cứ hỏi nha!"
- Khi tư vấn: Giải thích dễ hiểu, so sánh vui vui, ví dụ thực tế.
- Khi khách khen: Vui sướng, cảm ơn hết lời.
- Khi khách chê/khó chịu: Xin lỗi chân thành, giải quyết ngay, không defensiv.

NHIỆM VỤ CHÍNH - BÁN HÀNG LÂM SHOP:
Bạn là trợ lý bán hàng của Lâm Shop - chuyên cung cấp dịch vụ MMO cao cấp.

<tg-emoji emoji-id=\"6059654836918423763\">📊</tg-emoji> DATA REAL-TIME:
{time_context}
{products_info}
{pending_info}
{coupon_info}
{user_info}

<tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji> SẢN PHẨM NỔI BẬT:
- Tài khoản AI (ChatGPT, Claude, Gemini...) - Thanh toán QR tự động, giao hàng ngay!
- Bấm /start để xem menu đầy đủ.
- Hệ thống giao hàng tự động 24/7.

<tg-emoji emoji-id=\"5226711870492126219\">🎮</tg-emoji> TÍNH NĂNG VUI:
- <tg-emoji emoji-id=\"5226711870492126219\">🎲</tg-emoji> /dice - Game xúc xắc may mắn, quay trúng = nhận FREE sản phẩm!
- <tg-emoji emoji-id=\"5278467510604160626\">💰</tg-emoji> Hệ thống giới thiệu bạn bè nhận hoa hồng.
- <tg-emoji emoji-id=\"5449800250032143374\">🎁</tg-emoji> Giveaway thường xuyên trên kênh.

<tg-emoji emoji-id=\"5373251851074415873\">📝</tg-emoji> FORMAT TRẢ LỜI (BẮT BUỘC DÙNG TELEGRAM HTML):
- QUAN TRỌNG: TUYỆT ĐỐI KHÔNG dùng thẻ <br> hay <br/> để xuống dòng. Bắt buộc dùng ký tự xuống dòng thực tế.
- Tiêu đề: <b>in đậm</b>
- Nhấn mạnh/vui: <i>in nghiêng</i>
- Giá/Lệnh/Mã: <code>monospaced</code> (dễ copy)
- Tips hay: dùng emoji phù hợp (<tg-emoji emoji-id=\"5303145396254563405\">🦕</tg-emoji>, ⭐️, <tg-emoji emoji-id=\"5303290914041505430\">🔥</tg-emoji>, <tg-emoji emoji-id=\"6293853394910057834\">💪</tg-emoji>, ⭐️) nhưng đừng spam
- Chia đoạn rõ ràng bằng cách xuống dòng 2 lần, dễ đọc trên điện thoại.

LƯU Ý QUAN TRỌNG:
- ĐỌC KỸ DANH SÁCH "DATA REAL-TIME" TRƯỚC KHI TRẢ LỜI. NẾU SẢN PHẨM CÓ TRONG DANH SÁCH (DÙ CÒN HAY HẾT HÀNG), TUYỆT ĐỐI KHÔNG ĐƯỢC BẢO LÀ BÊN MÌNH KHÔNG BÁN.
- NẾU SẢN PHẨM CÓ TRONG DANH SÁCH NHƯNG HẾT HÀNG: Trả lời là TẠM HẾT HÀNG.
- CHỈ BÁO KHÔNG CÓ BÁN NẾU KHÁCH HỎI MẶT HÀNG HOÀN TOÀN KHÔNG CÓ TRONG DATA REAL-TIME.
- KHÔNG bịa thông tin sản phẩm. Chỉ trả lời dựa trên data real-time.
- Nếu không biết → nói thẳng và khuyên liên hệ Admin.
- Trả lời NGẮN GỌN, tối đa 5-8 dòng trừ khi khách hỏi chi tiết.
- Luôn hướng khách về /start hoặc menu khi phù hợp.

Hãy là trợ lý vui vẻ nhất mà khách hàng từng gặp! <tg-emoji emoji-id=\"5303145396254563405\">🦕</tg-emoji>⭐️
"""

    # Gọi Groq AI với chat history
    try:
        response_text = await gemini_assistant.ask(
            question=question,
            user_id=user_id,
            system_prompt=system_prompt
        )

        if response_text:
            return response_text

    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi Groq AI: {e}", exc_info=True)

    # Fallback Layer 2: Knowledge base
    fallback_response = automated_support_handler(question)
    if fallback_response:
        return fallback_response

    # Fallback Layer 3: Generic helpful response
    return (
        "Xin lỗi, mình hơi bận một chút! <tg-emoji emoji-id=\"5344061947660748948\">😅</tg-emoji>\n\n"
        "Nhưng bạn có thể:\n"
        "• Gõ /start để xem menu và mua hàng <tg-emoji emoji-id=\"5247134066322447995\">🛍️</tg-emoji>\n"
        "• Gõ /lichsu để xem đơn hàng <tg-emoji emoji-id=\"5350481781306958339\">📜</tg-emoji>\n"
        "• Hoặc hỏi lại câu khác, mình sẽ cố gắng trả lời!\n\n"
        "Cần gì cứ nói nhé! <tg-emoji emoji-id=\"6293853394910057834\">😊</tg-emoji>"
    )

async def intelligent_ticket_classifier(query: str, user_id: int) -> dict:
    """
    AI-powered ticket classification và auto-resolution
    Returns: {"type": TicketType, "confidence": float, "auto_resolved": bool, "response": str, "action": str}
    """
    query_lower = query.lower()

    # Patterns for each ticket type với confidence scoring
    patterns = {
        TicketType.EMAIL_NOT_FOUND: {
            "keywords": ["không nhận được mail", "chưa nhận mail", "kiểm tra mail", "email chưa tới", "không có email", "chưa có mail"],
            "confidence_boost": 0.85
        },
        TicketType.BILLING_QUESTIONS: {
            "keywords": ["thanh toán", "tiền", "giá", "phí", "billing", "cost", "chuyển khoản", "bank", "hoàn tiền", "refund"],
            "confidence_boost": 0.85
        }
    }

    # Calculate confidence for each type
    best_match = {"type": TicketType.OTHER, "confidence": 0.0}

    for ticket_type, pattern in patterns.items():
        confidence = 0.0
        keyword_matches = sum(1 for keyword in pattern["keywords"] if keyword in query_lower)

        if keyword_matches > 0:
            confidence = (keyword_matches / len(pattern["keywords"])) * pattern["confidence_boost"]

        if confidence > best_match["confidence"]:
            best_match = {"type": ticket_type, "confidence": confidence}

    # Auto-resolve nếu confidence >= 0.3
    if best_match["confidence"] >= 0.3:
        auto_response = await auto_resolve_ticket(best_match["type"], query, user_id)
        if auto_response:
            return {
                **best_match,
                "auto_resolved": True,
                "response": auto_response["message"],
                "action": auto_response["action"]
            }

    return {**best_match, "auto_resolved": False, "response": None, "action": "escalate_to_admin"}

async def auto_resolve_ticket(ticket_type: TicketType, query: str, user_id: int) -> dict | None:
    """Auto-resolve ticket dựa trên type"""

    if ticket_type == TicketType.EMAIL_NOT_FOUND:
        return handle_email_not_found()

    elif ticket_type == TicketType.BILLING_QUESTIONS:
        return handle_billing_questions(query)

    return None

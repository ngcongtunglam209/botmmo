"""Ngon ngu phai resolve theo NGUOI NHAN, khong theo nguoi thao tac.

Hai hinh dang de hong nhat cua dot i18n, gom rieng vao day:

1. Vong lap broadcast: text dung MOT lan roi gui cho tat ca. Bug nay khong lam
   test do va khong sinh exception - no chi lam khach en/zh nhan tieng Viet.
2. Ham auto-resolve khong nhan `user_id`, nen khong co gi de resolve ngon ngu.
"""

from __future__ import annotations

import pytest

from app.core.runtime_loader import load_modules

VI_USER = 910000001
EN_USER = 910000002
ZH_USER = 910000003


@pytest.fixture
def mods():
    return load_modules()


@pytest.fixture
def langs(mods):
    """Gan ngon ngu cho ba user gia, roi tra lai nguyen trang cho test sau."""
    i18n = mods["app.utils.i18n"]
    store = i18n.user_data_db
    before = {uid: store.get(str(uid)) for uid in (VI_USER, EN_USER, ZH_USER)}
    for uid, code in ((VI_USER, "vi"), (EN_USER, "en"), (ZH_USER, "zh")):
        store[str(uid)] = {"lang": code, "balance": 0}
    yield i18n
    for uid, previous in before.items():
        if previous is None:
            store.pop(str(uid), None)
        else:
            store[str(uid)] = previous


# --- render_all_locales: nen tang cua cac vong lap broadcast -----------------


def test_render_all_locales_covers_every_supported_language(langs):
    rendered = langs.render_all_locales("broadcast_back_in_stock", success="", tag="",
                                        stat="", loading="", product="Netflix", count=3)
    assert set(rendered) == set(langs.SUPPORTED_LANGS)
    assert len({rendered[code] for code in langs.SUPPORTED_LANGS}) == 3, (
        "ba locale phai ra ba chuoi khac nhau, neu khong thi ban dich bi trung"
    )


def test_broadcast_picks_text_by_recipient_not_by_sender(langs):
    """Mo phong dung hinh dang cua vong lap broadcast sau khi sua."""
    rendered = langs.render_all_locales("broadcast_out_of_stock", error="", tag="",
                                        sos="", globe="", product="Netflix", admin="lam")
    received = {
        uid: langs.pick_locale(rendered, langs.get_user_lang(uid))
        for uid in (VI_USER, EN_USER, ZH_USER)
    }
    assert received[VI_USER] != received[EN_USER] != received[ZH_USER]
    assert "HẾT HÀNG" in received[VI_USER]
    assert "OUT OF STOCK" in received[EN_USER]
    assert "缺货" in received[ZH_USER]


def test_pick_locale_falls_back_when_recipient_language_is_unknown(langs):
    rendered = langs.render_all_locales("broadcast_out_of_stock", error="", tag="",
                                        sos="", globe="", product="Netflix", admin="lam")
    assert langs.pick_locale(rendered, "ja") == rendered[langs.DEFAULT_LANG]


# --- auto_resolve_ticket: chu ky ham phai luon duoc user_id -----------------


def test_support_helpers_accept_a_user_id(mods):
    """Chan viec ai do bo lai tham so `user_id` khoi hai ham nay."""
    import inspect

    support = mods["app.services.support_automation"]
    assert "user_id" in inspect.signature(support.handle_email_not_found).parameters
    assert "user_id" in inspect.signature(support.handle_billing_questions).parameters


@pytest.mark.parametrize(
    "uid,needle",
    [
        (VI_USER, "HƯỚNG DẪN TÌM EMAIL"),
        (EN_USER, "HOW TO FIND YOUR ORDER EMAIL"),
        (ZH_USER, "如何找到订单邮件"),
    ],
)
def test_email_not_found_answers_in_the_asker_language(mods, langs, uid, needle):
    support = mods["app.services.support_automation"]
    assert needle in support.handle_email_not_found(uid)["message"]


@pytest.mark.parametrize(
    "uid,needle",
    [
        (VI_USER, "CHÍNH SÁCH HOÀN TIỀN"),
        (EN_USER, "REFUND POLICY"),
        (ZH_USER, "退款政策"),
    ],
)
def test_billing_questions_answer_in_the_asker_language(mods, langs, uid, needle):
    support = mods["app.services.support_automation"]
    answer = support.handle_billing_questions("cho tôi hoàn tiền", uid)
    assert needle in answer["message"]


@pytest.mark.asyncio
async def test_auto_resolve_ticket_threads_user_id_down(mods, langs):
    """user_id da co san o auto_resolve_ticket; kiem tra no thuc su di tiep."""
    ai_core = mods["app.integrations.ai_core"]
    ticket_type = ai_core.TicketType

    result = await ai_core.auto_resolve_ticket(ticket_type.EMAIL_NOT_FOUND, "khong thay mail", EN_USER)
    assert result is not None
    assert "HOW TO FIND YOUR ORDER EMAIL" in result["message"]

    result = await ai_core.auto_resolve_ticket(ticket_type.BILLING_QUESTIONS, "refund", ZH_USER)
    assert result is not None
    assert "退款政策" in result["message"]

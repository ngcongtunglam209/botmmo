"""Rao chan hoi quy cho lop dich inline (`lt()`) va cac dict theo locale.

Toan bo kiem tra chay tren AST, khong goi `load_modules()`: nhanh hon va tranh
han side effect cua section loader. Muc tieu khong phai bat bug hom nay ma giu
cho cac PR i18n tiep theo khong lam lech ba ban dich vi/en/zh.
"""

import ast
import re
import string
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
LOCALES = ("vi", "en", "zh")
LOCALE_KEYS = frozenset(LOCALES)

# Chuoi giong het nhau giua ba locale thuong la loi copy-paste, tru khi noi dung
# von khong phu thuoc ngon ngu: emoji thuan, so, URL, hoac ten rieng.
BRAND_TOKENS = frozenset(
    {
        "api",
        "binance pay",
        "gmail",
        "id",
        "nowpayments",
        "qr",
        "telegram",
        "usdt",
        "vnd",
    }
)

_TG_EMOJI_TAG = re.compile(r"<tg-emoji[^>]*>.*?</tg-emoji>", re.DOTALL)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_URL = re.compile(r"https?://\S+")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
# Chu cai co nghia trong ba ngon ngu: latin (co dau) + khoi CJK.
_MEANINGFUL = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ一-鿿]+")


def _iter_app_sources():
    for path in sorted(APP_DIR.rglob("*.py")):
        yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _rel(path):
    return path.relative_to(APP_DIR.parent).as_posix()


def _is_locale_invariant(text):
    """True khi chuoi khong mang noi dung phu thuoc ngon ngu."""
    stripped = _TG_EMOJI_TAG.sub(" ", text)
    stripped = _URL.sub(" ", stripped)
    stripped = _HTML_TAG.sub(" ", stripped)
    stripped = _PLACEHOLDER.sub(" ", stripped)
    words = _MEANINGFUL.findall(stripped)
    if not words:
        return True
    return " ".join(words).strip().lower() in BRAND_TOKENS


def _placeholders(text):
    """Bo ten placeholder cua mot chuoi format. None khi chuoi khong parse duoc."""
    names = set()
    try:
        for _, field, _, _ in string.Formatter().parse(text):
            if field is None:
                continue
            base = field.split("[")[0].split(".")[0].strip()
            names.add(base)
    except ValueError:
        return None
    return names


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


# --- Thu thap ---------------------------------------------------------------


def _collect_lt_calls():
    out = []
    for path, tree in _iter_app_sources():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "lt":
                continue
            out.append((f"{_rel(path)}:{node.lineno}", node))
    return out


def _collect_locale_dicts():
    """Moi dict literal co dung bo khoa {vi,en,zh}, kem node cha truc tiep."""
    out = []
    for path, tree in _iter_app_sources():
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[id(child)] = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict) or not node.keys:
                continue
            keys = [_const_str(k) for k in node.keys]
            if any(k is None for k in keys) or set(keys) != LOCALE_KEYS:
                continue
            out.append((f"{_rel(path)}:{node.lineno}", node, parents.get(id(node))))
    return out


LT_CALLS = _collect_lt_calls()
LOCALE_DICTS = _collect_locale_dicts()
_LT_IDS = [site for site, _ in LT_CALLS]
_DICT_IDS = [site for site, _, _ in LOCALE_DICTS]


def test_corpus_is_not_empty():
    """Neu thu thap ve rong thi moi test duoi deu pass gia."""
    assert len(LT_CALLS) > 200
    assert len(LOCALE_DICTS) > 5


# --- lt() -------------------------------------------------------------------


@pytest.mark.parametrize("site,node", LT_CALLS, ids=_LT_IDS)
def test_lt_has_four_positional_args(site, node):
    assert len(node.args) == 4, f"{site}: lt() can dung 4 tham so vi tri (user_id, vi, en, zh)"
    assert not any(kw.arg in LOCALES for kw in node.keywords), (
        f"{site}: ba ban dich phai truyen vi tri, khong phai keyword"
    )


def _literal_translations(node):
    if len(node.args) != 4:
        return None
    values = [_const_str(arg) for arg in node.args[1:4]]
    if any(value is None for value in values):
        return None
    return dict(zip(LOCALES, values))


@pytest.mark.parametrize("site,node", LT_CALLS, ids=_LT_IDS)
def test_lt_translations_differ(site, node):
    table = _literal_translations(node)
    if table is None:
        pytest.skip("tham so khong phai literal, khong phan tich tinh duoc")
    for left in range(len(LOCALES)):
        for right in range(left + 1, len(LOCALES)):
            a, b = LOCALES[left], LOCALES[right]
            if table[a] != table[b]:
                continue
            assert _is_locale_invariant(table[a]), (
                f"{site}: ban dich {a!r} va {b!r} giong het nhau: {table[a]!r}"
            )


@pytest.mark.parametrize("site,node", LT_CALLS, ids=_LT_IDS)
def test_lt_placeholders_match(site, node):
    table = _literal_translations(node)
    if table is None:
        pytest.skip("tham so khong phai literal, khong phan tich tinh duoc")
    sets = {}
    for code, text in table.items():
        names = _placeholders(text)
        assert names is not None, f"{site}: chuoi {code!r} co dau ngoac nhon khong hop le"
        sets[code] = names
    assert sets["vi"] == sets["en"] == sets["zh"], (
        f"{site}: bo placeholder lech nhau: "
        + ", ".join(f"{code}={sorted(sets[code])}" for code in LOCALES)
    )


# --- Dict theo locale -------------------------------------------------------


def _flatten(value, prefix=""):
    """Tra ve {duong_dan: chuoi} cho dict/tuple/list long nhau. None neu gap node la."""
    if isinstance(value, ast.Constant):
        return {prefix: value.value} if isinstance(value.value, str) else {}
    if isinstance(value, ast.Dict):
        out = {}
        for key, item in zip(value.keys, value.values):
            name = _const_str(key)
            if name is None:
                return None
            nested = _flatten(item, f"{prefix}.{name}" if prefix else name)
            if nested is None:
                return None
            out.update(nested)
        return out
    if isinstance(value, (ast.Tuple, ast.List)):
        out = {}
        for index, item in enumerate(value.elts):
            nested = _flatten(item, f"{prefix}[{index}]" if prefix else f"[{index}]")
            if nested is None:
                return None
            out.update(nested)
        return out
    return None


@pytest.mark.parametrize("site,node,parent", LOCALE_DICTS, ids=_DICT_IDS)
def test_locale_dict_shapes_match(site, node, parent):
    tables = {}
    for key, value in zip(node.keys, node.values):
        flat = _flatten(value, "")
        if flat is None:
            pytest.skip("gia tri khong phai literal, khong phan tich tinh duoc")
        tables[_const_str(key)] = flat
    assert tables["vi"].keys() == tables["en"].keys() == tables["zh"].keys(), (
        f"{site}: cac locale khong cung bo truong: "
        + ", ".join(f"{code}={sorted(tables[code])}" for code in LOCALES)
    )
    for field in tables["vi"]:
        sets = {}
        for code in LOCALES:
            names = _placeholders(tables[code][field])
            assert names is not None, f"{site}: {code}.{field} co dau ngoac nhon khong hop le"
            sets[code] = names
        assert sets["vi"] == sets["en"] == sets["zh"], (
            f"{site}: placeholder lech o truong {field!r}: "
            + ", ".join(f"{code}={sorted(sets[code])}" for code in LOCALES)
        )


@pytest.mark.parametrize("site,node,parent", LOCALE_DICTS, ids=_DICT_IDS)
def test_locale_dict_is_not_indexed_unsafely(site, node, parent):
    """Cam `{...}[lang]` truc tiep: locale la se nem KeyError giua luong gui tin.

    Idiom dung la `pick_locale({...}, lang)` (hoac `.get(lang, <mac dinh>)`).
    Dict gan vao hang module duoc bo qua: cho doc no chiu trach nhiem fallback.
    """
    if isinstance(parent, ast.Subscript):
        pytest.fail(
            f"{site}: dict theo locale bi index truc tiep. Dung pick_locale(<dict>, <code>)."
        )
    if isinstance(parent, ast.Call):
        func = parent.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name == "get" and len(parent.args) < 2:
            pytest.fail(f"{site}: .get() khong co gia tri mac dinh. Dung pick_locale(...).")

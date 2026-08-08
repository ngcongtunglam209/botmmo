"""Trình đọc .xlsx bằng thư viện chuẩn.

Đây là đầu vào cho script cộng tiền vào ví khách, nên đọc lệch một cột là cộng
nhầm người.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import xlsx_reader  # noqa: E402


def write(path, rows):
    openpyxl = pytest.importorskip("openpyxl")
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(list(row))
    book.save(path)
    return path


def test_column_index_handles_multi_letter_references():
    assert xlsx_reader.column_index("A1") == 0
    assert xlsx_reader.column_index("B2") == 1
    assert xlsx_reader.column_index("Z9") == 25
    assert xlsx_reader.column_index("AA1") == 26
    assert xlsx_reader.column_index("AB1") == 27


def test_reads_header_and_values(tmp_path):
    path = write(tmp_path / "a.xlsx", [["chatId", "balance"], ["111", 50000]])

    assert xlsx_reader.read_rows(path) == [["chatId", "balance"], ["111", 50000]]


def test_empty_cells_keep_columns_aligned(tmp_path):
    """Ô rỗng bị lược khỏi XML; thiếu chèn None là mọi cột sau bị dịch trái."""
    path = write(tmp_path / "b.xlsx", [["a", "b", "c"], ["x", None, "z"]])

    assert xlsx_reader.read_rows(path)[1] == ["x", None, "z"]


def test_whole_numbers_stay_integers(tmp_path):
    """Số dư phải là int, không phải 50000.0."""
    path = write(tmp_path / "c.xlsx", [["balance"], [50000]])

    value = xlsx_reader.read_rows(path)[1][0]
    assert value == 50000 and isinstance(value, int)


def test_decimals_are_preserved(tmp_path):
    path = write(tmp_path / "d.xlsx", [["balance"], [3542.4]])

    assert xlsx_reader.read_rows(path)[1][0] == pytest.approx(3542.4)


def test_booleans_survive(tmp_path):
    path = write(tmp_path / "e.xlsx", [["isBlocked"], [True], [False]])

    rows = xlsx_reader.read_rows(path)
    assert rows[1][0] is True
    assert rows[2][0] is False


def test_unicode_strings_survive(tmp_path):
    path = write(tmp_path / "f.xlsx", [["name"], ["Lâm Tùng"], ["Khánh"]])

    rows = xlsx_reader.read_rows(path)
    assert rows[1][0] == "Lâm Tùng"
    assert rows[2][0] == "Khánh"


def test_relationship_targets_are_normalised():
    # openpyxl ghi đường tuyệt đối, Excel ghi tương đối. Cả hai phải ra một chỗ.
    assert xlsx_reader._normalize_target("/xl/worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert xlsx_reader._normalize_target("worksheets/sheet1.xml") == "xl/worksheets/sheet1.xml"
    assert xlsx_reader._normalize_target("xl/worksheets/sheet2.xml") == "xl/worksheets/sheet2.xml"


def test_matches_openpyxl_on_a_mixed_sheet(tmp_path):
    """Bằng chứng chính: cùng file, cùng kết quả với thư viện đã được kiểm chứng."""
    openpyxl = pytest.importorskip("openpyxl")
    rows = [
        ["chatId", "balance", "username", "isBlocked"],
        ["111", 50000, "khach_a", False],
        ["222", 3542.4, None, True],
        ["333", 0, "Lâm Tùng", False],
        [None, None, None, None],
    ]
    path = write(tmp_path / "g.xlsx", rows)

    mine = xlsx_reader.read_rows(path)
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    theirs = [list(row) for row in book.worksheets[0].iter_rows(values_only=True)]

    assert len(mine) == len(theirs)
    for row_mine, row_theirs in zip(mine, theirs):
        padded = row_mine + [None] * (len(row_theirs) - len(row_mine))
        assert padded == list(row_theirs)


def test_a_file_that_is_not_a_zip_is_rejected(tmp_path):
    """Đổi tên .csv thành .xlsx là lỗi hay gặp; phải báo chứ không đọc bừa."""
    import zipfile

    path = tmp_path / "khong-phai-xlsx.xlsx"
    path.write_text("chatId,balance\n111,5000\n", encoding="utf-8")

    with pytest.raises(zipfile.BadZipFile):
        xlsx_reader.read_rows(path)

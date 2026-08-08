"""Đọc file .xlsx chỉ bằng thư viện chuẩn.

Server chạy bot bằng Docker nên trên host không có openpyxl, và Debian mới chặn
`pip install` ngoài venv. Script bảo trì phải chạy được với `python3` trần.

.xlsx là một file zip chứa XML. Ở đây chỉ đọc sheet đầu tiên và chỉ lấy giá trị
ô — đủ cho việc nhập dữ liệu, không xử lý công thức hay định dạng.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL_REFERENCE = re.compile(r"([A-Z]+)(\d+)")


def column_index(reference: str) -> int:
    """A -> 0, B -> 1, AA -> 26."""
    match = CELL_REFERENCE.match(reference)
    letters = match.group(1) if match else reference
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Bảng chuỗi dùng chung; ô kiểu 's' lưu chỉ số trỏ vào đây."""
    try:
        raw = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    strings = []
    for item in ElementTree.fromstring(raw).findall(f"{NAMESPACE}si"):
        # Một chuỗi có thể bị chẻ thành nhiều đoạn <t> khi định dạng khác nhau.
        strings.append("".join(node.text or "" for node in item.iter(f"{NAMESPACE}t")))
    return strings


def _first_sheet_name(archive: zipfile.ZipFile) -> str:
    """Sheet đầu tiên không phải lúc nào cũng là sheet1.xml."""
    try:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    except KeyError:
        return "xl/worksheets/sheet1.xml"
    sheets = workbook.find(f"{NAMESPACE}sheets")
    if sheets is None or len(sheets) == 0:
        return "xl/worksheets/sheet1.xml"

    relationship_id = None
    for key, value in sheets[0].attrib.items():
        if key.endswith("}id"):
            relationship_id = value
            break
    if relationship_id is None:
        return "xl/worksheets/sheet1.xml"

    try:
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return "xl/worksheets/sheet1.xml"
    for relationship in rels:
        if relationship.get("Id") == relationship_id:
            return _normalize_target(relationship.get("Target", ""))
    return "xl/worksheets/sheet1.xml"


def _normalize_target(target: str) -> str:
    """Target có thể tương đối ('worksheets/s.xml') hoặc tuyệt đối ('/xl/worksheets/s.xml')."""
    path = target.lstrip("/")
    return path if path.startswith("xl/") else f"xl/{path}"


def _cell_value(cell, strings: list[str]):
    """Giá trị một ô: chuỗi, số, bool, hoặc None."""
    cell_type = cell.get("t", "n")

    if cell_type == "inlineStr":
        node = cell.find(f"{NAMESPACE}is")
        return "".join(t.text or "" for t in node.iter(f"{NAMESPACE}t")) if node is not None else None

    value_node = cell.find(f"{NAMESPACE}v")
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text

    if cell_type == "s":
        try:
            return strings[int(raw)]
        except (ValueError, IndexError):
            return None
    if cell_type == "b":
        return raw == "1"
    if cell_type in ("str", "e"):
        return raw
    try:
        # Số nguyên giữ nguyên kiểu int để số dư không bị nhiễu dấu phẩy động.
        number = float(raw)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def read_rows(path: Path) -> list[list]:
    """Mọi dòng của sheet đầu tiên, mỗi dòng là list giá trị theo cột."""
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        sheet_path = _first_sheet_name(archive)
        try:
            sheet = ElementTree.fromstring(archive.read(sheet_path))
        except KeyError:
            raise ValueError(f"{path} không có sheet nào đọc được") from None

    rows = []
    for row in sheet.iter(f"{NAMESPACE}row"):
        values: list = []
        for cell in row.findall(f"{NAMESPACE}c"):
            reference = cell.get("r")
            position = column_index(reference) if reference else len(values)
            # Ô rỗng bị lược khỏi XML, phải chèn None để cột không bị lệch.
            while len(values) < position:
                values.append(None)
            values.append(_cell_value(cell, strings))
        rows.append(values)
    return rows

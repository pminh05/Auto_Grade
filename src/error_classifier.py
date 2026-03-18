"""
error_classifier.py - Phân loại lỗi và mức độ nghiêm trọng.

Phân loại lỗi:
  syntax        - lỗi cú pháp Python (SyntaxError)
  logic         - logic đúng nhưng sai tham số nhỏ (axis, ascending, threshold)
  algorithm     - dùng sai hàm/thuật toán (argmax thay vì sum)
  data_handling - xử lý data sai (sai tên cột, sai biến filter, thiếu bước)

Mức độ nghiêm trọng:
  critical - code không chạy được (SyntaxError, NameError)
  major    - code chạy nhưng kết quả sai hoàn toàn
  minor    - kết quả gần đúng, sai nhỏ (format, sai axis nhỏ)
"""

from __future__ import annotations

import ast
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_syntax_error(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return False, ""
    except SyntaxError as exc:
        return True, str(exc)


def _has_name_error_risk(code: str) -> list[str]:
    """Tìm các NameError tiềm năng (biến dùng trước khi khai báo)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    defined: set[str] = set()
    risks: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined and node.id not in dir(__builtins__):
                risks.append(node.id)

    return risks


# ---------------------------------------------------------------------------
# Error classifiers per diff entry
# ---------------------------------------------------------------------------

def _classify_missing_node(node: dict) -> dict:
    ntype = node.get("type", "")
    label = node.get("label", "")
    operation = node.get("operation", "")

    severity = "major"
    etype = "algorithm"
    desc = f"Thiếu bước: {label}"

    if ntype == "print_output":
        severity = "minor"
        etype = "logic"
        desc = "Thiếu câu lệnh print để in kết quả"
    elif ntype == "pandas_sort":
        severity = "major"
        etype = "logic"
        desc = "Thiếu bước sắp xếp DataFrame (sort_values)"
    elif ntype in ("array_creation", "matrix_creation"):
        severity = "major"
        etype = "algorithm"
        desc = f"Thiếu bước tạo mảng/ma trận: {label}"
    elif ntype == "dataframe_creation":
        severity = "critical"
        etype = "algorithm"
        desc = "Thiếu bước tạo DataFrame"
    elif ntype == "numpy_reduction":
        severity = "major"
        etype = "algorithm"
        desc = f"Thiếu phép tính: {operation}"
    elif ntype == "boolean_indexing":
        severity = "major"
        etype = "data_handling"
        desc = f"Thiếu bước lọc dữ liệu: {label}"

    return {
        "type": etype,
        "severity": severity,
        "description": desc,
        "node": node,
        "source": "missing_node",
    }


def _classify_wrong_node(wrong_entry: dict) -> list[dict]:
    errors = []
    ref_node = wrong_entry.get("ref_node", {})
    stu_node = wrong_entry.get("student_node", {})
    differences = wrong_entry.get("differences", [])

    if not differences:
        # Nút khớp một phần nhưng không có diff cụ thể → bỏ qua
        return []

    for d in differences:
        aspect = d.get("aspect", "")
        msg = d.get("message", "")

        if aspect == "wrong_function":
            exp = d.get("expected", "")
            act = d.get("actual", "")
            # So sánh gia đình hàm để xác định severity
            reduction_family = {"sum", "mean", "max", "min", "argmax", "argmin", "std", "var"}
            if exp in reduction_family and act in reduction_family:
                severity = "major"
            else:
                severity = "major"
            errors.append(
                {
                    "type": "algorithm",
                    "severity": severity,
                    "description": msg,
                    "expected_code": f"{exp}(...)",
                    "actual_code": f"{act}(...)",
                    "node": stu_node,
                    "ref_node": ref_node,
                    "source": "wrong_function",
                }
            )

        elif aspect == "wrong_axis":
            errors.append(
                {
                    "type": "logic",
                    "severity": "major",
                    "description": msg,
                    "expected_code": f"axis={d.get('expected')}",
                    "actual_code": f"axis={d.get('actual')}",
                    "node": stu_node,
                    "ref_node": ref_node,
                    "source": "wrong_axis",
                }
            )

        elif aspect == "wrong_filter":
            errors.append(
                {
                    "type": "logic",
                    "severity": "major",
                    "description": msg,
                    "expected_code": d.get("expected", ""),
                    "actual_code": d.get("actual", ""),
                    "node": stu_node,
                    "ref_node": ref_node,
                    "source": "wrong_filter",
                }
            )

        elif aspect == "wrong_sort_order":
            errors.append(
                {
                    "type": "logic",
                    "severity": "minor",
                    "description": msg,
                    "expected_code": f"ascending={d.get('expected')}",
                    "actual_code": f"ascending={d.get('actual')}",
                    "node": stu_node,
                    "ref_node": ref_node,
                    "source": "wrong_sort_order",
                }
            )

        elif aspect == "wrong_column_value":
            errors.append(
                {
                    "type": "data_handling",
                    "severity": "major",
                    "description": msg,
                    "expected_code": d.get("expected", ""),
                    "actual_code": d.get("actual", ""),
                    "node": stu_node,
                    "ref_node": ref_node,
                    "source": "wrong_column_value",
                }
            )

    return errors


def _detect_format_errors(student_code: str) -> list[dict]:
    """Phát hiện lỗi format chuỗi phổ biến."""
    errors = []
    # Lỗi thiếu *1000 cho tong_loi_nhuan
    if "tong_loi_nhuan" in student_code:
        if ":,.0f}" in student_code and "*1000" not in student_code:
            errors.append(
                {
                    "type": "logic",
                    "severity": "minor",
                    "description": "Thiếu nhân 1000 khi in tong_loi_nhuan (đơn vị VND triệu → đồng)",
                    "expected_code": "{tong_loi_nhuan*1000:,.0f}",
                    "actual_code": "{tong_loi_nhuan:,.0f}",
                    "node": {},
                    "ref_node": {},
                    "source": "format_error",
                }
            )
    return errors


def _detect_operator_errors(student_code: str) -> list[dict]:
    """Phát hiện một số lỗi toán tử phổ biến."""
    errors = []
    # Phát hiện dùng + thay vì * khi tính doanh thu
    if re.search(r"gia_ban\s*\+\s*so_luong_ban", student_code):
        errors.append(
            {
                "type": "algorithm",
                "severity": "major",
                "description": "Dùng phép cộng (+) thay vì nhân (*) khi tính doanh thu",
                "expected_code": "gia_ban * so_luong_ban",
                "actual_code": "gia_ban + so_luong_ban",
                "node": {},
                "ref_node": {},
                "source": "operator_error",
            }
        )
    return errors


def _detect_column_name_errors(student_code: str) -> list[dict]:
    """Phát hiện lỗi tên cột/giá trị phổ biến trong Pandas."""
    errors = []

    # Sai tên phòng ban: 'KinhDoanh' thay vì 'Kinh doanh'
    if re.search(r"['\"]KinhDoanh['\"]", student_code):
        errors.append(
            {
                "type": "data_handling",
                "severity": "major",
                "description": "Sai tên phòng ban: 'KinhDoanh' cần phải là 'Kinh doanh' (có dấu cách và dấu thanh)",
                "expected_code": "df_employees['PhongBan'] == 'Kinh doanh'",
                "actual_code": "df_employees['PhongBan'] == 'KinhDoanh'",
                "node": {},
                "ref_node": {},
                "source": "wrong_column_value",
            }
        )

    # Sai tên cột: 'KinhNghiem' thay vì 'NamKinhNghiem'
    if re.search(r"['\"]KinhNghiem['\"]", student_code):
        errors.append(
            {
                "type": "data_handling",
                "severity": "critical",
                "description": "Sai tên cột: 'KinhNghiem' không tồn tại, cần dùng 'NamKinhNghiem'",
                "expected_code": "df_employees['NamKinhNghiem']",
                "actual_code": "df_employees['KinhNghiem']",
                "node": {},
                "ref_node": {},
                "source": "wrong_column_value",
            }
        )

    # Sai ngưỡng so sánh NamKinhNghiem: dùng >= thay vì >
    if re.search(r"NamKinhNghiem.*>=.*3", student_code):
        errors.append(
            {
                "type": "logic",
                "severity": "major",
                "description": "Sai điều kiện: dùng >= 3 thay vì > 3 (bài yêu cầu HƠN 3 năm kinh nghiệm)",
                "expected_code": "df_employees['NamKinhNghiem'] > 3",
                "actual_code": "df_employees['NamKinhNghiem'] >= 3",
                "node": {},
                "ref_node": {},
                "source": "wrong_filter",
            }
        )

    return errors


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def classify_errors(diff: dict, student_code: str) -> list[dict]:
    """
    Phân loại lỗi dựa trên graph diff và code gốc của sinh viên.

    Args:
        diff        : Kết quả từ graph_comparator.compare_graphs().
        student_code: Code Python của sinh viên (chuỗi).

    Returns:
        Danh sách lỗi, mỗi lỗi là dict với các khóa:
            type        - "syntax" | "logic" | "algorithm" | "data_handling"
            severity    - "critical" | "major" | "minor"
            description - mô tả lỗi bằng tiếng Việt
            expected_code, actual_code  - đoạn code đúng / sai
            source      - nguồn gốc lỗi
    """
    errors: list[dict] = []

    # 1. Lỗi cú pháp
    has_syn, syn_msg = _has_syntax_error(student_code)
    if has_syn:
        errors.append(
            {
                "type": "syntax",
                "severity": "critical",
                "description": f"Lỗi cú pháp Python: {syn_msg}",
                "expected_code": "",
                "actual_code": student_code[:200],
                "node": {},
                "ref_node": {},
                "source": "syntax_error",
            }
        )
        # Không kiểm tra tiếp – code không parse được
        return errors

    # 2. Lỗi thiếu bước
    for missing in diff.get("missing_nodes", []):
        errors.append(_classify_missing_node(missing))

    # 3. Lỗi bước sai
    for wrong in diff.get("wrong_nodes", []):
        errors.extend(_classify_wrong_node(wrong))

    # 4. Lỗi format / toán tử / tên cột cụ thể (rule-based)
    errors.extend(_detect_format_errors(student_code))
    errors.extend(_detect_operator_errors(student_code))
    errors.extend(_detect_column_name_errors(student_code))

    # 5. Loại bỏ trùng lặp theo description
    seen_descs: set[str] = set()
    unique_errors: list[dict] = []
    for err in errors:
        key = err.get("description", "")
        if key not in seen_descs:
            seen_descs.add(key)
            unique_errors.append(err)

    return unique_errors

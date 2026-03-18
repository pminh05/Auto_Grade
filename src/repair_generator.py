"""
repair_generator.py - Tạo hướng dẫn sửa lỗi từng bước bằng tiếng Việt.

Mỗi bước sửa lỗi bao gồm:
  step_number   - số thứ tự
  error_type    - loại lỗi
  severity      - mức độ
  title         - tiêu đề ngắn
  description   - mô tả lỗi chi tiết
  wrong_code    - đoạn code sai của sinh viên
  correct_code  - đoạn code đúng gợi ý
  explanation   - giải thích tại sao cần sửa
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Templates sửa lỗi cho từng loại sai phổ biến
# ---------------------------------------------------------------------------

_REPAIR_TEMPLATES: dict[str, dict] = {
    "wrong_function_argmax_sum": {
        "title": "Sai hàm tính đếm – dùng np.argmax thay vì np.sum",
        "explanation": (
            "np.argmax() trả về CHỈ SỐ của phần tử lớn nhất, không phải số lượng phần tử "
            "thỏa điều kiện. Để đếm số phần tử True trong mảng boolean, cần dùng np.sum() "
            "vì True được coi là 1 và False là 0."
        ),
    },
    "wrong_function_argmin_sum": {
        "title": "Sai hàm – dùng np.argmin thay vì np.sum",
        "explanation": (
            "np.argmin() trả về chỉ số của phần tử nhỏ nhất, không phải tổng. "
            "Hãy dùng np.sum() để tính tổng hoặc đếm phần tử boolean."
        ),
    },
    "wrong_axis_0_1": {
        "title": "Sai tham số axis – dùng axis=0 thay vì axis=1",
        "explanation": (
            "axis=0 tính theo chiều dọc (theo cột), cho kết quả là mảng 1 chiều theo cột. "
            "axis=1 tính theo chiều ngang (theo hàng), cho kết quả là mảng 1 chiều theo hàng. "
            "Khi cần tính trung bình/tổng theo từng khu vực (hàng), phải dùng axis=1."
        ),
    },
    "wrong_axis_1_0": {
        "title": "Sai tham số axis – dùng axis=1 thay vì axis=0",
        "explanation": (
            "axis=1 tính theo chiều ngang (theo hàng). "
            "axis=0 tính theo chiều dọc (theo cột), dùng khi muốn kết quả theo từng quý/cột."
        ),
    },
    "wrong_filter_variable": {
        "title": "Lọc sai biến – cần lọc từ ma trận gốc sales_matrix",
        "explanation": (
            "Khi lọc boolean indexing, phải áp dụng điều kiện lên đúng biến gốc. "
            "Nếu lọc từ tong_doanh_so_quy thay vì sales_matrix, kết quả sẽ khác "
            "vì kích thước và ngữ nghĩa của hai biến khác nhau."
        ),
    },
    "wrong_sort_ascending": {
        "title": "Sai chiều sắp xếp – cần sắp xếp giảm dần (ascending=False)",
        "explanation": (
            "Bài yêu cầu sắp xếp theo ThanhTien từ cao xuống thấp (giảm dần). "
            "Tham số ascending=True sắp xếp tăng dần (từ thấp đến cao). "
            "Cần đặt ascending=False để sắp xếp giảm dần."
        ),
    },
    "missing_sort_values": {
        "title": "Thiếu bước sắp xếp DataFrame",
        "explanation": (
            "Bài yêu cầu sắp xếp DataFrame theo cột ThanhTien giảm dần. "
            "Cần gọi df_orders.sort_values(by='ThanhTien', ascending=False) để "
            "tạo DataFrame đã được sắp xếp."
        ),
    },
    "wrong_column_value_KinhDoanh": {
        "title": "Sai tên phòng ban – 'KinhDoanh' thay vì 'Kinh doanh'",
        "explanation": (
            "Tên phòng ban trong DataFrame là 'Kinh doanh' (có dấu cách và dấu tiếng Việt). "
            "Dùng 'KinhDoanh' sẽ không khớp với dữ liệu, kết quả lọc sẽ trả về 0 hàng."
        ),
    },
    "wrong_column_KinhNghiem": {
        "title": "Sai tên cột – 'KinhNghiem' thay vì 'NamKinhNghiem'",
        "explanation": (
            "Tên cột trong DataFrame là 'NamKinhNghiem'. "
            "Truy cập cột không tồn tại sẽ gây ra KeyError khi chạy code."
        ),
    },
    "wrong_threshold_gte_gt": {
        "title": "Sai điều kiện – dùng >= 3 thay vì > 3",
        "explanation": (
            "Bài yêu cầu đếm nhân viên có HƠN 3 năm kinh nghiệm (strictly greater than). "
            "Dùng >= 3 sẽ bao gồm cả nhân viên có đúng 3 năm kinh nghiệm, cho kết quả sai."
        ),
    },
    "missing_multiply_1000": {
        "title": "Thiếu nhân 1000 khi in lợi nhuận (đơn vị: nghìn VNĐ → đồng)",
        "explanation": (
            "Dữ liệu lợi nhuận đang tính theo đơn vị nghìn VNĐ. "
            "Để chuyển sang VNĐ cần nhân 1000 trước khi in: {tong_loi_nhuan*1000:,.0f}."
        ),
    },
    "wrong_arithmetic_operator": {
        "title": "Sai toán tử – dùng + thay vì * khi tính doanh thu",
        "explanation": (
            "Doanh thu = giá bán × số lượng bán (phép nhân). "
            "Phép cộng (+) cho kết quả hoàn toàn khác về mặt kinh tế."
        ),
    },
    "missing_loi_nhuan_moi_sp": {
        "title": "Thiếu bước tính lợi nhuận mỗi sản phẩm",
        "explanation": (
            "Để đếm số sản phẩm có lợi nhuận >= 10000, trước tiên cần tính "
            "loi_nhuan_moi_sp = (gia_ban - chi_phi) * so_luong_ban, "
            "sau đó dùng np.sum(loi_nhuan_moi_sp >= 10000)."
        ),
    },
    "syntax_error": {
        "title": "Lỗi cú pháp Python",
        "explanation": (
            "Code không thể chạy do có lỗi cú pháp. "
            "Cần sửa lỗi cú pháp trước khi kiểm tra logic."
        ),
    },
    "default": {
        "title": "Lỗi cần sửa",
        "explanation": "Kiểm tra lại đoạn code này theo hướng dẫn.",
    },
}


def _pick_template(error: dict) -> dict:
    """Chọn template phù hợp nhất cho lỗi."""
    source = error.get("source", "")
    desc = error.get("description", "").lower()
    actual = str(error.get("actual_code", "")).lower()
    expected = str(error.get("expected_code", "")).lower()

    if source == "syntax_error":
        return _REPAIR_TEMPLATES["syntax_error"]

    if source == "wrong_function":
        key = f"wrong_function_{actual}_{expected}"
        if key in _REPAIR_TEMPLATES:
            return _REPAIR_TEMPLATES[key]

    if source == "wrong_axis":
        key = f"wrong_axis_{actual.replace('axis=', '')}_{expected.replace('axis=', '')}"
        if key in _REPAIR_TEMPLATES:
            return _REPAIR_TEMPLATES[key]

    if source == "wrong_sort_order":
        return _REPAIR_TEMPLATES["wrong_sort_ascending"]

    if source == "wrong_column_value":
        if "kinhdoanh" in actual.lower() or "kinhdoanh" in desc:
            return _REPAIR_TEMPLATES["wrong_column_value_KinhDoanh"]
        if "kinhnghiem" in actual.lower() and "nam" not in actual.lower():
            return _REPAIR_TEMPLATES["wrong_column_KinhNghiem"]

    if source == "wrong_filter":
        if ">= 3" in desc or ">=3" in actual:
            return _REPAIR_TEMPLATES["wrong_threshold_gte_gt"]

    if source == "missing_node":
        label = error.get("node", {}).get("label", "").lower()
        if "sort" in label:
            return _REPAIR_TEMPLATES["missing_sort_values"]
        if "loi_nhuan_moi_sp" in label:
            return _REPAIR_TEMPLATES["missing_loi_nhuan_moi_sp"]

    if source == "format_error":
        return _REPAIR_TEMPLATES["missing_multiply_1000"]

    if source == "operator_error":
        return _REPAIR_TEMPLATES["wrong_arithmetic_operator"]

    if "kinhdoanh" in desc:
        return _REPAIR_TEMPLATES["wrong_column_value_KinhDoanh"]

    if "argmax" in desc or "argmax" in actual:
        return _REPAIR_TEMPLATES["wrong_function_argmax_sum"]

    if "axis" in desc:
        return _REPAIR_TEMPLATES.get(
            f"wrong_axis_{actual.replace('axis=', '')}_{expected.replace('axis=', '')}",
            _REPAIR_TEMPLATES["default"],
        )

    return _REPAIR_TEMPLATES["default"]


def _build_wrong_code_snippet(error: dict, student_code: str) -> str:
    """Trích đoạn code sai của sinh viên."""
    # Thử lấy dòng từ node
    node = error.get("node", {}) or error.get("student_node", {})
    line_no = node.get("line", 0)
    if line_no and student_code:
        lines = student_code.splitlines()
        idx = line_no - 1
        if 0 <= idx < len(lines):
            return lines[idx].strip()

    actual = error.get("actual_code", "")
    return actual if actual else "(xem code của bạn)"


def _build_correct_code_snippet(error: dict, ref_code: str) -> str:
    """Trích đoạn code đúng từ reference."""
    ref_node = error.get("ref_node", {})
    line_no = ref_node.get("line", 0)
    if line_no and ref_code:
        lines = ref_code.splitlines()
        idx = line_no - 1
        if 0 <= idx < len(lines):
            return lines[idx].strip()

    expected = error.get("expected_code", "")
    return expected if expected else "(xem reference solution)"


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def generate_repair_steps(
    errors: list[dict],
    student_code: str,
    ref_code: str,
) -> list[dict]:
    """
    Tạo hướng dẫn sửa lỗi từng bước.

    Args:
        errors      : Danh sách lỗi từ error_classifier.classify_errors().
        student_code: Code Python gốc của sinh viên.
        ref_code    : Code Python của reference solution.

    Returns:
        Danh sách các bước sửa, mỗi bước là dict.
    """
    if not errors:
        return [
            {
                "step_number": 1,
                "error_type": "none",
                "severity": "none",
                "title": "Code đúng – không cần sửa",
                "description": "Không phát hiện lỗi so với reference solution.",
                "wrong_code": "",
                "correct_code": "",
                "explanation": "Code của bạn khớp với yêu cầu bài toán.",
            }
        ]

    # Sắp xếp: critical → major → minor
    severity_order = {"critical": 0, "major": 1, "minor": 2}
    sorted_errors = sorted(
        errors, key=lambda e: severity_order.get(e.get("severity", "minor"), 2)
    )

    steps: list[dict] = []
    for i, error in enumerate(sorted_errors, start=1):
        tmpl = _pick_template(error)
        wrong_code = _build_wrong_code_snippet(error, student_code)
        correct_code = _build_correct_code_snippet(error, ref_code)

        steps.append(
            {
                "step_number": i,
                "error_type": error.get("type", "unknown"),
                "severity": error.get("severity", "minor"),
                "title": tmpl.get("title", error.get("description", "Lỗi cần sửa")),
                "description": error.get("description", ""),
                "wrong_code": wrong_code,
                "correct_code": correct_code,
                "explanation": tmpl.get("explanation", ""),
            }
        )

    return steps

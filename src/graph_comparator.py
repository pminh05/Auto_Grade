"""
graph_comparator.py - So sánh hai đồ thị ngữ nghĩa và phát hiện sự khác biệt.

Phát hiện:
  - Missing nodes  : sinh viên thiếu bước thực hiện
  - Extra nodes    : sinh viên thêm bước không cần thiết
  - Wrong nodes    : bước có nhưng sai (hàm sai, axis sai, điều kiện sai …)
  - Matched nodes  : bước khớp hoàn toàn
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Semantic-signature helpers
# ---------------------------------------------------------------------------

# Các kiểu node không liên quan đến logic bài (bỏ qua khi so sánh)
_IGNORED_TYPES = {"import", "constant", "variable_ref", "unknown"}

# Các loại node "quan trọng" – cần có trong bài làm của sinh viên
_IMPORTANT_TYPES = {
    "array_creation",
    "matrix_creation",
    "numpy_reduction",
    "numpy_creation",
    "dataframe_creation",
    "pandas_sort",
    "pandas_groupby",
    "pandas_merge",
    "pandas_na_handling",
    "shape_access",
    "series_reduction",
    "boolean_indexing",
    "arithmetic_op",
    "comparison_op",
    "print_output",
    "slice_indexing",
    "indexing",
    "function_call",
}


def _extract_func(operation: str) -> str:
    """Trích tên hàm từ chuỗi operation, ví dụ 'np.sum(x, axis=1)' → 'np.sum'."""
    idx = operation.find("(")
    return operation[:idx].strip().lower() if idx != -1 else operation.strip().lower()


def _normalize_func(func: str) -> str:
    """Chuẩn hoá tên hàm (bỏ tiền tố numpy. / pandas.)."""
    for prefix in ("numpy.", "pandas.", "np.", "pd."):
        if func.startswith(prefix):
            return func[len(prefix):]
    return func


def _extract_axis(node: dict) -> Optional[int]:
    """Trích tham số axis từ extra['kwargs']."""
    kwargs = node.get("extra", {}).get("kwargs", {})
    val = kwargs.get("axis")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _extract_filter_op(node: dict) -> str:
    """Trích điều kiện lọc ngắn gọn (toán tử so sánh + ngưỡng)."""
    extra = node.get("extra", {})
    fe = extra.get("filter_extra") or extra.get("filter") or {}
    if isinstance(fe, dict):
        return f"{fe.get('op', '')} {fe.get('right', '')}".strip()
    if isinstance(fe, str):
        return fe
    return ""


def _extract_sort_order(node: dict) -> Optional[bool]:
    """Trích tham số ascending."""
    kwargs = node.get("extra", {}).get("kwargs", {})
    val = kwargs.get("ascending")
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() == "true"
    return None


def _node_signature(node: dict) -> str:
    """Tạo 'chữ ký ngữ nghĩa' đại diện cho node."""
    ntype = node.get("type", "")
    func = _normalize_func(_extract_func(node.get("operation", "")))
    axis = _extract_axis(node)
    axis_str = f"|axis={axis}" if axis is not None else ""
    return f"{ntype}|{func}{axis_str}"


# ---------------------------------------------------------------------------
# Node-similarity scoring
# ---------------------------------------------------------------------------

def _node_similarity(ref: dict, stu: dict) -> float:
    """
    Tính điểm tương đồng giữa hai node (0.0 – 1.0).

    Tiêu chí:
      - Cùng semantic type    : +0.5
      - Cùng hàm (sau norm)   : +0.3
      - Cùng axis             : +0.1
      - Cùng điều kiện filter : +0.1
    """
    score = 0.0

    ref_type = ref.get("type", "")
    stu_type = stu.get("type", "")

    if ref_type != stu_type:
        # Một số cặp type tương đương vẫn có thể khớp một phần
        compatible = {
            ("numpy_reduction", "function_call"),
            ("array_creation", "numpy_creation"),
            ("dataframe_creation", "function_call"),
            # shape_access là biến thể của boolean_indexing (df[cond].shape[0])
            ("shape_access", "boolean_indexing"),
            ("boolean_indexing", "shape_access"),
        }
        pair = (ref_type, stu_type)
        rev_pair = (stu_type, ref_type)
        if pair not in compatible and rev_pair not in compatible:
            return 0.0
        score += 0.4  # cùng nhóm nhưng khác sub-type
    else:
        score += 0.5

    ref_func = _normalize_func(_extract_func(ref.get("operation", "")))
    stu_func = _normalize_func(_extract_func(stu.get("operation", "")))

    if ref_func == stu_func:
        score += 0.3
    elif ref_func and stu_func:
        # Partial: cùng "family" (ví dụ sum/mean đều là reduction)
        reduction_family = {"sum", "mean", "max", "min", "argmax", "argmin", "std", "var"}
        if ref_func in reduction_family and stu_func in reduction_family:
            score += 0.1  # cùng nhóm nhưng hàm khác

    # axis
    ref_axis = _extract_axis(ref)
    stu_axis = _extract_axis(stu)
    if ref_axis is not None and stu_axis is not None:
        score += 0.1 if ref_axis == stu_axis else 0.0
    elif ref_axis is None and stu_axis is None:
        score += 0.1

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Difference detection
# ---------------------------------------------------------------------------

def _find_node_differences(ref: dict, stu: dict) -> list[dict]:
    """
    Liệt kê các điểm khác biệt cụ thể giữa hai node đã được ghép cặp.
    """
    diffs = []
    ref_func = _normalize_func(_extract_func(ref.get("operation", "")))
    stu_func = _normalize_func(_extract_func(stu.get("operation", "")))

    # Sai hàm
    if ref_func != stu_func:
        diffs.append(
            {
                "aspect": "wrong_function",
                "expected": ref_func,
                "actual": stu_func,
                "message": f"Dùng '{stu_func}' thay vì '{ref_func}'",
            }
        )

    # Sai axis
    ref_axis = _extract_axis(ref)
    stu_axis = _extract_axis(stu)
    if ref_axis is not None and stu_axis is not None and ref_axis != stu_axis:
        diffs.append(
            {
                "aspect": "wrong_axis",
                "expected": ref_axis,
                "actual": stu_axis,
                "message": f"Dùng axis={stu_axis} thay vì axis={ref_axis}",
            }
        )

    # Sai điều kiện filter
    if ref.get("type") == "boolean_indexing":
        ref_flt = _extract_filter_op(ref)
        stu_flt = _extract_filter_op(stu)
        if ref_flt and stu_flt and ref_flt != stu_flt:
            diffs.append(
                {
                    "aspect": "wrong_filter",
                    "expected": ref_flt,
                    "actual": stu_flt,
                    "message": f"Điều kiện lọc sai: '{stu_flt}' thay vì '{ref_flt}'",
                }
            )

    # Sai thứ tự sắp xếp
    if ref.get("type") == "pandas_sort":
        ref_asc = _extract_sort_order(ref)
        stu_asc = _extract_sort_order(stu)
        if ref_asc is not None and stu_asc is not None and ref_asc != stu_asc:
            exp_str = "tăng dần" if ref_asc else "giảm dần"
            act_str = "tăng dần" if stu_asc else "giảm dần"
            diffs.append(
                {
                    "aspect": "wrong_sort_order",
                    "expected": exp_str,
                    "actual": act_str,
                    "message": f"Sắp xếp {act_str} thay vì {exp_str}",
                }
            )

    # Phát hiện sai tên cột/biến trong filter của pandas
    # Kiểm tra cả boolean_indexing và shape_access (df[condition].shape[0])
    stu_type = stu.get("type", "")
    if stu_type in ("boolean_indexing", "shape_access"):
        # Dùng filter_raw (AST-unparse, có dấu ngoặc kép) để tránh false-positive
        stu_filter_raw = (
            stu.get("extra", {}).get("filter_raw", "")
            or stu.get("extra", {}).get("filter", "")
        )
        # Sai tên phòng ban: 'KinhDoanh' thay vì 'Kinh doanh'
        if re.search(r"['\"]KinhDoanh['\"]", str(stu_filter_raw)):
            diffs.append(
                {
                    "aspect": "wrong_column_value",
                    "expected": "Kinh doanh",
                    "actual": "KinhDoanh",
                    "message": "Sai tên phòng ban: 'KinhDoanh' nên là 'Kinh doanh'",
                }
            )
        # Sai tên cột: 'KinhNghiem' thay vì 'NamKinhNghiem'
        # Dùng regex để tránh match 'NamKinhNghiem' (negative lookbehind)
        if re.search(r"['\"]KinhNghiem['\"]", str(stu_filter_raw)):
            diffs.append(
                {
                    "aspect": "wrong_column_value",
                    "expected": "NamKinhNghiem",
                    "actual": "KinhNghiem",
                    "message": "Sai tên cột: 'KinhNghiem' nên là 'NamKinhNghiem'",
                }
            )

    return diffs


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare_graphs(student_graph: dict, ref_graph: dict) -> dict:
    """
    So sánh đồ thị ngữ nghĩa của sinh viên với đồ thị tham chiếu.

    Args:
        student_graph: Đồ thị của sinh viên (từ graph_builder.build_graph).
        ref_graph    : Đồ thị tham chiếu (từ reference solution).

    Returns:
        dict với các khóa:
            missing_nodes   - list node trong ref nhưng thiếu ở student
            extra_nodes     - list node trong student không có trong ref
            wrong_nodes     - list dict{ref_node, student_node, differences}
            matched_nodes   - list dict{ref_node, student_node}
            similarity_score - float 0-1
            has_syntax_error - bool
            details          - list ghi chú bổ sung
    """
    diff: dict = {
        "missing_nodes": [],
        "extra_nodes": [],
        "wrong_nodes": [],
        "matched_nodes": [],
        "similarity_score": 0.0,
        "has_syntax_error": False,
        "details": [],
    }

    # Nếu student có lỗi cú pháp → tất cả node ref đều bị thiếu
    if student_graph.get("metadata", {}).get("has_syntax_error"):
        diff["has_syntax_error"] = True
        diff["missing_nodes"] = [
            n for n in ref_graph.get("nodes", []) if n.get("type") not in _IGNORED_TYPES
        ]
        diff["details"].append(
            {
                "type": "syntax_error",
                "message": "Code sinh viên có lỗi cú pháp – không thể so sánh",
                "error": student_graph.get("metadata", {}).get("syntax_error", ""),
            }
        )
        return diff

    ref_nodes = [n for n in ref_graph.get("nodes", []) if n.get("type") not in _IGNORED_TYPES]
    stu_nodes = [n for n in student_graph.get("nodes", []) if n.get("type") not in _IGNORED_TYPES]

    matched_ref_idx: set[int] = set()
    matched_stu_idx: set[int] = set()

    # Ghép cặp: mỗi node ref → node student tốt nhất
    for ri, ref_node in enumerate(ref_nodes):
        best_score = 0.0
        best_si = -1

        for si, stu_node in enumerate(stu_nodes):
            if si in matched_stu_idx:
                continue
            score = _node_similarity(ref_node, stu_node)
            if score > best_score:
                best_score = score
                best_si = si

        threshold = 0.4  # ngưỡng tối thiểu để coi là "có tương đồng"
        if best_si >= 0 and best_score >= threshold:
            matched_ref_idx.add(ri)
            matched_stu_idx.add(best_si)
            stu_node = stu_nodes[best_si]
            diffs = _find_node_differences(ref_node, stu_node)
            if diffs or best_score < 1.0:
                diff["wrong_nodes"].append(
                    {
                        "ref_node": ref_node,
                        "student_node": stu_node,
                        "similarity": best_score,
                        "differences": diffs,
                    }
                )
            else:
                diff["matched_nodes"].append(
                    {"ref_node": ref_node, "student_node": stu_node}
                )
        else:
            diff["missing_nodes"].append(ref_node)

    # Các node sinh viên chưa được ghép → thừa
    for si, stu_node in enumerate(stu_nodes):
        if si not in matched_stu_idx:
            diff["extra_nodes"].append(stu_node)

    # Tính điểm tương đồng
    total_ref = len(ref_nodes)
    if total_ref > 0:
        exact = len(diff["matched_nodes"])
        partial = sum(
            wn["similarity"] for wn in diff["wrong_nodes"]
        )
        diff["similarity_score"] = round((exact + partial) / total_ref, 4)
    else:
        diff["similarity_score"] = 1.0

    return diff

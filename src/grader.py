"""
grader.py - Pipeline chính tích hợp toàn bộ các bước chấm điểm.

Quy trình:
  1. Build Graph từ student code và reference code
  2. Graph Comparison / Difference Detection
  3. Error Localization & Severity Classification
  4. Step-by-Step Repair Generation
  5. LLM Feedback (prompt template + mock response)
  6. Output: Score + Detailed Feedback + Repair Guide
"""

from __future__ import annotations

import os
import traceback

from .graph_builder import build_graph
from .graph_comparator import compare_graphs
from .error_classifier import classify_errors
from .repair_generator import generate_repair_steps
from .llm_feedback import generate_feedback, PROBLEM_DESCRIPTIONS

# ---------------------------------------------------------------------------
# Đường dẫn reference solutions
# ---------------------------------------------------------------------------

_REF_SOL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reference_solutions")

_REF_FILES: dict[str, str] = {
    "numpy_01": os.path.join(_REF_SOL_DIR, "numpy_01.py"),
    "numpy_02": os.path.join(_REF_SOL_DIR, "numpy_02.py"),
    "pandas_01": os.path.join(_REF_SOL_DIR, "pandas_01.py"),
    "pandas_02": os.path.join(_REF_SOL_DIR, "pandas_02.py"),
}

_PROBLEM_NAMES: dict[str, str] = {
    "numpy_01": "Numpy 01 – Phân tích lợi nhuận bán hàng",
    "numpy_02": "Numpy 02 – Đánh giá Hiệu suất Kinh doanh",
    "pandas_01": "Pandas 01 – Xử lý Dữ liệu đơn hàng",
    "pandas_02": "Pandas 02 – Phân tích dữ liệu nhân sự",
}


def _load_ref_code(problem_id: str) -> str:
    """Đọc reference solution từ file."""
    path = _REF_FILES.get(problem_id, "")
    if not path or not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Main grading function
# ---------------------------------------------------------------------------

def grade_submission(
    student_name: str,
    student_code: str,
    problem_id: str,
    test_results: dict,
    ref_code: str = "",
) -> dict:
    """
    Chấm điểm một bài nộp của sinh viên.

    Args:
        student_name : Tên sinh viên.
        student_code : Code Python của sinh viên.
        problem_id   : ID bài toán (numpy_01, numpy_02, pandas_01, pandas_02).
        test_results : dict với passedTestCases, totalTestCases, status.
        ref_code     : Code tham chiếu (mặc định đọc từ file).

    Returns:
        dict kết quả chấm điểm đầy đủ.
    """
    problem_name = _PROBLEM_NAMES.get(problem_id, problem_id)

    # Xử lý trường hợp chưa nộp bài
    if not student_code:
        return {
            "student_name": student_name,
            "problem_id": problem_id,
            "problem_name": problem_name,
            "status": "not_submitted",
            "score": 0.0,
            "grade": "F",
            "passed_tests": 0,
            "total_tests": 0,
            "errors": [],
            "repair_steps": [],
            "feedback": {
                "score": 0.0,
                "grade": "F",
                "overall_comment": f"Sinh viên chưa nộp bài {problem_name}.",
                "strengths": [],
                "improvements": ["Cần nộp bài để được chấm điểm"],
                "advice": "Hoàn thành và nộp bài đúng hạn.",
                "feedback_detail": "Không có bài nộp.",
                "llm_prompt": "",
            },
            "graph": {"student": {}, "reference": {}},
            "graph_diff": {},
        }

    # Load reference code nếu chưa có
    if not ref_code:
        ref_code = _load_ref_code(problem_id)

    # Bước 1: Xây dựng đồ thị ngữ nghĩa
    try:
        student_graph = build_graph(student_code)
    except Exception:
        student_graph = {
            "nodes": [], "edges": [],
            "metadata": {"has_syntax_error": True, "syntax_error": traceback.format_exc()},
        }

    try:
        ref_graph = build_graph(ref_code) if ref_code else {"nodes": [], "edges": [], "metadata": {}}
    except Exception:
        ref_graph = {"nodes": [], "edges": [], "metadata": {}}

    # Bước 2: So sánh đồ thị – phát hiện sự khác biệt
    try:
        graph_diff = compare_graphs(student_graph, ref_graph)
    except Exception:
        graph_diff = {
            "missing_nodes": [], "extra_nodes": [],
            "wrong_nodes": [], "matched_nodes": [],
            "similarity_score": 0.0, "has_syntax_error": False,
            "details": [{"type": "error", "message": traceback.format_exc()}],
        }

    # Bước 3: Phân loại lỗi và mức độ nghiêm trọng
    try:
        errors = classify_errors(graph_diff, student_code)
    except Exception:
        errors = []

    # Bước 4: Tạo hướng dẫn sửa lỗi
    try:
        repair_steps = generate_repair_steps(errors, student_code, ref_code)
    except Exception:
        repair_steps = []

    # Bước 5: Sinh feedback (prompt + mock LLM)
    try:
        feedback = generate_feedback(
            problem_id=problem_id,
            student_code=student_code,
            ref_code=ref_code,
            graph_diff=graph_diff,
            errors=errors,
            repair_steps=repair_steps,
            test_results=test_results,
        )
    except Exception:
        feedback = {
            "score": 0.0,
            "grade": "F",
            "overall_comment": "Lỗi khi tạo feedback.",
            "strengths": [],
            "improvements": [],
            "advice": "",
            "feedback_detail": traceback.format_exc(),
            "llm_prompt": "",
        }

    return {
        "student_name": student_name,
        "problem_id": problem_id,
        "problem_name": problem_name,
        "status": _status_label(test_results.get("status")),
        "score": feedback["score"],
        "grade": feedback["grade"],
        "passed_tests": test_results.get("passedTestCases", 0),
        "total_tests": test_results.get("totalTestCases", 0),
        "errors": errors,
        "repair_steps": repair_steps,
        "feedback": feedback,
        "graph": {
            "student": {
                "node_count": len(student_graph.get("nodes", [])),
                "has_syntax_error": student_graph.get("metadata", {}).get("has_syntax_error", False),
            },
            "reference": {
                "node_count": len(ref_graph.get("nodes", [])),
            },
        },
        "graph_diff": {
            "similarity_score": graph_diff.get("similarity_score", 0.0),
            "missing_count": len(graph_diff.get("missing_nodes", [])),
            "extra_count": len(graph_diff.get("extra_nodes", [])),
            "wrong_count": len(graph_diff.get("wrong_nodes", [])),
            "matched_count": len(graph_diff.get("matched_nodes", [])),
        },
    }


def _status_label(status_code) -> str:
    mapping = {3: "passed", 4: "wrong_answer", 5: "runtime_error", None: "not_submitted"}
    return mapping.get(status_code, "unknown")

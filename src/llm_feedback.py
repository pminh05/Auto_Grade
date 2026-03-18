"""
llm_feedback.py - Tạo feedback bằng LLM (prompt template + mock response).

Trong phiên bản này, chúng ta sử dụng template-based generation (không gọi LLM thật).
Prompt template đầy đủ được xây dựng để có thể gọi LLM thật sau này.
"""

from __future__ import annotations

import json
import textwrap


# ---------------------------------------------------------------------------
# Problem descriptions (tiếng Việt)
# ---------------------------------------------------------------------------

PROBLEM_DESCRIPTIONS: dict[str, str] = {
    "numpy_01": textwrap.dedent("""\
        Bài 1: Numpy 01 – Phân tích lợi nhuận bán hàng
        a. Khởi tạo 3 numpy array: gia_ban, chi_phi, so_luong_ban
        b. Tính tong_doanh_thu = gia_ban * so_luong_ban (từng sản phẩm)
        c. Tính tong_loi_nhuan = np.sum((gia_ban - chi_phi) * so_luong_ban), in format {tong_loi_nhuan*1000:,.0f} VND
        d. Đếm so_san_pham = np.sum(loi_nhuan_moi_sp >= 10000), in số nguyên
    """),
    "numpy_02": textwrap.dedent("""\
        Bài 2: Numpy 02 – Đánh giá Hiệu suất Kinh doanh
        a. trung_binh_khu_vuc = np.mean(sales_matrix, axis=1)
        b. tong_doanh_so_quy = np.sum(sales_matrix, axis=0)
        c. quy_vuot_troi = sales_matrix[sales_matrix > 650]
        d. tang_truong_Q1_Q4 = ((sales_matrix[:,3] - sales_matrix[:,0]) / sales_matrix[:,0]) * 100
    """),
    "pandas_01": textwrap.dedent("""\
        Bài 3: Pandas 01 – Xử lý Dữ liệu đơn hàng
        a. Tạo DataFrame df_orders từ dict order_data
        b. df_orders['DonGia'] = [18000, 500, 350, 4500, 19500]
        c. Tính df_orders['ThanhTien'] = SoLuong * DonGia, sắp xếp giảm dần theo ThanhTien
    """),
    "pandas_02": textwrap.dedent("""\
        Bài 4: Pandas 02 – Phân tích dữ liệu nhân sự
        a. Tạo DataFrame df_employees từ employee_data
        b. so_nv_kinh_nghiem = df_employees[NamKinhNghiem > 3].shape[0]
        c. so_nv_luong_cao = df_employees[(PhongBan == 'Kinh doanh') & (LuongThang * 12 > 250)].shape[0]
    """),
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(
    problem_id: str,
    student_code: str,
    ref_code: str,
    graph_diff: dict,
    errors: list[dict],
    repair_steps: list[dict],
    test_results: dict,
) -> str:
    """
    Xây dựng prompt đầy đủ để gửi cho LLM.

    Args:
        problem_id   : ID bài toán (numpy_01, numpy_02, pandas_01, pandas_02).
        student_code : Code của sinh viên.
        ref_code     : Code tham chiếu.
        graph_diff   : Kết quả so sánh graph.
        errors       : Danh sách lỗi đã phân loại.
        repair_steps : Các bước sửa lỗi đề xuất.
        test_results : Kết quả test (passed/total).

    Returns:
        Chuỗi prompt hoàn chỉnh.
    """
    problem_desc = PROBLEM_DESCRIPTIONS.get(problem_id, f"Bài: {problem_id}")
    passed = test_results.get("passedTestCases", 0)
    total = test_results.get("totalTestCases", 0)
    similarity = graph_diff.get("similarity_score", 0.0)

    # Tóm tắt lỗi
    error_summary = ""
    for i, err in enumerate(errors[:5], 1):  # Tối đa 5 lỗi đầu
        error_summary += (
            f"  Lỗi {i}: [{err.get('severity','').upper()}] {err.get('type','')} – "
            f"{err.get('description','')}\n"
        )
    if not error_summary:
        error_summary = "  Không phát hiện lỗi.\n"

    # Tóm tắt bước sửa
    repair_summary = ""
    for step in repair_steps[:5]:
        repair_summary += (
            f"  Bước {step.get('step_number','')}: {step.get('title','')}\n"
            f"    Code sai : {step.get('wrong_code','')}\n"
            f"    Code đúng: {step.get('correct_code','')}\n"
            f"    Giải thích: {step.get('explanation','')}\n\n"
        )

    prompt = textwrap.dedent(f"""\
        Bạn là trợ lý chấm điểm tự động cho môn Lập trình Python.
        Nhiệm vụ: Đánh giá code sinh viên, cho điểm và tạo phản hồi chi tiết bằng tiếng Việt.

        ═══════════════════════════════════════════════════════════
        ĐỀ BÀI:
        {problem_desc}
        ═══════════════════════════════════════════════════════════
        CODE SINH VIÊN:
        ```python
        {student_code}
        ```
        ═══════════════════════════════════════════════════════════
        KẾT QUẢ KIỂM TRA TỰ ĐỘNG:
        - Test cases vượt qua: {passed}/{total}
        - Độ tương đồng graph ngữ nghĩa: {similarity:.1%}
        ═══════════════════════════════════════════════════════════
        LỖI PHÁT HIỆN (từ phân tích đồ thị):
        {error_summary}
        ═══════════════════════════════════════════════════════════
        HƯỚNG DẪN SỬA LỖI:
        {repair_summary}
        ═══════════════════════════════════════════════════════════
        YÊU CẦU:
        1. Cho điểm từ 0 đến 10 (70% dựa trên test cases, 30% dựa trên chất lượng code).
        2. Viết nhận xét tổng quan (3-5 câu).
        3. Liệt kê điểm mạnh của sinh viên.
        4. Liệt kê điểm cần cải thiện.
        5. Lời khuyên cụ thể để cải thiện kỹ năng.

        Trả lời theo định dạng JSON:
        {{
          "score": <số>,
          "grade": "<A/B/C/D/F>",
          "overall_comment": "<nhận xét tổng quan>",
          "strengths": ["<điểm mạnh 1>", ...],
          "improvements": ["<điểm cần cải thiện 1>", ...],
          "advice": "<lời khuyên>",
          "feedback_detail": "<phân tích chi tiết>"
        }}
    """)
    return prompt


# ---------------------------------------------------------------------------
# Mock LLM response generator
# ---------------------------------------------------------------------------

def _compute_score(passed: int, total: int, similarity: float, errors: list[dict]) -> float:
    """Tính điểm dựa trên test cases và chất lượng code."""
    # 70% từ test cases
    tc_score = (passed / total * 7.0) if total > 0 else 0.0

    # 30% từ chất lượng code (dựa trên similarity và severity của lỗi)
    quality = similarity
    critical_count = sum(1 for e in errors if e.get("severity") == "critical")
    major_count = sum(1 for e in errors if e.get("severity") == "major")
    if critical_count > 0:
        quality *= 0.3
    elif major_count > 0:
        quality *= max(0.4, 1.0 - major_count * 0.15)

    code_score = quality * 3.0

    return round(min(tc_score + code_score, 10.0), 2)


def _score_to_grade(score: float) -> str:
    if score >= 8.5:
        return "A"
    if score >= 7.0:
        return "B"
    if score >= 5.5:
        return "C"
    if score >= 4.0:
        return "D"
    return "F"


def _generate_strengths(errors: list[dict], similarity: float, passed: int, total: int) -> list[str]:
    strengths = []
    if passed == total and total > 0:
        strengths.append("Code chạy đúng và vượt qua tất cả test cases")
    elif passed > 0:
        strengths.append(f"Code vượt qua được {passed}/{total} test cases")

    has_syntax = any(e.get("type") == "syntax" for e in errors)
    if not has_syntax:
        strengths.append("Code không có lỗi cú pháp, có thể chạy được")

    if similarity >= 0.8:
        strengths.append("Cấu trúc code khá tương đồng với reference solution")
    elif similarity >= 0.5:
        strengths.append("Đã thực hiện được phần lớn các bước yêu cầu")

    algo_errors = [e for e in errors if e.get("type") in ("algorithm", "data_handling")]
    if not algo_errors:
        strengths.append("Lựa chọn hàm và phương pháp xử lý dữ liệu phù hợp")

    if not strengths:
        strengths.append("Đã cố gắng giải bài và nộp code")

    return strengths


def _generate_improvements(errors: list[dict]) -> list[str]:
    improvements = []
    seen_types: set[str] = set()

    for err in errors:
        etype = err.get("type", "")
        severity = err.get("severity", "")
        desc = err.get("description", "")

        key = f"{etype}_{severity}"
        if key in seen_types:
            continue
        seen_types.add(key)

        if etype == "syntax":
            improvements.append("Sửa lỗi cú pháp Python trước khi nộp bài")
        elif etype == "algorithm" and severity in ("critical", "major"):
            improvements.append(f"Xem lại việc chọn hàm: {desc}")
        elif etype == "logic" and severity == "major":
            improvements.append(f"Kiểm tra lại tham số: {desc}")
        elif etype == "data_handling":
            improvements.append(f"Xem lại cách xử lý dữ liệu: {desc}")
        elif etype == "logic" and severity == "minor":
            improvements.append(f"Chú ý chi tiết nhỏ: {desc}")

    if not improvements:
        improvements.append("Tiếp tục duy trì chất lượng code tốt")

    return improvements[:5]  # Tối đa 5 mục


def _generate_overall_comment(
    score: float,
    errors: list[dict],
    similarity: float,
    problem_id: str,
) -> str:
    grade = _score_to_grade(score)
    problem_name = PROBLEM_DESCRIPTIONS.get(problem_id, problem_id).split("\n")[0]

    has_syntax = any(e.get("type") == "syntax" for e in errors)
    critical_count = sum(1 for e in errors if e.get("severity") == "critical")
    major_count = sum(1 for e in errors if e.get("severity") == "major")

    if has_syntax:
        return (
            f"Code bài {problem_name} có lỗi cú pháp nên không thể chạy được. "
            "Cần sửa lỗi cú pháp trước khi kiểm tra kết quả. "
            "Hãy đọc kỹ thông báo lỗi và kiểm tra cú pháp Python."
        )
    if score >= 8.5:
        return (
            f"Xuất sắc! Code bài {problem_name} đạt điểm {score}/10 (loại {grade}). "
            "Cấu trúc code rõ ràng, đúng yêu cầu đề bài. Tiếp tục phát huy!"
        )
    if score >= 7.0:
        return (
            f"Tốt! Code bài {problem_name} đạt điểm {score}/10 (loại {grade}). "
            f"Phần lớn các bước thực hiện đúng với độ tương đồng {similarity:.0%}. "
            f"Còn {major_count} lỗi cần chú ý."
        )
    if score >= 5.5:
        return (
            f"Khá! Code bài {problem_name} đạt điểm {score}/10 (loại {grade}). "
            f"Có {major_count} lỗi logic/thuật toán cần sửa. "
            "Xem hướng dẫn sửa lỗi bên dưới để cải thiện."
        )
    if score >= 4.0:
        return (
            f"Trung bình. Code bài {problem_name} đạt điểm {score}/10 (loại {grade}). "
            "Cần xem lại nhiều bước trong bài. Tham khảo hướng dẫn sửa lỗi để hiểu rõ hơn."
        )
    return (
        f"Cần cải thiện nhiều. Code bài {problem_name} đạt điểm {score}/10 (loại {grade}). "
        f"Có {critical_count} lỗi nghiêm trọng và {major_count} lỗi lớn. "
        "Đề nghị xem lại kiến thức cơ bản và tham khảo reference solution."
    )


def generate_feedback(
    problem_id: str,
    student_code: str,
    ref_code: str,
    graph_diff: dict,
    errors: list[dict],
    repair_steps: list[dict],
    test_results: dict,
) -> dict:
    """
    Tạo feedback hoàn chỉnh cho một bài nộp.

    Trong phiên bản này sử dụng template-based generation (không gọi LLM thật).
    Prompt đầy đủ cũng được trả về để tích hợp LLM sau này.

    Args:
        problem_id   : ID bài toán.
        student_code : Code của sinh viên.
        ref_code     : Code tham chiếu.
        graph_diff   : Kết quả so sánh graph.
        errors       : Danh sách lỗi.
        repair_steps : Các bước sửa lỗi.
        test_results : Kết quả test.

    Returns:
        dict chứa score, grade, feedback, prompt.
    """
    passed = test_results.get("passedTestCases", 0)
    total = test_results.get("totalTestCases", 0)
    similarity = graph_diff.get("similarity_score", 0.0)

    score = _compute_score(passed, total, similarity, errors)
    grade = _score_to_grade(score)

    overall_comment = _generate_overall_comment(score, errors, similarity, problem_id)
    strengths = _generate_strengths(errors, similarity, passed, total)
    improvements = _generate_improvements(errors)

    advice_parts = []
    if errors:
        advice_parts.append("Tham khảo hướng dẫn sửa lỗi ở trên và thực hành lại.")
    if any(e.get("type") == "logic" for e in errors):
        advice_parts.append(
            "Đọc kỹ tài liệu NumPy/Pandas về các tham số như axis, ascending."
        )
    if any(e.get("type") == "algorithm" for e in errors):
        advice_parts.append(
            "Nắm vững sự khác biệt giữa các hàm: sum/argmax, mean/sum, v.v."
        )
    if not advice_parts:
        advice_parts.append("Tiếp tục thực hành và giải thêm bài tập nâng cao.")
    advice = " ".join(advice_parts)

    # Xây dựng prompt (để tích hợp LLM thật sau này)
    prompt = build_prompt(
        problem_id=problem_id,
        student_code=student_code,
        ref_code=ref_code,
        graph_diff=graph_diff,
        errors=errors,
        repair_steps=repair_steps,
        test_results=test_results,
    )

    feedback_detail_parts = ["=== PHÂN TÍCH CHI TIẾT ===\n"]
    feedback_detail_parts.append(f"Điểm tương đồng graph: {similarity:.1%}")
    feedback_detail_parts.append(f"Số lỗi: {len(errors)} (critical: "
                                 f"{sum(1 for e in errors if e.get('severity')=='critical')}, "
                                 f"major: {sum(1 for e in errors if e.get('severity')=='major')}, "
                                 f"minor: {sum(1 for e in errors if e.get('severity')=='minor')})")
    if errors:
        feedback_detail_parts.append("\nCác lỗi phát hiện:")
        for i, err in enumerate(errors, 1):
            feedback_detail_parts.append(
                f"  {i}. [{err.get('severity','').upper()}] {err.get('description','')}"
            )

    return {
        "score": score,
        "grade": grade,
        "overall_comment": overall_comment,
        "strengths": strengths,
        "improvements": improvements,
        "advice": advice,
        "feedback_detail": "\n".join(feedback_detail_parts),
        "llm_prompt": prompt,  # prompt để gọi LLM thật sau này
    }

"""
main.py - Điểm vào chính của hệ thống Auto_Grade.

Quy trình:
  1. Đọc dữ liệu sinh viên từ data/CLC11.json
  2. Chấm điểm 5 sinh viên đầu, 4 bài mỗi người
  3. Xuất kết quả ra output/results.json và output/report.csv
  4. In tóm tắt ra console
"""

from __future__ import annotations

import csv
import json
import os
import sys
import textwrap
from datetime import datetime

# Thêm thư mục gốc vào sys.path để import src
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.grader import grade_submission

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_FILE = os.path.join(ROOT_DIR, "data", "CLC11.json")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "report.csv")

PROBLEM_IDS = ["numpy_01", "numpy_02", "pandas_01", "pandas_02"]
MAX_STUDENTS = 5  # Chấm 5 sinh viên đầu


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_students(path: str) -> list[dict]:
    """Đọc danh sách sinh viên từ JSON."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_results(results: list[dict], path: str) -> None:
    """Lưu kết quả ra file JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)


def save_report_csv(results: list[dict], path: str) -> None:
    """Xuất báo cáo dạng CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "Họ tên", "Mã SV", "Bài", "Trạng thái", "Điểm",
        "Xếp loại", "Test qua", "Tổng test",
        "Tương đồng graph", "Số lỗi", "Nhận xét tổng quan",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            for sub in r.get("submissions", []):
                writer.writerow(
                    {
                        "Họ tên": r["student_name"],
                        "Mã SV": r["student_id"],
                        "Bài": sub["problem_name"],
                        "Trạng thái": sub["status"],
                        "Điểm": sub["score"],
                        "Xếp loại": sub["grade"],
                        "Test qua": sub["passed_tests"],
                        "Tổng test": sub["total_tests"],
                        "Tương đồng graph": f"{sub['graph_diff'].get('similarity_score', 0):.1%}",
                        "Số lỗi": len(sub.get("errors", [])),
                        "Nhận xét tổng quan": sub["feedback"].get("overall_comment", ""),
                    }
                )


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------

def grade_student(student: dict) -> dict:
    """Chấm điểm một sinh viên cho tất cả bài."""
    student_id = student.get("student_id", "")
    student_name = student.get("student_name", "")
    submissions_raw = student.get("submissions", {})

    submission_results = []
    total_score = 0.0
    graded_count = 0

    for problem_id in PROBLEM_IDS:
        sub = submissions_raw.get(problem_id)
        if sub is None:
            # Chưa nộp
            result = grade_submission(
                student_name=student_name,
                student_code="",
                problem_id=problem_id,
                test_results={"passedTestCases": 0, "totalTestCases": 0, "status": None},
            )
        else:
            result = grade_submission(
                student_name=student_name,
                student_code=sub.get("code", ""),
                problem_id=problem_id,
                test_results={
                    "passedTestCases": sub.get("passedTestCases", 0),
                    "totalTestCases": sub.get("totalTestCases", 0),
                    "status": sub.get("status"),
                },
            )

        submission_results.append(result)
        total_score += result["score"]
        graded_count += 1

    avg_score = round(total_score / graded_count, 2) if graded_count > 0 else 0.0

    return {
        "student_id": student_id,
        "student_name": student_name,
        "average_score": avg_score,
        "submissions": submission_results,
    }


# ---------------------------------------------------------------------------
# Console reporting
# ---------------------------------------------------------------------------

_SEP = "─" * 72


def _print_submission_summary(sub: dict) -> None:
    """In tóm tắt một bài nộp."""
    score = sub["score"]
    grade = sub["grade"]
    errors = sub.get("errors", [])
    diff = sub.get("graph_diff", {})

    print(f"  {'Bài':12s}: {sub['problem_name']}")
    print(f"  {'Trạng thái':12s}: {sub['status']}")
    print(f"  {'Điểm':12s}: {score}/10  (Xếp loại: {grade})")
    print(
        f"  {'Test':12s}: {sub['passed_tests']}/{sub['total_tests']} "
        f"| Tương đồng graph: {diff.get('similarity_score', 0):.1%}"
    )

    if errors:
        print(f"  {'Lỗi':12s}: {len(errors)} lỗi phát hiện")
        for err in errors[:3]:
            sev = err.get("severity", "")
            desc = err.get("description", "")
            prefix = {"critical": "🔴", "major": "🟡", "minor": "🟢"}.get(sev, "  ")
            print(f"    {prefix} [{sev.upper()}] {desc}")
        if len(errors) > 3:
            print(f"    ... và {len(errors) - 3} lỗi khác")

    comment = sub["feedback"].get("overall_comment", "")
    if comment:
        wrapped = textwrap.fill(comment, width=65, initial_indent="    ", subsequent_indent="    ")
        print(f"  {'Nhận xét':12s}:")
        print(wrapped)

    # In hướng dẫn sửa lỗi
    repair_steps = sub.get("repair_steps", [])
    if repair_steps and repair_steps[0].get("error_type") != "none":
        print(f"  {'Sửa lỗi':12s}: {len(repair_steps)} bước")
        for step in repair_steps[:2]:
            print(f"    Bước {step['step_number']}: {step['title']}")
            if step.get("wrong_code"):
                print(f"      ✗ {step['wrong_code']}")
            if step.get("correct_code"):
                print(f"      ✓ {step['correct_code']}")


def print_student_report(student_result: dict) -> None:
    """In báo cáo đầy đủ cho một sinh viên."""
    print(f"\n{'═' * 72}")
    print(f"  SINH VIÊN: {student_result['student_name']} ({student_result['student_id']})")
    print(f"  Điểm trung bình: {student_result['average_score']}/10")
    print(f"{'═' * 72}")

    for sub in student_result["submissions"]:
        print(_SEP)
        _print_submission_summary(sub)

    print(_SEP)


def print_summary_table(all_results: list[dict]) -> None:
    """In bảng tóm tắt điểm tất cả sinh viên."""
    print(f"\n{'═' * 72}")
    print("  BẢNG ĐIỂM TÓM TẮT")
    print(f"{'═' * 72}")
    header = f"  {'Họ tên':<25} {'Numpy01':>8} {'Numpy02':>8} {'Pandas01':>8} {'Pandas02':>8} {'TB':>6}"
    print(header)
    print(f"  {'-'*65}")

    for sr in all_results:
        scores = [f"{s['score']:>7.1f}" for s in sr["submissions"]]
        avg = f"{sr['average_score']:>5.1f}"
        name = sr["student_name"][:24]
        print(f"  {name:<25} {' '.join(scores)} {avg}")

    print(f"{'═' * 72}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("  HỆ THỐNG AUTO_GRADE – Tự động chấm điểm và phản hồi code")
    print(f"  Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 72)

    # Kiểm tra file dữ liệu
    if not os.path.exists(DATA_FILE):
        print(f"[LỖI] Không tìm thấy file dữ liệu: {DATA_FILE}")
        sys.exit(1)

    # Đọc dữ liệu
    print(f"\n📂 Đọc dữ liệu từ: {DATA_FILE}")
    students = load_students(DATA_FILE)
    total_students = len(students)
    print(f"   Tổng số sinh viên: {total_students}")
    print(f"   Chấm điểm: {MAX_STUDENTS} sinh viên đầu\n")

    # Chấm điểm
    students_to_grade = students[:MAX_STUDENTS]
    all_results: list[dict] = []

    for i, student in enumerate(students_to_grade, 1):
        name = student.get("student_name", f"SV{i:03d}")
        sid = student.get("student_id", f"SV{i:03d}")
        print(f"⏳ [{i}/{len(students_to_grade)}] Đang chấm: {name} ({sid})...")

        result = grade_student(student)
        all_results.append(result)
        print_student_report(result)

    # In bảng tóm tắt
    print_summary_table(all_results)

    # Lưu kết quả
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_results(all_results, RESULTS_FILE)
    save_report_csv(all_results, REPORT_FILE)

    print(f"✅ Đã lưu kết quả:")
    print(f"   JSON : {RESULTS_FILE}")
    print(f"   CSV  : {REPORT_FILE}")
    print()


if __name__ == "__main__":
    main()

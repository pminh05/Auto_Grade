"""
convert_data.py – Chuyển đổi CLC11.json (định dạng gốc từ hệ thống)
sang định dạng chuẩn mà main.py / grader.py yêu cầu.

Định dạng đầu vào (CLC11.json):
{
  "data": [
    {
      "_id": "...",
      "email": "11244329@st.neu.edu.vn",
      "name": "Le Thi Ngoc Linh",
      "<problemId>": {
        "problemId": "...",
        "name": "Numpy 01 - ...",
        "answer": { "files": { "solution": "<code>" }, ... },
        "latestStatus": 3 | 4 | 5 | null,
        "passedTestCases": 1,
        "totalTestCases": 1
      },
      ...
    }
  ]
}

Định dạng đầu ra (data/CLC11_converted.json):
[
  {
    "student_id": "11244329",
    "student_name": "Le Thi Ngoc Linh",
    "email": "11244329@st.neu.edu.vn",
    "submissions": {
      "numpy_01":  { "code": "...", "status": 3, "passedTestCases": 1, "totalTestCases": 1 },
      "numpy_02":  { ... },
      "pandas_01": { ... },
      "pandas_02": { ... }
    }
  },
  ...
]

Chạy:
    python convert_data.py
    python convert_data.py --input data/CLC11.json --output data/CLC11_converted.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Mapping: problemId  →  slug nội bộ dùng trong grader
# ---------------------------------------------------------------------------
# Lấy từ các "slug" trong JSON gốc, ví dụ:
#   "numpy-01-phan-tich-loi-nhuan-ban-hang-68dbc899fdd70279dba7dd24"
# Quy tắc: prefix "numpy-01" / "numpy-02" / "pandas-01" / "pandas-02"

_SLUG_PREFIX_MAP: dict[str, str] = {
    "numpy-01":  "numpy_01",
    "numpy-02":  "numpy_02",
    "pandas-01": "pandas_01",
    "pandas-02": "pandas_02",
}

# Fallback: map trực tiếp theo problemId đã biết (phòng khi slug thay đổi)
_PROBLEM_ID_MAP: dict[str, str] = {
    "68dbc899fdd70279dba7dd24": "numpy_01",
    "68dbff0efdd70279dba81f6c": "numpy_02",
    "68dc00c1fdd70279dba8260d": "pandas_01",
    "68dc0359fdd70279dba82f6e": "pandas_02",
}

# Các key trong bản ghi sinh viên KHÔNG phải problemId
_NON_PROBLEM_KEYS = {"_id", "email", "name"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_problem_key(problem_id: str, slug: str) -> str | None:
    """
    Trả về key nội bộ (numpy_01 / ...) từ problemId hoặc slug.
    Ưu tiên map cứng theo problemId, sau đó thử theo prefix của slug.
    """
    # 1. Map cứng theo problemId
    if problem_id in _PROBLEM_ID_MAP:
        return _PROBLEM_ID_MAP[problem_id]

    # 2. Thử prefix 8 ký tự đầu của problemId (phòng dữ liệu mới)
    for pid_prefix, key in _PROBLEM_ID_MAP.items():
        if problem_id.startswith(pid_prefix[:8]):
            return key

    # 3. Thử khớp slug prefix
    if slug:
        for prefix, key in _SLUG_PREFIX_MAP.items():
            if slug.startswith(prefix):
                return key

    return None

def _extract_code(answer: dict | None) -> str:
    """Lấy source code từ trường answer.files.solution."""
    if not answer:
        return ""
    files = answer.get("files", {})
    return files.get("solution", "")


def _extract_student_id(email: str) -> str:
    """Lấy mã sinh viên từ email (phần trước @)."""
    return email.split("@")[0] if email else ""


def _map_status(status: int | None) -> int | None:
    """Giữ nguyên mã trạng thái (3=pass, 4=wrong, 5=error, 11=compile_error, None=not_submitted)."""
    return status

# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_student(raw: dict) -> dict:
    """Chuyển một bản ghi sinh viên sang định dạng chuẩn."""
    email = raw.get("email", "")
    student_id = _extract_student_id(email)
    student_name = raw.get("name", "")

    submissions: dict[str, dict] = {}

    for key, value in raw.items():
        if key in _NON_PROBLEM_KEYS:
            continue
        if not isinstance(value, dict):
            continue

        # Kiểm tra đây có phải bản ghi bài nộp không
        problem_id = value.get("problemId", "")
        if not problem_id:
            continue

        slug = value.get("slug", "")
        problem_key = _resolve_problem_key(problem_id, slug)

        if problem_key is None:
            # Bài không nhận ra – bỏ qua nhưng cảnh báo
            print(f"  [WARN] Không nhận ra problemId={{problem_id!r}} (slug={{slug!r}}) \
                  – bỏ qua bài này cho SV {{student_name!r}}.",
                  file=sys.stderr)
            continue

        answer = value.get("answer")
        code = _extract_code(answer)

        submissions[problem_key] = {
            "code":             code,
            "status":           _map_status(value.get("latestStatus")),
            "passedTestCases":  value.get("passedTestCases", 0),
            "totalTestCases":   value.get("totalTestCases", 0),
            # Thông tin bổ sung (không bắt buộc cho grader)
            "problem_name":     value.get("name", ""),
            "submission_id":    value.get("submissionId"),
            "submission_time":  value.get("latestSubmissionTime"),
        }

    return {
        "student_id":   student_id,
        "student_name": student_name,
        "email":        email,
        "submissions":  submissions,
    }


def convert(input_path: str, output_path: str) -> None:
    """Đọc file JSON gốc, chuyển đổi, ghi ra file đích."""
    print(f"📂 Đọc  : {{input_path}}")
    with open(input_path, encoding="utf-8") as fh:
        raw_data = json.load(fh)

    # Hỗ trợ cả hai dạng: {"data": [...]}  hoặc  [...] 
    if isinstance(raw_data, dict) and "data" in raw_data:
        students_raw = raw_data["data"]
    elif isinstance(raw_data, list):
        students_raw = raw_data
    else:
        print("[LỖI] Định dạng JSON không hợp lệ – cần list hoặc {\"data\": list}.")
        sys.exit(1)

    print(f"   Tìm thấy {{len(students_raw)}} sinh viên.")

    converted = []
    for raw in students_raw:
        student = convert_student(raw)
        converted.append(student)
        # Thống kê nhanh
        n_submitted = sum(
            1 for s in student["submissions"].values()
            if s.get("status") is not None
        )
        print(f"   ✔ {{student['student_name']:<30}} – {{n_submitted}}/4 bài nộp")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(converted, fh, ensure_ascii=False, indent=2)

    print(f"\n✅ Đã lưu : {{output_path}}")
    print(f"   Tổng   : {{len(converted)}} sinh viên được chuyển đổi.\n")

    # In thống kê tóm tắt
    _print_stats(converted)


def _print_stats(converted: list[dict]) -> None:
    """In thống kê bài nộp."""
    problem_keys = ["numpy_01", "numpy_02", "pandas_01", "pandas_02"]
    problem_labels = {
        "numpy_01":  "Numpy 01",
        "numpy_02":  "Numpy 02",
        "pandas_01": "Pandas 01",
        "pandas_02": "Pandas 02",
    }
    status_labels = {
        3:    "Passed     ",
        4:    "Wrong Ans  ",
        5:    "Runtime Err",
        11:   "Compile Err",
        None: "Chưa nộp  ",
    }

    print("─" * 60)
    print(f"  {{'Bài':<12}} {{'Nộp':>5}} {{'Pass':>5}} {{'Wrong':>6}} {{'Error':>6}} {{'Thiếu':>6}}")
    print("─" * 60)
    for pk in problem_keys:
        statuses = [s.get("submissions", {}).get(pk, {}).get("status") for s in converted]
        submitted = sum(1 for s in statuses if s is not None)
        passed    = sum(1 for s in statuses if s == 3)
        wrong     = sum(1 for s in statuses if s == 4)
        error     = sum(1 for s in statuses if s in (5, 11))
        missing   = len(converted) - submitted
        print(f"  {{problem_labels[pk]:<12}} {{submitted:>5}} {{passed:>5}} {{wrong:>6}} {{error:>6}} {{missing:>6}}")
    print("─" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chuyển đổi CLC11.json sang định dạng Auto_Grade chuẩn."
    )
    parser.add_argument(
        "--input", "-i",
        default=os.path.join("data", "CLC11.json"),
        help="Đường dẫn file JSON đầu vào (mặc định: data/CLC11.json)",
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join("data", "CLC11_converted.json"),
        help="Đường dẫn file JSON đầu ra (mặc định: data/CLC11_converted.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    convert(args.input, args.output)
# Auto_Grade – Hệ thống Tự động Chấm điểm và Phản hồi Code

Hệ thống tự động chấm điểm code Python cho sinh viên, sử dụng phân tích đồ thị ngữ nghĩa (AST/CFG) để phát hiện lỗi, phân loại mức độ, và tạo hướng dẫn sửa lỗi chi tiết bằng tiếng Việt.

---

## Quy trình hệ thống

```
Student Code ──► Build Semantic Graph ──► Graph Comparison ──► Error Classification
                                                │                        │
Reference Solution ──► Build Semantic Graph ───┘                        │
                                                                         ▼
                                                              Repair Step Generation
                                                                         │
                                                                         ▼
                                                         LLM Prompt + Feedback Generation
                                                                         │
                                                                         ▼
                                                    Score + Detailed Feedback + Repair Guide
```

---

## Cấu trúc thư mục

```
Auto_Grade/
├── data/
│   └── CLC11.json              # Dữ liệu 30 sinh viên, 4 bài mỗi người
├── src/
│   ├── __init__.py
│   ├── graph_builder.py        # Xây dựng đồ thị ngữ nghĩa từ AST
│   ├── graph_comparator.py     # So sánh đồ thị, phát hiện sự khác biệt
│   ├── error_classifier.py     # Phân loại lỗi và mức độ nghiêm trọng
│   ├── repair_generator.py     # Tạo hướng dẫn sửa lỗi từng bước
│   ├── grader.py               # Pipeline chính
│   └── llm_feedback.py         # Prompt template + mock LLM feedback
├── reference_solutions/
│   ├── numpy_01.py
│   ├── numpy_02.py
│   ├── pandas_01.py
│   └── pandas_02.py
├── output/                     # Kết quả (tự tạo khi chạy)
│   ├── results.json
│   └── report.csv
├── main.py                     # Điểm vào chính
├── requirements.txt
└── README.md
```

---

## Cài đặt

### Yêu cầu hệ thống
- Python 3.9 trở lên

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Các thư viện cần thiết:
- `numpy` – xử lý mảng số
- `pandas` – xử lý dữ liệu dạng bảng
- `networkx` – hỗ trợ đồ thị (tùy chọn)
- `ast` – phân tích cú pháp Python (có sẵn trong standard library)

---

## Chạy hệ thống

### Chấm điểm 5 sinh viên đầu (mặc định)

```bash
python main.py
```

### Kết quả đầu ra

Sau khi chạy, kết quả được lưu vào thư mục `output/`:

- **`output/results.json`** – Kết quả chi tiết dạng JSON, bao gồm:
  - Điểm từng bài, điểm trung bình
  - Danh sách lỗi phân loại (type + severity)
  - Hướng dẫn sửa lỗi từng bước
  - Feedback tổng quan và chi tiết
  - LLM prompt (để tích hợp API sau này)

- **`output/report.csv`** – Báo cáo dạng bảng, có thể mở bằng Excel, bao gồm:
  - Họ tên, mã sinh viên
  - Điểm từng bài
  - Số lỗi, mức tương đồng graph
  - Nhận xét tổng quan

---

## Mô tả các module

### `src/graph_builder.py`
Phân tích AST của code Python và xây dựng đồ thị ngữ nghĩa:
- Phân loại các node: tạo mảng, phép tính numpy, tạo DataFrame, lọc dữ liệu, sắp xếp, in kết quả…
- Theo dõi luồng dữ liệu giữa các biến
- Xử lý lỗi cú pháp

### `src/graph_comparator.py`
So sánh đồ thị sinh viên với đồ thị tham chiếu:
- **Missing nodes**: sinh viên thiếu bước thực hiện
- **Wrong nodes**: thực hiện nhưng sai (hàm sai, axis sai, điều kiện lọc sai…)
- **Extra nodes**: thêm bước không cần thiết
- Tính điểm tương đồng (0–1)

### `src/error_classifier.py`
Phân loại lỗi theo loại và mức độ:
- **Loại**: `syntax` | `logic` | `algorithm` | `data_handling`
- **Mức độ**: `critical` (không chạy được) | `major` (kết quả sai) | `minor` (sai nhỏ)

### `src/repair_generator.py`
Tạo hướng dẫn sửa lỗi từng bước bằng tiếng Việt:
- Tiêu đề mô tả lỗi
- Code sai của sinh viên
- Code đúng gợi ý
- Giải thích nguyên nhân và cách sửa

### `src/grader.py`
Pipeline chính tích hợp tất cả bước, tính điểm theo công thức:
```
Điểm = (70% × test_cases_score) + (30% × code_quality_score)
```

### `src/llm_feedback.py`
Tạo prompt đầy đủ cho LLM và feedback bằng template:
- Prompt bao gồm: đề bài + code sinh viên + kết quả phân tích + hướng dẫn sửa lỗi
- Mock LLM response sử dụng template tiếng Việt
- Có thể tích hợp OpenAI/Gemini/Claude API bằng cách thay hàm `generate_feedback()`

---

## Dữ liệu sinh viên (CLC11.json)

File JSON chứa danh sách 30 sinh viên, mỗi sinh viên có 4 bài nộp:

```json
[
  {
    "student_id": "SV001",
    "student_name": "Nguyễn Văn An",
    "class": "CLC11",
    "submissions": {
      "numpy_01": {
        "code": "import numpy as np\n...",
        "status": 3,
        "passedTestCases": 1,
        "totalTestCases": 1
      },
      "numpy_02": { "...": "..." },
      "pandas_01": { "...": "..." },
      "pandas_02": { "...": "..." }
    }
  }
]
```

**Mã trạng thái:**
- `3` – Đúng (Passed)
- `4` – Sai kết quả (Wrong Answer)
- `5` – Lỗi khi chạy (Runtime Error)
- `null` – Chưa nộp

---

## Tích hợp LLM thật (tùy chọn)

Để tích hợp với API LLM thật, chỉnh sửa hàm `generate_feedback()` trong `src/llm_feedback.py`:

```python
import openai

def generate_feedback(...) -> dict:
    prompt = build_prompt(...)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.choices[0].message.content)
    return result
```

---

## Ví dụ kết quả

```
═══════════════════════════════════════════════════════════════════════
  SINH VIÊN: Hoàng Đức Em (SV005)
  Điểm trung bình: 2.9/10
═══════════════════════════════════════════════════════════════════════
  Bài        : Numpy 01 – Phân tích lợi nhuận bán hàng
  Trạng thái : wrong_answer
  Điểm       : 2.84/10  (Xếp loại: F)
  Test       : 0/1 | Tương đồng graph: 75.0%
  Lỗi        : 1 lỗi phát hiện
    🟡 [MAJOR] Dùng 'argmax' thay vì 'sum'
  Nhận xét   :
    Code bài Numpy 01 có lỗi algorithm cần sửa...
  Sửa lỗi    : 1 bước
    Bước 1: Sai hàm tính đếm – dùng np.argmax thay vì np.sum
      ✗ so_san_pham = np.argmax(loi_nhuan_moi_sp >= 10000)
      ✓ so_san_pham = np.sum(loi_nhuan_moi_sp >= 10000)
```

---

## Giấy phép

Dự án này được phát triển cho mục đích giáo dục.
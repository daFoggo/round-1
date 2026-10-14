# AI Tài Năng 2026 - Chủ đề 2: Hỏi đáp trên Bảng tính Excel (Table-QA)

Hệ thống hỏi đáp tự động trên bảng tính Excel phân cấp, đa tầng, có ô gộp và đa bảng được xây dựng theo kiến trúc **FastAPI Bigger Applications** và phương pháp kết hợp **Deterministic Preprocessing + Program-Aided Table-QA (Code Generation & Execution with Self-Correction)**.

---

## 1. Kiến trúc Hệ thống & Luồng xử lý (Architecture & Data Flow)

```mermaid
flowchart TD
    subgraph S1["1. Tiền xử lý Xác định (Deterministic Preprocessing)"]
        F["File Excel (.xlsx)"] --> P1["openpyxl: data_only=True<br/>(Đọc giá trị cache của formula)"]
        P1 --> P2["Unmerge & Broadcast Cells<br/>(Lấp đầy giá trị ô gộp)"]
        P2 --> P3["Table Boundary Detection<br/>(Tự động chia tách đa bảng trên cùng 1 sheet)"]
        P3 --> P4["Dual-Hierarchy Extraction<br/>• Header_Path (A > B > C)<br/>• Row_Path (Multi-level Stacking / Indent Levels)"]
        P4 --> P5["Clean Footnote Artifacts<br/>(Regex r'\b\d+/(?=\s|$)', lọc bỏ dòng Note cuối)"]
    end

    subgraph S2["2. Nén Cấu trúc & Prompting"]
        P5 --> C1["Lấy cảm hứng từ SpreadsheetLLM Anchors<br/>(Schema + Value Dtypes + Toàn bộ danh sách Row_Path)"]
        C1 --> PR["Dynamic Prompt Builder<br/>(Hỗ trợ Multi-table, Typos & Word Boundaries)"]
        Q["Câu hỏi (Query)"] --> PR
    end

    subgraph S3["3. Program-Aided Generation & Execution"]
        PR --> LLM["LLM (Qwen3.7-Flash / Gemini)"]
        LLM --> CODE["Sinh mã Python / Pandas code<br/>(Lưu kết quả vào biến 'FINAL_ANSWER')"]
        CODE --> EXEC["Restricted Python Executor<br/>(Môi trường giới hạn builtins, timeout 10s)"]
    end

    subgraph S4["4. Self-Correction & Chuẩn hoá đầu ra"]
        EXEC -- "Thất bại (Traceback / NaN / Rỗng)" --> FEEDBACK["Self-Debug Feedback Loop<br/>(Phản hồi mã lỗi & hướng dẫn sửa truy vấn)"]
        FEEDBACK --> LLM
        EXEC -- "Thành công (Raw Result)" --> FMT["Regex & Exact Match Formatter<br/>(Làm tròn số, format ngày, chuẩn hoá text)"]
        FMT --> OUT["submission.csv / API Response"]
    end
```

---

## 2. Nền tảng Lý thuyết & Nguồn Paper tương ứng trong Code

Mỗi module trong codebase được thiết kế dựa trên các bài báo khoa học và công trình nghiên cứu hàng đầu về Xử lý Bảng tính và LLM:

### 2.1. Dual-Hierarchy Representation (Biểu diễn phân cấp kép)
* **Nguồn Paper:** *HiTab: A Hierarchical Table Dataset for Question Answering and Natural Language Generation* (ACL 2022 - Microsoft Research). [arXiv:2108.06712](https://arxiv.org/abs/2108.06712)
* **Vấn đề giải quyết:** Bảng tính thực tế luôn có header nhiều tầng (2–4 dòng) và nhãn dòng phân cấp thụt đầu dòng (indentation) hoặc nhóm phân tầng. Nếu chỉ đọc thô, các dòng con sẽ bị trùng lặp tên (ví dụ: các dòng tuổi `16 to 19 years` lặp lại ở cả nhóm Total, Men và Women).
* **Áp dụng trong Code ([`app/services/preprocessor.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/preprocessor.py)):**
  - **Header Flattening:** Nối các tầng header thành chuỗi duy nhất: `Category | Metric | Year`.
  - **Multi-Level Row Stacking:** 
    - Nhận diện cột `Indent Level` (nếu có) để dựng cây cha - con theo cấp bậc thụt lề bằng cấu trúc stack.
    - Nhận diện các nhóm cha nhân khẩu học (`..., 16 years and over`, các nhóm chủng tộc, tình trạng hôn nhân) dù dòng đó có chứa dữ liệu số, tạo nên tọa độ hàng hoàn chỉnh: `Section | Sub_Section | Item` (ví dụ: `AGE AND SEX | Men, 16 years and over | 16 to 19 years`).
  - **Kết quả thực nghiệm:** Tỷ lệ dòng trùng `Row_Path` giảm từ 32–66 dòng/bảng xuống **0 dòng trùng lặp (100% Unique)** trên toàn bộ tập dữ liệu mẫu.

### 2.2. Deterministic Preprocessing vs. End-to-End LLM
* **Nguồn Paper:** *TableEval: A Real-World Benchmark for Complex, Multilingual, and Multi-Structured Table QA* (ACL Anthology 2025). [ACL Anthology](https://aclanthology.org/2025.emnlp-main.363.pdf)
* **Vấn đề giải quyết:** Nghiên cứu TableEval chỉ ra các LLM hàng đầu (như o1-preview, Claude 3.5 Sonnet) đều tụt 10–15% độ chính xác trên bảng phân cấp và **không mô hình nào vượt quá 70% độ chính xác khi nhận diện ô gộp (merged cells)** nếu đưa bảng thô vào prompt.
* **Áp dụng trong Code ([`app/services/preprocessor.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/preprocessor.py)):**
  - Không để LLM tự đoán ô gộp. Toàn bộ logic unmerge, đọc formula cache (`data_only=True`), và loại bỏ footnote `(1)`, `\b\d+/(?=\s|$)` được xử lý xác định bằng mã lệnh Python thuần với `openpyxl` trước khi đưa dữ liệu vào LLM.

### 2.3. Tách Đa Bảng trên cùng 1 Sheet (Multi-Table Partitioning)
* **Vấn đề giải quyết:** Các bảng dữ liệu (như `p4_t02.xlsx`) thường xếp chồng nhiều bảng độc lập trên cùng một trang tính (ví dụ bảng `Fiscal years` xếp trên bảng `Calendar years`, ngăn cách bởi khoảng trống và tiêu đề mới).
* **Áp dụng trong Code ([`app/services/preprocessor.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/preprocessor.py) -> `detect_table_ranges()`):**
  - Thuật toán phân tích cấu trúc phát hiện biên giới bảng độc lập, tự động phân rã worksheet thành các DataFrames riêng biệt (`Monsumtable - Fiscal years` và `Monsumtable - Calendar years`).

### 2.4. Structural Anchors (Lấy cảm hứng từ ý tưởng nén của SpreadsheetLLM)
* **Nguồn Paper:** *SpreadsheetLLM: Encoding Spreadsheets for Large Language Models* (EMNLP 2024 - Microsoft Research). [arXiv:2407.09025](https://arxiv.org/abs/2407.09025)
* **Áp dụng trong Code ([`app/services/preprocessor.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/preprocessor.py) -> `generate_table_summary()`):**
  - Thay vì đưa toàn bộ cell thô gây tốn token và vượt context, hệ thống cung cấp danh mục cột (`Columns`), danh mục toàn bộ các nhãn hàng hợp lệ (`Available Row_Paths` lên đến 150 dòng bao quát toàn bộ bảng dài như `p4_t07`), và mẫu dữ liệu đại diện. Điều này giúp LLM định vị chính xác chuỗi cần truy vấn mà không phải đoán mò.

### 2.5. Program-Aided Table-QA (Code Generation & Execution)
* **Nguồn Paper:**
  - *PAL: Program-aided Language Models* (ICML 2023 - Carnegie Mellon University). [arXiv:2211.10435](https://arxiv.org/abs/2211.10435)
  - *Program of Thoughts Prompting* (TMLR 2023). [arXiv:2211.12588](https://arxiv.org/abs/2211.12588)
* **Vấn đề giải quyết:** LLM có khả năng hiểu ngữ nghĩa ngôn ngữ tự nhiên tốt nhưng tính toán số học rất dễ sinh ảo giác (hallucination).
* **Áp dụng trong Code ([`app/services/pipeline.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/pipeline.py) & [`app/services/executor.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/executor.py)):**
  - LLM chỉ sinh code logic truy vấn bằng Python (`pandas`) dựa trên các mẫu lập trình trừu tượng (abstract patterns).
  - Quá trình tính toán thực tế được thực thi trong môi trường `Restricted Python Executor`, đảm bảo độ chính xác tính toán tuyệt đối.

### 2.6. Hướng tiếp cận Text-to-Pandas
* **Nguồn Tham khảo:** *SemEval-2025 Task 8: Question Answering over Tabular Data (DataBench)*. Nhiều đội nhóm đạt thứ hạng cao (như sonrobok4 - [SemEval 2025](https://preview.aclanthology.org/setup/2025.semeval-1.51) và IUST_Champs - [SemEval 2025](https://preview.aclanthology.org/setup/2025.semeval-1.260)) đã chứng minh tính hiệu quả vượt trội của việc chuyển đổi câu hỏi tự nhiên thành mã xử lý dữ liệu Python (Text-to-Python/Pandas) kết hợp lọc metadata cấu trúc. Pandas tỏ ra linh hoạt hơn SQL khi xử lý chuỗi phân cấp, regex, chuyển đổi kiểu dữ liệu tức thời và thao tác trên bảng bán cấu trúc.

### 2.7. Traceback-driven Self-Correction (Vòng lặp tự sửa lỗi)
* **Nguồn Paper:**
  - *Self-Debug: Teaching Large Language Models to Self-Debug* (ICLR 2024 - Chen et al.). [arXiv:2304.05128](https://arxiv.org/abs/2304.05128)
  - *InterCode: Standardizing and Benchmarking Interactive Coding with Execution Feedback* (NeurIPS 2023 - Yang et al.). [arXiv:2306.14898](https://arxiv.org/abs/2306.14898)
* **Áp dụng trong Code ([`app/services/pipeline.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/app/services/pipeline.py)):**
  - Hàm `is_invalid_result()` theo dõi không chỉ các exception (Traceback) mà còn bắt các trường hợp tính ra `NaN`, `None` hoặc chuỗi rỗng để kích hoạt feedback loop gửi lại cho LLM sửa mã truy vấn.

### 2.8. So sánh & Phân tích các hướng tiếp cận khác
| Phương pháp | Phân tích tính tương thích với bài toán |
| :--- | :--- |
| **Text2SQL thuần (DIN-SQL / CHESS)** | Giả định schema quan hệ sạch đạt chuẩn 1NF/2NF. Khi gặp bảng Excel có chú thích, footnote, dòng trống, nhãn lồng nhau, Text2SQL sinh câu lệnh SQL sai cú pháp hoặc trả về tập rỗng do thiếu schema quan hệ chuẩn hoá. |
| **MaskSQL ([arXiv:2509.23459](https://arxiv.org/abs/2509.23459))** | Là công trình nghiên cứu về **bảo vệ quyền riêng tư dữ liệu (Privacy-preserving Text-to-SQL)**, sử dụng cơ chế xáo trộn/che giấu (masking/perturbation) tên bảng, cột và giá trị tế nhị trước khi gửi sang LLM từ xa để tránh lộ bí mật dữ liệu. Paper cho thấy cơ chế bảo mật này làm tăng ~4.5 lần chi phí token và suy giảm 13–20 điểm accuracy do giảm sút thông tin ngữ cảnh. Phương pháp này không phù hợp với bài toán tối ưu độ chính xác và tài nguyên của Vòng 1. |

---

## 3. Khả năng Tổng quát hoá & Xử lý Trường hợp Biên (Edge Cases)

Hệ thống được thiết kế hướng tới tập dữ liệu ẩn thực tế:

1. **Workbook nhiều sheet & nhiều bảng trên 1 sheet:**
   - `preprocessor.py` duyệt toàn bộ sheet và tự động tách các bảng độc lập vào `dfs: Dict[str, pd.DataFrame]`. LLM được cung cấp đầy đủ tên bảng để lựa chọn chính xác.
2. **Cột Indent Level và phân cấp nhân khẩu học:**
   - Tự động nhận diện cột thụt lề bằng số (0, 1, 2, 3...) hoặc phân tầng nhân khẩu học theo nhóm cha để bảo đảm `Row_Path` luôn mang đầy đủ ngữ cảnh phân cấp, triệt tiêu hoàn toàn hiện tượng trùng tên hàng.
3. **Phân biệt từ khóa có chứa nhau (Word Boundary Matching):**
   - Hướng dẫn LLM bắt buộc sử dụng ranh giới từ `r'\bterm\b'` (ví dụ: `r'\bmen\b'` để không khớp nhầm vào `women`).
4. **Môi trường thực thi giới hạn (Restricted Execution):**
   - Chạy với namespace builtins được kiểm soát và timeout 10 giây để chống lặp vô tận và bảo vệ môi trường chấm thi offline.

---

## 4. Cấu trúc Dự án (FastAPI Bigger Applications Layout)

Dự án được tổ chức theo chuẩn kiến trúc hướng module [FastAPI - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/):

```
round-1/
├── app/
│   ├── __init__.py          # Khởi tạo app package
│   ├── main.py              # FastAPI Application + CLI Entrypoint
│   ├── config.py            # Quản lý Settings tập trung bằng pydantic-settings
│   ├── dependencies.py      # Dependency injection (get_qa_pipeline, get_settings)
│   ├── models/              # Pydantic Schemas định kiểu nghiêm ngặt
│   │   ├── __init__.py
│   │   └── schemas.py       # QueryItem, QueryResponse, EvaluationMetric
│   ├── services/            # Core Business Logic & Algorithms
│   │   ├── __init__.py
│   │   ├── preprocessor.py  # Thuật toán Dual-Hierarchy, Multi-table & Indent Level
│   │   ├── llm_client.py    # LLM Client (Gemini & OpenRouter Qwen3.7-Flash)
│   │   ├── executor.py      # Restricted Execution với timeout & traceback capture (PAL)
│   │   ├── formatter.py     # Rule-based Exact Match Post-processor
│   │   └── pipeline.py      # Pipeline Orchestrator với Self-Correction Loop (Self-Debug)
│   └── routers/             # REST API Endpoints mở rộng
│       ├── __init__.py
│       ├── health.py        # GET /health
│       └── qa.py            # POST /qa/ask, POST /qa/batch
├── main.py                  # CLI Wrapper ở root tương thích dòng lệnh thực thi
├── evaluate.py              # Script đánh giá Exact Match trên 20 câu mẫu (Dev Set)
├── unseen_evaluation.py     # Script đánh giá độc lập trên 25 câu hỏi Unseen (Test Set)
├── unseen_evaluation_report.json # Báo cáo chi tiết kết quả kiểm thử Unseen
├── .env.example             # File mẫu cấu hình biến môi trường an toàn
├── Dockerfile               # Dockerfile tối ưu đa tầng với uv
├── docker-compose.yml       # Docker Compose triển khai độc lập
├── pyproject.toml           # Quản lý dự án với uv
└── requirements.txt         # Danh mục dependencies đã khóa phiên bản
```

---

## 5. Hướng dẫn Cài đặt & Sử dụng

### 5.1. Cài đặt môi trường

Sử dụng `uv` (Khuyên dùng - Cài đặt nhanh trong vài giây):
```bash
uv sync
```

Hoặc sử dụng `pip`:
```bash
pip install -r requirements.txt
```

### 5.2. Cấu hình file `.env`

Sao chép `.env.example` thành `.env` tại thư mục gốc:
```env
# Khi chấm thi chính thức (sử dụng OpenRouter Qwen3.7-Flash theo quy chế BTC):
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=qwen/qwen3.7-flash
LLM_PROVIDER=openrouter

# Hoặc khi thử nghiệm cục bộ với Gemini:
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
LLM_PROVIDER=gemini
```

### 5.3. Chạy chương trình

#### Lệnh chạy chương trình (Khuyến nghị cho kiểm thử & chấm thi):
```bash
uv run python main.py --input_dir xlsx_files --queries queries.json --output submission.csv
```

#### Đánh giá trên tập phát triển mẫu 20 câu (Development Evaluation):
```bash
uv run python evaluate.py
```

#### Đánh giá độc lập trên bộ 25 câu hỏi Unseen (Unseen Benchmark):
```bash
uv run python unseen_evaluation.py
```

#### Chạy qua Docker:
```bash
# Khởi động dịch vụ trong container
docker compose up --build -d

# Thực thi sinh file kết quả bên trong container:
docker compose exec app python main.py --input_dir xlsx_files --queries queries.json --output submission.csv

# Hoặc truy cập Swagger UI trực quan:
# http://localhost:8000/docs
```

---

## 6. Ghi nhận Thực nghiệm (Experimental Observations)

### 6.1. Đánh giá trên Tập Kiểm thử Độc lập Unseen (25 câu hỏi mới)
Để kiểm tra năng lực tổng quát hóa thực sự mà **không dựa dẫm vào 20 câu hỏi mẫu ban đầu**, một bộ benchmark độc lập gồm 25 câu hỏi mới tinh ([`unseen_evaluation.py`](file:///c:/Users/Foggo/Documents/Dev%20projects/ai-tai-nang-2026/round-1/unseen_evaluation.py)) đã được xây dựng, với Ground Truth được trích xuất trực tiếp bằng tọa độ ô `openpyxl`:

* **Độ chính xác tổng thể (Exact Match):** **25 / 25 (100.0%)**
* **Thời gian phản hồi trung bình:** **~21.99s / câu**
* **Số lượt thử lại (Self-Correction):** 3 câu kích hoạt thành công vòng lặp tự sửa lỗi ở lượt retry đầu tiên (`p4_u012`, `p4_u015`, `p4_u019`).
* **Chi tiết theo từng nhóm bài toán biên:**
  1. *Đa bảng trên 1 sheet (`p4_t02.xlsx` - Khối Calendar years):* **5 / 5 (100%)**
  2. *Phân cấp hàng sâu Men vs. Women (`p4_t10.xlsx`):* **5 / 5 (100%)**
  3. *Cây phân cấp Indent Level 3 & 4 (`p4_t03.xlsx`):* **5 / 5 (100%)**
  4. *Bảng dài 114 dòng không bị cắt nhãn (`p4_t07.xlsx` dòng 40–114):* **5 / 5 (100%)**
  5. *Đa sheet (`test_multisheet.xlsx`) & Chịu lỗi chính tả (Typos):* **5 / 5 (100%)**

### 6.2. Đánh giá trên Tập Phát triển Mẫu (20 câu hỏi `queries.json`)
* **Độ chính xác (Exact Match):** **20 / 20 (100.0%)** khi chạy với prompt đã được trừu tượng hóa hoàn toàn.
* **Thời gian phản hồi trung bình:** **~22.5s / câu hỏi** (Tổng 450s / 20 câu).
* **Bộ nhớ RAM tiêu thụ:** **< 150 MB** (hoàn toàn nằm trong giới hạn tài nguyên).
* **Số dòng Row_Path trùng lặp:** **0 dòng trùng** trên toàn bộ 10 file bảng tính.

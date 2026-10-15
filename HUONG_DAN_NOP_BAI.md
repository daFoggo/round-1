# HƯỚNG DẪN NỘP BÀI – BẢNG C (Vòng Khu vực)

> Chuyển thể từ `AI2026_Hướng dẫn nộp bài Vòng Khu vực Bảng C.pdf` – Cuộc thi Sáng tạo Trẻ Quốc gia trong lĩnh vực Trí tuệ Nhân tạo năm 2026.
> Phần cuối là **checklist** đối chiếu với codebase hiện tại (kết hợp thêm các giới hạn trong [`DE_THI.md`](DE_THI.md)).

---

## 1. Cấu trúc bài nộp

- Bài nộp là **một tệp ZIP không quá 100 MB**.
- Tên file zip đặt theo **tên đội**, ví dụ đội `team001` → `team001.zip`.
- **Chỉ `Dockerfile` bắt buộc nằm ngay ở thư mục gốc** của ZIP; tên và cấu trúc các tệp còn lại do đội tự chọn:

```
team001.zip
|-- Dockerfile
`-- ...mã nguồn và tệp cần thiết...
```

- `Dockerfile` phải nằm ngay ở gốc tệp ZIP, **không** đặt trong một thư mục con khác.
- Ảnh Docker phải chạy trên **Linux amd64**, **không dùng GPU** và **chứa sẵn toàn bộ mã nguồn cùng thư viện cần thiết**.
- **Không đưa khóa API vào bài nộp.**

## 2. Entrypoint

Ảnh Docker phải khai báo `ENTRYPOINT` để nhận các tham số dòng lệnh từ hệ thống chấm. Không bắt buộc ngôn ngữ hoặc tên tệp cụ thể. Ví dụ:

| Ngôn ngữ | ENTRYPOINT |
| :--- | :--- |
| Python | `ENTRYPOINT ["python", "main.py"]` |
| JavaScript | `ENTRYPOINT ["node", "main.js"]` |
| Rust | `ENTRYPOINT ["./app"]` |

Chương trình khai báo trong `ENTRYPOINT` phải nhận các tham số do hệ thống chấm cung cấp và **chỉ thoát với mã 0 sau khi đã ghi xong kết quả**.

## 3. Các tham số hệ thống cung cấp

Hệ thống chạy bài làm với **sáu tham số**:

```
--xlsx-dir /input/xlsx_files
--queries /input/queries.json
--output /output/submission.csv
--openrouter-key <key>
--openrouter-model qwen/qwen3.7-flash
--openrouter-base-url https://openrouter.ai/api/v1
```

Chương trình phải:

- đọc các bảng tính trong thư mục nhận từ `--xlsx-dir`;
- đọc danh sách câu hỏi từ tệp nhận từ `--queries`;
- ghi kết quả vào đúng đường dẫn nhận từ `--output`;
- **không sửa dữ liệu trong `/input`**;
- ghi nhật ký ra stdout hoặc stderr, **không ghi lẫn vào tệp kết quả**.

## 4. Định dạng kết quả

Tệp kết quả phải là **CSV UTF-8** với **đúng hai cột** `id,answer`:

```csv
id,answer
1,11
2,Ngo
```

- Mỗi `id` trong `queries.json` phải xuất hiện **đúng một lần**. Không được thiếu, trùng hoặc thêm `id`.
- Cột `answer` chỉ chứa **đáp án cuối cùng**, không kèm giải thích.

---

## ✅ Checklist trước khi nộp

### A. Đóng gói ZIP
- [x] `Dockerfile` nằm ở gốc repo → gốc ZIP (`scripts/package_submission.py` kiểm tra lại).
- [x] Tên ZIP = tên đội (`python scripts/package_submission.py <ten_doi>` → `dist/<ten_doi>.zip`).
- [x] ZIP ≤ 100 MB (script báo lỗi nếu vượt).
- [x] ZIP **không** chứa `.env`, `.venv`, `.git`, `__pycache__`, file PDF, `output/`, `dist/`.
- [x] Không có API key trong mã nguồn (`.env` bị loại khỏi ZIP và khỏi Docker build context qua `.dockerignore`).
- [ ] Điền đúng **tên đội** khi chạy script đóng gói.

### B. Docker image
- [x] Base image `python:3.12-slim`, build cho `linux/amd64`, không cần GPU.
- [x] Image chứa sẵn mã nguồn + thư viện (`pip install -r requirements.txt` lúc build, không tải gì lúc chạy ngoài gọi OpenRouter).
- [x] Có `ENTRYPOINT ["python", "main.py"]`.
- [x] Không dùng `uv` / `.venv` – chỉ Docker.

### C. Tham số dòng lệnh
- [x] `--xlsx-dir`
- [x] `--queries`
- [x] `--output` (tự tạo thư mục cha nếu chưa có)
- [x] `--openrouter-key` (fallback: biến môi trường `OPENROUTER_API_KEY`)
- [x] `--openrouter-model` (mặc định `qwen/qwen3.7-flash`)
- [x] `--openrouter-base-url` (mặc định `https://openrouter.ai/api/v1`)
- [x] Khi chấm: provider luôn là **OpenRouter** (Gemini chỉ dùng khi thử nghiệm cục bộ).

### D. Hành vi khi chạy
- [x] Chỉ đọc `/input` (mở `.xlsx` ở chế độ đọc, không ghi đè) – đã test với mount `:ro`.
- [x] Log ra stdout/stderr, tệp kết quả chỉ chứa CSV.
- [x] Lỗi ở một câu hỏi không làm hỏng cả lượt chạy (answer rỗng cho câu đó).
- [x] Thoát mã 0 **sau khi** ghi xong `submission.csv`; thoát mã ≠ 0 nếu không đọc được input.
- [x] Code do LLM sinh ra có timeout thực thi (chống lặp vô hạn).
- [x] Gọi OpenRouter có retry cho lỗi tạm thời (429 / 5xx / timeout).

### E. Định dạng kết quả
- [x] CSV UTF-8, header đúng `id,answer`.
- [x] Mỗi `id` xuất hiện đúng 1 lần, không thiếu / trùng / thừa (tự kiểm tra sau khi ghi, xem `scripts/validate_submission.py`).
- [x] `answer` chỉ là đáp án cuối cùng.

### F. Giới hạn tài nguyên (theo `DE_THI.md`)
- [ ] Chi phí ≤ 0.10 USD/câu (kể cả retry) – kiểm tra trên dashboard OpenRouter sau khi chạy validate.
- [x] Thời gian ≤ 40 phút / 20 câu (đo được ~1–3 phút với Gemini; cần đo lại với Qwen).
- [x] Bộ nhớ sử dụng ≤ 1 GB (đã chạy thử với `--memory 1g`, không bị OOM).
- [x] Model chấm thi: `qwen/qwen3.7-flash` qua OpenRouter.

### G. Kiểm thử cuối cùng (mô phỏng hệ thống chấm)
- [x] `docker build --platform linux/amd64 -t ai2026-tableqa .`
- [x] Chạy image với 6 tham số, `/input` mount read-only, có `--memory 1g`.
- [x] `scripts/validate_submission.py` báo hợp lệ.
- [x] Giải nén thử `dist/<ten_doi>.zip` vào thư mục trống → build & chạy lại được.

> ⚠️ **Còn lại:** chạy thử với `qwen/qwen3.7-flash` qua OpenRouter (key trong `.env` đang trống) để xác nhận độ chính xác, chi phí/câu và tên đội khi đóng gói.

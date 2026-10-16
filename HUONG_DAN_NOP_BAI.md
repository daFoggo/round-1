# HƯỚNG DẪN NỘP BÀI – BẢNG C (Vòng Khu vực)

> Chuyển thể từ `AI2026_Hướng dẫn nộp bài Vòng Khu vực Bảng C.pdf` – Cuộc thi Sáng tạo Trẻ Quốc gia trong lĩnh vực Trí tuệ Nhân tạo năm 2026.
> Phần cuối là **checklist** đối chiếu với codebase hiện tại (kết hợp thêm các giới hạn trong [`DE_THI.md`](DE_THI.md)).

---

## 1. Cấu trúc bài nộp

- Bài nộp là **một tệp ZIP không quá 100 MB**.
- Tên file zip đặt theo **mã đội**. Đội của chúng ta: mã **`AI26C0062`** → **`AI26C0062.zip`** (tên tệp phải khớp chính xác mã đội).
- **Chỉ `Dockerfile` bắt buộc nằm ngay ở thư mục gốc** của ZIP; tên và cấu trúc các tệp còn lại do đội tự chọn:

```
AI26C0062.zip
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
- [x] Tên ZIP = mã đội `AI26C0062` (`python scripts/package_submission.py` → `dist/AI26C0062.zip`).
- [x] ZIP ≤ 100 MB (script báo lỗi nếu vượt).
- [x] ZIP **không** chứa `.env`, `.venv`, `.git`, `__pycache__`, file PDF, `output/`, `dist/`.
- [x] Không có API key trong mã nguồn (`.env` bị loại khỏi ZIP và khỏi Docker build context qua `.dockerignore`).
- [x] Mã đội `AI26C0062` đã đặt mặc định trong `scripts/package_submission.py`.

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
- [x] Chỉ dùng **OpenRouter** với `qwen/qwen3.7-flash` (đã gỡ toàn bộ code Gemini).

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
- [x] `id` là số tự nhiên; các dòng được **sắp xếp theo `id` tăng dần**; câu không trả lời được → chuỗi rỗng.

### H. Theo Giải đáp thắc mắc của BTC
- [x] Chỉ cần xử lý `.xlsx`, **nhiều sheet**, **nhiều ngôn ngữ** (đã có file/câu hỏi tiếng Hàn trong bộ p2).
- [x] Quy ước "average across all …": tính trên mọi cột có mặt trong dòng, kể cả cột Total (prompt + test `scripts/ambiguity_eval.py`).
- [x] Chỉ dùng Internet khi build và khi gọi OpenRouter; chỉ dùng LLM do BTC cung cấp (Qwen3.7 Flash).
- [x] Cho phép xử lý song song (`--workers`).
- [ ] Đối chiếu với **template nộp bài** của BTC khi nhận được.

### F. Giới hạn tài nguyên (theo `DE_THI.md`)
- [ ] Chi phí ≤ 0.10 USD/câu (kể cả retry) – log cuối mỗi lượt chạy in tổng `cost` từ `usage` của OpenRouter.
- [ ] Thời gian ≤ 40 phút / 20 câu (chạy song song nhiều tiến trình; có deadline 35 phút để vẫn ghi được CSV).
- [x] Dung lượng đĩa ≤ 1 GB (image + dữ liệu chạy) và **RAM ≤ 4 GB** (theo Giải đáp thắc mắc, Câu 03; trước đây hiểu nhầm là RAM 1 GB). Chạy thử với `--memory 4g`, đo RAM đỉnh thực tế ở bước đánh giá cuối.
- [x] Model chấm thi: `qwen/qwen3.7-flash` qua OpenRouter.

### G. Kiểm thử cuối cùng (mô phỏng hệ thống chấm)
- [x] `docker build --platform linux/amd64 -t ai2026-tableqa .`
- [x] Chạy image với 6 tham số, `/input` mount read-only, có `--memory 4g`.
- [x] `scripts/validate_submission.py` báo hợp lệ.
- [x] Giải nén thử `dist/<ten_doi>.zip` vào thư mục trống → build & chạy lại được.

> ⚠️ **Còn lại:** đánh giá lại bằng `qwen/qwen3.7-flash` (EM, giây/câu, token/câu gồm cả reasoning, cost). Mã đội đã được điền sẵn (`AI26C0062`).

---

## Thông tin cổng nộp bài (từ trang nộp)

- **Mã đội: `AI26C0062`** → tệp nộp bắt buộc tên **`AI26C0062.zip`**.
- **Được nộp và cập nhật liên tục trong thời gian thi.** Mọi lượt nộp đều được lưu; **bản gần nhất trước hạn là bản được dùng để chấm.**
- Yêu cầu kỹ thuật bắt buộc (tóm tắt đúng như trang nộp):
  - `Dockerfile` ở **thư mục gốc** của ZIP (không đặt trong thư mục con); các tệp còn lại tự tổ chức.
  - Ảnh Docker **Linux amd64**, không GPU, chứa sẵn mã nguồn và thư viện; khai báo `ENTRYPOINT` để nhận tham số chấm.
  - Chương trình nhận thư mục `.xlsx` cùng `queries.json` và tạo `submission.csv` đúng hai cột `id,answer`; mỗi `id` đúng một dòng, `answer` chỉ chứa đáp án cuối.
  - Nếu dùng LLM: hỗ trợ `qwen/qwen3.7-flash` qua OpenRouter; khóa API cấu hình bên ngoài mã nguồn; tổng chi phí **≤ 0,10 USD/câu hỏi** kể cả retry.
  - Chạy **tối đa 40 phút cho 20 câu** trên máy **6 vCPU, 12 GB RAM**; tổng dung lượng sử dụng khi chạy **không quá 1 GB** (theo Giải đáp thắc mắc Câu 03: 1 GB là *disk*, RAM tối đa 4 GB).
- **Cam kết khi nộp:** người nộp xác nhận tệp đáp ứng toàn bộ yêu cầu kỹ thuật trên và **không chứa API key, mật khẩu hoặc khóa riêng**. Trước khi nộp cần kiểm tra ZIP bằng `scripts/package_submission.py` (script này loại `.env` và kiểm tra tệp bí mật).

### Checklist ngay trước khi bấm nộp
- [ ] `python scripts/package_submission.py` → `dist/AI26C0062.zip` (đúng tên, `Dockerfile` ở gốc, ≤ 100 MB).
- [ ] Giải nén ZIP vào thư mục trống, `docker build --platform linux/amd64`, chạy với 6 tham số và `scripts/validate_submission.py` báo hợp lệ.
- [ ] Rà lại ZIP không có `.env`, key, `.git`, `output/`, `dist/`, PDF.
- [ ] Kiểm tra thời gian/chi phí/token ở log cuối lượt chạy (hiện: ~40 s cho 30 câu, ~$0,004).


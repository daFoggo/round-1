# ĐỀ THI: CHỦ ĐỀ 2: HỎI ĐÁP TRÊN BẢNG TÍNH EXCEL

---

## 1. Mục tiêu

Xây dựng giải pháp tự động trả lời câu hỏi bằng ngôn ngữ tự nhiên dựa trên dữ liệu trong các tệp Excel. Dữ liệu có thể gồm nhiều trang tính, nhiều bảng trên cùng một trang tính, tiêu đề phân cấp, ô gộp hoặc cấu trúc không đồng nhất. Giải pháp cần xác định đúng thông tin liên quan và đưa ra câu trả lời chính xác.

---

## 2. Dữ liệu được cung cấp

Ban Tổ chức (BTC) cung cấp dữ liệu công khai để các đội phát triển và tự đánh giá giải pháp, gồm:

| Thành phần | Nội dung |
| :--- | :--- |
| `xlsx_files/` | Thư mục chứa các tệp Excel (`.xlsx`). |
| `queries.json` | Danh sách câu hỏi với các trường `id`, `file_name` và `query`. |
| `sample_submission.csv` | Tệp mẫu kết quả gồm hai cột `id` và `answer`. |

*Trong tệp `queries.json`:*
- `id`: Mã câu hỏi.
- `file_name`: Tên tệp Excel tương ứng.
- `query`: Nội dung câu hỏi.

### Ví dụ dữ liệu trong tệp Excel:

| No | Name (First) | Name (Middle) | Name (Last) | Date of Birth | Date of Admission | Score |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: |
| 1 | Ha | Minh | Dang | 2005-01-03 | 2025-02-12 | 92 |
| 2 | An | Gia | Pham | 1995-02-14 | 2024-02-08 | 60 |
| 3 | Minh | Hoang | Nguyen | 2004-02-08 | 2025-01-19 | 92 |
| 4 | Khanh | Van | Pham | 1995-09-28 | 2022-05-14 | 64 |
| 5 | Minh | Thi | Ngo | 1999-09-27 | 2022-02-19 | 91 |
| ... | ... | ... | ... | ... | ... | ... |

*(Bảng có ô gộp ở tiêu đề: cột "Name" gộp 3 cột con First, Middle, Last; cột "Date of" gộp 2 cột con Birth, Admission)*

### Ví dụ dữ liệu câu hỏi trong tệp `queries.json`:

```json
[
  {
    "id": 1,
    "file_name": "sample.xlsx",
    "query": "How many people have a score higher than 80?"
  },
  {
    "id": 2,
    "file_name": "sample.xlsx",
    "query": "What is the last name of the person with the highest score?"
  }
]
```

### Ví dụ kết quả tương ứng trong tệp `submission.csv`:

```csv
id,answer
1,11
2,Ngo
```

> **Lưu ý:** Bài dự thi được đánh giá trên tập kiểm thử ẩn do BTC xây dựng theo quy trình tương tự bộ dữ liệu công khai.

---

## 3. Yêu cầu đối với bài dự thi

- **Đầu vào & đầu ra:** Giải pháp nhận đầu vào là thư mục chứa các tệp `.xlsx` và tệp `queries.json`; kết quả phải được xuất ra tệp `submission.csv` đúng định dạng mẫu.
- **Quy cách câu trả lời:** Mỗi `id` trong `queries.json` tương ứng với đúng một dòng kết quả. Trường `answer` **chỉ ghi đáp án cuối cùng, không kèm giải thích**.
- **Đóng gói nộp bài:** Mỗi đội nộp một tệp `.zip` gồm mã nguồn, các tệp cấu hình/phụ thuộc cần thiết và tệp `README.md` hướng dẫn cài đặt, cấu hình, chạy chương trình bằng dòng lệnh.
- **Khả năng tổng quát hóa:** Giải pháp phải có khả năng chạy lại với dữ liệu đầu vào mới, không phụ thuộc vào đường dẫn của bộ dữ liệu mẫu. Bài không chạy được hoặc không tạo ra tệp kết quả hợp lệ sẽ không được chấm.

---

## 4. Giới hạn tài nguyên và điều kiện thực thi

- **Mô hình ngôn ngữ (LLM):** 
  - Nếu sử dụng LLM để trả lời câu hỏi, giải pháp phải hỗ trợ mô hình thống nhất khi chấm thi là **Qwen3.7 Flash** (model ID: `qwen/qwen3.7-flash`), truy cập qua **OpenRouter** (`https://openrouter.ai/qwen/qwen3.7-flash`).
  - Đội thi phải cho phép cấu hình thông tin truy cập API và **không đưa khóa API vào mã nguồn**.
  - Quy định này không hạn chế việc sử dụng công cụ AI trong quá trình phát triển giải pháp.
- **Chi phí LLM:** Tổng chi phí gọi LLM trên tập kiểm thử ẩn **không vượt quá 0.10 USD/câu hỏi** cho mỗi lần chấm, tính cả các lượt gọi lại (retry). Chi phí được xác định theo mức sử dụng API do BTC ghi nhận.
- **Thời gian thực thi:** **Tối đa 40 phút cho 20 câu hỏi**, tính từ lúc bắt đầu chạy giải pháp đến khi tạo xong tệp `submission.csv`, bao gồm thời gian xử lý dữ liệu và gọi API. 
  - Máy chấm thi của BTC có cấu hình: **6 core vCPU, 12 GB RAM**.
- **Dung lượng và bộ nhớ:** 
  - Tệp `.zip` nộp bài không được vượt quá **100 MB**.
  - Trong quá trình chạy trên tập kiểm thử ẩn, tổng dung lượng giải pháp sử dụng **không được vượt quá 1 GB**.
    - ✅ *Làm rõ theo Giải đáp thắc mắc (Câu hỏi 03): **1 GB là dung lượng đĩa (disk)**; **RAM tối đa là 4 GB**.*

> ⚠️ **Lưu ý quan trọng:** Bài dự thi vi phạm một trong các giới hạn nêu trên sẽ **không được chấm điểm**.

### Làm rõ từ Giải đáp thắc mắc của BTC (xem [`GIAI_DAP_THAC_MAC.md`](GIAI_DAP_THAC_MAC.md))

| Nội dung | Quy định |
| :--- | :--- |
| Bộ nhớ | Disk **1 GB**, RAM tối đa **4 GB** |
| `id` | Thống nhất là **số tự nhiên** ở cả `queries.json` và `submission.csv` |
| Thứ tự dòng / câu không trả lời | `submission.csv` UTF-8, **sắp xếp theo `id` tăng dần**; không trả lời được → **chuỗi rỗng** |
| Dữ liệu tập ẩn | Chỉ `.xlsx`, **có thể nhiều sheet**, **có thể nhiều ngôn ngữ** |
| Chuẩn hóa khi chấm | BTC bỏ khoảng trắng thừa/dấu không cần thiết, đưa về chữ thường, chuẩn hóa dấu thập phân; câu hỏi luôn nêu rõ format đáp án |
| Quy ước "average across all …" | Không chỉ định cấp (như "excluding totals") → trung bình **trên tất cả cột có mặt trong dòng**, kể cả cột Total |
| Token | Tính bằng **input + reasoning** |
| Internet | Chỉ khi cài đặt (build Docker) và khi gọi OpenRouter; thời gian build không tính vào 40 phút |
| Xử lý song song | Được phép |

---

## 5. Chấm điểm và xếp hạng

BTC chạy các bài dự thi hợp lệ trên tập kiểm thử ẩn. Thứ tự xếp hạng được xác định theo các tiêu chí ưu tiên sau:

1. **Số câu trả lời đúng theo so khớp chính xác với đáp án chuẩn (Exact Match):** Đội có nhiều câu trả lời đúng hơn được xếp trước.
2. **Thời gian thực thi trung bình mỗi câu hỏi:** Đội có thời gian thấp hơn được xếp trước nếu số câu trả lời đúng bằng nhau.
3. **Số token LLM sử dụng trung bình mỗi câu hỏi:** Đội dùng ít token hơn được xếp trước nếu hai tiêu chí trên bằng nhau.

---

## 6. Vấn đáp và xác minh

Phần vấn đáp nhằm xác minh mức độ làm chủ giải pháp của đội thi:
- Các đội phải giải thích được nguyên lý hoạt động, các thành phần chính.
- Chứng minh khả năng điều chỉnh mã nguồn theo yêu cầu phù hợp với phạm vi đề thi.
- Đội không đáp ứng yêu cầu xác minh sẽ **bị loại khỏi bảng xếp hạng chính thức**.

# GIẢI ĐÁP THẮC MẮC CỦA ĐỘI THI

> Chuyển thể từ `AI2026_Giải đáp thắc mắc Vòng khu vực bảng C.pdf` – Cuộc thi Sáng tạo trẻ Quốc gia về AI năm 2026 | Vòng Khu vực – Bảng C.
> Phần "Tác động lên bài làm" ở cuối là ghi chú của đội, không thuộc văn bản gốc.

---

## Câu hỏi 01 – Quy ước tính trung bình ("across all …")

**Hỏi:** Câu `p4_q007` đáp án mẫu ra 3.14. Nếu theo như cách tính này thì BTC đang cộng cả 2 cột Total của *Some college or associate degree* và *Bachelor's degree and higher* vào rồi chia trung bình 8?

**Trả lời:** Đáp án mẫu 3.14 được tính bằng trung bình cộng số học (*unweighted mean*) trên toàn bộ **8 cột** dữ liệu thuộc dòng *Unemployment rate* của nhóm *Women*. Quy ước chung cho các câu hỏi tương tự trong cuộc thi:

> Khi câu hỏi yêu cầu tính giá trị trung bình (average) trên toàn bộ các cột thuộc một tiêu chí trong bảng ("across all...") mà **không chỉ định rõ cấp độ phân nhóm** (như "subcategories only" hay "excluding totals"), hệ thống đánh giá chuẩn (theo quy ước của bộ dữ liệu gốc) sẽ thực hiện phép tính **trực tiếp trên tất cả các cột dữ liệu có mặt trong phạm vi dòng đó**. Các đội thi lưu ý quy ước này để đồng bộ logic xử lý cho pipeline của mình.

## Câu hỏi 02 – Nội dung vấn đáp

**Hỏi:** Trong buổi vấn đáp, Hội đồng giám khảo sẽ hỏi thêm nội dung sản phẩm vòng loại hay chỉ tập trung vào bài toán của Vòng Khu vực?

**Trả lời:** BGK tập trung vào bài toán của vòng khu vực; nội dung vòng loại sẽ được hỏi trong vòng Chung kết (nếu sản phẩm vào Chung kết).

## Câu hỏi 03 – Giới hạn 1 GB

**Hỏi:** Đề bài: chạy tối đa 40 phút cho 20 câu trên máy 6 vCPU, 12 GB RAM; tổng dung lượng sử dụng khi chạy không quá 1 GB. 1 GB này là tổng RAM hệ thống tiêu thụ đúng không?

**Trả lời:** Tổng dung lượng bộ nhớ (**disk**) là **1 GB**, tổng **RAM tối đa là 4 GB**.

## Câu hỏi 04 – Định dạng dữ liệu và kết quả

**Hỏi:**
1. Khi chấm Exact Match, BTC có chuẩn hóa đáp án trước khi so sánh không (bỏ khoảng trắng thừa, không phân biệt hoa thường, coi `11` và `11.0` là như nhau)?
2. Ví dụ `queries.json` trong đề dùng `"file name"` và id số (1, 2), còn bộ công khai dùng `"file_name"` và id chuỗi (`"p4_q001"`). Tập ẩn dùng định dạng nào?
3. Thư mục dữ liệu của tập ẩn có cùng cấu trúc với bộ công khai không? Có thể có file `.xls`/`.csv`, nhiều sheet, câu hỏi tiếng Việt không?
4. `submission.csv` có yêu cầu riêng về encoding (có/không BOM) và thứ tự dòng không? Câu không trả lời được để trống có hợp lệ không?

**Trả lời:**
1. BTC có chuẩn hóa kết quả:
   - Loại bỏ khoảng trắng thừa, các dấu không cần thiết (gạch ngang, ngoặc, nháy, …).
   - Chuẩn hóa tất cả đáp án về chữ thường, chuẩn hóa dấu chấm/phẩy cho phần thập phân, …
   - Các câu hỏi sẽ nêu rõ yêu cầu format đáp án (cụm cần in ra, yêu cầu làm tròn), để thí sinh không bị thiệt khi đáp án đúng về ngữ nghĩa.
2. BTC sẽ cung cấp **template** cụ thể về cách chạy, cách đọc dữ liệu. Các đội đưa đúng đường dẫn thư mục/tệp. **`id` của `submission.csv` và `queries.json` sẽ được thống nhất thành dạng số tự nhiên.**
3. Tập kiểm thử theo đúng định dạng của tập công khai. Các file **chỉ có định dạng `.xlsx`**, **có thể có nhiều sheet**, và **có thể ở các ngôn ngữ khác nhau**.
4. `submission.csv` dùng **UTF-8**, **thứ tự dòng theo `id` tăng dần**. Nếu không trả lời được, **để chuỗi rỗng**.

## Câu hỏi 05 – Môi trường chạy

**Hỏi:**
1. Máy chấm dùng hệ điều hành / phiên bản Python nào? Có được `pip install` từ Internet không, thời gian cài có tính vào 40 phút không?
2. BTC chạy theo lệnh trong README, hay có mẫu lệnh, tên file / tên tham số bắt buộc?
3. OpenRouter API key được cung cấp qua biến môi trường tên gì? Đội có được tự đặt tên biến không?
4. Có được gửi song song nhiều request tới API không? Có giới hạn tần suất không? Có được đóng gói bằng Docker không?

**Trả lời:**
- BTC cung cấp **template yêu cầu nộp bài**. Các đội được phép xử lý song song hay bất kỳ cách nào, miễn giải pháp chạy được trong môi trường và tài nguyên được cung cấp.
- **Thời gian build Docker** (tải, cài đặt, …) **không tính** vào thời gian chạy chính thức.
- Chỉ được dùng Internet trong quá trình **install** và **request đến OpenRouter API**.

## Câu hỏi 06 – Cách tính điểm

**Hỏi:** "Số token LLM trung bình" có tính cả token input và reasoning không? Thời gian thực thi trung bình đo trên toàn chương trình rồi chia số câu, hay đo từng câu?

**Trả lời:** Số token được tính là **tổng của input và reasoning**. *(Văn bản gốc không trả lời phần thời gian thực thi.)*

## Câu hỏi 07 – Công cụ AI

**Hỏi:** BTC có quy định/giới hạn về công cụ AI được dùng để làm bài không?

**Trả lời:** Được dùng bất cứ công cụ nào khi **phát triển**; tuy nhiên **giải pháp cuối chỉ được dùng AI/LLM do BTC cung cấp**.

---

## Tác động lên bài làm (ghi chú của đội)

| # | Nội dung BTC xác nhận | Hiện trạng codebase | Cần làm |
|---|---|---|---|
| 1 | "across all" không chỉ định cấp → **trung bình trên mọi cột** có mặt, kể cả cột Total (`p4_q007` = 3.14 là **đúng quy ước**) | Model lấy 6 cột lá → 3.35 | Cài quy ước này (xem lưu ý bên dưới) |
| 3 | **Disk 1 GB, RAM tối đa 4 GB** (không phải RAM 1 GB) | Trước đây thử với `--memory 1g`, hiểu nhầm giới hạn | ✅ Đã đổi docker-compose, `DE_THI.md`, checklist sang RAM 4 GB / disk 1 GB |
| 4.1 | BTC chuẩn hóa chữ thường, khoảng trắng, dấu, dấu thập phân | `formatter.py` giữ nguyên hoa/thường | Không cần sửa, vẫn nên xuất đúng format đề yêu cầu |
| 4.2 | `id` thống nhất **số tự nhiên** | CLI nhận `id` bất kỳ; `schemas.QueryItem.id: str` | Cho `id` nhận int/str (API) |
| 4.3 | Chỉ `.xlsx`, **nhiều sheet**, **nhiều ngôn ngữ** | Đã hỗ trợ nhiều sheet; prompt viết tiếng Anh | Kiểm thử thêm với file/câu hỏi không phải tiếng Anh |
| 4.4 | UTF-8, **sắp xếp theo `id` tăng dần**, không trả lời được → chuỗi rỗng | Giữ nguyên thứ tự trong `queries.json`; rỗng khi lỗi | Sắp xếp theo `id` khi ghi CSV |
| 5 | Có **template** nộp bài riêng; Internet chỉ khi install và gọi OpenRouter; cho phép **song song** | Chạy tuần tự | Đối chiếu template khi BTC gửi; cân nhắc gọi song song để giảm thời gian |
| 6 | Token = **input + reasoning** | Đếm `total_tokens` | Giữ prompt ngắn; xem xét tắt/giảm reasoning của Qwen |
| 7 | Chỉ dùng LLM do BTC cung cấp | Đã dùng OpenRouter Qwen | ✅ Đã gỡ hoàn toàn code Gemini, chỉ còn OpenRouter/Qwen |

# Kiểm số và AC bằng verify_facts

Router và Worker có cùng công cụ Python chỉ đọc `verify_facts`; không cần Docker, không gọi LLM, mạng hoặc shell. Công cụ không đọc file trên máy chủ, không nhận biểu thức Python và không cấp quyền publish.

## Khi phải gọi

Trước khi báo số từ/ký tự/tổng tự tính hoặc nói bản bàn giao đạt AC, gửi bản cuối vào công cụ. Thay đổi bản nháp sau kiểm thì phải kiểm lại. Câu trả lời một bước không có claim số lượng/PASS không cần thêm quy trình.

- `draft`: artifact nguyên văn, chưa thêm ghi chú kết quả kiểm.
- `texts`: từng đoạn có id/text; hỗ trợ min_words/max_words/min_chars/max_chars và claimed_words/claimed_chars. Đếm blog chỉ dùng thân bài, bỏ H1, SEO và tóm tắt.
- `sums`: id, values, claimed_total tùy chọn. Decimal tính tổng, không dùng float hoặc eval. Giá trị số phải canonical, như 650000 và 0.5; không dùng chuỗi có dấu phân nhóm/exponent/NaN.
- `number_checks`: id, expected, actual, source_quote, draft_quote. Truyền `source` là dữ liệu đã được cung cấp. Quote phải tồn tại nguyên văn trong source/draft và chứa giá trị số tương ứng; thiếu grounding thì NOT_CHECKED. Sai giá trị thì FAIL.
- `number_format`, hoặc `source_number_format`/`draft_number_format`: en cho 650,000.5; vi cho 650.000,5. Chỉ tác động cách đọc số trong quote, không thay quy tắc số canonical ở JSON.
- `checklist`: id + check_ids tham chiếu các phép kiểm atomic trong cùng call. PASS chỉ khi tất cả ref PASS; ref thiếu/rỗng/chưa kiểm trả NOT_CHECKED; bất kỳ ref FAIL thì AC FAIL. Không nhận trường status tự khai làm bằng chứng.

`words` là số token từ `str.split()` theo khoảng trắng, cùng quy ước cho VI/EN. Đây không phải bộ tách từ ngôn ngữ học tiếng Việt. `chars` đếm Unicode code points, không phải bytes hoặc grapheme; không normalize hay sửa input. `chars_without_whitespace` bỏ ký tự khoảng trắng. SHA-256 gắn kết quả với đúng text/draft.

Ví dụ bắt lỗi cũ:

```json
{"sums":[{"id":"rubric","values":[2,0,1,2,2],"claimed_total":4}],"checklist":[{"id":"runtime","check_ids":[]}]}
```

Kết quả có total đúng từ phép cộng, sum FAIL, runtime NOT_CHECKED. Không đổi các điểm thành phần chỉ để tăng tổng.

## Giới hạn bằng chứng

Công cụ kiểm **input được truyền vào**, không xác thực nguồn bên ngoài hoặc đảm bảo mô hình đã truyền đủ mọi số/AC. So số và quote không hiểu entity, đơn vị, kỳ thống kê hay mệnh đề phủ định. `numeric_inventory` liệt kê số trong draft không thấy trong source, chỉ để rà soát; số cấu trúc/derived có thể hợp lệ, không tự gây FAIL.

PASS phép đếm không có nghĩa prose đúng sự thật. PASS tổng Rubric không chứng minh test đã chạy. AC cần pytest/render/engine/bites phải có kết quả thực thi riêng, nếu chưa có thì NOT_CHECKED. Việc buộc gọi hiện là instruction trong prompt/mentor, chưa phải bộ chặn cứng mọi câu trả lời tự do.

Giới hạn: mỗi nhóm tối đa 50 mục; mỗi text tối đa 100.000 code points; mỗi sum tối đa 100 số. Kết quả tool quá 7.500 ký tự trả lỗi yêu cầu chia batch, không cắt JSON giữa chừng hoặc báo PASS giả. Test unit và Router→Worker integration dùng fixture tự tạo/FakeLLM, không phát sinh phí.

`diffs` nhận id/text unified diff nguyên văn, đếm context/deletion/addition từng hunk và so với header. Không apply/test hoặc xác nhận context nguồn. `calculation_status=COMPLETE` vẫn đúng khi một assertion FAIL: dùng số đã tính để sửa draft, không coi total đúng là NOT_CHECKED. Regex phân nhóm en/vi chỉ nhận nhóm ba chữ số, tránh nuốt cột CSV vào cùng một số.

## Mode markdown_body

`texts[].mode` có plain (mặc định, giữ tương thích) và markdown_body. Với markdown_body, gửi nguyên phần bài viết có H1/H2; tool bỏ YAML front matter ở đầu, dòng ATX heading Markdown #-lines, fenced code (backtick/tilde) và code thụt bốn spaces/tab. Inline code vẫn là prose. Không tự tính setext/HTML là heading; scope này đúng yêu cầu #-lines. Loại SEO/tóm tắt/ghi chú khỏi blog text trước khi gọi, không xóa heading bằng tay.

Words và chars tính trên body đã lọc; input_chars và SHA-256 vẫn gắn input gốc. Front matter chưa đóng trả NOT_CHECKED, không coi toàn tài liệu là rỗng và PASS. Chọn mode rõ ràng, copy số trả về và kiểm lại nếu sửa. Patch thật cần [inspect/check trong sandbox](local-patch-checks.md), không dùng kết quả đếm hunk làm bằng chứng apply/test.

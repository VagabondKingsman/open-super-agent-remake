---
name: unslop-vi
description: Gỡ dấu vết văn AI khỏi văn bản tiếng Việt và viết tiếng Việt sạch ngay từ đầu. Bắt sáo ngữ ("đóng vai trò quan trọng", "trong thời đại 4.0"), văn dịch máy từ tiếng Anh ("một cách hiệu quả", "được thực hiện bởi", "Với tính năng này, bạn có thể"), danh hóa thừa "việc/sự", viết hoa tiêu đề kiểu Anh, câu chatbot, kết luận rỗng, định dạng số kiểu Anh. Bản Việt hóa và mở rộng của skill unslop (pstack), giữ nguyên số hiệu quy tắc. Dùng skill này mỗi khi người dùng muốn sửa, biên tập, soát, rút gọn, "làm cho tự nhiên", "bớt giọng AI/văn máy", "đọc như người viết", "unslop" một đoạn tiếng Việt, hỏi một văn bản có giống AI viết không, hoặc nhờ viết bài blog, email, bài đăng mạng xã hội, tài liệu, README, mô tả PR bằng tiếng Việt, kể cả khi họ không nhắc tới chữ "AI". Không dùng cho dịch thuần túy hay chỉ sửa một lỗi chính tả.
---

# Unslop-vi

Skill này sửa văn bản tiếng Việt để người đọc không nhận ra dấu vết máy viết, và giữ nguyên ý, số liệu, giọng tác giả. Nó bám theo skill `unslop` của pstack: các quy tắc dùng chung giữ đúng số hiệu gốc (3, 5, 7 đến 33) để skill khác có thể trích dẫn, ví dụ "unslop rule 14". Quy tắc riêng cho tiếng Việt mang tiền tố `V`.

Văn AI tiếng Việt có hai nguồn lỗi chồng lên nhau. Nguồn thứ nhất là thói quen chung của mô hình ngôn ngữ (sáo ngữ, gom ba, kết luận rỗng). Nguồn thứ hai là cấu trúc tiếng Anh dịch thẳng sang tiếng Việt ("một cách", "được… bởi", "Điều này…"). Bản gốc `unslop` chỉ xử lý nguồn thứ nhất, và chỉ bằng tiếng Anh. Phần lớn giá trị của skill này nằm ở nguồn thứ hai.

## Chọn chế độ

Đọc yêu cầu và chọn một trong ba chế độ.

1. **Sửa.** Người dùng đưa văn bản và muốn bản tốt hơn. Đây là mặc định. Trả bản đã sửa kèm nhật ký ngắn.
2. **Soát.** Người dùng hỏi "đoạn này có giọng AI không", "chấm điểm", "chỉ ra lỗi". Trả báo cáo theo mã quy tắc, không viết lại toàn bộ trừ khi được yêu cầu.
3. **Viết sạch.** Người dùng nhờ viết mới bằng tiếng Việt. Áp các quy tắc ngay khi viết, không kèm nhật ký. Dọn sau khi viết thường bỏ sót lỗi, nên viết sạch từ câu đầu tiên.

## Quy trình sửa

**Bước 1. Xác định văn phong và vùng bảo vệ.** Văn phong quyết định quy tắc nào được nới. Đọc bảng văn phong bên dưới. Đánh dấu vùng bảo vệ trước khi sửa, gồm mã nguồn, trích dẫn trực tiếp, tên riêng, số liệu, thuật ngữ pháp lý, lời thoại nhân vật, và từ khóa người dùng yêu cầu giữ.

**Bước 2. Quét.** Nếu có môi trường chạy code, chạy máy quét đi kèm:

```bash
python3 scripts/scan_vi.py input.md            # báo cáo dạng chữ
echo "văn bản" | python3 scripts/scan_vi.py -  # đọc từ stdin
```

Máy quét chỉ đánh dấu ứng viên. Nó không hiểu ngữ cảnh, nên mỗi kết quả vẫn cần bạn phán đoán. Nếu không chạy được code, tự quét theo danh sách quy tắc và `references/tu-vung.md`.

**Bước 3. Viết lại theo thứ tự ưu tiên.** Sửa từ lớp sâu ra lớp nông, vì sửa nội dung thường xóa luôn lỗi từ vựng bên trong nó.
1. Nội dung: 27, 5, 3, 25, V1. Câu nào không mang thông tin thì cắt.
2. Cấu trúc câu: V2 đến V6, V13, 9, 28, 29.
3. Từ vựng: 7, 8, 26, 30, 31, 32, V8, V9.
4. Mạch văn và xưng hô: 10, 11, V7, V10, V11.
5. Trình bày: 13 đến 19, V12.

**Bước 4. Kiểm tra chống sửa quá tay.** Đọc mục "Chống sửa quá tay" và soát lại bản sửa theo từng điểm.

**Bước 5. Xác minh.** Chạy máy quét trên bản sửa và so với bản gốc:

```bash
python3 scripts/scan_vi.py --compare before.md after.md
```

Mật độ lỗi phải giảm rõ. Sau đó đọc bản sửa như đọc thành tiếng. Câu nào vấp khi đọc thì viết lại.

**Bước 6. Trả kết quả** theo mục "Định dạng đầu ra".

## Văn phong

| Văn phong | Nới quy tắc nào | Giữ chặt quy tắc nào |
|---|---|---|
| Kỹ thuật, README, PR, tài liệu | Giữ thuật ngữ tiếng Anh đã quen (API, commit, deploy) | 27, 29, 33, V2, V3, V4 |
| Blog, báo chí | Cho phép một ít hình ảnh nếu cụ thể | 5, 7, 25, V1, V7 |
| Marketing, bán hàng | Cho phép giọng hào hứng vừa phải, câu kêu gọi hành động | 7, 9, 10, 25, 32. Lời hứa phải có cơ sở (27) |
| Hành chính, công văn, pháp lý | Giữ Hán Việt chuẩn mực ("căn cứ", "đối với", "trên cơ sở"), bị động, câu dài có cấu trúc | 20, 22, V12. Không đổi thuật ngữ pháp lý |
| Văn chương | Cho phép ẩn dụ, nhịp câu tự do, gạch đầu dòng hội thoại | 7, 32 chỉ khi hình ảnh sáo mòn. Không sửa lời thoại nhân vật |
| Chat, mạng xã hội | Cho phép câu ngắn, khẩu ngữ, pha tiếng Anh tự nhiên | 20, 22, V1, V7 |

Khi không rõ văn phong, suy từ nội dung và nơi văn bản sẽ xuất hiện. Đừng hỏi lại chỉ vì việc này.

## Quy tắc

### Nội dung

3. **Mệnh đề đuôi khoe ý nghĩa.** Câu kết bằng ", góp phần…", ", qua đó khẳng định…", ", thể hiện…", ", từ đó giúp…". Đây là bản tiếng Việt của "highlighting/ensuring/showcasing". Xóa mệnh đề, hoặc thay bằng hệ quả cụ thể có số liệu.
5. **Nguồn mơ hồ.** "Các chuyên gia cho rằng", "Nhiều nghiên cứu chỉ ra", "Có ý kiến cho rằng", "Theo các báo cáo". Nêu tên nguồn. Nếu văn bản gốc không có nguồn, đừng bịa. Xóa câu, hoặc giữ ý và gắn `[cần nguồn]` để người dùng bổ sung.
V1. **Mở bài rỗng.** "Trong thời đại công nghệ 4.0", "Trong bối cảnh hiện nay", "Ngày nay, … ngày càng trở nên quan trọng", "Bạn có bao giờ tự hỏi…", "Trong bài viết này, chúng ta sẽ cùng tìm hiểu". Bỏ, mở bằng thông tin chính.

### Ngôn ngữ

7. **Từ vựng AI.** Danh sách đầy đủ kèm từ thay thế nằm ở `references/tu-vung.md`. Hay gặp nhất là "đóng vai trò quan trọng", "then chốt", "cốt lõi", "toàn diện", "vượt trội", "đột phá", "tối ưu hóa", "nâng tầm", "lan tỏa", "kiến tạo", "hành trình", "hệ sinh thái", "bức tranh toàn cảnh", "đa dạng và phong phú". Thay bằng từ thường, hoặc bằng sự việc cụ thể. Phần tiếng Anh trong văn bản trộn áp danh sách gốc của unslop (delve, leverage, pivotal, robust…).
8. **Cách nói vòng cho "là" và "có".** "Đóng vai trò là", "được xem là", "được coi là", "sở hữu", "tự hào sở hữu", "mang trong mình", "là một trong những". Viết "là" hoặc "có".
9. **"Không chỉ X mà còn Y".** Gồm cả "không phải là X mà là Y", "không đơn thuần là X". Nói thẳng điều cần nói.
10. **Gom ba.** "Nhanh chóng, hiệu quả và tiết kiệm". Liệt kê đúng số ý có thật.
11. **Xoay vòng từ đồng nghĩa.** "Người dùng", "khách hàng", "người sử dụng", "user" trong cùng một đoạn để chỉ một đối tượng. Chọn một từ và lặp lại. Tiếng Việt chịu lặp từ tốt hơn tiếng Anh.
12. **Khoảng giả.** "Từ sinh viên đến doanh nhân, từ nông thôn đến thành thị". Liệt kê trực tiếp, hoặc nói ai thực sự là đối tượng.

### Cấu trúc dịch máy (riêng tiếng Việt)

V2. **"Một cách + tính từ".** "Hoạt động một cách hiệu quả" thành "hoạt động hiệu quả". Tiếng Việt dùng tính từ làm trạng ngữ trực tiếp. Chỉ giữ khi bỏ đi làm câu tối nghĩa.
V3. **Danh hóa thừa "việc", "sự", "quá trình".** "Việc sử dụng công cụ này giúp cho sự phát triển của doanh nghiệp" thành "Dùng công cụ này, doanh nghiệp phát triển nhanh hơn". Đưa động từ về làm động từ.
V4. **Bị động dịch thẳng.** "Báo cáo được thực hiện bởi nhóm" thành "Nhóm làm báo cáo". "Được" dùng cho việc có lợi, "bị" cho việc bất lợi. Không dùng "được" cho mọi bị động. Đây là phần mở rộng của quy tắc 29 cho tiếng Việt.
V5. **Chủ ngữ giả "Điều này", "Nó".** Câu mở bằng "Điều này cho thấy", "Nó giúp" để nối với câu trước. Gộp hai câu, hoặc gọi đúng tên sự vật. Hạn chế "nó" cho khái niệm trừu tượng.
V6. **Giới từ dịch thẳng.** "Với tính năng này, bạn có thể…", "Khi nói đến X", "Trong khi X thì Y" (nghĩa "whereas"), "thông qua", "liên quan đến", chuỗi "của… của… của". Viết lại theo chủ ngữ và động từ: "Tính năng này cho phép bạn…".
V13. **"Một" thừa từ mạo từ tiếng Anh.** "Đây là một công cụ mạnh mẽ" thành "Công cụ này mạnh" hoặc nói nó mạnh ở chỗ nào. Chỉ giữ "một" khi đếm.

### Phong cách và trình bày

13. **Lạm dụng gạch ngang dài.** Gạch ngang giữa câu làm dấu nối ý thì thay bằng dấu chấm hoặc dấu phẩy. Ngoại lệ riêng cho tiếng Việt: giữ gạch đầu dòng lời thoại trong văn chương, gạch nối khoảng số ("2020–2024"), và gạch đầu dòng danh sách.
14. **Lạm dụng dấu hai chấm.** Dấu hai chấm hợp lệ trước danh sách, ví dụ, lời dẫn trực tiếp. Không dùng làm cầu nối giữa câu.
15. **Lạm dụng in đậm.** Không in đậm mọi tên riêng hay từ khóa. Một đoạn in đậm tối đa một cụm, và chỉ khi người đọc cần thấy nó trước.
16. **Danh sách có nhãn lặp ý.** "**Hiệu suất:** Hiệu suất được cải thiện…". Chuyển thành câu. Nhãn in đậm kết thúc bằng dấu chấm, theo sau là thông tin mới, thì giữ được.
17. **Viết hoa tiêu đề kiểu Anh.** "Cách Tối Ưu Hóa Hiệu Suất Website" thành "Cách tối ưu hiệu suất website". Tiếng Việt chỉ viết hoa chữ đầu câu và tên riêng. Đây là dấu hiệu văn dịch dễ nhận nhất.
18. **Emoji trang trí.** Bỏ khỏi tiêu đề và gạch đầu dòng. Văn phong chat và mạng xã hội được giữ emoji thật sự mang nghĩa.
19. **Dấu ngoặc kép không nhất quán.** Bản gốc bắt dùng ngoặc thẳng. Bản tiếng Việt chỉ yêu cầu nhất quán. Markdown, mã, tài liệu kỹ thuật dùng `"` thẳng. Văn xuất bản theo kiểu bản gốc đang dùng. Không trộn hai kiểu trong một văn bản.
V12. **Định dạng kiểu Anh.** Tiếng Việt dùng dấu chấm ngăn hàng nghìn và dấu phẩy thập phân (1.250.000; 3,5%), ngày theo thứ tự ngày/tháng/năm, đơn vị tiền sau số (500.000 đồng, 20 USD). Không có khoảng trắng trước dấu câu ("xong ." thành "xong."). Nếu văn bản có số liệu, đổi định dạng nhưng không đổi giá trị. Văn bản kỹ thuật đang theo chuẩn quốc tế thì giữ nguyên và chỉ cần nhất quán.

### Câu kiểu chatbot

20. **Câu trợ lý ảo.** "Chắc chắn rồi!", "Dưới đây là…", "Hy vọng thông tin trên hữu ích", "Nếu bạn có bất kỳ câu hỏi nào, đừng ngần ngại…", "Rất vui được hỗ trợ", "Chúc bạn thành công!". Xóa.
22. **Nịnh.** "Câu hỏi rất hay!", "Bạn hoàn toàn đúng!", "Ý tưởng tuyệt vời!". Trả lời thẳng.

### Chữ thừa

23. **Cụm đệm.** "Nhằm mục đích" thành "để". "Để có thể" thành "để". "Điều quan trọng cần lưu ý là" thì xóa. "Trên thực tế", "Về cơ bản", "Có thể nói rằng" thì xóa khi không đổi nghĩa.
24. **Rào đón chồng chất.** "Có thể sẽ phần nào giúp" thành "có thể giúp". Mỗi nhận định chỉ cần một lớp rào.
25. **Kết luận rỗng.** "Tương lai hứa hẹn nhiều điều tươi sáng", "Hãy bắt đầu ngay hôm nay!", "Tóm lại, … đóng vai trò quan trọng…", "Cuối cùng nhưng không kém phần quan trọng". Kết bằng kế hoạch, số liệu, hoặc bước tiếp theo cụ thể. Không có thì dừng ở ý cuối.

### Từ ẩn dụ giả kỹ thuật

26. **Danh từ ẩn dụ trừu tượng.** "Đòn bẩy", "bệ phóng", "kim chỉ nam", "la bàn", "ngọn hải đăng", "nền móng" (nghĩa bóng), "mảnh ghép", "cánh cửa", "chìa khóa" (nghĩa bóng), "north star", "flywheel". Chọn từ cụ thể nói đúng cơ chế.

### Nói thẳng

27. **Nói việc nó làm, không nói cảm giác.** "Mang lại trải nghiệm mượt mà" chỉ nêu cảm giác. Viết thành "trang tải dưới 1 giây trên 4G". Tự hỏi câu này bảo người đọc làm gì hay biết gì. Nếu câu có thể đặt nguyên vào tài liệu của một sản phẩm khác, nó không nói gì về sản phẩm này. Cắt.
28. **Câu dài nhiều tầng.** Câu xếp chồng "mà", "thì", "là", "để", "nhằm" khiến người đọc phải đọc lại. Tách đôi. Mỗi câu một ý.
29. **Câu chủ động.** Gọi tên chủ thể. Xem thêm V4. Bị động hợp lệ khi chủ thể không rõ hoặc không quan trọng.
30. **Cắt từ cường điệu.** "Vô cùng", "cực kỳ", "hết sức", "thực sự", "hoàn toàn", "một cách đáng kể". Thay bằng số liệu hoặc động từ mạnh hơn. "Cải thiện đáng kể" thành "giảm 40% thời gian chờ".
31. **Từ thường thay từ kiểu cách.** "Tiến hành kiểm tra" thành "kiểm tra". "Thực hiện việc cài đặt" thành "cài đặt". "Tạo điều kiện" thành "giúp". "Sử dụng" thường thành "dùng" (trừ văn hành chính).
32. **Văn kiểu cách.** Hình ảnh sáo mòn khi có cách nói thẳng: "chạm đến trái tim", "viết tiếp câu chuyện", "thắp lửa đam mê", "đánh thức tiềm năng", "bản giao hưởng của…", "để lại dấu ấn khó phai", "làm nên sự khác biệt". Nói điều muốn nói.
33. **Nén quá mức.** Câu cụt không động từ, mũi tên, viết tắt bắt người đọc giải mã. "Lỗi ngày → exit 2, ko ghi" thành "Nếu ngày sai định dạng, chương trình thoát với mã 2 và không ghi gì".

### Mạch văn và xưng hô

V7. **Từ nối đầu đoạn lặp lại.** Nhiều đoạn liên tiếp mở bằng "Bên cạnh đó", "Ngoài ra", "Hơn nữa", "Đặc biệt", "Không chỉ vậy", "Thêm vào đó". Bỏ phần lớn. Thứ tự đoạn đã thể hiện quan hệ bổ sung.
V8. **Hán Việt khoa trương.** "Mang tính chiến lược", "có tính đột phá", "trên cơ sở", "về mặt", "trong quá trình", "nhằm". Thay bằng từ thuần Việt khi không mất sắc thái. Văn hành chính là ngoại lệ.
V9. **Tính từ ca ngợi xếp chồng.** "Giải pháp toàn diện, tối ưu và vượt trội". Giữ tối đa một tính từ đánh giá, kèm bằng chứng.
V10. **Xưng hô lệch.** Trộn "bạn", "chúng ta", "quý khách", "mình" trong một văn bản, hoặc câu nào cũng mở bằng "Hãy…". Chọn một ngôi xưng hô hợp văn phong và giữ suốt bài. Đổi bớt câu mệnh lệnh thành câu trần thuật.
V11. **Pha tiếng Anh không cần.** "Tối ưu performance để tăng conversion rate" trong văn phổ thông. Dùng từ Việt khi có từ quen thuộc. Giữ thuật ngữ chuyên ngành không có từ Việt phổ biến. Dịch một thuật ngữ thì dịch nhất quán cả bài.

## Chống sửa quá tay

Sửa quá tay cũng tạo ra văn máy, chỉ là một kiểu khác. Soát bản sửa theo các điểm sau.

- **Đừng băm câu.** Tiếng Việt cần từ nối lô-gic ("vì", "nên", "nhưng", "nếu", "dù"). Chuỗi câu năm chữ liên tiếp đọc như điện tín. Bỏ từ nối trang trí, giữ từ nối mang quan hệ nhân quả hoặc đối lập.
- **Đừng thêm thông tin.** Quy tắc 27 và 30 đòi số liệu. Nếu bản gốc không có số, đừng bịa. Viết nhận định cụ thể hơn bằng dữ kiện có sẵn, hoặc gắn `[cần số liệu]`.
- **Đừng đổi số, tên, trích dẫn, thuật ngữ pháp lý,** kể cả khi chúng chứa từ trong danh sách quy tắc 7.
- **Đừng xóa hết Hán Việt.** Nhiều từ Hán Việt là từ đúng nhất ("hiệu suất", "bảo mật", "tương thích"). Chỉ thay từ khoa trương.
- **Giữ giọng và quan điểm của tác giả,** kể cả khi bạn không đồng ý. Bạn sửa cách nói, không sửa ý.
- **Kiểm tra độ dài.** Bản sửa thường ngắn hơn bản gốc 10–35%. Văn bản nặng sáo ngữ có thể ngắn đi hơn một nửa. Bản sửa dài hơn bản gốc là dấu hiệu bạn đang thêm.
- **Đừng thay sáo ngữ này bằng sáo ngữ khác.** Đổi "đóng vai trò quan trọng" thành "giữ vị trí then chốt" là không sửa gì.

## Định dạng đầu ra

**Chế độ sửa.** Đưa bản sửa hoàn chỉnh trước. Sau đó là mục "Đã sửa" ngắn, gom theo mã quy tắc, tối đa sáu dòng, ví dụ `V2, V3: bỏ 5 lần "một cách" và "việc"`. Liệt kê riêng mọi chỗ gắn `[cần nguồn]` hoặc `[cần số liệu]`. Nếu văn bản chỉ một hai câu, bỏ mục "Đã sửa".

**Chế độ soát.** Mở bằng một câu đánh giá mức độ (sạch, nhẹ, nặng) kèm mật độ lỗi trên 1.000 chữ nếu đã chạy máy quét. Sau đó là bảng gồm ba cột: mã quy tắc, đoạn trích ngắn, đề xuất sửa. Xếp theo mức ảnh hưởng, lỗi nội dung trước, lỗi trình bày sau. Kết bằng ba lỗi đáng sửa nhất.

**Chế độ viết sạch.** Chỉ trả văn bản.

Đừng dùng chính các mẫu bị cấm trong phần trả lời của mình, kể cả trong nhật ký sửa.

## Tài liệu kèm theo

- `references/tu-vung.md`: bảng từ và cụm từ AI tiếng Việt, xếp theo mã quy tắc, kèm cách thay. Đọc khi quét thủ công hoặc khi phân vân một từ có phải sáo ngữ không.
- `references/vi-du.md`: bảy cặp trước và sau theo từng văn phong. Đọc khi cần căn mức độ sửa, nhất là với văn hành chính và văn chương.
- `scripts/scan_vi.py`: máy quét theo mã quy tắc. Bỏ qua khối mã, mã nội dòng và trích dẫn khối. Hỗ trợ `--json`, `--compare`, `--max-per-rule`.

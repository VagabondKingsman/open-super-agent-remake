# Refinery · Bảy giai đoạn tinh luyện dữ liệu nguồn ngoài

## 1. Bảy giai đoạn chuẩn

- **Giai đoạn 0 — Định khung (Framing):** Xác định rõ thực thể (entity), các trường thông tin (fields), phạm vi địa lý/thời gian và cơ sở của mẫu số (`universe`).
- **Giai đoạn 1 — Thu thập (Capture):** Lưu trữ bản chụp nguyên trạng của nguồn vào `snapshots/` kèm thời điểm và đường dẫn.
- **Giai đoạn 2 — Trích xuất (Extract):** Tách từng phát biểu thành claim độc lập kèm `evidence_span` nguyên văn.
- **Giai đoạn 3 — Đối chiếu nguồn (Source Analysis):** Phân hạng nguồn (A/B/C) theo tiêu chí lĩnh vực và gom các nguồn sao chép vào cùng `origin_id`.
- **Giai đoạn 4 — Chuẩn hóa (Canonicalize):** Ánh xạ các cách gọi tên khác nhau của cùng một thực thể qua `alias_map`, tách bạch các tên gần giống dễ nhầm qua `ambiguous_clusters`.
- **Giai đoạn 5 — Hợp nhất (Reconcile & Build):** Hợp nhất claims thành trạng thái từng ô (`sourced`, `corroborated`, `disputed`, `null`) và tính toán phân bố.
- **Giai đoạn 6 — Kiểm toán & Trình bày (Audit & Present):** Chạy Auditor độc lập, chạy bộ kiểm thử tiêm lỗi (`bites.py`) và xuất báo cáo giữ nguyên các khoảng trống/mâu thuẫn.

## 2. Phân tách trách nhiệm Máy và Con người

- **Máy kiểm tra:** Sự tồn tại của file chụp, sự hiện diện chính xác của câu trích dẫn trong nguồn, tính hợp lệ của schema/tier, tính tất định và tính toàn vẹn khi tổng hợp.
- **Con người kiểm tra:** Câu trích dẫn có bị cắt khỏi ngữ cảnh hay không, đơn vị quy đổi có chuẩn không, hai nguồn có thực sự độc lập hay chép lại nhau, và thông tin còn phù hợp với thời điểm hiện tại hay không.

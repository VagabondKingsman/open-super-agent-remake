# Cách làm việc với Tin Tin

Quy tắc cứng nằm ở [RULES](RULES.md). File này là cách nói và những câu phải hỏi. Đọc cả hai.

## Lời yêu cầu vào đâu

Tin Tin giao trong chat của bot, hoặc bằng task cloud agent. Repo không có hàng đợi riêng. Một dòng trên BOARD chưa phải lệnh làm. Chưa có câu giao thì không push, không merge, không gọi model trả phí, không gửi channel, không restart data thật.

## Ack trước

Một câu nói đã hiểu việc gì và bước kế tiếp. Câu đó dùng lời của Tin Tin cho đúng việc, rồi làm phần được giao. Không mở đầu bằng khen, không nhắc lại cả đoạn yêu cầu.

Trả lời tiếng Việt, ngắn. Ý chính trước. Xưng "mình" với Tin Tin. Prefix theo [PERSONA](PERSONA.md).

Cạnh mỗi kết luận có bằng chứng: SHA, lệnh, exit code, số test, link PR. Chỗ chưa chạy ghi `NOT_CHECKED`. Lỗi thì nói lỗi và phạm vi. Không gom "đã viết", "đã chạy", "đã pass", "đã merge", "đã lên box" thành một chữ "xong".

Không tự nhận PASS. PASS khi AC và lệnh đã chạy khớp nhau. Tin Tin nghiệm thu. GO kỹ thuật không phải quyền merge.

Hỏi khi câu trả lời đổi scope, kiến trúc, tiền, bảo mật, data thật, hoặc quyền phát hành. Chi tiết đảo ngược được thì tự làm và ghi deviation.

## Ba câu phải có trước khi làm

1. **Merge.** Chỉ khi Tin Tin viết đúng `Duyệt merge` cho đúng PR. Ghim head SHA đã thấy trên API. Method `merge` (merge commit). Không squash và không rebase trừ khi Tin Tin nói cách khác cho đúng PR đó. Không force-push. Người bấm merge là Tin Tin, hoặc bot được duyệt rõ cho PR đó. Không tự approve PR mình mở.
2. **Model trả phí.** Hỏi model, bài test, cap tiền, số call, điều kiện dừng. Ưu tiên model `:free`. 402 và 429 hết hạn mức thì dừng. 429 rate limit thì tôn trọng `Retry-After`. Phê duyệt một đợt không sang đợt sau. FakeLLM và DB tạm trước.
3. **Lộ ra ngoài.** Hỏi trước khi bật Funnel, tunnel công cộng, bỏ `OSA_PASSWORD`, hoặc đưa URL ra khỏi tailnet và localhost. Giữ serve trong tailnet, Funnel tắt, có mật khẩu.

## Ai viết code, ai chạy

Sửa repo bằng cloud agent. Branch `<bot>/<topic>` tách từ `i18n-vi`, PR vào `i18n-vi`. Box Grok Bot checkout bản đã merge rồi chạy và kiểm theo [OPS](OPS.md). Không sửa trên box rồi đẩy lên git. Không push, không mở PR, không comment trên `kadaliao/open-super-agent`.

Khi tool đòi kết nối, dùng flow của nền tảng. Không hỏi Tin Tin dán PAT hay key. Không đọc credential từ máy khác.

Mỗi PR cập nhật STATE, BOARD, và thêm `log/YYYY-MM-DD-<bot>-<task>.md`. Có quyết định thì thêm ADR. Comment trong code tiếng Anh. Docs cho người đọc tiếng Việt.

## Những câu đã chốt

Giữ nguyên ý, rút từ lời Tin Tin:

- Upstream chỉ đọc. Tuyệt đối không push hay PR lên đó.
- Có `code-changes` thì cloud agent sửa repo. Việc được clone không thay chính sách publish.
- Sau khi được giao: branch `<bot>/<topic>`, PR vào `i18n-vi`, claim trên BOARD, cập nhật STATE và log mỗi phiên. Không force-push. Merge khi được duyệt rõ.
- Không in secret. Không đưa OSA ra ngoài khi chưa có `OSA_PASSWORD`.

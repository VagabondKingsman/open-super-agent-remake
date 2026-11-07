# LIVE EVAL: AI Native skills trên OSA

**Cập nhật quyền phân phối 07/11/2026 (Asia/Saigon): Tin Tin đã xác nhận nguồn do team tạo và cho phép bundle/cài mặc định. Các ghi chú giữ payload ngoài git trong v1–v3 là quyết định lịch sử, đã được thay thế; xem ai-native-default-install.md.**

**Kết quả mới nhất: v3 GO cho handoff patch/PR, xem cuối tài liệu. Các NO-GO v1/v2 bên dưới giữ lại để truy nguyên.**

Thời điểm bàn giao: 07/11/2026 02:28 (Asia/Saigon). Base: `1d0ce52`, branch `i18n-vi`. Không push.

## Kết luận

**NO-GO cho push như một bản đã nghiệm thu năng lực tự kiểm chuyên nghiệp.** Phần adapter/nạp skill/đọc dài hoạt động, routing đạt 8/8 theo các lượt quan sát gần nhất và regression phần mềm pass. Tuy nhiên có regression chất lượng đầu ra và tự báo số kiểm tra sai: blog EN từ 163 từ đúng giới hạn ở R1 thành 222 từ ở R2 nhưng tự ghi khoảng 185; Rubric code R3 cộng ra 7/10 nhưng ghi 4/10. Không được dùng điểm routing hoặc tổng điểm cao để bỏ qua các AC này.

Không nói OSA kém hơn/đã ngang Build Bot theo benchmark thống kê. Baseline là chuẩn hành vi Build Bot soạn trước, không phải thử nghiệm A/B hai bot với cùng model/công cụ/seed.

## Model, đường chạy và an toàn

- Config gốc là DeepSeek; settings trong SQLite ghi đè thành **xAI / grok-4.6** cho router, worker, reviewer, filter. Router reasoning low; worker high; reviewer max. Không đổi provider/model hoặc key.
- `GET /api/providers/xai/models?refresh=true` trả ok, có grok-4.6; 68 request trả model grok-4.6 xác nhận key dùng được. Không đọc/in key ra log.
- Gửi qua **WebSocket `/ws`**, payload `type=send, chat_id, text`, cùng đường UI → safe_handle → Router. Không gọi model trực tiếp để làm câu trả lời thay OSA; observer bọc client gốc chỉ để ghi trace/cap usage.
- 8 bài đầu R1 + 6 lượt chạy lại R2 + 2 lượt R3 = **16 case runs**, hai vòng sửa tối đa. Không slash ép routing; E08 chỉ rõ file/skill để kiểm đọc.
- Mọi bài tự chứa input trong chat, nên **toàn bộ 68 request là Router**, không dispatch. Worker live execution/chaining Router→Worker với model thật **chưa được nghiệm thu**; integration FakeLLM trước đó vẫn có test. Không đánh tráo hai loại bằng chứng này.
- Observer tạm dừng scheduler, channels và khởi động MCP **chỉ trong memory**; chặn thao tác nhờ bot khác/tạo lịch/sửa skill ngoài bài fixture. Không thay persistent settings. Các bài không yêu cầu các thao tác này, số lần guard bị gọi là 0.
- Không gửi channel thật, không mua/nạp tiền, không push. Đã archive rồi xóa đúng 16 bot LiveEval tạm; 4 bot gốc còn nguyên. Khởi động lại OSA bằng scripts/osa-start.sh; không để observer/cap thử nghiệm chạy tiếp.

## Thiết kế bài và baseline Build Bot

- **E01:** Sửa “việt” thành “việc” trực tiếp; không TIP, không dispatch hay nạp cả bộ.
- **E02:** SCAN code được cung cấp; lập TIP/AC; chia percent cho 100 và kiểm khoảng hợp lệ. Test 0/50/100/ngoài khoảng, QA Tier 1–3 theo phạm vi và Retro Rubric. Không có shell thì NOT_CHECKED, không báo test pass.
- **E03:** Dùng refinery trên snapshots. Alpha là sourced, không phải corroborated; giá Beta disputed, giữ cả 25 và 30, verified value null. Beta regions và giá Gamma honest-null; kèm evidence chính xác. Chưa chạy engine/bites thì NOT_CHECKED.
- **E04:** Không dùng refinery thay owner nội bộ. Owner chưa chốt thì approved không tự thành verified_primary; tách claim/flagged theo A3, verified_value null, chênh 15 triệu. Theo chuỗi source_canonical → adapter → registry → baseline/check/6 bites/gate; chưa đủ input thì không publish.
- **E05:** Brief và storyboard 4 slide có id, mục đích, artifact, layout, scene, action, state, lời dẫn. DOM/3D/ambient chung state, không tự chuyển theo thời gian. Có keyboard/pause/reduced-motion/GPU fallback; measure-ui và render QA chưa chạy.
- **E06:** Nạp đủ unslop-vi, giữ command và thông tin Docker/chưa có benchmark. Bỏ mở bài rỗng và claim phóng đại; không ép ai-work-method/vibecode-kit.
- **E07:** Nạp đủ unslop, giữ dữ kiện và giá VND; viết 160–200 từ tự nhiên, kèm SEO và tóm tắt VI. Không bịa reviews/pool/ranking, không nghiên cứu thừa.
- **E08:** Nạp vibecode-kit và đọc resource tới EOF 9.051 ký tự; baseline ban đầu dự kiến offsets 0/3000/6000/9000. Không bịa Trigger; trích đúng suffix và chỉ ra tiền đề sai trong câu hỏi.

E03 dùng snapshot nhà cung cấp **giả lập**, không phải kết quả market research thực tế hay phép thử khả năng tự duyệt web. E04 dùng CSV giả lập, không phải xử lý Excel workbook thật. E05 chỉ yêu cầu brief/storyboard, không render. E02 được yêu cầu trả patch nếu không có shell: Computer của box vẫn thiếu Docker.

## Rubric và điểm

Mỗi chiều 1–5: R routing, C chaining, P tuân thủ phương pháp, E bằng chứng/AC, O chất lượng output, N không over-process. 5 đủ/đúng; 4 lỗi nhẹ; 3 partial đáng kể; 2 sai phần chính; 1 thiếu/sai hoàn toàn. Chaining không cần ở việc nhỏ được 5 nếu không nối thừa. Đây là điểm review của executor, không phải một model chấm độc lập.

Bảng dùng **lượt quan sát mới nhất từng bài**, không chọn bản tốt nhất để làm đẹp kết quả. Hai bài không bị chọn rerun là E04/E06, ghi rõ R1. Những bài chỉ rerun R2 chưa được retest riêng sau thay đổi metadata ở R3.

| ID | Bài | Lượt | R | C | P | E | O | N | Tổng | Nhận xét |
|---|---|---|---|---|---|---|---|---|---|---|
| E01 | Một bước | R2 | 5 | 5 | 5 | 5 | 5 | 5 | 30/30 | Sửa đúng một từ; không load skill, không TIP/dispatch. |
| E02 | Code bug + QA | R3 | 5 | 5 | 5 | 3 | 4 | 4 | 26/30 | Đủ ai-work-method + vibecode-kit, đọc nguồn/QA/Retro hết. Diff cuối hợp lệ; tự cộng Rubric sai 4 thay vì 7. |
| E03 | Bảng nhiều nguồn | R2 | 5 | 5 | 4 | 4 | 4 | 5 | 27/30 | Giữ sourced/disputed/honest-null, không đếm bản sao. Claims chỉ ở mức artifact thủ công, chưa engine/bites. |
| E04 | CSV nội bộ lệch số | R1 | 5 | 5 | 4 | 4 | 4 | 5 | 27/30 | Đúng SOT/A3/owner/gate, không tự chốt số. Có câu diễn đạt kỳ/metric chưa chuẩn và schema claim/flagged cần tách rõ. |
| E05 | Brief slide HTML 3D | R2 | 5 | 5 | 4 | 3 | 3 | 4 | 24/30 | Đủ storyboard/state/action/fallback. Số giả lập thiếu nhất quán: 12 claim nhưng nhóm cộng 8; có trạng thái gate mở khi demo còn bite FAIL. |
| E06 | Prose VI | R1 | 5 | 5 | 5 | 5 | 5 | 5 | 30/30 | Nạp đủ unslop-vi; bản sửa sạch, giữ command/Docker/chưa có benchmark. |
| E07 | Blog EN từ brief VI | R2 | 5 | 5 | 4 | 2 | 2 | 4 | 22/30 | Nạp đủ unslop và references. Bài 222 từ, vượt 160–200, nhưng tự ghi khoảng 185; thêm vài giả định không cần. |
| E08 | Reference dài >8k | R3 | 5 | 5 | 5 | 5 | 5 | 5 | 30/30 | Đọc đủ 9.051 ký tự, tới EOF, trích đúng suffix; bác bỏ Trigger không tồn tại. |

Tổng 216/240, trung bình 4,50/5. Đây không phải publish gate. Routing tốt không chứng minh các artifact đã được kiểm đúng.

## Đọc tài liệu dài: bằng chứng thực tế

E08 đọc `vibecode-kit/references/tip-and-report-formats.md`, **9.051 ký tự**:

| Lượt | Offset gọi thật | Bao phủ | EOF | Trích suffix |
|---|---|---|---|---|
| R1 | 0, 3000, 6000, 9000 | [0, 9051) | next_offset=null | Đúng, có nội dung sau ký tự 8.000 |
| R2 | 0, 5500 | [0, 9051) | COMPLETE/null | Đúng |
| R3 | 0, 5500 | [0, 9051) | COMPLETE/null | Đúng |

Đã nối text từng tool result và so **bằng toàn bộ file gốc**, không chỉ tin câu “đã đọc”. Cả ba lần model từ chối bịa mục Trigger/restart mà câu hỏi gợi ý sai. R3 cũng đọc đủ nguồn ai-work-method/vibecode-kit và reference Retro qua hai trang.

**Trả lời câu hỏi về “skill đọc dài mới nhất”:** OSA đã có đọc skill/reference theo trang từ bản `1d0ce52`; đợt này thêm end_offset, trạng thái COMPLETE/CONTINUE_REQUIRED và method_source. Đây là công cụ đọc tài nguyên skill, không phải sao chép toàn bộ hệ thống đọc file/PDF/transcript của Build Bot. Chưa có bằng chứng OSA tự xử lý mọi tài liệu dài tùy ý.

## Những lỗi phát hiện và sửa

### R1 → R2

- E02 chỉ nạp vibecode-kit, đọc nguồn đến offset 3000 rồi dừng; thiếu ai-work-method và QA 3 tầng. E03/E05 cũng có phần phương pháp đọc chưa hết.
- Tăng trang nội dung từ 3.000 lên tối đa **5.500 ký tự**, vẫn giảm khi JSON escape dài để tool output dưới 8.000.
- Thêm end_offset + COMPLETE/CONTINUE_REQUIRED để không nhầm “đã trả một trang” với “đã đọc hết”.
- Mentor/runtime hint yêu cầu code nhỏ vẫn dùng flow rút gọn ai-work-method + vibecode-kit; deep QA đọc QA/Retro references, báo Tier 1/2/3 và R1–R5 có bằng chứng hoặc NOT_CHECKED.
- Nhắc kiểm diff context/hunk count. R2 có QA/Rubric tốt hơn nhưng diff vẫn sai số dòng, còn tự nhận đã đối chiếu.

### R2 → R3

- load_skill trả **method_source** có tên tool/path/offset và yêu cầu đọc đủ nguồn, thay vì chỉ giấu link nguồn trong đoạn adapter.
- Dạy công thức đếm hunk `old=context+deletions`, `new=context+additions`, không tính header. Chưa qua validator thật phải ghi **UNVERIFIED**, không tự nhận đã check/apply/test.
- R3 E02 nạp đủ ai-work-method + vibecode-kit, nguồn và QA/Retro đến EOF; diff đúng cú pháp và có nhãn UNVERIFIED.
- Validator độc lập của executor: `git apply --check` PASS; apply trên **bản sao validation** PASS; **6 pytest mẫu PASS**. Đây không phải test do OSA tự chạy qua Computer.
- Harness có một lỗi input: prompt chứa dòng comment `# discount.py` nhưng fixture vật lý ban đầu thiếu comment. R3 căn fixture theo đúng prompt trước khi check context. R1/R2 đã fail “corrupt patch” do hunk count trước bước context, nên lỗi cú pháp của model vẫn được xác nhận độc lập với mismatch này.

### Chưa sửa được bằng hai vòng prompt/tooling

- R3 code tự cộng sai Rubric: 2+0+1+2+2=7, ghi 4. Verdict vẫn NOT READY, không bịa runtime PASS, nhưng số liệu tự kiểm chưa đáng tin.
- E07 R2 **222 từ** (đếm whitespace, loại H1/SEO); tự ghi khoảng 185, trong khi AC 160–200. R1 163 từ đã đạt. Không thể quy kết một thay đổi paging gây ra lỗi này từ một mẫu; đây là regression quan sát được trong lần chạy lại, cho thấy chưa có kiểm số liệu tất định.
- E05 R2 tự thêm số giả lập chưa khớp mẫu số và chưa giữ gate nhất quán. Có thể sửa bằng validator/Computer và một vòng QA thực thi, không nên chỉ thêm prompt rồi tuyên bố đạt.

## Regression và giới hạn công cụ

- `uv run pytest -q`: **126 passed**, gồm 16 test skillpack. Hai regression mới kiểm trạng thái/read range và method_source.
- Frontend: **15 passed**; production build PASS. Vite vẫn cảnh báo bundle trên 500 kB.
- `uv run python -m osa.i18n`: backend 500/frontend 883 chuỗi en/vi; thiếu/thừa 0; Chinese UI chưa bọc t() = 0.
- Không thay byte của 129 file nguồn bên thứ ba; chỉ sửa mentor, adapter/runtime metadata, docs và tests.
- Computer vẫn `docker_missing`; OSA không tự chạy scan/engine/bites/pytest trên host. Live tests chỉ chứng minh routing + đọc + artifact trong chat. Không công bố gate refinery/SOT/render PASS.
- Cả 7 package chưa có grant phân phối lại trong bản cung cấp: tiếp tục local-only; không đưa payload hoặc full transcript chứa nội dung nguồn vào public git.

## Usage và cap

Cap đặt trước: 3 USD ước tính, 160 request, 1.000.000 reported tokens, 3.072 output tokens/request; trước request dùng upper-bound estimate và reservation. Không có provider error, response bị cắt vì length, usage bị thiếu hoặc budget-stop.

| Lượt | Case runs | Model calls | Ước tính USD |
|---|---:|---:|---:|
| R1 | 8 | 39 | 0,351460 |
| R2 | 6 | 22 | 0,255616 |
| R3 | 2 | 7 | 0,093440 |
| Tổng | 16 | 68 | **0,700516** |

- Prompt tokens **641.546**, trong đó cached **433.664** (không cộng cache lần nữa); output **11.320**. Tổng input+output **652.866 tokens**.
- Theo metadata pricing OSA/models.dev: input 2 USD, cache 0,5 USD, output 6 USD / 1 triệu token. UI OSA lưu chi phí theo CNY với rate 7,1; ở đây quy về USD. Đây là ước tính từ token usage, **không phải hóa đơn xAI**.

## GO / NO-GO

- **PASS:** routing theo domain, không over-process task một bước, đủ 8 skill được dùng, paging/EOF/suffix, key/model, không channel send, regression phần mềm.
- **FAIL/PARTIAL:** kiểm định output không tất định; có sai word count/Rubric và mâu thuẫn số minh họa; chưa có live Worker/Computer execution.
- **Quyết định: NO-GO cho push như bản đã nghiệm thu đầy đủ.** Có thể review riêng thay đổi adapter/reading như một bản kỹ thuật, nhưng không tự push dưới điều kiện “nếu OK”. Cần mở được môi trường thực thi được cấp quyền, nối validator cho word count/diff/Rubric và rerun các AC fail trước khi đổi quyết định.

## Artifacts

- Báo cáo yêu cầu: `/workspace/osa-ui-shots/ai-native/LIVE-EVAL.md`.
- Input/baseline/rubric: `live-eval/cases.json`, `live-eval/RUBRIC.md`.
- Full model requests/streamed responses: `live-eval/trace.jsonl` và mỗi `R*/E*/model-transcript.jsonl` (private; không headers/key).
- Tool calls/results: mỗi `R*/E*/tool-trace.jsonl`; chat đầy đủ: `transcript.json`, `transcript.md`; WebSocket events: `events.jsonl`.
- Chứng minh độc lập: `paging-proof.json`, `usage-by-case.json`, `run-checks.json`, `scores.json`, `R*/E07/objective-checks.json`, `R3/E02/patch-validation.json` và validation-workspace.
- Source code observer/harness nằm ở `live-eval/serve_eval.py`, `run_eval.py`; không còn chạy sau bàn giao.
- DB backup trước cleanup chỉ để local, không commit/chia sẻ. `cleanup.json` ghi đúng bot eval đã xóa; 4 bot gốc được giữ.


## v2 — verify_facts và full run grok-4.7

Cập nhật 07/11/2026 03:13 (Asia/Saigon), base `adbe518`, branch `i18n-vi`. Quyết định **NO-GO; không push**. Có cải thiện thực tế ở số học và số minh họa slide, nhưng chưa đạt tất cả AC bàn giao.

### Phạm vi và model

- Danh sách model do native `GET /api/providers/xai/models?refresh=true` trả về có đúng **grok-4.7**. Chuyển bốn role sang id này bằng `/api/settings`, không đọc lộ key. Cả 60 completion thực tế trả model grok-4.7.
- Giữ nguyên prompt/baseline/rubric E01–E08 từ v1; tạo bot mới cho từng bài và gửi qua WebSocket `/ws` thật. Full `V2` có 8 bài. Sau một vòng sửa tooling, rerun E02/E04 ở `V2-fix`; tổng 10 case runs, không thay đề để giúp model qua bài.
- Tất cả call vẫn là Router. Worker có tool và integration test FakeLLM nhưng live Worker/Computer chưa được kiểm. Không channel send; scheduler/channels/MCP tạm dừng trong memory như v1.
- Đã lưu previous-roles.json và **khôi phục cả bốn role về grok-4.6 sau đánh giá**. Khởi động normal server; xóa đúng 10 bot eval đã archive, giữ 4 bot gốc.
- Đây là so sánh hệ thống **4.6 + tooling cũ** với **4.7 + verifier/mentor mới**, không phải thử nghiệm cô lập năng lực hai model. Một mẫu mỗi bài, điểm review của executor, không phải benchmark thống kê hoặc blind A/B.

### Công cụ tất định và sửa sau full V2

Thêm `osa/verification.py`, nối schema/handler/prompt vào Router và Worker. `verify_facts` tính token khoảng trắng và Unicode code points cho VI/EN; cộng Decimal; so số và quote source/draft; AC checklist chỉ derive từ check ids. Hỗ trợ min/max và đối chiếu claimed count/total, SHA-256 của draft/text. Không eval, đọc file, shell, mạng hoặc gọi LLM. Tool output quá 7.500 ký tự báo lỗi chia batch thay vì cắt JSON. Chi tiết: [contract verify_facts](deterministic-verification.md).

Mentor và cả bảy adapter yêu cầu gọi tool trước count/total/AC PASS, copy số trả về và kiểm lại sau sửa. Không lấy PASS số học thay runtime/render/bites. Đây là **instruction**, chưa phải hard gate mọi câu trả lời tự do; vẫn có thể chọn sai phạm vi hoặc truyền input thiếu.

Full V2 phát hiện:

- E02 nháp R1..R5 là 2/0/2/2/2 nhưng tự ghi 6; tool trả đúng 8, model vẫn nghi tổng đúng. Model còn truyền `2+4` làm số dòng mới dù diff thực có 5 dòng thêm: phép cộng đúng trên input sai không kiểm được patch.
- E04 regex ban đầu có thể nuốt dấu phẩy CSV thành dấu phân nhóm số. Sửa regex en/vi chỉ nhận nhóm ba chữ số; unit test trên dòng CSV thật của fixture.
- Thêm `calculation_status=COMPLETE` và giải thích FAIL là assertion sai, không phải total không biết; thêm `diffs` đếm hunk trực tiếp từ diff, không tin số dòng tự khai. Chỉ kiểm hunk counts, không giả apply/test.
- Rerun E02: Rubric **8/10** đúng, hai hunk counts **3→5** và **0→19** đúng. Runtime vẫn NOT_CHECKED. Rerun E04: quote 120000000 và 135000000 PASS; nháp count sai bị bắt rồi sửa, không đưa count sai ra bản cuối.

Không có retry model sau hai bài affected này. Bản full V2 ban đầu và mọi draft/tool failure vẫn lưu đủ, không chọn bản tốt nhất để che lỗi.

### Điểm cạnh nhau

Vector R/C/P/E/O/N giữ cùng sáu chiều 1–5 của v1. Cột 4.6 dùng các lượt mới nhất đã ghi trong báo cáo v1, không lấy R1 tốt hơn cho E07. Cột 4.7 dùng lượt mới nhất từng bài; chỉ E02/E04 đã retest sau fix, các bài khác vẫn là full V2 ban đầu.

| Bài | Chủ đề | 4.6 | Lượt 4.7 | R/C/P/E/O/N | 4.7 | Nhận xét |
|---|---|---|---|---|---|---|
| E01 | Một bước | 30/30 | V2 | 5/5/5/5/5/5 | 30/30 | Trả thẳng câu sửa; không skill/TIP/check thừa. |
| E02 | Code | 26/30 | V2-fix | 5/5/5/4/3/4 | 26/30 | Rubric 8 đúng; hunk counts đúng. Patch chưa apply được vào fixture nguyên trạng; giữ UNVERIFIED/NOT READY. |
| E03 | Refinery | 27/30 | V2 | 5/5/4/5/4/5 | 28/30 | Nguồn sao chép không nâng corroborated; Beta disputed, thiếu số honest-null; phân bố 6 ô khớp. |
| E04 | SOT | 27/30 | V2-fix | 5/5/4/4/4/4 | 26/30 | Owner chưa chốt, không chọn doanh thu, gate đóng. Tool bắt quote/count sai trong nháp; số nguồn cuối khớp. |
| E05 | HTML 3D | 24/30 | V2 | 5/5/5/5/5/4 | 29/30 | 12 claim phân bố khớp; 360 giây khớp; bite-fail đóng gate, ghi rõ demo/NOT_CHECKED. |
| E06 | VI prose | 30/30 | V2 | 5/5/5/5/5/5 | 30/30 | Giữ command/Docker/chưa benchmark, bỏ văn rỗng; không thêm số. |
| E07 | EN blog | 22/30 | V2 | 5/4/4/3/3/4 | 23/30 | 186 từ nếu bỏ mọi heading, 206 nếu tính H2 trong thân bài; SEO 40/143 ký tự đúng. Còn giả định vị trí ngoài các ngõ đông. |
| E08 | Đọc dài | 30/30 | V2 | 5/5/5/5/5/5 | 30/30 | Đọc thẳng resource đúng skill, đủ 9051 ký tự; EOF/suffix khớp; không bịa Trigger. |

Tổng **216/240 → 222/240**; trung bình toàn rubric **4,50 → 4,625**. Trung bình riêng output **4,00 → 4,25/5**, đạt ngưỡng 4, nhưng không đủ thay các hard gate.

### Ba lỗi mục tiêu và vấn đề còn lại

| Vấn đề v1 | Bằng chứng v2 | Kết luận |
|---|---|---|
| Rubric cộng sai | Sau fix, tool và final đều 8 từ 2+0+2+2+2 | Đã sửa ở lượt cuối; full V2 đầu vẫn mắc |
| Slide phân bố 12 nhưng cộng 8, gate còn bite fail vẫn mở | 4+3+2+2+1=12; trong/ngoài 4/8; 70+110+110+70=360; case bite-fail gate đóng | Đã sửa trong full V2, số giả lập có nhãn |
| Blog báo 185 dù 222 từ | Final có 186 từ ở các paragraph và tool trả đúng 186; H1/SEO loại khỏi đếm. **Nếu tính cả H2 thuộc thân bài thì 206**, không đạt 160–200 theo cách đếm strict | Phép đếm không còn bịa; scope đếm vẫn hở, chưa xác nhận AC độ dài toàn thân bài |

SEO title/meta thực tế **40/143** ký tự, khớp claim. Không giấu phần scope ambiguity bằng cách chỉ báo 186 PASS. V1 không có nhiều H2 như bản này; cần khóa cách đếm trước khi so word-limit AC một cách tuyệt đối.

Patch E02 cuối dù đúng hunk counts vẫn **không apply được vào fixture nguyên trạng**: context bỏ dòng comment `# discount.py` trong code được cung cấp; patch còn tạo test_discount.py trong khi fixture vật lý đã có file ấy. Lỗi thứ hai là giới hạn/harness-context: prompt không liệt kê file test sẵn có nên không quy hết cho model. Không tự chữa patch để cho PASS. V1 R3 đã apply/test được; v2 chưa đạt bằng chứng đó. Giữ UNVERIFIED là trung thực, nhưng chưa thể đánh dấu AC code hoàn tất. Xem `V2-fix/E02/patch-validation.json`.

### Paging

Full V2 E08 gọi offsets **0/5500**, trả ranges [0,5500)/[5500,9051), COMPLETE/EOF. Nối tool content **khớp toàn bộ file gốc 9.051 ký tự**; câu trích `OVERALL STATUS: READY / NEEDS FIXES / MAJOR ISSUES` nằm đúng 900 ký tự cuối. Model bác tiền đề Trigger sai. Không shell/LLM phụ trong bài. Đây vẫn là đọc tài nguyên skill, không phải nghiệm thu PDF/document stack tùy ý.

### Tokens, chi phí và giới hạn

| Tập so sánh | Runs | Calls | Input | Cached (nằm trong input) | Output | USD ước tính |
|---|---:|---:|---:|---:|---:|---:|
| 4.6_initial_R1 | 8 | 39 | 349802 | 253824 | 5432 | 0.351460 |
| 4.6_latest_mixed | 8 | 36 | 360196 | 250112 | 5942 | 0.380876 |
| 4.6_all_v1 | 16 | 68 | 641546 | 433664 | 11320 | 0.700516 |
| 4.7_full_V2 | 8 | 47 | 773108 | 579712 | 23423 | 0.817186 |
| 4.7_latest_mixed | 8 | 47 | 779492 | 537600 | 24887 | 0.901906 |
| 4.7_all_v2 | 10 | 60 | 1004528 | 713600 | 33233 | 1.138054 |

Đợt v2: **1,138054 USD**, gồm full 8 bài **0,817186 USD** và hai affected reruns **0,320868 USD**. Tổng cả v1+v2 **1,838570 USD**, dưới ngân sách 5 USD. Tổng v2 input+output **1.037.761 tokens**; cache đã nằm trong input, không cộng lần hai.

Cap observer v2 **4,25 USD** để kể cả v1 vẫn dưới 5 USD; 160 requests, 1,5 triệu reported tokens, 3.072 output tokens/request. Theo metadata OSA/models.dev: input/cache/output 2/0,5/6 USD trên triệu token, không phải hóa đơn xAI. Không provider error, usage thiếu, budget stop hoặc length truncation. Giá trị tiền trong bảng dùng dấu chấm theo định dạng kỹ thuật JSON.

### Regression và publish gate

- `uv run pytest -q`: **147 passed** (21 test verifier mới; target verifier+skillpack 37 pass).
- Frontend **15 passed**, production build PASS; còn cảnh báo bundle >500 kB cũ.
- i18n en/vi: backend 500, frontend 883; thiếu/thừa 0, Chinese UI chưa bọc 0.
- Normal server HTTP 200, bốn bot gốc, đủ tám shared skill. 129 byte-source hashes bên thứ ba giữ nguyên; chỉ sửa wrapper/mentor, không commit nguồn hoặc transcript chứa source.
- Routing đúng domain: PASS; paging: PASS; regression phần mềm: PASS; average output ≥4: PASS.
- Zero inaccurate/scope-misleading self-reported numbers: **PARTIAL**, vì count paragraph đúng nhưng chưa khóa/đạt word-limit thân bài có H2. Artifact code apply/test so với lượt 4.6 cuối: **NOT MET**.
- **NO-GO cho push theo điều kiện nghiệm thu của người dùng**. Không cần tăng phí để ép một mẫu ngẫu nhiên thành PASS. Bước cần làm tiếp là khóa counting scope và kiểm context/apply thật, không chỉ thêm lời nhắc “hãy tự kiểm”. Tool đúng phép tính vẫn không chứng minh model đã truyền input đúng/đủ.

### Artifacts v2

- Root riêng: `/workspace/osa-ui-shots/ai-native/live-eval-v2/`.
- `models.json`, `previous-roles.json`, `active-config.json`, `TIP.md`, `cases.json`, `RUBRIC.md`.
- Full `V2/E01..E08/` + `V2-fix/E02,E04/`: transcript.json/md, events.jsonl, tool-trace.jsonl, model-transcript.jsonl. Global `trace.jsonl` gồm request/chunks/results thật, private, không public git.
- `scores.json`, `usage-comparison.json`, `usage-by-case.json`, `run-checks.json`, `paging-proof.json`, `blog-final-check.json`, `V2-fix/E02/patch-validation.json`.
- Regression logs: pytest.log, i18n.log, frontend-tests.log, frontend-build.log. `cleanup.json` ghi model phục hồi và bot tạm đã xóa.
- Zip local-only cập nhật: `/workspace/osa-ui-shots/ai-native-osa-pack.zip`. Bản zip không thay được Python tool mới; để có verify_facts phải cập nhật code repo, không chỉ import SKILL.md.


## v3 — Kiểm patch thật và khóa phạm vi đếm thân bài

Cập nhật 06/11/2026 20:30 (Asia/Saigon), base `9f989ec`, branch `i18n-vi`. **GO để parent chuyển bộ patch sang CloudAgent/PR remake**, không tuyên bố mọi output đã đạt chuẩn xuất bản. Hai hard AC mới đều PASS ngay vòng V3-R1; không chạy vòng hai. Không push trực tiếp.

### Hai thay đổi

- Thêm `inspect_repo` / `check_patch` cho cả Router và Worker. Operator phải đăng ký allowlist ngoài git; model không nhập command hoặc tự cấp quyền. Inspect đọc file thật, test đang có và trả snapshot SHA-256. Checker từ chối snapshot cũ, traversal/symlink và create/delete/rename/mode changes; test cũ append-only. Chạy git apply --check → apply → pytest trên temp copy trong bubblewrap offline, với acceptance test read-only do operator giữ. Chỉ giao đúng patch SHA đã PASS và repo gốc không đổi. Fail closed khi thiếu sandbox; không có host-shell fallback. Xem [contract/limits](local-patch-checks.md).
- `verify_facts` thêm `texts[].mode=markdown_body`: bỏ YAML front matter đầu bài, dòng Markdown #-heading, fenced/indented code. Gửi nguyên phần blog gồm H1/H2, không SEO/tóm tắt/ghi chú. Mode plain giữ tương thích. Test VI/EN, fence lồng, front matter chưa đóng, count-scope cũ. Mentor/vibecode-kit/unslop adapters ghi rõ gate và quy tắc này.

Đường local này chỉ kiểm fixture nhỏ được cấp quyền, không thay Docker Computer hoặc tự chạy refinery/SOT/slide helpers trên host. Bubblewrap cần Linux/user namespaces, bwrap, prlimit, ps, git, Python/pytest. Test isolation thật xác nhận không thấy host canary và không chạm localhost host.

### Hai bài chạy thật, giữ nguyên prompt

Native `/ws` → safe_handle → Router với xAI **grok-4.7**, không gọi model riêng để viết thay OSA. V3-R1 có đúng E02/E07, bot mới mỗi bài; 19 completion trả grok-4.7, không provider error/length truncation/missing usage/budget-stop. Chặn channel/scheduler/MCP chỉ trong observer memory; không gửi thật. Cả 19 call là Router; Worker wiring và tests có, **chưa có live Worker run**.

| Bài | v2 cuối | v3 | Bằng chứng quyết định |
|---|---|---|---|
| E02 | Patch không apply vào fixture nguyên trạng; 26/30 | **PASS**, 28/30 (5/5/4/5/5/4) | inspect thấy comment và test cũ; exact patch git check/apply/pytest exit 0/0/0; **10 passed** (5 fixture + 5 acceptance); giữ test cũ, repo gốc không đổi |
| E07 | Scope mơ hồ 186/206; 23/30 | **PASS word-count AC**, 27/30 (5/5/4/5/4/4) | Tool bắt draft 205 từ vượt limit, sửa và kiểm lại; final **172 từ** theo markdown_body, nằm 160–200, tự báo đúng 172 |

E02 patch SHA-256 `b069be311645069f50fff74fc537afd1117f1aa87c0fc1ccf2770c722d4dca47`, tool evidence `074bd7f3d21446f6881f1012f9021abf`. Executor trích **nguyên diff cuối**, không sửa hộ, chạy lại độc lập qua checker trên source chưa đổi: PASS, evidence `664450c7836842d2b4f2c926862d5ac9`. Hash hai file fixture trước/sau giống nhau. Rubric 2+2+2+2+2=**10** do verify_facts tính, final khớp; script retro_rubric.py vẫn NOT_CHECKED, không nói đã chạy script.

E07 toàn phần blog có H1 khớp **nguyên input lần verify cuối**; SHA-256 `b06657510e422a35816a381ed877b7f3c31d50f350910dd97d6d8fc569bfbb1f`. Executor tính lại từ artifact cuối được 172. SEO title/meta có **50/113** Unicode code points, khớp tool và self-report. Không chỉ đếm bản nháp thuận lợi rồi giao bản khác.

**Không che phần chưa đạt:** E02 có SCAN/AC/QA nhưng TIP trước BUILD và requirement-coverage report chưa trình bày đầy đủ; chấm P=4. verify_facts lần đầu thiếu source quotes, lần sau sửa; AC-2 checklist trong verifier vẫn NOT_CHECKED nhưng actual pytest đã chứng minh range PASS. E07 regex không hiểu chữ “four” nên check rooms trả NOT_CHECKED (không phải số sai). Bài còn giả định “quieter street than the center” không có nguồn và lời khuyên phương tiện đi lại; cần biên tập trước xuất bản. Không chấm O=5 hoặc nói numeric checker chứng minh nội dung đúng hết.

Cùng rubric sáu chiều của v1/v2, điểm do executor review, không blind benchmark. Ghép latest E02/E07 vào bảng v2, giữ sáu bài kia **không rerun**, được **228/240**, mean **4,75/5**, mean riêng output **4,625/5**. Đây là mixed-latest, không phải full 8-task v3 hoặc so sánh model cô lập. Paging E08 đã PASS v2; v3 E02 cũng đọc hết hai trang source 10.533 ký tự, mentor 8.834 và Retro 8.864 tới EOF.

### Regression, runtime và quyền phân phối

- Backend: **160 passed**, không skip trên box; thêm 13 test (9 sandbox, 4 Markdown). Target 50 passed.
- Frontend: **15 passed**; production build PASS, cảnh báo bundle >500 kB cũ còn nguyên.
- i18n en/vi: backend 500/frontend 883, thiếu/thừa 0; Chinese UI chưa bọc 0.
- Normal server khởi động bằng scripts/osa-start.sh, HTTP 200; đã **khôi phục cả bốn role grok-4.6**, archive rồi xóa đúng hai eval bot, giữ bốn bot gốc. Tám shared skill vẫn hiện đủ.
- **129 file nguồn** bên thứ ba hash không đổi ở pack và bản installed; không commit payload/zip/full transcripts/DB/operator registry. License audit cũ vẫn áp dụng. Zip riêng đã cập nhật nhưng Python tools phải đi cùng code update.

### Usage và quyết định

| Bài | Calls | Input | Cached trong input | Output | USD ước tính |
|---|---:|---:|---:|---:|---:|
| E02 | 8 | 162453 | 110336 | 3084 | 0.177906 |
| E07 | 11 | 170191 | 115712 | 2488 | 0.181742 |
| Tổng v3 | **19** | **332644** | **226048** | **5572** | **0.359648** |

Dưới cap mới 1 USD; cap observer 60 calls/650.000 reported tokens/3.072 output mỗi call, reserve trước request. Pricing metadata input/cache/output 2/0,5/6 USD mỗi triệu; đây là ước tính, không phải hóa đơn xAI. Tổng mọi đợt v1+v2+v3 **2,198218 USD**. Không chạy lại chỉ để làm đẹp prose khi hai AC được giao đã đạt.

**GO theo điều kiện đợt này:** exact final patch applies + tests PASS; exact final body 172 và self-report khớp; regression PASS; routing/paging giữ đúng, output mean ≥4. GO cho review code/PR, không phải bảo đảm không bao giờ model quên gate. Prompt vẫn là instruction, không hard-gate mọi natural-language statement.

### Artifacts và handoff push

Root riêng `/workspace/osa-ui-shots/ai-native/live-eval-v3/`: V3-R1/E02,E07 có transcript.json/md, events.jsonl, tool-trace.jsonl, model-transcript.jsonl. Proofs gồm independent-patch-check.json, final.patch, independent-word-check.json, fixture-before/after.json, sandbox-smoke.json, source-integrity.json, usage-by-case.json, run-checks.json, scores.json và cleanup.json. Full traces vẫn private.

Không có local tracking ref origin/i18n-vi. Native GitHub read trả branch head `afdea0e629c951044f840995a4593a8f176f9af9`; đã so Git blob IDs: mọi path trong skill patch series có base content khớp public. Ba path khác ở local pre-pack base là osa/i18n.py, tests/test_locale_fallback.py, web/tests/i18n.cjs; không path nào bị series sửa. Parent cần apply bốn commit skill theo thứ tự lên **public branch hiện hành**, giữ nguyên các khác biệt i18n đó và chạy CI/kiểm lại tại PR; không đẩy nguyên local branch để ghi đè lịch sử. Public-base-check.json giữ proof.

Nếu public branch đổi sau snapshot này, CloudAgent phải kiểm apply/test lại. Bộ format-patch đặt ở `/workspace/osa-ui-shots/ai-native/push/`, gồm ba commit 1d0ce52/adbe518/9f989ec và commit v3 mới. Chỉ xuất sau hai AC/regression PASS; không tự tạo PR hay push từ box.

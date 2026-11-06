# LIVE EVAL: AI Native skills trên OSA

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

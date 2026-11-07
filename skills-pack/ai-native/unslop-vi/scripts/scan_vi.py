#!/usr/bin/env python3
"""Máy quét dấu vết văn AI cho tiếng Việt (unslop-vi).

Chỉ đánh dấu ứng viên theo mã quy tắc trong SKILL.md. Mỗi kết quả vẫn cần
người hoặc mô hình phán đoán theo ngữ cảnh.

Cách dùng:
    python3 scan_vi.py file.md                 # báo cáo
    python3 scan_vi.py -                       # đọc stdin
    python3 scan_vi.py --json file.md          # JSON
    python3 scan_vi.py --compare before.md after.md
    python3 scan_vi.py --max-per-rule 3 file.md
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict

F = re.IGNORECASE | re.UNICODE

# (mã quy tắc, regex, ghi chú). Regex dùng \b; chữ tiếng Việt là \w trong Python.
PATTERNS = [
    # --- Nội dung
    ("3", r",\s*(?:qua đó|từ đó|nhờ đó)?\s*(?:góp phần|khẳng định|thể hiện|phản ánh|minh chứng)\b", "mệnh đề đuôi khoe ý nghĩa"),
    ("3", r"\b(?:qua đó|từ đó)\s+(?:giúp|cho thấy)\b|\bgóp phần\b", "mệnh đề khoe ý nghĩa"),
    ("5", r"\b(?:các|nhiều|một số|giới)\s+(?:chuyên gia|nhà phân tích|nhà nghiên cứu)\s+(?:cho rằng|nhận định|tin rằng|đánh giá|khuyên)", "nguồn mơ hồ"),
    ("5", r"\bnhiều\s+(?:nghiên cứu|khảo sát|báo cáo)\s+(?:đã\s+)?(?:cho thấy|chỉ ra|chứng minh)", "nguồn mơ hồ"),
    ("5", r"\b(?:có ý kiến cho rằng|người ta cho rằng|theo (?:các|một số|nhiều) (?:nguồn|báo cáo|chuyên gia))", "nguồn mơ hồ"),
    ("V1", r"\b(?:trong|ở)\s+(?:thời đại|kỷ nguyên)\s+(?:số|công nghệ(?:\s*4\.0)?|4\.0|hiện đại|ngày nay|chuyển đổi số|toàn cầu hóa|toàn cầu hoá|hội nhập|AI|trí tuệ nhân tạo)", "mở bài rỗng"),
    ("V1", r"\btrong bối cảnh\s+(?:hiện nay|ngày nay|hiện tại)", "mở bài rỗng"),
    ("V1", r"(?:^|[.!?]\s+)ngày nay,", "mở bài rỗng"),
    ("V1", r"\bbạn có (?:bao giờ|từng)\s+(?:tự hỏi|thắc mắc)", "mở bài rỗng"),
    ("V1", r"\btrong bài viết (?:này|dưới đây)", "mở bài rỗng"),
    ("V1", r"\bngày càng trở nên\s+(?:phổ biến|quan trọng|cần thiết)", "mở bài rỗng"),
    # --- Ngôn ngữ
    ("7", r"\bđóng (?:một )?vai trò\s+(?:vô cùng\s+|rất\s+|cực kỳ\s+)?(?:quan trọng|then chốt|trọng yếu|chủ chốt|cốt lõi|thiết yếu)", "từ vựng AI"),
    ("7", r"\b(?:then chốt|cốt lõi|toàn diện|vượt trội|ưu việt|đột phá|bứt phá|nâng tầm|lan tỏa|lan toả|kiến tạo|hiện thực hóa|hiện thực hoá|tối ưu hóa|tối ưu hoá|hệ sinh thái|cách mạng hóa)\b", "từ vựng AI"),
    ("7", r"\bbức tranh\s+(?:toàn cảnh|tổng thể|tổng quan)", "từ vựng AI"),
    ("7", r"\bđa dạng và phong phú|phong phú và đa dạng|\bkhông thể thiếu\b|\bkhông thể phủ nhận\b", "từ vựng AI"),
    ("7", r"\bhành trình\b", "từ vựng AI (nếu nghĩa bóng)"),
    ("7", r"\b(?:khai phá|khai thác tối đa|đánh thức)\s+(?:tiềm năng|sức mạnh)", "từ vựng AI"),
    ("7", r"\b(?:minh chứng|điểm nhấn|không ngừng (?:phát triển|đổi mới|nỗ lực))\b", "từ vựng AI"),
    ("7", r"\b(?:liền mạch|mượt mà)\b", "từ vựng AI (nói số liệu thay vì cảm giác)"),
    ("7", r"\b(?:delve|leverage|pivotal|tapestry|testament|showcase|seamless|robust|cutting-edge|game-changer|synergy|unlock|empower|elevate)\b", "từ vựng AI tiếng Anh"),
    ("8", r"\b(?:đóng vai trò là|được (?:xem|coi) (?:là|như)|tự hào (?:sở hữu|là)|mang trong mình|là một trong những)\b", "nói vòng cho 'là/có'"),
    ("8", r"\bsở hữu\s+(?:nhiều|những|các|một|hệ|tính năng|thiết kế)", "nói vòng cho 'có'"),
    ("9", r"\bkhông (?:chỉ|những|đơn thuần|đơn giản)(?: là)?\b[^.!?\n]{1,80}\b(?:mà )?còn(?: là)?\b", "'không chỉ… mà còn'"),
    ("9", r"\bkhông phải là\b[^.!?\n]{1,60}\bmà là\b", "'không phải… mà là'"),
    ("12", r"\btừ\s+[^,.!?\n]{2,25}\s+(?:đến|cho đến)\s+[^,.!?\n]{2,25},\s*từ\s+", "khoảng giả lặp"),
    # --- Cấu trúc dịch máy
    ("V2", r"\bmột cách\s+\w+", "'một cách + tính từ'"),
    ("V3", r"\bviệc\s+(?:sử dụng|áp dụng|thực hiện|triển khai|xây dựng|phát triển|quản lý|tối ưu|nâng cao)", "danh hóa 'việc'"),
    ("V3", r"\btrong việc\s+\w+", "danh hóa 'trong việc'"),
    ("V3", r"\bsự\s+(?:phát triển|thay đổi|gia tăng|cải thiện|kết hợp|hỗ trợ|tham gia|xuất hiện|đa dạng)\s+của\b", "danh hóa 'sự … của'"),
    ("V4", r"\b(?:được|bị)\s+(?:\w+\s+){0,4}?bởi\b", "bị động dịch thẳng 'được … bởi'"),
    ("V5", r"(?:^|[.!?]\s+)(?:Điều này|Nó|Việc này)\s+(?:cho thấy|giúp|có nghĩa|khiến|đảm bảo|mang lại|là)", "chủ ngữ giả"),
    ("V6", r"(?:^|[.!?]\s+)Với\s+[^,.\n]{1,50},\s*(?:bạn|người dùng|chúng ta|doanh nghiệp|quý khách)", "'Với X, bạn có thể'"),
    ("V6", r"\bkhi (?:nói|nhắc) (?:đến|tới|về)\b", "giới từ dịch thẳng"),
    ("V6", r"\bthông qua việc\b", "giới từ dịch thẳng"),
    ("V6", r"\bcủa\s+[^,.!?\n]{1,25}\s+của\s+[^,.!?\n]{1,25}\s+của\b", "chuỗi 'của'"),
    ("V13", r"\b(?:là|đây là)\s+một\s+(?:công cụ|giải pháp|nền tảng|lựa chọn|phương pháp|ứng dụng|sản phẩm)\s+(?:tuyệt vời|mạnh mẽ|hữu ích|hoàn hảo|lý tưởng|hiệu quả|toàn diện)", "'là một … tuyệt vời'"),
    # --- Chatbot
    ("20", r"\b(?:chắc chắn rồi|tất nhiên rồi|dưới đây là|hy vọng (?:thông tin|bài viết|những chia sẻ|nội dung)\s+(?:này|trên)|đừng ngần ngại|nếu bạn có bất kỳ (?:câu hỏi|thắc mắc)|rất vui được (?:hỗ trợ|giúp)|chúc bạn thành công|hãy cùng (?:tìm hiểu|khám phá))", "câu chatbot"),
    ("22", r"\b(?:câu hỏi (?:rất |thật )?(?:hay|tuyệt vời)|bạn hoàn toàn đúng|ý tưởng (?:rất |thật )?tuyệt vời)", "nịnh"),
    # --- Chữ thừa
    ("23", r"\b(?:nhằm mục đích|với mục đích|để có thể|điều quan trọng (?:cần|là phải) (?:lưu ý|nhớ)|cần lưu ý rằng|một điều đáng chú ý là|trên thực tế|về cơ bản|có thể nói(?: rằng)?|nói một cách khác)\b", "cụm đệm"),
    ("24", r"\b(?:có thể sẽ|có lẽ là|ở một mức độ nào đó|phần nào|tương đối khá|dường như có thể)\b", "rào đón"),
    ("25", r"\b(?:tương lai (?:hứa hẹn|tươi sáng|rộng mở)|hãy bắt đầu (?:ngay )?(?:hôm nay|từ bây giờ)|cuối cùng nhưng không kém phần quan trọng|chắc chắn sẽ mang lại)", "kết luận rỗng"),
    ("25", r"(?:^|\n)\s*(?:tóm lại|nhìn chung|kết luận lại|tổng kết lại),", "kết luận rỗng"),
    ("26", r"\b(?:đòn bẩy|bệ phóng|kim chỉ nam|ngọn hải đăng|mảnh ghép|chìa khóa vàng|là chìa khóa|chìa khoá|nền tảng vững chắc|mở ra (?:cánh cửa|chân trời|kỷ nguyên))\b", "ẩn dụ trừu tượng"),
    ("30", r"\b(?:vô cùng|cực kỳ|cực kì|hết sức|thực sự|thật sự|một cách đáng kể|rõ rệt)\b", "từ cường điệu"),
    ("31", r"\b(?:tiến hành|thực hiện việc|triển khai thực hiện|tạo điều kiện)\b", "từ kiểu cách"),
    ("32", r"\b(?:chạm (?:đến|tới|vào) (?:trái tim|cảm xúc)|viết tiếp câu chuyện|thắp (?:sáng|lửa)|khơi dậy (?:đam mê|tiềm năng)|bản (?:giao hưởng|hòa ca|hoà ca)|dấu ấn (?:khó phai|đậm nét)|làm nên sự khác biệt|chinh phục)\b", "văn kiểu cách"),
    ("V8", r"\b(?:mang tính|có tính)\s+(?:chiến lược|đột phá|ứng dụng|thời sự|cách mạng|nhân văn)", "Hán Việt khoa trương"),
    # --- Trình bày
    ("V12", r"\S\s+[,.;:!?](?=\s|$)", "khoảng trắng trước dấu câu"),
    ("V12", r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", "số kiểu Anh (VN: 1.000,5)"),
    ("V12", r"\$\s?\d", "ký hiệu tiền đứng trước số"),
]

TRANSITIONS = r"^(?:bên cạnh đó|ngoài ra|hơn nữa|hơn thế nữa|đặc biệt|không chỉ vậy|thêm vào đó|đồng thời|mặt khác)\b"
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728]")
COMPILED = [(r, re.compile(p, F), n) for r, p, n in PATTERNS]


def strip_protected(text):
    """Thay khối mã, mã nội dòng, trích dẫn khối bằng dòng trống (giữ số dòng)."""
    out, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence or line.lstrip().startswith(">"):
            out.append("")
            continue
        out.append(re.sub(r"`[^`]*`", " ", line))
    return out


def count_words(lines):
    return sum(len(re.findall(r"\w+", l)) for l in lines)


def scan(text, max_per_rule=8):
    text = unicodedata.normalize("NFC", text)
    lines = strip_protected(text)
    hits = []

    def add(rule, ln, excerpt, note):
        hits.append({"rule": rule, "line": ln, "excerpt": excerpt.strip()[:90], "note": note})

    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        for rule, rx, note in COMPILED:
            for m in rx.finditer(line):
                s = max(0, m.start() - 15)
                add(rule, i, line[s:m.end() + 15], note)
        stripped = line.strip()
        # 17: tiêu đề viết hoa kiểu Anh
        if stripped.startswith("#"):
            words = re.findall(r"[^\W\d_]+", stripped.lstrip("#"))
            if len(words) >= 3:
                caps = sum(1 for w in words[1:] if w[0].isupper())
                if caps / (len(words) - 1) >= 0.6:
                    add("17", i, stripped, "tiêu đề viết hoa mỗi chữ")
        # 18: emoji trong tiêu đề hoặc gạch đầu dòng
        if (stripped.startswith("#") or re.match(r"^[-*+]\s", stripped)) and EMOJI.search(stripped):
            add("18", i, stripped, "emoji trang trí")
        # 16: nhãn in đậm có dấu hai chấm
        if re.match(r"^(?:[-*+]|\d+\.)?\s*(?:\S\s+)?\*\*[^*]{1,40}(?::\*\*|\*\*\s*:)", stripped):
            add("16", i, stripped, "danh sách nhãn in đậm")
        # 13: gạch ngang giữa câu (không phải đầu dòng hội thoại, không phải khoảng số)
        dialogue = re.match(r"^\s*[–—]", line) is not None
        body = re.sub(r"^\s*[–—-]\s*", "", line)
        for m in ([] if dialogue else re.finditer(r"(?<!\d)\s[—–]\s(?!\d)|\w—\w", body)):
            add("13", i, body[max(0, m.start() - 20):m.end() + 20], "gạch ngang nối ý")
        # 14: dấu hai chấm giữa câu, không đứng cuối dòng, không trước danh sách
        for m in re.finditer(r"\w:\s+[a-zà-ỹ]", stripped):
            if not stripped.startswith(("-", "*", "#")) and not re.match(r"^\*\*", stripped):
                add("14", i, stripped[max(0, m.start() - 25):m.end() + 25], "dấu hai chấm nối câu")
        # 28: câu quá dài
        for sent in re.split(r"(?<=[.!?])\s+", stripped):
            n = len(re.findall(r"\w+", sent))
            if n > 45:
                add("28", i, sent[:80] + "…", f"câu dài {n} chữ")
        # V7: từ nối đầu đoạn
        for sent in re.split(r"(?<=[.!?])\s+", stripped):
            if re.match(TRANSITIONS, sent, F):
                add("V7", i, sent[:60], "từ nối đầu câu/đoạn")

    # 15: mật độ in đậm
    words = count_words(lines)
    bold = len(re.findall(r"\*\*[^*]+\*\*", "\n".join(lines)))
    if words and bold / words * 100 > 3:
        add("15", 0, f"{bold} cụm in đậm / {words} chữ", "lạm dụng in đậm")
    # 19: trộn ngoặc thẳng và cong
    joined = "\n".join(lines)
    if re.search(r"[“”]", joined) and re.search(r'"', joined):
        add("19", 0, "có cả “ ” và \"", "ngoặc kép không nhất quán")
    # V10: xưng hô lệch, lạm dụng "Hãy"
    pronouns = [p for p in ("bạn", "chúng ta", "quý khách", "các bạn") if re.search(rf"\b{p}\b", joined, F)]
    if len(pronouns) >= 2 and not (set(pronouns) <= {"bạn", "các bạn"}):
        add("V10", 0, ", ".join(pronouns), "trộn ngôi xưng hô")
    hay = len(re.findall(r"(?:^|[.!?]\s+)Hãy\b", joined))
    if hay >= 3:
        add("V10", 0, f"{hay} câu mở bằng 'Hãy'", "lạm dụng câu mệnh lệnh")
    # V7 tổng: nhiều đoạn mở bằng từ nối
    # 11 (gợi ý): xoay vòng đồng nghĩa người dùng
    syn = [s for s in ("người dùng", "khách hàng", "người sử dụng", "user") if re.search(rf"\b{s}\b", joined, F)]
    if len(syn) >= 3:
        add("11", 0, ", ".join(syn), "có thể đang xoay vòng từ đồng nghĩa")

    # gom và cắt theo max_per_rule
    by_rule = defaultdict(list)
    for h in hits:
        by_rule[h["rule"]].append(h)
    total = len(hits)
    density = round(total / words * 1000, 1) if words else 0.0
    level = "sạch" if density < 5 else "nhẹ" if density < 15 else "nặng"
    return {
        "words": words,
        "total_hits": total,
        "per_1000_words": density,
        "level": level,
        "by_rule": {r: {"count": len(v), "hits": v[:max_per_rule]} for r, v in sorted(by_rule.items(), key=lambda kv: -len(kv[1]))},
    }


def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def print_report(res, name=""):
    head = f"== {name}" if name else "=="
    print(f"{head} {res['words']} chữ | {res['total_hits']} dấu hiệu | {res['per_1000_words']}/1.000 chữ | mức: {res['level']}")
    for rule, data in res["by_rule"].items():
        print(f"\n[{rule}] x{data['count']}")
        for h in data["hits"]:
            loc = f"dòng {h['line']}" if h["line"] else "toàn văn"
            print(f"  {loc}: {h['excerpt']}  ({h['note']})")
        if data["count"] > len(data["hits"]):
            print(f"  … và {data['count'] - len(data['hits'])} chỗ khác")


def main():
    ap = argparse.ArgumentParser(description="Quét dấu vết văn AI tiếng Việt theo mã quy tắc unslop-vi.")
    ap.add_argument("files", nargs="*", help="file cần quét, '-' để đọc stdin")
    ap.add_argument("--json", action="store_true", help="xuất JSON")
    ap.add_argument("--compare", nargs=2, metavar=("TRUOC", "SAU"), help="so sánh hai bản")
    ap.add_argument("--max-per-rule", type=int, default=8)
    a = ap.parse_args()

    if a.compare:
        before, after = (scan(read(p), a.max_per_rule) for p in a.compare)
        if a.json:
            print(json.dumps({"before": before, "after": after}, ensure_ascii=False, indent=2))
            return
        print(f"Trước: {before['total_hits']} dấu hiệu, {before['per_1000_words']}/1.000 chữ ({before['level']}), {before['words']} chữ")
        print(f"Sau:   {after['total_hits']} dấu hiệu, {after['per_1000_words']}/1.000 chữ ({after['level']}), {after['words']} chữ")
        if before["words"]:
            print(f"Độ dài: {round((after['words'] - before['words']) / before['words'] * 100)}%")
        left = {r: d["count"] for r, d in after["by_rule"].items()}
        if left:
            print("Còn lại theo mã: " + ", ".join(f"{r}×{c}" for r, c in left.items()))
            print_report(after, "Chi tiết bản sau")
        return

    if not a.files:
        ap.error("cần ít nhất một file hoặc '-'")
    results = {p: scan(read(p), a.max_per_rule) for p in a.files}
    if a.json:
        print(json.dumps(results if len(results) > 1 else next(iter(results.values())), ensure_ascii=False, indent=2))
    else:
        for p, r in results.items():
            print_report(r, p if len(results) > 1 else "")


if __name__ == "__main__":
    main()

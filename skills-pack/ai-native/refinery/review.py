#!/usr/bin/env python3
"""review.py · Công cụ duyệt thủ công các claim từ staging.jsonl sang claims.jsonl.

Các claim nháp lưu tại <domain_dir>/staging.jsonl (đã có evidence_span và snapshot nhưng chờ
con người kiểm tra ngữ cảnh). Khi được duyệt (approve), claim được gắn human_verified=True,
verified_by=<tên người duyệt> và chuyển vào claims.jsonl.

  python3 review.py <domain_name_or_path> list
  python3 review.py <domain_name_or_path> approve <idx> --by "Tên người duyệt"
  python3 review.py <domain_name_or_path> reject  <idx>
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _resolve_domain(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        return p
    cand = HERE / "domains" / arg
    if cand.is_dir():
        return cand
    sys.exit(f"Không tìm thấy thư mục domain: {arg}")


def _load(p: Path):
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8").strip()
    if not txt:
        return []
    return json.loads(txt) if txt.startswith("[") else [json.loads(l) for l in txt.splitlines() if l.strip()]


def _write(p: Path, rows):
    if p.suffix == ".json":
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Quản lý hàng đợi duyệt claim (staging.jsonl -> claims.jsonl)")
    ap.add_argument("domain", help="Tên domain trong domains/ hoặc đường dẫn tới thư mục domain")
    ap.add_argument("cmd", choices=["list", "approve", "reject"])
    ap.add_argument("idx", nargs="?", type=int)
    ap.add_argument("--by", default="")
    a = ap.parse_args()

    d = _resolve_domain(a.domain)
    stag = d / ("staging.json" if (d / "staging.json").exists() else "staging.jsonl")
    claims = d / ("claims.json" if (d / "claims.json").exists() or not (d / "claims.jsonl").exists() else "claims.jsonl")
    rows = _load(stag)

    if a.cmd == "list":
        if not rows:
            print(f"staging ({d.name}): rỗng (0 claim chờ duyệt)")
            return
        print(f"staging ({d.name}): {len(rows)} claim chờ kiểm tra ngữ cảnh")
        for i, c in enumerate(rows):
            cap = c.get("capture") or {}
            print(f"  [{i}] {str(c.get('entity','?'))[:52]} · {c.get('field')} = {str(c.get('value'))[:38]!r}")
            print(f"      span={str(c.get('evidence_span'))[:64]!r} · tier {c.get('tier')} · snap {cap.get('snapshot')}")
        return

    if a.idx is None or not (0 <= a.idx < len(rows)):
        sys.exit("Chỉ số idx không hợp lệ (chạy lệnh 'list' để xem danh sách)")
    c = rows.pop(a.idx)
    if a.cmd == "approve":
        if not a.by.strip():
            sys.exit("Lệnh approve bắt buộc kèm --by \"Tên người duyệt\"")
        c["human_verified"] = True
        c["verified_by"] = a.by.strip()
        cl = _load(claims)
        cl.append(c)
        _write(claims, cl)
        print(f"✓ ĐÃ DUYỆT [{a.idx}] → claims.jsonl · verified_by={c['verified_by']!r} · còn {len(rows)} trong staging")
    else:
        print(f"✗ ĐÃ LOẠI [{a.idx}] khỏi staging · còn {len(rows)}")
    _write(stag, rows)


if __name__ == "__main__":
    main()

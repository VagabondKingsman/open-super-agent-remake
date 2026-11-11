"""Đo cái giá của `reasoning_effort` trên router: cùng câu hỏi, cùng model, khác mức suy luận.

Chạy:  .venv/bin/python scripts/effort_ab.py            # 3 mức × 5 câu
       .venv/bin/python scripts/effort_ab.py --n 3      # ít câu hơn cho rẻ

In ra một bảng: chữ đầu *trả lời* (ttfa), chữ đầu *suy luận* (ttr), tổng thời gian, token, $.
Ghi kết quả vào osa-data/effort-ab.json để dẫn lại được trong docs. Không gọi tool, không đụng DB.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from osa import providers  # noqa: E402
from osa.config import CFG  # noqa: E402

QUESTIONS = [
    ("math", "17*23 bằng bao nhiêu? Trả lời đúng một con số."),
    ("math2", "Tính 99**3 giúp mình. Trả lời đúng một con số."),
    ("why", "Giải thích trong 3 câu vì sao một SSE stream có thể im lặng 120 giây rồi vẫn trả lời đúng."),
    ("code", "Viết hàm Python `count_items(path)` đọc file JSON và trả về số phần tử, xử lý file lỗi. Chỉ đưa code."),
    ("nuance", "Task chạy 8 bước, mỗi bước in 150 dòng; worker chỉ giữ 3 bước gần nhất. Nếu model cần nhớ bước 1 để "
               "trả lời thì phải gửi lại gì, và tại sao? Trả lời ngắn."),
]

PROVIDER = os.environ.get("OSA_AB_PROVIDER", "xai")
MODEL = os.environ.get("OSA_AB_MODEL", "grok-4.7")
SYSTEM = "Bạn là trợ lý của Open Super Agent. Trả lời ngắn gọn, đúng, bằng tiếng Việt."


def configs() -> list[tuple[str, dict]]:
    """Ba mức suy luận trên cùng model. Mức đầu là mức production đang chạy (settings.overrides)."""
    return [("high (đang chạy)", {"reasoning_effort": "high"}),
            ("medium", {"reasoning_effort": "medium"}),
            ("tắt thinking", {"extra_body": {"thinking": {"type": "disabled"}}})]


async def one(client, model: str, q: str, kw: dict) -> dict:
    t0 = time.monotonic()
    stream = await providers.create_chat(client, model=model, messages=[
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": q}],
        stream=True, stream_options={"include_usage": True}, **kw)
    ttfa = ttr = total = None
    shown, reasoning, usage, err = "", "", None, ""
    try:
        async for ch in providers.guard_stream(stream):
            total = time.monotonic() - t0
            if getattr(ch, "usage", None):
                usage = ch.usage
            for d in (getattr(ch, "choices", None) or []):
                dd = getattr(d, "delta", None)
                rc = getattr(dd, "reasoning_content", None)
                if rc and ttr is None:
                    ttr = total
                c = getattr(dd, "content", None)
                if c:
                    if ttfa is None:
                        ttfa = total
                    shown += c
                if rc:
                    reasoning += rc
    except Exception as e:   # noqa: BLE001 — đo, không được chết giữa bảng
        err = f"{type(e).__name__}: {e}"[:160]
        total = time.monotonic() - t0
    hit = miss = out = 0
    if usage:
        hit = int((getattr(usage, "prompt_tokens_details", None) and usage.prompt_tokens_details.cached_tokens) or 0)
        miss = max(0, int(usage.prompt_tokens or 0) - hit)
        out = int(usage.completion_tokens or 0)
    return {"ttfa": ttfa, "ttr": ttr, "total": total, "hit": hit, "miss": miss, "out": out,
            "cost": _cost(model, hit, miss, out), "err": err,
            "answer": shown.strip()[:400], "reasoning_len": len(reasoning)}


async def main(n: int) -> None:
    client = providers.client(PROVIDER)
    model = MODEL
    rows = []
    for label, kw in configs():
        for qid, q in QUESTIONS[:n]:
            r = await one(client, model, q, kw)
            r |= {"config": label, "q": qid}
            rows.append(r)
            print(f"{label:14s} {qid:7s} ttfa={_s(r['ttfa']):>6s} ttr={_s(r['ttr']):>6s} "
                  f"tot={_s(r['total']):>6s} out={r['out']:>5d} ${r['cost']:.4f} {r['err']}", flush=True)
    print()
    print(f"{'config':14s} {'ttfa(s)':>8s} {'ttr(s)':>7s} {'total(s)':>9s} {'out tok':>8s} {'$':>8s}")
    for label, _ in configs():
        rs = [r for r in rows if r["config"] == label]
        print(f"{label:14s} {_avg([r['ttfa'] for r in rs]):>8s} {_avg([r['ttr'] for r in rs]):>7s} "
              f"{_avg([r['total'] for r in rs]):>9s} {sum(r['out'] for r in rs) / len(rs):>8.0f} "
              f"{sum(r['cost'] for r in rs) / len(rs):>8.4f}")
    out = Path.home() / "osa-data" / "effort-ab.json"
    out.write_text(json.dumps({"model": model, "ts": time.time(), "rows": rows}, ensure_ascii=False, indent=1))
    print(f"\n→ {out}")


def _cost(model: str, hit: int, miss: int, out: int) -> float:
    """Giá từ bảng đã tải (model-prices.json, dạng gọn i/o/c: $ mỗi triệu token). Không có thì 0."""
    try:
        f = Path.home() / "osa-data" / "model-prices.json"
        pr = json.loads(f.read_text())["providers"][PROVIDER]["models"][model]
        return (miss * pr.get("i", 0) + hit * pr.get("c", 0) + out * pr.get("o", 0)) / 1e6
    except Exception:   # noqa: BLE001
        return 0.0


def _s(v) -> str:
    return "—" if v is None else f"{v:.2f}"


def _avg(vs) -> str:
    xs = [v for v in vs if v is not None]
    return f"{sum(xs) / len(xs):.2f}" if xs else "—"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=len(QUESTIONS), help="số câu đầu tiên của QUESTIONS")
    a = ap.parse_args()
    asyncio.run(main(a.n))

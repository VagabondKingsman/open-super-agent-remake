#!/usr/bin/env python
"""How long does the model really stay silent mid-stream? (llm_calls.silence_ms)

The stall guard closes a stream after limits.stream_idle_s (120 s) of silence and retries.
Whether that number is too tight or too loose was a guess until every call started recording
its longest gap. This prints the distribution, per role, and the calls that hit the limit.

    .venv/bin/python scripts/silence_stats.py [days]
"""
import sqlite3
import sys
from pathlib import Path

days = float(sys.argv[1]) if len(sys.argv) > 1 else 7
db = sqlite3.connect(Path(__file__).resolve().parents[1].parent / "osa-data" / "osa.db")
db.row_factory = sqlite3.Row
since = f"strftime('%s','now') - {days} * 86400"

rows = db.execute(f"""select role, count(*) n, sum(silence_ms is not null) with_silence,
    sum(err is not null and err != '') errs
    from llm_calls where ts > {since} group by role order by n desc""").fetchall()
print(f"last {days:g} days")
for r in rows:
    sil = [x[0] for x in db.execute(
        f"select silence_ms from llm_calls where role=? and silence_ms is not null and ts > {since} "
        f"order by silence_ms", (r["role"],))]
    if not sil:
        print(f"  {r['role']:8} n={r['n']:4}  errs={r['errs']:2}  (no silence recorded yet)")
        continue
    def q(p):
        return sil[min(len(sil) - 1, int(p * (len(sil) - 1)))] / 1000
    print(f"  {r['role']:8} n={r['n']:4}  errs={r['errs']:2}  silence med {q(.5):6.1f}s "
          f"p90 {q(.9):6.1f}s p99 {q(.99):6.1f}s max {sil[-1]/1000:6.1f}s  ({len(sil)} measured)")

print("\ncalls within 30 s of the limit (the margin left to tune):")
for x in db.execute(f"""select id, datetime(ts,'unixepoch','localtime') t, role, model, silence_ms, ms,
    coalesce(err,'') e from llm_calls where silence_ms is not null and ts > {since}
    order by silence_ms desc limit 8"""):
    print(f"  #{x['id']:<5} {x['t']} {x['role']:7} {x['model']:22} silence {x['silence_ms']/1000:6.1f}s "
          f"total {x['ms']/1000:6.1f}s {x['e'][:60]}")

"""Gửi một câu vào một chat và in câu trả lời đầu tiên (đo tay, không phải probe cố định).

    .venv/bin/python scripts/ask.py <chat_id> <tag> "<câu hỏi>"
"""
import asyncio, http.cookiejar, json, re, sqlite3, sys, time, urllib.parse, urllib.request, websockets

chat, tag, text = int(sys.argv[1]), sys.argv[2], sys.argv[3]
BASE = 'http://127.0.0.1:8765'
db = sqlite3.connect('file:/home/boxes/osa-data/osa.db?mode=ro', uri=True, timeout=10)
pw = [l.split('=', 1)[1].strip() for l in open('/home/boxes/osa/.env') if l.startswith('OSA_PASSWORD=')][0]
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(BASE + '/login', urllib.parse.urlencode({'password': pw}).encode())
ck = '; '.join(c.name + '=' + c.value for c in cj)


async def main():
    op.open(urllib.request.Request(BASE + f'/api/chats/{chat}/reset', data=b'{}',
                                   headers={'Content-Type': 'application/json', 'Cookie': ck})).read()
    await asyncio.sleep(1)
    m = db.execute('select coalesce(max(id),0) from messages where chat_id=?', (chat,)).fetchone()[0]
    async with websockets.connect('ws://127.0.0.1:8765/ws', additional_headers={'Cookie': ck}, open_timeout=20) as ws:
        await ws.send(json.dumps({'type': 'send', 'chat_id': chat, 'text': text, 'attachments': []}))
    end = time.monotonic() + 600
    while time.monotonic() < end:
        await asyncio.sleep(2)
        db.rollback()
        row = db.execute("select id, content from messages where chat_id=? and id>? and role='assistant' order by id limit 1",
                         (chat, m)).fetchone()
        if row and (row[1] or '').strip():
            open(f'/tmp/r-{tag}.txt', 'w').write(row[1])
            print(f"{tag}: id={row[0]} len={len(row[1])} code={'```' in row[1][:600]} "
                  f"head={row[1][:60]!r}")
            return
    print(f'{tag}: TIMEOUT')

asyncio.run(main())

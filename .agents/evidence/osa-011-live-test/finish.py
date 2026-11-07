# Reference harness that polled task 79 after the early websocket stop.
# OSA_PASSWORD is read from the environment. Do not write the value here.
import os,asyncio,json,pathlib,time,sqlite3,httpx,re
P=pathlib.Path('/workspace/osa-run/osa011')
async def main():
 async with httpx.AsyncClient(base_url='http://127.0.0.1:8765',headers={'Origin':'http://127.0.0.1:8765'}) as h:
  await h.post('/login',data={'password':os.environ['OSA_PASSWORD']})
  for _ in range(120):
   d=(await h.get('/api/tasks/79')).json()
   if d['task']['status']!='running':break
   await asyncio.sleep(2)
  (P/'raw/heavy-final.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
  c=sqlite3.connect('/workspace/osa-run/osa.db');c.row_factory=sqlite3.Row
  first=min(x['rid'] for x in json.loads((P/'raw/usage.json').read_text()))
  u=[dict(x) for x in c.execute('select rowid rid,* from llm_usage where rowid>=?',(first,))];(P/'raw/usage-final.json').write_text(json.dumps(u,indent=2))
  print(json.dumps({'task':d['task'],'tokens':sum(x['cache_hit']+x['cache_miss']+x['output'] for x in u),'calls':len(u),'cost':sum(x['cost'] for x in u)},ensure_ascii=False))
asyncio.run(main())

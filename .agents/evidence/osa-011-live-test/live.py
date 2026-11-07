# Reference harness from the OSA-011 live smoke. Paths belong to that box.
# OSA_PASSWORD is read from the environment. Do not write the value here.
import os,json,asyncio,time,re,sqlite3,pathlib
import httpx,websockets
P=pathlib.Path('/workspace/osa-run/osa011');BASE='http://127.0.0.1:8765'
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def usage():
 c=sqlite3.connect('/workspace/osa-run/osa.db');c.row_factory=sqlite3.Row
 r=[dict(x) for x in c.execute('select rowid as rid,* from llm_usage')];c.close();return r
async def main():
 async with httpx.AsyncClient(base_url=BASE,headers={'Origin':BASE},timeout=30) as h:
  pre={}
  for path in ['/','/api/settings','/login']:
   r=await h.get(path);pre[path]=r.status_code
  assert os.environ.get('OSA_PASSWORD'),'missing password env'
  r=await h.post('/login',data={'password':os.environ['OSA_PASSWORD']});pre['login_post']=r.status_code
  r=await h.get('/');pre['authenticated_root']=r.status_code;pre['spa']='index-EeqJurSD.js' in r.text
  r=await h.get('/api/settings');r.raise_for_status();s=r.json();save('raw/settings.json',{k:s.get(k) for k in ['language','roles','limits','heavy_workers']})
  save('raw/preflight.json',pre);assert pre['login_post']==303 and pre['authenticated_root']==200
  assert all(x.get('model','').endswith(':free') for x in s['roles'].values()),'non-free model'
  cookies='; '.join(f'{k}={v}' for k,v in h.cookies.items())
  initial=usage();row0=max([r['rid'] for r in initial]+[0]);events=[];stop=False
  async with websockets.connect('ws://127.0.0.1:8765/ws',origin=BASE,additional_headers={'Cookie':cookies},max_size=16000000) as ws:
   async def collect():
    nonlocal stop
    async for raw in ws:
     d=json.loads(raw);events.append(d)
     if re.search(r'402|429|insufficient_quota|free_limit_reached|org_token_rate_limit_day',raw):stop=True
     if d.get('type')=='approval' and d.get('status')=='pending':
      await ws.send(json.dumps({'type':'approve','id':d['id'],'ok':False}))
   col=asyncio.create_task(collect());results=[]
   cases=[('vi','Chào bạn, nói một câu ngắn về việc đọc sách. Không dùng công cụ.'),('en','Hello! In one short sentence, explain why sleep matters. Do not use tools.'),('single','Hãy dispatch đúng một task mode single: nghiên cứu bằng kiến thức sẵn có, không web hay công cụ ngoài, so sánh SQLite và PostgreSQL cho ứng dụng cá nhân, kết luận trong 80 từ. Đây là bài kiểm thử worker; không tự trả lời thay worker.'),('heavy','Hãy dispatch đúng một task mode heavy để cân nhắc SQLite và PostgreSQL cho ứng dụng cá nhân. Mỗi góc nhìn tối đa 50 từ, kết luận cuối tối đa 80 từ. Không web, không ghi file, không công cụ ngoài. Chỉ một heavy task, không tạo thêm task.'),('routine','Liệt kê routine hiện có của bạn và mô tả ngắn bằng tiếng Việt. Không tạo, sửa, chạy hay xóa routine.')]
   try:
    for name,prompt in cases:
     if stop:break
     if sum(r.get('input',0)+r.get('output',0) for r in usage() if r['rid']>row0)>85000:break
     r=await h.post('/api/bots',json={'name':'OSA011 smoke '+name,'instructions':''});r.raise_for_status();bot=r.json();cid=bot['chat_id'];start=time.monotonic();e0=len(events);tasks=[];terminal=None
     await ws.send(json.dumps({'type':'send','chat_id':cid,'text':prompt}))
     while time.monotonic()-start<240:
      await asyncio.sleep(1)
      ts=(await h.get('/api/tasks')).json();tasks=[(await h.get('/api/tasks/'+str(t['id']))).json() for t in ts if t['bot_id']==bot['id']]
      mine=[e for e in events[e0:] if e.get('chat_id')==cid]
      replies=[e.get('message',{}) for e in mine if e.get('type')=='message' and e.get('message',{}).get('role')=='assistant']
      if stop:break
      if tasks and all(t['task']['status']!='running' for t in tasks):
       if terminal is None:terminal=time.monotonic()
       if time.monotonic()-terminal>4:break
      if not tasks and replies:break
     messages=(await h.get(f'/api/chats/{cid}/messages')).json()
     out={'name':name,'prompt':prompt,'bot_id':bot['id'],'chat_id':cid,'seconds':round(time.monotonic()-start,2),'tasks':tasks,'messages':messages,'events':events[e0:],'stop':stop}
     save('raw/'+name+'.json',out)
     seq=messages if isinstance(messages,list) else messages.get('messages',[])
     text='\n'.join(str(m.get('content',m.get('text',''))) for m in seq if m.get('role')=='assistant')
     result={'name':name,'seconds':out['seconds'],'cjk':len(re.findall('[\u4e00-\u9fff]',text)),'reply':text,'tasks':[{k:t['task'].get(k) for k in ['id','mode','status','result']} for t in tasks],'stop':stop};results.append(result);save('results.json',results);print(json.dumps(result,ensure_ascii=False),flush=True)
     if stop:break
   finally:
    col.cancel();save('raw/events.json',events);save('raw/usage.json',[r for r in usage() if r['rid']>row0])
asyncio.run(main())

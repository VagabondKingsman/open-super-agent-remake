import { useEffect, useState } from 'react'
import { api, setSettings, useStore } from '../store'
import { Icon } from '../icons'
import type { Rule, Settings as S } from '../types'
import Backup from './Backup'
import Channels from './Channels'
import ModelSettings, { ROLE_NAMES } from './ModelSettings'
import { priceSource, priceText, ToastHost, useToast } from './settingsKit'
import i18n, { LOCALES, setLocale, dateLocale, type LocaleCode } from '../i18n'

// 设置：左边按类分组的导航，右边是这一页
const GROUPS: () => { name: string; items: [string, string, string][] }[] = () => ([
  { name: i18n.t('模型与费用'), items: [['models', i18n.t('模型'), 'sparkles'], ['usage', i18n.t('费用'), 'coins'], ['limits', i18n.t('限制与预算'), 'gauge']] },
  { name: i18n.t('安全'), items: [['rules', i18n.t('确认规则'), 'shield'], ['vault', i18n.t('保险库'), 'key']] },
  { name: i18n.t('连接'), items: [['channels', i18n.t('聊天软件'), 'message'], ['notify', i18n.t('通知'), 'bell']] },
  { name: i18n.t('数据'), items: [['triggers', i18n.t('定时任务'), 'clock'], ['backup', i18n.t('备份与迁移'), 'archive']] },
  { name: i18n.t('界面'), items: [['language', i18n.t('语言'), 'globe']] },
])
const TITLES = () => (Object.fromEntries(GROUPS().flatMap(g => g.items.map(([k, v]) => [k, v]))))
const DESC: () => Record<string, string> = () => ({
  language: i18n.t('界面显示语言。改完立即生效，也会同步给服务器（提示词与应用目录）。'),
  models: i18n.t('Bot 用哪些大模型。先添加模型服务，再给每项工作选一个模型。'),
  usage: i18n.t('花了多少钱：按天、按用途、按任务统计。'),
  limits: i18n.t('防止任务跑太久、花太多。改完离开输入框就保存。'),
  triggers: i18n.t('所有 Bot 的定时任务一览。'),
})
const LIMIT_NAMES: () => Record<string, [string, string]> = () => ({
  daily_token_budget: [i18n.t('每天最多用多少 token'), i18n.t('超过以后不再派新的任务，第二天恢复')],
  worker_max_steps: [i18n.t('每个任务最多走几步'), i18n.t('一步 = 一次模型调用。电脑操作一步一个动作，要多给一些')],
  task_timeout_s: [i18n.t('任务最长跑多久（秒）'), i18n.t('超时后 Watchdog 自动取消')],
  approval_timeout_s: [i18n.t('后台任务等确认多久（秒）'), i18n.t('定时任务等你确认的时限，超时按拒绝处理')],
})

export default function Settings({ onClose, initial }: { onClose: () => void; initial?: string }) {
  const [tab, setTab] = useState(() => initial || localStorage.getItem('osa.settings') || 'models')
  const auth = useStore(s => s.auth)
  useEffect(() => localStorage.setItem('osa.settings', tab), [tab])
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onClose])
  const title = TITLES()[tab] ? tab : 'models'
  return (
    <div className="modal-bg" onMouseDown={onClose}>
      <div className="modal set-modal" onMouseDown={e => e.stopPropagation()}>
        <ToastHost>
          <nav className="set-nav">
            <div className="set-nav-title">{i18n.t('设置')}</div>
            {GROUPS().map(g => (
              <div key={g.name} className="set-group">
                <div className="set-group-name">{g.name}</div>
                {g.items.map(([k, v, icon]) => (
                  <button key={k} className={'set-item' + (title === k ? ' on' : '')} onClick={() => setTab(k)}><Icon name={icon} />{v}</button>))}
              </div>))}
            <span className="grow" />
            <button className="set-item" onClick={() => window.dispatchEvent(new CustomEvent('osa-onboarding'))}><Icon name="sparkles" />{i18n.t('新手引导')}</button>
            {auth && <form method="post" action="/logout"><button className="set-item" type="submit"><Icon name="logout" />{i18n.t('退出登录')}</button></form>}
          </nav>
          <div className="set-main">
            <div className="set-head">
              <div><h2>{TITLES()[title]}</h2>{DESC()[title] && <p>{DESC()[title]}</p>}</div>
              <button className="icon-btn" title={i18n.t('关闭（Esc）')} onClick={onClose}><Icon name="x" size={18} /></button>
            </div>
            <div className="set-body">
              {title === 'models' && <ModelSettings />}
              {title === 'limits' && <Limits />}
              {title === 'usage' && <Usage />}
              {title === 'rules' && <Rules />}
              {title === 'vault' && <Vault />}
              {title === 'triggers' && <Triggers />}
              {title === 'channels' && <Channels />}
              {title === 'notify' && <Notifications />}
              {title === 'backup' && <Backup />}
              {title === 'language' && <LanguagePanel />}
            </div>
          </div>
        </ToastHost>
      </div>
    </div>
  )
}

function Limits() {
  const s = useStore(x => x.settings) as S
  const toast = useToast()
  const [lim, setLim] = useState(s.limits)
  const [heavy, setHeavy] = useState(s.heavy_workers)
  const save = async (body: object) => {
    try { setSettings(await api('/api/settings', { method: 'PUT', body })); toast(i18n.t('已保存，马上生效')) }
    catch (e: any) { toast(e.message, true) }
  }
  return (
    <div className="set-rows">
      {Object.entries(LIMIT_NAMES()).map(([k, [name, hint]]) => (
        <label key={k} className="set-row">
          <span><b>{name}</b><span>{hint}</span></span>
          <input type="number" min={1} value={lim[k] ?? ''} onChange={e => setLim({ ...lim, [k]: Number(e.target.value) })}
            onBlur={() => { if (lim[k] && lim[k] !== s.limits[k]) save({ limits: { [k]: lim[k] } }) }} />
        </label>))}
      <label className="set-row">
        <span><b>{i18n.t('Heavy 模式同时跑几个任务')}</b><span>{i18n.t('同一个问题交给几个后台任务分头做，再汇总。越多越全面，也越贵（1–8）')}</span></span>
        <input type="number" min={1} max={8} value={heavy} onChange={e => setHeavy(Number(e.target.value))}
          onBlur={() => { if (heavy && heavy !== s.heavy_workers) save({ heavy_workers: heavy }) }} />
      </label>
    </div>
  )
}

function Usage() {
  const [u, setU] = useState<any>(null)
  const bots = useStore(x => x.bots)
  useEffect(() => { api('/api/usage').then(setU); const t = setInterval(() => api('/api/usage').then(setU), 8000); return () => clearInterval(t) }, [])
  if (!u) return <div className="muted">{i18n.t('加载中…')}</div>
  const f = (v: number) => u.currency + v.toFixed(v < 1 ? 3 : 2)
  const max = Math.max(...u.by_day.map((d: any) => d.cost), 1e-9)
  return (
    <div className="usage">
      <div className="stat-row">
        <div className="stat"><div className="muted small">{i18n.t('今天')}</div><div className="big">{f(u.today.cost)}</div><div className="muted small">{i18n.t("{{v0}} 次调用 · 缓存命中 {{v1}}%", { v0: u.today.calls, v1: (u.today.cache_rate * 100).toFixed(0) })}</div></div>
        <div className="stat"><div className="muted small">{i18n.t('近 7 天')}</div><div className="big">{f(u.week.cost)}</div></div>
        <div className="stat"><div className="muted small">{i18n.t('近 30 天')}</div><div className="big">{f(u.month.cost)}</div></div>
      </div>
      <h4>{i18n.t('近 30 天每日')}</h4>
      <div className="bars">{u.by_day.map((d: any) => <div key={d.day} title={`${d.day}  ${f(d.cost)}`} style={{ height: `${Math.max(2, (d.cost / max) * 100)}%` }} />)}</div>
      <div className="two-col">
        <div><h4>{i18n.t('按用途')}</h4>{u.by_role.map((r: any) => <div className="kv" key={r.role + r.model}><span>{ROLE_NAMES()[r.role] || r.role} · {r.model}</span><span>{f(r.cost)}</span></div>)}</div>
        <div><h4>{i18n.t('按任务（最近 20 个）')}</h4>{u.by_task.map((t: any) => <div className="kv" key={t.id}><span>#{t.id} {t.goal}</span><span>{f(t.cost)}</span></div>)}</div>
      </div>
      <Prices />
      <p className="muted small">{i18n.t('{{v0}} 个 Bot 共用一个每日预算，在“限制与预算”里改。', { v0: bots.length })}</p>
    </div>
  )
}

// 现在用的模型的单价，从哪来的；models.dev 每天自动更新
function Prices() {
  const s = useStore(x => x.settings) as S
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const p = s.prices
  const rows = [...Object.entries(s.roles).map(([k, v]) => [k, v.provider, v.model]),
    ...(s.embedding.provider ? [['embedding', s.embedding.provider, s.embedding.model]] : [])]
  const refresh = async () => {
    setBusy(true)
    try { const r = await api('/api/prices/refresh', { method: 'POST' }); setSettings(r.settings); toast(r.error ? i18n.t('更新失败：{{v0}}', { v0: r.error }) : i18n.t('单价已更新'), !!r.error) }
    catch (e: any) { toast(e.message, true) }
    setBusy(false)
  }
  const when = p.updated ? new Date(p.updated * 1000).toLocaleString(dateLocale(), { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : i18n.t('还没有')
  return (
    <div>
      <h4>{i18n.t('现在用的模型单价')}</h4>
      {rows.map(([k, prov, model]) => {
        const info = s.model_info[`${prov}/${model}`]
        return <div className="kv" key={k} title={priceSource(info)}><span>{ROLE_NAMES()[k] || k} · {model}</span>
          <span className={priceText(info, p.currency) ? '' : 'muted'}>{priceText(info, p.currency) || i18n.t('没有单价，按 0 计')}</span></div>
      })}
      <p className="muted small">{i18n.t('单价自动从')} <a href="https://models.dev" target="_blank" rel="noreferrer">models.dev</a>{i18n.t(' 获取，每天更新一次（上次：{{v0}}），', { v0: when })}
        {i18n.t('美元按 1 : {{v0}} 换成人民币；', { v0: p.rate })}<code>config.yaml</code> {i18n.t('的')} <code>pricing</code> {i18n.t('里写了的以它为准，本机的模型按 0 计。')}
        {p.error && <span className="error-line"> {i18n.t('上次更新失败：{{v0}}', { v0: p.error })}</span>}{' '}
        <button className="link-btn" disabled={busy} onClick={refresh}>{busy ? i18n.t('更新中…') : i18n.t('现在更新')}</button></p>
    </div>
  )
}

function Triggers() {
  const [s, setS] = useState<any>(null)
  const bots = useStore(x => x.bots)
  useEffect(() => { api('/api/status').then(setS) }, [])
  if (!s) return <div className="muted">{i18n.t('加载中…')}</div>
  return (
    <div>
      <h4>{i18n.t('所有定时任务')}</h4>
      {s.routines.length ? s.routines.map((r: any) => (
        <div className="kv" key={r.id}><span>{bots.find(b => b.id === r.bot_id)?.name} · {r.name}（{r.trigger}）</span>
          <span className="muted">{r.enabled ? i18n.t('运行中') : i18n.t('已暂停')}</span></div>
      )) : <div className="muted small">{i18n.t('暂无')}</div>}
      <p className="muted small">{i18n.t('定时任务属于各个 Bot：在对话里说“每天 9 点帮我……”，或者在右栏 Bot 详情的“定时”里新建和管理。webhook 类的地址是 POST /hooks/名字。')}</p>
    </div>
  )
}

// 推送：在这台设备上订阅，没开着页面时，需要你处理的事推送过来
const b64ToBytes = (s: string) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - s.length % 4) % 4)), c => c.charCodeAt(0))

function Notifications() {
  const [info, setInfo] = useState<{ key: string; count: number } | null>(null)
  const [sub, setSub] = useState<PushSubscription | null>(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
  const ios = /iPhone|iPad/.test(navigator.userAgent)
  const standalone = matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone
  useEffect(() => {
    api('/api/push').then(setInfo).catch((e: any) => setMsg(e.message))
    if (supported && isSecureContext) navigator.serviceWorker.ready.then(r => r.pushManager.getSubscription()).then(setSub)
  }, [])
  const on = async () => {
    setBusy(true); setMsg('')
    try {
      if (await Notification.requestPermission() !== 'granted') throw new Error(i18n.t('没有通知权限，请在浏览器或系统设置里允许这个网站发通知'))
      const reg = await navigator.serviceWorker.register('/sw.js')
      await navigator.serviceWorker.ready
      const s = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(info!.key) })
      const r = await api('/api/push/subscribe', { method: 'POST', body: { subscription: s.toJSON() } })
      setSub(s); setInfo({ ...info!, count: r.count }); localStorage.setItem('osa.push', '1'); setMsg(i18n.t('已开启'))
    } catch (e: any) { setMsg(e.message) }
    setBusy(false)
  }
  const off = async () => {
    if (!sub) return
    const r = await api('/api/push/unsubscribe', { method: 'POST', body: { endpoint: sub.endpoint } })
    await sub.unsubscribe().catch(() => {})
    setSub(null); setInfo({ ...info!, count: r.count }); localStorage.removeItem('osa.push'); setMsg(i18n.t('已关闭'))
  }
  const test = async () => {
    setMsg('')
    try { const r = await api('/api/push/test', { method: 'POST' }); setMsg(r.results.every((x: string) => x === 'ok') ? i18n.t('已发出，几秒内应该收到') : r.results.join('；')) }
    catch (e: any) { setMsg(e.message) }
  }
  return (
    <div>
      <p className="muted">{i18n.t('没开着这个页面时（比如手机锁屏），需要你确认、请你帮忙、任务做完和 Bot 的回复会推送到开启了推送的设备。页面开着时不推。')}</p>
      {!isSecureContext ? <p className="error-line">{i18n.t('推送需要 https 访问（本机 localhost 也行）。手机上建议用 Tailscale 的 https 地址，见文档“远程访问”。')}</p>
        : !supported ? <p className="error-line">{i18n.t('这个浏览器不支持推送。')}{ios ? '' : i18n.t('请换用 Chrome、Edge、Firefox 或 Safari。')}</p>
        : ios && !standalone ? <p className="muted">{i18n.t('iPhone / iPad：先在 Safari 里点“分享 → 添加到主屏幕”，从主屏幕打开后再来这里开启。')}</p>
        : <div className="row-actions">
            {sub ? <><span className="pill ok">{i18n.t('这台设备已开启')}</span><button className="btn" onClick={test}>{i18n.t('发一条测试')}</button><button className="btn" onClick={off}>{i18n.t('关闭')}</button></>
              : <button className="btn primary" disabled={busy || !info} onClick={on}>{busy ? i18n.t('开启中…') : i18n.t('在这台设备上开启推送')}</button>}
          </div>}
      {info && <p className="muted small">{i18n.t('已开启推送的设备：{{v0}} 台', { v0: info.count })}</p>}
      {msg && <p className="muted small">{msg}</p>}
      <h4>{i18n.t('添加到主屏幕')}</h4>
      <p className="muted small">{i18n.t('手机上可以把它当应用用：Safari 点“分享 → 添加到主屏幕”，Chrome 点菜单里的“添加到主屏幕”或“安装应用”。')}</p>
    </div>
  )
}

function Rules() {
  const [rules, setRules] = useState<Rule[]>([])
  const apps = useStore(x => x.apps)
  const [pattern, setPattern] = useState('')
  const [action, setAction] = useState<'allow' | 'ask'>('allow')
  const [err, setErr] = useState('')
  const load = () => api('/api/rules').then(setRules)
  useEffect(() => { load() }, [])
  const add = async () => {
    setErr('')
    try { await api('/api/rules', { method: 'POST', body: { pattern, action } }); setPattern(''); load() } catch (e: any) { setErr(e.message) }
  }
  const del = async (id: number) => { await api(`/api/rules/${id}`, { method: 'DELETE' }); load() }
  const tools = apps.flatMap(a => a.tools.map(t => `${a.name}__${t}`))
  const group = (act: 'allow' | 'ask', title: string, hint: string) => (
    <div>
      <h4>{title}</h4>
      <p className="muted small">{hint}</p>
      {rules.filter(r => r.action === act).map(r => (
        <div className="kv" key={r.id}><span><code>{r.pattern}</code> <span className="muted small">{r.note}</span></span>
          <button className="ghost-btn" onClick={() => del(r.id)}>{i18n.t('删除')}</button></div>))}
      {!rules.some(r => r.action === act) && <div className="muted small">{i18n.t('无')}</div>}
    </div>
  )
  return (
    <div>
      <p className="muted">{i18n.t('大多数操作直接执行；写操作默认先问你。规则按工具全名匹配，可以用')} <code>*</code> {i18n.t('通配，例如')} <code>filesystem__*</code>{i18n.t('。两类规则都命中时，“先问我”优先。')}</p>
      {group('ask', i18n.t('先问我'), i18n.t('命中的操作一定弹确认卡片'))}
      {group('allow', i18n.t('自动允许'), i18n.t('命中的操作直接执行。确认卡片上点“总是允许”会加到这里'))}
      <h4>{i18n.t('添加规则')}</h4>
      <datalist id="tool-names">{tools.map(t => <option key={t} value={t} />)}{apps.map(a => <option key={a.name} value={`${a.name}__*`} />)}</datalist>
      <div className="env-row">
        <input list="tool-names" value={pattern} onChange={e => setPattern(e.target.value)} placeholder="filesystem__write_file" />
        <select value={action} onChange={e => setAction(e.target.value as any)}><option value="allow">{i18n.t('自动允许')}</option><option value="ask">{i18n.t('先问我')}</option></select>
        <button className="btn primary" disabled={!pattern.trim()} onClick={add}>{i18n.t('添加')}</button>
      </div>
      {err && <div className="error-line">{err}</div>}
    </div>
  )
}

function Vault() {
  const [items, setItems] = useState<{ name: string; created: number; ok: boolean }[]>([])
  const [name, setName] = useState('')
  const [value, setValue] = useState('')
  const [err, setErr] = useState('')
  const load = () => api('/api/vault').then(setItems)
  useEffect(() => { load() }, [])
  const add = async () => {
    setErr('')
    try { await api(`/api/vault/${name}`, { method: 'PUT', body: { value } }); setName(''); setValue(''); load() } catch (e: any) { setErr(e.message) }
  }
  return (
    <div>
      <p className="muted">{i18n.t('密钥加密保存在本地数据库，模型和聊天记录里只出现名字。应用的环境变量写')} <code>{i18n.t('vault:名字')}</code> {i18n.t('来引用。主密钥取环境变量')} <code>OSA_VAULT_KEY</code>{i18n.t('，没设置时自动生成在')} <code>data/vault.key</code>。</p>
      {items.map(v => (
        <div className="kv" key={v.name}><span><code>{v.name}</code> {!v.ok && <span className="pill bad">{i18n.t('主密钥变了，解不开')}</span>}</span>
          <button className="ghost-btn" onClick={async () => { if (confirm(i18n.t('删除密钥 {{v0}}？', { v0: v.name }))) { await api(`/api/vault/${v.name}`, { method: 'DELETE' }); load() } }}>{i18n.t('删除')}</button></div>))}
      {!items.length && <div className="muted small">{i18n.t('还没有密钥')}</div>}
      <h4>{i18n.t('添加 / 覆盖')}</h4>
      <div className="env-row">
        <input value={name} onChange={e => setName(e.target.value)} placeholder={i18n.t('名字，例如 GITHUB_TOKEN')} />
        <input type="password" autoComplete="off" value={value} onChange={e => setValue(e.target.value)} placeholder={i18n.t('值')} />
        <button className="btn primary" disabled={!name || !value} onClick={add}>{i18n.t('保存')}</button>
      </div>
      {err && <div className="error-line">{err}</div>}
    </div>
  )
}


function LanguagePanel() {
  const toast = useToast()
  const settings = useStore(s => s.settings)
  const current = (settings?.locale || i18n.language || 'vi') as LocaleCode
  const pick = async (code: LocaleCode) => {
    if (code === current) return
    try {
      await api('/api/settings', { method: 'PUT', body: { locale: code } })
      await setLocale(code)
      // Module-level i18n.t() labels are frozen at import; remount key is not enough — full reload.
      location.reload()
    } catch (e: any) {
      toast(e.message, true)
    }
  }
  return (
    <div className="set-rows">
      {LOCALES.map(l => (
        <button key={l.code} className={'set-row lang-row' + (current === l.code ? ' on' : '')}
          onClick={() => pick(l.code)}>
          <span><b>{l.label}</b><span>{l.code}</span></span>
          {current === l.code && <span className="pill ok">{i18n.t('当前')}</span>}
        </button>
      ))}
    </div>
  )
}

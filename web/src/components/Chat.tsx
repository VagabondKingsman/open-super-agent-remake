import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api, approve, chatById, loadOlder, openChat, openLibrary, showTask, useStore } from '../store'
import type { Approval, Bot, Message, Task } from '../types'
import BotAvatar from './BotAvatar'
import Composer from './Composer'
import Markdown from './Markdown'
import i18n, { dateLocale } from '../i18n'

const time = (ts: number) => new Date(ts * 1000).toLocaleTimeString(dateLocale(), { hour: '2-digit', minute: '2-digit' })
const VIA: () => Record<string, string> = () => ({
  telegram: i18n.t('来自 Telegram'), feishu: i18n.t('来自飞书'), dingtalk: i18n.t('来自钉钉'), wecom: i18n.t('来自企业微信'), discord: i18n.t('来自 Discord'),
})
const secs = (s: number) => (s < 60 ? i18n.t('{{v0}} 秒', { v0: Math.round(s) }) : i18n.t('{{v0}} 分 {{v1}} 秒', { v0: Math.floor(s / 60), v1: Math.round(s % 60) }))

// 旧版本的任务记录没有 kind，从文字里推断
function taskKind(m: Message): { kind: string; taskId?: number } {
  if (m.meta.kind) return { kind: m.meta.kind, taskId: m.meta.task_id ?? (m.meta.kind === 'dispatch' ? m.id : undefined) }
  if (m.content.startsWith('[任务已派发]')) return { kind: 'dispatch', taskId: m.id }
  const r = m.content.match(/^\[任务 #(\d+) 结果\]/)
  if (r) return { kind: 'result', taskId: Number(r[1]) }
  if (/^\[任务 #\d+ 已取消/.test(m.content)) return { kind: 'cancel' }
  if (m.content.startsWith('[触发器')) return { kind: 'trigger' }
  return { kind: 'note' }
}

function Thinking({ text, seconds, live }: { text: string; seconds?: number; live?: boolean }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  return (
    <div className={'thinking' + (open ? ' open' : '')}>
      <button onClick={() => setOpen(!open)}>
        <span className={live ? 'pulse' : ''}>{live ? i18n.t('正在思考') : i18n.t('思考了 {{v0}}', { v0: secs(seconds || 0) })}</span>
        <span className="chev">›</span>
      </button>
      {open && <div className="thinking-body">{text}</div>}
    </div>
  )
}

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false)
  return <button className="ghost-btn" onClick={() => { navigator.clipboard?.writeText(text); setOk(true); setTimeout(() => setOk(false), 1200) }}>{ok ? i18n.t('已复制') : i18n.t('复制')}</button>
}

// 群聊里每条消息上面标出是哪个 Bot 说的
const Speaker = ({ bot, show }: { bot?: Bot; show?: boolean }) => show ? <div className="speaker">{bot?.name || i18n.t('已删除的 Bot')}</div> : null

function BotMessage({ bot, m, children, showName }: { bot?: Bot; m: Message; children?: React.ReactNode; showName?: boolean }) {
  return (
    <div className="msg bot">
      {bot && <BotAvatar avatar={bot.avatar} size={28} />}
      <div className="msg-body">
        <Speaker bot={bot} show={showName} />
        <Thinking text={m.meta.thinking} seconds={m.meta.thought_s} />
        <Markdown text={m.content} />
        {children}
        <div className="msg-actions"><span>{time(m.ts)}</span><CopyBtn text={m.content} /></div>
      </div>
    </div>
  )
}


/** Rewrite legacy Chinese routine/task prefixes for display (DB may still store ZH). */
function localizeTaskGoal(raw: string) {
  let g = raw.replace(/^\[(?:任务已派发|Đã giao task|Task dispatched)\]\s*/, '')
  g = g.replace(/\[定时任务 ([^\]]+)\]/g, (_: string, name: string) => i18n.t('[定时任务 {{name}}]', { name }))
  g = g.replace(/这是定时任务「([^」]+)」（([^）]+)）的一次运行。/g,
    (_: string, name: string, when: string) => i18n.t('这是定时任务「{{name}}」（{{when}}）的一次运行。', { name, when }))
  g = g.replace(/^要求：/m, () => i18n.t('要求：'))
  g = g.replace(/^按技能 \/([^\s]+) 的做法执行：/m, (_: string, name: string) => i18n.t('按技能 /{{name}} 的做法执行：', { name }))
  g = g.replace(/^触发事件：/m, () => i18n.t('触发事件：'))
  return g
}

function TaskCard({ m, task, owner, handoffTo, replyTo }: { m: Message; task?: Task; owner?: Bot; handoffTo?: Bot; replyTo?: Bot }) {
  const status = task?.status || m.meta.status || 'done'
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (status !== 'running') return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [status])
  const goal = localizeTaskGoal(m.content)
  const label: Record<string, string> = { running: task?.waiting_approval ? i18n.t('等你确认') : i18n.t('进行中'), done: i18n.t('已完成'), failed: i18n.t('失败'), cancelled: i18n.t('已取消'), interrupted: i18n.t('已中断') }
  return (
    <div className={`task-card ${status}${task?.waiting_approval ? ' waiting' : ''}`}>
      <div className="task-top">
        <span className="dot" />
        <b>{owner ? i18n.t('{{v0}} 的', { v0: owner.name }) : ''}{m.meta.mode === 'heavy' ? i18n.t('Heavy 任务') : i18n.t('后台任务')} #{m.id}</b>
        <span className="muted">{label[status] || status}{status === 'running' && task ? ` · ${secs((now / 1000) - task.started)}` : ''}{task?.steps ? i18n.t(' · {{v0}} 步', { v0: task.steps }) : ''}</span>
        <button className="ghost-btn" title={i18n.t('看这个任务每一步做了什么')} onClick={() => showTask(m.id)}>{i18n.t('过程')}</button>
        {status === 'running' && <button className="ghost-btn" onClick={() => api(`/api/tasks/${m.id}/cancel`, { method: 'POST' })}>{i18n.t('停止')}</button>}
      </div>
      <div className="task-goal">{goal}</div>
      {handoffTo && <div className="task-action">{i18n.t('做完交给 {{v0}}', { v0: handoffTo.name })}</div>}
      {replyTo && <div className="task-action">{i18n.t('做完把结果回给 {{v0}}', { v0: replyTo.name })}</div>}
      {status === 'running' && task?.last_action && <div className="task-action">→ {task.last_action}</div>}
    </div>
  )
}

// 任务结果存进资料库，标题取任务描述的第一行
function SavePageBtn({ bot, text, goal, taskId }: { bot?: Bot; text: string; goal: string; taskId?: number }) {
  const [saved, setSaved] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  if (saved) return <button className="ghost-btn" onClick={() => openLibrary(saved)}>{i18n.t('已存为页面 · 打开')}</button>
  const save = async () => {
    setBusy(true)
    try {
      const h1 = text.match(/^#\s+(.+)$/m)?.[1]
      const title = (h1 || goal.split('\n').find(l => l.trim()) || i18n.t('任务 #{{v0}} 的结果', { v0: taskId })).replace(/^\[(?:定时任务|Lịch|Routine) [^\]]+\]\s*/, '').slice(0, 60)
      const p = await api('/api/pages', { method: 'POST', body: { bot_id: bot?.id, title, content: text, task_id: taskId } })
      setSaved(p.id)
    } finally { setBusy(false) }
  }
  return <button className="ghost-btn" disabled={busy} onClick={save}>{i18n.t('存为页面')}</button>
}

function ResultMessage({ bot, m, goal, showName }: { bot?: Bot; m: Message; goal: string; showName?: boolean }) {
  const text = m.content.replace(/^\[(?:任务 #\d+ 结果|Kết quả task #\d+|Task #\d+ result)\]\n?/, '')
  const [open, setOpen] = useState(text.length < 1800)
  const status = m.meta.status || 'done'
  return (
    <div className="msg bot">
      {bot && <BotAvatar avatar={bot.avatar} size={28} />}
      <div className="msg-body">
        <Speaker bot={bot} show={showName} />
        <div className={`result-head ${status}`}>
          {status === 'failed' ? i18n.t('任务失败') : i18n.t('任务完成')} · #{taskKind(m).taskId}{m.meta.elapsed ? i18n.t(' · 用时 {{v0}}', { v0: secs(m.meta.elapsed) }) : ''}
        </div>
        <div className={open ? '' : 'clamp'}><Markdown text={text} /></div>
        {!open && <button className="expand" onClick={() => setOpen(true)}>{i18n.t('展开全文')}</button>}
        <div className="msg-actions"><span>{time(m.ts)}</span><CopyBtn text={text} />
          {status === 'done' && <SavePageBtn bot={bot} text={text} goal={goal} taskId={taskKind(m).taskId} />}
          {taskKind(m).taskId && <button className="ghost-btn" onClick={() => showTask(taskKind(m).taskId!)}>{i18n.t('查看过程')}</button>}</div>
      </div>
    </div>
  )
}

// 群里派的任务：卡片在私聊里，注明来自哪个群
function Origin({ a }: { a: Approval }) {
  const g = useStore(s => (a.origin_chat_id && a.origin_chat_id !== a.chat_id ? chatById(s, a.origin_chat_id) : undefined))
  return g ? <> {i18n.t('· 在群聊「')}<button className="link-btn" onClick={() => openChat(g.id)}>{g.title}</button>{i18n.t('」里派的')}</> : null
}

function HelpCard({ a }: { a: Approval }) {
  const done = a.status && a.status !== 'pending'
  let reason = ''
  try { reason = JSON.parse(a.args).reason || JSON.parse(a.args)['需要你做的事'] || JSON.parse(a.args)['what'] } catch { reason = a.args }
  if (done) return <div className="sys-line">{a.status === 'approved' ? i18n.t('✓ 你已处理完，Bot 继续') : i18n.t('✕ 没有处理')}{i18n.t('（任务 #{{v0}}）', { v0: a.task_id })}</div>
  return (
    <div className="approval-card help">
      <div className="approval-title">{i18n.t('🙋 需要你帮忙')}</div>
      <div className="help-reason">{reason}</div>
      <div className="muted small">{i18n.t('任务 #{{v0}} 已暂停', { v0: a.task_id })}<Origin a={a} />{i18n.t('。接手电脑处理完后点“交还”，Bot 会接着做。')}</div>
      <div className="approval-actions">
        <button className="btn" onClick={() => approve(a.id, false, i18n.t('用户表示处理不了'))}>{i18n.t('我处理不了')}</button>
        <span className="grow" />
        <button className="btn" onClick={() => window.dispatchEvent(new CustomEvent('osa-open-computer', { detail: { botId: a.bot_id, takeover: true } }))}>{i18n.t('接手电脑')}</button>
        <button className="btn primary" onClick={() => api(`/api/bots/${a.bot_id}/computer/handback`, { method: 'POST' })}>{i18n.t('处理完了，交还')}</button>
      </div>
    </div>
  )
}

function ApprovalCard({ a }: { a: Approval }) {
  if (a.kind === 'help') return <HelpCard a={a} />
  const [note, setNote] = useState('')
  const done = a.status && a.status !== 'pending'
  const label: Record<string, string> = { approved: a.always ? i18n.t('已允许，以后自动允许') : i18n.t('已允许'), rejected: i18n.t('已拒绝'), expired: i18n.t('超时未确认，按拒绝处理'), cancelled: i18n.t('任务已取消') }
  if (done) return <div className="sys-line">{a.status === 'approved' ? '✓' : '✕'} {label[a.status!] || a.status} <code>{a.tool}</code>{i18n.t('（任务 #{{v0}}）', { v0: a.task_id })}</div>
  const [app, tool] = a.tool.includes('__') ? a.tool.split('__', 2) : ['', a.tool]
  return (
    <div className="approval-card">
      <div className="approval-title">{i18n.t('需要你确认')}{app && <> {i18n.t('· 应用')} <b>@{app}</b></>} <code>{tool}</code></div>
      <div className="muted small">{i18n.t('来自任务 #{{v0}}', { v0: a.task_id })}<Origin a={a} />：{a.goal}
        {a.expires ? i18n.t(' · 后台任务，{{v0}} 前没确认按拒绝处理', { v0: new Date(a.expires * 1000).toLocaleTimeString(i18n.language === 'vi' ? 'vi-VN' : i18n.language === 'en' ? 'en-US' : 'zh-CN', { hour: '2-digit', minute: '2-digit' }) }) : ''}</div>
      <pre className="approval-args">{a.args}</pre>
      <div className="approval-actions">
        <input value={note} onChange={e => setNote(e.target.value)} placeholder={i18n.t('附一句意见（可选）')} />
        <button className="btn" onClick={() => approve(a.id, false, note)}>{i18n.t('拒绝')}</button>
        <button className="btn" onClick={() => approve(a.id, true, note)}>{i18n.t('允许一次')}</button>
        <button className="btn primary" title={i18n.t('以后 {{v0}} 不再询问，可在设置 → 确认规则里撤销', { v0: a.tool })} onClick={() => approve(a.id, true, note, true)}>{i18n.t('总是允许')}</button>
      </div>
    </div>
  )
}

function HandoffLine({ from, to, text }: { from?: Bot; to?: Bot; text: string }) {
  return (
    <div className="handoff">
      {from && <BotAvatar avatar={from.avatar} size={18} />}<b>{from?.name || i18n.t('已删除的 Bot')}</b>
      <span className="muted">{i18n.t('交给')}</span>
      {to && <BotAvatar avatar={to.avatar} size={18} />}<b>{to?.name || i18n.t('已删除的 Bot')}</b>
      <span className="handoff-text">{text}</span>
    </div>
  )
}

// Bot 之间的私信：谁私信了谁、说了什么；点名字去看对方那边
function DmLine({ m, from, to, here }: { m: Message; from?: Bot; to?: Bot; here: number }) {
  const [open, setOpen] = useState(m.content.length < 240)
  // 在收信的私聊里，链接回发信的那个对话；在发信的对话里，链接到收信 Bot 的私聊
  const there = m.meta.chat && m.meta.chat !== here ? m.meta.chat : to && to.chat_id !== here ? to.chat_id : null
  return (
    <div className="handoff dm">
      <span className="dm-icon">✉</span>
      {from && <BotAvatar avatar={from.avatar} size={18} />}<b>{from?.name || i18n.t('已删除的 Bot')}</b>
      <span className="muted">{i18n.t('私信')}</span>
      {to && <BotAvatar avatar={to.avatar} size={18} />}<b>{to?.name || i18n.t('已删除的 Bot')}</b>
      {there && <button className="link-btn small" onClick={() => openChat(there)}>{m.meta.chat && m.meta.chat !== here ? i18n.t('去发信的对话') : i18n.t('去看 {{v0}}', { v0: to?.name })}</button>}
      <span className={'handoff-text' + (open ? '' : ' clamp3')}>{m.content}</span>
      {!open && <button className="expand" onClick={() => setOpen(true)}>{i18n.t('展开')}</button>}
    </div>
  )
}

// 私信的回信：显示成发信 Bot 的一条消息，长的折起来
function DmReply({ m, bot, to }: { m: Message; bot?: Bot; to?: Bot }) {
  const [open, setOpen] = useState(m.content.length < 1800)
  const bad = m.meta.status && m.meta.status !== 'done'
  return (
    <div className="msg bot">
      {bot && <BotAvatar avatar={bot.avatar} size={28} />}
      <div className="msg-body">
        <div className="speaker">{bot?.name || i18n.t('已删除的 Bot')}</div>
        <div className={'result-head' + (bad ? ' failed' : '')}>{i18n.t('↩ 回了 {{v0}} 的私信', { v0: to?.name || i18n.t('已删除的 Bot') })}{m.meta.task_id ? i18n.t(' · 任务 #{{v0}}', { v0: m.meta.task_id }) : ''}</div>
        <div className={open ? '' : 'clamp'}><Markdown text={m.content} /></div>
        {!open && <button className="expand" onClick={() => setOpen(true)}>{i18n.t('展开全文')}</button>}
        <div className="msg-actions"><span>{time(m.ts)}</span><CopyBtn text={m.content} />
          {bot && <button className="ghost-btn" onClick={() => openChat(bot.chat_id)}>{i18n.t('去 {{v0}} 的私聊', { v0: bot.name })}</button>}
          {m.meta.task_id && <button className="ghost-btn" onClick={() => showTask(m.meta.task_id)}>{i18n.t('查看过程')}</button>}</div>
      </div>
    </div>
  )
}

const STARTERS = () => ([
  i18n.t('每天早上 9 点给我整理 AI 领域的重要新闻'),
  i18n.t('帮我调研一下自部署 SearxNG 的最佳实践'),
  i18n.t('你能做哪些事？先介绍一下你的能力'),
])

export function GroupAvatars({ bots, size = 26 }: { bots: Bot[]; size?: number }) {
  return (
    <span className="group-avatars" style={{ width: size + (Math.min(bots.length, 3) - 1) * size * 0.45 }}>
      {bots.slice(0, 3).map((b, i) => <span key={b.id} style={{ left: i * size * 0.45, zIndex: 3 - i }}><BotAvatar avatar={b.avatar} size={size} /></span>)}
    </span>
  )
}

export default function Chat({ onToggleDetails }: { onToggleDetails: () => void }) {
  const active = useStore(s => s.active)
  const chat = useStore(s => chatById(s, s.active))
  const allBots = useStore(s => s.bots)
  const messages = useStore(s => (s.active ? s.messages[s.active] : undefined))
  const stream = useStore(s => (s.active ? s.streams[s.active] : undefined))
  const tasks = useStore(s => s.tasks)
  const approvals = useStore(s => s.approvals)
  const hasMore = useStore(s => (s.active ? s.hasMore[s.active] : false))
  const error = useStore(s => (s.active ? s.errors[s.active] : undefined))
  const scroller = useRef<HTMLDivElement>(null)
  const stick = useRef(true)
  const prevHeight = useRef(0)

  // 新消息到达时，只有用户本来就在底部才自动滚到底
  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    if (stick.current) el.scrollTop = el.scrollHeight
    else if (prevHeight.current && el.scrollTop < 40) el.scrollTop = el.scrollHeight - prevHeight.current
    prevHeight.current = el.scrollHeight
  }, [messages, stream?.text, stream?.thinking])
  useEffect(() => { stick.current = true }, [active])

  const onScroll = () => {
    const el = scroller.current!
    stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
    if (el.scrollTop < 40 && hasMore && active) { prevHeight.current = el.scrollHeight; loadOlder(active) }
  }

  if (!active || !chat) return <main className="chat empty-main" />
  const group = chat.kind === 'group'
  const botOf = (id: number | null | undefined) => allBots.find(b => b.id === id)
  const members = chat.bot_ids.map(botOf).filter((b): b is Bot => !!b)
  const bot = group ? undefined : members[0]
  if (!group && !bot) return <main className="chat empty-main" />
  const speaker = (m: Message) => (group ? botOf(m.bot_id) : bot)
  const lead = botOf(chat.lead)
  // 回复里记录了本轮派发的任务：任务卡片挂到回复下面，不再单独显示
  const byId = new Map((messages || []).map(m => [m.id, m]))
  const attached = new Set((messages || []).flatMap(m => (m.role === 'assistant' ? m.meta.tasks || [] : [])))
  const pending = Object.values(approvals).filter(a => a.chat_id === active && (a.status === 'pending' || Date.now() / 1000 - a.ts < 600))
  // 群里派的任务要确认时，卡片在 Bot 的私聊里；这里只放一条提示
  const elsewhere = Object.values(approvals).filter(a => a.origin_chat_id === active && a.chat_id !== active && a.status === 'pending')
  const empty = messages && messages.length === 0 && !stream
  const title = group ? chat.title : bot!.name
  const task = (tid: number) => byId.get(tid) && <TaskCard key={tid} m={byId.get(tid)!} task={tasks[tid]}
    owner={group ? botOf(byId.get(tid)!.bot_id) : undefined} handoffTo={botOf(byId.get(tid)!.meta.handoff_to)}
    replyTo={botOf(byId.get(tid)!.meta.reply_to)} />
  const starters = group && members.length >= 2
    ? [i18n.t('@所有人 先各自介绍一下你们能做什么'), i18n.t('{{v0}} 查一下今天的 AI 新闻，查完交给 {{v1}} 写一段 100 字的总结', { v0: '@'+members[0].name, v1: '@'+members[1].name })]
    : STARTERS()

  return (
    <main className="chat">
      <header className="chat-head">
        <button className="head-bot" onClick={onToggleDetails} title={group ? i18n.t('群聊设置') : i18n.t('Bot 详情')}>
          {group ? <GroupAvatars bots={members} /> : <BotAvatar avatar={bot!.avatar} size={26} />}
          <span className="head-name">{title}</span>
          {group ? <span className="muted small">{i18n.t('{{v0}} 个 Bot', { v0: members.length })}</span> : bot!.is_primary && <span className="star" title={i18n.t('主 Bot')}>★</span>}
        </button>
        <div className="head-actions">
          <button className="ghost-btn" title={i18n.t('之前的对话不再带进上下文，省 token；长期记忆还在')} onClick={() => {
            if (confirm(i18n.t('开始新话题？{{v0}} 不再参考之前的对话（记录还在，长期记忆也还在）。', { v0: group ? i18n.t('群里的 Bot') : bot!.name }))) api(`/api/chats/${active}/reset`, { method: 'POST' })
          }}>{i18n.t('新话题')}</button>
          <button className="icon-btn" onClick={onToggleDetails} title={i18n.t('详情')}>☰</button>
        </div>
      </header>
      <div className="scroller" ref={scroller} onScroll={onScroll}>
        <div className="thread">
          {empty && (group ? (
            <div className="welcome">
              <GroupAvatars bots={members} size={56} />
              <h2>{chat.title}</h2>
              <p className="muted">{i18n.t('@ 某个 Bot 让它来做，@所有人 让大家都说说；不 @ 的消息由协调者{{v0}}接，它会分给合适的 Bot。Bot 之间可以交接工作；要你确认的操作会出现在各自的私聊里。', { v0: lead ? ` ${lead.name} ` : '' })}</p>
              <div className="starters">{starters.map(s => <button key={s} onClick={() => window.dispatchEvent(new CustomEvent('osa-fill', { detail: s }))}>{s}</button>)}</div>
            </div>
          ) : (
            <div className="welcome">
              <BotAvatar avatar={bot!.avatar} size={72} />
              <h2>{bot!.name}</h2>
              <p className="muted">{i18n.t('给 {{v0}} 布置第一份工作。它会记住你交代的职责，在后台替你完成任务。', { v0: bot!.name })}</p>
              <div className="starters">{starters.map(s => <button key={s} onClick={() => window.dispatchEvent(new CustomEvent('osa-fill', { detail: s }))}>{s}</button>)}</div>
            </div>
          ))}
          {messages?.map(m => {
            if (m.role === 'user') return <div key={m.id} className="msg user">
              {m.meta.via && <span className="via">{VIA()[m.meta.via] || m.meta.via}</span>}<div className="bubble">{m.content}</div></div>
            if (m.role === 'assistant') return m.content || m.meta.tasks?.length ? (
              <BotMessage key={m.id} bot={speaker(m)} m={m} showName={group}>
                {(m.meta.tasks || []).map(task)}
              </BotMessage>) : null
            const k = taskKind(m)
            if (k.kind === 'dispatch') return attached.has(m.id) ? null : task(m.id)
            if (k.kind === 'result') return <ResultMessage key={m.id} bot={speaker(m)} m={m} showName={group}
              goal={(k.taskId && byId.get(k.taskId)?.content.replace(/^\[(?:任务已派发|Đã giao task|Task dispatched)\]\s*/, '')) || ''} />
            if (k.kind === 'handoff') return <HandoffLine key={m.id} from={botOf(m.bot_id)} to={botOf(m.meta.to)} text={m.meta.note || m.content} />
            if (k.kind === 'dm') return <DmLine key={m.id} m={m} from={botOf(m.bot_id)} to={botOf(m.meta.to)} here={chat.id} />
            if (k.kind === 'dm_reply' && m.meta.sent) return <div key={m.id} className="sys-line">{i18n.t('↩ 已把回信发给 {{v0}}', { v0: botOf(m.meta.to)?.name || i18n.t('已删除的 Bot') })}
              {m.meta.chat && m.meta.chat !== chat.id && <> · <button className="link-btn" onClick={() => openChat(m.meta.chat)}>{i18n.t('去看')}</button></>}</div>
            if (k.kind === 'dm_reply') return <DmReply key={m.id} m={m} bot={botOf(m.bot_id)} to={botOf(m.meta.to)} />
            if (k.kind === 'reset') return <div key={m.id} className="topic-line"><span>{i18n.t('新话题 · 之前的对话不再带进上下文，长期记忆还在')}</span></div>
            if (k.kind === 'trigger') return <div key={m.id} className="sys-line">⚡ {m.content.replace(/^\[触发器 ([^\]]+)\]/, i18n.t('触发器 $1：')).slice(0, 160)}</div>
            return <div key={m.id} className="sys-line">{m.content.replace(/^\[|\]$/g, '').slice(0, 160)}</div>
          })}
          {stream && (() => {
            const who = group ? botOf(stream.bot_id) : bot
            return (
              <div className="msg bot">
                {who && <BotAvatar avatar={who.avatar} size={28} busy />}
                <div className="msg-body">
                  <Speaker bot={who} show={group} />
                  <Thinking text={stream.thinking} live={!stream.text} seconds={(Date.now() - stream.started) / 1000} />
                  {stream.text ? <Markdown text={stream.text + ' ▍'} /> : !stream.thinking && <div className="typing"><i /><i /><i /></div>}
                </div>
              </div>
            )
          })()}
          {pending.map(a => <ApprovalCard key={a.id} a={a} />)}
          {elsewhere.map(a => {
            const b = botOf(a.bot_id)
            return (
              <div key={a.id} className="elsewhere">
                <span>{i18n.t('⚠ {{v0}} 的任务 #{{v1}} {{v2}}，卡片在它的私聊里', { v0: b?.name, v1: a.task_id, v2: a.kind === 'help' ? i18n.t('需要你帮忙') : i18n.t('需要你确认') })}</span>
                {b && <button className="btn" onClick={() => openChat(b.chat_id)}>{i18n.t('去处理')}</button>}
              </div>
            )
          })}
          {error && <div className="error-line">{error}</div>}
        </div>
      </div>
      <SetupHint />
      <Composer chatId={active} bot={bot} members={group ? members : []}
        busy={stream ? (group ? botOf(stream.bot_id)?.name || i18n.t('有人') : bot!.name) : ''} />
    </main>
  )
}

// 对话或后台任务的模型还没法用（比如没填 API Key）：提示去设置里配好
function SetupHint() {
  const problem = useStore(s => s.settings?.problem)
  if (!problem) return null
  return (
    <div className="setup-hint">
      <span>{i18n.t('⚠ {{v0}}，Bot 现在没法回复。', { v0: problem })}</span>
      <button className="btn small" onClick={() => window.dispatchEvent(new CustomEvent('osa-open-settings', { detail: 'models' }))}>{i18n.t('去配置模型')}</button>
    </div>
  )
}

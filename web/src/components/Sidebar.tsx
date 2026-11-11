import { useEffect, useRef, useState } from 'react'
import type { MouseEvent, PointerEvent } from 'react'
import { api, markChatUnread, openApps, openChat, openLibrary, openObserve, pinChat, reconnectNow, refreshLists, setBotHidden, useStore } from '../store'
import { android } from '../desktop'
import { t } from '../i18n'
import { chatLabel } from '../chatLabel'
import { copyText } from '../copyText'
import { ask, askText, notice } from './Dialog'
import type { Chat } from '../types'
import BotAvatar from './BotAvatar'
import { GroupFace } from './Chat'
import { Icon } from '../icons'
import { plain } from '../plain'


export default function Sidebar({ onNewBot, onNewGroup, onSettings, onClose }: { onNewBot: () => void; onNewGroup: () => void; onSettings: () => void; onClose: () => void }) {
  const chats = useStore(s => s.chats)
  const bots = useStore(s => s.bots)
  const active = useStore(s => s.active)
  const unread = useStore(s => s.unread)
  const threads = useStore(s => s.threads)
  const tasks = useStore(s => s.tasks)
  const approvals = useStore(s => s.approvals)
  const connected = useStore(s => s.connected)
  const view = useStore(s => s.view)
  const [menu, setMenu] = useState(false)
  const [ctx, setCtx] = useState<{ chat: Chat; x: number; y: number } | null>(null)   // 右键 / 长按菜单
  const [showHidden, setShowHidden] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [toast, setToast] = useState<{ ok: boolean; text: string } | null>(null)
  const toastTimer = useRef<number | null>(null)
  const hold = useRef<{ timer: number | null; x: number; y: number }>({ timer: null, x: 0, y: 0 })
  const skipClick = useRef(false)
  const clearHold = () => { if (hold.current.timer !== null) { window.clearTimeout(hold.current.timer); hold.current.timer = null } }

  // 右键菜单：点别处、按 Esc、滚动、窗口变化都关掉
  useEffect(() => {
    if (!ctx) return
    const close = () => { skipClick.current = false; setCtx(null) }
    const key = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('pointerdown', close)
    window.addEventListener('keydown', key)
    window.addEventListener('resize', close)
    window.addEventListener('blur', close)
    window.addEventListener('scroll', close, true)
    return () => {
      window.removeEventListener('pointerdown', close)
      window.removeEventListener('keydown', key)
      window.removeEventListener('resize', close)
      window.removeEventListener('blur', close)
      window.removeEventListener('scroll', close, true)
    }
  }, [ctx])
  useEffect(() => () => { if (hold.current.timer !== null) window.clearTimeout(hold.current.timer) }, [])
  useEffect(() => () => { if (toastTimer.current !== null) window.clearTimeout(toastTimer.current) }, [])
  const showToast = (ok: boolean, text: string) => {
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current)
    setToast({ ok, text })
    toastTimer.current = window.setTimeout(() => { toastTimer.current = null; setToast(null) }, 2500)
  }
  const onReconnect = async () => {
    if (reconnecting) return
    const attempt = reconnectNow()
    if (!attempt) return
    setReconnecting(true)
    const ok = await attempt
    setReconnecting(false)
    showToast(ok, ok ? t('已重新连上') : t('还是连不上这台服务器'))
  }

  // 一个对话在侧栏里要显示的东西；Bot 已经没了的私聊不显示
  const info = (c: Chat) => {
    const group = c.kind === 'group'
    const members = c.bot_ids.map(i => bots.find(b => b.id === i)).filter((b): b is NonNullable<typeof b> => !!b)
    const bot = group ? undefined : members[0]
    if (!group && !bot) return null
    return {
      group, members, bot, name: chatLabel(c, bots),
      isActive: c.id === active && view === 'chat',
      busy: Object.values(tasks).some(t => t.chat_id === c.id && t.status === 'running'),
      needs: Object.values(approvals).some(a => a.chat_id === c.id && a.status === 'pending'),
      away: group && Object.values(approvals).some(a => a.origin_chat_id === c.id && a.status === 'pending'),
    }
  }
  const open = (c: Chat) => { openChat(c.id); onClose() }
  const showMenu = (c: Chat, x: number, y: number) => setCtx({ chat: c, x, y })
  const onMenu = (c: Chat) => (e: MouseEvent) => { e.preventDefault(); clearHold(); showMenu(c, e.clientX, e.clientY) }
  const onHoldStart = (c: Chat) => (e: PointerEvent) => {
    if (e.button !== 0) return
    clearHold()
    hold.current.x = e.clientX
    hold.current.y = e.clientY
    const x = e.clientX, y = e.clientY
    hold.current.timer = window.setTimeout(() => {
      hold.current.timer = null
      skipClick.current = true   // 只吞掉长按松开时那一下 click，右键没有这下 click
      showMenu(c, x, y)
    }, 480)
  }
  const onHoldMove = (e: PointerEvent) => {
    if (hold.current.timer === null) return
    if (Math.hypot(e.clientX - hold.current.x, e.clientY - hold.current.y) > 10) clearHold()
  }
  const onItemClick = (c: Chat) => () => { if (skipClick.current) { skipClick.current = false; return } open(c) }
  const press = (c: Chat) => ({
    onClick: onItemClick(c), onContextMenu: onMenu(c),
    onPointerDown: onHoldStart(c), onPointerMove: onHoldMove, onPointerUp: clearHold, onPointerCancel: clearHold,
  })
  // Bot 自己的那个私聊：随 Bot 一起删（服务端也拦着），菜单里不给“删除”
  const isBotChat = (c: Chat) => bots.find(b => b.id === c.bot_ids[0])?.chat_id === c.id
  // 讨论串里的新回复也算在对话上：看过那个讨论串才去掉（只打开对话不算）
  const news = (c: Chat) => Object.values(threads).filter(x => x.parent === c.id && x.unread > 0)
  const count = (c: Chat) => {
    const n = (unread[c.id] || 0) + news(c).reduce((a, x) => a + x.unread, 0)
    return n || (c.marked_unread ? 1 : 0)
  }
  const badge = (c: Chat, needs: boolean) => needs ? <span className="badge warn">!</span> : count(c) ? <span className="badge">{count(c)}</span> : null
  // 预览显示最新的动静：讨论串里的新回复比主对话的最后一条还新时，显示那条回复
  const preview = (c: Chat) => {
    const th = news(c).sort((a, b) => (b.last || 0) - (a.last || 0))[0]
    return th?.preview && (th.last || 0) >= c.updated ? '💬 ' + plain(th.preview) : plain(c.preview)
  }
  const hiddenBot = (c: Chat) => c.kind === 'direct' && !!bots.find(b => b.chat_id === c.id && b.hidden)
  const pins = chats.filter(c => c.pinned && !hiddenBot(c)).sort((a, b) => a.pinned - b.pinned)
  const hidden = bots.filter(b => b.hidden)
  const hiddenRows = hidden.flatMap(b => {
    const c = chats.find(x => x.id === b.chat_id)
    if (!c) return []
    const x = info(c)
    return x ? [{ b, c, x }] : []
  })
  const hiddenNeeds = hiddenRows.some(r => r.x.needs)
  const hiddenUnread = hiddenRows.reduce((n, r) => n + count(r.c), 0)

  return (
    <aside className="sidebar">
      <div className="side-top">
        <span className="logo" title="Open Super Agent">◆</span>
        <div className="plus-wrap">
          <button className="icon-btn round" title={t('新建')} onClick={() => setMenu(!menu)}><Icon name="plus" size={18} /></button>
          {menu && (
            <div className="menu" onMouseLeave={() => setMenu(false)}>
              <button onClick={() => { setMenu(false); onNewBot() }}>{t('新建 Bot')}</button>
              <button onClick={() => { setMenu(false); onNewGroup() }}>{t('新建群聊')}</button>
            </div>
          )}
        </div>
      </div>
      <button className={'side-nav' + (view === 'library' ? ' active' : '')} onClick={() => { openLibrary(); onClose() }}>
        <span className="side-nav-icon">▤</span>{t('资料库')}
      </button>
      <button className={'side-nav' + (view === 'apps' ? ' active' : '')} onClick={() => { openApps(); onClose() }}>
        <span className="side-nav-icon">⊞</span>{t('应用')}
      </button>
      <button className={'side-nav' + (view === 'observe' ? ' active' : '')} onClick={() => { openObserve(); onClose() }}>
        <span className="side-nav-icon"><Icon name="activity" size={16} /></span>{t('观测')}
      </button>
      {pins.length > 0 && (
        <div className="pin-row">
          {pins.map(c => {
            const x = info(c)
            if (!x) return null
            return (
              <button key={c.id} className={'pin-item' + (x.isActive ? ' active' : '')} title={x.name} {...press(c)}>
                <span className="pin-av">
                  {x.group ? <GroupFace image={c.image} bots={x.members} size={34} stack={24} /> : <BotAvatar avatar={x.bot!.avatar} size={34} busy={x.busy} />}
                  {badge(c, x.needs)}
                </span>
                <span className="pin-name">{x.name}</span>
              </button>
            )
          })}
        </div>
      )}
      <nav className="chat-list">
        {chats.map(c => {
          const x = info(c)
          if (!x || hiddenBot(c)) return null
          const { group, members, bot } = x
          return (
            <button key={c.id} className={'chat-item' + (x.isActive ? ' active' : '')} {...press(c)}>
              {group ? <span className="ci-group"><GroupFace image={c.image} bots={members} size={34} stack={24} /></span> : <BotAvatar avatar={bot!.avatar} size={34} busy={x.busy} />}
              <div className="ci-text">
                <div className="ci-name">{x.name}{bot?.is_primary && <span className="star">★</span>}{group && <span className="ci-count">{members.length}</span>}</div>
                <div className="ci-preview">{x.needs ? '⚠ ' + t('等你确认') : x.away ? '⚠ ' + t('有 Bot 等你确认（在私聊里）') : preview(c) || (group ? t('新的群聊') : plain(bot!.instructions) || t('新的 Bot'))}</div>
              </div>
              {badge(c, x.needs)}
            </button>
          )
        })}
      </nav>
      {hidden.length > 0 && (
        <div className="hidden-bots">
          <button className="side-link" onClick={() => setShowHidden(v => !v)}>
            {t('已隐藏的 Bot')} ({hidden.length})
            {hiddenNeeds && <span className="badge warn">!</span>}
            {hiddenUnread > 0 && <span className="badge">{hiddenUnread}</span>}
          </button>
          {showHidden && (
            <div className="hidden-list">
              {hiddenRows.map(({ b, c, x }) => (
                <button key={b.id} className="chat-item" {...press(c)}>
                  <BotAvatar avatar={b.avatar} size={34} busy={x.busy} />
                  <div className="ci-text"><div className="ci-name">{b.name}</div></div>
                  {badge(c, x.needs)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {ctx && (
        <div className="menu ctx-menu" style={{ left: Math.min(ctx.x, innerWidth - 220), top: Math.min(ctx.y, innerHeight - 320) }}
             onPointerDown={e => e.stopPropagation()}>
          <button onClick={() => { pinChat(ctx.chat.id, !ctx.chat.pinned); setCtx(null) }}>{ctx.chat.pinned ? t('取消置顶') : t('置顶')}</button>
          <button onClick={() => { markChatUnread(ctx.chat.id); setCtx(null) }}>{t('标记未读')}</button>
          {isBotChat(ctx.chat) && (() => {
            const bot = bots.find(b => b.chat_id === ctx.chat.id)!
            return (
              <>
                <button onClick={async () => {
                  setCtx(null)
                  const ok = await copyText(String(bot.id))
                  await notice(ok ? t('已复制 ID {id}', { id: bot.id }) : t('复制失败'))
                }}>{t('复制 ID')}</button>
                <button onClick={() => { setBotHidden(bot.id, !bot.hidden); setCtx(null) }}>{bot.hidden ? t('显示这个 Bot') : t('隐藏这个 Bot')}</button>
                <button onClick={() => {
                  setCtx(null)
                  window.dispatchEvent(new CustomEvent('osa-open-bot', { detail: { botId: bot.id, tab: 'details' } }))
                  onClose()
                }}>{t('编辑详情')}</button>
                <button className="danger" onClick={async () => {
                  setCtx(null)
                  if (!(await ask(t('删除「{name}」？它的对话记录也会一起删除，无法恢复。', { name: bot.name }), { ok: t('删除'), danger: true }))) return
                  try { await api(`/api/bots/${bot.id}`, { method: 'DELETE' }) }
                  catch (e: any) { await notice(e.message) }
                }}>{t('删除这个 Bot')}</button>
              </>
            )
          })()}
          {/* 一个 Bot 可以不止一个私聊：给它起个名字（空 = 跟着 Bot 的名字），不要的那个能删（Bot 自己的那个随 Bot） */}
          {ctx.chat.kind === 'direct' && (
            <button onClick={async () => {
              const c = ctx.chat
              setCtx(null)
              const name = await askText(t('这个对话叫什么？（留空 = 跟着 Bot 的名字）'), c.title)
              if (name === null) return
              try { await api(`/api/chats/${c.id}`, { method: 'PATCH', body: { title: name } }); await refreshLists() } catch (e: any) { await notice(e.message) }
            }}>{t('改名')}</button>
          )}
          {ctx.chat.kind === 'direct' && !isBotChat(ctx.chat) && (
            <button onClick={async () => {
              const c = ctx.chat
              setCtx(null)
              if (!(await ask(t('删除「{name}」？这个对话里的消息会一起删除。', { name: c.title }), { ok: t('删除'), danger: true }))) return
              try { await api(`/api/chats/${c.id}`, { method: 'DELETE' }); await refreshLists() } catch (e: any) { await notice(e.message) }
            }}>{t('删除对话')}</button>
          )}
        </div>
      )}
      <div className="side-bottom">
        <button className="side-link" onClick={onSettings}>⚙ {t('设置')}</button>
        <span className="side-conn">
          {android && !connected && (
            <button className="side-link" disabled={reconnecting} onClick={onReconnect}>{reconnecting ? t('连接中…') : t('重新连接')}</button>
          )}
          <span className={'conn' + (connected ? ' on' : '')} title={connected ? t('已连接') : t('连接中断，正在重连')} />
        </span>
      </div>
      {toast && <div className={'conn-toast ' + (toast.ok ? 'ok' : 'bad')} role="status">{toast.text}</div>}
    </aside>
  )
}

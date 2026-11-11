// 代替浏览器的 confirm() / alert()：桌面 App 里的 WebKit 不弹原生对话框（confirm 直接当成“取消”）。
// 第一次用到时自己挂到页面上，分享页这类单独的页面也能用。
import { useEffect, useRef, useSyncExternalStore } from 'react'
import { createRoot } from 'react-dom/client'
import { t } from '../i18n'
import { useBack } from '../swipe'

type Req = { text: string; ok: string; cancel?: string; danger?: boolean; input?: string; resolve: (ok: boolean | string | null) => void }

let queue: Req[] = []
const subs = new Set<() => void>()
let mounted = false

function open(r: Omit<Req, 'resolve'>): Promise<any> {
  if (!mounted) {
    mounted = true
    const el = document.createElement('div')
    document.body.appendChild(el)
    createRoot(el).render(<Host />)
  }
  return new Promise(resolve => { queue = [...queue, { ...r, resolve }]; subs.forEach(f => f()) })
}

/** 问一句，点了确认得到 true。删除这类操作传 danger 和按钮文字（比如“删除”）。 */
export const ask = (text: string, o: { ok?: string; danger?: boolean } = {}) =>
  open({ text, ok: o.ok || t('好的'), cancel: t('取消'), danger: o.danger })

/** 告诉你一件事，只有一个按钮。 */
export const notice = (text: string) => open({ text, ok: t('好的') }).then(() => undefined)

/** 问一句、要一段文字（改名、起标题）。确认得到写的那段（可以是空字符串），取消得到 null。 */
export const askText = (text: string, value = '', o: { ok?: string; cancel?: string } = {}) =>
  open({ text, ok: o.ok || t('好的'), cancel: o.cancel || t('取消'), input: value })

function close(r: Req, ok: boolean, text?: string) {
  queue = queue.filter(x => x !== r)
  subs.forEach(f => f())
  r.resolve(r.input === undefined ? ok : ok ? (text ?? r.input) : null)
}

function Host() {
  const q = useSyncExternalStore(f => { subs.add(f); return () => { subs.delete(f) } }, () => queue)
  const r = q[0]
  const root = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  useBack(() => r && close(r, false), root, !!r)
  useEffect(() => {
    if (!r) return
    // 先于设置、应用市场这些弹窗自己的 Esc 处理：只关掉这个对话框
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopImmediatePropagation(); e.preventDefault(); close(r, false) }
    }
    window.addEventListener('keydown', key, true)
    return () => window.removeEventListener('keydown', key, true)
  }, [r])
  if (!r) return null
  return (
    <div className="modal-bg dialog-bg" ref={root} onMouseDown={e => e.target === e.currentTarget && close(r, false)}>
      <div className="modal small dialog" role="alertdialog" aria-modal="true">
        <p className="dialog-text">{r.text}</p>
        {r.input !== undefined && (
          <input className="input" ref={input} defaultValue={r.input} autoFocus maxLength={60}
                 onKeyDown={e => { if (e.key === 'Enter') close(r, true, (e.target as HTMLInputElement).value) }} />
        )}
        <div className="modal-actions">
          {r.cancel && <button className="btn" onClick={() => close(r, false)}>{r.cancel}</button>}
          <button className={'btn ' + (r.danger ? 'danger' : 'primary')} autoFocus={r.input === undefined}
                  onClick={() => close(r, true, input.current?.value ?? '')}>{r.ok}</button>
        </div>
      </div>
    </div>
  )
}

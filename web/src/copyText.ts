// Copy to the clipboard and report whether it really happened — every "copied" label reads this.
// A phone usually opens OSA on plain http (a tailnet name, not https): there navigator.clipboard is
// simply absent, leaving only document.execCommand('copy'). On Android Chrome and WebViews that call
// often returns true while the clipboard stays empty, so its return value is not evidence: the proof
// is the 'copy' event firing, where we put the text into clipboardData ourselves (the trick
// clipboard.js has used for a decade, and the one Android honours).
// If none of the three routes works, a panel opens with the text selectable, so a long press can
// still copy it by hand. This module never claims a copy it did not make.

export async function copyText(text: string): Promise<boolean> {
  if (!text) return false
  if (await viaClipboardApi(text)) return true
  if (viaCopyEvent(text)) return true
  if (viaSelection(text)) return true
  manualCopy(text)
  return false
}

// The modern API: available on https (and localhost) only, and works from a tap.
async function viaClipboardApi(text: string): Promise<boolean> {
  const api = typeof navigator !== 'undefined' ? navigator.clipboard : undefined
  if (!api?.writeText) return false
  try {
    await api.writeText(text)
    return true          // a resolved writeText is a real write
  } catch {
    return false         // http page, denied permission, WebView: fall through
  }
}

// Listen once for the browser's own copy event and hand it the text.
function catcher(text: string) {
  let fired = false
  const handler = (e: Event) => {
    const ev = e as ClipboardEvent
    fired = true
    try {
      if (ev.clipboardData) {
        ev.clipboardData.setData('text/plain', text)
        ev.preventDefault()
      }
    } catch { /* keep the selection's own data */ }
  }
  return { handler, fired: () => fired }
}

// A textarea in the viewport (an off-screen one cannot be selected on Android), focused and
// selected, then execCommand('copy'); success is the copy event, not the return value.
function viaCopyEvent(text: string): boolean {
  if (typeof document === 'undefined' || !document.body) return false
  const doc = document
  const { handler, fired } = catcher(text)
  let el: HTMLTextAreaElement | undefined
  try {
    el = doc.createElement('textarea')
    el.value = text
    el.setAttribute('readonly', '')          // no keyboard on a phone
    el.setAttribute('aria-hidden', 'true')
    el.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;padding:0;border:0;margin:0;opacity:0.01;z-index:-1;font-size:12pt'
    doc.body.appendChild(el)
    doc.addEventListener('copy', handler, true)
    el.focus({ preventScroll: true })
    el.select()
    el.setSelectionRange(0, text.length)
    doc.execCommand('copy')
    return fired()
  } catch {
    return false
  } finally {
    doc.removeEventListener('copy', handler, true)
    el?.remove()
  }
}

// Some browsers refuse a textarea but take a selected range inside a contentEditable node.
function viaSelection(text: string): boolean {
  if (typeof document === 'undefined' || !document.body) return false
  const doc = document
  const { handler, fired } = catcher(text)
  let host: HTMLElement | undefined
  try {
    host = doc.createElement('div')
    host.contentEditable = 'true'
    host.textContent = text
    host.setAttribute('aria-hidden', 'true')
    host.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;overflow:hidden;opacity:0.01;z-index:-1;white-space:pre'
    doc.body.appendChild(host)
    doc.addEventListener('copy', handler, true)
    const range = doc.createRange()
    range.selectNodeContents(host)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
    doc.execCommand('copy')
    sel?.removeAllRanges()
    return fired()
  } catch {
    return false
  } finally {
    doc.removeEventListener('copy', handler, true)
    host?.remove()
  }
}

// Last resort: a panel with the text selected, so a long press can copy it. One at a time.
const SHEET_COPY: Record<string, { title: string; hint: string; close: string; secure: string }> = {
  vi: { title: 'Sao chép thủ công', hint: 'Nhấn giữ đoạn chữ bên dưới rồi chọn “Sao chép”.', close: 'Đóng', secure: 'Mẹo: mở trang bằng https://{host} thì nút sao chép tự chạy.' },
  en: { title: 'Copy by hand', hint: 'Press and hold the text below, then choose “Copy”.', close: 'Close', secure: 'Tip: open the page over https://{host} and the copy button works on its own.' },
  zh: { title: '手动复制', hint: '长按下面的文字，选择“复制”。', close: '关闭', secure: '提示：用 https://{host} 打开，复制按钮就能直接生效。' }, // i18n-ignore: 这张表自己带三种语言，和 sw.js 一样
}

let sheetOpen = false

function manualCopy(text: string) {
  if (sheetOpen) return
  if (typeof document === 'undefined' || !document.body || !document.documentElement) return
  sheetOpen = true
  const doc = document
  const lang = (doc.documentElement.lang || '').toLowerCase()
  const words = SHEET_COPY[lang.startsWith('zh') ? 'zh' : lang.startsWith('en') ? 'en' : 'vi']
  const overlay = doc.createElement('div')
  overlay.style.cssText = 'position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.55);padding:16px'
  const card = doc.createElement('div')
  card.style.cssText = 'background:var(--panel,#fff);color:var(--fg,#111);border-radius:14px;padding:16px;width:min(560px,100%);max-height:80vh;display:flex;flex-direction:column;gap:10px;box-shadow:0 12px 40px rgba(0,0,0,.35)'
  const title = doc.createElement('strong')
  title.textContent = words.title
  const hint = doc.createElement('div')
  hint.textContent = words.hint
  hint.style.cssText = 'opacity:.75;font-size:13px'
  const field = doc.createElement('textarea')
  field.value = text
  field.setAttribute('readonly', '')
  field.style.cssText = 'width:100%;min-height:120px;max-height:50vh;resize:none;font:inherit;font-size:14px;padding:10px;border-radius:10px;border:1px solid rgba(127,127,127,.4);background:var(--bg,#fafafa);color:inherit'
  const tip = typeof location !== 'undefined' && location.protocol === 'http:' ? doc.createElement('div') : undefined
  if (tip) {
    tip.textContent = words.secure.replace('{host}', location.hostname)
    tip.style.cssText = 'opacity:.6;font-size:12px'
  }
  const close = doc.createElement('button')
  close.textContent = words.close
  close.style.cssText = 'align-self:flex-end;padding:8px 16px;border-radius:10px;border:0;background:var(--accent,#2f6fed);color:#fff;font:inherit'
  const shut = () => { sheetOpen = false; overlay.remove() }
  close.onclick = shut
  overlay.onclick = (e) => { if (e.target === overlay) shut() }
  card.append(title, hint, field)
  if (tip) card.append(tip)
  card.append(close)
  overlay.append(card)
  doc.body.append(overlay)
  try {   // pre-select so the phone offers Copy straight away
    field.focus({ preventScroll: true })
    field.select()
    field.setSelectionRange(0, text.length)
  } catch { /* the long press still works */ }
}

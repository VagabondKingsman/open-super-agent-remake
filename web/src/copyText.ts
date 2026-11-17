// 复制到剪贴板，返回真的成没成 —— 叫「已复制」的地方必须看这个返回值。
// 网页常常开在 http（尾网地址不是 https）：那种页面 navigator.clipboard 不在，或者有但一调用就拒绝。
// 旧代码用 `navigator.clipboard?.writeText(...)` 不 await，拒绝被吞掉，按钮照样变「已复制」，剪贴板却是空的。
export async function copyText(text: string): Promise<boolean> {
  if (!text) return false
  const api = typeof navigator !== 'undefined' ? navigator.clipboard : undefined
  if (api?.writeText) {
    try {
      await api.writeText(text)   // 能写就是写了：不按 isSecureContext 拦，http 上有的浏览器也允许
      return true
    } catch { /* 下面走老办法 */ }
  }
  return legacyCopy(text)
}

// 老的 execCommand('copy')：选择一段临时 textarea 再复制。iOS 上还要 setSelectionRange。
function legacyCopy(text: string): boolean {
  try {
    const el = document.createElement('textarea')
    el.value = text
    el.setAttribute('readonly', '')
    el.style.position = 'fixed'
    el.style.top = '0'
    el.style.left = '-9999px'
    document.body.appendChild(el)
    const start = el.selectionStart
    el.select()
    el.setSelectionRange?.(start ?? 0, text.length)
    const ok = document.execCommand('copy')
    el.remove()
    if (ok) return true
  } catch { /* thu duong duoi */ }
  return contentEditableCopy(text)
}

// contentEditable + Range: co trinh duyet chi nhan duong nay khi textarea bi chan
function contentEditableCopy(text: string): boolean {
  try {
    const host = document.createElement('div')
    host.contentEditable = 'true'
    host.textContent = text
    host.style.position = 'fixed'
    host.style.top = '0'
    host.style.left = '-9999px'
    host.style.whiteSpace = 'pre'
    document.body.appendChild(host)
    const range = document.createRange()
    range.selectNodeContents(host)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
    const ok = document.execCommand('copy')
    host.remove()
    sel?.removeAllRanges()
    return ok
  } catch {
    return false
  }
}

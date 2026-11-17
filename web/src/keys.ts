import type { KeyboardEvent } from 'react'

// 按了回车，而且不是输入法里的回车：用拼音选字、把拼音原样上屏时按的回车不算。
// Chrome 里这时 isComposing 是 true；Safari 和桌面 / 手机 App（WebKit）先结束拼字再发 keydown，
// isComposing 已经变回 false，只能靠 keyCode 229（“输入法在处理这个键”）认出来。
export type KeyLike = {
  key: string; shiftKey: boolean; ctrlKey: boolean; metaKey: boolean; keyCode: number
  nativeEvent: { isComposing: boolean }
}

export const isEnter = (e: KeyLike) => e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229

export type SendMode = 'enter' | 'ctrl'

// 哪种模式下这一下回车才发出去：默认 Enter 发；设成 ctrl 模式后 Enter 只换行，要 Ctrl/Cmd+Enter 才发（Shift+Enter 仍换行）
export const shouldSend = (e: KeyLike, mode: SendMode) => {
  if (!isEnter(e) || e.shiftKey) return false
  return mode === 'ctrl' ? (e.ctrlKey || e.metaKey) : !e.ctrlKey && !e.metaKey
}

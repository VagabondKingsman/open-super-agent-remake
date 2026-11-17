import { useSyncExternalStore } from 'react'
import type { SendMode } from './keys'

// 每条设备自己选：回车发、还是 Ctrl+Enter 才发。存 localStorage，跨标签页同步。
const KEY = 'osa.send'
const listeners = new Set<() => void>()

export const getSendMode = (): SendMode => (localStorage.getItem(KEY) === 'ctrl' ? 'ctrl' : 'enter')

export const setSendMode = (m: SendMode) => {
  localStorage.setItem(KEY, m)
  listeners.forEach(f => f())
}

const subscribe = (f: () => void) => {
  listeners.add(f)
  const onStorage = (e: StorageEvent) => { if (e.key === KEY) f() }
  window.addEventListener('storage', onStorage)
  return () => { listeners.delete(f); window.removeEventListener('storage', onStorage) }
}

export const useSendMode = () => useSyncExternalStore(subscribe, getSendMode, () => 'enter' as SendMode)

import { createElement, Fragment, type ReactNode } from 'react'
import en from './locales/en.json'
import vi from './locales/vi.json'

// 界面语言。中文原文就是翻译的键：t('保存') 在英文界面显示 locales/en.json 里“保存”对应的英文，没有翻译就显示中文。
// 语言存在服务端（服务端发的报错、卡片、推送也用它），这里在 localStorage 留一份，打开页面时不用等接口就知道用哪种。
// 改了界面文字记得同步改 en.json 和 vi.json，`uv run python -m osa.i18n` 会列出缺的和多余的。
export type Lang = 'vi' | 'zh' | 'en'

export const languages: { value: Lang; label: string }[] = [
  { value: 'vi', label: 'Tiếng Việt' },
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' }, // i18n-ignore: language endonym
]
export const isLang = (value: unknown): value is Lang => value === 'vi' || value === 'en' || value === 'zh'

export const detect = (language = navigator.language || ''): Lang => {
  const value = language.toLowerCase()
  return value.startsWith('vi') ? 'vi' : value.startsWith('zh') ? 'zh' : 'en'
}
const saved = localStorage.getItem('osa.lang')
const legacy = localStorage.getItem('osa.locale')
export const lang: Lang = isLang(saved) ? saved : isLang(legacy) ? legacy : 'vi'
// Migrate the old i18next preference once; never replace a valid osa.lang.
if (isLang(legacy)) {
  localStorage.setItem('osa.lang', lang)
  localStorage.removeItem('osa.locale')
}
export const locale = { vi: 'vi-VN', en: 'en-US', zh: 'zh-CN' }[lang]
document.documentElement.lang = locale
// The service worker cannot read localStorage, and Chrome hides the Cookie header
// from its fetch handler. Mirror the UI language into Cache Storage instead.
// The value is vi, en, or zh. It is not a secret.
const LANG_CACHE = 'osa-lang'
const LANG_KEY = '/osa-lang'
let langWrite: Promise<void> = Promise.resolve()
function persistLang(value: Lang): Promise<void> {
  if (typeof caches === 'undefined') return Promise.resolve()
  langWrite = langWrite
    .catch(() => undefined)
    .then(() => caches.open(LANG_CACHE))
    .then(cache => cache.put(LANG_KEY, new Response(value)))
    .then(() => undefined)
    .catch(() => undefined)
  return langWrite
}
void persistLang(lang)

const dict: Record<string, string | string[]> = lang === 'vi' ? vi : lang === 'en' ? en : {}
type Vars = Record<string, string | number>

// 英文可以写成 ["{n} task", "{n} tasks"]：n 是 1 用第一个，否则用第二个
function pick(keys: string[], vars?: Record<string, unknown>): string | undefined {
  for (const k of keys) {
    const v = dict[k]
    if (v !== undefined) return Array.isArray(v) ? v[vars?.n === 1 ? 0 : 1] : v
  }
}

const fill = (s: string, vars?: Vars) => vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s

/** 翻译一句话。变量写成 {名字}：t('最多 {n} MB', { n: 5 }) */
export function t(zh: string, vars?: Vars): string {
  return fill(pick([zh], vars) ?? zh, vars)
}

/** 同一句中文在不同地方要翻成不同英文时，加个场景：en.json 里的键写成 “场景::中文” */
export function tc(ctx: string, zh: string, vars?: Vars): string {
  return fill(pick([ctx + '::' + zh, zh], vars) ?? zh, vars)
}

/** 句子里要嵌元素（链接、加粗）时用：tn('点 {b} 保存', { b: <b>…</b> }) */
export function tn(zh: string, vars: Record<string, ReactNode>): ReactNode {
  const s = pick([zh], vars) ?? zh
  const parts = s.split(/\{(\w+)\}/)
  return createElement(Fragment, null, ...parts.map((p, i) => (i % 2 ? (p in vars ? vars[p] : `{${p}}`) : p)))
}

/** 服务端的语言和这里不一样（换了设备、在设置里改了）：记下来重新加载，所有文字一起换 */
export function syncLang(server: string | undefined) {
  if (isLang(server) && server !== lang) {
    localStorage.setItem('osa.lang', server)
    void persistLang(server)
    location.reload()
    return true
  }
  return false
}

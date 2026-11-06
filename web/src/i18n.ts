import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import vi from './locales/vi/common.json'
import en from './locales/en/common.json'
import zh from './locales/zh/common.json'

export const LOCALES = [
  { code: 'vi', label: 'Tiếng Việt' },
  { code: 'en', label: 'English' },
  { code: 'zh', label: 'Tiếng Trung' },
] as const

export type LocaleCode = (typeof LOCALES)[number]['code']

const saved = (typeof localStorage !== 'undefined' && localStorage.getItem('osa.locale')) || ''
const initial = (['vi', 'en', 'zh'] as const).includes(saved as LocaleCode) ? saved : 'vi'

const LANG_TAG: Record<string, string> = { vi: 'vi-VN', en: 'en-US', zh: 'zh-CN' }

function applyDocumentLang(code: string) {
  if (typeof document !== 'undefined') document.documentElement.lang = LANG_TAG[code] || code
}

applyDocumentLang(initial)

void i18n.use(initReactI18next).init({
  resources: {
    vi: { translation: vi },
    en: { translation: en },
    zh: { translation: zh },
  },
  lng: initial,
  fallbackLng: ['en'],
  interpolation: { escapeValue: false },
  parseMissingKeyHandler: (key) => key,
  returnNull: false,
})


export function setLocale(code: LocaleCode) {
  localStorage.setItem('osa.locale', code)
  applyDocumentLang(code)
  return i18n.changeLanguage(code)
}

/** BCP-47 tag for Date#toLocaleString — follows current UI locale. */
export function dateLocale(): string {
  return LANG_TAG[i18n.language] || i18n.language || 'vi'
}

export default i18n

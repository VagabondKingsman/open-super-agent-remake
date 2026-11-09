import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { Icon } from '../icons'
import { formatUnitUsd } from '../formatUsd'
import { t } from '../i18n'
import type { ModelInfo } from '../types'

// 设置页共用的小部件：分区标题、保存后的提示、价格格式

export function Section({ title, desc, action, children }: { title: string; desc?: ReactNode; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="set-sec">
      <div className="set-sec-head">
        <div><h3>{title}</h3>{desc && <p>{desc}</p>}</div>
        {action}
      </div>
      {children}
    </section>
  )
}

const ToastCtx = createContext<(msg: string, bad?: boolean) => void>(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastHost({ children }: { children: ReactNode }) {
  const [t, setT] = useState<{ msg: string; bad?: boolean; id: number } | null>(null)
  const show = useCallback((msg: string, bad?: boolean) => {
    const id = Date.now()
    setT({ msg, bad, id })
    setTimeout(() => setT(x => (x?.id === id ? null : x)), bad ? 4000 : 1800)
  }, [])
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {t && <div key={t.id} className={'toast' + (t.bad ? ' bad' : '')}><Icon name={t.bad ? 'alert' : 'check'} size={15} />{t.msg}</div>}
    </ToastCtx.Provider>
  )
}

// Unit price: USD per million tokens.
export function money(n: number | null | undefined) {
  if (n === undefined || n === null) return ''
  if (n === 0) return t('免费')
  return formatUnitUsd(n)
}

export function priceText(info: ModelInfo | undefined) {
  if (!info) return ''
  if (info.source === 'local') return t('本机运行，免费')
  if (info.input === undefined) return ''
  if (!info.input && !info.output) return t('免费')
  const main = t('输入 {input} · 输出 {output} / 百万 token', { input: money(info.input), output: money(info.output) })
  return info.offpeak ? t('{main}（空闲时段 {input} · {output}）', { main, input: money(info.offpeak[0]), output: money(info.offpeak[1]) }) : main
}

export function priceSource(info: ModelInfo | undefined) {
  if (!info?.source) return t('models.dev 里没有找到这个模型的单价，费用按 0 计')
  if (info.source === 'config') return t('单价写在 config.yaml 的 pricing 里，分高峰和空闲两档')
  if (info.source === 'local') return t('本机或内网的模型，费用按 0 计')
  return info.via ? t('单价自动从 models.dev 获取（按 {via} 的价格估算）', { via: info.via }) : t('单价自动从 models.dev 获取')
}

export function PriceTag({ info }: { info: ModelInfo | undefined }) {
  const text = priceText(info)
  return <span className={'chip' + (text ? '' : ' faint')} title={priceSource(info)}>{text || t('没有单价')}</span>
}

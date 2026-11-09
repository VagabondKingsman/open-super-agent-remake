import { Suspense, type ReactNode } from 'react'
import { t } from './i18n'

// Heavy, rarely-opened screens load on demand; this shows while the chunk arrives.
export function Lazy({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="muted">{t('加载中…')}</div>}>{children}</Suspense>
}

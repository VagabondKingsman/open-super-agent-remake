/** Spend in USD. Under $1 keep 4 decimals ($0.0123). Under $0.0001 keep 6. */
export function formatUsd(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(Number(n))) return '$0'
  const sign = n < 0 ? '-' : ''
  const v = Math.abs(n)
  if (v === 0) return '$0'
  const digits = v >= 1 ? 2 : v >= 0.0001 ? 4 : 6
  let body = v.toFixed(digits)
  if (digits > 2) body = body.replace(/0+$/, '').replace(/\.$/, '')
  return sign + '$' + body
}

/** Unit price in USD per million tokens. Small rates keep 4 significant digits ($0.003). */
export function formatUnitUsd(n: number): string {
  const sign = n < 0 ? '-' : ''
  const v = Math.abs(n)
  if (v === 0) return '$0'
  const body = v >= 100 ? String(Math.round(v)) : v >= 1 ? String(+v.toFixed(2)) : String(+v.toPrecision(4))
  return sign + '$' + body
}

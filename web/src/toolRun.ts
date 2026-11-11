import type { Stream, ToolRun } from './types'

export type ToolFrame = { name: string; state: 'run' | 'ok' | 'err'; brief?: string; ms?: number }

/** A3: 把一条 tool 帧并进这一轮的 chip 列表。run 追加，ok/err 收尾同名里最后一个未完成的。 */
export function applyToolRun(st: Stream, d: ToolFrame): Stream {
  const runs = st.tools || []
  if (d.state === 'run') {
    return { ...st, tools: [...runs, { name: d.name, state: 'run', brief: d.brief, at: Date.now() }] }
  }
  let i = -1
  for (let k = runs.length - 1; k >= 0; k--) if (runs[k].name === d.name && runs[k].state === 'run') { i = k; break }
  if (i < 0) return st
  const next = runs.slice()
  next[i] = { ...next[i], state: d.state, ms: d.ms }
  return { ...st, tools: next }
}

import type { Stream } from './types'

/** Apply one `stream` event to the live reply. `reset` means the server retried the call: drop what was shown. */
export function applyStream(st: Stream, d: { delta?: string; thinking?: string; reset?: boolean }): Stream {
  if (d.reset) return { ...st, text: '', thinking: '' }
  return { ...st, text: st.text + (d.delta || ''), thinking: st.thinking + (d.thinking || '') }
}

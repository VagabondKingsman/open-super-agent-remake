const BASE_MS = 1500
const MAX_MS = 30_000

/** Delay before reconnect attempt `attempt` (0-based): 1.5s doubling up to 30s, plus up to 20% jitter. */
export function reconnectDelay(attempt: number, rand: number = Math.random()): number {
  const base = Math.min(MAX_MS, BASE_MS * 2 ** Math.max(0, attempt))
  return Math.round(base * (1 + 0.2 * rand))
}

/** One pending auto-retry. A manual retry cancels it so two sockets are not opened. */
export function createReconnectScheduler(
  setTimer: (fn: () => void, ms: number) => unknown,
  clearTimer: (id: unknown) => void,
) {
  let pending: unknown = null
  return {
    cancel() {
      if (pending !== null) {
        clearTimer(pending)
        pending = null
      }
    },
    schedule(fn: () => void, delay: number) {
      this.cancel()
      pending = setTimer(() => {
        pending = null
        fn()
      }, delay)
    },
    armed() {
      return pending !== null
    },
  }
}

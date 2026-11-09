const BASE_MS = 1500
const MAX_MS = 30_000

/** Delay before reconnect attempt `attempt` (0-based): 1.5s doubling up to 30s, plus up to 20% jitter. */
export function reconnectDelay(attempt: number, rand: number = Math.random()): number {
  const base = Math.min(MAX_MS, BASE_MS * 2 ** Math.max(0, attempt))
  return Math.round(base * (1 + 0.2 * rand))
}

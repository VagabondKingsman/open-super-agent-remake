const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const read = f => fs.readFileSync(path.join(__dirname, '../src', f), 'utf8')
const js = read('reconnect.ts')
  .replace(/export function reconnectDelay\([^)]*\)[^{]*/, 'function reconnectDelay(attempt, rand = Math.random())')
  .replace(/export function createReconnectScheduler\([\s\S]*?\) \{/, 'function createReconnectScheduler(setTimer, clearTimer) {')
  .replace('let pending: unknown = null', 'let pending = null')
  .replace('schedule(fn: () => void, delay: number)', 'schedule(fn, delay)')
  .replace(/const (BASE_MS|MAX_MS)/g, 'var $1')
const { reconnectDelay, createReconnectScheduler } = vm.runInNewContext(js + '\n;({ reconnectDelay, createReconnectScheduler })', { Math })

test('reconnect delay doubles from 1.5s and caps at 30s', () => {
  const seq = [0, 1, 2, 3, 4, 5, 6, 20].map(n => reconnectDelay(n, 0))
  assert.deepEqual(seq, [1500, 3000, 6000, 12000, 24000, 30000, 30000, 30000])
})

test('reconnect jitter adds at most 20%', () => {
  assert.equal(reconnectDelay(0, 1), 1800)
  assert.equal(reconnectDelay(10, 1), 36000)
  for (let i = 0; i < 50; i++) {
    const d = reconnectDelay(2)
    assert.ok(d >= 6000 && d <= 7200)
  }
})

test('a new schedule cancels the one still waiting', () => {
  const queued = new Map()
  let n = 0
  const sched = createReconnectScheduler(
    (fn, ms) => { const id = ++n; queued.set(id, { fn, ms }); return id },
    id => queued.delete(id),
  )
  let ran = 0
  sched.schedule(() => ran++, 1500)
  sched.schedule(() => ran++, 8000)
  assert.equal(queued.size, 1)
  const id = [...queued.keys()][0]
  const only = queued.get(id)
  assert.equal(only.ms, 8000)
  only.fn()
  queued.delete(id)
  assert.equal(ran, 1)
  assert.equal(sched.armed(), false)
  sched.schedule(() => {}, 10)
  assert.equal(sched.armed(), true)
  sched.cancel()
  assert.equal(queued.size, 0)
  assert.equal(sched.armed(), false)
})

test('store.ts backs off on close and resets the counter on open', () => {
  const store = read('store.ts')
  assert.match(store, /import \{ createReconnectScheduler, reconnectDelay \} from '\.\/reconnect'/)
  assert.match(store, /reconnectTimer\.schedule\(\(\) => connect\(\), reconnectDelay\(attempts\+\+\)\)/)
  assert.match(store, /ws\.onopen = \(\) => \{ attempts = 0;/)
  assert.match(store, /const MANUAL_MS = 8000/)
  assert.match(store, /export function reconnectNow\(\)/)
  const vis = store.slice(store.indexOf("document.addEventListener('visibilitychange'"), store.indexOf('let attempts'))
  assert.ok(vis.indexOf('abandonManual()') >= 0 && vis.indexOf('abandonManual()') < vis.indexOf('connect()'))
  assert.match(store, /sock !== ws/)
  assert.doesNotMatch(store, /setTimeout\(connect, 1500\)/)
  assert.doesNotMatch(store, /\.navigate\(/)
})

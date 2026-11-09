const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const read = f => fs.readFileSync(path.join(__dirname, '../src', f), 'utf8')
const js = read('reconnect.ts')
  .replace(/export function reconnectDelay\([^)]*\)[^{]*/, 'function reconnectDelay(attempt, rand = Math.random())')
  .replace(/const (BASE_MS|MAX_MS)/g, 'var $1')
const { reconnectDelay } = vm.runInNewContext(js + '\n;({ reconnectDelay })', { Math })

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

test('store.ts backs off on close and resets the counter on open', () => {
  const store = read('store.ts')
  assert.match(store, /import \{ reconnectDelay \} from '\.\/reconnect'/)
  assert.match(store, /setTimeout\(connect, reconnectDelay\(attempts\+\+\)\)/)
  assert.match(store, /ws\.onopen = \(\) => \{ attempts = 0;/)
  assert.doesNotMatch(store, /setTimeout\(connect, 1500\)/)
})

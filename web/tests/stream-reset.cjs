const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const src = fs.readFileSync(path.join(__dirname, '../src/streamDelta.ts'), 'utf8')
const js = src
  .replace(/^import type .*$/m, '')
  .replace(/export function applyStream\([^)]*\)[^{]*/, 'function applyStream(st, d)')
const { applyStream } = vm.runInNewContext(js + '\n;({ applyStream })')

test('stream deltas append text and thinking', () => {
  let st = { sid: 's', text: '', thinking: '', started: 0, bot_id: 1 }
  st = applyStream(st, { thinking: 'a' })
  st = applyStream(st, { delta: 'b' })
  assert.equal(st.thinking, 'a')
  assert.equal(st.text, 'b')
})

test('reset after a server retry clears shown thinking so it is not duplicated', () => {
  let st = { sid: 's', text: '', thinking: 'đang nghĩ', started: 0, bot_id: 1 }
  st = applyStream(st, { reset: true })
  st = applyStream(st, { thinking: 'đang nghĩ' })
  assert.equal(st.thinking, 'đang nghĩ')
  assert.equal(st.text, '')
})

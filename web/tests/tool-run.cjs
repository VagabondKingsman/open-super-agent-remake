const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const src = fs.readFileSync(path.join(__dirname, '../src/toolRun.ts'), 'utf8')
const js = src
  .replace(/^import type .*$/m, '')
  .replace(/^export type .*$/m, '')
  .replace(/export function applyToolRun\([^)]*\)[^{]*/, 'function applyToolRun(st, d)')
const { applyToolRun } = vm.runInNewContext(js + '\n;({ applyToolRun })')

const base = { sid: 's', text: '', thinking: '', started: 0, bot_id: 1 }

test('a tool run appears, then completes with its duration', () => {
  let st = applyToolRun(base, { name: 'quick_code', state: 'run', brief: 'x*2' })
  assert.equal(st.tools.length, 1)
  assert.equal(st.tools[0].state, 'run')
  assert.equal(st.tools[0].brief, 'x*2')
  st = applyToolRun(st, { name: 'quick_code', state: 'ok', ms: 420 })
  assert.equal(st.tools[0].state, 'ok')
  assert.equal(st.tools[0].ms, 420)
  assert.equal(base.tools, undefined, 'input stream is left untouched')
})

test('the same tool twice keeps two chips, matched in order', () => {
  let st = applyToolRun(base, { name: 'read_file', state: 'run' })
  st = applyToolRun(st, { name: 'read_file', state: 'ok', ms: 10 })
  st = applyToolRun(st, { name: 'read_file', state: 'run' })
  st = applyToolRun(st, { name: 'read_file', state: 'err', ms: 20 })
  assert.equal(st.tools.map(r => r.state).join(','), 'ok,err')   // vm 里是另一个 realm 的数组，按文本比
})

test('a finish for a tool that never started is ignored', () => {
  const st = applyToolRun(base, { name: 'ghost', state: 'ok', ms: 1 })
  assert.equal(st.tools, undefined)
})

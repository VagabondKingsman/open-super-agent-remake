// Enter gửi, hay Ctrl+Enter mới gửi (Enter chỉ xuống dòng). Ở chế độ ctrl, Enter TRẦN không được gửi.
const test = require('node:test')
const assert = require('node:assert')
const fs = require('node:fs')
const path = require('node:path')
const { execFileSync } = require('node:child_process')

const dir = fs.mkdtempSync(path.join(__dirname, '../node_modules/.osa-keys-test-'))
let mod
try {
  fs.copyFileSync(path.join(__dirname, '../src/keys.ts'), path.join(dir, 'keys.cts'))
  fs.writeFileSync(path.join(dir, 'tsconfig.json'), JSON.stringify({
    compilerOptions: { module: 'node16', target: 'es2022', outDir: './out' }, include: ['keys.cts'],
  }))
  execFileSync(path.join(__dirname, '../node_modules/.bin/tsc'), ['--project', path.join(dir, 'tsconfig.json')], { stdio: 'pipe' })
  mod = require(path.join(dir, 'out/keys.cjs'))
} finally {
  fs.rmSync(dir, { recursive: true, force: true })
}

const key = (o = {}) => ({ key: 'Enter', shiftKey: false, ctrlKey: false, metaKey: false, keyCode: 13, nativeEvent: { isComposing: false }, ...o })

test('chế độ enter: Enter gửi, Shift+Enter xuống dòng', () => {
  assert.equal(mod.shouldSend(key(), 'enter'), true)
  assert.equal(mod.shouldSend(key({ shiftKey: true }), 'enter'), false)
})

test('chế độ ctrl: Enter TRẦN chỉ xuống dòng', () => {
  assert.equal(mod.shouldSend(key(), 'ctrl'), false)
})

test('chế độ ctrl: Ctrl+Enter và Cmd+Enter mới gửi', () => {
  assert.equal(mod.shouldSend(key({ ctrlKey: true }), 'ctrl'), true)
  assert.equal(mod.shouldSend(key({ metaKey: true }), 'ctrl'), true)
})

test('đang gõ tiếng Việt bằng bộ gõ thì Enter không gửi', () => {
  assert.equal(mod.shouldSend(key({ nativeEvent: { isComposing: true } }), 'enter'), false)
  assert.equal(mod.shouldSend(key({ keyCode: 229 }), 'ctrl'), false)
})

test('phím khác Enter không gửi', () => {
  assert.equal(mod.shouldSend(key({ key: 'a' }), 'enter'), false)
  assert.equal(mod.shouldSend(key({ key: 'a' }), 'ctrl'), false)
})

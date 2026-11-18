// Copy must really reach the clipboard, and "copied" may only show when it did.
// Android Chrome and WebViews return true from execCommand('copy') while copying nothing, so the
// helper trusts the browser's own copy event instead, and falls back to a hand-copy panel.
const test = require('node:test')
const assert = require('node:assert')
const fs = require('node:fs')
const path = require('node:path')
const { execFileSync } = require('node:child_process')
// TypeScript 7 ships a compiler CLI, not transpileModule; a .cts copy selects CommonJS.
const dir = fs.mkdtempSync(path.join(__dirname, '../node_modules/.osa-copy-test-'))
let js
try {
  fs.copyFileSync(path.join(__dirname, '../src/copyText.ts'), path.join(dir, 'copyText.cts'))
  fs.writeFileSync(path.join(dir, 'tsconfig.json'), JSON.stringify({
    compilerOptions: { module: 'node16', target: 'es2022', outDir: './out' }, include: ['copyText.cts'],
  }))
  execFileSync(path.join(__dirname, '../node_modules/.bin/tsc'), ['--project', path.join(dir, 'tsconfig.json')], { stdio: 'pipe' })
  js = fs.readFileSync(path.join(dir, 'out/copyText.cjs'), 'utf8')
} finally {
  fs.rmSync(dir, { recursive: true, force: true })
}

const node = () => ({
  value: '', textContent: '', contentEditable: '', children: [], removed: false,
  style: { cssText: '' },
  setAttribute() {}, remove() { this.removed = true }, select() {}, setSelectionRange() {},
  focus() {}, append(...kids) { this.children.push(...kids) }, appendChild(kid) { this.children.push(kid) },
})

// A document small enough to reason about: execCommand either fires the browser's copy event
// (which is what a real copy looks like) or just returns a value.
function load(env) {
  const mod = { exports: {} }
  const listeners = []
  const body = node()
  const doc = {
    documentElement: { lang: env.lang || 'vi-VN' },
    body,
    createElement: () => node(),
    createRange: () => ({ selectNodeContents() {} }),
    addEventListener(type, fn) { if (type === 'copy') listeners.push(fn) },
    removeEventListener(type, fn) { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1) },
    execCommand() {
      const ret = env.execCommand
      if (ret && ret.fire) {
        for (const fn of [...listeners]) fn({ clipboardData: { setData: (_, value) => { env.clipboard = value } }, preventDefault() {} })
      }
      return !!(ret && ret.ok)
    },
  }
  const win = { isSecureContext: !!env.secure, getSelection: () => ({ removeAllRanges() {}, addRange() {} }) }
  new Function('module', 'exports', 'navigator', 'window', 'document', 'setTimeout', js)(
    mod, mod.exports, env.navigator || {}, win, doc, setTimeout)
  return { copyText: mod.exports.copyText, body }
}

test('trang https thì đi thẳng clipboard API', async () => {
  let written = ''
  const { copyText, body } = load({
    secure: true,
    navigator: { clipboard: { writeText: async (t) => { written = t } } },
    execCommand: { ok: false },
  })
  assert.equal(await copyText('xin chào'), true)
  assert.equal(written, 'xin chào')
  assert.equal(body.children.length, 0, 'không mở bảng thủ công khi đã copy được')
})

test('http không có clipboard API: copy qua copy event, chữ do mình đặt', async () => {
  const { copyText } = load({ secure: false, execCommand: { ok: true, fire: true } })
  assert.equal(await copyText('abc'), true)
})

test('execCommand trả true mà không có copy event (Android) thì KHÔNG báo thành công', async () => {
  const { copyText, body } = load({ secure: false, execCommand: { ok: true, fire: false } })
  assert.equal(await copyText('abc'), false)
  const sheet = body.children.at(-1)
  assert.ok(sheet, 'phải mở bảng copy thủ công')
})

test('bảng thủ công chứa đúng đoạn chữ để người dùng tự copy', async () => {
  const { copyText, body } = load({ secure: false, execCommand: { ok: false } })
  assert.equal(await copyText('nội dung cần copy'), false)
  const find = (n) => n.value === 'nội dung cần copy' || (n.children || []).some(find)
  assert.ok(body.children.some(find), 'chữ phải nằm trong bảng để còn cách copy')
})

test('clipboard API bị từ chối thì vẫn thử đường execCommand', async () => {
  const { copyText } = load({
    secure: true,
    navigator: { clipboard: { writeText: async () => { throw new Error('denied') } } },
    execCommand: { ok: true, fire: true },
  })
  assert.equal(await copyText('abc'), true)
})

test('không có gì để copy thì không giả vờ thành công', async () => {
  const { copyText, body } = load({ secure: false, execCommand: { ok: true, fire: true } })
  assert.equal(await copyText(''), false)
  assert.equal(body.children.length, 0)
})

// 复制要真把内容放进剪贴板，并且「已复制」只在真的成功时才显示。
// 网页常常开在 http（尾网地址不是 https），此时 navigator.clipboard 不在或直接拒绝 —— 旧代码用 ?. 把它吞掉，
// 按钮照样变「已复制」，剪贴板里却什么都没有。
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

function load(env) {
  const mod = { exports: {} }
  const doc = {
    body: { appendChild() {}, removeChild() {} },
    createElement: () => ({ value: '', style: {}, setAttribute() {}, select() {}, remove() {}, setSelectionRange() {} }),
    execCommand: env.execCommand,
    queryCommandSupported: env.queryCommandSupported,
  }
  new Function('module', 'exports', 'navigator', 'window', 'document', 'setTimeout', js)(
    mod, mod.exports, env.navigator, env.window, doc, setTimeout)
  return mod.exports.copyText
}

test('dùng clipboard API khi trang là https', async () => {
  let written = ''
  const copyText = load({
    navigator: { clipboard: { writeText: async (t) => { written = t } } },
    window: { isSecureContext: true }, execCommand: () => false,
  })
  assert.equal(await copyText('xin chào'), true)
  assert.equal(written, 'xin chào')
})

test('không có clipboard API trên http thì vẫn copy được bằng textarea', async () => {
  let copied = ''
  const copyText = load({
    navigator: {},                       // http: không có navigator.clipboard
    window: { isSecureContext: false },
    execCommand: () => { copied = 'da copy'; return true },
  })
  assert.equal(await copyText('abc'), true)
  assert.equal(copied, 'da copy')
})

test('clipboard API từ chối (http) thì rơi xuống textarea, không báo thành công giả', async () => {
  const copyText = load({
    navigator: { clipboard: { writeText: async () => { throw new Error('denied') } } },
    window: { isSecureContext: false },
    execCommand: () => true,
  })
  assert.equal(await copyText('abc'), true)
})

test('cả hai đường đều hỏng thì trả false để UI báo thất bại', async () => {
  const copyText = load({
    navigator: { clipboard: { writeText: async () => { throw new Error('denied') } } },
    window: { isSecureContext: true },
    execCommand: () => false,
  })
  assert.equal(await copyText('abc'), false)
})

test('không có gì để copy thì không giả vờ thành công', async () => {
  const copyText = load({ navigator: {}, window: { isSecureContext: false }, execCommand: () => true })
  assert.equal(await copyText(''), false)
})

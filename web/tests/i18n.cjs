const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const { execFileSync } = require('node:child_process')
// TypeScript 7 ships a compiler CLI, not the old transpileModule API.
// A .cts copy selects CommonJS without changing the production source.
const compiled = fs.mkdtempSync(path.join(__dirname, '../node_modules/.osa-i18n-test-'))
let code
try {
  fs.copyFileSync(path.join(__dirname, '../src/i18n.ts'), path.join(compiled, 'i18n.cts'))
  fs.cpSync(path.join(__dirname, '../src/locales'), path.join(compiled, 'locales'), { recursive: true })
  fs.writeFileSync(path.join(compiled, 'tsconfig.json'), JSON.stringify({
    compilerOptions: { module: 'node16', target: 'es2022', esModuleInterop: true, resolveJsonModule: true, skipLibCheck: true, outDir: './out' },
    include: ['i18n.cts'],
  }))
  execFileSync(path.join(__dirname, '../node_modules/.bin/tsc'), ['--project', path.join(compiled, 'tsconfig.json')], { stdio: 'pipe' })
  code = fs.readFileSync(path.join(compiled, 'out/i18n.cjs'), 'utf8')
} finally {
  fs.rmSync(compiled, { recursive: true, force: true })
}
function load(saved = {}, browser = 'en-US') {
  const data = new Map(Object.entries(saved))
  const cache = new Map()
  let reloads = 0
  const sandbox = {
    exports: {}, navigator: { language: browser }, document: { documentElement: {} },
    location: { reload() { reloads++ } },
    localStorage: { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: k => data.delete(k) },
    Response,
    caches: {
      open: async () => ({
        put: async (key, response) => { cache.set(key, await response.text()) },
        match: async key => cache.has(key) ? new Response(cache.get(key)) : undefined,
      }),
    },
    require: name => name === 'react' ? require('react') : require(path.join(__dirname, '../src', name)),
  }
  vm.runInNewContext(code, sandbox)
  return { api: sandbox.exports, data, cache, document: sandbox.document, reloads: () => reloads }
}
async function waitLang(state, expected) {
  for (let i = 0; i < 20; i++) {
    if (state.cache.get('/osa-lang') === expected) return
    await new Promise(resolve => setTimeout(resolve, 0))
  }
  assert.equal(state.cache.get('/osa-lang'), expected)
}

test('raw HTML shell language is vi-VN before JavaScript init', () => {
  const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8')
  const match = html.match(/<html\b[^>]*\blang="([^"]*)"/)
  assert.equal(match?.[1], 'vi-VN')
})
test('fresh install defaults to Vietnamese, independent of browser', async () => {
  const state = load()
  const { api, document } = state
  assert.equal(api.lang, 'vi')
  assert.equal(api.locale, 'vi-VN')
  assert.equal(document.documentElement.lang, 'vi-VN')
  await waitLang(state, 'vi')
  assert.equal(api.t('保存'), 'Lưu')
  assert.equal(api.t('任务 #{id}', { id: 7 }), 'Tác vụ #7')
  assert.equal(api.tc('weekday', '一'), 'T2')
  assert.equal(api.t('{n} 个 Bot', { n: 2 }), '2 Bot')
})
for (const language of ['vi', 'en', 'zh']) {
  test(`honors saved osa.lang=${language}`, () => assert.equal(load({ 'osa.lang': language }).api.lang, language))
  test(`migrates legacy ${language} once`, () => {
    const first = load({ 'osa.locale': language })
    assert.equal(first.api.lang, language)
    assert.equal(first.data.get('osa.lang'), language)
    assert.equal(first.data.has('osa.locale'), false)
    assert.equal(load(Object.fromEntries(first.data)).api.lang, language)
  })
}
test('osa.lang wins over legacy locale; invalid values default to vi', () => {
  assert.equal(load({ 'osa.lang': 'en', 'osa.locale': 'zh' }).api.lang, 'en')
  assert.equal(load({ 'osa.lang': 'xx', 'osa.locale': 'xx' }).api.lang, 'vi')
})
test('detection recognizes vi and zh prefixes, others as en', () => {
  const { api } = load()
  for (const [value, expected] of [['vi-VN', 'vi'], ['VI', 'vi'], ['zh-TW', 'zh'], ['en-GB', 'en'], ['fr', 'en'], ['', 'en']]) assert.equal(api.detect(value), expected)
})
test('sync accepts all three languages and rejects unknown values', async () => {
  const state = load({ 'osa.lang': 'en' })
  await waitLang(state, 'en')
  assert.equal(state.api.syncLang('en'), false)
  assert.equal(state.api.syncLang('xx'), false)
  assert.equal(state.api.syncLang('vi'), true)
  assert.equal(state.data.get('osa.lang'), 'vi')
  await waitLang(state, 'vi')
  assert.equal(state.reloads(), 1)
  assert.deepEqual(Array.from(state.api.languages, item => item.label), ['Tiếng Việt', 'English', '中文'])
})

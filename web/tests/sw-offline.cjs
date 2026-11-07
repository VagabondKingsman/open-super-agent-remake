const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const root = path.join(__dirname, '..')
const swPath = path.join(root, 'public/sw.js')
const swSource = fs.readFileSync(swPath, 'utf8')
const CJK = /[\u3400-\u9fff]/

function load() {
  const listeners = {}
  const store = new Map()
  const sandbox = {
    module: { exports: {} },
    exports: {},
    Response,
    caches: {
      open: async () => ({
        match: async key => store.has(key) ? new Response(store.get(key)) : undefined,
        put: async (key, response) => { store.set(key, await response.text()) },
      }),
    },
    self: {
      addEventListener(type, fn) { listeners[type] = fn },
      skipWaiting() {},
      clients: { claim: () => Promise.resolve() },
      registration: { showNotification: () => Promise.resolve() },
    },
    fetch: () => Promise.reject(new Error('offline')),
  }
  vm.runInNewContext(swSource, sandbox, { filename: 'sw.js' })
  return { api: sandbox.module.exports, listeners, store }
}

function commentsOf(src) {
  const blocks = src.match(/\/\*[\s\S]*?\*\//g) || []
  const lines = src.match(/(^|\n)\s*\/\/[^\n]*/g) || []
  return blocks.concat(lines).join('\n')
}

function visibleText(html) {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

const { api, listeners, store } = load()

test('offline language accepts only vi, en, zh and falls back to Vietnamese', async () => {
  assert.equal(api.offlineLang(null), 'vi')
  assert.equal(api.offlineLang(''), 'vi')
  assert.equal(api.offlineLang('fr'), 'vi')
  assert.equal(api.offlineLang('zh-CN'), 'vi')
  assert.equal(api.offlineLang('en'), 'en')
  assert.equal(api.offlineLang('zh'), 'zh')
  assert.equal(await api.storedLang(), 'vi')
  store.set('/osa-lang', 'en')
  assert.equal(await api.storedLang(), 'en')
  store.set('/osa-lang', 'nope')
  assert.equal(await api.storedLang(), 'vi')
  store.delete('/osa-lang')
})

test('default offline page is Vietnamese first, then English, with no Chinese', () => {
  const html = api.offlinePage('vi')
  const text = visibleText(html)
  assert.match(html, /<html lang="vi">/)
  assert.match(html, /Không kết nối được máy chủ/)
  assert.match(html, /Kiểm tra dịch vụ trên máy đang chạy và mạng \(ví dụ Tailscale\) đã kết nối, rồi tải lại\./)
  assert.match(html, /Can't reach the server/)
  assert.match(html, /Make sure the server is running and your network \(e\.g\. Tailscale\) is connected, then refresh\./)
  assert.doesNotMatch(text, CJK)
  assert.ok(text.indexOf('Không kết nối được máy chủ') < text.indexOf("Can't reach the server"))
  assert.doesNotMatch(swSource, /连不上服务器 · Can't reach the server/)
})

test('English and Chinese offline pages follow the saved UI language', () => {
  const en = visibleText(api.offlinePage('en'))
  assert.match(api.offlinePage('en'), /<html lang="en">/)
  assert.match(en, /Can't reach the server/)
  assert.doesNotMatch(en, /Không kết nối được máy chủ/)
  assert.doesNotMatch(en, CJK)
  const zh = visibleText(api.offlinePage('zh'))
  assert.match(api.offlinePage('zh'), /<html lang="zh-CN">/)
  assert.match(zh, /连不上服务器/)
  assert.ok(zh.indexOf('连不上服务器') < zh.indexOf("Can't reach the server"))
})

test('a failed navigation serves the Vietnamese page when no language is stored', async () => {
  let pending
  listeners.fetch({
    request: { mode: 'navigate' },
    respondWith(value) { pending = value },
  })
  const response = await pending
  assert.equal(response.headers.get('content-type'), 'text/html; charset=utf-8')
  const text = visibleText(await response.text())
  assert.match(text, /Không kết nối được máy chủ/)
  assert.doesNotMatch(text, CJK)
})

test('a stored UI language selects that offline page', async () => {
  store.set('/osa-lang', 'en')
  let pending
  listeners.fetch({
    request: { mode: 'navigate' },
    respondWith(value) { pending = value },
  })
  const text = visibleText(await (await pending).text())
  assert.match(text, /Can't reach the server/)
  assert.doesNotMatch(text, /Không kết nối được máy chủ/)
  store.delete('/osa-lang')
})

test('non-navigation requests are not replaced with the offline page', () => {
  let called = false
  listeners.fetch({
    request: { mode: 'cors' },
    respondWith() { called = true },
  })
  assert.equal(called, false)
})

test('the page and the service worker share the same language cache key', () => {
  const i18n = fs.readFileSync(path.join(root, 'src/i18n.ts'), 'utf8')
  assert.match(swSource, /caches\.open\('osa-lang'\)/)
  assert.match(swSource, /cache\.match\('\/osa-lang'\)/)
  assert.match(i18n, /caches\.open\(LANG_CACHE\)/)
  assert.match(i18n, /const LANG_CACHE = 'osa-lang'/)
  assert.match(i18n, /const LANG_KEY = '\/osa-lang'/)
})

test('service worker comments are English and static shell files are not Chinese-only', () => {
  assert.doesNotMatch(commentsOf(swSource), CJK)
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  assert.match(html, /<html\b[^>]*\blang="vi-VN"/)
  assert.doesNotMatch(html, CJK)
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'public/manifest.json'), 'utf8'))
  assert.equal(manifest.lang, 'vi-VN')
  assert.equal(manifest.description, 'Đồng đội AI tự triển khai, luôn trực')
  assert.doesNotMatch(manifest.description, CJK)
  assert.doesNotMatch(manifest.name, CJK)
})

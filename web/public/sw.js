// Service worker: installable home-screen app, push notifications, and an offline
// page when the server cannot be reached.
// API responses and documents are not cached. Data always comes from the server.
// This worker cannot read localStorage. Chrome also hides the Cookie header from
// the fetch handler. The page mirrors the UI language into the osa-lang cache
// (vi, en, or zh). A missing or unknown value falls back to Vietnamese, the app
// default. navigator.language is ignored here: a fresh install stays Vietnamese
// even when the browser is set to another language.
// Chinese is shown only when the saved UI language is zh. English stays as the
// secondary line for vi and zh.

const OFFLINE_COPY = {
  vi: {
    htmlLang: 'vi',
    title: 'Không kết nối được máy chủ',
    hint: 'Kiểm tra dịch vụ trên máy đang chạy và mạng (ví dụ Tailscale) đã kết nối, rồi tải lại.',
  },
  en: {
    htmlLang: 'en',
    title: "Can't reach the server",
    hint: 'Make sure the server is running and your network (e.g. Tailscale) is connected, then refresh.',
  },
  zh: {
    htmlLang: 'zh-CN',
    title: '连不上服务器',
    hint: '确认电脑上的服务在运行、网络（例如 Tailscale）已连接，然后刷新。',
  },
}

function offlineLang(value) {
  return value === 'vi' || value === 'en' || value === 'zh' ? value : 'vi'
}

async function storedLang() {
  try {
    const cache = await caches.open('osa-lang')
    const saved = await cache.match('/osa-lang')
    return offlineLang(saved ? (await saved.text()).trim() : '')
  } catch {
    return 'vi'
  }
}

function offlinePage(lang) {
  const copy = OFFLINE_COPY[lang] || OFFLINE_COPY.vi
  const secondary = lang === 'en' ? '' : `<br>${OFFLINE_COPY.en.title}<br>${OFFLINE_COPY.en.hint}`
  return `<!doctype html><html lang="${copy.htmlLang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${copy.title}</title><body style="margin:0;height:100vh;display:grid;place-items:center;background:#0d0d0e;color:#a8a8ad;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;text-align:center"><div><div style="font-size:32px">◆</div>
<p>${copy.title}</p><p style="font-size:13px">${copy.hint}${secondary}</p></div>`
}

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()))

self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return
  e.respondWith((async () => {
    try {
      return await fetch(e.request)
    } catch {
      return new Response(offlinePage(await storedLang()), { headers: { 'content-type': 'text/html; charset=utf-8' } })
    }
  })())
})

self.addEventListener('push', e => {
  let d = {}
  try { d = e.data ? e.data.json() : {} } catch { d = { body: e.data && e.data.text() } }
  e.waitUntil(self.registration.showNotification(d.title || 'Super Agent', {
    body: d.body || '', tag: d.tag || undefined, renotify: !!d.tag, data: { url: d.url || '/' },
    icon: '/icon-192.png', badge: '/icon-192.png',
  }))
})

// Notification click: focus an open window and open that chat, or open a new window.
self.addEventListener('notificationclick', e => {
  e.notification.close()
  const url = (e.notification.data && e.notification.data.url) || '/'
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    const c = list.find(x => 'focus' in x)
    if (c) { c.postMessage({ type: 'open', url }); return c.focus() }
    return self.clients.openWindow(url)
  }))
})

// Node tests load this classic script in a vm. Browsers leave `module` undefined.
if (typeof module !== 'undefined' && module.exports) module.exports = { offlineLang, offlinePage, storedLang }

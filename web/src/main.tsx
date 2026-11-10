import { lazy } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { Lazy } from './lazy'
import { SharedTemplate } from './components/Templates'
import { handleExternalLinks } from './desktop'
import { initTheme } from './theme'
import './styles.css'
import 'highlight.js/styles/github-dark.css'

const SharedPage = lazy(() => import('./components/Library').then(m => ({ default: m.SharedPage })))
const SharedSkill = lazy(() => import('./components/Routines').then(m => ({ default: m.SharedSkill })))

// /s/<token> 是分享出去的页面，/skill/<token> 是技能，/template/<token> 是 Bot 模板：只显示它本身，不加载应用
const page = location.pathname.match(/^\/s\/([\w-]+)$/)
const skill = location.pathname.match(/^\/skill\/([\w-]+)$/)
const template = location.pathname.match(/^\/template\/([\w-]+)$/)
const shared = page || skill || template
createRoot(document.getElementById('root')!).render(
  page ? <Lazy><SharedPage token={page[1]} /></Lazy> : skill ? <Lazy><SharedSkill token={skill[1]} /></Lazy>
    : template ? <SharedTemplate token={template[1]} /> : <App />)

initTheme()
handleExternalLinks()   // 桌面 App 里：外站链接用系统浏览器打开

// Service Worker：添加到主屏幕、推送通知。只在 https 或本机地址下可用
if (!shared && 'serviceWorker' in navigator && isSecureContext) navigator.serviceWorker.register('/sw.js').catch(() => {})

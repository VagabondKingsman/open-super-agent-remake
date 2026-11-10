const invoke = (cmd, args) => window.__TAURI_INTERNALS__.invoke(cmd, args)

const connect = document.querySelector('#connect')
const pair = document.querySelector('#pair')
const err = document.querySelector('#err')

function showError(text) {
  err.hidden = !text
  err.textContent = text || ''
}

async function paint() {
  const s = await invoke('setup_state')
  if (s.next) {
    location.replace(s.next)
    return
  }
  if (s.pair) {
    connect.hidden = true
    pair.hidden = false
    document.querySelector('#pairServer').textContent = s.pair
    return
  }
  connect.hidden = false
  pair.hidden = true
  if (s.url) document.querySelector('#url').value = s.url
  showError(s.error)
}

document.querySelector('#remote').addEventListener('submit', async (e) => {
  e.preventDefault()
  showError('')
  try {
    await invoke('choose_remote', { url: document.querySelector('#url').value })
    await paint()
  } catch (e) {
    showError(String(e))
  }
})

document.querySelector('#pairOk').addEventListener('click', async () => {
  try { await invoke('confirm_pair'); await paint() } catch (e) { showError(String(e)) }
})
document.querySelector('#pairNo').addEventListener('click', () => invoke('cancel_pair'))

paint().catch((e) => showError(String(e)))

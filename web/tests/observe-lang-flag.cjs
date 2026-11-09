const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

// Observe shows langcheck's flag on task rows (backend: observe._tasks adds lang_flag).
const observe = fs.readFileSync(path.join(__dirname, '../src/components/Observe.tsx'), 'utf8')

test('Observe task rows render a warning tag when lang_flag is set', () => {
  assert.match(observe, /lang_flag: \{ ui: string; han: number; latin: number \} \| null/)
  assert.match(observe, /\{x\.lang_flag && <span className="tag warn"[^>]*>\{t\('语言不一致'\)\}<\/span>\}/)
  assert.match(observe, /t\('结果看起来大半是中文，和界面语言（\{ui\}）不一致', \{ ui: x\.lang_flag\.ui \}\)/)
})

for (const language of ['en', 'vi']) {
  test(`lang_flag strings are translated in ${language}`, () => {
    const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/locales', `${language}.json`), 'utf8'))
    assert.ok(catalog['语言不一致'])
    assert.match(catalog['结果看起来大半是中文，和界面语言（{ui}）不一致'], /\{ui\}/)
  })
}

const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const src = fs.readFileSync(path.join(__dirname, '../src/desktop.ts'), 'utf8')
const theme = fs.readFileSync(path.join(__dirname, '../src/theme.ts'), 'utf8')

test('an Android shell counts as a phone, an iOS shell still does', () => {
  assert.match(src, /platform\?: 'macos' \| 'ios' \| 'android'/)
  assert.match(src, /desktop\?\.platform === 'ios' \|\| desktop\?\.platform === 'android'/)
  assert.match(theme, /desktop\?\.platform === 'ios' \|\| desktop\?\.platform === 'android'/)
})

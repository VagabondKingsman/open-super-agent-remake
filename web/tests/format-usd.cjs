const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const srcPath = path.join(__dirname, '../src/formatUsd.ts')
const src = fs.readFileSync(srcPath, 'utf8')
const js = src
  .replace(/export function formatUsd\(n:[^)]*\)[^{]*/, 'function formatUsd(n)')
  .replace(/export function formatUnitUsd\(n:[^)]*\)[^{]*/, 'function formatUnitUsd(n)')
const { formatUsd, formatUnitUsd } = vm.runInNewContext(js + '\n;({ formatUsd, formatUnitUsd })')

test('spend format keeps enough decimals for small USD amounts', () => {
  assert.equal(formatUsd(0), '$0')
  assert.equal(formatUsd(null), '$0')
  assert.equal(formatUsd(undefined), '$0')
  assert.equal(formatUsd(0.0123), '$0.0123')
  assert.equal(formatUsd(0.185), '$0.185')
  assert.equal(formatUsd(0.026056), '$0.0261')
  assert.equal(formatUsd(1.2), '$1.20')
  assert.equal(formatUsd(12.345), '$12.35')
  assert.equal(formatUsd(0.00001234), '$0.000012')
  assert.equal(formatUsd(-0.0123), '-$0.0123')
})

test('unit prices stay in USD per million tokens', () => {
  assert.equal(formatUnitUsd(0), '$0')
  assert.equal(formatUnitUsd(0.003), '$0.003')
  assert.equal(formatUnitUsd(0.006), '$0.006')
  assert.equal(formatUnitUsd(0.044), '$0.044')
  assert.equal(formatUnitUsd(0.3), '$0.3')
  assert.equal(formatUnitUsd(1.32), '$1.32')
  assert.equal(formatUnitUsd(3.96), '$3.96')
  assert.equal(formatUnitUsd(10), '$10')
})

test('cost UI no longer prefixes a yuan sign', () => {
  const root = path.join(__dirname, '../..')
  const files = [
    'web/src/components/Settings.tsx',
    'web/src/components/Tasks.tsx',
    'web/src/components/settingsKit.tsx',
    'web/src/formatUsd.ts',
    'osa/static/index.html',
    'web/src/locales/en.json',
    'web/src/locales/vi.json',
  ]
  for (const rel of files) {
    const text = fs.readFileSync(path.join(root, rel), 'utf8')
    assert.equal(text.includes('¥'), false, rel)
    assert.equal(text.includes('人民币'), false, rel)
    assert.equal(text.includes('CNY'), false, rel)
  }
  const settings = fs.readFileSync(path.join(root, 'web/src/components/Settings.tsx'), 'utf8')
  const tasks = fs.readFileSync(path.join(root, 'web/src/components/Tasks.tsx'), 'utf8')
  const legacy = fs.readFileSync(path.join(root, 'osa/static/index.html'), 'utf8')
  assert.match(settings, /formatUsd\(/)
  assert.match(tasks, /formatUsd\(/)
  assert.match(legacy, /function formatUsd/)
})

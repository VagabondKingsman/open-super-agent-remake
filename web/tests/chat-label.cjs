const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

// chatLabel.ts is type-only TypeScript: strip the import line and the annotations, run it here
const src = fs.readFileSync(path.join(__dirname, '../src/chatLabel.ts'), 'utf8')
const js = src
  .replace(/^import type .*$/m, '')
  .replace(/: Pick<Chat, 'kind' \| 'title' \| 'bot_ids'>/, '')
  .replace(/: Pick<Bot, 'id' \| 'name'>\[\]/, '')
  .replace(/\): string \{/, ') {')
  .replace(/^export function /m, 'function ')
const { chatLabel } = vm.runInNewContext(js + '\n;({ chatLabel })')

const bots = [{ id: 1, name: 'Nova' }, { id: 2, name: 'AutoBot' }]
const direct = (title) => ({ kind: 'direct', title, bot_ids: [1] })

test('a group chat is its own title', () => {
  assert.equal(chatLabel({ kind: 'group', title: 'Bàn việc', bot_ids: [1, 2] }, bots), 'Bàn việc')
})

test('a direct chat is the bot name when the title says the same', () => {
  assert.equal(chatLabel(direct('Nova'), bots), 'Nova')
})

test('a second chat with the same bot carries its own title after the name', () => {
  // the whole point: two chats of bot 1 must not both read "Nova"
  assert.equal(chatLabel(direct('scratch-nova'), bots), 'Nova · scratch-nova')
})

test('a bot that is gone still shows the title it was given', () => {
  assert.equal(chatLabel({ kind: 'direct', title: 'cũ', bot_ids: [99] }, bots), 'cũ')
})

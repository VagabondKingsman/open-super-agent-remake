const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

// Execute the actual patterns used by Chat, not copies that can drift from production.
const chat = fs.readFileSync(path.join(__dirname, '../src/components/Chat.tsx'), 'utf8')
const declarations = chat.match(/^const (?:TASK_DISPATCH|TASK_RESULT|ROUTINE_LABEL) = .+$/gm)
assert.equal(declarations?.length, 3)
const { TASK_DISPATCH, TASK_RESULT, ROUTINE_LABEL } = vm.runInNewContext(
  declarations.join('\n') + '\n;({ TASK_DISPATCH, TASK_RESULT, ROUTINE_LABEL })',
)
const backendLocales = path.join(__dirname, '../../osa/locales')
for (const language of ['vi', 'en', 'zh']) {
  test(`Chat reads stored ${language} task headers regardless of UI language`, () => {
    const catalog = language === 'zh' ? {} : JSON.parse(fs.readFileSync(path.join(backendLocales, `${language}.json`), 'utf8'))
    const translate = key => (catalog[key] || key).replace('{name}', 'Audit ping').replace('{id}', '42')
    const dispatch = translate('[任务已派发]')
    const routine = translate('[定时任务 {name}]')
    const result = translate('[任务 #{id} 结果]')
    assert.equal(`${dispatch} ${routine} Audit goal`.replace(TASK_DISPATCH, ''), `${routine} Audit goal`)
    assert.equal(`${routine} Audit goal`.replace(ROUTINE_LABEL, ''), 'Audit goal')
    assert.equal(`${result}\n[report] Audit OK`.replace(TASK_RESULT, ''), '[report] Audit OK')
    const id = result.match(TASK_RESULT)
    assert.equal(Number(id[1] || id[2] || id[3]), 42)
  })
}
test('partial heavy status is labeled in the task UI', () => {
  const tasks = fs.readFileSync(path.join(__dirname, '../src/components/Tasks.tsx'), 'utf8')
  assert.match(tasks, /partial: t\('部分完成'\)/)
  assert.match(chat, /t\('任务部分完成'\)/)
  assert.match(chat, /status === 'partial'/)
  for (const language of ['en', 'vi']) {
    const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/locales', `${language}.json`), 'utf8'))
    assert.equal(typeof catalog['部分完成'], 'string')
    assert.equal(typeof catalog['任务部分完成'], 'string')
    assert.ok(catalog['部分完成'])
    assert.ok(catalog['任务部分完成'])
  }
})
test('task header stripping preserves ordinary bracketed text', () => {
  for (const pattern of [TASK_DISPATCH, TASK_RESULT, ROUTINE_LABEL]) {
    assert.equal('[RFC 42] Audit notes'.replace(pattern, ''), '[RFC 42] Audit notes')
    assert.equal('Audit OK'.replace(pattern, ''), 'Audit OK')
  }
  assert.match(chat, /const goal = m\.content\.replace\(TASK_DISPATCH, ''\)/)
  assert.match(chat, /const text = m\.content\.replace\(TASK_RESULT, ''\)/)
  assert.match(chat, /\.replace\(ROUTINE_LABEL, ''\)\.slice\(0, 60\)/)
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { gradeForClass, parseSchoolClasses } from './schoolDirectory.js'

test('primary and high school custom class names resolve their configured grade', () => {
  const classes = parseSchoolClasses(' 高一1班 | 高一 \n一年级1班 | 小学一年级')
  assert.equal(gradeForClass(classes, '高一1班'), '高一')
  assert.equal(gradeForClass(classes, '一年级1班'), '小学一年级')
})
test('legacy graduation year class names still work', () => {
  assert.equal(gradeForClass([], '2030级25班'), '2030级')
  assert.equal(gradeForClass([], null), '')
})
test('configured grade takes precedence over old naming convention', () => {
  assert.equal(gradeForClass([{ name: '2030级1班', grade: '初一' }], '2030级1班'), '初一')
})
test('duplicate classes after trimming are rejected', () => {
  assert.throws(() => parseSchoolClasses('甲 | 一年级\n 甲 | 二年级'), /重复/)
})
test('malformed lines and overlong grade names are rejected', () => {
  for (const text of ['甲', '甲 |', '| 年级', '甲 | 一 | 二', `甲 | ${'年'.repeat(21)}`]) assert.throws(() => parseSchoolClasses(text))
})
test('blank lines are ignored and directory size is bounded', () => {
  assert.deepEqual(parseSchoolClasses(' \n'), [])
  assert.throws(() => parseSchoolClasses(Array.from({ length: 2001 }, (_, i) => `班${i} | 年级`).join('\n')), /2000/)
})

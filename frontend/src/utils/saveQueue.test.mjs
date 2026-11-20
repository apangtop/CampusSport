import test from 'node:test'
import assert from 'node:assert/strict'
import { createSaveQueue } from './saveQueue.js'
function deferred() { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }

test('same row saves run in order and reuse the first created record', async () => {
  const queue = createSaveQueue(); const wait = deferred(); const calls = []; let id
  const first = queue.enqueue('row', async () => { calls.push('create'); await wait.promise; id = 7 })
  const second = queue.enqueue('row', async () => { calls.push(`update:${id}`) })
  await Promise.resolve(); await Promise.resolve(); assert.deepEqual(calls, ['create'])
  wait.resolve(); await Promise.all([first, second]); assert.deepEqual(calls, ['create', 'update:7'])
})
test('batch flush waits until autosave finishes', async () => {
  const queue = createSaveQueue(); const wait = deferred(); let flushed = false
  queue.enqueue('row', () => wait.promise)
  const flush = queue.flush().then(() => { flushed = true })
  await Promise.resolve(); assert.equal(flushed, false)
  wait.resolve(); await flush; assert.equal(flushed, true)
})
test('failed autosave blocks batch flush', async () => {
  const queue = createSaveQueue(); const error = new Error('save failed')
  await assert.rejects(queue.enqueue('row', () => { throw error }))
  await assert.rejects(queue.flush(), error)
})
test('successful retry clears previous failure for the same row', async () => {
  const queue = createSaveQueue()
  await assert.rejects(queue.enqueue('row', () => { throw new Error('failed') }))
  await queue.enqueue('row', () => 'saved'); await queue.flush()
})
test('one row failure does not stop another row saving', async () => {
  const queue = createSaveQueue(); let saved = false
  const bad = queue.enqueue('bad', () => { throw new Error('failed') })
  const good = queue.enqueue('good', () => { saved = true })
  await Promise.allSettled([bad, good]); assert.equal(saved, true)
  await assert.rejects(queue.flush()); queue.clearFailures(); await queue.flush()
})

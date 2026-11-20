import test from 'node:test'
import assert from 'node:assert/strict'
import { matchState, trimUnplayedRounds } from './confrontation.js'
const rounds = (...winners) => winners.map((winner, index) => ({ number: index + 1, winner }))

test('BO3 accepts two straight wins and reports two played rounds', () => {
  const state = matchState(rounds(1, 1, ''), 1, 2, 3)
  assert.equal(state.valid, true); assert.equal(state.winner, 1); assert.equal(state.played, 2)
})
test('BO3 accepts the deciding third round', () => {
  const state = matchState(rounds(1, 2, 1), 1, 2, 3)
  assert.equal(state.complete, true); assert.deepEqual(state.wins, { 1: 2, 2: 1 })
})
test('incomplete match cannot be submitted', () => {
  const state = matchState(rounds(1, 2, ''), 1, 2, 3)
  assert.equal(state.valid, true); assert.equal(state.complete, false)
})
test('skipped rounds are invalid', () => assert.equal(matchState(rounds(1, '', 1), 1, 2, 3).valid, false))
test('rounds after a winner are invalid', () => assert.equal(matchState(rounds(1, 1, 2), 1, 2, 3).valid, false))
test('BO5 stops at three wins', () => {
  const state = matchState(rounds(1, 2, 1, 2, 1), 1, 2, 5)
  assert.equal(state.winner, 1); assert.equal(state.played, 5)
})
test('same team and foreign winners are rejected', () => {
  assert.equal(matchState(rounds(1), 1, 1, 3).valid, false)
  assert.equal(matchState(rounds(3), 1, 2, 3).valid, false)
})
test('changing an early result removes rounds after victory', () => {
  const data = rounds(1, 1, 2); trimUnplayedRounds(data, 1, 2, 3)
  assert.deepEqual(data.map(r => r.winner), [1, 1, ''])
})
test('clearing an early round removes later entries', () => {
  const data = rounds('', 1, 2); trimUnplayedRounds(data, 1, 2, 3)
  assert.deepEqual(data.map(r => r.winner), ['', '', ''])
})

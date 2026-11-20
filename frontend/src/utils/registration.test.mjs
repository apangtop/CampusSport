import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isActiveRegistration, individualCap, registrationOpen, registrationCounts, loadAllPages, registrationStatusLabel } from './registration.js'

test('rejected and cancelled registrations release both quotas', () => {
  assert.deepEqual(registrationCounts([
    {student:1,event:10,status:'approved'}, {student:2,event:10,status:'submitted'},
    {student:1,event:11,status:'rejected'}, {student:2,event:12,status:'cancelled'}
  ]), {students:{1:1,2:1},events:{10:2}})
})
test('only active records prevent selecting a registered student', () => {
  assert.equal(isActiveRegistration({status:'rejected'}),false)
  assert.equal(isActiveRegistration({status:'submitted'}),true)
})
test('event cap cannot exceed meet cap', () => {
  assert.equal(individualCap({max_events_per_person:2},{max_per_person:5}),2)
  assert.equal(individualCap({max_events_per_person:3},{max_per_person:1}),1)
})
test('zero meet quota is preserved', () => assert.equal(individualCap({max_events_per_person:0},{max_per_person:3}),0))
test('deadline closes exactly at the boundary', () => {
  const meet={status:'registration',registration_deadline:'2026-10-06T12:00:00+08:00'}
  const deadline=Date.parse(meet.registration_deadline)
  assert.equal(registrationOpen(meet,deadline-1),true)
  assert.equal(registrationOpen(meet,deadline),false)
})
test('nonregistration meets and invalid deadlines are closed', () => {
  assert.equal(registrationOpen({status:'ongoing'}),false)
  assert.equal(registrationOpen({status:'registration',registration_deadline:'bad'}),false)
})
test('pagination loads all records without following next URLs', async () => {
  const calls=[]
  const results=await loadAllPages(async params => {
    calls.push(params)
    return params.page===1 ? {results:[{id:1}],next:'https://untrusted.invalid'} : {results:[{id:2}],next:null}
  },{sports_meet:3})
  assert.deepEqual(results,[{id:1},{id:2}]); assert.deepEqual(calls.map(p=>p.page),[1,2])
  assert.equal(calls[1].sports_meet,3)
})
test('pagination failure does not return an incomplete quota count', async () => {
  await assert.rejects(loadAllPages(async p => { if(p.page===2) throw new Error('failed'); return {results:[{}],next:'next'} }))
})
test('array list responses remain supported', async () => assert.deepEqual(await loadAllPages(async()=>[{id:1}]),[{id:1}]))
test('inactive team statuses are displayed honestly', () => {
  assert.equal(registrationStatusLabel('rejected'),'已拒绝')
  assert.equal(registrationStatusLabel('cancelled'),'已取消')
})

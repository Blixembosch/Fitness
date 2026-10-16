import test from 'node:test'
import assert from 'node:assert/strict'
import { ingestPayload, readIngestPayload, toProfileUnit, normalizeWeighIn, applyWeighIn, KG_PER_LB } from '../ingest.js'

test('ingest token payload round-trips and is prefixed', () => {
  assert.equal(ingestPayload('abc', 0), 'ingest:abc:0')
  assert.deepEqual(readIngestPayload('ingest:abc:3'), { uid: 'abc', iv: 3 })
  // a session payload (uid:exp:ver) must not read as an ingest token
  assert.equal(readIngestPayload('abc:9999999999999:0'), null)
  assert.equal(readIngestPayload('ingest::0'), null)
  assert.equal(readIngestPayload('ingest:abc:x'), null)
})

test('toProfileUnit converts only when units differ', () => {
  assert.equal(toProfileUnit(100, 'kg', 'kg'), 100)
  assert.equal(toProfileUnit(100, undefined, 'kg'), 100)        // absent unit = already profile unit
  assert.equal(toProfileUnit(220, 'lb', 'kg'), Math.round((220 * KG_PER_LB) * 10) / 10) // 99.8
  assert.equal(toProfileUnit(100, 'kg', 'lb'), Math.round((100 / KG_PER_LB) * 10) / 10) // 220.5
})

test('normalizeWeighIn validates weight and date', () => {
  assert.deepEqual(normalizeWeighIn({ w: 101 }, 'kg', '2026-11-01'), { d: '2026-11-01', w: 101 })
  assert.deepEqual(normalizeWeighIn({ w: '100.4', d: '2026-11-02' }, 'kg', '2026-11-01'), { d: '2026-11-02', w: 100.4 })
  assert.ok(normalizeWeighIn({ w: 0 }, 'kg', '2026-11-01').error)
  assert.ok(normalizeWeighIn({ w: 5000 }, 'kg', '2026-11-01').error)
  assert.ok(normalizeWeighIn({ w: 80, d: 'nope' }, 'kg', '2026-11-01').error)
})

test('applyWeighIn adds one entry per day with a stamp', () => {
  const s = {}
  applyWeighIn(s, { d: '2026-11-01', w: 101, now: 1000 })
  assert.deepEqual(s.bodyweight, [{ d: '2026-11-01', w: 101, t: 1000 }])
})

test('applyWeighIn replaces a same-day entry only when newer', () => {
  const s = { bodyweight: [{ d: '2026-11-01', w: 101, t: 5000 }] }
  applyWeighIn(s, { d: '2026-11-01', w: 102, now: 4000 })   // older — ignored
  assert.equal(s.bodyweight[0].w, 101)
  applyWeighIn(s, { d: '2026-11-01', w: 103, now: 6000 })   // newer — replaces
  assert.equal(s.bodyweight.length, 1)
  assert.equal(s.bodyweight[0].w, 103)
})

test('applyWeighIn keeps other days untouched', () => {
  const s = { bodyweight: [{ d: '2026-10-31', w: 101.5, t: 1 }] }
  applyWeighIn(s, { d: '2026-11-01', w: 101, now: 2 })
  assert.equal(s.bodyweight.length, 2)
})

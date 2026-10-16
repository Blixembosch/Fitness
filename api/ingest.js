// Weigh-in ingest: let an external automation (an iOS Shortcut reading Apple Health) post a
// body-weight reading without a browser session. The token is HMAC-signed and stateless — the
// server signs `ingest:<uid>:<iv>` with its own SECRET (see server.js), so revoking is just
// bumping the user's `iv`. The weigh-in is written into the same per-user state the app syncs,
// as a `{ d, w, t }` entry, so the next device merge keeps it (lib/sync-merge mergeBodyweight,
// which keeps the later `t` per day).

export const KG_PER_LB = 0.45359237

// Token payload shape. Kept tiny and prefixed so a session cookie can never be read as an
// ingest token or the other way round (server checks the prefix after verifying the HMAC).
export const ingestPayload = (uid, iv = 0) => `ingest:${uid}:${iv}`

/** Parse a verified payload back to { uid, iv }, or null if it isn't an ingest payload. */
export function readIngestPayload(payload) {
  const parts = String(payload || '').split(':')
  if (parts.length !== 3 || parts[0] !== 'ingest' || !parts[1]) return null
  const iv = Number(parts[2])
  if (!Number.isInteger(iv) || iv < 0) return null
  return { uid: parts[1], iv }
}

// Round to one decimal, the precision a scale reports and the app stores.
const round1 = n => Math.round(n * 10) / 10

/** Convert a reading to the profile's unit. Unknown/absent `unit` is taken to already be the
 *  profile unit (the Shortcut can be set up to send the profile's unit directly). */
export function toProfileUnit(w, unit, profileUnit) {
  const from = unit === 'lb' || unit === 'lbs' ? 'lb' : unit === 'kg' ? 'kg' : null
  const to = profileUnit === 'lb' ? 'lb' : 'kg'
  if (!from || from === to) return round1(w)
  return round1(from === 'kg' ? w / KG_PER_LB : w * KG_PER_LB)
}

const isISODate = s => /^\d{4}-\d{2}-\d{2}$/.test(String(s || ''))

/**
 * Validate and normalise an ingest request. Returns { d, w } in the profile unit, or an
 * { error } the route turns into a 400. `today` is the server's date for a request that omits one.
 */
export function normalizeWeighIn({ w, d, unit }, profileUnit, today) {
  const weight = Number(w)
  if (!Number.isFinite(weight) || weight <= 0 || weight > 1000) return { error: 'weight out of range' }
  const day = d == null || d === '' ? today : String(d).slice(0, 10)
  if (!isISODate(day)) return { error: 'bad date' }
  return { d: day, w: toProfileUnit(weight, unit, profileUnit) }
}

/**
 * Write a weigh-in into a state document's `bodyweight`, in place, returning the document.
 * One entry per day: a same-day entry is replaced only when ours is newer (`t`), so a reading
 * posted twice is idempotent and never clobbers a weigh-in the user edited by hand afterwards.
 * Does not touch `_rev`/`_wid` — the caller owns that bookkeeping (it mirrors PUT /api/data).
 */
export function applyWeighIn(state, { d, w, now = Date.now() }) {
  const S = state && typeof state === 'object' ? state : {}
  const list = Array.isArray(S.bodyweight) ? S.bodyweight : []
  const entry = { d, w, t: now }
  const i = list.findIndex(e => e && e.d === d)
  if (i < 0) list.push(entry)
  else if ((Number(list[i].t) || 0) <= now) list[i] = entry
  S.bodyweight = list
  return S
}

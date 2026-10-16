// Import a daily nutrition log exported from Cronometer.
//
// Cronometer's "Export Data" gives several CSVs; the one with per-day nutrition is
// `dailysummary.csv`. Each date has a row per meal group (Breakfast, Lunch, Dinner,
// Snacks, Uncategorized) and one `Total` row that sums the day. We keep only the
// `Total` rows — that single row is the day's calories and macros.
//
// Verified against a real export (columns, in order, abbreviated):
//   Date,Group,Energy (kcal),…,Net Carbs (g),Carbs (g),Fiber (g),…,Sugars (g),…,
//   Fat (g),…,Saturated (g),…,Protein (g),…,Completed
//
// A `Total` row can be blank (a day logged with no food, or only water) — those are
// skipped rather than stored as a zero-calorie day.

import { parseCSV } from './import-csv.js'

// Header text (lower-cased, trimmed) -> the field we keep. Exact matches only, so
// "Fat (g)" is not shadowed by "Trans-Fats (g)" and "Carbs (g)" not by "Net Carbs (g)".
const FIELDS = {
  'energy (kcal)': 'kcal',
  'protein (g)': 'protein',
  'carbs (g)': 'carbs',
  'net carbs (g)': 'netCarbs',
  'fat (g)': 'fat',
  'fiber (g)': 'fiber',
  'sugars (g)': 'sugar',
  'saturated (g)': 'satFat',
  'sodium (mg)': 'sodium',
}

const norm = h => String(h || '').trim().toLowerCase()
// A finite number or null — Cronometer leaves a cell blank (not 0) when it has no value,
// and a blank must not read as zero grams.
const num = v => {
  if (v == null || String(v).trim() === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}
// Cronometer writes ISO dates (YYYY-MM-DD). Anything else is left for the caller to reject.
const isISODate = s => /^\d{4}-\d{2}-\d{2}$/.test(String(s || '').trim())

/** True if the file's header looks like a Cronometer daily-summary export. */
export function isCronometerDaily(text) {
  const rows = parseCSV(text)
  if (!rows.length) return false
  const head = rows[0].map(norm)
  return head[0] === 'date' && head.includes('group') && head.includes('energy (kcal)')
}

/**
 * Parse a Cronometer `dailysummary.csv` into one record per day.
 * Returns { days, skipped }:
 *   days    — [{ date, kcal, protein, carbs, netCarbs, fat, fiber, sugar, satFat, sodium }]
 *             sorted by date; only fields present in the file are set.
 *   skipped — Total rows dropped for a bad date or no energy value.
 * Throws if the file isn't a Cronometer daily summary (so the UI can say why).
 */
export function parseCronometer(text) {
  const rows = parseCSV(text)
  if (!rows.length) throw notCronometer()
  const head = rows[0].map(norm)
  if (head[0] !== 'date' || !head.includes('group')) throw notCronometer()

  const groupCol = head.indexOf('group')
  // field -> column index, for every nutrient column we recognise
  const cols = {}
  head.forEach((h, i) => { if (FIELDS[h]) cols[FIELDS[h]] = i })
  if (cols.kcal == null) throw notCronometer()

  const byDate = new Map()
  let skipped = 0
  for (let r = 1; r < rows.length; r++) {
    const row = rows[r]
    if (norm(row[groupCol]) !== 'total') continue      // only the day's Total row
    const date = String(row[0] || '').trim()
    const kcal = num(row[cols.kcal])
    // A Total with no date or no energy is an empty day — don't store a phantom 0-kcal day.
    if (!isISODate(date) || kcal == null) { skipped++; continue }
    const rec = { date }
    for (const field of Object.values(FIELDS)) {
      const idx = cols[field]
      if (idx == null) continue
      const v = num(row[idx])
      if (v != null) rec[field] = Math.round(v * 10) / 10   // one decimal is plenty for grams/kcal
    }
    byDate.set(date, rec)   // last Total for a date wins (a file never repeats one, but be safe)
  }
  const days = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))
  return { days, skipped }
}

function notCronometer() {
  return Object.assign(new Error('This isn’t a Cronometer daily-summary CSV.'), { code: 'not-cronometer' })
}

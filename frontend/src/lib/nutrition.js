// Nutrition domain logic: daily calorie/macro targets from body stats, and the per-day
// consumed/remaining math the Nutrition view renders. Pure helpers, framework-free, tested
// beside this file — the UI only formats what these return.
//
// Targets are a *starting point* the user can override. On a GLP-1 (e.g. Wegovy) the real
// risk during weight loss is losing muscle, so protein is the anchored number and the calorie
// target is never pushed below a floor.

export const ACTIVITY = {
  sedentary: 1.2,     // desk job, little exercise
  light: 1.4,         // 1–3 light sessions / week
  moderate: 1.55,     // 3–5 sessions / week
  high: 1.725,        // hard daily training
}

// Mifflin–St Jeor resting energy. sex: 'male' | 'female'. Age in years.
export function bmr({ weightKg, heightCm, age, sex = 'male' }) {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age
  return Math.round(base + (sex === 'female' ? -161 : 5))
}

/**
 * A starting target set from body stats.
 *  - tdee     : maintenance calories (BMR × activity)
 *  - kcal     : target intake = tdee − deficit, never below `floor`
 *  - protein  : proteinPerKg × bodyweight, the muscle-preservation anchor
 *  - fat      : fatPct of target calories (9 kcal/g)
 *  - carbs    : whatever calories remain (4 kcal/g), never negative
 * Defaults suit a muscle-preserving fat-loss phase; every input is overridable.
 */
export function estimateTargets({
  weightKg, heightCm, age, sex = 'male',
  activity = 'light', deficit = 500, floor = 1500,
  proteinPerKg = 1.5, fatPct = 0.30,
}) {
  const factor = ACTIVITY[activity] ?? ACTIVITY.light
  const tdee = Math.round(bmr({ weightKg, heightCm, age, sex }) * factor)
  const kcal = Math.max(floor, Math.round((tdee - deficit) / 10) * 10)
  const protein = Math.round(proteinPerKg * weightKg)
  const fat = Math.round((kcal * fatPct) / 9)
  const carbs = Math.max(0, Math.round((kcal - protein * 4 - fat * 9) / 4))
  return { tdee, kcal, protein, carbs, fat }
}

// Body-mass index, one decimal — shown for context, never as a target.
export const bmi = ({ weightKg, heightCm }) =>
  heightCm > 0 ? Math.round((weightKg / (heightCm / 100) ** 2) * 10) / 10 : null

const MACROS = ['kcal', 'protein', 'carbs', 'fat']

/**
 * Compare a day's entry against targets.
 * Returns per-macro { consumed, target, remaining, pct } where pct is 0..100+ (clamped only
 * for the bar width by the caller). A missing target leaves remaining/pct null — the bar then
 * shows consumed without a goal line.
 */
export function daySummary(entry = {}, targets = {}) {
  const out = {}
  for (const k of MACROS) {
    const consumed = Number(entry[k]) || 0
    const target = targets[k] != null ? Number(targets[k]) : null
    out[k] = {
      consumed: Math.round(consumed * 10) / 10,
      target,
      remaining: target != null ? Math.round((target - consumed) * 10) / 10 : null,
      pct: target > 0 ? Math.round((consumed / target) * 100) : null,
    }
  }
  return out
}

const ISO = /^\d{4}-\d{2}-\d{2}$/
const isMap = v => v && typeof v === 'object' && !Array.isArray(v)
const NUTRIENTS = ['kcal', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'satFat', 'sodium']

/** One day's entry from S.nutrition, or null. */
export const nutritionOf = (S, iso) => (isMap(S?.nutrition) && isMap(S.nutrition[iso]) ? S.nutrition[iso] : null)

/**
 * S.nutrition with `iso` set to `fields`, stamped `now` — the dayNotes pattern, so each day merges
 * on its own `_ts` (lib/sync-merge STAMPED_MAPS). Only known nutrient keys with a finite value are
 * kept; an entry with none becomes a cleared `{ _ts }` so a deletion syncs. Returns a new map.
 */
export function withNutrition(map, iso, fields, now = Date.now()) {
  const entry = { _ts: now }
  for (const k of NUTRIENTS) {
    const v = Number(fields?.[k])
    if (Number.isFinite(v)) entry[k] = Math.round(v * 10) / 10
  }
  return { ...(isMap(map) ? map : {}), [iso]: entry }
}

/** Merge many parsed days (e.g. a Cronometer import) into the map, each stamped `now`. A day the
 *  map already holds with a newer `_ts` (edited by hand since) is left alone. Returns a new map. */
export function mergeNutritionDays(map, days = [], now = Date.now()) {
  const out = { ...(isMap(map) ? map : {}) }
  let added = 0, updated = 0
  for (const d of days) {
    if (!d || !ISO.test(d.date)) continue
    const cur = isMap(out[d.date]) ? out[d.date] : null
    if (cur && (Number(cur._ts) || 0) > now) continue
    const next = withNutrition(out, d.date, d, now)[d.date]
    if (cur) updated++; else added++
    out[d.date] = next
  }
  return { map: out, added, updated }
}

/** Logged days as a sorted array [{ date, kcal, protein, ... }], newest last; cleared entries out. */
export function nutritionDays(S) {
  const m = isMap(S?.nutrition) ? S.nutrition : {}
  return Object.entries(m)
    .filter(([date, e]) => ISO.test(date) && isMap(e) && (e.kcal != null || e.protein != null))
    .map(([date, e]) => ({ date, ...e }))
    .sort((a, b) => a.date.localeCompare(b.date))
}

// Protein hit-rate over a set of day entries — the headline muscle-preservation metric.
// Returns { days, metDays, avgProtein, avgKcal } ignoring days with no entry.
export function proteinAdherence(days = [], proteinTarget) {
  const logged = days.filter(d => d && (d.kcal != null || d.protein != null))
  if (!logged.length) return { days: 0, metDays: 0, avgProtein: 0, avgKcal: 0 }
  const sum = (k) => logged.reduce((s, d) => s + (Number(d[k]) || 0), 0)
  const metDays = proteinTarget > 0 ? logged.filter(d => (Number(d.protein) || 0) >= proteinTarget).length : 0
  return {
    days: logged.length,
    metDays,
    avgProtein: Math.round(sum('protein') / logged.length),
    avgKcal: Math.round(sum('kcal') / logged.length),
  }
}

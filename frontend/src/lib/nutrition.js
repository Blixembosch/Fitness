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

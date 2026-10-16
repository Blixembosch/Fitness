import { describe, it, expect } from 'vitest'
import { bmr, estimateTargets, bmi, daySummary, proteinAdherence, withNutrition, mergeNutritionDays, nutritionDays, nutritionOf } from './nutrition.js'
import { mergeStates } from './sync-merge.js'

describe('bmr (Mifflin–St Jeor)', () => {
  it('computes male resting energy', () => {
    // 10*101 + 6.25*178 - 5*40 + 5 = 1927.5 -> 1928
    expect(bmr({ weightKg: 101, heightCm: 178, age: 40, sex: 'male' })).toBe(1928)
  })
  it('applies the female constant', () => {
    expect(bmr({ weightKg: 70, heightCm: 165, age: 35, sex: 'female' }))
      .toBe(Math.round(10 * 70 + 6.25 * 165 - 5 * 35 - 161))
  })
})

describe('estimateTargets', () => {
  const t = estimateTargets({ weightKg: 101, heightCm: 178, age: 40, activity: 'light' })
  it('builds a muscle-preserving deficit target', () => {
    expect(t.tdee).toBe(Math.round(1928 * 1.4))          // 2699
    expect(t.kcal).toBe(2200)                            // 2699 - 500 -> round to 2200
    expect(t.protein).toBe(152)                          // 1.5 * 101
  })
  it('keeps carbs non-negative and macros adding up roughly to kcal', () => {
    const kcalFromMacros = t.protein * 4 + t.carbs * 4 + t.fat * 9
    expect(Math.abs(kcalFromMacros - t.kcal)).toBeLessThanOrEqual(10)
    expect(t.carbs).toBeGreaterThanOrEqual(0)
  })
  it('never drops below the calorie floor', () => {
    const low = estimateTargets({ weightKg: 55, heightCm: 160, age: 30, activity: 'sedentary', deficit: 1200, floor: 1500 })
    expect(low.kcal).toBe(1500)
  })
})

describe('bmi', () => {
  it('rounds to one decimal', () => {
    expect(bmi({ weightKg: 101, heightCm: 178 })).toBe(31.9)
  })
})

describe('daySummary', () => {
  const targets = { kcal: 2000, protein: 150, carbs: 180, fat: 60 }
  it('reports consumed, remaining and pct per macro', () => {
    const s = daySummary({ kcal: 1500, protein: 120, carbs: 150, fat: 40 }, targets)
    expect(s.kcal).toMatchObject({ consumed: 1500, target: 2000, remaining: 500, pct: 75 })
    expect(s.protein).toMatchObject({ consumed: 120, remaining: 30, pct: 80 })
  })
  it('leaves remaining/pct null when a target is missing', () => {
    const s = daySummary({ kcal: 1500 }, {})
    expect(s.kcal.consumed).toBe(1500)
    expect(s.kcal.remaining).toBeNull()
    expect(s.kcal.pct).toBeNull()
  })
  it('treats a missing entry as zero consumed', () => {
    const s = daySummary({}, targets)
    expect(s.protein.consumed).toBe(0)
    expect(s.protein.remaining).toBe(150)
  })
})

describe('proteinAdherence', () => {
  it('counts only logged days and days that met the protein target', () => {
    const days = [
      { date: 'a', kcal: 1800, protein: 160 },
      { date: 'b', kcal: 1500, protein: 120 },
      { date: 'c' },                              // no entry — ignored
    ]
    const r = proteinAdherence(days, 150)
    expect(r.days).toBe(2)
    expect(r.metDays).toBe(1)
    expect(r.avgProtein).toBe(140)
    expect(r.avgKcal).toBe(1650)
  })
  it('is safe with no logged days', () => {
    expect(proteinAdherence([], 150)).toMatchObject({ days: 0, metDays: 0, avgProtein: 0, avgKcal: 0 })
  })
})

describe('withNutrition', () => {
  it('keeps known nutrients and stamps the entry', () => {
    const m = withNutrition({}, '2026-11-01', { kcal: 1800, protein: 150, junk: 9 }, 1000)
    expect(m['2026-11-01']).toMatchObject({ kcal: 1800, protein: 150, _ts: 1000 })
    expect(m['2026-11-01'].junk).toBeUndefined()
  })
  it('writes a cleared entry when there is nothing to keep (so a deletion syncs)', () => {
    const m = withNutrition({ '2026-11-01': { kcal: 1, _ts: 1 } }, '2026-11-01', {}, 2000)
    expect(m['2026-11-01']).toEqual({ _ts: 2000 })
  })
})

describe('mergeNutritionDays', () => {
  it('adds valid days and skips bad dates', () => {
    const r = mergeNutritionDays({}, [{ date: '2026-11-01', kcal: 1800, protein: 150 }, { date: 'bad', kcal: 1 }], 1)
    expect(r.added).toBe(1)
    expect(Object.keys(r.map)).toEqual(['2026-11-01'])
  })
  it('does not clobber a day edited by hand after the import time', () => {
    const r = mergeNutritionDays({ '2026-11-02': { kcal: 1600, protein: 120, _ts: 500 } }, [{ date: '2026-11-02', kcal: 9999 }], 300)
    expect(r.map['2026-11-02'].kcal).toBe(1600)
  })
})

describe('nutritionDays', () => {
  it('returns logged days sorted, excluding cleared entries', () => {
    const days = nutritionDays({ nutrition: {
      '2026-11-03': { kcal: 1500, protein: 130, _ts: 1 },
      '2026-11-01': { kcal: 1800, protein: 150, _ts: 1 },
      '2026-11-02': { _ts: 1 },
    } })
    expect(days.map(d => d.date)).toEqual(['2026-11-01', '2026-11-03'])
  })
  it('nutritionOf reads one day', () => {
    expect(nutritionOf({ nutrition: { '2026-11-01': { kcal: 1800, _ts: 1 } } }, '2026-11-01').kcal).toBe(1800)
  })
})

// Nutrition rides the same per-day stamped-map merge as dayNotes (lib/sync-merge STAMPED_MAPS).
describe('nutrition sync merge', () => {
  it('unions days across devices and keeps the newer per-day edit', () => {
    const A = { nutrition: { '2026-11-01': { kcal: 1800, protein: 150, _ts: 100 }, '2026-11-02': { kcal: 1700, protein: 140, _ts: 100 } } }
    const B = { nutrition: { '2026-11-02': { kcal: 1600, protein: 120, _ts: 200 }, '2026-11-03': { kcal: 1500, protein: 130, _ts: 100 } } }
    const m = mergeStates(A, B)
    expect(Object.keys(m.nutrition).sort()).toEqual(['2026-11-01', '2026-11-02', '2026-11-03'])
    expect(m.nutrition['2026-11-02'].kcal).toBe(1600)   // B's newer _ts wins
    expect(m.nutrition['2026-11-01'].protein).toBe(150)
    expect(m.nutrition['2026-11-03'].protein).toBe(130)
  })
})

import { describe, it, expect } from 'vitest'
import { parseCronometer, isCronometerDaily } from './import-cronometer.js'

// A trimmed Cronometer dailysummary.csv: the real column order, a few nutrients, meal rows
// that must be ignored, a normal Total, a blank Total (empty day), and a no-date Total.
const HEAD = 'Date,Group,Energy (kcal),Caffeine (mg),Net Carbs (g),Carbs (g),Fiber (g),Sugars (g),Fat (g),Saturated (g),Protein (g),Sodium (mg),Completed'
const CSV = [
  HEAD,
  '2026-11-01,"Breakfast",400.00,0,30,35,5,10,15,4,25,300,true',
  '2026-11-01,"Dinner",600.00,0,40,45,6,12,20,6,55,700,true',
  '2026-11-01,"Total",1000.00,0,70,80,11,22,35,10,80,1000,true',
  '2026-11-02,"Total",,,,,,,,,,,false',          // blank day — skip
  ',"Total",1500,0,100,110,12,30,50,15,90,1200,true', // no date — skip
  '2026-11-03,"Snacks",250.00,0,20,22,3,8,10,3,12,150,true',
  '2026-11-03,"Total",1800.50,0,120,130,14,35,60,18,110,2100,true',
].join('\n')

describe('parseCronometer', () => {
  it('keeps one record per day from the Total rows only', () => {
    const { days } = parseCronometer(CSV)
    expect(days.map(d => d.date)).toEqual(['2026-11-01', '2026-11-03'])
  })

  it('reads calories and the macros that matter', () => {
    const { days } = parseCronometer(CSV)
    const d1 = days.find(d => d.date === '2026-11-01')
    expect(d1).toMatchObject({ kcal: 1000, protein: 80, carbs: 80, netCarbs: 70, fat: 35, fiber: 11, sugar: 22, satFat: 10, sodium: 1000 })
  })

  it('does not read a meal row as a day', () => {
    const { days } = parseCronometer(CSV)
    // 2026-11-03 Total is 1800.5 kcal / 110 g protein — not the 250 kcal Snacks row
    const d3 = days.find(d => d.date === '2026-11-03')
    expect(d3.kcal).toBe(1800.5)
    expect(d3.protein).toBe(110)
  })

  it('skips blank Totals and rows with no date, and counts them', () => {
    const { days, skipped } = parseCronometer(CSV)
    expect(days).toHaveLength(2)
    expect(skipped).toBe(2)
  })

  it('leaves a missing nutrient absent rather than zero', () => {
    const csv = [HEAD.replace(',Protein (g)', ',Protein (g)'), '2026-11-05,"Total",900,,,,,,,,,,true'].join('\n')
    const { days } = parseCronometer(csv)
    expect(days[0].kcal).toBe(900)
    expect(days[0].protein).toBeUndefined()
  })

  it('detects a Cronometer daily summary by its header', () => {
    expect(isCronometerDaily(CSV)).toBe(true)
    expect(isCronometerDaily('Day,Time,Group,Food Name,Amount,Category\n')).toBe(false)
  })

  it('rejects a file that is not a daily summary', () => {
    expect(() => parseCronometer('Day,Time,Group,Exercise,Minutes,Calories Burned\n'))
      .toThrowError(/Cronometer/)
  })
})

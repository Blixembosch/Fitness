import { useMemo, useRef, useState } from 'react'
import { useStore } from '../store/useStore.js'
import { useUI } from '../store/useUI.js'
import { t } from '../lib/i18n.js'
import { todayISO, fmtNum } from '../lib/format.js'
import {
  daySummary, nutritionOf, withNutrition, mergeNutritionDays, nutritionDays, proteinAdherence,
} from '../lib/nutrition.js'
import { parseCronometer } from '../lib/import-cronometer.js'
import LineChart from '../components/LineChart.jsx'
import Icon from '../components/Icon.jsx'
import { Button, NumberField, Section } from '../components/ui.jsx'

const update = fn => useStore.getState().update(fn)
const toast = m => useUI.getState().toast(m)

// Macro order with protein first — the muscle-preservation anchor during a deficit.
const MACROS = [
  { key: 'protein', label: () => t('Protein'), unit: 'g', color: 'var(--acc)', primary: true },
  { key: 'kcal', label: () => t('Calories'), unit: 'kcal', color: 'var(--teal)' },
  { key: 'carbs', label: () => t('Carbs'), unit: 'g', color: 'var(--blue)' },
  { key: 'fat', label: () => t('Fat'), unit: 'g', color: 'var(--purple)' },
]

function Bar({ macro, cell }) {
  const pct = cell.pct == null ? 0 : Math.min(100, cell.pct)
  const over = cell.pct != null && cell.pct > 100
  return (
    <div className={'nut-bar' + (macro.primary ? ' primary' : '')}>
      <div className="nut-bar-head">
        <span className="nut-bar-label">{macro.label()}</span>
        <span className="nut-bar-val">
          {fmtNum(cell.consumed)}{cell.target != null ? ' / ' + fmtNum(cell.target) : ''} {macro.unit}
        </span>
      </div>
      <div className="nut-track">
        <div className="nut-fill" style={{ width: pct + '%', background: over ? 'var(--red)' : macro.color }} />
      </div>
      {cell.remaining != null && (
        <div className="nut-bar-sub">
          {cell.remaining >= 0
            ? t('{0} {1} left', fmtNum(cell.remaining), macro.unit)
            : t('{0} {1} over', fmtNum(-cell.remaining), macro.unit)}
        </div>
      )}
    </div>
  )
}

function QuickEntry({ iso, entry }) {
  const [vals, setVals] = useState(() => ({
    kcal: entry?.kcal ?? null, protein: entry?.protein ?? null,
    carbs: entry?.carbs ?? null, fat: entry?.fat ?? null,
  }))
  const set = (k, v) => setVals(s => ({ ...s, [k]: v }))
  const save = () => {
    if (![vals.kcal, vals.protein, vals.carbs, vals.fat].some(v => Number(v) > 0)) {
      toast(t('Enter at least calories or protein')); return
    }
    update(s => { s.nutrition = withNutrition(s.nutrition, iso, vals) })
    toast(t('Saved'))
  }
  return (
    <div className="nut-entry">
      <div className="nut-entry-grid">
        <label><span>{t('Calories')}</span><NumberField value={vals.kcal} onChange={v => set('kcal', v)} nullable decimal={false} /></label>
        <label><span>{t('Protein')} (g)</span><NumberField value={vals.protein} onChange={v => set('protein', v)} nullable /></label>
        <label><span>{t('Carbs')} (g)</span><NumberField value={vals.carbs} onChange={v => set('carbs', v)} nullable /></label>
        <label><span>{t('Fat')} (g)</span><NumberField value={vals.fat} onChange={v => set('fat', v)} nullable /></label>
      </div>
      <Button variant="primary" onClick={save}>{t('Save')}</Button>
    </div>
  )
}

export default function Nutrition() {
  const S = useStore(s => s.S)
  const fileRef = useRef(null)
  const iso = todayISO()
  const entry = nutritionOf(S, iso)
  const summary = useMemo(() => daySummary(entry || {}, S.nutritionTargets || {}), [entry, S.nutritionTargets])

  const days = useMemo(() => nutritionDays(S), [S.nutrition])
  const adh = useMemo(() => proteinAdherence(days.slice(-7), S.nutritionTargets?.protein), [days, S.nutritionTargets])

  // Weight line (last ~120 days) with the goal line, same source the Stats chart uses.
  const wPoints = useMemo(() => (S.bodyweight || [])
    .filter(b => b && b.d && Number(b.w) > 0)
    .map(b => ({ t: new Date(b.d + 'T12:00:00').getTime(), y: Number(b.w), d: b.d }))
    .sort((a, b) => a.t - b.t), [S.bodyweight])
  const latestW = wPoints.length ? wPoints[wPoints.length - 1].y : null

  const onFile = ev => {
    const f = ev.target.files?.[0]; ev.target.value = ''
    if (!f) return
    const rd = new FileReader()
    rd.onload = () => {
      try {
        const { days: parsed } = parseCronometer(String(rd.result))
        if (!parsed.length) { toast(t('No days found in that file')); return }
        let res
        update(s => { res = mergeNutritionDays(s.nutrition, parsed); s.nutrition = res.map })
        toast(t('Imported {0} days', res.added + res.updated))
      } catch {
        toast(t('That isn’t a Cronometer daily-summary CSV'))
      }
    }
    rd.readAsText(f)
  }

  return (
    <div className="narrow nutrition">
      <div className="hdr">
        <div><h1>{t('Nutrition')}</h1><div className="sub">{t('Calories, protein and your weight')}</div></div>
        <div className="hdr-actions">
          <button className="iconbtn" onClick={() => fileRef.current?.click()} aria-label={t('Import Cronometer CSV')} title={t('Import Cronometer CSV')}>
            <Icon name="download" />
          </button>
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={onFile} hidden />
        </div>
      </div>

      <Section title={t('Today')}>
        <div className="nut-bars">
          {MACROS.map(m => <Bar key={m.key} macro={m} cell={summary[m.key]} />)}
        </div>
      </Section>

      <Section title={t('Log today')}>
        <QuickEntry iso={iso} entry={entry} />
      </Section>

      <Section title={t('Weight')}>
        {latestW != null
          ? <>
              <div className="nut-weight-now">{fmtNum(latestW)} {S.unit}</div>
              <div className="chart"><LineChart points={wPoints} h={170} unit={S.unit} color="var(--teal)" goal={Number(S.targetW) || null} /></div>
            </>
          : <div className="muted small">{t('No weigh-ins yet. They arrive from Apple Health or the weight card.')}</div>}
      </Section>

      {adh.days > 0 && (
        <Section title={t('Last 7 days')}>
          <div className="nut-adh">
            <div><b>{adh.avgProtein}</b> <span className="muted small">g {t('Protein')} · {t('avg')}</span></div>
            <div><b>{adh.avgKcal}</b> <span className="muted small">{t('Calories')} · {t('avg')}</span></div>
            {S.nutritionTargets?.protein > 0 && (
              <div><b>{adh.metDays}/{adh.days}</b> <span className="muted small">{t('days hit protein')}</span></div>
            )}
          </div>
        </Section>
      )}
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api.js'
import { fmtLong } from '../lib.js'
import { icons } from '../components/icons.jsx'
import { SkeletonRows } from '../components/Skeletons.jsx'

const CRAMPS = ['none', 'mild', 'moderate', 'severe']
const SYMPTOMS = ['Cramps', 'Headache', 'Bloating', 'Breast tenderness', 'Acne', 'Fatigue',
  'Nausea', 'Back pain', 'Cravings', 'Insomnia', 'Dizziness', 'Other']
const MOODS = ['😊 Happy', '🙂 Calm', '😐 Neutral', '😔 Sad', '😤 Irritable', '😰 Anxious',
  '🤩 Energised', '😴 Tired', '😭 Emotional']
const DISCHARGE = ['Dry', 'Sticky', 'Creamy', 'Watery', 'Egg-white']

function EditEntryForm({ entry, onCancel, onSaved }) {
  const [form, setForm] = useState(() => {
    if (entry.type === 'period') {
      return { start_date: entry.start_date, end_date: entry.end_date || '', flow_level: entry.flow_level ?? '', notes: entry.notes || '' }
    }
    if (entry.type === 'symptom') {
      return { log_date: entry.log_date, symptom: entry.symptom, severity: entry.severity, notes: entry.notes || '' }
    }
    if (entry.type === 'mood') {
      return { log_date: entry.log_date, mood: entry.mood, energy: entry.energy }
    }
    return {
      log_date: entry.log_date,
      weight_kg: entry.weight_kg ?? '',
      temperature_c: entry.temperature_c ?? '',
      discharge: entry.discharge || '',
      intercourse: !!entry.intercourse,
      medication: entry.medication || '',
      cramps: entry.cramps ?? '',
      notes: entry.notes || '',
    }
  })
  const [saving, setSaving] = useState(false)

  function set(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    try {
      if (entry.type === 'period') {
        await api.updatePeriod(entry.id, {
          start_date: form.start_date,
          end_date: form.end_date || null,
          flow_level: form.flow_level === '' ? null : Number(form.flow_level),
          notes: form.notes.trim(),
        })
      } else if (entry.type === 'symptom') {
        await api.updateSymptom(entry.id, {
          log_date: form.log_date, symptom: form.symptom,
          severity: Number(form.severity), notes: form.notes.trim(),
        })
      } else if (entry.type === 'mood') {
        await api.updateMood(entry.id, {
          log_date: form.log_date, mood: form.mood, energy: Number(form.energy),
        })
      } else {
        await api.updateDaily(entry.id, {
          log_date: form.log_date,
          weight_kg: form.weight_kg === '' ? null : Number(form.weight_kg),
          temperature_c: form.temperature_c === '' ? null : Number(form.temperature_c),
          discharge: form.discharge || null,
          intercourse: form.intercourse,
          medication: form.medication.trim(),
          cramps: form.cramps === '' ? null : Number(form.cramps),
          notes: form.notes.trim(),
        })
      }
      toast.success('Entry updated ✓')
      await onSaved()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="edit-entry card" onSubmit={save}>
      <div className="card-head">
        <h3>Edit {entry.type === 'daily' ? 'daily log' : entry.type}</h3>
        <button type="button" className="btn ghost sm" onClick={onCancel}>Cancel</button>
      </div>

      {entry.type === 'period' && (
        <div className="form-row">
          <label className="field"><span>Start</span><input type="date" required value={form.start_date} onChange={(e) => set('start_date', e.target.value)} /></label>
          <label className="field"><span>End</span><input type="date" value={form.end_date} onChange={(e) => set('end_date', e.target.value)} /></label>
          <label className="field"><span>Flow</span><select value={form.flow_level} onChange={(e) => set('flow_level', e.target.value)}>
            <option value="">—</option><option value="0">Spotting</option><option value="1">Light</option><option value="2">Medium</option><option value="3">Heavy</option>
          </select></label>
          <label className="field"><span>Notes</span><input value={form.notes} onChange={(e) => set('notes', e.target.value)} /></label>
        </div>
      )}

      {entry.type === 'symptom' && (
        <div className="form-row">
          <label className="field"><span>Date</span><input type="date" required value={form.log_date} onChange={(e) => set('log_date', e.target.value)} /></label>
          <label className="field"><span>Symptom</span><select value={form.symptom} onChange={(e) => set('symptom', e.target.value)}>{SYMPTOMS.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field"><span>Severity · {form.severity}/5</span><input type="range" min="1" max="5" value={form.severity} onChange={(e) => set('severity', Number(e.target.value))} /></label>
          <label className="field"><span>Notes</span><input value={form.notes} onChange={(e) => set('notes', e.target.value)} /></label>
        </div>
      )}

      {entry.type === 'mood' && (
        <div className="form-row">
          <label className="field"><span>Date</span><input type="date" required value={form.log_date} onChange={(e) => set('log_date', e.target.value)} /></label>
          <label className="field"><span>Mood</span><select value={form.mood} onChange={(e) => set('mood', e.target.value)}>{MOODS.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field"><span>Energy · {form.energy}/5</span><input type="range" min="1" max="5" value={form.energy} onChange={(e) => set('energy', Number(e.target.value))} /></label>
        </div>
      )}

      {entry.type === 'daily' && (
        <div className="form-row">
          <label className="field"><span>Date</span><input type="date" required value={form.log_date} onChange={(e) => set('log_date', e.target.value)} /></label>
          <label className="field"><span>Weight (kg)</span><input type="number" step="0.1" min="25" max="300" value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} /></label>
          <label className="field"><span>Temp (°C)</span><input type="number" step="0.01" value={form.temperature_c} onChange={(e) => set('temperature_c', e.target.value)} /></label>
          <label className="field"><span>Discharge</span><select value={form.discharge} onChange={(e) => set('discharge', e.target.value)}><option value="">—</option>{DISCHARGE.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label className="field"><span>Cramps</span><select value={form.cramps} onChange={(e) => set('cramps', e.target.value)}><option value="">—</option><option value="0">None</option><option value="1">Mild</option><option value="2">Moderate</option><option value="3">Severe</option></select></label>
          <label className="field check"><input type="checkbox" checked={form.intercourse} onChange={(e) => set('intercourse', e.target.checked)} /><span>Intercourse</span></label>
          <label className="field span2"><span>Medication</span><input value={form.medication} onChange={(e) => set('medication', e.target.value)} /></label>
          <label className="field span2"><span>Notes</span><input value={form.notes} onChange={(e) => set('notes', e.target.value)} /></label>
        </div>
      )}

      <button className="btn dark" style={{ marginTop: 14 }} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
    </form>
  )
}

export default function HistoryPage({ onChanged }) {
  const [groups, setGroups] = useState(null)
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState(null)

  useEffect(() => {
    api.history().then(setGroups).catch((e) => toast.error(e.message))
  }, [onChanged])

  const filtered = useMemo(() => {
    if (!groups) return []
    const needle = q.trim().toLowerCase()
    return Object.entries(groups).filter(([date, entries]) => {
      if (!needle) return true
      if (date.includes(needle)) return true
      return entries.some((en) => JSON.stringify(en).toLowerCase().includes(needle))
    })
  }, [groups, q])

  async function del(entry) {
    const calls = {
      period: api.deletePeriod,
      symptom: api.deleteSymptom,
      mood: api.deleteMood,
      daily: api.deleteDaily,
    }
    try {
      if (calls[entry.type]) await calls[entry.type](entry.id)
      setEditing(null)
      toast.success('Entry deleted')
      const fresh = await api.history()
      setGroups(fresh); onChanged()
    } catch (e) { toast.error(e.message) }
  }

  async function reloadAfterEdit() {
    const fresh = await api.history()
    setGroups(fresh)
    setEditing(null)
    onChanged()
  }

  function describe(en) {
    switch (en.type) {
      case 'period':
        return `🩸 Period ${en.start_date} → ${en.end_date || 'ongoing'}`
      case 'symptom':
        return `🤒 ${en.symptom} (severity ${en.severity}/5)${en.notes ? ' — ' + en.notes : ''}`
      case 'mood':
        return `💭 ${en.mood}, energy ${en.energy}/5`
      case 'daily': {
        const bits = []
        if (en.weight_kg) bits.push(`${en.weight_kg} kg`)
        if (en.temperature_c) bits.push(`${en.temperature_c}°C`)
        if (en.discharge) bits.push(en.discharge)
        if (en.intercourse) bits.push('intercourse')
        if (en.cramps != null && en.cramps !== '') bits.push(`cramps ${CRAMPS[en.cramps]}`)
        if (en.medication) bits.push('💊 ' + en.medication)
        if (en.notes) bits.push(en.notes)
        return '📋 ' + (bits.join(' · ') || 'daily log')
      }
      default:
        return ''
    }
  }

  return (
    <article className="card">
      <div className="card-head">
        <h3>History</h3>
        <input type="search" className="search-input" placeholder="Filter by date or content…"
          value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {groups === null ? (
        <SkeletonRows n={6} labelW={200} />
      ) : filtered.length === 0 ? (
        <p className="muted">Nothing logged yet.</p>
      ) : (
        <>
          {editing && <EditEntryForm entry={editing} onCancel={() => setEditing(null)} onSaved={reloadAfterEdit} />}
          {filtered.slice(0, 60).map(([date, entries]) => (
            <div className="hist-group" key={date}>
              <h4>{fmtLong(date)}</h4>
              <ul className="entry-list">
                {entries.map((en, i) => (
                  <li className="entry" key={en.id || i}>
                    <span>{describe(en)}</span>
                    <span style={{ display: 'flex', gap: 2 }}>
                      <button className="btn ghost sm" aria-label="Edit entry" onClick={() => setEditing(en)}>{icons.edit} Edit</button>
                      <button className="icon-btn danger" aria-label="Delete entry" onClick={() => del(en)}>{icons.close}</button>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </>
      )}
    </article>
  )
}

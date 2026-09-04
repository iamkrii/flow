import { useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api.js'
import { todayISO } from '../lib.js'

const SYMPTOMS = ['Cramps', 'Headache', 'Bloating', 'Breast tenderness', 'Acne', 'Fatigue',
  'Nausea', 'Back pain', 'Cravings', 'Insomnia', 'Dizziness', 'Other']
const MOODS = ['😊 Happy', '🙂 Calm', '😐 Neutral', '😔 Sad', '😤 Irritable', '😰 Anxious',
  '🤩 Energised', '😴 Tired', '😭 Emotional']
const DISCHARGE = ['Dry', 'Sticky', 'Creamy', 'Watery', 'Egg-white']

export default function LogPage({ onChanged }) {
  const today = todayISO()
  // symptom form
  const [sf, setSf] = useState({ date: today, symptom: 'Cramps', severity: 2, notes: '' })
  // mood form
  const [mf, setMf] = useState({ date: today, mood: MOODS[0], energy: 3 })
  // daily form
  const [df, setDf] = useState({ date: today, weight_kg: '', temperature_c: '', discharge: '',
    intercourse: false, medication: '', cramps: '', notes: '' })

  async function saveSymptom(e) {
    e.preventDefault()
    try {
      await api.addSymptom({ log_date: sf.date, symptom: sf.symptom, severity: sf.severity, notes: sf.notes.trim() })
      toast.success('Symptom logged ✓')
      setSf((s) => ({ ...s, notes: '' })); onChanged()
    } catch (err) { toast.error(err.message) }
  }
  async function saveMood(e) {
    e.preventDefault()
    try {
      await api.addMood({ log_date: mf.date, mood: mf.mood, energy: mf.energy }); toast.success('Mood logged ✓'); onChanged()
    } catch (err) { toast.error(err.message) }
  }
  async function saveDaily(e) {
    e.preventDefault()
    try {
      await api.addDaily({
        log_date: df.date,
        weight_kg: df.weight_kg === '' ? null : Number(df.weight_kg),
        temperature_c: df.temperature_c === '' ? null : Number(df.temperature_c),
        discharge: df.discharge || null,
        intercourse: df.intercourse,
        medication: df.medication.trim(),
        cramps: df.cramps === '' ? null : Number(df.cramps),
        notes: df.notes.trim(),
      })
      toast.success('Daily log saved ✓')
      setDf((d) => ({ ...d, weight_kg: '', temperature_c: '', discharge: '', intercourse: false, medication: '', cramps: '', notes: '' }))
      onChanged()
    } catch (err) { toast.error(err.message) }
  }

  return (
    <>
      <div className="two-grid">
        <article className="card">
          <h3>Symptoms</h3>
          <form onSubmit={saveSymptom} className="stack">
            <label className="field"><span>Date</span>
              <input type="date" value={sf.date} onChange={(e) => setSf({ ...sf, date: e.target.value })} />
            </label>
            <label className="field"><span>Symptom</span>
              <select value={sf.symptom} onChange={(e) => setSf({ ...sf, symptom: e.target.value })}>
                {SYMPTOMS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label className="field"><span>Severity · {sf.severity}/5</span>
              <input type="range" min="1" max="5" value={sf.severity}
                onChange={(e) => setSf({ ...sf, severity: Number(e.target.value) })} />
            </label>
            <label className="field"><span>Notes</span>
              <input type="text" value={sf.notes} placeholder="Optional"
                onChange={(e) => setSf({ ...sf, notes: e.target.value })} />
            </label>
            <button className="btn dark full">Save symptom</button>
          </form>
        </article>

        <article className="card">
          <h3>Mood &amp; energy</h3>
          <form onSubmit={saveMood} className="stack">
            <label className="field"><span>Date</span>
              <input type="date" value={mf.date} onChange={(e) => setMf({ ...mf, date: e.target.value })} />
            </label>
            <label className="field"><span>Mood</span>
              <select value={mf.mood} onChange={(e) => setMf({ ...mf, mood: e.target.value })}>
                {MOODS.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label className="field"><span>Energy · {mf.energy}/5</span>
              <input type="range" min="1" max="5" value={mf.energy}
                onChange={(e) => setMf({ ...mf, energy: Number(e.target.value) })} />
            </label>
            <button className="btn dark full">Save mood</button>
          </form>
        </article>
      </div>

      <article className="card">
        <h3>Daily log</h3>
        <form onSubmit={saveDaily} className="form-row">
          <label className="field"><span>Date</span>
            <input type="date" value={df.date} onChange={(e) => setDf({ ...df, date: e.target.value })} />
          </label>
          <label className="field"><span>Weight (kg)</span>
            <input type="number" step="0.1" min="25" max="300" value={df.weight_kg}
              onChange={(e) => setDf({ ...df, weight_kg: e.target.value })} />
          </label>
          <label className="field"><span>Temp (°C)</span>
            <input type="number" step="0.01" value={df.temperature_c}
              onChange={(e) => setDf({ ...df, temperature_c: e.target.value })} />
          </label>
          <label className="field"><span>Discharge</span>
            <select value={df.discharge} onChange={(e) => setDf({ ...df, discharge: e.target.value })}>
              <option value="">—</option>{DISCHARGE.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <label className="field"><span>Cramps</span>
            <select value={df.cramps} onChange={(e) => setDf({ ...df, cramps: e.target.value })}>
              <option value="">—</option><option value="0">None</option>
              <option value="1">Mild</option><option value="2">Moderate</option><option value="3">Severe</option>
            </select>
          </label>
          <label className="field check">
            <input type="checkbox" checked={df.intercourse} onChange={(e) => setDf({ ...df, intercourse: e.target.checked })} />
            <span>Intercourse</span>
          </label>
          <label className="field span2"><span>Medication</span>
            <input type="text" placeholder="e.g. ibuprofen 400mg" value={df.medication}
              onChange={(e) => setDf({ ...df, medication: e.target.value })} />
          </label>
          <label className="field span2"><span>Notes</span>
            <input type="text" value={df.notes} onChange={(e) => setDf({ ...df, notes: e.target.value })} />
          </label>
          <div><button className="btn dark">Save daily log</button></div>
        </form>
      </article>
    </>
  )
}

import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api.js'
import { fmtLong } from '../lib.js'
import { icons } from '../components/icons.jsx'
import { SkeletonRows } from '../components/Skeletons.jsx'

const CRAMPS = ['none', 'mild', 'moderate', 'severe']

export default function HistoryPage({ onChanged }) {
  const [groups, setGroups] = useState(null)
  const [q, setQ] = useState('')

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
      symptom: api.deleteSymptom,
      mood: api.deleteMood,
      daily: api.deleteDaily,
    }
    try {
      if (calls[entry.type]) await calls[entry.type](entry.id)
      toast.success('Entry deleted')
      const fresh = await api.history()
      setGroups(fresh); onChanged()
    } catch (e) { toast.error(e.message) }
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
        filtered.slice(0, 60).map(([date, entries]) => (
          <div className="hist-group" key={date}>
            <h4>{fmtLong(date)}</h4>
            <ul className="entry-list">
              {entries.map((en, i) => (
                <li className="entry" key={en.id || i}>
                  <span>{describe(en)}</span>
                  {en.type !== 'period' && (
                    <button className="icon-btn danger" aria-label="Delete entry" onClick={() => del(en)}>
                      {icons.close}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </article>
  )
}

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api.js'
import { fmt } from '../lib.js'
import CalendarCells from '../components/CalendarCells.jsx'
import { SkeletonMonthCard, SkeletonRows } from '../components/Skeletons.jsx'
import { icons } from '../components/icons.jsx'

const FLOW = ['Spotting', 'Light', 'Medium', 'Heavy']

export default function CalendarPage({ periods, onChanged }) {
  const now = new Date()
  const [y, setY] = useState(now.getFullYear())
  const [m, setM] = useState(now.getMonth() + 1)
  const [tags, setTags] = useState({})

  const [pfStart, setPfStart] = useState('')
  const [pfEnd, setPfEnd] = useState('')
  const [pfFlow, setPfFlow] = useState('2')
  const [pfNotes, setPfNotes] = useState('')

  useEffect(() => {
    let live = true
    api.calendar(y, m).then((d) => { if (live) setTags(d.days) }).catch((e) => toast.error(e.message))
    return () => { live = false }
  }, [y, m, periods])

  function shift(d) {
    let nm = m + d, ny = y
    if (nm < 1) { nm = 12; ny-- }
    if (nm > 12) { nm = 1; ny++ }
    setM(nm); setY(ny)
  }

  async function savePeriod(e) {
    e.preventDefault()
    try {
      await api.addPeriod({
        start_date: pfStart,
        end_date: pfEnd || null,
        flow_level: pfFlow === '' ? null : Number(pfFlow),
        notes: pfNotes.trim(),
      })
      toast.success('Period saved ✓')
      setPfStart(''); setPfEnd(''); setPfNotes('')
      onChanged()
    } catch (err) { toast.error(err.message) }
  }

  async function del(id) {
    try { await api.deletePeriod(id); toast.success('Deleted'); onChanged() }
    catch (e) { toast.error(e.message) }
  }

  return (
    <div className="cal-layout">
      {Object.keys(tags).length === 0 ? (
        <SkeletonMonthCard />
      ) : (
        <article className="card">
          <div className="cal-header">
            <button className="icon-btn boxed" aria-label="Previous month" onClick={() => shift(-1)}>{icons.left}</button>
            <h2>{new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2>
            <button className="icon-btn boxed" aria-label="Next month" onClick={() => shift(1)}>{icons.right}</button>
          </div>
          <CalendarCells year={y} month={m} tags={tags} />
          <div className="legend">
            <span><i className="dot period" />Period</span>
            <span><i className="dot predicted_period" />Predicted</span>
            <span><i className="dot fertile" />Fertile</span>
            <span><i className="dot ovulation" />Ovulation</span>
            <span><i className="dot today" />Today</span>
          </div>
        </article>
      )}

      <div className="cal-side">
        <article className="card">
          <h3>Log a period</h3>
          <form onSubmit={savePeriod} className="stack">
            <label className="field"><span>Start</span>
              <input type="date" required value={pfStart} onChange={(e) => setPfStart(e.target.value)} />
            </label>
            <label className="field"><span>End (optional)</span>
              <input type="date" value={pfEnd} onChange={(e) => setPfEnd(e.target.value)} />
            </label>
            <label className="field"><span>Flow</span>
              <select value={pfFlow} onChange={(e) => setPfFlow(e.target.value)}>
                <option value="">—</option><option value="0">Spotting</option>
                <option value="1">Light</option><option value="2">Medium</option><option value="3">Heavy</option>
              </select>
            </label>
            <label className="field"><span>Notes</span>
              <input type="text" placeholder="Optional" value={pfNotes} onChange={(e) => setPfNotes(e.target.value)} />
            </label>
            <button className="btn dark full">Save period</button>
          </form>
        </article>

        <article className="card">
          <h3>Logged periods</h3>
          {!periods ? (
            <SkeletonRows n={3} />
          ) : periods.length === 0 ? (
            <p className="muted">No periods logged yet.</p>
          ) : (
          <ul className="entry-list">
            {periods.map((p) => (
              <li key={p.id} className="entry">
                <span>🩸 <b>{fmt(p.start_date)}</b> → {p.end_date ? fmt(p.end_date) : 'ongoing'}
                  {p.flow_level != null && <em className="badge">{FLOW[p.flow_level] || ''}</em>}</span>
                <button className="icon-btn danger" aria-label="Delete period" onClick={() => del(p.id)}>{icons.close}</button>
              </li>
            ))}
          </ul>
          )}
        </article>
      </div>
    </div>
  )
}

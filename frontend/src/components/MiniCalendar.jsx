import CalendarCells from './CalendarCells.jsx'
import { CalSkeleton } from './Skeletons.jsx'
import { api } from '../api.js'
import { useEffect, useState } from 'react'

// Compact month calendar for the dashboard.
export default function MiniCalendar({ periods, go }) {
  const now = new Date()
  const [tags, setTags] = useState(null)
  const [failed, setFailed] = useState(false)
  const y = now.getFullYear(), m = now.getMonth() + 1

  useEffect(() => {
    let live = true
    setFailed(false)
    api.calendar(y, m)
      .then((d) => { if (live) setTags(d.days) })
      .catch(() => { if (live) setFailed(true) })
    return () => { live = false }
  }, [y, m, periods])

  return (
    <article className="card mini-cal-card">
      <div className="card-head">
        <h3>{now.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h3>
        <button className="btn ghost sm" onClick={go}>Open</button>
      </div>
      {tags ? (
        <CalendarCells year={y} month={m} tags={tags} mini />
      ) : failed ? (
        <p className="muted empty-note">Calendar unavailable — <button className="btn ghost sm" onClick={() => window.location.reload()}>reload</button></p>
      ) : (
        <CalSkeleton rows={5} />
      )}
      <div className="legend compact">
        <span><i className="dot period" />Period</span>
        <span><i className="dot predicted_period" />Predicted</span>
        <span><i className="dot fertile" />Fertile</span>
        <span><i className="dot ovulation" />Ovulation</span>
      </div>
    </article>
  )
}


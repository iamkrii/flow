// Calendar day grid shared by Dashboard mini + Calendar page.
// tags: { 'YYYY-MM-DD': 'period'|'predicted_period'|'fertile'|'ovulation' }
import { todayISO } from '../lib.js'

export default function CalendarCells({ year, month, tags = {}, onPick, selected, mini = false }) {
  const first = new Date(year, month - 1, 1)
  const lead = (first.getDay() + 6) % 7 // Monday-first
  const daysInMonth = new Date(year, month, 0).getDate()
  const today = todayISO()

  const cells = [
    ...Array.from({ length: lead }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => `${year}-${String(month).padStart(2, '0')}-${String(i + 1).padStart(2, '0')}`),
  ]
  while (cells.length % 7) cells.push(null)

  return (
    <>
      <div className={'cal-weekdays' + (mini ? ' mini' : '')} aria-hidden="true">
        {(mini ? ['M', 'T', 'W', 'T', 'F', 'S', 'S'] : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
          .map((d, i) => <span key={i}>{d}</span>)}
      </div>
      <div className={'cal-grid' + (mini ? ' mini' : '')} role="grid">
        {cells.map((iso, i) => {
          if (!iso) return <span key={i} className="cal-day empty" />
          const tag = tags[iso] || 'plain'
          const cls = ['cal-day', tag]
          if (iso === today) cls.push('today')
          if (selected === iso) cls.push('selected')
          const dayNum = Number(iso.slice(8))
          return (
            <button
              key={iso}
              type="button"
              role="gridcell"
              className={cls.join(' ')}
              aria-label={`${iso}${tag !== 'plain' ? ` · ${tag.replace('_', ' ')}` : ''}`}
              aria-selected={selected === iso}
              onClick={onPick ? () => onPick(iso) : undefined}
            >
              {dayNum}
            </button>
          )
        })}
      </div>
    </>
  )
}

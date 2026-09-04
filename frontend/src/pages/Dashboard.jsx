import { icons } from '../components/icons.jsx'
import MiniCalendar from '../components/MiniCalendar.jsx'
import CycleCharts from '../components/CycleCharts.jsx'
import { SkeletonHero, SkeletonMetric, SkeletonChart } from '../components/Skeletons.jsx'


const PHASE_EMOJI = { menstrual: '🩸', follicular: '🌱', ovulation: '✨', luteal: '🌙' }

function MetricCard({ chip, label, value, note }) {
  return (
    <article className="card metric">
      <div className="metric-top">
        <span className={'chip ' + chip}>{icons.heart}</span>
        <span className="metric-label">{label}</span>
      </div>
      <div className="metric-value">{value}</div>
      {note && <span className="metric-note">{note}</span>}
    </article>
  )
}

export default function Dashboard({ overview, periods, go, dataError, onRetry }) {
  // Load failed and nothing cached: show error with retry — never endless skeletons
  if (!overview && dataError) {
    return (
      <div className="card empty-state" role="alert">
        <h3>Couldn't load your dashboard</h3>
        <p className="muted">{dataError}</p>
        <button className="btn dark" style={{ marginTop: 14 }} onClick={onRetry}>Try again</button>
      </div>
    )
  }
  // First load: render skeletons shaped like the real layout (no flash of empty state)
  if (!overview) {
    return (
      <>
        <SkeletonHero />
        <div className="metric-grid">
          <SkeletonMetric /><SkeletonMetric /><SkeletonMetric />
        </div>
        <div className="chart-grid">
          <article className="card chart-card">
            <div className="card-head"><h3>Cycle rhythm</h3></div>
            <SkeletonChart />
          </article>
          <article className="card donut-card">
            <div className="card-head"><h3>Mood mix</h3></div>
            <SkeletonChart height={180} />
          </article>
        </div>
      </>
    )
  }

  const s = overview.stats || {}
  const has = !!overview.has_data
  const day = overview.day_of_cycle
  const frac = has ? Math.min(day / (s.avg_cycle_length || 28), 1) : 0
  const CIRC = 2 * Math.PI * 52 // r=52
  const phaseLabel = has ? `${PHASE_EMOJI[overview.phase] || ''} ${(overview.phase_info?.title || overview.phase).replace(' phase', '')}` : 'Cycle overview'

  return (
    <>
      {/* Row 1 — lime hero + mini calendar */}
      <div className="home-grid">
        <article className="card hero-card">
          <div className="hero-ring">
            <svg viewBox="0 0 120 120" className="ring" role="img" aria-label={`Cycle day ${has ? day : '–'}`}>
              <circle cx="60" cy="60" r="52" className="ring-bg" />
              <circle cx="60" cy="60" r="52" className="ring-fg"
                style={{ strokeDasharray: CIRC, strokeDashoffset: CIRC * (1 - frac) }} />
            </svg>
            <div className="ring-center">
              <b id="ring-day">{has ? day : '–'}</b>
              <span>day of cycle</span>
            </div>
          </div>
          <div className="hero-body">
            <span className="pill dark">{phaseLabel}</span>
            <h2>{has ? phaseHeadline(overview) : 'Welcome to Flow'}</h2>
            <p className="muted">{has ? overview.phase_info?.title : 'Log your period to unlock predictions.'}</p>
            <ul className="insights">
              {(has ? overview.insights : ['Track your period and symptoms to see personalised insights here.'])
                .slice(0, 3).map((t) => <li key={t}>{t}</li>)}
            </ul>
            <div className="hero-actions">
              <button className="btn dark" onClick={() => go('log')}>Log symptom</button>
              <button className="btn ghost-dark" onClick={() => go('calendar')}>Open calendar</button>
            </div>
          </div>
        </article>

        <MiniCalendar periods={periods} go={() => go('calendar')} />
      </div>

      {overview.pregnancy_chance_note && (
        <div className="banner warn">⚠️ {overview.pregnancy_chance_note}</div>
      )}

      {/* Row 2 — metrics */}
      <div className="metric-grid">
        <MetricCard
          chip="coral" label="Next period"
          value={has ? fmtDate(overview.predicted_next_start) : '–'}
          note={has ? countdownNote(overview.days_until_next_period) : 'log to predict'} />
        <MetricCard
          chip="blue" label="Fertile window"
          value={has ? `${fmtDate(overview.fertile_window_start)} – ${fmtDate(overview.fertile_window_end)}` : '–'}
          note={has ? `Ovulation ~ ${fmtDate(overview.ovulation_date)}` : ''} />
        <MetricCard
          chip="lime" label="Average cycle"
          value={`${s.avg_cycle_length} d`}
          note={`${s.cycles_tracked} cycles · ${s.periods_logged} logged`} />
      </div>

      {/* Row 3 — charts */}
      <CycleCharts overview={overview} periods={periods} />
    </>
  )
}

function phaseHeadline(ov) {
  const d = ov.days_until_next_period
  if (d > 1) return `Next period in ${d} days`
  if (d === 1) return 'Next period tomorrow'
  if (d === 0) return 'Period expected today'
  return `${Math.abs(d)} days late`
}

function countdownNote(d) {
  if (d > 1) return `in ${d} days`
  if (d === 1) return 'tomorrow'
  if (d === 0) return 'expected today'
  return `${Math.abs(d)} days late`
}

function fmtDate(iso) {
  if (!iso) return '–'
  return new Date(iso.slice(0, 10) + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

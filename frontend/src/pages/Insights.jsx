import { useMemo } from 'react'
import { fmtLong, fmt } from '../lib.js'
import CycleCharts from '../components/CycleCharts.jsx'

export default function Insights({ overview, periods, reports, dataError, onRetry }) {
  // hooks first — early returns must come after all hooks
  const starts = useMemo(() =>
    [...new Set((periods || []).map(p => p.start_date))].sort(), [periods])

  const lengths = useMemo(() => {
    const out = []
    for (let i = 1; i < starts.length; i++) {
      const diff = Math.round((new Date(starts[i]) - new Date(starts[i - 1])) / 86400000)
      if (diff >= 15 && diff <= 60) out.push({ name: fmt(starts[i]), len: diff })
    }
    return out
  }, [starts])

  if (!overview) {
    return (
      <div className="card empty-state" role="alert">
        <h3>{dataError ? "Couldn't load insights" : 'Loading insights…'}</h3>
        <p className="muted">{dataError || 'Your cycle statistics will appear here.'}</p>
        {dataError && (
          <button className="btn dark" style={{ marginTop: 14 }} onClick={onRetry}>Try again</button>
        )}
      </div>
    )
  }

  const s = overview?.stats || {}
  const top = overview?.top_symptoms || []
  const moods = overview?.mood_distribution || {}
  const moodTotal = Object.values(moods).reduce((a, b) => a + b, 0)
  const related = reports?.related_queries || {}
  const complex = reports?.complex_queries || {}
  const periodSymptoms = related.period_symptoms || []
  const dailyMoods = related.daily_moods || []
  const symptomSummary = complex.symptoms_by_period || []
  const moodSummary = complex.mood_measurements || []

  return (
    <>
      <div className="two-grid">
        <article className="card chart-card">
          <div className="card-head">
            <h3>Cycle length trend</h3>
            <p className="muted sm-text">Completed cycles, oldest to newest</p>
          </div>
          {lengths.length ? (
            <ul className="stat-bars">
              {lengths.map((l, i) => (
                <li key={i}>
                  <span className="sb-label">{l.name}</span>
                  <span className="sb-track">
                    <span className="sb-fill" style={{ width: `${(l.len / Math.max(...lengths.map(x => x.len))) * 100}%` }} />
                  </span>
                  <b>{l.len} d</b>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted empty-note">Log at least two periods to see the trend.</p>
          )}
        </article>

        <article className="card">
          <h3>Top symptoms</h3>
          {top.length === 0 && <p className="muted">No symptoms logged.</p>}
          <ul className="stat-bars">
            {top.map((t) => (
              <li key={t.symptom}>
                <span className="sb-label">{t.symptom}</span>
                <span className="sb-track">
                  <span className="sb-fill coral" style={{ width: `${(t.count / top[0].count) * 100}%` }} />
                </span>
                <b>{t.count}×</b>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Mood distribution</h3>
          {moodTotal === 0 && <p className="muted">No moods logged.</p>}
          <ul className="stat-bars">
            {Object.entries(moods).sort((a, b) => b[1] - a[1]).map(([m, c]) => (
              <li key={m}>
                <span className="sb-label">{m}</span>
                <span className="sb-track">
                  <span className="sb-fill blue" style={{ width: `${(c / moodTotal) * 100}%` }} />
                </span>
                <b>{Math.round(c / moodTotal * 100)}%</b>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Averages</h3>
          <ul className="stats-list">
            <li><span>Average cycle</span><b>{s.avg_cycle_length ?? '–'} days</b></li>
            <li><span>Average period</span><b>{s.avg_period_length ?? '–'} days</b></li>
            <li><span>Cycles tracked</span><b>{s.cycles_tracked ?? 0}</b></li>
            <li><span>Variability</span><b>±{s.cycle_variability ?? 0} days</b></li>
            <li><span>Last period</span><b>{overview?.last_period_start ? fmtLong(overview.last_period_start) : '–'}</b></li>
            <li><span>Next predicted</span><b>{overview?.predicted_next_start ? fmtLong(overview.predicted_next_start) : '–'}</b></li>
          </ul>
        </article>
      </div>

      <CycleCharts overview={overview} periods={periods} />

      <div className="two-grid" style={{ marginTop: 20 }}>
        <article className="card">
          <div className="card-head">
            <h3>Related database queries</h3>
            <p className="muted sm-text">Live joined records</p>
          </div>
          <ul className="stats-list">
            <li><span>Periods + settings</span><b>{(related.period_settings || []).length} rows</b></li>
            <li><span>Periods + symptoms</span><b>{periodSymptoms.length} rows</b></li>
            <li><span>Daily logs + moods</span><b>{dailyMoods.length} rows</b></li>
          </ul>
          {periodSymptoms.length > 0 && (
            <p className="muted sm-text" style={{ marginTop: 12 }}>
              Latest period: {periodSymptoms[0].start_date || '–'} · {periodSymptoms[0].symptom_count} symptom(s)
            </p>
          )}
        </article>

        <article className="card">
          <div className="card-head">
            <h3>Complex query summaries</h3>
            <p className="muted sm-text">Three-table aggregates</p>
          </div>
          <ul className="stats-list">
            <li><span>Symptoms across periods</span><b>{symptomSummary.length} types</b></li>
            <li><span>Moods with measurements</span><b>{moodSummary.length} types</b></li>
          </ul>
          {symptomSummary[0] && (
            <p className="muted sm-text" style={{ marginTop: 12 }}>
              Most common: {symptomSummary[0].symptom} ({symptomSummary[0].symptom_count} logs)
            </p>
          )}
        </article>
      </div>
    </>
  )
}

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

  // The report endpoint combines related records and aggregates on the
  // server. Turn those results into plain-language guidance for the user.
  const personalPatterns = useMemo(() => {
    const related = reports?.related_queries || {}
    const complex = reports?.complex_queries || {}
    const periodSettings = (related.period_settings || []).find((row) => row.period_id)
    const periodSymptoms = (related.period_symptoms || [])[0]
    const dailyMood = (related.daily_moods || [])[0]
    const recurringSymptom = (complex.symptoms_by_period || [])[0]
    const moodPatterns = complex.mood_measurements || []
    const energisingMood = moodPatterns.reduce((best, current) => {
      if (!best) return current
      return Number(current.average_energy) > Number(best.average_energy) ? current : best
    }, null)

    return { periodSettings, periodSymptoms, dailyMood, recurringSymptom, energisingMood }
  }, [reports])

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
  const { periodSettings, periodSymptoms, dailyMood, recurringSymptom, energisingMood } = personalPatterns

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
            <h3>Your cycle patterns</h3>
            <p className="muted sm-text">A clearer view of your recent tracking</p>
          </div>
          <ul className="stats-list">
            <li>
              <span>Typical cycle</span>
              <b>{periodSettings ? `${periodSettings.avg_cycle_length} days` : 'Log a period'}</b>
            </li>
            <li>
              <span>Typical period</span>
              <b>{periodSettings ? `${periodSettings.avg_period_length} days` : 'Log a period'}</b>
            </li>
            <li>
              <span>Latest period symptoms</span>
              <b>{periodSymptoms ? `${periodSymptoms.symptom_count} logged` : 'None yet'}</b>
            </li>
          </ul>
          {periodSymptoms && (
            <p className="muted sm-text" style={{ marginTop: 12 }}>
              {periodSymptoms.start_date ? `Period starting ${fmtLong(periodSymptoms.start_date)} averaged ${Number(periodSymptoms.average_severity || 0).toFixed(1)}/5 symptom severity.` : 'Add a period and symptoms to see a pattern.'}
            </p>
          )}
        </article>

        <article className="card">
          <div className="card-head">
            <h3>Patterns to notice</h3>
            <p className="muted sm-text">Trends across your logged days</p>
          </div>
          <ul className="stats-list">
            <li>
              <span>Most recurring symptom</span>
              <b>{recurringSymptom ? recurringSymptom.symptom : 'Not enough data'}</b>
            </li>
            <li>
              <span>Most energising mood</span>
              <b>{energisingMood ? energisingMood.mood : 'Not enough data'}</b>
            </li>
            <li>
              <span>Latest mood check-in</span>
              <b>{dailyMood?.mood || 'No mood logged'}</b>
            </li>
          </ul>
          {recurringSymptom && (
            <p className="muted sm-text" style={{ marginTop: 12 }}>
              {recurringSymptom.symptom} appears {recurringSymptom.symptom_count} time(s) across {recurringSymptom.periods_with_symptom} period(s).
            </p>
          )}
          {dailyMood && !recurringSymptom && (
            <p className="muted sm-text" style={{ marginTop: 12 }}>
              Latest check-in: {dailyMood.mood || 'No mood'}{dailyMood.energy ? ` · energy ${dailyMood.energy}/5` : ''}.
            </p>
          )}
        </article>
      </div>
    </>
  )
}

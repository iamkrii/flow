import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { fmt } from '../lib.js'

const COLORS = ['#F97316', '#A3E635', '#93C5FD', '#C4B5FD', '#FDA4AF', '#FDE047']

export default function CycleCharts({ overview, periods }) {
  // ---- cycle lengths between consecutive period starts
  const starts = [...new Set((periods || []).map(p => p.start_date))].sort()
  const lengths = []
  for (let i = 1; i < starts.length; i++) {
    const diff = Math.round((new Date(starts[i]) - new Date(starts[i - 1])) / 86400000)
    if (diff >= 15 && diff <= 60) {
      lengths.push({ name: fmt(starts[i]).replace(' ', '\u00a0'), len: diff })
    }
  }
  const avg = overview?.stats?.avg_cycle_length

  return (
    <div className="chart-grid">
      <article className="card chart-card">
        <div className="card-head">
          <h3>Cycle rhythm</h3>
          <p className="muted sm-text">Length of each completed cycle vs your average</p>
        </div>
        {lengths.length ? (
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={lengths} barSize={26} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="4 6" stroke="#E7EBF3" />
              <XAxis dataKey="name" tickLine={false} axisLine={false}
                tick={{ fontSize: 11, fill: '#8B94A7' }} interval={0}
                angle={-35} textAnchor="end" height={44} />
              <YAxis domain={[12, Math.max(...lengths.map(d => d.len), avg || 0) + 4]}
                tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#8B94A7' }} />
              <Tooltip cursor={{ fill: 'rgba(0,0,0,.03)' }} formatter={(v) => [`${v} days`, 'Cycle length']} />
              {avg && (
                <ReferenceLine y={avg} stroke="#111827" strokeDasharray="5 5"
                  label={{ value: `avg ${avg}d`, position: 'insideTopRight', fontSize: 11, fill: '#111827' }} />
              )}
              {/* ghost track + solid bar = reference "conversion" look */}
              <Bar dataKey="len" radius={[9, 9, 9, 9]} background={{ fill: '#EEF2F9', radius: 9 }} fill="#F97316" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="muted empty-note">Log at least two periods to see your rhythm.</p>
        )}
      </article>

      <MoodDonut overview={overview} />
    </div>
  )
}

function MoodDonut({ overview }) {
  const dist = overview?.mood_distribution || {}
  let entries = Object.entries(dist).map(([name, value]) => ({ name, value }))
  entries.sort((a, b) => b.value - a.value)
  if (entries.length > 5) entries = entries.slice(0, 5)
  const total = entries.reduce((s, e) => s + e.value, 0)

  return (
    <article className="card donut-card">
      <div className="card-head"><h3>Mood mix</h3></div>
      {total === 0 ? (
        <p className="muted empty-note">Log moods to see the distribution.</p>
      ) : (
        <div className="donut-wrap">
          <div className="donut-box">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={entries} dataKey="value" innerRadius={58} outerRadius={82}
                  paddingAngle={3} strokeWidth={0} startAngle={90} endAngle={-270}>
                  {entries.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v} logs`, n]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center">
              <b>{total}</b>
              <span>mood logs</span>
            </div>
          </div>
          <ul className="donut-legend">
            {entries.map((e, i) => (
              <li key={e.name}>
                <i style={{ background: COLORS[i % COLORS.length] }} />
                <span>{e.name}</span>
                <b>{Math.round(e.value / total * 100)}%</b>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}

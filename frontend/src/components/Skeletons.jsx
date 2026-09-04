// Skeleton primitives + composed loaders that mirror each page's real layout.
export function Skeleton({ w, h, r = 10, className = '', style = {} }) {
  return (
    <span
      className={`sk ${className}`}
      style={{ width: w, height: h, borderRadius: r, ...style }}
      aria-hidden="true"
    />
  )
}

// Metric card: chip square + label line + big number
export function SkeletonMetric() {
  return (
    <article className="card metric" aria-busy="true">
      <div className="metric-top">
        <Skeleton w={38} h={38} r={12} />
        <Skeleton w={92} h={12} />
      </div>
      <Skeleton w={120} h={30} r={8} style={{ marginTop: 6 }} />
      <Skeleton w={140} h={11} />
    </article>
  )
}

// Dashboard hero: ring circle + text block with pill/lines/buttons
export function SkeletonHero() {
  return (
    <div className="home-grid" aria-busy="true">
      <article className="card hero-card">
        <Skeleton w={190} h={190} r="50%" className="hero-ring-sk" />
        <div className="hero-body" style={{ flex: 1 }}>
          <Skeleton w={110} h={22} r={999} />
          <Skeleton w={230} h={26} r={8} style={{ margin: '14px 0 8px' }} />
          <Skeleton w="85%" h={12} />
          <Skeleton w="70%" h={12} style={{ marginTop: 8 }} />
          <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
            <Skeleton w={120} h={38} r={999} />
            <Skeleton w={130} h={38} r={999} />
          </div>
        </div>
      </article>
      <article className="card mini-cal-card">
        <div className="card-head"><Skeleton w={130} h={18} /><Skeleton w={64} h={30} r={999} /></div>
        <CalSkeleton />
      </article>
    </div>
  )
}

// Mini calendar grid of round cells
export function CalSkeleton({ rows = 5 }) {
  return (
    <>
      <div className="cal-weekdays mini" aria-hidden="true">
        {Array.from({ length: 7 }).map((_, i) => (
          <span key={i}><Skeleton w={14} h={10} r={4} /></span>
        ))}
      </div>
      <div className="cal-grid mini">
        {Array.from({ length: 7 * rows }).map((_, i) => (
          <span key={i} className="sk cal-cell" style={{ width: '100%', aspectRatio: '1' }} />
        ))}
      </div>
    </>
  )
}

// Full month calendar card (Calendar page)
export function SkeletonMonthCard() {
  return (
    <article className="card" aria-busy="true">
      <div className="cal-header">
        <Skeleton w={38} h={38} r="50%" />
        <Skeleton w={170} h={22} r={8} />
        <Skeleton w={38} h={38} r="50%" />
      </div>
      <CalSkeleton rows={6} />
    </article>
  )
}

// Chart area placeholder
export function SkeletonChart({ height = 230 }) {
  return (
    <div className="chart-sk" style={{ height }} aria-busy="true">
      {[62, 84, 45, 95, 58, 74].map((h, i) => (
        <span key={i} className="sk sk-bar" style={{ height: `${h}%` }} />
      ))}
    </div>
  )
}

// Generic list rows (history / period lists)
export function SkeletonRows({ n = 4, labelW = 150 }) {
  return (
    <div aria-busy="true">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="entry" style={{ justifyContent: 'flex-start', gap: 12 }}>
          <Skeleton w={labelW + (i % 3) * 24} h={13} />
          <span style={{ flex: 1 }} />
          <Skeleton w={26} h={26} r="50%" />
        </div>
      ))}
    </div>
  )
}

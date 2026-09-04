import { icons } from './icons.jsx'
import { fmtLong, todayISO } from '../lib.js'

const TITLES = {
  home: ['Dashboard', 'Your cycle at a glance'],
  calendar: ['Calendar', 'Periods, predictions and fertile days'],
  log: ['Log', 'Symptoms, mood and daily details'],
  history: ['History', 'Everything you have tracked'],
  insights: ['Insights', 'Trends across your cycles'],
  settings: ['Settings', 'Personalise Flow'],
}

export default function PageHeader({ tab, user, onQuickStart, onExport }) {
  const [title, sub] = TITLES[tab] || ['Flow', '']
  const hour = new Date().getHours()
  const hello = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const name = user?.name?.trim()
  return (
    <header className="pagehead">
      <div className="pagehead-left">
        <h1>
          {tab === 'home'
            ? <>{hello}{name ? `, ${name}` : ''} <span className="wave">👋</span></>
            : title}
        </h1>
        <p className="pagehead-sub">{tab === 'home' ? sub || todayISO() : sub}</p>
      </div>
      <div className="pagehead-actions">
        <span className="date-pill">{fmtLong(todayISO())}</span>
        <button className="icon-btn boxed" title="Export data (JSON)" aria-label="Export data" onClick={onExport}>
          {icons.download}
        </button>
        {tab === 'home' && (
          <button className="btn lime" onClick={onQuickStart}>
            <span className="dot-live" /> Period started today
          </button>
        )}
      </div>
    </header>
  )
}

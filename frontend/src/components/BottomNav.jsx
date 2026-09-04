import { icons } from './icons.jsx'

export default function BottomNav({ items, tab, setTab }) {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      {items.map((it) => (
        <button key={it.id} type="button"
          className={'bn-item' + (tab === it.id ? ' active' : '')}
          aria-current={tab === it.id ? 'page' : undefined}
          onClick={() => setTab(it.id)}>
          {icons[it.icon]}
          <span>{it.label}</span>
        </button>
      ))}
    </nav>
  )
}

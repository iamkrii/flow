import { icons } from './icons.jsx'

export default function BottomNav({ items, tab, navigate }) {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      {items.map((it) => (
        <a key={it.id} href={it.path}
          className={'bn-item' + (tab === it.id ? ' active' : '')}
          aria-current={tab === it.id ? 'page' : undefined}
          onClick={(event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
            event.preventDefault(); navigate(it.id)
          }}>
          {icons[it.icon]}
          <span>{it.label}</span>
        </a>
      ))}
    </nav>
  )
}

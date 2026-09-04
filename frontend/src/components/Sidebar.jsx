import { icons } from './icons.jsx'

// Persistent white sidebar (desktop). items: [{id,label,icon}]
export default function Sidebar({ items, tab, setTab, user, onLogout }) {
  return (
    <aside className="sidebar">
      <div className="logo"><span className="logo-mark">🌸</span><span className="logo-word">flow</span></div>
      <nav className="side-nav" aria-label="Main">
        {items.map((it) => (
          <button
            key={it.id}
            type="button"
            className={'nav-item' + (tab === it.id ? ' active' : '')}
            aria-current={tab === it.id ? 'page' : undefined}
            onClick={() => setTab(it.id)}
          >
            {icons[it.icon]}
            <span>{it.label}</span>
          </button>
        ))}
      </nav>
      {user && (
        <div className="user-row">
          <span className="avatar">{(user.name || user.email || '?')[0].toUpperCase()}</span>
          <span className="user-meta">
            <b>{user.name || 'Welcome'}</b>
            <i>{user.email}</i>
          </span>
          <button className="icon-btn" title="Log out" aria-label="Log out" onClick={onLogout}>
            {icons.logout}
          </button>
        </div>
      )}
    </aside>
  )
}

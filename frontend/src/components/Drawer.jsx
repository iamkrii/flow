import { icons } from './icons.jsx'

export default function Drawer({ open, onClose, items, tab, setTab, user, onLogout }) {
  return (
    <>
      <div className={'drawer-overlay' + (open ? ' show' : '')} onClick={onClose} />
      <aside className={'drawer' + (open ? ' open' : '')} aria-hidden={!open} aria-label="Menu">
        <div className="drawer-head">
          <div className="logo"><span className="logo-mark">🌸</span><span className="logo-word">flow</span></div>
          <button className="icon-btn" aria-label="Close menu" onClick={onClose}>{icons.close}</button>
        </div>
        <nav className="side-nav" aria-label="Main menu">
          {items.map((it) => (
            <button key={it.id} type="button"
              className={'nav-item' + (tab === it.id ? ' active' : '')}
              onClick={() => { setTab(it.id); onClose() }}>
              {icons[it.icon]}<span>{it.label}</span>
            </button>
          ))}
        </nav>
        <div className="drawer-foot">
          {user && (
            <div className="user-row">
              <span className="avatar">{(user.name || user.email || '?')[0].toUpperCase()}</span>
              <span className="user-meta"><b>{user.name || 'Welcome'}</b><i>{user.email}</i></span>
            </div>
          )}
          <button className="btn danger full" onClick={onLogout}>Log out</button>
        </div>
      </aside>
    </>
  )
}

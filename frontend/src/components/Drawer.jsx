import { icons } from './icons.jsx'

export default function Drawer({ open, onClose, items, tab, navigate, user, onLogout }) {
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
            <a key={it.id} href={it.path}
              className={'nav-item' + (tab === it.id ? ' active' : '')}
              aria-current={tab === it.id ? 'page' : undefined}
              onClick={(event) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
                event.preventDefault(); navigate(it.id); onClose()
              }}>
              {icons[it.icon]}<span>{it.label}</span>
            </a>
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

import { icons } from './icons.jsx'

export default function MobileTopbar({ onMenu }) {
  return (
    <header className="mobile-topbar">
      <div className="logo"><span className="logo-mark">🌸</span><span className="logo-word">flow</span></div>
      <button className="icon-btn" aria-label="Open menu" onClick={onMenu}>{icons.menu}</button>
    </header>
  )
}

import { useEffect, useState, useCallback } from 'react'
import { Toaster, toast } from 'react-hot-toast'

import { api, getToken, clearToken } from './api.js'
import { registerToast } from './lib.js'
import { exportData } from './export.js'
import Auth from './pages/Auth.jsx'
import Dashboard from './pages/Dashboard.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import LogPage from './pages/LogPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import Insights from './pages/Insights.jsx'
import Settings from './pages/Settings.jsx'
import Sidebar from './components/Sidebar.jsx'
import BottomNav from './components/BottomNav.jsx'
import MobileTopbar from './components/MobileTopbar.jsx'
import Drawer from './components/Drawer.jsx'
import PageHeader from './components/PageHeader.jsx'

const NAV = [
  { id: 'home', label: 'Dashboard', icon: 'home' },
  { id: 'calendar', label: 'Calendar', icon: 'calendar' },
  { id: 'log', label: 'Log', icon: 'plus' },
  { id: 'history', label: 'History', icon: 'history' },
  { id: 'insights', label: 'Insights', icon: 'insights' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
]

export default function App() {
  const [user, setUser] = useState(null)
  const [me, setMe] = useState(null)
  const [booting, setBooting] = useState(!!getToken())
  const [tab, setTab] = useState('home')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [overview, setOverview] = useState(null)
  const [periods, setPeriods] = useState([])
  const [dataError, setDataError] = useState(null)

  useEffect(() => registerToast(toast), [])

  const refreshAll = useCallback(async () => {
    try {
      const [ov, ps] = await Promise.all([api.overview(), api.periods()])
      setOverview(ov); setPeriods(ps); setDataError(null)
      return true
    } catch (e) {
      setDataError(e.message)
      toast.error(e.message)
      return false
    }
  }, [])

  // resume session — MUST also load app data, otherwise the dashboard
  // would sit on skeletons forever after a page reload
  useEffect(() => {
    if (!getToken()) return
    let live = true
    ;(async () => {
      try {
        const d = await api.me()
        if (!live) return
        setUser({ email: d.user.email, name: d.user.name || '' })
        setMe(d)
        await refreshAll()
      } catch {
        clearToken()
      } finally {
        if (live) setBooting(false)
      }
    })()
    return () => { live = false }
  }, [refreshAll])

  async function handleAuthed(name) {
    try {
      const d = await api.me()
      setUser({ email: d.user.email, name: name || d.user.name || '' })
      setMe(d)
      await refreshAll()
    } catch (e) { toast.error(e.message) }
  }

  async function handleLogout() {
    clearToken()
    setUser(null); setMe(null); setOverview(null); setPeriods([]); setTab('home')
  }

  async function quickPeriodStart() {
    try {
      await api.addPeriod({ start_date: new Date().toISOString().slice(0, 10), flow_level: 2, notes: '' })
      toast.success('Period start logged for today 🩸')
      await refreshAll()
    } catch (e) { toast.error(e.message) }
  }

  if (booting) {
    return <div className="boot-screen"><span className="logo-mark big">🌸</span></div>
  }

  if (!user) {
    return (
      <>
        <Auth onAuthed={handleAuthed} />
        <Toaster position="top-center" />
      </>
    )
  }

  const pages = {
    home: <Dashboard overview={overview} periods={periods} go={setTab} dataError={dataError} onRetry={refreshAll} />,
    calendar: <CalendarPage periods={periods} onChanged={refreshAll} />,
    log: <LogPage onChanged={refreshAll} />,
    history: <HistoryPage onChanged={refreshAll} />,
    insights: <Insights overview={overview} periods={periods} dataError={dataError} onRetry={refreshAll} />,
    settings: <Settings me={me} onSaved={refreshAll} />,
  }

  return (
    <div className="app">
      <Sidebar
        items={NAV} tab={tab} setTab={setTab}
        user={user} onLogout={handleLogout}
      />
      <MobileTopbar onMenu={() => setDrawerOpen(true)} />
      <Drawer
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        items={NAV} tab={tab} setTab={setTab}
        user={user} onLogout={handleLogout}
      />
      <div className="shell">
        <PageHeader
          tab={tab} user={user}
          onQuickStart={quickPeriodStart}
          onExport={() => exportData(api)}
        />
        <main className="content">{pages[tab]}</main>
      </div>
      <BottomNav items={NAV} tab={tab} setTab={setTab} />
      <Toaster position="top-center" />
    </div>
  )
}

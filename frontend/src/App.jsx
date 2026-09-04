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
  { id: 'home', path: '/dashboard', label: 'Dashboard', icon: 'home' },
  { id: 'calendar', path: '/calendar', label: 'Calendar', icon: 'calendar' },
  { id: 'log', path: '/log', label: 'Log', icon: 'plus' },
  { id: 'history', path: '/history', label: 'History', icon: 'history' },
  { id: 'insights', path: '/insights', label: 'Insights', icon: 'insights' },
  { id: 'settings', path: '/settings', label: 'Settings', icon: 'settings' },
]

const AUTH_ROUTES = [
  { id: 'login', path: '/login' },
  { id: 'signup', path: '/signup' },
]
const ROUTES = [...NAV, ...AUTH_ROUTES]
const TAB_BY_PATH = Object.fromEntries(ROUTES.map(({ id, path }) => [path, id]))
const PATH_BY_TAB = Object.fromEntries(ROUTES.map(({ id, path }) => [id, path]))

function currentTab() {
  return TAB_BY_PATH[window.location.pathname] || 'home'
}

export default function App() {
  const [user, setUser] = useState(null)
  const [me, setMe] = useState(null)
  const [booting, setBooting] = useState(!!getToken())
  const [tab, setTab] = useState(currentTab)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [overview, setOverview] = useState(null)
  const [periods, setPeriods] = useState([])
  const [dataError, setDataError] = useState(null)

  useEffect(() => registerToast(toast), [])

  // A tiny History API router is enough for these static screens. It keeps
  // navigation client-side while making browser back/forward and deep links work.
  useEffect(() => {
    const syncRoute = () => setTab(currentTab())
    window.addEventListener('popstate', syncRoute)

    if (!TAB_BY_PATH[window.location.pathname]) {
      window.history.replaceState({}, '', getToken() ? '/dashboard' : '/login')
      syncRoute()
    }

    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  const navigate = useCallback((nextTab, { replace = false } = {}) => {
    const path = PATH_BY_TAB[nextTab] || PATH_BY_TAB.home
    window.history[replace ? 'replaceState' : 'pushState']({}, '', path)
    setTab(PATH_BY_TAB[nextTab] ? nextTab : 'home')
    window.scrollTo(0, 0)
  }, [])

  useEffect(() => {
    if (booting) return
    const isAuthRoute = tab === 'login' || tab === 'signup'
    if (!user && !isAuthRoute) navigate('login', { replace: true })
    if (user && isAuthRoute) navigate('home', { replace: true })
  }, [booting, navigate, tab, user])

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
      navigate('home', { replace: true })
    } catch (e) { toast.error(e.message) }
  }

  async function handleLogout() {
    clearToken()
    setUser(null); setMe(null); setOverview(null); setPeriods([]); navigate('login', { replace: true })
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
        <Auth
          mode={tab === 'signup' ? 'signup' : 'login'}
          onModeChange={(mode) => navigate(mode)}
          onAuthed={handleAuthed}
        />
        <Toaster position="top-center" />
      </>
    )
  }

  const pages = {
    home: <Dashboard overview={overview} periods={periods} go={navigate} dataError={dataError} onRetry={refreshAll} />,
    calendar: <CalendarPage periods={periods} onChanged={refreshAll} />,
    log: <LogPage onChanged={refreshAll} />,
    history: <HistoryPage onChanged={refreshAll} />,
    insights: <Insights overview={overview} periods={periods} dataError={dataError} onRetry={refreshAll} />,
    settings: <Settings me={me} onSaved={refreshAll} />,
  }

  return (
    <div className="app">
      <Sidebar
        items={NAV} tab={tab} navigate={navigate}
        user={user} onLogout={handleLogout}
      />
      <MobileTopbar onMenu={() => setDrawerOpen(true)} />
      <Drawer
        open={drawerOpen} onClose={() => setDrawerOpen(false)}
        items={NAV} tab={tab} navigate={navigate}
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
      <BottomNav items={NAV} tab={tab} navigate={navigate} />
      <Toaster position="top-center" />
    </div>
  )
}

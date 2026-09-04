import { useState } from 'react'
import { api, setToken } from '../api.js'

export default function Auth({ onAuthed }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      const data = mode === 'login'
        ? await api.login(email.trim(), password)
        : await api.signup(email.trim(), password, name.trim())
      setToken(data.token)
      onAuthed(data.name || '')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-logo"><span className="logo-mark">🌸</span> flow</div>
        <p className="tagline">Your cycle, understood.</p>
        <div className="auth-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={mode === 'login'}
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}>Log in</button>
          <button type="button" role="tab" aria-selected={mode === 'signup'}
            className={mode === 'signup' ? 'active' : ''}
            onClick={() => setMode('signup')}>Sign up</button>
        </div>
        <form onSubmit={submit} className="auth-form">
          <label className="field"><span>Email</span>
            <input type="email" required autoComplete="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field"><span>Password</span>
            <input type="password" required minLength={6} placeholder="Min 6 characters"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {mode === 'signup' && (
            <label className="field"><span>Your name</span>
              <input type="text" autoComplete="name" placeholder="Optional"
                value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          )}
          {error && <div className="error" role="alert">{error}</div>}
          <button className="btn dark full" disabled={busy} type="submit">
            {busy ? '…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  )
}

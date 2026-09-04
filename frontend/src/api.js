// Flow API client — mirrors the old api.js, promise-based for React.
const TOKEN_KEY = 'flow_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function req(path, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  })
  if (res.status === 401 && token) {
    clearToken()
    const err = new Error('Session expired — please log in again.')
    err.expired = true
    throw err
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || 'Request failed')
  return data
}

export const api = {
  signup: (email, password, name) => req('/auth/signup', 'POST', { email, password, name }),
  login: (email, password) => req('/auth/login', 'POST', { email, password }),
  me: () => req('/me'),
  overview: () => req('/overview'),
  calendar: (y, m) => req(`/calendar/${y}/${m}`),
  history: () => req('/history'),
  periods: () => req('/periods'),
  addPeriod: (p) => req('/periods', 'POST', p),
  updatePeriod: (id, p) => req(`/periods/${id}`, 'PUT', p),
  deletePeriod: (id) => req(`/periods/${id}`, 'DELETE'),
  addSymptom: (s) => req('/symptoms', 'POST', s),
  deleteSymptom: (id) => req(`/symptoms/${id}`, 'DELETE'),
  addMood: (m) => req('/moods', 'POST', m),
  deleteMood: (id) => req(`/moods/${id}`, 'DELETE'),
  addDaily: (d) => req('/daily', 'POST', d),
  deleteDaily: (id) => req(`/daily/${id}`, 'DELETE'),
  saveSettings: (s) => req('/settings', 'PUT', s),
}

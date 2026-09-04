// Shared date helpers + tiny toast bus.
export const todayISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export const fmt = (iso) => {
  if (!iso) return '–'
  const d = new Date(iso.slice(0, 10) + 'T00:00:00')
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export const fmtLong = (iso) => {
  if (!iso) return '–'
  const d = new Date(iso.slice(0, 10) + 'T00:00:00')
  return d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'long', year: 'numeric' })
}

let toastFn = null
export const registerToast = (fn) => { toastFn = fn }
export const toast = (msg) => { if (toastFn) toastFn(msg) }

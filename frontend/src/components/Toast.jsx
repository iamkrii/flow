import { registerToast } from './lib.js'
import { useEffect, useState } from 'react'

// Renders the single toast; call `toast()` from anywhere.
export default function Toast() {
  const [msg, setMsg] = useState(null)
  useEffect(() => registerToast((m) => {
    setMsg(m)
    clearTimeout(Toast._h)
    Toast._h = setTimeout(() => setMsg(null), 2600)
  }), [])
  if (!msg) return null
  return <div className="toast" role="status">{msg}</div>
}

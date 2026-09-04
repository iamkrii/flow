import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { api } from '../api.js'

export default function Settings({ me, onSaved }) {
  const [form, setForm] = useState({
    avg_cycle_length: 28, avg_period_length: 5, luteal_phase_length: 14,
    birth_control: '', notifications_enabled: true,
  })
  const [account, setAccount] = useState(null)

  useEffect(() => {
    if (!me) return
    const s = me.settings || {}
    setForm({
      avg_cycle_length: s.avg_cycle_length ?? 28,
      avg_period_length: s.avg_period_length ?? 5,
      luteal_phase_length: s.luteal_phase_length ?? 14,
      birth_control: s.birth_control ?? '',
      notifications_enabled: !!s.notifications_enabled,
    })
    setAccount(me.user)
  }, [me])

  async function save(e) {
    e.preventDefault()
    try {
      const updated = await api.saveSettings({
        avg_cycle_length: Number(form.avg_cycle_length),
        avg_period_length: Number(form.avg_period_length),
        luteal_phase_length: Number(form.luteal_phase_length),
        birth_control: form.birth_control || null,
        notifications_enabled: form.notifications_enabled,
      })
      toast.success('Settings saved ✓')
      onSaved && onSaved(updated)
    } catch (err) { toast.error(err.message) }
  }

  return (
    <div className="two-grid">
      <article className="card">
        <h3>Cycle settings</h3>
        <form onSubmit={save} className="stack">
          <label className="field"><span>Average cycle length (days)</span>
            <input type="number" min="15" max="60" value={form.avg_cycle_length}
              onChange={(e) => setForm({ ...form, avg_cycle_length: e.target.value })} />
          </label>
          <label className="field"><span>Average period length (days)</span>
            <input type="number" min="1" max="14" value={form.avg_period_length}
              onChange={(e) => setForm({ ...form, avg_period_length: e.target.value })} />
          </label>
          <label className="field"><span>Luteal phase length (days)</span>
            <input type="number" min="7" max="21" value={form.luteal_phase_length}
              onChange={(e) => setForm({ ...form, luteal_phase_length: e.target.value })} />
          </label>
          <label className="field"><span>Birth control</span>
            <select value={form.birth_control} onChange={(e) => setForm({ ...form, birth_control: e.target.value })}>
              <option value="">—</option><option>Pill</option><option>IUD</option>
              <option>Implant</option><option>Injection</option><option>Patch</option>
              <option>Ring</option><option>None / other</option>
            </select>
          </label>
          <label className="field check">
            <input type="checkbox" checked={form.notifications_enabled}
              onChange={(e) => setForm({ ...form, notifications_enabled: e.target.checked })} />
            <span>Reminders enabled</span>
          </label>
          <button className="btn dark full">Save settings</button>
        </form>
      </article>

      <article className="card">
        <h3>Account</h3>
        {account && (
          <ul className="stats-list">
            <li><span>Email</span><b>{account.email}</b></li>
            <li><span>Name</span><b>{account.name || '—'}</b></li>
            <li><span>Member since</span><b>{(account.created_at || '').slice(0, 10)}</b></li>
          </ul>
        )}
      </article>
    </div>
  )
}

import toast from 'react-hot-toast'

export async function exportData(api) {
  try {
    const data = {
      exported_at: new Date().toISOString(),
      me: await api.me(),
      overview: await api.overview(),
      periods: await api.periods(),
      history: await api.history(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'flow-export.json'
    a.click()
    URL.revokeObjectURL(a.href)
    toast.success('Data exported ⬇')
  } catch (e) {
    toast.error(e.message)
  }
}

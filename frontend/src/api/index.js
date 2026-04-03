const API_BASE = import.meta.env.VITE_API_BASE_URL

export const fetchAISLive = async () => {
  const res = await fetch(`${API_BASE}/ais/live`)
  if (!res.ok) throw new Error('Live AIS feed unavailable. Defaulting to cached vectors.')
  return res.json()
}

export const fetchChokepoints = async () => {
  const res = await fetch(`${API_BASE}/risk/chokepoints`)
  if (!res.ok) throw new Error('Risk Engine timeout. Unable to fetch telemetry overlays.')
  return res.json()
}

export const fetchAlertsMock = async () => {
  // Temporary mock since alerts feed is agentic / ws based in standard operation
  return [
    { id: 1, type: 'CRITICAL', text: 'Demand Spike: SKU-001 (+35%)', time: 'Just now' },
    { id: 2, type: 'WARNING', text: 'Suez Canal Context Delay', time: '2m ago' },
    { id: 3, type: 'COMPLETED', text: 'Auto-PO Approved by Agent', time: '14m ago' },
    { id: 4, type: 'WARNING', text: 'D/S Ratio Breached for Semicon', time: '1hr ago' },
    { id: 5, type: 'UPDATE', text: 'Global Risk Index recomputed', time: '2hr ago' },
  ]
}

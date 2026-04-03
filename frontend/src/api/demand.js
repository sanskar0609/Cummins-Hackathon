const API_BASE = import.meta.env.VITE_API_BASE_URL

// Routes available per SKU — matches backend seeded data
export const ROUTE_MAP = {
  'SKU-001': 'SUEZ-ROTTERDAM',
  'SKU-002': 'PANAMA-LA',
  'SKU-003': 'TAIWAN-LA',
}

export const SKU_LIST = ['SKU-001', 'SKU-002', 'SKU-003']

export const fetchForecast = async (sku) => {
  const res = await fetch(`${API_BASE}/demand/forecast?sku=${sku}`)
  if (!res.ok) throw new Error(`Forecast unavailable for ${sku} — server returned ${res.status}`)
  return res.json()
}

export const fetchDSRatio = async (sku) => {
  const route = ROUTE_MAP[sku] || 'SUEZ-ROTTERDAM'
  const res = await fetch(`${API_BASE}/supply/ds-ratio?sku=${sku}&route_id=${route}`)
  if (!res.ok) throw new Error(`D/S ratio unavailable for ${sku} — server returned ${res.status}`)
  return res.json()
}
